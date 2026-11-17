import { LogoutButton } from "@/components/logout-button";
import { Link } from "@/i18n/navigation";
import { requireMe } from "@/lib/me";
import { getTranslations, setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

export const metadata = { robots: { index: false } };

export default async function MemberLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  await requireMe(locale);
  const t = await getTranslations("common.nav");

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <nav aria-label="Account" className="mb-8 flex flex-wrap items-center gap-2 border-b border-line pb-4 text-sm">
        <Link href="/app" className="rounded-full px-4 py-2 font-medium text-ink hover:bg-primary-soft">
          {t("dashboard")}
        </Link>
        <Link href="/app/settings" className="rounded-full px-4 py-2 font-medium text-ink hover:bg-primary-soft">
          {t("settings")}
        </Link>
        <span className="flex-1" />
        <LogoutButton label={t("logout")} />
      </nav>
      {children}
    </div>
  );
}
