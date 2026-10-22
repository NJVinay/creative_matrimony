"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { AuthGuard } from "@/components/ui/AuthGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface Plan {
    id: number;
    name: string;
    price: number;
    currency: string;
    duration_days: number;
    features: string[];
}

interface Subscription {
    id: number;
    plan_id: number;
    is_active: boolean;
    end_date: string;
}

interface OrderResponse {
    order_id: string;
    amount: number;
    currency: string;
    key: string;
}

function PlansInner() {
    const { toast } = useToast();
    const router = useRouter();
    const [plans, setPlans] = useState<Plan[]>([]);
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [loading, setLoading] = useState(true);

    // Checkout State
    const [checkoutPlan, setCheckoutPlan] = useState<Plan | null>(null);
    const [isCheckingOut, setIsCheckingOut] = useState(false);
    const [isSimulating, setIsSimulating] = useState(false);

    const fetchInitialData = useCallback(async () => {
        try {
            const [plansData, subData] = await Promise.all([
                apiFetch<Plan[]>("/payments/plans"),
                apiFetch<Subscription | null>("/payments/my-subscription").catch(() => null)
            ]);
            setPlans(plansData);
            setSubscription(subData);
        } catch {
            toast("Failed to load plans", "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        void fetchInitialData();
    }, [fetchInitialData]);

    const startCheckout = async (plan: Plan) => {
        setIsCheckingOut(true);
        try {
            const orderRes = await apiFetch<{ order_id: string; amount: number; currency: string; key: string }>("/payments/create-order", {
                method: "POST",
                body: { plan_id: plan.id }
            });
            setCheckoutPlan({ ...plan, ...orderRes });
        } catch {
            toast("Failed to initiate checkout", "error");
        } finally {
            setIsCheckingOut(false);
        }
    };

    const simulatePayment = async () => {
        if (!checkoutPlan) return;
        setIsSimulating(true);
        try {
            const order_id = (checkoutPlan as Plan & Partial<OrderResponse>).order_id;
            const payment_id = `pay_mock_${Math.random().toString(36).substring(7)}`;

            // 1. Get Mock Signature from our backend
            const signRes = await apiFetch<{ signature: string }>("/payments/mock/sign", {
                method: "POST",
                body: { order_id, payment_id }
            });

            // 2. Verify Payment
            await apiFetch("/payments/verify", {
                method: "POST",
                body: { order_id, payment_id, signature: signRes.signature }
            });

            toast("Payment successful! You are now premium.", "success");
            setCheckoutPlan(null);
            router.push("/dashboard");
        } catch {
            toast("Payment simulation failed", "error");
        } finally {
            setIsSimulating(false);
        }
    };

    const activateTrial = async () => {
        setIsCheckingOut(true);
        try {
            await apiFetch("/payments/trial", { method: "POST" });
            toast("30-Day Premium Trial activated!", "success");
            router.push("/dashboard");
        } catch {
            toast("Failed to activate trial", "error");
            setIsCheckingOut(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col relative">
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
                    <h1 className="text-4xl font-serif font-bold text-gray-900 dark:text-white mb-4">Choose Your Plan</h1>
                    <p className="text-xl text-gray-600 dark:text-gray-400">Unlock premium features to find your perfect match faster.</p>
                </div>

                {loading ? (
                    <div className="text-center py-20">Loading plans...</div>
                ) : (
                    <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto items-center">
                        {/* Free Plan */}
                        <Card className="p-8 border-gray-200">
                            <h2 className="text-2xl font-bold mb-2">Basic Match</h2>
                            <div className="text-4xl font-bold mb-6">Free</div>
                            <ul className="space-y-4 mb-8 text-gray-600 dark:text-gray-400">
                                <li className="flex items-center gap-2">✅ Create Profile & Upload Photos</li>
                                <li className="flex items-center gap-2">✅ Browse Matches</li>
                                <li className="flex items-center gap-2">❌ View Contact Details</li>
                                <li className="flex items-center gap-2">❌ Send Direct Messages</li>
                            </ul>
                            {!subscription ? (
                                <Button className="w-full" disabled>Current Plan</Button>
                            ) : (
                                <Button className="w-full" variant="outline" disabled>Downgrade to Free</Button>
                            )}
                        </Card>

                        {/* Premium Plans */}
                        {plans.map(plan => (
                            <Card key={plan.id} className="p-8 border-primary-500 dark:border-primary-500 shadow-xl relative scale-105">
                                <div className="absolute top-0 right-0 bg-primary-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg">
                                    RECOMMENDED
                                </div>
                                <h2 className="text-2xl font-bold mb-2 text-primary-700 dark:text-primary-400">{plan.name}</h2>
                                <div className="text-4xl font-bold mb-6">
                                    {plan.currency === "INR" ? "₹" : ""}{plan.price}
                                    <span className="text-lg font-normal text-gray-500"> / {plan.duration_days} days</span>
                                </div>
                                <ul className="space-y-4 mb-8">
                                    {plan.features.map((f, idx) => (
                                        <li key={idx} className="flex items-center gap-2 font-medium">
                                            ✅ {f}
                                        </li>
                                    ))}
                                    <li className="flex items-center gap-2 font-medium">✅ See Match Scores & Reasons</li>
                                </ul>

                                {subscription?.plan_id === plan.id ? (
                                    <div className="text-center text-green-600 font-bold p-2 bg-green-50 rounded-lg">
                                        Active until {new Date(subscription.end_date).toLocaleDateString()}
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <Button
                                            className="w-full h-12 text-lg"
                                            onClick={() => startCheckout(plan)}
                                            isLoading={isCheckingOut}
                                        >
                                            Subscribe Now
                                        </Button>
                                        {!subscription && (
                                            <Button
                                                variant="outline"
                                                className="w-full h-12 text-primary-600 border-primary-200 hover:bg-primary-50"
                                                onClick={activateTrial}
                                                isLoading={isCheckingOut}
                                            >
                                                Start 30-Day Free Trial
                                            </Button>
                                        )}
                                    </div>
                                )}
                            </Card>
                        ))}
                    </div>
                )}
            </main>

            {/* Mock Checkout Modal overlay */}
            {checkoutPlan && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <Card className="w-full max-w-md p-6 bg-white dark:bg-gray-900 shadow-2xl relative">
                        <button
                            className="absolute top-4 right-4 text-gray-400 hover:text-gray-800 dark:hover:text-white"
                            onClick={() => setCheckoutPlan(null)}
                            disabled={isSimulating}
                        >
                            ✕
                        </button>
                        <div className="text-center mb-6">
                            <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
                                💳
                            </div>
                            <h3 className="text-xl font-bold">Mock Payment Gateway</h3>
                            <p className="text-sm text-gray-500">Secure checkout simulation</p>
                        </div>

                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 mb-6">
                            <div className="flex justify-between mb-2">
                                <span>Plan</span>
                                <span className="font-bold">{checkoutPlan.name}</span>
                            </div>
                            <div className="flex justify-between mb-2">
                                <span>Order ID</span>
                                <span className="font-mono text-xs">{(checkoutPlan as Plan & Partial<OrderResponse>).order_id}</span>
                            </div>
                            <div className="flex justify-between pt-2 border-t border-gray-200 dark:border-gray-700 font-bold text-lg">
                                <span>Total Payable</span>
                                <span>{checkoutPlan.currency === 'INR' ? '₹' : ''}{checkoutPlan.price}</span>
                            </div>
                        </div>

                        <Button
                            className="w-full h-12 bg-green-600 hover:bg-green-700 text-white"
                            onClick={simulatePayment}
                            isLoading={isSimulating}
                        >
                            Simulate Successful Payment
                        </Button>
                        <p className="text-xs text-center text-gray-400 mt-4">
                            In a real app, this would open Razorpay/Stripe.
                        </p>
                    </Card>
                </div>
            )}
        </div>
    );
}

export default function PlansPage() {
    return (
        <AuthGuard>
            <PlansInner />
        </AuthGuard>
    );
}
