"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { Button } from "@/components/ui/Button";

interface AdminStats {
    total_users: number;
    active_subscriptions: number;
    pending_verifications: number;
}

function AdminDashboardInner() {
    const { toast } = useToast();
    const [stats, setStats] = useState<AdminStats | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = useCallback(async () => {
        try {
            const data = await apiFetch<AdminStats>("/admin/stats");
            setStats(data);
        } catch {
            toast("Failed to load admin stats", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchStats();
    }, [fetchStats]);

    const adminLinks = [
        { href: "/admin/users", title: "User Management", desc: "Ban, unban, and override phone numbers.", icon: "👥" },
        { href: "/admin/photos", title: "Photo Moderation", desc: "Review and approve/reject profile photos.", icon: "📸" },
        { href: "/admin/reports", title: "Reports Queue", desc: "Handle user-submitted reports and abuse.", icon: "🚩" },
        { href: "/admin/taxonomy", title: "Taxonomy (Tags)", desc: "Manage caste/community tag synonyms.", icon: "🏷️" },
        { href: "/admin/services", title: "Expert Services", desc: "Manage VIP matchmaking and astrology requests.", icon: "👑" },
    ];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            <header className="sticky top-0 w-full z-10 glass border-b border-white/20 bg-white/80 dark:bg-black/80">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Link href="/admin" className="text-2xl font-serif font-bold text-red-700 dark:text-red-500">
                            Admin Central
                        </Link>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link href="/dashboard">
                            <Button variant="outline" size="sm">Exit Admin</Button>
                        </Link>
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8 max-w-6xl flex-1">
                <h1 className="text-3xl font-bold mb-8">Platform Overview</h1>

                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                    <Card className="p-6 border-blue-200 bg-blue-50 dark:bg-blue-900/10 dark:border-blue-800">
                        <h3 className="text-gray-500 font-medium mb-2">Total Users</h3>
                        <div className="text-4xl font-bold text-blue-700 dark:text-blue-400">
                            {loading ? "..." : stats?.total_users}
                        </div>
                    </Card>
                    <Card className="p-6 border-green-200 bg-green-50 dark:bg-green-900/10 dark:border-green-800">
                        <h3 className="text-gray-500 font-medium mb-2">Active Subscriptions</h3>
                        <div className="text-4xl font-bold text-green-700 dark:text-green-400">
                            {loading ? "..." : stats?.active_subscriptions}
                        </div>
                    </Card>
                    <Card className="p-6 border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-800">
                        <h3 className="text-gray-500 font-medium mb-2">Pending Photo Moderation</h3>
                        <div className="text-4xl font-bold text-amber-700 dark:text-amber-400">
                            {loading ? "..." : stats?.pending_verifications}
                        </div>
                    </Card>
                </div>

                {/* Navigation Links */}
                <h2 className="text-2xl font-bold mb-6">Moderation Tools</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {adminLinks.map(link => (
                        <Link href={link.href} key={link.href}>
                            <Card className="p-6 hover:shadow-xl transition-shadow cursor-pointer h-full border-transparent hover:border-red-200 dark:hover:border-red-800">
                                <div className="text-4xl mb-4">{link.icon}</div>
                                <h3 className="text-xl font-bold mb-2">{link.title}</h3>
                                <p className="text-gray-600 dark:text-gray-400">{link.desc}</p>
                            </Card>
                        </Link>
                    ))}
                </div>
            </main>
        </div>
    );
}

export default function AdminDashboardPage() {
    return (
        <ProtectedRoute>
            <AdminDashboardInner />
        </ProtectedRoute>
    );
}
