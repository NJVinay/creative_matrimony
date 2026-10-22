import { ApiError } from "@/lib/api";

export interface OtpThrottle {
    /**
     * Which limit answered:
     * - "resend": this browser was sent a code for the number moments ago, so
     *   that code may still be valid (let the user enter it);
     * - "number": too many codes for the number from browsers that never logged
     *   in to it, so this browser may have no code at all;
     * - "code": the code being entered has used all its attempts.
     */
    kind: "resend" | "number" | "code";
    /** The server's message, shown as-is. */
    message: string;
    /** Seconds until a new OTP may be requested (0 = now or not stated). */
    waitSeconds: number;
}

/**
 * The backend's own OTP 429s, shared by the login and register pages:
 * - POST /auth/otp/request: "Please wait N seconds before requesting a new OTP."
 *   (resend window for this browser and number)
 * - POST /auth/otp/request: "Too many OTPs were requested for this number.
 *   Please try again in N minutes." (hourly cap for browsers new to the number)
 * - POST /auth/otp/verify: "Too many incorrect attempts for this code. Please
 *   request a new OTP[ in N seconds]." (only that code is used up)
 * All carry {detail}; SlowAPI's per-IP limit answers {error} instead, so it
 * returns null here and is shown like any other error. Retry-After is not
 * CORS-exposed, so the wait is read from the message.
 */
export function otpThrottle(err: unknown): OtpThrottle | null {
    if (!(err instanceof ApiError) || err.status !== 429) return null;
    const payload = err.payload as { detail?: unknown } | null | undefined;
    if (typeof payload?.detail !== "string") return null;
    const kind = /^Please wait/i.test(err.detail)
        ? "resend"
        : /for this number/i.test(err.detail)
            ? "number"
            : "code";
    return { kind, message: err.detail, waitSeconds: waitSecondsIn(err.detail) };
}

/** Countdown label: "45s" under 90 seconds, else "12 min". */
export function waitLabel(seconds: number): string {
    return seconds < 90 ? `${seconds}s` : `${Math.ceil(seconds / 60)} min`;
}

/** "…45 seconds…" → 45, "…2 minutes…" → 120, no time named → 0. */
function waitSecondsIn(text: string): number {
    const m = /(\d+)\s*(second|minute)/i.exec(text);
    if (!m) return 0;
    return Number(m[1]) * (m[2].toLowerCase() === "minute" ? 60 : 1);
}
