"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";

type ToastKind = "success" | "error" | "info";
interface Toast { id: number; kind: ToastKind; message: string }

interface ToastContextValue {
    toast: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
    const [items, setItems] = useState<Toast[]>([]);

    const toast = useCallback((message: string, kind: ToastKind = "info") => {
        const id = Date.now() + Math.random();
        setItems(prev => [...prev, { id, kind, message }]);
    }, []);

    useEffect(() => {
        if (items.length === 0) return;
        const t = setTimeout(() => {
            setItems(prev => prev.slice(1));
        }, 3500);
        return () => clearTimeout(t);
    }, [items]);

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
                {items.map(t => (
                    <div
                        key={t.id}
                        className={`pointer-events-auto px-4 py-3 rounded-lg shadow-lg text-sm font-medium animate-fade-in-up ${
                            t.kind === "success"
                                ? "bg-green-600 text-white"
                                : t.kind === "error"
                                ? "bg-red-600 text-white"
                                : "bg-gray-900 text-white"
                        }`}
                    >
                        {t.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast(): ToastContextValue {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error("useToast must be used within ToastProvider");
    return ctx;
}
