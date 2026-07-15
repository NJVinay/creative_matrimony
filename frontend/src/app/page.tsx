"use client";

import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LanguageToggle } from "@/components/ui/LanguageToggle";
import Link from "next/link";

export default function Home() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="fixed top-0 w-full z-10 glass border-b border-white/20">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-serif font-bold text-primary-700 dark:text-primary-400">
              Creative Matrimony
            </span>
          </div>
          <div className="flex items-center gap-4">
            <LanguageToggle />
            <ThemeToggle />
            <Link href="/login">
              <Button size="sm" variant="outline">{t("common.login")}</Button>
            </Link>
            <Link href="/register">
              <Button size="sm">{t("common.register")}</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center pt-16 bg-[url('https://images.unsplash.com/photo-1583939003579-730e3918a45a?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80')] bg-cover bg-center">
        <div className="absolute inset-0 bg-white/40 dark:bg-black/60 backdrop-blur-[2px]" />

        <div className="container mx-auto px-4 relative z-0">
          <div className="max-w-2xl mx-auto text-center">
            <Card glass className="p-8 md:p-12 animate-fade-in-up">
              <h1 className="text-4xl md:text-5xl font-serif font-bold text-gray-900 dark:text-white mb-6 text-balance">
                {t("hero.title")}
              </h1>
              <p className="text-lg text-gray-700 dark:text-gray-200 mb-8 text-balance">
                {t("hero.subtitle")}
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/register" className="w-full sm:w-auto">
                  <Button size="lg" className="w-full">
                    {t("hero.cta_primary")}
                  </Button>
                </Link>
                <a href="#features" className="w-full sm:w-auto">
                  <Button size="lg" variant="outline" className="w-full bg-white/50 backdrop-blur-sm">
                    {t("hero.cta_secondary")}
                  </Button>
                </a>
              </div>
            </Card>
          </div>
        </div>
      </main>

      {/* Features Grid */}
      <section id="features" className="py-20 bg-white dark:bg-gray-950">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8">
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
              <Card key={i} className="text-center hover:translate-y-[-4px] transition-transform duration-300">
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-bold mb-2 font-serif text-primary-800 dark:text-primary-300">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {feature.desc}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
