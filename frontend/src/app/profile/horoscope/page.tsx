"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import Image from "next/image";
import { staticUrl } from "@/lib/api";

// Hardcoded for MVP
const RASIS = [
    { value: "Mesha (Aries)", label: "Mesha (Aries)" },
    { value: "Vrishabha (Taurus)", label: "Vrishabha (Taurus)" },
    { value: "Mithuna (Gemini)", label: "Mithuna (Gemini)" },
    { value: "Karkataka (Cancer)", label: "Karkataka (Cancer)" },
    { value: "Simha (Leo)", label: "Simha (Leo)" },
    { value: "Kanya (Virgo)", label: "Kanya (Virgo)" },
    { value: "Tula (Libra)", label: "Tula (Libra)" },
    { value: "Vrischika (Scorpio)", label: "Vrischika (Scorpio)" },
    { value: "Dhanu (Sagittarius)", label: "Dhanu (Sagittarius)" },
    { value: "Makara (Capricorn)", label: "Makara (Capricorn)" },
    { value: "Kumbha (Aquarius)", label: "Kumbha (Aquarius)" },
    { value: "Meena (Pisces)", label: "Meena (Pisces)" },
];

const STARS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Arudra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshta", "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
];

export default function HoroscopePage() {
    const router = useRouter();
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    interface HoroscopeRecord {
        rasi?: string;
        star?: string;
        dosham?: boolean;
        time_of_birth?: string;
        place_of_birth?: string;
        chart_images?: string[];
    }

    const [data, setData] = useState<HoroscopeRecord>({});
    const [chartFile, setChartFile] = useState<File | null>(null);

    const fetchHoroscope = useCallback(async () => {
        try {
            // apiFetch throws on 404; treat empty as no record
            try {
                const json = await apiFetch<HoroscopeRecord>("/horoscope/me");
                setData(json);
            } catch (err: unknown) {
                if (err && typeof err === "object" && "status" in err && (err as { status?: number }).status === 404) setData({});
                else throw err;
            }
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchHoroscope();
    }, [fetchHoroscope]);

    const handleSave = async () => {
        setSaving(true);
        try {
            // 1. Update Details
            await apiFetch("/horoscope/me", {
                method: "PUT",
                body: {
                    rasi: data.rasi,
                    star: data.star,
                    dosham: data.dosham,
                    time_of_birth: data.time_of_birth,
                    place_of_birth: data.place_of_birth,
                },
            });

            // 2. Upload Chart if selected
            if (chartFile) {
                const formData = new FormData();
                formData.append("file", chartFile);
                await apiFetch("/horoscope/me/chart", {
                    method: "POST",
                    body: formData,
                });
            }

            toast("Horoscope updated!", "success");
            await fetchHoroscope();
        } catch (error) {
            const msg = error instanceof Error ? error.message : "Error saving";
            toast(msg, "error");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;

    return (
        <div className="container mx-auto px-4 py-8 max-w-2xl text-foreground">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                    My Horoscope (Jathakam)
                </h1>
                <Button variant="outline" onClick={() => router.push("/dashboard")}>
                    Back to Dashboard
                </Button>
            </div>

            <Card className="p-6 space-y-6">
                {/* Rasi & Star */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label htmlFor="rasi" className="text-sm font-medium">Rasi (Moon Sign)</label>
                        <select
                            id="rasi"
                            className="w-full p-2 rounded-md border border-gray-300 dark:border-gray-700 bg-background"
                            value={data.rasi || ""}
                            onChange={(e) => setData({ ...data, rasi: e.target.value })}
                        >
                            <option value="">Select Rasi</option>
                            {RASIS.map(r => (
                                <option key={r.value} value={r.value}>{r.label}</option>
                            ))}
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label htmlFor="star" className="text-sm font-medium">Star (Nakshatra)</label>
                        <select
                            id="star"
                            className="w-full p-2 rounded-md border border-gray-300 dark:border-gray-700 bg-background"
                            value={data.star || ""}
                            onChange={(e) => setData({ ...data, star: e.target.value })}
                        >
                            <option value="">Select Star</option>
                            {STARS.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Birth Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Time of Birth</label>
                        <Input
                            placeholder="e.g. 10:30 AM"
                            value={data.time_of_birth || ""}
                            onChange={(e) => setData({ ...data, time_of_birth: e.target.value })}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Place of Birth</label>
                        <Input
                            placeholder="City, District"
                            value={data.place_of_birth || ""}
                            onChange={(e) => setData({ ...data, place_of_birth: e.target.value })}
                        />
                    </div>
                </div>

                {/* Dosham */}
                <div className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        id="dosham"
                        checked={data.dosham || false}
                        onChange={(e) => setData({ ...data, dosham: e.target.checked })}
                        className="w-4 h-4"
                    />
                    <label htmlFor="dosham" className="text-sm font-medium">
                        I have Dosham (Manglik / Kuja / etc.)
                    </label>
                </div>

                {/* Chart Upload */}
                <div className="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-800">
                    <label htmlFor="chart-upload" className="text-sm font-medium block">Upload Horoscope Chart</label>
                    <div className="flex items-center gap-4">
                        <input
                            id="chart-upload"
                            type="file"
                            accept="image/*"
                            onChange={(e) => setChartFile(e.target.files?.[0] || null)}
                            className="text-sm"
                        />
                    </div>
                    {data.chart_images && data.chart_images.length > 0 && (
                        <div className="mt-4">
                            <p className="text-xs text-gray-500 mb-2">Current Chart:</p>
                            <Image
                                src={staticUrl(data.chart_images[data.chart_images.length - 1])}
                                alt="Horoscope Chart"
                                width={320}
                                height={240}
                                className="max-w-xs rounded-md border border-gray-200 dark:border-gray-700 shadow-sm"
                            />
                        </div>
                    )}
                </div>

                <div className="pt-4 flex justify-end">
                    <Button onClick={handleSave} disabled={saving} className="bg-primary-600 hover:bg-primary-700 text-white">
                        {saving ? "Saving..." : "Save Horoscope"}
                    </Button>
                </div>
            </Card>
        </div>
    );
}
