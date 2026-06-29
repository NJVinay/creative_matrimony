"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";

export default function LoginPage() {
    const { t } = useTranslation();
    const router = useRouter();

    const [step, setStep] = useState<"phone" | "otp">("phone");
    const [phone, setPhone] = useState("");
    const [otp, setOtp] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [otpSentMsg, setOtpSentMsg] = useState("");

    const handleSendOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        // Call backend API
        try {
            const res = await fetch("http://localhost:8000/api/auth/otp/request", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone }),
            });

            const data = await res.json();

            if (res.ok) {
                setStep("otp");
                if (data.dev_otp) {
                    console.log("DEV OTP:", data.dev_otp);
                    setOtpSentMsg(`DEV MODE: Your OTP is ${data.dev_otp}`);
                }
            } else {
                alert(data.detail || "Error sending OTP");
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to server");
        } finally {
            setIsLoading(false);
        }
    };

    const handleVerifyOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const res = await fetch("http://localhost:8000/api/auth/otp/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone, otp }),
            });

            const data = await res.json();

            if (res.ok) {
                // Auth tokens are set via httpOnly cookies by the backend
                
                // Redirect logic
                if (data.is_new_user) {
                    router.push("/onboarding");
                } else {
                    router.push("/dashboard");
                }
            } else {
                alert(data.detail || "Invalid OTP");
            }
        } catch (err) {
            console.error(err);
            alert("Verification failed");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-primary-50 dark:bg-gray-950 p-4">
            <div className="absolute top-4 right-4 flex gap-2">
                <LanguageToggle />
                <ThemeToggle />
            </div>

            <Card className="w-full max-w-md" glass>
                <div className="text-center mb-8">
                    <Link href="/" className="text-3xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <p className="text-gray-600 dark:text-gray-300 mt-2">
                        {t("hero.subtitle")}
                    </p>
                </div>

                {step === "phone" ? (
                    <form onSubmit={handleSendOtp} className="space-y-6">
                        <Input
                            label={t("auth.mobile_label")}
                            type="tel"
                            placeholder="+91 98765 43210"
                            value={phone}
                            onChange={(e) => setPhone(e.target.value)}
                            required
                            className="font-mono"
                        />
                        <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
                            {t("auth.send_otp")}
                        </Button>
                    </form>
                ) : (
                    <form onSubmit={handleVerifyOtp} className="space-y-6">
                        <div className="text-center">
                            <p className="text-sm text-gray-500 mb-4">
                                OTP sent to <span className="font-mono font-bold">{phone}</span>
                                <button
                                    type="button"
                                    onClick={() => setStep("phone")}
                                    className="ml-2 text-primary-600 hover:underline"
                                >
                                    Change
                                </button>
                            </p>
                            {otpSentMsg && (
                                <div className="mb-4 p-2 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-200">
                                    {otpSentMsg}
                                </div>
                            )}
                        </div>

                        <Input
                            label={t("auth.otp_label")}
                            type="text"
                            placeholder="123456"
                            value={otp}
                            onChange={(e) => setOtp(e.target.value)}
                            maxLength={6}
                            className="font-mono text-center tracking-[1em] text-lg"
                            autoFocus
                            required
                        />

                        <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
                            {t("auth.verify")}
                        </Button>

                        <div className="text-center mt-4">
                            <button
                                type="button"
                                className="text-sm text-gray-500 hover:text-primary-600"
                                onClick={() => setStep("phone")} // In real app, resend logic
                            >
                                {t("auth.resend")}
                            </button>
                        </div>
                    </form>
                )}
            </Card>
        </div>
    );
}
