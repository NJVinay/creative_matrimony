"use client";

import { useTranslation } from "@/lib/i18n";

export function LanguageToggle() {
    const { locale, setLocale } = useTranslation();

    return (
        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
                onClick={() => setLocale("en")}
                className={`px-3 py-1 rounded-md text-sm transition-all ${locale === "en"
                        ? "bg-white dark:bg-gray-700 shadow text-primary-600 font-medium"
                        : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
                    }`}
            >
                EN
            </button>
            <button
                onClick={() => setLocale("te")}
                className={`px-3 py-1 rounded-md text-sm transition-all ${locale === "te"
                        ? "bg-white dark:bg-gray-700 shadow text-primary-600 font-medium"
                        : "text-gray-500 hover:text-gray-900 dark:hover:text-white"
                    }`}
            >
                తె
            </button>
        </div>
    );
}
