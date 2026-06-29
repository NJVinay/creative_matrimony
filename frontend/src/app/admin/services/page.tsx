"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import Link from "next/link";

interface Inquiry {
    id: number;
    user_id: number;
    category: string;
    message: string;
    is_resolved: boolean;
    created_at: string;
}

function AdminServicesInner() {
    const { toast } = useToast();
    const [inquiries, setInquiries] = useState<Inquiry[]>([]);
    const [loading, setLoading] = useState(true);
    const [resolvingId, setResolvingId] = useState<number | null>(null);

    const fetchInquiries = useCallback(async () => {
        try {
            const data = await apiFetch<Inquiry[]>("/expert/admin/all");
            setInquiries(data);
        } catch {
            toast("Failed to load expert inquiries", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchInquiries();
    }, [fetchInquiries]);

    const handleResolve = async (id: number) => {
        setResolvingId(id);
        try {
            await apiFetch(`/expert/admin/${id}/resolve`, { method: "PATCH" });
            toast("Inquiry marked as resolved", "success");
            setInquiries(inquiries.map(i => i.id === id ? { ...i, is_resolved: true } : i));
        } catch {
            toast("Failed to resolve", "error");
        } finally {
            setResolvingId(null);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100">Expert Services Queue</h1>
                    <p className="text-gray-500">Manage VIP Matchmaking, Astrology, and Profile Writing requests.</p>
                </div>
                <Link href="/dashboard">
                    <Button variant="outline">Back to Dashboard</Button>
                </Link>
            </header>

            <main className="max-w-6xl mx-auto">
                <Card className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-gray-50 dark:bg-gray-900 border-b">
                                <tr>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">ID</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">User ID</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Category</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100 w-1/3">Message</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Date</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                {loading ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                            Loading queue...
                                        </td>
                                    </tr>
                                ) : inquiries.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                                            No expert service inquiries found.
                                        </td>
                                    </tr>
                                ) : (
                                    inquiries.map(inq => (
                                        <tr key={inq.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                                            <td className="px-6 py-4 font-mono">{inq.id}</td>
                                            <td className="px-6 py-4 font-medium">
                                                <Link href={`/profile/${inq.user_id}`} className="text-primary-600 hover:underline">
                                                    User {inq.user_id}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 capitalize">
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${inq.category === 'astrology' ? 'bg-purple-100 text-purple-700' :
                                                        inq.category === 'matchmaking' ? 'bg-amber-100 text-amber-700' :
                                                            'bg-blue-100 text-blue-700'
                                                    }`}>
                                                    {inq.category.replace('_', ' ')}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-gray-600 dark:text-gray-400">
                                                <div className="line-clamp-2" title={inq.message}>{inq.message}</div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {new Date(inq.created_at).toLocaleDateString()}
                                            </td>
                                            <td className="px-6 py-4">
                                                {inq.is_resolved ? (
                                                    <span className="text-green-600 font-medium">Resolved</span>
                                                ) : (
                                                    <span className="text-amber-600 font-medium">Pending</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                {!inq.is_resolved && (
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleResolve(inq.id)}
                                                        isLoading={resolvingId === inq.id}
                                                    >
                                                        Mark Resolved
                                                    </Button>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </main>
        </div>
    );
}

export default function AdminServicesPage() {
    return (
        <ProtectedRoute>
            <AdminServicesInner />
        </ProtectedRoute>
    );
}
