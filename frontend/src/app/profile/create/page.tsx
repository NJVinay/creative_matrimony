"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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

interface ProfileFormState {
    profile_mode: "self" | "parent";
    guardian_relationship: string;
    display_name: string;
    gender: "male" | "female" | "other";
    date_of_birth: string;
    city_village: string;
    state: string;
    religion_id: number | null;
    community_id: number | null;
    subcaste_id: number | null;
    bio: string;
    education_level: string;
    occupation_category: string;
    marital_status: string;
    family_details: string;
    partner_preferences: string;
}

const TOTAL_STEPS = 4;

function ProfileCreateInner() {
    const router = useRouter();
    const { toast } = useToast();
    const [step, setStep] = useState(1);
    const [submitting, setSubmitting] = useState(false);
    const [form, setForm] = useState<ProfileFormState>({
        profile_mode: "self",
        guardian_relationship: "",
        display_name: "",
        gender: "male",
        date_of_birth: "",
        city_village: "",
        state: "",
        religion_id: null,
        community_id: null,
        subcaste_id: null,
        bio: "",
        education_level: "",
        occupation_category: "",
        marital_status: "never_married",
        family_details: "",
        partner_preferences: "",
    });

    const update = <K extends keyof ProfileFormState>(key: K, value: ProfileFormState[K]) => {
        setForm(prev => ({ ...prev, [key]: value }));
    };

    const canAdvance = (): boolean => {
        if (step === 1) return true; // Mode step is always valid
        if (step === 2) {
            return form.display_name.trim().length >= 2 && form.date_of_birth !== "";
        }
        if (step === 3) {
            return form.city_village.trim().length > 0 && form.state.trim().length > 0;
        }
        return true; // Step 4 (optional) — always advanceable
    };

    const handleNext = () => {
        if (!canAdvance()) {
            toast("Please complete the required fields before continuing.", "error");
            return;
        }
        setStep(s => Math.min(s + 1, TOTAL_STEPS));
    };

    const handleBack = () => setStep(s => Math.max(s - 1, 1));

    const handleSubmit = async () => {
        setSubmitting(true);
        try {
            await apiFetch("/profiles", {
                method: "POST",
                body: {
                    profile_mode: form.profile_mode,
                    guardian_relationship: form.guardian_relationship || null,
                    display_name: form.display_name,
                    gender: form.gender,
                    date_of_birth: form.date_of_birth,
                    bio: form.bio || null,
                    city_village: form.city_village,
                    state: form.state,
                    country: "India",
                    religion_id: form.religion_id,
                    community_id: form.community_id,
                    subcaste_id: form.subcaste_id,
                    education_level: form.education_level || null,
                    occupation_category: form.occupation_category || null,
                    marital_status: form.marital_status || null,
                    identity_language_group: "Telugu",
                    family_details: form.family_details || null,
                    partner_preferences: form.partner_preferences || null,
                },
            });
            toast("Profile created! Welcome aboard.", "success");
            router.replace("/dashboard");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to create profile";
            toast(msg, "error");
        } finally {
            setSubmitting(false);
        }
    };

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

            <main className="flex-1 flex items-start justify-center pt-24 pb-12 px-4">
                <Card className="w-full max-w-2xl p-8 space-y-6">
                    {/* Progress */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm text-gray-500">
                            <span>Step {step} of {TOTAL_STEPS}</span>
                            <span>{Math.round((step / TOTAL_STEPS) * 100)}%</span>
                        </div>
                        <div className="h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary-600 transition-all duration-300"
                                style={{ width: `${(step / TOTAL_STEPS) * 100}%` }}
                            />
                        </div>
                    </div>

                    {/* Step 1: Mode */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <h2 className="text-2xl font-serif font-bold">Who&apos;s creating this profile?</h2>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                Parents or guardians can create profiles for their children.
                            </p>
                            <div className="space-y-3">
                                <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                    <input
                                        type="radio"
                                        name="mode"
                                        checked={form.profile_mode === "self"}
                                        onChange={() => update("profile_mode", "self")}
                                        className="mt-1"
                                    />
                                    <div>
                                        <div className="font-semibold">Myself</div>
                                        <div className="text-sm text-gray-500">I&apos;m creating my own profile</div>
                                    </div>
                                </label>
                                <label className="flex items-start gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                    <input
                                        type="radio"
                                        name="mode"
                                        checked={form.profile_mode === "parent"}
                                        onChange={() => update("profile_mode", "parent")}
                                        className="mt-1"
                                    />
                                    <div>
                                        <div className="font-semibold">On behalf of someone</div>
                                        <div className="text-sm text-gray-500">Parent/guardian creating for son or daughter</div>
                                    </div>
                                </label>
                            </div>
                            {form.profile_mode === "parent" && (
                                <div>
                                    <label className="text-sm font-medium block mb-1">Your relationship</label>
                                    <Input
                                        placeholder="e.g. Father, Mother, Uncle"
                                        value={form.guardian_relationship}
                                        onChange={e => update("guardian_relationship", e.target.value)}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 2: Basics */}
                    {step === 2 && (
                        <div className="space-y-4">
                            <h2 className="text-2xl font-serif font-bold">Basic Details</h2>
                            <div>
                                <label className="text-sm font-medium block mb-1">Display Name *</label>
                                <Input
                                    value={form.display_name}
                                    onChange={e => update("display_name", e.target.value)}
                                    placeholder="Your name or nickname"
                                    maxLength={100}
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Gender *</label>
                                <div className="flex gap-3">
                                    {(["male", "female", "other"] as const).map(g => (
                                        <label key={g} className="flex items-center gap-2 cursor-pointer">
                                            <input
                                                type="radio"
                                                name="gender"
                                                checked={form.gender === g}
                                                onChange={() => update("gender", g)}
                                            />
                                            <span className="capitalize">{g}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Date of Birth *</label>
                                <Input
                                    type="date"
                                    value={form.date_of_birth}
                                    onChange={e => update("date_of_birth", e.target.value)}
                                    max={new Date().toISOString().split("T")[0]}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 3: Location + Religion/Community */}
                    {step === 3 && (
                        <div className="space-y-4">
                            <h2 className="text-2xl font-serif font-bold">Location & Community</h2>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm font-medium block mb-1">City / Village *</label>
                                    <Input
                                        value={form.city_village}
                                        onChange={e => update("city_village", e.target.value)}
                                        placeholder="e.g. Hyderabad"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium block mb-1">State *</label>
                                    <Input
                                        value={form.state}
                                        onChange={e => update("state", e.target.value)}
                                        placeholder="e.g. Telangana"
                                    />
                                </div>
                            </div>
                            <TaxonomySelect
                                value={{
                                    religion_id: form.religion_id,
                                    community_id: form.community_id,
                                    subcaste_id: form.subcaste_id,
                                }}
                                onChange={next => {
                                    setForm(prev => ({
                                        ...prev,
                                        religion_id: next.religion_id ?? null,
                                        community_id: next.community_id ?? null,
                                        subcaste_id: next.subcaste_id ?? null,
                                    }));
                                }}
                            />
                        </div>
                    )}

                    {/* Step 4: Optional details */}
                    {step === 4 && (
                        <div className="space-y-4">
                            <h2 className="text-2xl font-serif font-bold">A bit more (optional)</h2>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                You can fill these later from your profile page. They help us find better matches.
                            </p>
                            <div>
                                <label className="text-sm font-medium block mb-1">Short bio</label>
                                <textarea
                                    value={form.bio}
                                    onChange={e => update("bio", e.target.value)}
                                    rows={3}
                                    maxLength={2000}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    placeholder="A few lines about yourself or your family"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-sm font-medium block mb-1">Education</label>
                                    <Input
                                        value={form.education_level}
                                        onChange={e => update("education_level", e.target.value)}
                                        placeholder="e.g. B.Tech, MBA"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium block mb-1">Occupation</label>
                                    <Input
                                        value={form.occupation_category}
                                        onChange={e => update("occupation_category", e.target.value)}
                                        placeholder="e.g. Software Engineer"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Marital Status</label>
                                <select
                                    value={form.marital_status}
                                    onChange={e => update("marital_status", e.target.value)}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                >
                                    <option value="never_married">Never married</option>
                                    <option value="divorced">Divorced</option>
                                    <option value="widowed">Widowed</option>
                                    <option value="awaiting_divorce">Awaiting divorce</option>
                                </select>
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Family details</label>
                                <textarea
                                    value={form.family_details}
                                    onChange={e => update("family_details", e.target.value)}
                                    rows={2}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    placeholder="Family background, values, etc."
                                />
                            </div>
                            <div>
                                <label className="text-sm font-medium block mb-1">Partner preferences</label>
                                <textarea
                                    value={form.partner_preferences}
                                    onChange={e => update("partner_preferences", e.target.value)}
                                    rows={2}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    placeholder="What you're looking for in a partner"
                                />
                            </div>
                        </div>
                    )}

                    {/* Navigation buttons */}
                    <div className="flex justify-between pt-4 border-t">
                        <Button
                            variant="outline"
                            onClick={handleBack}
                            disabled={step === 1}
                        >
                            Back
                        </Button>
                        {step < TOTAL_STEPS ? (
                            <Button onClick={handleNext}>
                                Next
                            </Button>
                        ) : (
                            <Button onClick={handleSubmit} isLoading={submitting}>
                                Create Profile
                            </Button>
                        )}
                    </div>
                </Card>
            </main>
        </div>
    );
}

export default function ProfileCreatePage() {
    return (
        <AuthGuard>
            <ProfileCreateInner />
        </AuthGuard>
    );
}
