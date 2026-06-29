"use client";

import Link from "next/link";
import { useProfile } from "@/lib/useProfile";
import { Card } from "@/components/ui/Card";

export function ProgressWidget() {
    const { profile, isLoading } = useProfile();

    if (isLoading || !profile) return null;

    const { completion_pct } = profile;
    const isComplete = completion_pct >= 100;

    // Determine missing fields to prompt the user
    const missingActions = [];
    if (!profile.religion_id) missingActions.push({ label: "Add Religion", path: "/profile/edit", pct: "+10%" });
    if (!profile.education_level) missingActions.push({ label: "Add Education", path: "/profile/edit", pct: "+10%" });
    if (!profile.bio) missingActions.push({ label: "Write a Bio", path: "/profile/edit", pct: "+15%" });
    if (!profile.marital_status) missingActions.push({ label: "Marital Status", path: "/profile/edit", pct: "+5%" });

    return (
        <Card className="bg-gradient-to-br from-primary-50 to-primary-100 dark:from-gray-900 dark:to-primary-950/20 p-6 relative overflow-hidden border-primary-200 dark:border-primary-900/50">
            <div className="relative z-10 flex flex-col md:flex-row gap-8 items-center">
                {/* Circular Progress */}
                <div className="relative w-32 h-32 flex-shrink-0 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                        <path
                            className="text-white dark:text-gray-800"
                            strokeWidth="3"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <path
                            className="text-primary-600 dark:text-primary-500 transition-all duration-1000 ease-out"
                            strokeDasharray={`${completion_pct}, 100`}
                            strokeWidth="3"
                            strokeLinecap="round"
                            stroke="currentColor"
                            fill="none"
                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                    </svg>
                    <div className="absolute flex flex-col items-center justify-center">
                        <span className="text-2xl font-bold text-primary-700 dark:text-primary-400">{completion_pct}%</span>
                    </div>
                </div>

                {/* Text Content & Actions */}
                <div className="flex-1 text-center md:text-left space-y-4">
                    <div>
                        <h2 className="text-2xl font-bold font-serif text-gray-900 dark:text-gray-100 mb-2">
                            {isComplete ? "Your profile is complete! 🎉" : "Complete your profile"}
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400 text-sm max-w-lg">
                            {isComplete
                                ? "You have unlocked all features and maximum visibility."
                                : "Profiles with higher completion percentages receive up to 5x more matches. Complete these missing details:"
                            }
                        </p>
                    </div>

                    {!isComplete && missingActions.length > 0 && (
                        <div className="flex flex-wrap gap-3 justify-center md:justify-start">
                            {missingActions.slice(0, 3).map((action, idx) => (
                                <Link key={idx} href={action.path}>
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-gray-800 border border-primary-200 dark:border-primary-800 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-primary-50 dark:hover:bg-gray-700 transition-colors shadow-sm cursor-pointer">
                                        {action.label}
                                        <span className="text-primary-600 dark:text-primary-400 font-bold">{action.pct}</span>
                                    </span>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Decorative background circle */}
            <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-white/40 dark:bg-primary-900/10 rounded-full blur-3xl pointer-events-none" />
        </Card>
    );
}
