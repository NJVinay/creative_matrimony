"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, staticUrl } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import Image from "next/image";

interface ProfilePhoto {
    id: number;
    storage_key: string;
    is_primary: boolean;
    created_at: string;
}

function AdminPhotosInner() {
    const { toast } = useToast();
    const [photos, setPhotos] = useState<ProfilePhoto[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState<number | null>(null);

    const fetchPhotos = useCallback(async () => {
        try {
            const data = await apiFetch<ProfilePhoto[]>("/admin/photos/pending");
            setPhotos(data);
        } catch {
            toast("Failed to load pending photos", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchPhotos();
    }, [fetchPhotos]);

    const handleAction = async (id: number, action: "approve" | "reject") => {
        setActionId(id);
        try {
            await apiFetch(`/admin/photos/${id}/${action}`, { method: "PATCH" });
            toast(`Photo ${action}d successfully.`, "success");
            setPhotos(photos.filter(p => p.id !== id));
        } catch {
            toast(`Failed to ${action} photo`, "error");
        } finally {
            setActionId(null);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
            <header className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100">Photo Moderation</h1>
                    <p className="text-gray-500">Review pending user uploads for inappropriate content.</p>
                </div>
                <Link href="/admin">
                    <Button variant="outline">Back to Admin Hub</Button>
                </Link>
            </header>

            <main className="max-w-7xl mx-auto">
                {loading ? (
                    <div className="text-center py-12 text-gray-500">Loading pending photos...</div>
                ) : photos.length === 0 ? (
                    <Card className="p-12 text-center text-gray-500 border-dashed">
                        <div className="text-4xl mb-4">✨</div>
                        <h3 className="text-xl font-bold mb-2">All Caught Up!</h3>
                        <p>There are no pending photos in the moderation queue.</p>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {photos.map(photo => (
                            <Card key={photo.id} className="overflow-hidden flex flex-col">
                                <div className="relative aspect-[3/4] bg-gray-100 dark:bg-gray-800">
                                    <Image
                                        src={staticUrl(photo.storage_key)}
                                        alt="Pending Photo"
                                        fill
                                        className="object-cover"
                                        unoptimized
                                    />
                                    {photo.is_primary && (
                                        <div className="absolute top-2 right-2 bg-yellow-500 text-white text-xs font-bold px-2 py-1 rounded">
                                            PRIMARY
                                        </div>
                                    )}
                                </div>
                                <div className="p-4 flex gap-2">
                                    <Button
                                        className="flex-1 bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400"
                                        onClick={() => handleAction(photo.id, "reject")}
                                        isLoading={actionId === photo.id}
                                    >
                                        Reject
                                    </Button>
                                    <Button
                                        className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                                        onClick={() => handleAction(photo.id, "approve")}
                                        isLoading={actionId === photo.id}
                                    >
                                        Approve
                                    </Button>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

export default function AdminPhotosPage() {
    return (
        <ProtectedRoute>
            <AdminPhotosInner />
        </ProtectedRoute>
    );
}
