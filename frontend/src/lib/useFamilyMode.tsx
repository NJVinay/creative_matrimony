"use client";

import { createContext, useContext } from "react";
import { PREF_KEYS, savePreference, useHtmlState } from "@/lib/htmlPreference";

interface FamilyModeContextType {
    isFamilyMode: boolean;
    toggleFamilyMode: () => void;
}

const FamilyModeContext = createContext<FamilyModeContextType | undefined>(undefined);

export function FamilyModeProvider({ children }: { children: React.ReactNode }) {
    // The `family-mode` class on <html> is the source of truth (applied before paint by the layout script)
    const isFamilyMode = useHtmlState(html => html.classList.contains("family-mode"), false);

    const toggleFamilyMode = () => {
        const next = !isFamilyMode;
        document.documentElement.classList.toggle("family-mode", next);
        savePreference(PREF_KEYS.familyMode, String(next));
    };

    return (
        <FamilyModeContext.Provider value={{ isFamilyMode, toggleFamilyMode }}>
            {children}
        </FamilyModeContext.Provider>
    );
}

export function useFamilyMode() {
    const context = useContext(FamilyModeContext);
    if (context === undefined) {
        throw new Error("useFamilyMode must be used within a FamilyModeProvider");
    }
    return context;
}
