"use client";

import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import Link from "next/link";

export default function Home() {
  const { t } = useTranslation();

  const steps = [
    { number: "1", title: t("steps.one_title"), desc: t("steps.one_desc") },
    { number: "2", title: t("steps.two_title"), desc: t("steps.two_desc") },
    { number: "3", title: t("steps.three_title"), desc: t("steps.three_desc") },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gold-50 dark:bg-gray-950">
      {/* Header */}
      <header className="fixed top-0 w-full z-10 glass">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-serif font-bold text-primary-700 dark:text-primary-300">
              Creative Matrimony
            </span>
          </div>
          <div className="flex items-center gap-3">
            <LanguageToggle />
            <ThemeToggle />
            <Link href="/login">
              <Button size="sm" variant="ghost">{t("common.login")}</Button>
            </Link>
            <Link href="/register">
              <Button size="sm">{t("common.register")}</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero — one strong section on a calm cream canvas */}
      <main className="flex-1 flex items-center pt-16 relative overflow-hidden">
        {/* Soft gold glow accent, not a dominant surface */}
        <div
          aria-hidden
          className="absolute -top-24 right-[-10%] w-[36rem] h-[36rem] rounded-full bg-gold-100 dark:bg-gold-950/40 blur-3xl opacity-70"
        />
        <div className="container mx-auto px-4 py-20 relative">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full bg-gold-100 dark:bg-gold-950/60 border border-gold-300 dark:border-gold-800 px-3 py-1 text-xs font-medium text-gray-800 dark:text-gold-200 mb-6">
              <span aria-hidden>✦</span> Telugu-first · Private · Family friendly
            </span>
            <h1 className="text-3xl md:text-4xl lg:text-[2.75rem] leading-tight font-serif font-bold text-gray-900 dark:text-white mb-4 text-balance">
              {t("hero.title")}
            </h1>
            <p className="text-base md:text-lg text-gray-600 dark:text-gray-300 mb-8 max-w-xl text-balance">
              {t("hero.subtitle")}
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link href="/register" className="w-full sm:w-auto">
                <Button size="lg" className="w-full">
                  {t("hero.cta_primary")}
                </Button>
              </Link>
              <a href="#how-it-works" className="w-full sm:w-auto">
                <Button size="lg" variant="outline" className="w-full">
                  {t("hero.cta_secondary")}
                </Button>
              </a>
            </div>
            <p className="mt-6 text-xs text-gray-500 dark:text-gray-400">
              🔒 {t("features.privacy_desc")}
            </p>
          </div>
        </div>
      </main>

      {/* Three-step guide */}
      <section id="how-it-works" className="py-16 bg-white dark:bg-gray-900 border-y border-sand dark:border-gray-800 scroll-mt-16">
        <div className="container mx-auto px-4">
          <h2 className="text-2xl font-serif font-bold text-center text-gray-900 dark:text-gray-100 mb-10">
            {t("steps.title")}
          </h2>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {steps.map((step) => (
              <div key={step.number} className="flex md:flex-col items-start gap-4">
                <span className="flex-shrink-0 w-9 h-9 rounded-full bg-primary-600 text-white text-sm font-bold flex items-center justify-center">
                  {step.number}
                </span>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-1">{step.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-16 bg-gold-50 dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              {
                icon: "🔒",
                title: t("features.privacy"),
                desc: t("features.privacy_desc")
              },
              {
                icon: "✅",
                title: t("features.verified"),
                desc: t("features.verified_desc")
              },
              {
                icon: "🤝",
                title: t("features.community"),
                desc: t("features.community_desc")
              },
            ].map((feature, i) => (
              <Card key={i} className="text-center hover:-translate-y-1 transition-transform duration-200">
                <div className="text-3xl mb-3">{feature.icon}</div>
                <h3 className="text-lg font-bold mb-2 font-serif text-primary-700 dark:text-primary-300">
                  {feature.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {feature.desc}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-white dark:bg-gray-900 border-t border-sand dark:border-gray-800">
        <div className="container mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
          {/* Page is prerendered at build time; the client's year may be newer */}
          <span suppressHydrationWarning>© {new Date().getFullYear()} Creative Matrimony</span>
          <div className="flex gap-4">
            <Link href="/legal/terms" className="hover:text-primary-600 dark:hover:text-primary-300">Terms</Link>
            <Link href="/legal/privacy" className="hover:text-primary-600 dark:hover:text-primary-300">Privacy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
