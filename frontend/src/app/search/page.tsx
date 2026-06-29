"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { apiFetch } from "@/lib/api";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { TaxonomySelect } from "@/components/ui/TaxonomySelect";
import { MatchCard } from "@/components/matches/MatchCard";
import { ProfilePublicOut } from "@/components/matches/MatchCard";

interface SearchResponse {
    results: ProfilePublicOut[];
    page: number;
    limit: number;
    total: number;
}

function SearchInner() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const { t } = useTranslation();

    const [profiles, setProfiles] = useState<ProfilePublicOut[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(false);

    // Initialize local filter state from URL params
    const initialFilters = {
        min_age: Number(searchParams.get("min_age")) || 18,
        max_age: Number(searchParams.get("max_age")) || 40,
        state: searchParams.get("state") || "",
        city_village: searchParams.get("city_village") || "",
        religion_id: searchParams.get("religion_id") ? Number(searchParams.get("religion_id")) : null,
        community_id: searchParams.get("community_id") ? Number(searchParams.get("community_id")) : null,
        subcaste_id: searchParams.get("subcaste_id") ? Number(searchParams.get("subcaste_id")) : null,
        page: Number(searchParams.get("page")) || 1,
    };

    const [filters, setFilters] = useState(initialFilters);

    // We also track "applied filters" independently of the input state 
    // so we only fetch when the user explicitly clicks "Search".
    // But since we want URL syncing, we can just fetch whenever URL params change.

    const fetchProfiles = useCallback(async () => {
        setIsLoading(true);
        try {
            const page = Number(searchParams.get("page")) || 1;
            const min_age = Number(searchParams.get("min_age")) || 18;
            const max_age = Number(searchParams.get("max_age")) || 40;
            const state = searchParams.get("state") || "";
            const city_village = searchParams.get("city_village") || "";
            const religion_id = searchParams.get("religion_id") ? Number(searchParams.get("religion_id")) : undefined;
            const community_id = searchParams.get("community_id") ? Number(searchParams.get("community_id")) : undefined;
            const subcaste_id = searchParams.get("subcaste_id") ? Number(searchParams.get("subcaste_id")) : undefined;

            const payload = {
                min_age,
                max_age,
                state: state || undefined,
                city_village: city_village || undefined,
                religion_id,
                community_id: community_id ? [community_id] : undefined,
                subcaste_id,
                page,
                limit: 12,
            };

            const data = await apiFetch<SearchResponse>("/search", {
                method: "POST",
                body: payload,
            });
            setProfiles(data.results);
            setTotal(data.total);
        } catch (err) {
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [searchParams]);

    // Fetch when URL params change
    useEffect(() => {
        fetchProfiles();
    }, [fetchProfiles]);

    // Apply filters updates URL
    const applyFilters = (overrides: Partial<typeof filters> = {}) => {
        const merged = { ...filters, ...overrides };
        const params = new URLSearchParams();
        if (merged.min_age !== 18) params.set("min_age", String(merged.min_age));
        if (merged.max_age !== 40) params.set("max_age", String(merged.max_age));
        if (merged.state) params.set("state", merged.state);
        if (merged.city_village) params.set("city_village", merged.city_village);
        if (merged.religion_id) params.set("religion_id", String(merged.religion_id));
        if (merged.community_id) params.set("community_id", String(merged.community_id));
        if (merged.subcaste_id) params.set("subcaste_id", String(merged.subcaste_id));

        // Reset to page 1 on new filter search
        const page = overrides.page || 1;
        if (page > 1) params.set("page", String(page));

        router.push(`${pathname}?${params.toString()}`);
    };

    const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFilters(prev => ({
            ...prev,
            [name]: name.includes("age") ? parseInt(value) || 0 : value
        }));
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            {/* Header */}
            <header className="sticky top-0 w-full z-20 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/dashboard" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-4">
                        <LanguageToggle />
                        <ThemeToggle />
                        <Link href="/dashboard">
                            <Button size="sm" variant="ghost">{t("common.dashboard")}</Button>
                        </Link>
                    </div>
                </div>
            </header>

            <div className="container mx-auto px-4 py-8 flex flex-col md:flex-row gap-8">
                {/* Filters Sidebar */}
                <aside className="w-full md:w-72 flex-shrink-0">
                    <Card className="sticky top-24 space-y-6 p-5">
                        <div className="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-3">
                            <h3 className="font-bold font-serif text-lg text-gray-900 dark:text-gray-100">
                                {t("common.search")} Filters
                            </h3>
                        </div>

                        <div className="space-y-5">
                            <div>
                                <label className="text-sm font-medium mb-1.5 block text-gray-700 dark:text-gray-300">Age Range</label>
                                <div className="flex gap-2 items-center">
                                    <Input
                                        type="number"
                                        name="min_age"
                                        value={filters.min_age}
                                        onChange={handleFilterChange}
                                        className="w-full text-center"
                                        min={18}
                                        max={99}
                                    />
                                    <span className="text-gray-400">to</span>
                                    <Input
                                        type="number"
                                        name="max_age"
                                        value={filters.max_age}
                                        onChange={handleFilterChange}
                                        className="w-full text-center"
                                        min={18}
                                        max={99}
                                    />
                                </div>
                            </div>

                            <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
                                <label className="text-sm font-bold mb-3 block text-gray-900 dark:text-gray-100">Community & Religion</label>
                                <TaxonomySelect
                                    value={{
                                        religion_id: filters.religion_id,
                                        community_id: filters.community_id,
                                        subcaste_id: filters.subcaste_id,
                                    }}
                                    onChange={(val) => setFilters(prev => ({ ...prev, ...val }))}
                                />
                            </div>

                            <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
                                <label className="text-sm font-bold mb-3 block text-gray-900 dark:text-gray-100">Location</label>
                                <div className="space-y-3">
                                    <div>
                                        <label className="text-xs font-medium mb-1 block text-gray-600 dark:text-gray-400">State</label>
                                        <Input
                                            name="state"
                                            value={filters.state}
                                            onChange={handleFilterChange}
                                            placeholder="e.g. Telangana"
                                        />
                                    </div>

                                    <div>
                                        <label className="text-xs font-medium mb-1 block text-gray-600 dark:text-gray-400">City / Village</label>
                                        <Input
                                            name="city_village"
                                            value={filters.city_village}
                                            onChange={handleFilterChange}
                                            placeholder="e.g. Hyderabad"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="pt-4 flex gap-2">
                                <Button
                                    onClick={() => {
                                        const reset = { min_age: 18, max_age: 40, state: "", city_village: "", religion_id: null, community_id: null, subcaste_id: null, page: 1 };
                                        setFilters(reset);
                                        // Update URL to empty
                                        router.push(pathname);
                                    }}
                                    variant="outline"
                                    className="flex-1"
                                >
                                    Reset
                                </Button>
                                <Button onClick={() => applyFilters({ page: 1 })} className="flex-1" isLoading={isLoading}>
                                    Apply
                                </Button>
                            </div>
                        </div>
                    </Card>
                </aside>

                {/* Results Grid */}
                <main className="flex-1 space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold font-serif">
                            {isLoading ? "Searching..." : `${total} profiles found`}
                        </h2>
                    </div>

                    {isLoading ? (
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[1, 2, 3, 4, 5, 6].map(i => (
                                <Card key={i} className="h-[350px] animate-pulse bg-gray-100 dark:bg-gray-800 border-none" />
                            ))}
                        </div>
                    ) : profiles.length > 0 ? (
                        <>
                            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                {profiles.map(profile => (
                                    <MatchCard key={profile.id} match={{ profile }} />
                                ))}
                            </div>

                            {/* Pagination Controls */}
                            {total > 12 && (
                                <div className="flex items-center justify-center gap-4 py-8 border-t border-gray-200 dark:border-gray-800 mt-8">
                                    <Button
                                        variant="outline"
                                        disabled={filters.page <= 1}
                                        onClick={() => {
                                            const newPage = filters.page - 1;
                                            setFilters(prev => ({ ...prev, page: newPage }));
                                            applyFilters({ page: newPage });
                                        }}
                                    >
                                        &larr; Previous
                                    </Button>
                                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                        Page {filters.page} of {Math.ceil(total / 12)}
                                    </span>
                                    <Button
                                        variant="outline"
                                        disabled={filters.page >= Math.ceil(total / 12)}
                                        onClick={() => {
                                            const newPage = filters.page + 1;
                                            setFilters(prev => ({ ...prev, page: newPage }));
                                            applyFilters({ page: newPage });
                                        }}
                                    >
                                        Next &rarr;
                                    </Button>
                                </div>
                            )}
                        </>
                    ) : (
                        <Card className="text-center py-20 bg-transparent border-dashed">
                            <div className="text-4xl mb-4">🔍</div>
                            <h3 className="text-lg font-bold text-gray-700 dark:text-gray-300 mb-2">No matches found</h3>
                            <p className="text-gray-500 max-w-md mx-auto mb-6">
                                We couldn&apos;t find any profiles matching your exact criteria. Try broadening your age range or clearing location filters.
                            </p>
                            <Button
                                variant="outline"
                                onClick={() => {
                                    router.push(pathname); // Clears URL params
                                }}
                            >
                                Clear All Filters
                            </Button>
                        </Card>
                    )}
                </main>
            </div>
        </div>
    );
}

export default function SearchPage() {
    return (
        <ProtectedRoute>
            <Suspense fallback={
                <div className="min-h-screen flex items-center justify-center">
                    <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
                </div>
            }>
                <SearchInner />
            </Suspense>
        </ProtectedRoute>
    );
}
