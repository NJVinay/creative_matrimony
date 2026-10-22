"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, staticUrl } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useToast } from "@/components/ui/Toast";
import { AuthGuard } from "@/components/ui/AuthGuard";
import Image from "next/image";

interface Stats {
    total_users: number;
    active_subscriptions: number;
    pending_verifications: number;
}

interface User {
    id: number;
    phone: string;
    role: string;
    is_banned: boolean;
    created_at: string;
}

interface PendingPhoto {
    id: number;
    profile_id: number;
    storage_key: string;
    is_primary: boolean;
    created_at: string;
}

type Tab = "users" | "photos";

function AdminInner() {
    const router = useRouter();
    const { toast } = useToast();
    const [tab, setTab] = useState<Tab>("users");
    const [stats, setStats] = useState<Stats | null>(null);
    const [users, setUsers] = useState<User[]>([]);
    const [pendingPhotos, setPendingPhotos] = useState<PendingPhoto[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchAdminData = useCallback(async () => {
        setIsLoading(true);
        try {
            const statsData = await apiFetch<Stats>("/admin/stats");
            const usersData = await apiFetch<User[]>("/admin/users");
            setStats(statsData);
            setUsers(usersData);
        } catch (err) {
            const status = (err as { status?: number })?.status;
            if (status === 403) {
                toast("Access denied: admin only", "error");
                router.push("/dashboard");
                return;
            }
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [router, toast]);

    const fetchPendingPhotos = async () => {
        try {
            const list = await apiFetch<PendingPhoto[]>("/admin/photos/pending");
            setPendingPhotos(list);
        } catch (err) {
            console.error("Failed to load pending photos:", err);
        }
    };

    useEffect(() => {
        void fetchAdminData();
    }, [fetchAdminData]);

    useEffect(() => {
        if (tab === "photos") {
            fetchPendingPhotos();
        }
    }, [tab]);

    const toggleBan = async (user: User) => {
        if (!window.confirm(`Are you sure you want to ${user.is_banned ? "unban" : "ban"} user ${user.phone}?`)) return;

        try {
            const action = user.is_banned ? "unban" : "ban";
            await apiFetch(`/admin/users/${user.id}/${action}`, { method: "PATCH" });
            setUsers(users.map(u => u.id === user.id ? { ...u, is_banned: !u.is_banned } : u));
            toast(`User ${action}ned`, "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Action failed";
            toast(msg, "error");
        }
    };

    const handleApprove = async (photo: PendingPhoto) => {
        try {
            await apiFetch(`/admin/photos/${photo.id}/approve`, { method: "PATCH" });
            setPendingPhotos(pendingPhotos.filter(p => p.id !== photo.id));
            toast("Photo approved", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to approve";
            toast(msg, "error");
        }
    };

    const handleReject = async (photo: PendingPhoto) => {
        const reason = window.prompt("Reason for rejection (optional):") || "";
        try {
            await apiFetch(`/admin/photos/${photo.id}/reject?reason=${encodeURIComponent(reason)}`, { method: "PATCH" });
            setPendingPhotos(pendingPhotos.filter(p => p.id !== photo.id));
            toast("Photo rejected", "info");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to reject";
            toast(msg, "error");
        }
    };

    if (isLoading) return <div className="p-10 text-center">Loading Admin...</div>;

    return (
        <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
            <header className="bg-white dark:bg-gray-800 shadow p-4 flex justify-between items-center">
                <h1 className="text-xl font-bold text-red-600">Admin Dashboard</h1>
                <div className="flex gap-4">
                    <ThemeToggle />
                    <Link href="/dashboard"><Button variant="ghost">Exit</Button></Link>
                </div>
            </header>

            <main className="container mx-auto p-6 space-y-6">
                {/* KPI Cards */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <Card className="p-6">
                            <h3 className="text-gray-500 text-sm uppercase">Total Users</h3>
                            <p className="text-3xl font-bold">{stats.total_users}</p>
                        </Card>
                        <Card className="p-6">
                            <h3 className="text-gray-500 text-sm uppercase">Active Subscribers</h3>
                            <p className="text-3xl font-bold text-green-600">{stats.active_subscriptions}</p>
                        </Card>
                        <Card className="p-6">
                            <h3 className="text-gray-500 text-sm uppercase">Pending Verifications</h3>
                            <p className="text-3xl font-bold text-orange-500">{stats.pending_verifications}</p>
                        </Card>
                    </div>
                )}

                {/* Tabs */}
                <div className="flex gap-2 border-b border-gray-200 dark:border-gray-800">
                    <button
                        onClick={() => setTab("users")}
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "users"
                                ? "border-primary-600 dark:border-primary-400 text-primary-600"
                                : "border-transparent text-gray-500"
                            }`}
                    >
                        Users
                    </button>
                    <button
                        onClick={() => setTab("photos")}
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "photos"
                                ? "border-primary-600 dark:border-primary-400 text-primary-600"
                                : "border-transparent text-gray-500"
                            }`}
                    >
                        Pending Photos {pendingPhotos.length > 0 && `(${pendingPhotos.length})`}
                    </button>
                </div>

                {/* User Table */}
                {tab === "users" && (
                    <Card className="p-4 overflow-hidden">
                        <h2 className="text-lg font-bold mb-4">User Management</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-gray-50 dark:bg-gray-800 text-gray-400">
                                    <tr>
                                        <th className="p-3">ID</th>
                                        <th className="p-3">Phone</th>
                                        <th className="p-3">Role</th>
                                        <th className="p-3">Created</th>
                                        <th className="p-3">Status</th>
                                        <th className="p-3">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                    {users.map(u => (
                                        <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                            <td className="p-3">#{u.id}</td>
                                            <td className="p-3 font-mono">{u.phone}</td>
                                            <td className="p-3">
                                                <span className={`px-2 py-1 rounded-full text-xs ${u.role === 'admin' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
                                                    {u.role}
                                                </span>
                                            </td>
                                            <td className="p-3">{new Date(u.created_at).toLocaleDateString()}</td>
                                            <td className="p-3">
                                                {u.is_banned ? (
                                                    <span className="text-red-600 font-bold">BANNED</span>
                                                ) : (
                                                    <span className="text-green-600">Active</span>
                                                )}
                                            </td>
                                            <td className="p-3">
                                                <Button
                                                    size="sm"
                                                    variant={u.is_banned ? "primary" : "danger"}
                                                    onClick={() => toggleBan(u)}
                                                    disabled={u.role === 'admin'}
                                                >
                                                    {u.is_banned ? "Unban" : "Ban"}
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                )}

                {/* Photo Moderation Queue */}
                {tab === "photos" && (
                    <Card className="p-4">
                        <h2 className="text-lg font-bold mb-4">Pending Photo Moderation</h2>
                        {pendingPhotos.length === 0 ? (
                            <div className="text-center text-gray-500 py-12">
                                No photos pending review. ✓
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {pendingPhotos.map(photo => (
                                    <div key={photo.id} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                                        <div className="aspect-square relative bg-gray-100">
                                            <Image
                                                src={staticUrl(photo.storage_key)}
                                                alt="Pending"
                                                fill
                                                className="object-cover"
                                            />
                                        </div>
                                        <div className="p-2 space-y-1">
                                            <div className="text-xs text-gray-500">
                                                Photo #{photo.id} · Profile #{photo.profile_id}
                                            </div>
                                            <div className="flex gap-1">
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleApprove(photo)}
                                                    className="flex-1"
                                                >
                                                    Approve
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="danger"
                                                    onClick={() => handleReject(photo)}
                                                    className="flex-1"
                                                >
                                                    Reject
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                )}
            </main>
        </div>
    );
}

export default function AdminPage() {
    return (
        <AuthGuard>
            <AdminInner />
        </AuthGuard>
    );
}
