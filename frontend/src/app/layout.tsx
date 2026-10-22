import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-playfair" });

export const metadata: Metadata = {
  title: "Creative Matrimony - Find Your Perfect Match",
  description: "Premier Telugu matrimony service. Safe, secure, and tradition-respecting.",
};

// Applies saved display preferences to <html> before first paint, so dark mode and
// family mode never flash. No saved theme → follow the OS. Keys match
// PREF_KEYS in lib/htmlPreference.ts; storage can throw (private mode, blocked data).
const preferenceInitScript = `(function () {
  var html = document.documentElement;
  function get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  var theme = get("theme");
  if (theme === "dark" || (!theme && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches)) html.classList.add("dark");
  if (get("familyMode") === "true") html.classList.add("family-mode");
  if (get("app-locale") === "te") html.lang = "te";
})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: the init script changes <html> class/lang before hydration
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: preferenceInitScript }} />
      </head>
      <body className={`${inter.variable} ${playfair.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
