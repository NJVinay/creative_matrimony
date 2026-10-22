/**
 * Legal minimum marriage age in India (Prohibition of Child Marriage Act, 2006):
 * 18 for women, 21 for men; any other gender gets the stricter bound.
 * Mirrors backend `app/services/profile_service.py`, which enforces it too.
 */
export const MIN_MARRIAGE_AGE: Record<string, number> = { female: 18, male: 21 };
export const DEFAULT_MIN_MARRIAGE_AGE = 21;

export function minimumAgeFor(gender: string): number {
    return MIN_MARRIAGE_AGE[gender] ?? DEFAULT_MIN_MARRIAGE_AGE;
}

function toIsoDate(d: Date): string {
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${mm}-${dd}`;
}

/** Latest allowed date of birth (YYYY-MM-DD) for the gender — use as the date input's `max`. */
export function maxDobFor(gender: string, today: Date = new Date()): string {
    const d = new Date(today.getFullYear() - minimumAgeFor(gender), today.getMonth(), today.getDate());
    // 29 Feb in a non-leap target year rolls into March; step back to 28 Feb
    if (d.getMonth() !== today.getMonth()) d.setDate(0);
    return toIsoDate(d);
}

/** Field-level error for a date of birth, or null when it is empty or allowed. */
export function dobError(dob: string, gender: string): string | null {
    if (!dob || !gender) return null;
    if (dob <= maxDobFor(gender)) return null;
    const who = gender === "female" ? " for women" : gender === "male" ? " for men" : "";
    return `Must be at least ${minimumAgeFor(gender)} years old (the legal minimum marriage age${who} in India).`;
}
