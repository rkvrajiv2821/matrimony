import { getTranslations } from "next-intl/server";

const TONE: Record<string, string> = {
  draft: "bg-line text-ink",
  submitted: "bg-accent-soft text-accent",
  approved: "bg-success-soft text-success",
  needs_changes: "bg-danger-soft text-danger",
  suspended: "bg-danger-soft text-danger",
  archived: "bg-line text-muted",
};

export async function StatusChip({ status }: { status: string }) {
  const t = await getTranslations("profile.status");
  return (
    <span
      data-testid="profile-status"
      data-status={status}
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${TONE[status] ?? TONE.draft}`}
    >
      {t(status)}
    </span>
  );
}

export async function CompletionBar({ percent }: { percent: number }) {
  const t = await getTranslations("profile");
  return (
    <div className="space-y-1">
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={t("complete", { percent })}
        className="h-2 overflow-hidden rounded-full bg-line"
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-sm text-muted">{t("complete", { percent })}</p>
    </div>
  );
}
