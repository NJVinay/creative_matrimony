import Link from "next/link";
import { Card } from "@/components/ui/Card";

export interface ProfilePublicOut {
    id: number;
    display_name: string;
    gender: string;
    age: number;
    bio: string | null;
    city_village: string | null;
    state: string | null;
    religion_id: number | null;
    community_id: number | null;
    education_level: string | null;
    occupation_category: string | null;
    marital_status: string | null;
    is_verified: boolean;
    completion_pct: number;
}

export interface MatchRecommendation {
    profile: ProfilePublicOut;
    score?: number;
}

export function MatchCard({ match }: { match: MatchRecommendation }) {
    const { profile, score } = match;

    return (
        <Card className="group relative overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-xl border-gray-200 dark:border-gray-800 hover:border-primary-300 dark:hover:border-primary-700 bg-white dark:bg-gray-900">
            {/* Avatar placeholder / background */}
            <div className="h-32 bg-gradient-to-r from-primary-200 to-primary-300 dark:from-gray-800 dark:to-gray-700 relative">
                <div className="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors" />
                {score !== undefined && (
                    <div className="absolute top-2 right-2 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm px-2 py-1 rounded text-xs font-bold text-primary-700 dark:text-primary-400 shadow-sm border border-white/20">
                        {Math.round(score)}% Match
                    </div>
                )}
            </div>

            <div className="p-4 relative">
                {/* Profile Picture Circle */}
                <div className="absolute -top-10 left-4 w-16 h-16 rounded-full border-4 border-white dark:border-gray-900 bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden shadow-sm">
                    <span className="text-2xl">
                        {profile.gender === "female" ? "👩" : "👨"}
                    </span>
                </div>

                <div className="mt-8 space-y-2">
                    <div className="flex items-center gap-2">
                        <h3 className="font-bold font-serif text-lg text-gray-900 dark:text-gray-100 truncate">
                            {profile.display_name}
                        </h3>
                        {profile.is_verified && (
                            <span className="text-blue-500" title="Verified">✓</span>
                        )}
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-400">
                        <span className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                            {profile.age} yrs
                        </span>
                        {(profile.city_village || profile.state) && (
                            <span className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate max-w-[120px]">
                                {profile.city_village}{profile.city_village && profile.state ? ", " : ""}{profile.state}
                            </span>
                        )}
                        {profile.education_level && (
                            <span className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate max-w-[120px]">
                                {profile.education_level}
                            </span>
                        )}
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                    <Link href={`/profile/${profile.id}`}>
                        <button className="w-full text-center text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors">
                            View Profile
                        </button>
                    </Link>
                </div>
            </div>
        </Card>
    );
}
