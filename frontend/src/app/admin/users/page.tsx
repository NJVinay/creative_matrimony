"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";

interface UserItem {
    id: number;
    phone: string;
    email: string | null;
    role: string;
    is_banned: boolean;
    created_at: string;
}

function AdminUsersInner() {
    const { toast } = useToast();
    const [users, setUsers] = useState<UserItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState<number | null>(null);

    const fetchUsers = useCallback(async () => {
        try {
            const data = await apiFetch<UserItem[]>("/admin/users?limit=100");
            setUsers(data);
        } catch {
            toast("Failed to load users", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchUsers();
    }, [fetchUsers]);

    const toggleBan = async (id: number, currentBanned: boolean) => {
        setActionId(id);
        const action = currentBanned ? "unban" : "ban";
        try {
            await apiFetch(`/admin/users/${id}/${action}`, { method: "PATCH" });
            toast(`User successfully ${action}ned.`, "success");
            setUsers(users.map(u => u.id === id ? { ...u, is_banned: !currentBanned } : u));
        } catch {
            toast(`Failed to ${action} user`, "error");
        } finally {
            setActionId(null);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100">User Management</h1>
                    <p className="text-gray-500">Ban, unban, and manage platform users.</p>
                </div>
                <Link href="/admin">
                    <Button variant="outline">Back to Admin Hub</Button>
                </Link>
            </header>

            <main className="max-w-6xl mx-auto">
                <Card className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-gray-50 dark:bg-gray-900 border-b">
                                <tr>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">ID</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Phone</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Role</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Joined</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                {loading ? (
                                    <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500">Loading users...</td></tr>
                                ) : users.map(user => (
                                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                                        <td className="px-6 py-4 font-mono text-gray-500">{user.id}</td>
                                        <td className="px-6 py-4 font-bold">{user.phone}</td>
                                        <td className="px-6 py-4 capitalize">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${user.role === 'admin' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                                                }`}>
                                                {user.role}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            {user.is_banned ? (
                                                <span className="text-red-600 font-bold">Banned</span>
                                            ) : (
                                                <span className="text-green-600 font-bold">Active</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                                            {new Date(user.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            {user.role !== 'admin' && (
                                                <Button
                                                    size="sm"
                                                    variant={user.is_banned ? "outline" : "primary"}
                                                    className={!user.is_banned ? "bg-red-600 hover:bg-red-700 text-white border-transparent" : ""}
                                                    onClick={() => toggleBan(user.id, user.is_banned)}
                                                    isLoading={actionId === user.id}
                                                >
                                                    {user.is_banned ? "Unban" : "Ban"}
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </main>
        </div>
    );
}

export default function AdminUsersPage() {
    return (
        <ProtectedRoute>
            <AdminUsersInner />
        </ProtectedRoute>
    );
}
