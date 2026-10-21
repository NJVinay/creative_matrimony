"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

interface OtpRequestOut {
    message: string;
    expires_in_seconds: number;
    dev_otp?: string | null;
}

interface OtpVerifyOut {
    access_token: string;
    refresh_token: string;
    is_new_user: boolean;
}

function RegisterForm() {
    const router = useRouter();
    const { toast } = useToast();
    const { refresh } = useAuth();
    const [phone, setPhone] = useState("");
    const [otp, setOtp] = useState("");
    const [stage, setStage] = useState<"phone" | "otp">("phone");
    const [devOtp, setDevOtp] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(0);

    useEffect(() => {
        if (countdown <= 0) return;
        const t = setTimeout(() => setCountdown(c => c - 1), 1000);
        return () => clearTimeout(t);
    }, [countdown]);

    const validPhone = /^\+?\d{10,15}$/.test(phone);

    const requestOtp = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!validPhone) {
            toast("Enter a valid phone number (10–15 digits).", "error");
            return;
        }
        setLoading(true);
        try {
            const res = await apiFetch<OtpRequestOut>("/auth/otp/request", {
                method: "POST",
                body: { phone },
                anonymous: true,
            });
            setDevOtp(res.dev_otp ?? null);
            setStage("otp");
            setCountdown(60);
            if (res.dev_otp) {
                toast(`OTP sent. (Dev OTP: ${res.dev_otp})`, "info");
            } else {
                toast("OTP sent to your phone.", "success");
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to send OTP";
            toast(msg, "error");
        } finally {
            setLoading(false);
        }
    };

    const verifyOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!/^\d{6}$/.test(otp)) {
            toast("Enter the 6-digit OTP.", "error");
            return;
        }
        setLoading(true);
        try {
            const res = await apiFetch<OtpVerifyOut>("/auth/otp/verify", {
                method: "POST",
                body: { phone, otp },
                anonymous: true,
            });
            // Tokens arrive as httpOnly cookies set by the backend. Load the user into
            // auth context first, or AuthGuard on the next page bounces to /login.
            await refresh();
            if (res.is_new_user) {
                toast("Welcome! Let's set up your profile.", "success");
                router.replace("/profile/create");
            } else {
                toast("You're already registered. Logging you in.", "info");
                router.replace("/dashboard");
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Invalid OTP";
            toast(msg, "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col">
            <header className="fixed top-0 w-full z-10 glass border-b border-white/20">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Link href="/" className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
                        Creative Matrimony
                    </Link>
                    <div className="flex items-center gap-3">
                        <LanguageToggle />
                        <ThemeToggle />
                    </div>
                </div>
            </header>

            <main className="flex-1 flex items-center justify-center pt-24 pb-12 px-4 bg-gradient-to-b from-primary-50 to-white dark:from-gray-950 dark:to-gray-900">
                <Card className="w-full max-w-md p-8 space-y-6">
                    <div className="text-center space-y-2">
                        <h1 className="text-3xl font-serif font-bold text-primary-700 dark:text-primary-400">
                            {stage === "phone" ? "Create Account" : "Verify Phone"}
                        </h1>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                            {stage === "phone"
                                ? "Join the Telugu-first matrimony community. Free to start."
                                : `Enter the 6-digit code sent to +${phone}.`}
                        </p>
                    </div>

                    {stage === "phone" ? (
                        <form onSubmit={requestOtp} className="space-y-4">
                            <div>
                                <label htmlFor="phone" className="text-sm font-medium block mb-1">
                                    Mobile Number
                                </label>
                                <div className="flex items-stretch">
                                    <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm text-gray-600">
                                        +
                                    </span>
                                    <Input
                                        id="phone"
                                        name="phone"
                                        type="tel"
                                        placeholder="9876543210"
                                        value={phone}
                                        onChange={e => setPhone(e.target.value.replace(/[^\d]/g, ""))}
                                        className="rounded-l-none"
                                        autoComplete="tel"
                                        required
                                    />
                                </div>
                            </div>
                            <Button type="submit" className="w-full" isLoading={loading}>
                                Send OTP
                            </Button>
                            <p className="text-center text-sm text-gray-600 dark:text-gray-400">
                                Already have an account?{" "}
                                <Link href="/login" className="text-primary-600 hover:underline font-medium">
                                    Sign in
                                </Link>
                            </p>
                        </form>
                    ) : (
                        <form onSubmit={verifyOtp} className="space-y-4">
                            <div>
                                <label htmlFor="otp" className="text-sm font-medium block mb-1">
                                    One-Time Password
                                </label>
                                <Input
                                    id="otp"
                                    name="otp"
                                    inputMode="numeric"
                                    maxLength={6}
                                    placeholder="000000"
                                    value={otp}
                                    onChange={e => setOtp(e.target.value.replace(/[^\d]/g, ""))}
                                    autoFocus
                                    required
                                />
                                {devOtp && (
                                    <p className="mt-2 text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-2 rounded">
                                        Dev OTP: <span className="font-mono font-bold">{devOtp}</span>
                                    </p>
                                )}
                            </div>
                            <Button type="submit" className="w-full" isLoading={loading}>
                                Verify & Create Account
                            </Button>
                            <div className="flex justify-between text-sm">
                                <button
                                    type="button"
                                    className="text-gray-600 hover:text-primary-600 disabled:opacity-50"
                                    disabled={countdown > 0 || loading}
                                    onClick={() => requestOtp()}
                                >
                                    {countdown > 0 ? `Resend in ${countdown}s` : "Resend OTP"}
                                </button>
                                <button
                                    type="button"
                                    className="text-gray-600 hover:text-primary-600"
                                    onClick={() => {
                                        setStage("phone");
                                        setOtp("");
                                        setDevOtp(null);
                                    }}
                                >
                                    Change number
                                </button>
                            </div>
                        </form>
                    )}

                    <p className="text-xs text-gray-500 text-center pt-2 border-t">
                        By continuing, you agree to our{" "}
                        <Link href="/legal/terms" className="text-primary-600 hover:underline">Terms</Link> and{" "}
                        <Link href="/legal/privacy" className="text-primary-600 hover:underline">Privacy Policy</Link>.
                    </p>
                </Card>
            </main>
        </div>
    );
}

export default function RegisterPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading…</div>}>
            <RegisterForm />
        </Suspense>
    );
}
