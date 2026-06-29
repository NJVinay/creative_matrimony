"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

const CATEGORIES = [
    { value: "matchmaking", label: "Personalized Matchmaking" },
    { value: "astrology", label: "Astrology Consultation" },
    { value: "profile_writing", label: "Profile Writing Assistance" },
    { value: "other", label: "Other Support" },
];

interface ExpertInquiry {
    id: number;
    category: string;
    message: string;
    preferred_contact_time: string | null;
    is_resolved: boolean;
    created_at: string;
}

export default function ExpertPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [inquiries, setInquiries] = useState<ExpertInquiry[]>([]);

    // Form
    const [category, setCategory] = useState("matchmaking");
    const [message, setMessage] = useState("");
    const [preferredTime, setPreferredTime] = useState("");

    useEffect(() => {
        fetchInquiries();
    }, []);

    const fetchInquiries = async () => {
        try {
            const data = await apiFetch<ExpertInquiry[]>("/expert/inquiries");
            setInquiries(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await apiFetch("/expert/inquiry", {
                method: "POST",
                body: {
                    category,
                    message,
                    preferred_contact_time: preferredTime,
                },
            });
            toast("Inquiry submitted! Our expert will contact you soon.", "success");
            setMessage("");
            setPreferredTime("");
            fetchInquiries();
        } catch (error) {
            const msg = error instanceof Error ? error.message : "Submission failed";
            toast(msg, "error");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading...</div>;

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl text-foreground">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                    Expert Services
                </h1>
                <Button variant="outline" onClick={() => router.push("/dashboard")}>
                    Back to Dashboard
                </Button>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
                {/* Form */}
                <Card className="p-6">
                    <h2 className="text-xl font-bold mb-4">Request Consultation</h2>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label htmlFor="category" className="text-sm font-medium">I need help with</label>
                            <select
                                id="category"
                                className="w-full p-2 rounded-md border bg-background"
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                            >
                                {CATEGORIES.map(c => (
                                    <option key={c.value} value={c.value}>{c.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label htmlFor="message" className="text-sm font-medium">Message / Details</label>
                            <textarea
                                id="message"
                                className="w-full p-2 rounded-md border bg-background min-h-[100px]"
                                placeholder="Describe what you are looking for..."
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                required
                            />
                        </div>

                        <div className="space-y-2">
                            <label htmlFor="time" className="text-sm font-medium">Preferred Contact Time (Optional)</label>
                            <Input
                                id="time"
                                placeholder="e.g. Weekends, After 6 PM"
                                value={preferredTime}
                                onChange={(e) => setPreferredTime(e.target.value)}
                            />
                        </div>

                        <Button type="submit" disabled={submitting} className="w-full bg-primary-600 hover:bg-primary-700 text-white">
                            {submitting ? "Submitting..." : "Submit Request"}
                        </Button>
                    </form>
                </Card>

                {/* Status / History */}
                <div className="space-y-6">
                    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800">
                        <h3 className="font-bold text-blue-800 dark:text-blue-300 mb-2">Why use Expert Services?</h3>
                        <ul className="list-disc list-inside space-y-2 text-sm text-blue-700 dark:text-blue-400">
                            <li>Get personalized match recommendations</li>
                            <li>Professional profile writing to attract better matches</li>
                            <li>Astrological compatibility analysis</li>
                            <li>Dedicated relationship manager support</li>
                        </ul>
                    </Card>

                    <div>
                        <h3 className="font-bold mb-4">Past Inquiries</h3>
                        {inquiries.length === 0 ? (
                            <p className="text-gray-500 text-sm">No past inquiries.</p>
                        ) : (
                            <div className="space-y-3">
                                {inquiries.map(inq => (
                                    <Card key={inq.id} className="p-4">
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="inline-block px-2 py-1 rounded-full bg-primary-100 text-primary-800 text-xs font-bold capitalize">
                                                {inq.category.replace("_", " ")}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {new Date(inq.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <p className="text-sm mb-2">{inq.message}</p>
                                        <div className="text-xs text-gray-500">
                                            Status: <span className={inq.is_resolved ? "text-green-600" : "text-orange-600"}>
                                                {inq.is_resolved ? "Resolved" : "Pending"}
                                            </span>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
