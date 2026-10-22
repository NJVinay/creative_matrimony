import { useSyncExternalStore } from "react";

/**
 * Display preferences live on <html>: the `dark` and `family-mode` classes and
 * the `lang` attribute. The inline script in app/layout.tsx applies the saved
 * values before first paint; components read them back with useHtmlState.
 *
 * useSyncExternalStore renders `serverValue` during hydration (matching the
 * server HTML) and switches to the live value right after, so a saved
 * preference never causes a hydration mismatch.
 */

/** localStorage keys — the init script in app/layout.tsx reads the same ones. */
export const PREF_KEYS = {
    theme: "theme",
    familyMode: "familyMode",
    locale: "app-locale",
} as const;

function subscribe(onChange: () => void) {
    const observer = new MutationObserver(onChange);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "lang"] });
    return () => observer.disconnect();
}

export function useHtmlState<T extends string | boolean>(read: (html: HTMLElement) => T, serverValue: T): T {
    return useSyncExternalStore(subscribe, () => read(document.documentElement), () => serverValue);
}

/** Persist a preference; storage can throw (private mode, blocked site data). */
export function savePreference(key: string, value: string) {
    try {
        localStorage.setItem(key, value);
    } catch {
        // The choice still applies for this page view, it just won't be remembered
    }
}
