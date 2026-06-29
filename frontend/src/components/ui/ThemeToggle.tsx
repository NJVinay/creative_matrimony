"use client";

import { useState } from "react";

export function ThemeToggle() {
    const [isDark, setIsDark] = useState(() => {
        if (typeof window === "undefined") return false;
        const stored = localStorage.getItem("theme");
        if (stored) return stored === "dark";
        return document.documentElement.classList.contains("dark");
    });

    const toggle = () => {
        const html = document.documentElement;
        if (html.classList.contains("dark")) {
            html.classList.remove("dark");
            localStorage.setItem("theme", "light");
            setIsDark(false);
        } else {
            html.classList.add("dark");
            localStorage.setItem("theme", "dark");
            setIsDark(true);
        }
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
