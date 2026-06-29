"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import en from "@/i18n/en.json";
import te from "@/i18n/te.json";

type Locale = "en" | "te";

/* Quick-and-dirty nested key accessor */
function getNested(obj: Record<string, unknown>, path: string): string {
    const value = path.split(".").reduce<unknown>((acc, part) => {
        if (acc && typeof acc === "object" && part in acc) {
            return (acc as Record<string, unknown>)[part];
        }
        return undefined;
    }, obj);

    return typeof value === "string" ? value : path;
}

interface I18nContextType {
    locale: Locale;
    setLocale: (l: Locale) => void;
    t: (key: string) => string;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
    const [locale, setLocaleState] = useState<Locale>(() => {
        if (typeof window === "undefined") return "en";
        const saved = localStorage.getItem("app-locale");
        return saved === "te" ? "te" : "en";
    });

    const setLocale = (l: Locale) => {
        setLocaleState(l);
        localStorage.setItem("app-locale", l);
    };

    const t = (key: string) => {
        const dict = (locale === "te" ? te : en) as Record<string, unknown>;
        return getNested(dict, key);
    };

    return (
        <I18nContext.Provider value={{ locale, setLocale, t }}>
            {children}
        </I18nContext.Provider>
    );
}

export function useTranslation() {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error("useTranslation must be used within an I18nProvider");
    }
    return context;
}
