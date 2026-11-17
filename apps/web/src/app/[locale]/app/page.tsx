import { InvitationCard } from "@/components/profile/delegation";
import { CompletionBar, StatusChip } from "@/components/profile/status";
import { Link } from "@/i18n/navigation";
import { apiGet } from "@/lib/api-server";
import { requireMe } from "@/lib/me";
import type { Schemas } from "@vaibhav/api-client";
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
  const tp = await getTranslations("profile");
  const td = await getTranslations("delegation");
  const [profiles, invitations] = await Promise.all([
    apiGet<Schemas["ProfileSummaryOut"][]>("/profiles/managed"),
    apiGet<Schemas["InvitationOut"][]>("/delegations/invitations"),
  ]);
  const hasOwn = profiles.some((p) => p.my_role === "owner");

  const since = new Intl.DateTimeFormat(isLocale(locale) ? intlLocale[locale] : "en-IN", {
    dateStyle: "long",
    timeZone: DISPLAY_TIME_ZONE,
  }).format(new Date(me.created_at));

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-bold text-primary" data-testid="dashboard-heading">
        {welcome ? t("welcomeNew") : t("welcomeBack")}
      </h1>

      {invitations.length > 0 && (
        <section aria-labelledby="inv-h" className="space-y-3">
          <h2 id="inv-h" className="font-serif text-xl font-semibold text-ink">{td("invitationsTitle")}</h2>
          {invitations.map((inv) => (
            <InvitationCard key={inv.id} invite={inv} />
          ))}
        </section>
      )}

      {profiles.length > 0 && (
        <section aria-labelledby="profiles-h" className="space-y-3">
          <h2 id="profiles-h" className="font-serif text-xl font-semibold text-ink">{tp("myProfiles")}</h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {profiles.map((p) => (
              <li key={p.id}>
                <Link
                  href={`/app/profile/${p.id}`}
                  className="flex gap-4 rounded-card-lg border border-line bg-surface p-4 shadow-card hover:border-primary"
                  data-testid="profile-card"
                >
                  <div className="size-20 shrink-0 overflow-hidden rounded-card bg-bg">
                    {p.primary_photo_url && (
                      // eslint-disable-next-line @next/next/no-img-element -- private, authenticated image
                      <img src={p.primary_photo_url} alt="" className="size-full object-cover" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate font-semibold text-ink">{p.display_name ?? p.subject_name}</p>
                      <StatusChip status={p.status} />
                    </div>
                    <p className="text-xs text-subtle">
                      {p.subject_consent_pending
                        ? tp("awaitingConsent", { name: p.subject_name })
                        : p.my_role === "owner"
                          ? tp("roleOwner")
                          : tp("roleDelegate")}
                    </p>
                    {!p.subject_consent_pending && <CompletionBar percent={p.completion_percent} />}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!hasOwn && (
        <section className="rounded-card-lg border border-gold/50 bg-accent-soft/60 p-6">
          <h2 className="mb-2 font-serif text-xl font-semibold text-ink">{t("nextStepTitle")}</h2>
          <p className="mb-4 text-muted">{t("nextStepBody")}</p>
          <Link
            href="/app/profile/new"
            className="inline-flex min-h-12 items-center rounded-full bg-primary px-6 font-semibold text-white hover:bg-primary-hover"
            data-testid="create-profile-cta"
          >
            {tp("createCta")}
          </Link>
        </section>
      )}
      {hasOwn && (
        <Link href="/app/profile/new" className="inline-flex min-h-11 items-center font-medium text-primary underline">
          {tp("createForFamily")}
        </Link>
      )}

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
