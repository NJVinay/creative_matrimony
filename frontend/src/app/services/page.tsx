"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { AuthGuard } from "@/components/ui/AuthGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

interface ServiceData {
    category: "matchmaking" | "astrology" | "profile_writing" | "other";
    message: string;
    preferred_contact_time?: string;
}

function ServicesInner() {
    const { toast } = useToast();
    const [selectedService, setSelectedService] = useState<ServiceData["category"] | null>(null);
    const [formData, setFormData] = useState<Partial<ServiceData>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    const services = [
        {
            id: "astrology",
            title: "Astrology Consultation",
            description: "Get your horoscope analyzed by our expert astrologers. We provide deep compatibility reports and guidance on auspicious timings.",
            icon: "⭐"
        },
        {
            id: "matchmaking",
            title: "VIP Matchmaking Concierge",
            description: "Let our dedicated matchmakers find the perfect partner for you. We handle the searching, shortlisting, and initial conversations.",
            icon: "🤝"
        },
        {
            id: "profile_writing",
            title: "Profile Makeover",
            description: "Struggling to get matches? Our writers will revamp your bio and select your best photos to maximize your profile's appeal.",
            icon: "✍️"
        }
    ];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedService || !formData.message) return;

        setIsSubmitting(true);
        try {
            await apiFetch("/expert/inquiry", {
                method: "POST",
                body: {
                    category: selectedService,
                    message: formData.message,
                    preferred_contact_time: formData.preferred_contact_time || undefined
                }
            });
            setIsSuccess(true);
            toast("Inquiry submitted successfully", "success");
        } catch {
            toast("Failed to submit inquiry", "error");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
            <header className="sticky top-0 w-full z-10 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/dashboard" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-4">
                        <Link href="/dashboard" className="text-sm font-medium hover:text-primary-600">Dashboard</Link>
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <main className="container mx-auto px-4 py-12 max-w-5xl flex-1">
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-serif font-bold text-gray-900 dark:text-white mb-4">Expert Services</h1>
                    <p className="text-xl text-gray-600 dark:text-gray-400">Premium assistance to fast-track your partner search.</p>
                </div>

                {isSuccess ? (
                    <Card className="p-12 text-center max-w-2xl mx-auto border-green-200 bg-green-50 dark:bg-green-900/10">
                        <div className="text-5xl mb-4">✅</div>
                        <h2 className="text-2xl font-bold text-green-800 dark:text-green-300 mb-2">Inquiry Received</h2>
                        <p className="text-green-700 dark:text-green-400 mb-6">
                            Thank you! Our expert team will review your request and contact you at your preferred time.
                        </p>
                        <Button onClick={() => { setIsSuccess(false); setSelectedService(null); }}>
                            Book Another Service
                        </Button>
                    </Card>
                ) : !selectedService ? (
                    <div className="grid md:grid-cols-3 gap-8">
                        {services.map(s => (
                            <Card key={s.id} className="p-6 flex flex-col hover:shadow-xl transition-shadow cursor-pointer border-t-4 border-t-primary-500" onClick={() => setSelectedService(s.id as ServiceData["category"])}>
                                <div className="text-4xl mb-4">{s.icon}</div>
                                <h3 className="text-xl font-bold mb-3">{s.title}</h3>
                                <p className="text-gray-600 dark:text-gray-400 mb-6 flex-1">{s.description}</p>
                                <Button className="w-full">Inquire Now</Button>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <Card className="p-8 max-w-2xl mx-auto relative overflow-hidden">
                        <button
                            onClick={() => setSelectedService(null)}
                            className="absolute top-4 right-4 text-gray-500 hover:text-gray-800 dark:hover:text-white"
                        >
                            ✕ Cancel
                        </button>

                        <h2 className="text-2xl font-bold mb-2">Book: {services.find(s => s.id === selectedService)?.title}</h2>
                        <p className="text-gray-500 mb-6">Please provide some details so our experts can prepare for your consultation.</p>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">How can we help you?</label>
                                <textarea
                                    required
                                    rows={4}
                                    value={formData.message || ""}
                                    onChange={e => setFormData({ ...formData, message: e.target.value })}
                                    className="w-full px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                                    placeholder="Briefly describe what you are looking for..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Preferred Contact Time (Optional)</label>
                                <Input
                                    type="text"
                                    value={formData.preferred_contact_time || ""}
                                    onChange={e => setFormData({ ...formData, preferred_contact_time: e.target.value })}
                                    placeholder="e.g. Weekdays after 6 PM, Sunday mornings"
                                />
                            </div>
                            <Button type="submit" isLoading={isSubmitting} className="w-full text-lg h-12 mt-4">
                                Submit Request
                            </Button>
                        </form>
                    </Card>
                )}
            </main>
        </div>
    );
}

export default function ServicesPage() {
    return (
        <AuthGuard>
            <ServicesInner />
        </AuthGuard>
    );
}
