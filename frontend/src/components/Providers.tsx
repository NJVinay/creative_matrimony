"use client";

import { I18nProvider } from "@/lib/i18n";
import { ToastProvider } from "@/components/ui/Toast";
import { AuthProvider } from "@/lib/useAuth";
import { ProfileProvider } from "@/lib/useProfile";
import { FamilyModeProvider } from "@/lib/useFamilyMode";

// Saved theme / family mode / locale are applied to <html> before first paint by
// the inline script in app/layout.tsx — no client-side init effect needed here.
export function Providers({ children }: { children: React.ReactNode }) {
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
