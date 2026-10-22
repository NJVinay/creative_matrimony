"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch, staticUrl } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { useToast } from "@/components/ui/Toast";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image from "next/image";

// Types
interface Profile {
    id: number;
    display_name: string;
    age: number;
    city_village: string;
    state: string;
    education_level?: string;
    occupation_category?: string;
    marital_status: string;
    community?: { id: number; name: string };
    photo_blur_until_mutual?: boolean;
    // Resolved for this viewer by the API: the photo URL only when they may
    // see it; photo_locked only while blur-until-mutual still applies to them
    profile_photo?: { url: string } | null;
    photo_locked?: boolean;
}
interface Recommendation {
    profile: Profile;
    score: number;
    reasons: string[];
}

export default function MatchesPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [matches, setMatches] = useState<Recommendation[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchMatches = useCallback(async () => {
        try {
            const data = await apiFetch<Recommendation[]>("/matches/recommendations");
            setMatches(data);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const sendInterest = async (profileId: number) => {
        try {
            await apiFetch(`/interests/${profileId}`, { method: "POST" });
            toast("Interest sent!", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to send interest";
            toast(msg, "error");
        }
    };

    useEffect(() => {
        void fetchMatches();
    }, [fetchMatches]);

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

            <main className="container mx-auto px-4 py-8 flex-1">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-white">Daily Matches</h1>
                        <p className="text-gray-500">Based on your preferences</p>
                    </div>
                    <Button variant="outline" onClick={() => router.push("/profile/preferences")}>
                        Edit Preferences
                    </Button>
                </div>

                {isLoading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
                    </div>
                ) : matches.length === 0 ? (
                    <Card className="text-center py-20">
                        <p className="text-gray-500 text-lg mb-4">No matches found based on your current preferences.</p>
                        <Button variant="outline">Update Preferences</Button>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {matches.map(({ profile, score, reasons }) => (
                            <Card key={profile.id} className="overflow-hidden hover:shadow-xl transition-shadow flex flex-col relative">
                                {/* Match Score Badge */}
                                <div className="absolute top-4 right-4 z-10 bg-white/90 dark:bg-black/80 backdrop-blur px-3 py-1 rounded-full shadow-sm border border-primary-100 dark:border-primary-800">
                                    <span className="text-sm font-bold text-primary-600">{score}% Match</span>
                                </div>

                                <div className="aspect-[4/5] bg-gray-200 relative">
                                    {profile.profile_photo?.url ? (
                                        <div className="w-full h-full relative">
                                            <Image
                                                src={staticUrl(profile.profile_photo.url)}
                                                alt={profile.display_name}
                                                fill
                                                sizes="(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw"
                                                className="object-cover"
                                            />
                                        </div>
                                    ) : profile.photo_locked ? (
                                        <div className="w-full h-full flex flex-col items-center justify-center gap-2 px-6 text-center bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                                            <span className="text-4xl" aria-hidden>🔒</span>
                                            <span className="text-sm font-medium">Photos visible after mutual interest</span>
                                        </div>
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-4xl bg-gray-100 dark:bg-gray-800">
                                            👤
                                        </div>
                                    )}
                                    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-4 text-white">
                                        <h3 className="font-bold text-xl">{profile.display_name}, {profile.age}</h3>
                                        <p className="text-sm opacity-90">{profile.city_village}, {profile.state}</p>
                                    </div>
                                </div>

                                <div className="p-4 space-y-3 flex-1 flex flex-col">
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <div>
                                            <span className="text-gray-500 block text-xs">Education</span>
                                            <span className="font-medium">{profile.education_level || "-"}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 block text-xs">Community</span>
                                            <span className="font-medium">{profile.community?.name || "-"}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 block text-xs">Profession</span>
                                            <span className="font-medium">{profile.occupation_category || "-"}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 block text-xs">Status</span>
                                            <span className="font-medium">{profile.marital_status}</span>
                                        </div>
                                    </div>

                                    {/* Match Reasons */}
                                    {reasons && reasons.length > 0 && (
                                        <div className="mt-2 text-xs space-y-1 bg-green-50 dark:bg-green-900/10 p-2 rounded-md border border-green-100 dark:border-green-800">
                                            {reasons.slice(0, 3).map((r, idx) => (
                                                <div key={idx} className="flex items-start gap-1.5 text-green-700 dark:text-green-400">
                                                    <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                    </svg>
                                                    <span>{r}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className="pt-2 flex gap-2 mt-auto">
                                        <Link href={`/profile/${profile.id}`} className="flex-1">
                                            <Button variant="outline" className="w-full">View Profile</Button>
                                        </Link>
                                        <Button className="flex-1" onClick={() => sendInterest(profile.id)}>
                                            Send Interest
                                        </Button>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
