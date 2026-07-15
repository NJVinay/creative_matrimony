"use client";

import { useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

export interface ProfilePublicOut {
    id: number;
    display_name: string;
    gender: string;
    age: number;
    bio: string | null;
    city_village: string | null;
    state: string | null;
    religion_id: number | null;
    community_id: number | null;
    education_level: string | null;
    occupation_category: string | null;
    marital_status: string | null;
    is_verified: boolean;
    completion_pct: number;
    photo_blur_until_mutual?: boolean;
}

export interface MatchRecommendation {
    profile: ProfilePublicOut;
    score?: number;
    reasons?: string[];
    confidence?: number;
}

function confidenceLabel(confidence?: number): string | null {
    if (confidence === undefined) return null;
    if (confidence >= 83) return "High confidence";
    if (confidence >= 67) return "Good confidence";
    return "Early estimate";
}

export function MatchCard({ match }: { match: MatchRecommendation }) {
    const { profile, score, reasons, confidence } = match;
    const { toast } = useToast();
    const [interestSent, setInterestSent] = useState(false);
    const [sending, setSending] = useState(false);

    const handleSendInterest = async () => {
        setSending(true);
        try {
            await apiFetch(`/interests/${profile.id}`, { method: "POST" });
            setInterestSent(true);
            toast("Interest sent! They will be notified.", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to send interest";
            toast(msg, "error");
        } finally {
            setSending(false);
        }
    };

    const location = [profile.city_village, profile.state].filter(Boolean).join(", ");

    return (
        <Card className="group p-0 overflow-hidden hover:-translate-y-0.5 hover:shadow-md transition-all duration-200">
            {/* 1. Photo / privacy state */}
            <div className="h-24 bg-gradient-to-r from-gold-100 to-gold-50 dark:from-gray-800 dark:to-gray-700 relative">
                {profile.photo_blur_until_mutual && (
                    <span className="absolute top-2 left-2 text-[11px] bg-white/90 dark:bg-gray-900/90 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full border border-sand dark:border-gray-700">
                        🔒 Photo private
                    </span>
                )}
            </div>

            <div className="p-4 relative">
                {/* Avatar */}
                <div className="absolute -top-8 left-4 w-14 h-14 rounded-full border-[3px] border-white dark:border-gray-900 bg-gold-50 dark:bg-gray-800 flex items-center justify-center overflow-hidden shadow-sm">
                    <span className="text-xl" aria-hidden>
                        {profile.gender === "female" ? "👩" : "👨"}
                    </span>
                </div>

                {/* 2. Core details */}
                <div className="mt-6 space-y-1">
                    <div className="flex items-center gap-1.5">
                        <h3 className="font-bold font-serif text-base text-gray-900 dark:text-gray-100 truncate">
                            {profile.display_name}, {profile.age}
                        </h3>
                        {profile.is_verified && (
                            <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-success" title="Identity verified">
                                ✓ Verified
                            </span>
                        )}
                    </div>
                    {location && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{location}</p>
                    )}
                    {(profile.occupation_category || profile.education_level) && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {profile.occupation_category || profile.education_level}
                        </p>
                    )}
                </div>

                {/* 3. Compatibility */}
                {score !== undefined && (
                    <div className="mt-3">
                        <p className="text-sm font-semibold text-primary-700 dark:text-primary-300">
                            {Math.round(score)}% Match
                            {confidenceLabel(confidence) && (
                                <span className="font-normal text-gray-500 dark:text-gray-400"> · {confidenceLabel(confidence)}</span>
                            )}
                        </p>
                        {reasons && reasons.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                                {reasons.slice(0, 3).map((reason, idx) => (
                                    <span
                                        key={idx}
                                        className="text-[11px] px-2 py-0.5 rounded-full bg-gold-100 dark:bg-gold-950/60 text-gray-700 dark:text-gold-200 border border-gold-200 dark:border-gold-800"
                                    >
                                        {reason}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Actions */}
                <div className="mt-4 pt-3 border-t border-sand dark:border-gray-800 flex gap-2">
                    <Link href={`/profile/${profile.id}`} className="flex-1">
                        <Button variant="outline" size="sm" className="w-full">
                            View Profile
                        </Button>
                    </Link>
                    <Button
                        size="sm"
                        className="flex-1"
                        onClick={handleSendInterest}
                        disabled={interestSent}
                        isLoading={sending}
                    >
                        {interestSent ? "Interest Sent ✓" : "Send Interest"}
                    </Button>
                </div>
            </div>
        </Card>
    );
}
