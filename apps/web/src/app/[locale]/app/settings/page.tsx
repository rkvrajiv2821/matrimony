import { LanguagePreference } from "@/components/language-preference";
import { LogoutButton } from "@/components/logout-button";
import { SessionList } from "@/components/session-list";
import { apiGet } from "@/lib/api-server";
import { requireMe } from "@/lib/me";
import type { Schemas } from "@vaibhav/api-client";
import type { Locale } from "@vaibhav/localization";
import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function SettingsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const me = await requireMe(locale);
  const sessions = await apiGet<Schemas["SessionOut"][]>("/auth/sessions");
  const t = await getTranslations("settings");

  return (
    <div className="space-y-8">
      <h1 className="font-serif text-3xl font-bold text-primary">{t("title")}</h1>

      <section className="rounded-card-lg border border-line bg-surface p-6 shadow-card" aria-labelledby="lang-h">
        <h2 id="lang-h" className="mb-1 font-serif text-xl font-semibold text-ink">
          {t("languageTitle")}
        </h2>
        <p className="mb-4 text-sm text-muted">{t("languageBody")}</p>
        <LanguagePreference current={me.preferred_language as Locale} />
      </section>

      <section className="rounded-card-lg border border-line bg-surface p-6 shadow-card" aria-labelledby="sess-h">
        <h2 id="sess-h" className="mb-1 font-serif text-xl font-semibold text-ink">
          {t("sessionsTitle")}
        </h2>
        <p className="mb-4 text-sm text-muted">{t("sessionsBody")}</p>
        <SessionList sessions={sessions} />
        <div className="mt-6">
          <LogoutButton label={t("logoutAll")} allDevices />
        </div>
      </section>
    </div>
  );
}
