"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";

export interface ProfileOut {
    id: number;
    user_id: number;
    profile_mode: string;
    guardian_relationship: string | null;
    display_name: string;
    gender: string;
    date_of_birth: string;
    bio: string | null;
    city_village: string | null;
    state: string | null;
    country: string;
    religion_id: number | null;
    community_id: number | null;
    subcaste_id: number | null;
    education_level: string | null;
    occupation_category: string | null;
    marital_status: string | null;
    completion_pct: number;
    is_active: boolean;
    visibility: string;
    photo_blur_until_mutual: boolean;
    created_at: string;
}

interface ProfileContextType {
    profile: ProfileOut | null;
    isLoading: boolean;
    error: string | null;
    refreshProfile: () => Promise<void>;
}

const ProfileContext = createContext<ProfileContextType | undefined>(undefined);

export function ProfileProvider({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const [profile, setProfile] = useState<ProfileOut | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refreshProfile = useCallback(async () => {
        if (!isAuthenticated) {
            setProfile(null);
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            const data = await apiFetch<ProfileOut>("/profiles/me");
            setProfile(data);
        } catch (err: unknown) {
            if (err && typeof err === "object" && "status" in err && (err as { status?: number }).status === 404) {
                setProfile(null);
            } else {
                setError(err instanceof Error ? err.message : "Failed to fetch profile");
            }
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated]);

    useEffect(() => {
        if (!authLoading) {
            void refreshProfile();
        }
    }, [authLoading, refreshProfile]);

    return (
        <ProfileContext.Provider value={{ profile, isLoading, error, refreshProfile }}>
            {children}
        </ProfileContext.Provider>
    );
}

export function useProfile() {
    const context = useContext(ProfileContext);
    if (!context) {
        throw new Error("useProfile must be used within a ProfileProvider");
    }
    return context;
}