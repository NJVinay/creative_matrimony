"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { TaxonomySelect } from "@/components/ui/TaxonomySelect";

interface Suggestion {
    id: number;
    user_id: number;
    user_submitted_value: string;
    field_name: "religion" | "community" | "subcaste";
    status: string;
    created_at: string;
}

function AdminTaxonomyInner() {
    const { toast } = useToast();
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [loading, setLoading] = useState(true);

    // Track selected target_id for each suggestion row
    const [mappings, setMappings] = useState<Record<number, number | null>>({});
    const [resolving, setResolving] = useState<Record<number, boolean>>({});

    const fetchSuggestions = useCallback(async () => {
        try {
            const data = await apiFetch<Suggestion[]>("/admin/taxonomy/suggestions");
            setSuggestions(data);
        } catch {
            toast("Failed to load suggestions", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchSuggestions();
    }, [fetchSuggestions]);

    const handleResolve = async (id: number, action: "approve" | "reject") => {
        setResolving(prev => ({ ...prev, [id]: true }));
        try {
            const target_id = mappings[id];
            if (action === "approve" && !target_id) {
                toast("Please select a target mapping to approve", "error");
                setResolving(prev => ({ ...prev, [id]: false }));
                return;
            }

            await apiFetch(`/admin/taxonomy/suggestions/${id}/resolve`, {
                method: "POST",
                body: { action, target_id: target_id || null }
            });
            toast(`Suggestion ${action}d successfully`, "success");
            void fetchSuggestions();
        } catch {
            toast("Failed to resolve suggestion", "error");
            setResolving(prev => ({ ...prev, [id]: false }));
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100">Taxonomy Moderation</h1>
                    <p className="text-gray-500">Review and map user-submitted unknown values to canonical categories.</p>
                </div>
                <Link href="/dashboard">
                    <Button variant="outline">Back to Dashboard</Button>
                </Link>
            </header>

            <main className="max-w-6xl mx-auto space-y-6">
                {loading ? (
                    <div className="text-center py-20">Loading queue...</div>
                ) : suggestions.length === 0 ? (
                    <Card className="p-12 text-center text-gray-500">
                        <p className="text-lg">No pending suggestions!</p>
                        <p className="text-sm">The taxonomy moderation queue is clear.</p>
                    </Card>
                ) : (
                    suggestions.map(sug => (
                        <Card key={sug.id} className="p-6 flex flex-col md:flex-row items-start md:items-center gap-6">
                            <div className="flex-1">
                                <div className="text-xs text-primary-600 font-bold uppercase mb-1">{sug.field_name}</div>
                                <div className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                                    &quot;{sug.user_submitted_value}&quot;
                                </div>
                                <div className="text-xs text-gray-500">
                                    Submitted by User ID: {sug.user_id} on {new Date(sug.created_at).toLocaleString()}
                                </div>
                            </div>

                            <div className="flex-1 w-full border-l pl-6 border-gray-200 dark:border-gray-800">
                                <label className="text-sm font-medium block mb-2">Map to existing Canonical Value:</label>
                                <TaxonomySelect
                                    value={{
                                        religion_id: sug.field_name === "religion" ? mappings[sug.id] : undefined,
                                        community_id: sug.field_name === "community" ? mappings[sug.id] : undefined,
                                        subcaste_id: sug.field_name === "subcaste" ? mappings[sug.id] : undefined,
                                    }}
                                    onChange={(next) => {
                                        let target = null;
                                        if (sug.field_name === "religion") target = next.religion_id;
                                        if (sug.field_name === "community") target = next.community_id;
                                        if (sug.field_name === "subcaste") target = next.subcaste_id;
                                        setMappings(prev => ({ ...prev, [sug.id]: target || null }));
                                    }}
                                />
                            </div>

                            <div className="flex flex-col gap-2 w-full md:w-32 flex-shrink-0">
                                <Button
                                    onClick={() => handleResolve(sug.id, "approve")}
                                    isLoading={resolving[sug.id]}
                                    disabled={!mappings[sug.id]}
                                    className="w-full bg-green-600 hover:bg-green-700 text-white"
                                >
                                    Approve Map
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() => handleResolve(sug.id, "reject")}
                                    isLoading={resolving[sug.id]}
                                    className="w-full border-red-200 text-red-600 hover:bg-red-50"
                                >
                                    Reject (Spam)
                                </Button>
                            </div>
                        </Card>
                    ))
                )}
            </main>
        </div>
    );
}

export default function AdminTaxonomyPage() {
    return (
        <ProtectedRoute>
            {/* Note: In a real app we'd also check user role here. ProtectedRoute just checks logged in for MVP. */}
            <AdminTaxonomyInner />
        </ProtectedRoute>
    );
}
