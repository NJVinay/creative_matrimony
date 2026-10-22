"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { AuthGuard } from "@/components/ui/AuthGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { TaxonomySelect } from "@/components/ui/TaxonomySelect";
import Link from "next/link";
import Image from "next/image";
import { staticUrl } from "@/lib/api";

interface ProfileData {
    id: number;
    display_name: string;
    gender: string;
    date_of_birth: string;
    bio: string | null;
    city_village: string | null;
    state: string | null;
    religion_id: number | null;
    community_id: number | null;
    subcaste_id: number | null;
    education_level: string | null;
    occupation_category: string | null;
    marital_status: string | null;
    family_details: string | null;
    partner_preferences: string | null;
    visibility: string;
    photo_blur_until_mutual: boolean;
    hide_from_search: boolean;
    completion_pct: number;
}

interface PhotoItem {
    id: number;
    storage_key: string;
    is_primary: boolean;
    is_approved: boolean | null;
}

interface HoroscopeData {
    id?: number;
    rasi?: string;
    star?: string;
    dosham?: boolean;
    dosham_details?: string;
    time_of_birth?: string;
    place_of_birth?: string;
    chart_images?: string[];
}

type Tab = "basic" | "location" | "details" | "horoscope" | "photos";

function ProfileEditInner() {
    const { toast } = useToast();
    const [tab, setTab] = useState<Tab>("basic");
    const [profile, setProfile] = useState<ProfileData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [notFound, setNotFound] = useState(false);
    const [photos, setPhotos] = useState<PhotoItem[]>([]);
    const [uploading, setUploading] = useState(false);

    // Horoscope
    const [horoscope, setHoroscope] = useState<HoroscopeData>({});
    const [savingHoroscope, setSavingHoroscope] = useState(false);
    const [chartUploading, setChartUploading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await apiFetch<ProfileData>("/profiles/me");
                if (!cancelled) setProfile(data);

                // Fetch Horoscope
                try {
                    const hsData = await apiFetch<HoroscopeData>("/horoscope/me");
                    if (!cancelled) setHoroscope(hsData);
                } catch {
                    // It's optional, so 404 is fine.
                    console.log("No horoscope found for user");
                }
            } catch (err) {
                const msg = err instanceof Error ? err.message : "Failed to load profile";
                if (msg.includes("Profile not found") || msg.includes("404")) {
                    setNotFound(true);
                } else {
                    toast(msg, "error");
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [toast]);

    const fetchPhotos = useCallback(async () => {
        try {
            const list = await apiFetch<Array<{ id: number; storage_key: string; is_primary: boolean; is_approved: boolean | null }>>("/profiles/me/photos");
            setPhotos(list);
        } catch (err) {
            console.error("Failed to load photos:", err);
        }
    }, []);

    useEffect(() => {
        if (tab === "photos" && !notFound) {
            void fetchPhotos();
        }
    }, [tab, notFound, fetchPhotos]);

    const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
            toast("File too large. Max 5 MB.", "error");
            return;
        }
        setUploading(true);
        try {
            const fd = new FormData();
            fd.append("file", file);
            await apiFetch("/profiles/me/photos", { method: "POST", body: fd });
            toast("Photo uploaded. Pending moderator review.", "success");
            await fetchPhotos();
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Upload failed";
            toast(msg, "error");
        } finally {
            setUploading(false);
            e.target.value = "";
        }
    };

    const handleSave = async () => {
        if (!profile) return;
        setSaving(true);
        try {
            await apiFetch("/profiles/me", {
                method: "PATCH",
                body: {
                    display_name: profile.display_name,
                    bio: profile.bio,
                    city_village: profile.city_village,
                    state: profile.state,
                    religion_id: profile.religion_id,
                    community_id: profile.community_id,
                    subcaste_id: profile.subcaste_id,
                    education_level: profile.education_level,
                    occupation_category: profile.occupation_category,
                    marital_status: profile.marital_status,
                    family_details: profile.family_details,
                    partner_preferences: profile.partner_preferences,
                },
            });
            toast("Profile saved", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Save failed";
            toast(msg, "error");
        } finally {
            setSaving(false);
        }
    };

    const handleSaveHoroscope = async () => {
        setSavingHoroscope(true);
        try {
            await apiFetch("/horoscope/me", {
                method: "PUT",
                body: horoscope,
            });
            toast("Horoscope saved", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Save failed";
            toast(msg, "error");
        } finally {
            setSavingHoroscope(false);
        }
    };

    const handleChartUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setChartUploading(true);
        try {
            const fd = new FormData();
            fd.append("file", file);
            const hsData = await apiFetch<HoroscopeData>("/horoscope/me/chart", { method: "POST", body: fd });
            setHoroscope(hsData);
            toast("Chart uploaded.", "success");
        } catch {
            toast("Upload failed", "error");
        } finally {
            setChartUploading(false);
            e.target.value = "";
        }
    };

    const update = <K extends keyof ProfileData>(key: K, value: ProfileData[K]) => {
        setProfile(prev => prev ? { ...prev, [key]: value } : prev);
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (notFound) {
        return (
            <div className="min-h-screen flex items-center justify-center px-4">
                <Card className="p-8 text-center max-w-md space-y-4">
                    <h2 className="text-2xl font-bold">No profile yet</h2>
                    <p className="text-gray-600 dark:text-gray-400">
                        Let&apos;s set up your profile first.
                    </p>
                    <Link href="/profile/create">
                        <Button className="w-full">Create Profile</Button>
                    </Link>
                </Card>
            </div>
        );
    }

    if (!profile) return null;

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
                        <Link href="/dashboard">
                            <Button variant="outline" size="sm">Back to Dashboard</Button>
                        </Link>
                    </div>
                </div>
            </header>

            <main className="flex-1 container mx-auto px-4 pt-24 pb-8 max-w-3xl">
                <div className="flex items-center justify-between mb-6">
                    <h1 className="text-3xl font-serif font-bold">Edit Profile</h1>
                    <div className="text-sm text-gray-500">
                        Completion: <span className="font-bold text-primary-600">{Math.round(profile.completion_pct)}%</span>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-800 overflow-x-auto pb-1">
                    {(["basic", "location", "details", "horoscope", "photos"] as Tab[]).map(t => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${tab === t
                                ? "border-primary-600 dark:border-primary-400 text-primary-600"
                                : "border-transparent text-gray-500 hover:text-gray-700"
                                }`}
                        >
                            {t === "basic" && "Basic Info"}
                            {t === "location" && "Location & Community"}
                            {t === "details" && "Education & Family"}
                            {t === "horoscope" && "Horoscope"}
                            {t === "photos" && "Photos"}
                        </button>
                    ))}
                </div>

                <Card className="p-6 space-y-4">
                    {tab === "basic" && (
                        <>
                            <div>
                                <label className="text-sm font-medium block mb-1">Display Name</label>
                                <Input
                                    value={profile.display_name}
                                    onChange={e => update("display_name", e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Bio</label>
                                <textarea
                                    value={profile.bio ?? ""}
                                    onChange={e => update("bio", e.target.value || null)}
                                    rows={4}
                                    maxLength={2000}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                />
                            </div>
                        </>
                    )}

                    {tab === "location" && (
                        <>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm font-medium block mb-1">City / Village</label>
                                    <Input
                                        value={profile.city_village ?? ""}
                                        onChange={e => update("city_village", e.target.value || null)}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium block mb-1">State</label>
                                    <Input
                                        value={profile.state ?? ""}
                                        onChange={e => update("state", e.target.value || null)}
                                    />
                                </div>
                            </div>
                            <TaxonomySelect
                                value={{
                                    religion_id: profile.religion_id,
                                    community_id: profile.community_id,
                                    subcaste_id: profile.subcaste_id,
                                }}
                                onChange={next => {
                                    setProfile(prev => prev ? {
                                        ...prev,
                                        religion_id: next.religion_id ?? null,
                                        community_id: next.community_id ?? null,
                                        subcaste_id: next.subcaste_id ?? null,
                                    } : prev);
                                }}
                            />
                        </>
                    )}

                    {tab === "details" && (
                        <>
                            <div>
                                <label className="text-sm font-medium block mb-1">Education</label>
                                <Input
                                    value={profile.education_level ?? ""}
                                    onChange={e => update("education_level", e.target.value || null)}
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Occupation</label>
                                <Input
                                    value={profile.occupation_category ?? ""}
                                    onChange={e => update("occupation_category", e.target.value || null)}
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Marital Status</label>
                                <select
                                    value={profile.marital_status ?? ""}
                                    onChange={e => update("marital_status", e.target.value || null)}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                >
                                    <option value="">— Select —</option>
                                    <option value="never_married">Never married</option>
                                    <option value="divorced">Divorced</option>
                                    <option value="widowed">Widowed</option>
                                    <option value="awaiting_divorce">Awaiting divorce</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Family details</label>
                                <textarea
                                    value={profile.family_details ?? ""}
                                    onChange={e => update("family_details", e.target.value || null)}
                                    rows={3}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Partner preferences</label>
                                <textarea
                                    value={profile.partner_preferences ?? ""}
                                    onChange={e => update("partner_preferences", e.target.value || null)}
                                    rows={3}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                />
                            </div>
                        </>
                    )}

                    {/* Privacy tab was moved to /settings */}

                    {tab === "horoscope" && (
                        <>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium block mb-1">Rasi (Moon Sign)</label>
                                    <select
                                        value={horoscope.rasi || ""}
                                        onChange={e => setHoroscope(h => ({ ...h, rasi: e.target.value || undefined }))}
                                        className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    >
                                        <option value="">Unknown</option>
                                        <option value="mesha">Mesha (Aries)</option>
                                        <option value="vrishabha">Vrishabha (Taurus)</option>
                                        <option value="mithuna">Mithuna (Gemini)</option>
                                        <option value="karka">Karka (Cancer)</option>
                                        <option value="simha">Simha (Leo)</option>
                                        <option value="kanya">Kanya (Virgo)</option>
                                        <option value="tula">Tula (Libra)</option>
                                        <option value="vrischika">Vrischika (Scorpio)</option>
                                        <option value="dhanu">Dhanu (Sagittarius)</option>
                                        <option value="makara">Makara (Capricorn)</option>
                                        <option value="kumbha">Kumbha (Aquarius)</option>
                                        <option value="meena">Meena (Pisces)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-sm font-medium block mb-1">Nakshatra (Star)</label>
                                    <select
                                        value={horoscope.star || ""}
                                        onChange={e => setHoroscope(h => ({ ...h, star: e.target.value || undefined }))}
                                        className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    >
                                        <option value="">Unknown</option>
                                        <option value="ashwini">Ashwini</option>
                                        <option value="bharani">Bharani</option>
                                        <option value="krittika">Krittika</option>
                                        {/* Simplified list for MVP */}
                                        <option value="rohini">Rohini</option>
                                        <option value="mrigashira">Mrigashira</option>
                                    </select>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium block mb-1">Place of Birth</label>
                                    <Input
                                        value={horoscope.place_of_birth || ""}
                                        onChange={e => setHoroscope(h => ({ ...h, place_of_birth: e.target.value }))}
                                        placeholder="e.g. Hyderabad"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium block mb-1">Time of Birth</label>
                                    <Input
                                        type="time"
                                        value={horoscope.time_of_birth || ""}
                                        onChange={e => setHoroscope(h => ({ ...h, time_of_birth: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div className="flex items-center gap-2 mt-2">
                                <input
                                    type="checkbox"
                                    id="dosham"
                                    checked={horoscope.dosham || false}
                                    onChange={e => setHoroscope(h => ({ ...h, dosham: e.target.checked }))}
                                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                />
                                <label htmlFor="dosham" className="text-sm font-medium">Manglik / Kuja Dosham present</label>
                            </div>
                            {horoscope.dosham && (
                                <div>
                                    <label className="text-sm font-medium block mb-1">Dosham Details</label>
                                    <textarea
                                        value={horoscope.dosham_details || ""}
                                        onChange={e => setHoroscope(h => ({ ...h, dosham_details: e.target.value }))}
                                        rows={2}
                                        className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    />
                                </div>
                            )}

                            <div className="pt-4 border-t border-gray-200 dark:border-gray-800 mt-4">
                                <h3 className="font-bold mb-2">Horoscope Chart Upload</h3>
                                <p className="text-xs text-gray-500 mb-2">Upload an image of your physical horoscope chart. This will only be visible to mutual matches.</p>
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleChartUpload}
                                    disabled={chartUploading}
                                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                                />
                                {chartUploading && <span className="text-xs text-gray-500">Uploading...</span>}

                                {horoscope.chart_images && horoscope.chart_images.length > 0 && (
                                    <div className="mt-4 grid grid-cols-2 gap-2">
                                        {horoscope.chart_images.map((img, idx) => (
                                            <div key={idx} className="aspect-[4/3] bg-gray-100 relative rounded-md overflow-hidden">
                                                <Image src={staticUrl(img)} alt="Horoscope Chart" fill className="object-cover" />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {tab === "photos" && (
                        <>
                            <div>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                                    Upload up to 5 photos. Photos are reviewed by moderators before they appear on your profile.
                                </p>
                                <label className="block">
                                    <input
                                        type="file"
                                        accept="image/jpeg,image/png,image/webp"
                                        onChange={handlePhotoUpload}
                                        disabled={uploading}
                                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                                    />
                                </label>
                                {uploading && <p className="text-sm text-gray-500 mt-2">Uploading...</p>}
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-4 border-t border-gray-200 dark:border-gray-800">
                                {photos.length === 0 ? (
                                    <div className="col-span-full text-center text-gray-500 py-8">
                                        No photos yet. Upload your first photo above.
                                    </div>
                                ) : (
                                    photos.map(photo => (
                                        <div key={photo.id} className="aspect-square relative rounded-lg overflow-hidden bg-gray-100 border-2 border-transparent">
                                            <Image
                                                src={staticUrl(photo.storage_key)}
                                                alt="My photo"
                                                fill
                                                className="object-cover"
                                            />
                                            <div className="absolute top-2 left-2 flex gap-1">
                                                {photo.is_primary && (
                                                    <span className="bg-primary-600 text-white text-xs px-2 py-0.5 rounded">
                                                        Primary
                                                    </span>
                                                )}
                                                {photo.is_approved === null && (
                                                    <span className="bg-yellow-500 text-white text-xs px-2 py-0.5 rounded">
                                                        Pending
                                                    </span>
                                                )}
                                                {photo.is_approved === false && (
                                                    <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded">
                                                        Rejected
                                                    </span>
                                                )}
                                                {photo.is_approved === true && (
                                                    <span className="bg-green-500 text-white text-xs px-2 py-0.5 rounded">
                                                        ✓
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </>
                    )}

                    <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-800">
                        <Button
                            onClick={tab === "horoscope" ? handleSaveHoroscope : handleSave}
                            isLoading={tab === "horoscope" ? savingHoroscope : saving}
                        >
                            Save Changes
                        </Button>
                    </div>
                </Card>
            </main>
        </div>
    );
}

export default function ProfileEditPage() {
    return (
        <AuthGuard>
            <ProfileEditInner />
        </AuthGuard>
    );
}
