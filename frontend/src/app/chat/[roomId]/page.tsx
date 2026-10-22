"use client";

import { useState, useEffect, useRef, use } from "react";
import { apiFetch, API_BASE, tokenStore } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/lib/useAuth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProfilePublicOut } from "@/components/matches/MatchCard";

interface ChatMessage {
    id: number;
    sender_id: number;
    content: string;
    created_at: string;
    is_read: boolean;
}

interface ChatParticipant {
    user_id: number;
    user: {
        id: number;
        profile: ProfilePublicOut | null;
    };
}

interface ChatRoom {
    id: number;
    is_active: boolean;
    participants: ChatParticipant[];
}

function ChatRoomInner({ roomId }: { roomId: number }) {
    const { toast } = useToast();
    const { user } = useAuth();
    const router = useRouter();

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [roomInfo, setRoomInfo] = useState<ChatRoom | null>(null);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    // Text sent but not yet accepted by the server. The input is only cleared once
    // the server echoes it back, so a blocked message can be edited, not retyped.
    const pendingRef = useRef<string | null>(null);
    const userIdRef = useRef<number | null>(null);

    useEffect(() => {
        userIdRef.current = user?.id ?? null;
    }, [user?.id]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        let isMounted = true;

        const fetchInitialData = async () => {
            try {
                // 1. Fetch Room Info to get participant details
                const rooms = await apiFetch<ChatRoom[]>("/chat/rooms");
                const currentRoom = rooms.find(r => r.id === roomId);
                if (!currentRoom) {
                    toast("Chat room not found or unauthorized.", "error");
                    router.push("/inbox");
                    return;
                }
                if (isMounted) setRoomInfo(currentRoom);

                // 2. Fetch Chat History
                const history = await apiFetch<ChatMessage[]>(`/chat/rooms/${roomId}/messages`);
                if (isMounted) setMessages(history);
                // Unmounted while loading (e.g. StrictMode's double effect run):
                // don't open a socket nobody will close.
                if (!isMounted) return;

                // 3. Setup WebSocket
                // API_BASE is e.g. "http://localhost:8000" or empty if proxying
                const baseWsUrl = (API_BASE && API_BASE.startsWith("http"))
                    ? API_BASE.replace(/^http/, "ws")
                    : `ws://${window.location.host}`;

                const wsUrl = `${baseWsUrl}/api/chat/rooms/${roomId}/ws`;
                const websocket = new WebSocket(wsUrl);
                wsRef.current = websocket;

                websocket.onopen = () => {
                    console.log("WebSocket connected");
                };

                websocket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.error) {
                            // Blocked (e.g. contact sharing): keep the text in the input
                            pendingRef.current = null;
                            toast(data.error, "error");
                        } else if (data.id) {
                            // It's a new message
                            if (
                                isMounted &&
                                pendingRef.current !== null &&
                                data.sender_id === userIdRef.current &&
                                data.content === pendingRef.current
                            ) {
                                pendingRef.current = null;
                                // Leave anything typed since sending untouched
                                setInputValue(prev => (prev.trim() === data.content ? "" : prev));
                            }
                            if (isMounted) {
                                setMessages(prev => {
                                    // Prevent duplicates
                                    if (prev.some(m => m.id === data.id)) return prev;
                                    return [...prev, data as ChatMessage];
                                });
                            }
                        }
                    } catch (e) {
                        console.error("Failed to parse WS message", e);
                    }
                };

                websocket.onclose = () => {
                    console.log("WebSocket disconnected");
                };

            } catch (err) {
                console.error(err);
                toast("Failed to load chat", "error");
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchInitialData();

        return () => {
            isMounted = false;
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [roomId, router, toast]);

    const handleSendMessage = (e?: React.FormEvent) => {
        e?.preventDefault();
        const content = inputValue.trim();
        if (!content || !wsRef.current) return;

        // Send via WebSocket; the input clears when the server accepts it (onmessage)
        pendingRef.current = content;
        wsRef.current.send(content);
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-950">
                <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!roomInfo) return null;

    const otherParticipant = roomInfo.participants.find(p => p.user_id !== user?.id);
    const otherProfile = otherParticipant?.user?.profile;

    return (
        <div className="h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            {/* Header */}
            <header className="flex-none w-full z-10 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between max-w-4xl">
                    <div className="flex items-center gap-4">
                        <Link href="/inbox">
                            <Button variant="ghost" size="sm" className="px-2">&larr; Back</Button>
                        </Link>
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-lg">
                                👤
                            </div>
                            <div>
                                <h2 className="font-bold text-gray-900 dark:text-gray-100">
                                    {otherProfile?.display_name || "Unknown"}
                                </h2>
                                <p className="text-xs text-gray-500">
                                    {otherProfile?.city_village || "Unknown Location"}
                                </p>
                            </div>
                        </div>
                    </div>
                    <Link href={`/profile/${otherProfile?.id}`}>
                        <Button variant="outline" size="sm">View Profile</Button>
                    </Link>
                </div>
            </header>

            {/* Chat Messages Area */}
            <main className="flex-1 container mx-auto p-4 max-w-4xl flex flex-col overflow-y-auto">
                {messages.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center text-gray-500">
                        No messages yet. Say hi!
                    </div>
                ) : (
                    <div className="flex-1 space-y-4 pt-4">
                        {messages.map((msg, index) => {
                            const isMine = msg.sender_id === user?.id;
                            const showTime = index === 0 ||
                                new Date(msg.created_at).getTime() - new Date(messages[index - 1].created_at).getTime() > 5 * 60 * 1000;

                            return (
                                <div key={msg.id} className={`flex flex-col ${isMine ? "items-end" : "items-start"}`}>
                                    {showTime && (
                                        <div className="text-xs text-gray-400 mb-2">
                                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    )}
                                    <div
                                        className={`px-4 py-2 max-w-[80%] rounded-2xl ${isMine
                                                ? "bg-primary-600 text-white rounded-tr-sm shadow-md"
                                                : "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm shadow-sm border border-gray-100 dark:border-gray-700"
                                            }`}
                                    >
                                        <p className="whitespace-pre-wrap break-words text-sm">{msg.content}</p>
                                    </div>
                                </div>
                            );
                        })}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </main>

            {/* Input Area */}
            <footer className="flex-none bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 p-4 pb-safe">
                <div className="container mx-auto max-w-4xl">
                    <form onSubmit={handleSendMessage} className="flex gap-2 items-center">
                        <Input
                            value={inputValue}
                            onChange={e => setInputValue(e.target.value)}
                            placeholder="Type a message..."
                            className="flex-1 rounded-full px-4 focus-visible:ring-primary-500"
                            maxLength={4000}
                        />
                        <Button
                            type="submit"
                            disabled={!inputValue.trim()}
                            className="rounded-full w-12 h-12 p-0 flex items-center justify-center bg-primary-600 hover:bg-primary-700 text-white flex-shrink-0"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 ml-1">
                                <path d="M3.478 2.404a.75.75 0 00-.926.941l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.404z" />
                            </svg>
                        </Button>
                    </form>
                    <p className="text-center text-[10px] text-gray-400 mt-2">
                        For your safety, sharing phone numbers and emails via chat is prohibited by our community guidelines.
                    </p>
                </div>
            </footer>
        </div>
    );
}

export default function ChatRoomPage({ params }: { params: Promise<{ roomId: string }> }) {
    const { roomId } = use(params);
    return (
        <ProtectedRoute>
            <ChatRoomInner roomId={Number(roomId)} />
        </ProtectedRoute>
    );
}
