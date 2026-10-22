"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { apiFetch, ApiError, staticUrl } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useToast } from "@/components/ui/Toast";
import { AuthGuard } from "@/components/ui/AuthGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import Image from "next/image";

interface PublicProfile {
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

interface Photo {
    id: number;
    // null + locked while the owner blurs photos until mutual interest:
    // the API withholds the file URL, so there is nothing to show yet.
    storage_key: string | null;
    locked?: boolean;
    is_primary: boolean;
}

interface HoroscopeData {
    rasi?: string;
    star?: string;
    dosham?: boolean;
    dosham_details?: string;
    time_of_birth?: string;
    place_of_birth?: string;
    chart_images?: string[];
    charts_locked?: boolean; // charts exist but are withheld until mutual interest
}

// Staff open member profiles from the moderation queues; the API lets them
// past visibility, block, photo-blur and age checks so reports can be reviewed.
const REVIEWER_ROLES = new Set(["admin", "moderator"]);

const REPORT_REASONS = [
    { value: "fake_profile", label: "Fake profile" },
    { value: "harassment", label: "Harassment" },
    { value: "inappropriate_photo", label: "Inappropriate photo" },
    { value: "spam", label: "Spam" },
    { value: "age_misrepresentation", label: "Age misrepresentation" },
    { value: "other", label: "Other" },
];

function PublicProfileInner({ profileId }: { profileId: number }) {
    const { toast } = useToast();
    const { user } = useAuth();
    const isReviewer = REVIEWER_ROLES.has(user?.role ?? "");
    const [profile, setProfile] = useState<PublicProfile | null>(null);
    const [photos, setPhotos] = useState<Photo[]>([]);
    const [horoscope, setHoroscope] = useState<HoroscopeData | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [showReport, setShowReport] = useState(false);
    const [reportReason, setReportReason] = useState("other");
    const [reportEvidence, setReportEvidence] = useState("");
    const [reportSubmitting, setReportSubmitting] = useState(false);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                // Photos and horoscope are optional (a 404 horoscope just means none)
                const [p, photosData, hs] = await Promise.all([
                    apiFetch<PublicProfile>(`/profiles/${profileId}`),
                    apiFetch<Photo[]>(`/profiles/${profileId}/photos`).catch(() => [] as Photo[]),
                    apiFetch<HoroscopeData>(`/horoscope/profile/${profileId}`).catch(() => null),
                ]);

                if (!cancelled) {
                    setProfile(p);
                    setPhotos(photosData);
                    setHoroscope(hs);
                }
            } catch (err) {
                if (cancelled) return;
                const status = err instanceof ApiError ? err.status : 0;
                if (status === 404) {
                    setNotFound(true);
                } else if (status === 403) {
                    toast("This profile is not visible to you.", "error");
                    setNotFound(true);
                } else {
                    toast(err instanceof Error ? err.message : "Failed to load profile", "error");
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [profileId, toast]);

    const handleSendInterest = async () => {
        try {
            await apiFetch(`/interests/${profileId}`, { method: "POST" });
            toast("Interest sent! They will be notified.", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to send interest";
            toast(msg, "error");
        }
    };

    const handlePanicBlock = async () => {
        if (!window.confirm("Block this profile? They will no longer see you, message you, or appear in your matches. Any shared chat will be closed immediately.")) {
            return;
        }
        try {
            await apiFetch(`/safety/block/${profileId}`, { method: "POST", body: {} });
            toast("Profile blocked. They can no longer contact you.", "success");
            setNotFound(true); // hide the profile locally right away
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to block";
            toast(msg, "error");
        }
    };

    const handleReport = async () => {
        if (reportReason === "other" && !reportEvidence.trim()) {
            toast("Please provide a description for the 'other' reason.", "error");
            return;
        }
        setReportSubmitting(true);
        try {
            await apiFetch("/reports", {
                method: "POST",
                body: {
                    target_profile_id: profileId,
                    reason: reportReason,
                    evidence_text: reportEvidence || null,
                },
            });
            toast("Report submitted. Our team will review it.", "success");
            setShowReport(false);
            setReportEvidence("");
            setReportReason("other");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to submit report";
            toast(msg, "error");
        } finally {
            setReportSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (notFound || !profile) {
        return (
            <div className="min-h-screen flex items-center justify-center px-4">
                <Card className="p-8 text-center max-w-md space-y-4">
                    <h2 className="text-2xl font-bold">Profile unavailable</h2>
                    <p className="text-gray-600 dark:text-gray-400">
                        This profile either does not exist or is hidden from you.
                    </p>
                    <Link href={isReviewer ? "/admin/reports" : "/search"}>
                        <Button>{isReviewer ? "Back to Reports" : "Back to Search"}</Button>
                    </Link>
                </Card>
            </div>
        );
    }

    // Only photos the API shared a URL for are shown; locked ones are counted
    const visiblePhotos = photos.filter((p): p is Photo & { storage_key: string } => !!p.storage_key);
    const lockedCount = photos.length - visiblePhotos.length;
    const primaryPhoto = visiblePhotos.find(p => p.is_primary) || visiblePhotos[0];

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            <header className="fixed top-0 w-full z-10 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/dashboard" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-3">
                        <LanguageToggle />
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 pt-24 pb-8 max-w-4xl">
                {isReviewer && (
                    <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20 px-4 py-3 text-sm text-amber-900 dark:text-amber-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <span>
                            🛡️ Moderator view — shown regardless of the member&apos;s visibility, blocks and photo privacy, for review only.
                        </span>
                        <Link href="/admin/reports" className="font-semibold underline whitespace-nowrap">
                            Back to reports
                        </Link>
                    </div>
                )}
                <Card className="overflow-hidden">
                    {/* Photo header: the real photo when the API shares one, else a placeholder */}
                    <div className="aspect-video bg-gradient-to-br from-primary-100 to-primary-300 dark:from-primary-900 dark:to-primary-700 relative overflow-hidden">
                        {primaryPhoto ? (
                            <Image
                                src={staticUrl(primaryPhoto.storage_key)}
                                alt={profile.display_name}
                                fill
                                sizes="(min-width: 896px) 896px, 100vw"
                                className="object-cover"
                            />
                        ) : lockedCount > 0 ? (
                            <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4 text-primary-900 dark:text-primary-100">
                                <span className="text-5xl mb-2" aria-hidden>🔒</span>
                                <p className="font-bold">Photos visible after mutual interest</p>
                                <p className="text-sm opacity-80 max-w-xs mt-1">
                                    {profile.display_name} shares {lockedCount === 1 ? "their photo" : `${lockedCount} photos`} once you both accept an interest.
                                </p>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full text-6xl text-primary-400">
                                👤
                            </div>
                        )}

                        {profile.is_verified && (
                            <div className="absolute top-4 right-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-semibold z-10 shadow-sm">
                                ✓ Verified
                            </div>
                        )}
                    </div>

                    <div className="p-6 space-y-6">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                            <div>
                                <h1 className="text-3xl font-serif font-bold">{profile.display_name}</h1>
                                <p className="text-gray-500">
                                    {profile.age} years old · {profile.city_village}, {profile.state}
                                </p>
                            </div>
                            {/* Member actions; staff review without interacting (they may have no profile) */}
                            {!isReviewer && (
                                <div className="flex gap-2">
                                    <Button onClick={handleSendInterest}>
                                        💌 Send Interest
                                    </Button>
                                    <Button variant="outline" onClick={() => setShowReport(true)}>
                                        ⚠️ Report
                                    </Button>
                                    <Button
                                        variant="outline"
                                        onClick={handlePanicBlock}
                                        className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                                    >
                                        🚫 Block
                                    </Button>
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                            <div>
                                <div className="text-xs text-gray-500 uppercase">Education</div>
                                <div className="font-medium">{profile.education_level || "—"}</div>
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 uppercase">Occupation</div>
                                <div className="font-medium">{profile.occupation_category || "—"}</div>
                            </div>
                            <div>
                                <div className="text-xs text-gray-500 uppercase">Marital Status</div>
                                <div className="font-medium capitalize">
                                    {profile.marital_status?.replace(/_/g, " ") || "—"}
                                </div>
                            </div>
                        </div>

                        {profile.bio && (
                            <div>
                                <h2 className="font-bold text-lg mb-2">About</h2>
                                <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{profile.bio}</p>
                            </div>
                        )}

                        {/* Horoscope details */}
                        {horoscope && (
                            <div className="pt-6 border-t border-gray-100 dark:border-gray-800">
                                <h2 className="font-bold text-lg mb-3">Horoscope Details</h2>
                                <div className="grid grid-cols-2 gap-y-4 gap-x-2 text-sm">
                                    {horoscope.rasi && (
                                        <div>
                                            <span className="text-gray-500 block mb-1">Rasi (Moon Sign)</span>
                                            <span className="font-medium capitalize">{horoscope.rasi}</span>
                                        </div>
                                    )}
                                    {horoscope.star && (
                                        <div>
                                            <span className="text-gray-500 block mb-1">Nakshatra</span>
                                            <span className="font-medium capitalize">{horoscope.star}</span>
                                        </div>
                                    )}
                                    {(horoscope.place_of_birth || horoscope.time_of_birth) && (
                                        <div>
                                            <span className="text-gray-500 block mb-1">Birth Details</span>
                                            <span className="font-medium">
                                                {horoscope.place_of_birth} {horoscope.place_of_birth && horoscope.time_of_birth ? '·' : ''} {horoscope.time_of_birth}
                                            </span>
                                        </div>
                                    )}
                                    {horoscope.dosham !== undefined && (
                                        <div>
                                            <span className="text-gray-500 block mb-1">Manglik / Kuja Dosham</span>
                                            <span className="font-medium">
                                                {horoscope.dosham ? (
                                                    <span className="text-red-600 font-bold">Yes</span>
                                                ) : "No"}
                                            </span>
                                            {horoscope.dosham && horoscope.dosham_details && (
                                                <p className="text-xs text-gray-500 mt-1">{horoscope.dosham_details}</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {/* The API decides: charts arrive only when the viewer may see them */}
                                {horoscope.chart_images && horoscope.chart_images.length > 0 && (
                                    <div className="mt-4">
                                        <h3 className="font-medium text-sm text-gray-500 mb-2">Horoscope Chart</h3>
                                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                            {horoscope.chart_images.map((img, idx) => (
                                                <div key={idx} className="aspect-square relative rounded-lg overflow-hidden bg-gray-100 border">
                                                    <Image
                                                        src={staticUrl(img)}
                                                        alt="Horoscope Chart"
                                                        fill
                                                        sizes="(min-width: 640px) 33vw, 50vw"
                                                        className="object-cover"
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {horoscope.charts_locked && (
                                    <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                                        🔒 Horoscope chart visible after mutual interest.
                                    </p>
                                )}
                            </div>
                        )}

                        {/* Photo gallery (unlocked photos only) */}
                        {visiblePhotos.length > 1 && (
                            <div>
                                <h2 className="font-bold text-lg mb-3">Photos</h2>
                                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                                    {visiblePhotos.map(p => (
                                        <div key={p.id} className="aspect-square relative rounded-lg overflow-hidden bg-gray-100">
                                            <Image
                                                src={staticUrl(p.storage_key)}
                                                alt=""
                                                fill
                                                sizes="(min-width: 640px) 25vw, 33vw"
                                                className="object-cover"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="text-xs text-gray-400 pt-4 border-t">
                            Profile completion: {Math.round(profile.completion_pct)}% · Contact details are private
                        </div>
                    </div>
                </Card>
            </main>

            {/* Report modal */}
            {showReport && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <Card className="w-full max-w-md p-6 space-y-4">
                        <h2 className="text-xl font-bold">Report this profile</h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            Help us keep the community safe. Reports are reviewed by our moderation team.
                        </p>
                        <div>
                            <label className="text-sm font-medium block mb-1">Reason</label>
                            <select
                                value={reportReason}
                                onChange={e => setReportReason(e.target.value)}
                                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                            >
                                {REPORT_REASONS.map(r => (
                                    <option key={r.value} value={r.value}>{r.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="text-sm font-medium block mb-1">Details (optional)</label>
                            <textarea
                                value={reportEvidence}
                                onChange={e => setReportEvidence(e.target.value)}
                                rows={3}
                                maxLength={2000}
                                className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                placeholder="Any additional context..."
                            />
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button variant="outline" onClick={() => setShowReport(false)}>
                                Cancel
                            </Button>
                            <Button onClick={handleReport} isLoading={reportSubmitting}>
                                Submit Report
                            </Button>
                        </div>
                    </Card>
                </div>
            )}
        </div>
    );
}

export default function PublicProfilePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);
    return (
        <AuthGuard>
            <PublicProfileInner profileId={Number(id)} />
        </AuthGuard>
    );
}
