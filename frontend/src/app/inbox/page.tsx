"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { useAuth } from "@/lib/useAuth";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface ProfileSnippet {
    display_name: string;
    age?: number;
    city_village?: string | null;
    state?: string | null;
}
import { ProfilePublicOut } from "@/components/matches/MatchCard";

// Schemas
interface Interest {
    id: number;
    sender: ProfileSnippet;
    receiver: ProfileSnippet;
    status: "pending" | "accepted" | "rejected";
    created_at: string;
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

type Tab = "received" | "sent" | "chats";

function InboxInner() {
    const { toast } = useToast();
    const { user } = useAuth();
    const router = useRouter();

    const [tab, setTab] = useState<Tab>("received");
    const [received, setReceived] = useState<Interest[]>([]);
    const [sent, setSent] = useState<Interest[]>([]);
    const [chats, setChats] = useState<ChatRoom[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            if (tab === "received") {
                const data = await apiFetch<Interest[]>("/interests/received");
                setReceived(data);
            } else if (tab === "sent") {
                const data = await apiFetch<Interest[]>("/interests/sent");
                setSent(data);
            } else if (tab === "chats") {
                const data = await apiFetch<ChatRoom[]>("/chat/rooms");
                setChats(data);
            }
        } catch (err) {
            console.error(err);
            toast("Failed to load data", "error");
        } finally {
            setLoading(false);
        }
    }, [tab, toast]);

    useEffect(() => {
        void fetchData();
    }, [fetchData]);

    const handleAction = async (id: number, action: "accept" | "reject") => {
        try {
            await apiFetch(`/interests/${id}/${action}`, { method: "PUT" });
            toast(`Interest ${action}ed!`, "success");
            // Refresh list
            void fetchData();
        } catch (err) {
            console.error(err);
            toast("Failed to update interest", "error");
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            <header className="sticky top-0 w-full z-10 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/dashboard" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-4">
                        <Link href="/dashboard" className="text-sm font-medium hover:text-primary-600">Dashboard</Link>
                        <LanguageToggle />
                        <ThemeToggle />
                        <NotificationBell />
                    </div>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
                <h1 className="text-3xl font-serif font-bold mb-8 text-gray-900 dark:text-gray-100">Inbox</h1>

                {/* Tabs */}
                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-800 overflow-x-auto">
                    {(["received", "sent", "chats"] as Tab[]).map(t => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${tab === t
                                ? "border-primary-600 text-primary-600"
                                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                                }`}
                        >
                            {t === "received" && "Received Interests"}
                            {t === "sent" && "Sent Interests"}
                            {t === "chats" && "Active Chats"}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {/* Received Interests */}
                        {tab === "received" && (
                            received.length === 0 ? (
                                <Card className="p-8 text-center text-gray-500">
                                    No pending received interests.
                                </Card>
                            ) : (
                                received.map(interest => (
                                    <Card key={interest.id} className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:shadow-md transition-shadow">
                                        <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-2xl flex-shrink-0">
                                            👤
                                        </div>
                                        <div className="flex-1 text-center sm:text-left">
                                            <h3 className="font-bold text-lg">{interest.sender.display_name}</h3>
                                            <p className="text-sm text-gray-500">
                                                {interest.sender.age} yrs · {interest.sender.city_village}, {interest.sender.state}
                                            </p>
                                            <p className="text-xs text-gray-400 mt-1">
                                                Received on {new Date(interest.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                        {interest.status === "pending" ? (
                                            <div className="flex gap-2 w-full sm:w-auto">
                                                <Button variant="outline" className="flex-1 border-red-200 text-red-600 hover:bg-red-50" onClick={() => handleAction(interest.id, "reject")}>
                                                    Decline
                                                </Button>
                                                <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={() => handleAction(interest.id, "accept")}>
                                                    Accept
                                                </Button>
                                            </div>
                                        ) : (
                                            <div className="px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-md text-sm font-medium capitalize text-gray-500">
                                                {interest.status}
                                            </div>
                                        )}
                                    </Card>
                                ))
                            )
                        )}

                        {/* Sent Interests */}
                        {tab === "sent" && (
                            sent.length === 0 ? (
                                <Card className="p-8 text-center text-gray-500">
                                    You haven&apos;t sent any interests yet.
                                </Card>
                            ) : (
                                sent.map(interest => (
                                    <Card key={interest.id} className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:shadow-md transition-shadow">
                                        <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-2xl flex-shrink-0">
                                            👤
                                        </div>
                                        <div className="flex-1 text-center sm:text-left">
                                            <h3 className="font-bold text-lg">{interest.receiver.display_name}</h3>
                                            <p className="text-sm text-gray-500">
                                                {interest.receiver.age} yrs · {interest.receiver.city_village}, {interest.receiver.state}
                                            </p>
                                            <p className="text-xs text-gray-400 mt-1">
                                                Sent on {new Date(interest.created_at).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <div className={`px-4 py-2 rounded-md text-sm font-medium capitalize ${interest.status === "accepted" ? "bg-green-100 text-green-700" :
                                            interest.status === "rejected" ? "bg-red-100 text-red-700" :
                                                "bg-yellow-100 text-yellow-700"
                                            }`}>
                                            {interest.status}
                                        </div>
                                    </Card>
                                ))
                            )
                        )}

                        {/* Active Chats */}
                        {tab === "chats" && (
                            chats.length === 0 ? (
                                <Card className="p-8 text-center text-gray-500">
                                    No active chats yet. Accept an interest to start chatting!
                                </Card>
                            ) : (
                                chats.map(chat => {
                                    // Find the other participant
                                    const otherParticipant = chat.participants.find(p => p.user_id !== user?.id);
                                    const otherProfile = otherParticipant?.user?.profile;

                                    return (
                                        <Card key={chat.id} className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => router.push(`/chat/${chat.id}`)}>
                                            <div className="w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-2xl flex-shrink-0 relative overflow-hidden">
                                                {/* Add photo fetching logic later, fallback to emoji */}
                                                <span>👤</span>
                                            </div>
                                            <div className="flex-1 text-center sm:text-left">
                                                <h3 className="font-bold text-lg text-gray-900 dark:text-gray-100">
                                                    {otherProfile?.display_name || "Unknown User"}
                                                </h3>
                                                <p className="text-sm text-gray-500 truncate max-w-sm">
                                                    Tap to open chat...
                                                </p>
                                            </div>
                                            <Button variant="outline">
                                                Open Chat
                                            </Button>
                                        </Card>
                                    );
                                })
                            )
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

export default function InboxPage() {
    return (
        <ProtectedRoute>
            <InboxInner />
        </ProtectedRoute>
    );
}
