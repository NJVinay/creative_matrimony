"use client";

import { useEffect } from "react";
import { I18nProvider } from "@/lib/i18n";
import { ToastProvider } from "@/components/ui/Toast";
import { AuthProvider } from "@/lib/useAuth";
import { ProfileProvider } from "@/lib/useProfile";
import { FamilyModeProvider } from "@/lib/useFamilyMode";

export function Providers({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        // Init theme
        const theme = localStorage.getItem("theme");
        if (theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
            document.documentElement.classList.add("dark");
        } else {
            document.documentElement.classList.remove("dark");
        }
    }, []);

    return (
        <AuthProvider>
            <ProfileProvider>
                <I18nProvider>
                    <FamilyModeProvider>
                        <ToastProvider>
                            {children}
                        </ToastProvider>
                    </FamilyModeProvider>
                </I18nProvider>
            </ProfileProvider>
        </AuthProvider>
    );
}
