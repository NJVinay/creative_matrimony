"use client";

import { createContext, useContext, type ReactNode } from "react";
import { PREF_KEYS, savePreference, useHtmlState } from "@/lib/htmlPreference";
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
    // <html lang> holds the active locale (restored before paint by the layout script).
    // Hydration renders "en" like the server did, then switches to a saved "te".
    const locale = useHtmlState<Locale>(html => (html.lang === "te" ? "te" : "en"), "en");

    const setLocale = (l: Locale) => {
        document.documentElement.lang = l;
        savePreference(PREF_KEYS.locale, l);
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
