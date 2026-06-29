"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";

interface ReportItem {
    id: number;
    reporter_id: number;
    target_user_id: number;
    reason: string;
    evidence_text: string | null;
    status: string;
    created_at: string;
}

function AdminReportsInner() {
    const { toast } = useToast();
    const [reports, setReports] = useState<ReportItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState<number | null>(null);

    const fetchReports = useCallback(async () => {
        try {
            const data = await apiFetch<ReportItem[]>("/admin/reports");
            setReports(data);
        } catch {
            toast("Failed to load reports", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchReports();
    }, [fetchReports]);

    const resolveReport = async (id: number) => {
        setActionId(id);
        try {
            await apiFetch(`/admin/reports/${id}/resolve`, { method: "PATCH" });
            toast(`Report marked as resolved.`, "success");
            setReports(reports.map(r => r.id === id ? { ...r, status: "resolved" } : r));
        } catch {
            toast(`Failed to resolve report`, "error");
        } finally {
            setActionId(null);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100">Reports Moderation</h1>
                    <p className="text-gray-500">Handle user-submitted reports for abuse or spam.</p>
                </div>
                <Link href="/admin">
                    <Button variant="outline">Back to Admin Hub</Button>
                </Link>
            </header>

            <main className="max-w-7xl mx-auto">
                <Card className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-gray-50 dark:bg-gray-900 border-b">
                                <tr>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">ID</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Reporter</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100 text-red-600">Target User</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Reason</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100 w-1/4">Evidence</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Date</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Status</th>
                                    <th className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                {loading ? (
                                    <tr><td colSpan={8} className="px-6 py-12 text-center text-gray-500">Loading reports...</td></tr>
                                ) : reports.length === 0 ? (
                                    <tr><td colSpan={8} className="px-6 py-12 text-center text-gray-500">No reports found.</td></tr>
                                ) : reports.map(report => (
                                    <tr key={report.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                                        <td className="px-6 py-4 font-mono text-gray-500">{report.id}</td>
                                        <td className="px-6 py-4 font-bold text-blue-600">
                                            User {report.reporter_id}
                                        </td>
                                        <td className="px-6 py-4 font-bold text-red-600 hover:underline cursor-pointer">
                                            <Link href={`/profile/${report.target_user_id}`}>
                                                User {report.target_user_id}
                                            </Link>
                                        </td>
                                        <td className="px-6 py-4 capitalize font-semibold">
                                            {report.reason.replace('_', ' ')}
                                        </td>
                                        <td className="px-6 py-4 text-gray-600 dark:text-gray-400 italic">
                                            {report.evidence_text || "No evidence provided."}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                                            {new Date(report.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            {report.status === 'resolved' ? (
                                                <span className="text-green-600 font-bold">Resolved</span>
                                            ) : (
                                                <span className="text-amber-600 font-bold">Pending</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            {report.status !== 'resolved' && (
                                                <Button
                                                    size="sm"
                                                    onClick={() => resolveReport(report.id)}
                                                    isLoading={actionId === report.id}
                                                >
                                                    Resolve
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

export default function AdminReportsPage() {
    return (
        <ProtectedRoute>
            <AdminReportsInner />
        </ProtectedRoute>
    );
}
