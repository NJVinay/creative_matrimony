"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface AuthUser {
    id: number;
    phone: string;
    role: string;
    is_verified: boolean;
    is_banned: boolean;
}

interface MeResponse extends AuthUser {
    email?: string | null;
}

export interface AuthContextType {
    user: AuthUser | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    refresh: () => Promise<AuthUser | null>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);

    const refresh = useCallback(async (): Promise<AuthUser | null> => {
        try {
            const me = await apiFetch<MeResponse>("/auth/me");
            const nextUser: AuthUser = {
                id: me.id,
                phone: me.phone,
                role: me.role,
                is_verified: me.is_verified,
                is_banned: me.is_banned,
            };
            setUser(nextUser);
            return nextUser;
        } catch {
            setUser(null);
            return null;
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    const logout = useCallback(() => {
        apiFetch("/auth/logout", { method: "POST" }).catch(() => {});
        setUser(null);
    }, []);

    const value = {
        user,
        isLoading,
        isAuthenticated: !!user,
        refresh,
        logout,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}