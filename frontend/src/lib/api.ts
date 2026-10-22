/**
 * Centralized API client.
 * - Reads API base from NEXT_PUBLIC_API_URL (default http://localhost:8000)
 * - Injects Bearer token from localStorage if present
 * - Throws ApiError on non-2xx; auto-handles 401 by clearing tokens and redirecting to /login
 */

const FALLBACK_BASE = "http://localhost:8000";

export const API_BASE: string =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || FALLBACK_BASE;

export const tokenStore = {
    // Deprecated: Tokens are now handled via httpOnly cookies
    get: () => null,
    set: () => {},
    clear: () => {},
};

export class ApiError extends Error {
    constructor(public status: number, public detail: string, public payload?: unknown) {
        super(detail);
        this.name = "ApiError";
    }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
    body?: unknown; // auto-stringified when object
    /**
     * When true, a 401 is returned to the caller instead of redirecting to /login.
     * Use for requests that are fine to make logged out (OTP, the /auth/me probe);
     * protected pages redirect via AuthGuard / ProtectedRoute.
     */
    anonymous?: boolean;
    /** When true, do not throw on non-2xx (caller handles) */
    allowNon2xx?: boolean;
}

/** Human-readable message from an error payload, incl. FastAPI 422 lists. */
function errorDetail(payload: unknown): string | undefined {
    if (!payload || typeof payload !== "object" || !("detail" in payload)) return undefined;
    const detail = (payload as { detail: unknown }).detail;
    if (!Array.isArray(detail)) return String(detail);
    // [{ loc: ["body", "date_of_birth"], msg: "..." }, ...] → "Date of birth: ..."
    return detail
        .map(item => {
            const { loc, msg } = (item ?? {}) as { loc?: unknown[]; msg?: string };
            const field = Array.isArray(loc) && loc.length > 1 ? String(loc[loc.length - 1]) : "";
            const label = field ? `${field.charAt(0).toUpperCase()}${field.slice(1).replace(/_/g, " ")}: ` : "";
            return `${label}${msg ?? "Invalid value"}`;
        })
        .join(" ");
}

function buildUrl(path: string): string {
    if (/^https?:\/\//.test(path)) return path;
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${API_BASE}/api${p}`;
}

export async function apiFetch<T = unknown>(
    path: string,
    options: ApiFetchOptions = {}
): Promise<T> {
    const { body, anonymous, allowNon2xx, headers, ...rest } = options;

    const finalHeaders: Record<string, string> = {
        Accept: "application/json",
        ...(headers as Record<string, string> | undefined),
    };

    let finalBody: BodyInit | undefined;
    if (body !== undefined && body !== null) {
        if (body instanceof FormData) {
            finalBody = body;
            // Let the browser set the multipart boundary
        } else if (typeof body === "string") {
            finalBody = body;
            finalHeaders["Content-Type"] =
                finalHeaders["Content-Type"] ?? "application/json";
        } else {
            finalBody = JSON.stringify(body);
            finalHeaders["Content-Type"] =
                finalHeaders["Content-Type"] ?? "application/json";
        }
    }

    const res = await fetch(buildUrl(path), {
        ...rest,
        headers: finalHeaders,
        body: finalBody,
        credentials: "include",
    });

    // 401 = token invalid; clear and force re-auth
    if (res.status === 401 && !anonymous) {
        tokenStore.clear();
        if (
            typeof window !== "undefined" &&
            !window.location.pathname.startsWith("/login") &&
            !window.location.pathname.startsWith("/register")
        ) {
            const next = encodeURIComponent(
                window.location.pathname + window.location.search
            );
            window.location.href = `/login?redirect=${next}`;
        }
    }

    const contentType = res.headers.get("content-type") || "";
    let payload: unknown = undefined;
    if (contentType.includes("application/json")) {
        payload = await res.json().catch(() => undefined);
    } else {
        payload = await res.text().catch(() => undefined);
    }

    if (!res.ok && !allowNon2xx) {
        const detail =
            errorDetail(payload) ||
            (typeof payload === "string" ? payload : undefined) ||
            res.statusText ||
            `Request failed (${res.status})`;
        throw new ApiError(res.status, detail, payload);
    }

    return payload as T;
}

/** Convenience: build a relative image URL when backend serves /static/... */
export function staticUrl(path: string): string {
    if (!path) return "";
    if (/^https?:\/\//.test(path)) return path;
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${API_BASE}${p}`;
}

/**
 * Mock payment signature for /payments/verify.
 * Mirrors backend `PaymentProvider.sign` (HMAC-SHA256 over "order_id|payment_id").
 * Must be kept in sync with `backend/app/services/payment_service.py`.
 */
const MOCK_PAYMENT_SECRET = "MOCK_RAZORPAY_SECRET_DO_NOT_USE_IN_PROD";

export async function mockSign(orderId: string, paymentId: string): Promise<string> {
    const enc = new TextEncoder();
    const keyData = enc.encode(MOCK_PAYMENT_SECRET);
    const msg = enc.encode(`${orderId}|${paymentId}`);

    // SubtleCrypto HMAC is async; fall back to non-crypto hash for old environments.
    if (typeof crypto !== "undefined" && crypto.subtle) {
        try {
            const key = await crypto.subtle.importKey(
                "raw",
                keyData,
                { name: "HMAC", hash: "SHA-256" },
                false,
                ["sign"]
            );
            const sig = await crypto.subtle.sign("HMAC", key, msg);
            const bytes = new Uint8Array(sig);
            return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
        } catch {
            // fall through
        }
    }
    // Tiny non-crypto fallback (browser without SubtleCrypto)
    let h1 = 0x811c9dc5;
    const data = `${MOCK_PAYMENT_SECRET}|${orderId}|${paymentId}`;
    for (let i = 0; i < data.length; i++) {
        h1 ^= data.charCodeAt(i);
        h1 = Math.imul(h1, 0x01000193) >>> 0;
    }
    return h1.toString(16).padStart(8, "0").repeat(8);
}
