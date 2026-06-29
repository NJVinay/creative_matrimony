"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Religion {
    id: number;
    name_en: string;
    name_te?: string | null;
}

interface Community {
    id: number;
    name_en: string;
    name_te?: string | null;
    religion_id: number;
    language_group_id?: number | null;
}

interface SubCaste {
    id: number;
    name_en: string;
    name_te?: string | null;
    community_id: number;
}

interface TaxonomySelectProps {
    /** Currently selected IDs */
    value: {
        religion_id?: number | null;
        community_id?: number | null;
        subcaste_id?: number | null;
    };
    /** Called when selection changes */
    onChange: (next: { religion_id?: number | null; community_id?: number | null; subcaste_id?: number | null }) => void;
    /** Optional: pre-load all on mount to avoid cascade waterfall */
    preloadAll?: boolean;
    /** UI language for labels */
    language?: "en" | "te";
    /** Disabled state */
    disabled?: boolean;
}

/**
 * Cascading Religion → Community → SubCaste dropdown component.
 * Fetches communities when a religion is selected, subcastes when a community is selected.
 */
export function TaxonomySelect({
    value,
    onChange,
    preloadAll = false,
    language = "en",
    disabled = false,
}: TaxonomySelectProps) {
    const [religions, setReligions] = useState<Religion[]>([]);
    const [communities, setCommunities] = useState<Community[]>([]);
    const [subcastes, setSubcastes] = useState<SubCaste[]>([]);
    const [loading, setLoading] = useState(false);

    const label = (item: { name_en: string; name_te?: string | null }) =>
        language === "te" && item.name_te ? item.name_te : item.name_en;

    // Load religions on mount
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const list = await apiFetch<Religion[]>("/taxonomy/religions");
                if (!cancelled) setReligions(list);
            } catch (err) {
                console.error("Failed to load religions:", err);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    // Load communities when religion changes
    useEffect(() => {
        if (!value.religion_id) {
            setCommunities([]);
            return;
        }
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const list = await apiFetch<Community[]>(
                    `/taxonomy/communities?religion_id=${value.religion_id}`
                );
                if (!cancelled) setCommunities(list);
            } catch (err) {
                console.error("Failed to load communities:", err);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [value.religion_id]);

    // Load subcastes when community changes
    useEffect(() => {
        if (!value.community_id) {
            setSubcastes([]);
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const list = await apiFetch<SubCaste[]>(
                    `/taxonomy/subcastes?community_id=${value.community_id}`
                );
                if (!cancelled) setSubcastes(list);
            } catch (err) {
                console.error("Failed to load subcastes:", err);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [value.community_id]);

    // Optional pre-load (skip cascade for default-state UI)
    useEffect(() => {
        if (preloadAll && religions.length && !communities.length) {
            // No-op: still respect cascade to keep semantics simple
        }
    }, [preloadAll, religions, communities.length]);

    return (
        <div className="space-y-3">
            <div>
                <label className="text-sm font-medium block mb-1">Religion</label>
                <select
                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
                    value={value.religion_id ?? ""}
                    onChange={e => {
                        const id = e.target.value ? Number(e.target.value) : null;
                        onChange({ religion_id: id, community_id: null, subcaste_id: null });
                    }}
                    disabled={disabled}
                >
                    <option value="">— Select Religion —</option>
                    {religions.map(r => (
                        <option key={r.id} value={r.id}>
                            {label(r)}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label className="text-sm font-medium block mb-1">Community</label>
                <select
                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm disabled:opacity-50"
                    value={value.community_id ?? ""}
                    onChange={e => {
                        const id = e.target.value ? Number(e.target.value) : null;
                        onChange({ ...value, community_id: id, subcaste_id: null });
                    }}
                    disabled={disabled || !value.religion_id || loading}
                >
                    <option value="">
                        {loading
                            ? "Loading..."
                            : !value.religion_id
                                ? "Select a religion first"
                                : "— Select Community —"}
                    </option>
                    {communities.map(c => (
                        <option key={c.id} value={c.id}>
                            {label(c)}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label className="text-sm font-medium block mb-1">Sub-Caste</label>
                <select
                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm disabled:opacity-50"
                    value={value.subcaste_id ?? ""}
                    onChange={e => {
                        const id = e.target.value ? Number(e.target.value) : null;
                        onChange({ ...value, subcaste_id: id });
                    }}
                    disabled={disabled || !value.community_id}
                >
                    <option value="">
                        {!value.community_id
                            ? "Select a community first"
                            : "— Select Sub-Caste (optional) —"}
                    </option>
                    {subcastes.map(s => (
                        <option key={s.id} value={s.id}>
                            {label(s)}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}
