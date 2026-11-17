import { requireMe } from "@/lib/me";
import { intlLocale, isLocale, DISPLAY_TIME_ZONE } from "@vaibhav/localization";
import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function DashboardPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ welcome?: string }>;
}) {
  const { locale } = await params;
  const { welcome } = await searchParams;
  setRequestLocale(locale);
  const me = await requireMe(locale);
  const t = await getTranslations("dashboard");

  const since = new Intl.DateTimeFormat(isLocale(locale) ? intlLocale[locale] : "en-IN", {
    dateStyle: "long",
    timeZone: DISPLAY_TIME_ZONE,
  }).format(new Date(me.created_at));

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-bold text-primary" data-testid="dashboard-heading">
        {welcome ? t("welcomeNew") : t("welcomeBack")}
      </h1>

      <section className="rounded-card-lg border border-gold/50 bg-accent-soft/60 p-6">
        <h2 className="mb-2 font-serif text-xl font-semibold text-ink">{t("nextStepTitle")}</h2>
        <p className="text-muted">{t("nextStepBody")}</p>
      </section>

      <section className="rounded-card-lg border border-line bg-surface p-6 shadow-card">
        <h2 className="mb-4 font-serif text-xl font-semibold text-ink">{t("accountTitle")}</h2>
        <dl className="grid gap-3 sm:grid-cols-[10rem_1fr]">
          <dt className="text-sm text-subtle">{t("phone")}</dt>
          <dd className="flex items-center gap-2 font-mono text-ink" data-testid="masked-phone">
            {me.phone_masked}
            {me.phone_verified && (
              <span className="rounded-full bg-success-soft px-2 py-0.5 font-sans text-xs font-medium text-success">
                {t("verified")}
              </span>
            )}
          </dd>
        </dl>
        <p className="mt-4 text-sm text-muted">{t("memberSince", { date: since })}</p>
      </section>
    </div>
  );
}
