"use client";

import { useFamilyMode } from "@/lib/useFamilyMode";

export function FamilyModeToggle() {
    const { isFamilyMode, toggleFamilyMode } = useFamilyMode();

    return (
        <button
            onClick={toggleFamilyMode}
            className={`p-2 rounded-full transition-colors flex items-center justify-center gap-1 ${
                isFamilyMode 
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-400 font-bold" 
                    : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
            aria-label="Toggle Family Mode (Larger Text)"
            title="Toggle Family Mode"
        >
            <span className="text-xl leading-none" aria-hidden="true">
                {isFamilyMode ? "👓" : "👀"}
            </span>
            <span className="text-xs hidden md:inline">
                Family Mode
            </span>
        </button>
    );
}
