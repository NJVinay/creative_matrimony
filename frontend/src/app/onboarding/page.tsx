"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";
import { dobError, maxDobFor } from "@/lib/age";
import { useProfile } from "@/lib/useProfile";

interface OnboardingData {
    profile_mode: string;
    guardian_relationship?: string;
    display_name: string;
    gender: string;
    date_of_birth: string;
    city_village: string;
    state: string;
    country: string;
    identity_language_group: string;
}

export default function OnboardingPage() {
    const router = useRouter();
    const { toast } = useToast();
    const { refreshProfile } = useProfile();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);

    const [formData, setFormData] = useState<OnboardingData>({
        profile_mode: "",
        guardian_relationship: "",
        display_name: "",
        gender: "",
        date_of_birth: "",
        city_village: "",
        state: "",
        country: "India",
        identity_language_group: "Telugu"
    });
    // Women-first safety: verified-only visibility opt-in (shown for female profiles)
    const [verifiedOnlyOptIn, setVerifiedOnlyOptIn] = useState(false);

    const updateField = (field: keyof OnboardingData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const dobErr = dobError(formData.date_of_birth, formData.gender);

    const nextStep = () => setStep(prev => prev + 1);
    const prevStep = () => setStep(prev => prev - 1);

    const handleSubmit = async () => {
        setLoading(true);
        try {
            // Send payload to backend
            const payload = {
                ...formData,
                guardian_relationship: formData.profile_mode === "parent" ? formData.guardian_relationship : null,
                verified_only_opt_in: verifiedOnlyOptIn,
            };
            await apiFetch("/profiles", {
                method: "POST",
                body: payload,
            });
            // Load the new profile into context so the dashboard unlocks without a reload
            await refreshProfile();
            toast("Profile created successfully!", "success");
            router.push("/dashboard");
        } catch (err: unknown) {
            toast(err instanceof Error ? err.message : "Failed to create profile.", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <ProtectedRoute>
            <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col items-center justify-center p-4">
                <div className="w-full max-w-xl">
                    {/* Progress Bar */}
                    <div className="flex gap-2 mb-8">
                        {[1, 2, 3].map((s) => (
                            <div
                                key={s}
                                className={`h-2 flex-1 rounded-full ${s <= step ? "bg-primary-600" : "bg-gray-200 dark:bg-gray-800"
                                    } transition-all duration-300`}
                            />
                        ))}
                    </div>

                    <Card className="p-8 shadow-xl">
                        {step === 1 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100 text-center">
                                    Who are you creating this profile for?
                                </h1>
                                <p className="text-center text-gray-600 dark:text-gray-400">
                                    Select the option that best describes your role.
                                </p>
                                <div className="grid gap-4 mt-8">
                                    <button
                                        onClick={() => {
                                            updateField("profile_mode", "self");
                                            nextStep();
                                        }}
                                        className={`p-6 border-2 rounded-xl text-left transition-all ${formData.profile_mode === "self"
                                                ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                                : "border-gray-200 dark:border-gray-800 hover:border-primary-300"
                                            }`}
                                    >
                                        <h3 className="font-bold text-xl mb-1">For Myself</h3>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            I am managing my own matrimonial profile.
                                        </p>
                                    </button>

                                    <button
                                        onClick={() => {
                                            updateField("profile_mode", "parent");
                                        }}
                                        className={`p-6 border-2 rounded-xl text-left transition-all ${formData.profile_mode === "parent"
                                                ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                                : "border-gray-200 dark:border-gray-800 hover:border-primary-300"
                                            }`}
                                    >
                                        <h3 className="font-bold text-xl mb-1">For My Son / Daughter / Relative</h3>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            I am managing this profile on behalf of someone else.
                                        </p>
                                    </button>
                                </div>

                                {formData.profile_mode === "parent" && (
                                    <div className="space-y-4 mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg animate-in fade-in duration-300">
                                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                            What is your relationship to the person?
                                        </label>
                                        <select
                                            value={formData.guardian_relationship || ""}
                                            onChange={(e) => updateField("guardian_relationship", e.target.value)}
                                            className="w-full h-11 px-3 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                                        >
                                            <option value="" disabled>Select Relationship</option>
                                            <option value="Father">Father</option>
                                            <option value="Mother">Mother</option>
                                            <option value="Brother">Brother</option>
                                            <option value="Sister">Sister</option>
                                            <option value="Relative">Other Relative</option>
                                        </select>
                                        <Button
                                            className="w-full mt-4"
                                            onClick={nextStep}
                                            disabled={!formData.guardian_relationship}
                                        >
                                            Continue
                                        </Button>
                                    </div>
                                )}
                            </div>
                        )}

                        {step === 2 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                                <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100 mb-6">
                                    Basic Details
                                </h1>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Full Name</label>
                                        <Input
                                            value={formData.display_name}
                                            onChange={(e) => updateField("display_name", e.target.value)}
                                            placeholder="Enter full name"
                                            required
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Gender</label>
                                        <div className="flex gap-4">
                                            {["male", "female"].map((g) => (
                                                <button
                                                    key={g}
                                                    onClick={() => updateField("gender", g)}
                                                    className={`flex-1 p-3 rounded-md border-2 transition-all ${formData.gender === g
                                                            ? "border-primary-600 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300"
                                                            : "border-gray-200 dark:border-gray-800"
                                                        }`}
                                                >
                                                    <span className="capitalize">{g}</span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Date of Birth</label>
                                        <Input
                                            type="date"
                                            value={formData.date_of_birth}
                                            onChange={(e) => updateField("date_of_birth", e.target.value)}
                                            max={maxDobFor(formData.gender || "female")}
                                            error={dobErr ?? undefined}
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-4 pt-4">
                                    <Button variant="outline" onClick={prevStep} className="flex-1">Back</Button>
                                    <Button
                                        className="flex-1"
                                        onClick={nextStep}
                                        disabled={!formData.display_name || !formData.gender || !formData.date_of_birth || !!dobErr}
                                    >
                                        Continue
                                    </Button>
                                </div>
                            </div>
                        )}

                        {step === 3 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                                <h1 className="text-3xl font-serif font-bold text-gray-900 dark:text-gray-100 mb-6">
                                    Where do they live?
                                </h1>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">City / Village</label>
                                        <Input
                                            value={formData.city_village}
                                            onChange={(e) => updateField("city_village", e.target.value)}
                                            placeholder="e.g. Hyderabad"
                                            required
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">State</label>
                                        <select
                                            value={formData.state}
                                            onChange={(e) => updateField("state", e.target.value)}
                                            className="w-full h-11 px-3 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                                            required
                                        >
                                            <option value="" disabled>Select State</option>
                                            <option value="Andhra Pradesh">Andhra Pradesh</option>
                                            <option value="Telangana">Telangana</option>
                                            <option value="Karnataka">Karnataka</option>
                                            <option value="Tamil Nadu">Tamil Nadu</option>
                                            <option value="Other">Other</option>
                                        </select>
                                    </div>
                                </div>

                                {formData.gender === "female" && (
                                    <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-100 dark:border-primary-800">
                                        <label className="flex items-start gap-3 cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={verifiedOnlyOptIn}
                                                onChange={(e) => setVerifiedOnlyOptIn(e.target.checked)}
                                                className="mt-1 w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                            />
                                            <div>
                                                <div className="font-bold text-sm">Extra safety: show my profile only to verified members</div>
                                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                    Photos are blurred until mutual interest by default. You can change both anytime in Settings.
                                                </div>
                                            </div>
                                        </label>
                                    </div>
                                )}

                                <div className="flex gap-4 pt-4">
                                    <Button variant="outline" onClick={prevStep} className="flex-1" disabled={loading}>Back</Button>
                                    <Button
                                        className="flex-1"
                                        onClick={handleSubmit}
                                        isLoading={loading}
                                        disabled={!formData.city_village || !formData.state}
                                    >
                                        Complete Profile
                                    </Button>
                                </div>
                            </div>
                        )}
                    </Card>
                </div>
            </div>
        </ProtectedRoute>
    );
}
