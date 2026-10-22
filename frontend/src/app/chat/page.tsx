"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { NotificationBell } from "@/components/ui/NotificationBell";
import Link from "next/link";

interface ProfileSnippet {
    display_name: string;
    age?: number;
    city_village?: string | null;
    state?: string | null;
}

// Types
interface ChatRoom {
    id: number;
    participants: { user_id: number }[];
    // To display name/photo, we need to fetch profile or include it in API.
    // MVP: Show "Chat #{id}" or basic info.
}

interface Interest {
    id: number;
    sender: ProfileSnippet;
    receiver: ProfileSnippet;
    status: string;
    created_at: string;
}

export default function ChatPage() {
    const [activeTab, setActiveTab] = useState<"messages" | "interests">("messages");

    // Data
    const [chats, setChats] = useState<ChatRoom[]>([]);
    const [receivedInterests, setReceivedInterests] = useState<Interest[]>([]);
    const [sentInterests, setSentInterests] = useState<Interest[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchData = async () => {
        setIsLoading(true);
        try {
            const [resChats, resReceived, resSent] = await Promise.all([
                apiFetch<ChatRoom[]>("/chat/rooms"),
                apiFetch<Interest[]>("/interests/received"),
                apiFetch<Interest[]>("/interests/sent"),
            ]);
            setChats(resChats);
            setReceivedInterests(resReceived);
            setSentInterests(resSent);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleInterestAction = async (id: number, action: "accept" | "reject") => {
        try {
            await apiFetch(`/interests/${id}/${action}`, { method: "PUT" });
            fetchData(); // Refresh to move to chats if accepted
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            {/* Header */}
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

            <main className="container mx-auto px-4 py-8 flex-1 max-w-4xl">
                <h1 className="text-3xl font-serif font-bold mb-6">Messages & Interests</h1>

                {/* Tabs */}
                <div className="flex border-b border-gray-200 dark:border-gray-800 mb-6">
                    <button
                        className={`px-6 py-3 font-medium text-sm transition-colors ${activeTab === "messages" ? "border-b-2 border-primary-600 dark:border-primary-400 text-primary-600" : "text-gray-500 hover:text-gray-700"}`}
                        onClick={() => setActiveTab("messages")}
                    >
                        Messages
                    </button>
                    <button
                        className={`px-6 py-3 font-medium text-sm transition-colors ${activeTab === "interests" ? "border-b-2 border-primary-600 dark:border-primary-400 text-primary-600" : "text-gray-500 hover:text-gray-700"}`}
                        onClick={() => setActiveTab("interests")}
                    >
                        Interests
                        {receivedInterests.filter(i => i.status === "pending").length > 0 && (
                            <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                                {receivedInterests.filter(i => i.status === "pending").length}
                            </span>
                        )}
                    </button>
                </div>

                {isLoading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {activeTab === "messages" && (
                            <div className="space-y-4">
                                {chats.length === 0 ? (
                                    <div className="text-center py-10 text-gray-500">
                                        No active chats. Check your interests tab!
                                    </div>
                                ) : (
                                    chats.map(chat => (
                                        <Link key={chat.id} href={`/chat/${chat.id}`}>
                                            <Card className="p-4 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer flex justify-between items-center bg-white dark:bg-gray-800">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center text-xl">
                                                        💬
                                                    </div>
                                                    <div>
                                                        <h3 className="font-bold">Chat Room #{chat.id}</h3>
                                                        <p className="text-sm text-gray-500">Click to open conversation</p>
                                                    </div>
                                                </div>
                                                <div className="text-gray-400 text-xl">›</div>
                                            </Card>
                                        </Link>
                                    ))
                                )}
                            </div>
                        )}

                        {activeTab === "interests" && (
                            <div className="space-y-8">
                                {/* Received */}
                                <div>
                                    <h3 className="font-bold text-lg mb-4">Received Requests</h3>
                                    {receivedInterests.length === 0 ? (
                                        <p className="text-gray-500 text-sm italic">No requests received yet.</p>
                                    ) : (
                                        <div className="space-y-3">
                                            {receivedInterests.map(interest => (
                                                <Card key={interest.id} className="p-4 flex flex-col sm:flex-row justify-between items-center gap-4 bg-white dark:bg-gray-800">
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                                                            👤
                                                        </div>
                                                        <div>
                                                            <p className="font-medium">Interest from <span className="font-bold">{interest.sender?.display_name || "User"}</span></p>
                                                            <p className="text-xs text-gray-500">{new Date(interest.created_at).toLocaleDateString()}</p>
                                                        </div>
                                                    </div>
                                                    {interest.status === "pending" ? (
                                                        <div className="flex gap-2">
                                                            <Button size="sm" variant="outline" onClick={() => handleInterestAction(interest.id, "reject")}>Reject</Button>
                                                            <Button size="sm" onClick={() => handleInterestAction(interest.id, "accept")}>Accept</Button>
                                                        </div>
                                                    ) : (
                                                        <span className={`text-sm font-bold ${interest.status === "accepted" ? "text-green-600" : "text-red-600"}`}>
                                                            {interest.status.toUpperCase()}
                                                        </span>
                                                    )}
                                                </Card>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* Sent */}
                                <div>
                                    <h3 className="font-bold text-lg mb-4">Sent Requests</h3>
                                    {sentInterests.length === 0 ? (
                                        <p className="text-gray-500 text-sm italic">You haven&apos;t sent any requests.</p>
                                    ) : (
                                        <div className="space-y-3">
                                            {sentInterests.map(interest => (
                                                <Card key={interest.id} className="p-4 flex justify-between items-center opacity-80 bg-gray-50 dark:bg-gray-900">
                                                    <div>
                                                        <p className="font-medium text-sm">Sent to <span className="font-bold">{interest.receiver?.display_name || "User"}</span></p>
                                                        <p className="text-xs text-gray-500">{new Date(interest.created_at).toLocaleDateString()}</p>
                                                    </div>
                                                    <span className={`text-xs font-bold px-2 py-1 rounded bg-gray-200 dark:bg-gray-800`}>
                                                        {interest.status.toUpperCase()}
                                                    </span>
                                                </Card>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
