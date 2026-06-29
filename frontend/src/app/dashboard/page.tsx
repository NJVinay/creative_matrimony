"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useProfile } from "@/lib/useProfile";
import { useToast } from "@/components/ui/Toast";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { FamilyModeToggle } from "@/components/ui/FamilyModeToggle";

import { ProgressWidget } from "@/components/dashboard/ProgressWidget";
import { MatchCard, MatchRecommendation } from "@/components/matches/MatchCard";

function DashboardInner() {
    const { t } = useTranslation();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { profile, isLoading: profileLoading } = useProfile();
    const { toast } = useToast();

    const [matches, setMatches] = useState<MatchRecommendation[]>([]);
    const [matchesLoading, setMatchesLoading] = useState(false);
    const [hasSubscription, setHasSubscription] = useState<boolean>(true); // default true to avoid flash

    const handleLogout = () => {
        logout();
        toast("Signed out", "info");
        router.push("/login");
    };

    useEffect(() => {
        // Only fetch matches if profile is active (completion >= 30%)
        const loadingTimer = window.setTimeout(() => {
            setMatchesLoading(!!profile?.is_active);
        }, 0);

        if (profile?.is_active) {
            apiFetch<MatchRecommendation[]>("/matches/recommendations")
                .then(data => setMatches(data))
                .catch(err => toast(err.message || "Failed to load matches", "error"))
                .finally(() => setMatchesLoading(false));
        }

        // Fetch subscription
        apiFetch<{ id: number } | null>("/payments/my-subscription")
            .then(sub => setHasSubscription(!!sub))
            .catch(() => setHasSubscription(false));

        return () => {
            window.clearTimeout(loadingTimer);
        };

    }, [profile?.is_active, toast]);

    if (profileLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                <div className="animate-pulse text-lg font-serif text-primary-600">Loading Dashboard...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
            {/* Dashboard Header */}
            <header className="sticky top-0 w-full z-20 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/dashboard" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-gray-500 hidden sm:inline font-medium bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded-full">
                            {user ? `+${user.phone}` : ""}
                        </span>
                        <FamilyModeToggle />
                        <LanguageToggle />
                        <ThemeToggle />
                        <NotificationBell />
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={handleLogout}
                        >
                            {t("common.logout")}
                        </Button>
                    </div>
                </div>
            </header>

            <div className="container mx-auto px-4 py-8">
                <div className="grid md:grid-cols-4 gap-8">
                    {/* Sidebar Navigation */}
                    <aside className="space-y-4">
                        <Card className="p-4 flex flex-col gap-1 border-none shadow-sm bg-white/50 dark:bg-gray-900/50 backdrop-blur">
                            <Link href="/dashboard">
                                <Button variant="ghost" className="w-full justify-start text-primary-700 bg-primary-50 dark:bg-primary-900/20 font-semibold">
                                    <span className="mr-2">🏠</span> {t("common.dashboard")}
                                </Button>
                            </Link>
                            <Link href="/matches">
                                <Button variant="ghost" className="w-full justify-start hover:bg-gray-100 dark:hover:bg-gray-800">
                                    <span className="mr-2">💘</span> Daily Matches
                                </Button>
                            </Link>
                            <Link href="/chat">
                                <Button variant="ghost" className="w-full justify-start hover:bg-gray-100 dark:hover:bg-gray-800">
                                    <span className="mr-2">💬</span> Messages
                                </Button>
                            </Link>
                            <Link href="/search">
                                <Button variant="ghost" className="w-full justify-start hover:bg-gray-100 dark:hover:bg-gray-800">
                                    <span className="mr-2">🔍</span> {t("common.search")}
                                </Button>
                            </Link>
                            <div className="my-2 border-t border-gray-200 dark:border-gray-800" />
                            <Link href="/profile/edit">
                                <Button variant="ghost" className="w-full justify-start hover:bg-gray-100 dark:hover:bg-gray-800">
                                    <span className="mr-2">⚙️</span> Edit Profile
                                </Button>
                            </Link>
                            <Link href="/plans">
                                <Button variant="ghost" className="w-full justify-start text-gold-600 hover:bg-gold-50 dark:hover:bg-gold-900/20 font-medium">
                                    <span className="mr-2">👑</span> Upgrade Plan
                                </Button>
                            </Link>
                        </Card>
                    </aside>

                    {/* Main Content */}
                    <main className="md:col-span-3 space-y-8">
                        {!hasSubscription && (
                            <Card className="p-4 sm:p-6 bg-gradient-to-r from-gold-500 to-amber-500 text-white shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4 border-none">
                                <div>
                                    <h3 className="text-xl font-bold mb-1">Unlock Your 30-Day Premium Trial 👑</h3>
                                    <p className="text-amber-50">Get unlimited messaging, see contact details, and priority support.</p>
                                </div>
                                <Link href="/plans">
                                    <Button className="whitespace-nowrap bg-white text-amber-700 hover:bg-amber-50">
                                        Activate Now
                                    </Button>
                                </Link>
                            </Card>
                        )}

                        {/* Dynamic Progress Widget */}
                        <ProgressWidget />

                        {/* Quick Actions */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <Link href="/matches">
                                <Card className="p-4 text-center hover:bg-white dark:hover:bg-gray-800 transition-all hover:shadow-md h-full flex flex-col items-center justify-center gap-2 cursor-pointer border-transparent hover:border-primary-200 dark:hover:border-primary-800 bg-transparent">
                                    <div className="w-12 h-12 rounded-full bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center text-xl mb-1">
                                        💘
                                    </div>
                                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">Matches</span>
                                </Card>
                            </Link>
                            <Link href="/search">
                                <Card className="p-4 text-center hover:bg-white dark:hover:bg-gray-800 transition-all hover:shadow-md h-full flex flex-col items-center justify-center gap-2 cursor-pointer border-transparent hover:border-primary-200 dark:hover:border-primary-800 bg-transparent">
                                    <div className="w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-xl mb-1">
                                        🔍
                                    </div>
                                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{t("common.search")}</span>
                                </Card>
                            </Link>
                            <Link href="/plans">
                                <Card className="p-4 text-center hover:bg-white dark:hover:bg-gray-800 transition-all hover:shadow-md h-full flex flex-col items-center justify-center gap-2 cursor-pointer border-transparent hover:border-primary-200 dark:hover:border-primary-800 bg-transparent">
                                    <div className="w-12 h-12 rounded-full bg-gold-100 dark:bg-gold-900/30 flex items-center justify-center text-xl mb-1">
                                        👑
                                    </div>
                                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">Upgrade</span>
                                </Card>
                            </Link>
                            <Link href="/expert">
                                <Card className="p-4 text-center hover:bg-white dark:hover:bg-gray-800 transition-all hover:shadow-md h-full flex flex-col items-center justify-center gap-2 cursor-pointer border-transparent hover:border-primary-200 dark:hover:border-primary-800 bg-transparent">
                                    <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-xl mb-1">
                                        🔮
                                    </div>
                                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">Horoscope</span>
                                </Card>
                            </Link>
                        </div>

                        {/* Recent Matches */}
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xl font-serif font-bold text-gray-900 dark:text-gray-100">
                                    New Matches
                                </h3>
                                {profile?.is_active && matches.length > 0 && (
                                    <Link href="/matches" className="text-primary-600 hover:text-primary-700 text-sm font-medium hover:underline">
                                        View All &rarr;
                                    </Link>
                                )}
                            </div>

                            {matchesLoading ? (
                                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {[1, 2, 3].map(i => (
                                        <Card key={i} className="h-64 animate-pulse bg-gray-100 dark:bg-gray-800 border-none" />
                                    ))}
                                </div>
                            ) : !profile?.is_active ? (
                                <Card className="p-8 text-center text-gray-500 bg-gray-50 dark:bg-gray-900 border-dashed border-2">
                                    <div className="text-4xl mb-4">🔒</div>
                                    <h4 className="font-bold text-lg text-gray-700 dark:text-gray-300 mb-2">Matches are locked</h4>
                                    <p className="max-w-md mx-auto text-sm">
                                        You need a profile completion score of at least 30% to view match recommendations.
                                        Update your profile using the widget above to unlock this feature.
                                    </p>
                                </Card>
                            ) : matches.length === 0 ? (
                                <Card className="p-8 text-center text-gray-500 bg-gray-50 dark:bg-gray-900">
                                    <p>No new matches found today. Try expanding your search preferences!</p>
                                    <Link href="/search">
                                        <Button variant="outline" className="mt-4">Search Manually</Button>
                                    </Link>
                                </Card>
                            ) : (
                                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {matches.slice(0, 3).map(match => (
                                        <MatchCard key={match.profile.id} match={match} />
                                    ))}
                                </div>
                            )}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}

export default function DashboardPage() {
    return (
        <ProtectedRoute>
            <DashboardInner />
        </ProtectedRoute>
    );
}
