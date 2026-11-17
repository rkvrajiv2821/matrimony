import { SubmitButton, VisibilityToggle, WithdrawButton } from "@/components/profile/actions";
import { CompletionBar, StatusChip } from "@/components/profile/status";
import { REQUIRED_STEPS, STEPS, STEP_COMPLETION } from "@/components/profile/steps";
import { Link } from "@/i18n/navigation";
import { apiGet } from "@/lib/api-server";
import { loadManagedProfile } from "@/lib/profile";
import type { Schemas } from "@vaibhav/api-client";
import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function ProfileOverview({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const p = await loadManagedProfile(id, locale);
  const t = await getTranslations("profile");
  const tOpt = await getTranslations("options");
  const name = p.display_name ?? p.subject_name;
  const base = `/app/profile/${p.id}`;

  if (p.my_role === "creator_pending") {
    const delegates = await apiGet<Schemas["DelegateSummary"][]>(`/profiles/${p.id}/delegates`);
    const mine = delegates.find((d) => d.is_me) ?? delegates[0];
    return (
      <div className="space-y-6">
        <h1 className="font-serif text-3xl font-bold text-primary">{p.subject_name}</h1>
        <section className="space-y-3 rounded-card-lg border border-gold/50 bg-accent-soft/60 p-6" data-testid="awaiting-consent">
          <h2 className="font-serif text-xl font-semibold text-ink">{t("awaitingConsent", { name: p.subject_name })}</h2>
          <p className="text-muted">{t("awaitingConsentBody", { name: p.subject_name })}</p>
          {mine && <WithdrawButton delegationId={mine.id} />}
        </section>
      </div>
    );
  }

  const editable = p.status === "draft" || p.status === "needs_changes";
  const canSubmit = editable && p.completion.missing_required.length === 0;
  const done = (s: (typeof STEPS)[number]) => STEP_COMPLETION[s].every((k) => p.completion.sections[k]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-subtle">{p.my_role === "owner" ? t("roleOwner") : t("roleDelegate")}</p>
          <h1 className="font-serif text-3xl font-bold text-primary">{name}</h1>
        </div>
        <StatusChip status={p.status} />
      </div>

      <section className="space-y-3 rounded-card-lg border border-line bg-surface p-6 shadow-card">
        <p className="text-ink" data-testid="status-body">{t(`statusBody.${p.status}`)}</p>
        {p.visibility === "paused" && p.status === "approved" && (
          <p className="rounded-md bg-accent-soft px-3 py-2 text-sm text-ink">{t("pausedBody")}</p>
        )}
        {p.status_reason_code && p.status !== "approved" && (
          <div className="rounded-md bg-danger-soft px-4 py-3 text-sm text-ink" data-testid="review-reason">
            <p className="font-medium">{tOpt(`review_reason.${p.status_reason_code}`)}</p>
            {p.status_note && (
              <p className="mt-1">
                <span className="text-muted">{t("noteFromTeam")}: </span>
                {p.status_note}
              </p>
            )}
          </div>
        )}
        <CompletionBar percent={p.completion.percent} />
        {editable && p.completion.missing_required.length > 0 && (
          <div className="text-sm">
            <p className="text-muted">{t("submitHelp")}</p>
            <ul className="mt-1 list-inside list-disc text-ink">
              {p.completion.missing_required.map((k) => (
                <li key={k}>{t(`completionItems.${k}`)}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex flex-wrap gap-3 pt-2">
          {editable && p.my_scopes.includes("edit_profile") && <SubmitButton profileId={p.id} disabled={!canSubmit} />}
          <Link href={`${base}/preview`} className="inline-flex min-h-12 items-center rounded-full border border-primary px-6 font-semibold text-primary hover:bg-primary-soft">
            {t("preview")}
          </Link>
          {p.my_role === "owner" && p.status === "approved" && (
            <VisibilityToggle profileId={p.id} paused={p.visibility === "paused"} />
          )}
        </div>
      </section>

      <section aria-labelledby="sections-h" className="rounded-card-lg border border-line bg-surface p-6 shadow-card">
        <h2 id="sections-h" className="mb-4 font-serif text-xl font-semibold text-ink">{t("sectionsTitle")}</h2>
        <ul className="divide-y divide-line">
          {STEPS.map((s) => (
            <li key={s}>
              <Link href={`${base}/edit/${s}`} className="flex min-h-14 items-center justify-between gap-3 py-2 hover:text-primary" data-testid={`section-${s}`}>
                <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
                  <span aria-hidden="true" className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm ${done(s) ? "bg-success-soft text-success" : "bg-line text-muted"}`}>
                    {done(s) ? "✓" : "•"}
                  </span>
                  <span className="font-medium text-ink">{t(`sections.${s}`)}</span>
                  <span className="text-xs text-subtle">{REQUIRED_STEPS.has(s) ? t("required") : t("optional")}</span>
                </span>
                <span className="shrink-0 text-sm text-muted">{done(s) ? t("done") : t("todo")}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {p.my_role === "owner" && (
        <Link href={`${base}/helpers`} className="inline-flex min-h-11 items-center font-medium text-primary underline">
          {t("helpers")}
        </Link>
      )}
    </div>
  );
}
