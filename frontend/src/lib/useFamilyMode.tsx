"use client";

import { createContext, useContext, useState } from "react";

interface FamilyModeContextType {
    isFamilyMode: boolean;
    toggleFamilyMode: () => void;
}

const FamilyModeContext = createContext<FamilyModeContextType | undefined>(undefined);

export function FamilyModeProvider({ children }: { children: React.ReactNode }) {
    const [isFamilyMode, setIsFamilyMode] = useState(() => {
        if (typeof window === "undefined") return false;
        const stored = localStorage.getItem("familyMode") === "true";
        document.documentElement.classList.toggle("family-mode", stored);
        return stored;
    });

    const toggleFamilyMode = () => {
        setIsFamilyMode(prev => {
            const newValue = !prev;
            if (newValue) {
                document.documentElement.classList.add("family-mode");
                localStorage.setItem("familyMode", "true");
            } else {
                document.documentElement.classList.remove("family-mode");
                localStorage.setItem("familyMode", "false");
            }
            return newValue;
        });
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
