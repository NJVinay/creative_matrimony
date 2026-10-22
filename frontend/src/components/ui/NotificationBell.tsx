"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import Link from "next/link";

interface Notification {
    id: number;
    type: string;
    title: string;
    body: string;
    is_read: boolean;
    created_at: string;
}

export function NotificationBell() {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const fetchNotifications = async () => {
        try {
            const data = await apiFetch<Notification[]>("/notifications?limit=5");
            setNotifications(data);
            setUnreadCount(data.filter((n: Notification) => !n.is_read).length);
        } catch (err) {
            // Silent — bell on public pages or while unauthed
            console.error(err);
        }
    };

    useEffect(() => {
        const initial = window.setTimeout(() => {
            void fetchNotifications();
        }, 0);
        const interval = setInterval(fetchNotifications, 60000); // Poll every minute
        return () => {
            window.clearTimeout(initial);
            clearInterval(interval);
        };
    }, []);

    useEffect(() => {
        // Close on click outside
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const markAsRead = async (id: number) => {
        try {
            await apiFetch(`/notifications/${id}/read`, { method: "PATCH" });
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-gray-600 hover:text-primary-600 dark:text-gray-300 transition-colors"
            >
                <span className="text-xl">🔔</span>
                {unreadCount > 0 && (
                    <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform translate-x-1/4 -translate-y-1/4 bg-red-600 rounded-full">
                        {unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <Card className="absolute right-0 mt-2 w-80 z-50 p-0 overflow-hidden shadow-xl border-gray-200 dark:border-gray-700">
                    <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex justify-between items-center">
                        <h3 className="font-bold text-sm">Notifications</h3>
                        <button
                            className="text-xs text-primary-600 hover:underline"
                            onClick={fetchNotifications}
                        >
                            Refresh
                        </button>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="p-4 text-center text-gray-500 text-sm">
                                No notifications
                            </div>
                        ) : (
                            notifications.map(n => (
                                <div
                                    key={n.id}
                                    className={`p-3 border-b border-gray-100 dark:border-gray-800 transition-colors ${!n.is_read ? "bg-primary-50 dark:bg-primary-900/10" : "hover:bg-gray-50 dark:hover:bg-gray-800"}`}
                                    onClick={() => !n.is_read && markAsRead(n.id)}
                                >
                                    <p className="text-sm font-medium mb-1">{n.title}</p>
                                    <p className="text-xs text-gray-500">{n.body}</p>
                                    <div className="mt-1 flex justify-between items-center">
                                        <span className="text-[10px] text-gray-400">
                                            {new Date(n.created_at).toLocaleDateString()}
                                        </span>
                                        {!n.is_read && (
                                            <span className="text-[10px] text-primary-600 font-bold">New</span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    <div className="p-2 border-t border-gray-200 dark:border-gray-700 text-center bg-gray-50 dark:bg-gray-800">
                        <Link href="/dashboard" className="text-xs text-gray-500 hover:text-primary-600">
                            View All
                        </Link>
                    </div>
                </Card>
            )}
        </div>
    );
}
