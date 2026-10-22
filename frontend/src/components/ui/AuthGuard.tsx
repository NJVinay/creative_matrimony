"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/useAuth";

interface AuthGuardProps {
    children: React.ReactNode;
    /** If true, render children even while loading (skeleton fallback recommended) */
    showFallback?: boolean;
    /** Path to redirect to when not authenticated. Default: /login */
    redirectTo?: string;
}

/**
 * Client-side route guard. Redirects unauthenticated visitors to /login,
 * preserving the current URL via ?redirect=...
 */
export function AuthGuard({ children, redirectTo = "/login" }: AuthGuardProps) {
    const { isLoading, isAuthenticated } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (isLoading) return;
        if (!isAuthenticated) {
            const next = encodeURIComponent((pathname || "/") + window.location.search);
            router.replace(`${redirectTo}?redirect=${next}`);
        }
    }, [isLoading, isAuthenticated, pathname, redirectTo, router]);

    if (isLoading) {
        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!isAuthenticated) return null;

    return <>{children}</>;
}
