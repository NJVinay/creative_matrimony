"use client";

import { PREF_KEYS, savePreference, useHtmlState } from "@/lib/htmlPreference";

export function ThemeToggle() {
    // The `dark` class on <html> is the source of truth (applied before paint by the layout script)
    const isDark = useHtmlState(html => html.classList.contains("dark"), false);

    const toggle = () => {
        const next = !isDark;
        document.documentElement.classList.toggle("dark", next);
        savePreference(PREF_KEYS.theme, next ? "dark" : "light");
    };

    return (
        <button
            onClick={toggle}
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
            {isDark ? "🌞" : "🌙"}
        </button>
    );
}
