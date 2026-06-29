"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useAuth } from "@/lib/useAuth";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface PrivacyData {
    visibility: string;
    photo_blur_until_mutual: boolean;
    hide_from_search: boolean;
}

function SettingsInner() {
    const { toast } = useToast();
    const { user, logout } = useAuth();
    const router = useRouter();

    const [privacy, setPrivacy] = useState<PrivacyData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                // We fetch the profile to get the privacy settings
                const data = await apiFetch<PrivacyData & { hide_from_search: boolean }>("/profiles/me");
                if (!cancelled) {
                    setPrivacy({
                        visibility: data.visibility,
                        photo_blur_until_mutual: data.photo_blur_until_mutual,
                        hide_from_search: data.hide_from_search,
                    });
                }
            } catch (err) {
                const msg = err instanceof Error ? err.message : "Failed to load settings";
                if (!msg.includes("404")) {
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

    const handleSavePrivacy = async () => {
        if (!privacy) return;
        setSaving(true);
        try {
            await apiFetch("/profiles/me/privacy", {
                method: "PATCH",
                body: privacy,
            });
            toast("Privacy settings updated successfully", "success");
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to save privacy settings";
            toast(msg, "error");
        } finally {
            setSaving(false);
        }
    };

    const handleLogout = () => {
        logout();
        toast("You have been signed out.", "info");
        router.push("/login");
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-950">
                <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            <header className="sticky top-0 w-full z-10 glass border-b border-white/20">
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

            <main className="flex-1 container mx-auto px-4 py-8 max-w-3xl">
                <h1 className="text-3xl font-serif font-bold mb-8 text-gray-900 dark:text-gray-100">Account Settings</h1>

                <div className="space-y-8">
                    {/* Account Info */}
                    <Card className="p-6">
                        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100">Account Details</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-medium text-gray-500 block mb-1">Registered Phone Number</label>
                                <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md font-mono text-gray-700 dark:text-gray-300">
                                    {user?.phone || "Unknown"}
                                </div>
                                <p className="text-xs text-gray-500 mt-2">
                                    Phone number cannot be changed currently. Contact support for assistance.
                                </p>
                            </div>
                        </div>
                    </Card>

                    {/* Privacy Settings */}
                    {privacy ? (
                        <Card className="p-6 border-primary-200 dark:border-primary-900/50">
                            <h2 className="text-xl font-bold mb-1 text-gray-900 dark:text-gray-100">Privacy & Visibility</h2>
                            <p className="text-sm text-gray-500 mb-6">Control who can see your profile and photos.</p>

                            <div className="space-y-6">
                                <div>
                                    <label className="text-sm font-medium block mb-2">Profile Visibility</label>
                                    <select
                                        value={privacy.visibility}
                                        onChange={e => setPrivacy({ ...privacy, visibility: e.target.value })}
                                        className="w-full md:w-2/3 px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                                    >
                                        <option value="public">Public — anyone can see</option>
                                        <option value="verified_only">Verified Members Only</option>
                                        <option value="hidden">Hidden completely from search</option>
                                    </select>
                                    <p className="text-xs text-gray-500 mt-2">
                                        If hidden, you can still view others but they won&apos;t find you.
                                    </p>
                                </div>

                                <div className="border-t border-gray-200 dark:border-gray-800 pt-6">
                                    <label className="flex items-start gap-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={privacy.photo_blur_until_mutual}
                                            onChange={e => setPrivacy({ ...privacy, photo_blur_until_mutual: e.target.checked })}
                                            className="mt-1 w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                        />
                                        <div>
                                            <div className="font-bold text-sm text-gray-900 dark:text-gray-100">Blur my photos until mutual interest</div>
                                            <div className="text-xs text-gray-500 mt-1 max-w-lg">
                                                When enabled, your photos will appear heavily blurred to everyone. They will only be revealed if you accept an interest request from another user.
                                            </div>
                                        </div>
                                    </label>
                                </div>

                                <div className="border-t border-gray-200 dark:border-gray-800 pt-6">
                                    <label className="flex items-start gap-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={privacy.hide_from_search}
                                            onChange={e => setPrivacy({ ...privacy, hide_from_search: e.target.checked })}
                                            className="mt-1 w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                        />
                                        <div>
                                            <div className="font-bold text-sm text-gray-900 dark:text-gray-100">Hide completely from Search</div>
                                            <div className="text-xs text-gray-500 mt-1 max-w-lg">
                                                Overrides visibility settings. Your profile will not appear in the daily matches or search results.
                                            </div>
                                        </div>
                                    </label>
                                </div>

                                <div className="flex justify-end pt-4">
                                    <Button onClick={handleSavePrivacy} isLoading={saving}>
                                        Save Privacy Settings
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    ) : (
                        <Card className="p-6 text-center text-gray-500">
                            You need to <Link href="/profile/create" className="text-primary-600 hover:underline">create a profile</Link> before accessing privacy settings.
                        </Card>
                    )}

                    {/* Danger Zone */}
                    <Card className="p-6 border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-950/10">
                        <h2 className="text-xl font-bold mb-4 text-red-600 dark:text-red-400">Danger Zone</h2>
                        <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
                            <div>
                                <p className="text-sm font-bold text-gray-900 dark:text-gray-100">Sign out</p>
                                <p className="text-xs text-gray-500">Sign out of your account on this device.</p>
                            </div>
                            <Button variant="outline" onClick={handleLogout} className="border-red-200 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 w-full md:w-auto">
                                Sign Out
                            </Button>
                        </div>
                    </Card>

                </div>
            </main>
        </div>
    );
}

export default function SettingsPage() {
    return (
        <ProtectedRoute>
            <SettingsInner />
        </ProtectedRoute>
    );
}
