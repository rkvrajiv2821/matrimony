"use client";

import { FormError, primaryButton, secondaryButton, useSave } from "@/components/form";
import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";

export function SubmitButton({ profileId, disabled }: { profileId: string; disabled: boolean }) {
  const t = useTranslations("profile");
  const router = useRouter();
  const { busy, error, save } = useSave();
  return (
    <div className="space-y-3">
      <button
        type="button"
        className={primaryButton}
        disabled={disabled || busy}
        data-testid="submit-profile"
        onClick={async () => {
          if (await save(`/api/v1/profiles/${profileId}/submit`, undefined, "POST")) router.refresh();
        }}
      >
        {busy ? t("submitting") : t("submit")}
      </button>
      <FormError message={error} />
    </div>
  );
}

export function VisibilityToggle({ profileId, paused }: { profileId: string; paused: boolean }) {
  const t = useTranslations("profile");
  const router = useRouter();
  const { busy, error, save } = useSave();
  return (
    <div className="space-y-3">
      <button
        type="button"
        className={secondaryButton}
        disabled={busy}
        data-testid="toggle-visibility"
        onClick={async () => {
          const action = paused ? "resume" : "pause";
          if (await save(`/api/v1/profiles/${profileId}/${action}`, undefined, "POST")) router.refresh();
        }}
      >
        {paused ? t("resume") : t("pause")}
      </button>
      <FormError message={error} />
    </div>
  );
}

export function WithdrawButton({ delegationId }: { delegationId: string }) {
  const t = useTranslations("profile");
  const router = useRouter();
  const { busy, error, save } = useSave();
  return (
    <div className="space-y-2">
      <button
        type="button"
        className={secondaryButton}
        disabled={busy}
        onClick={async () => {
          if ((await save(`/api/v1/delegates/${delegationId}`, undefined, "DELETE")) !== null) {
            router.replace("/app");
            router.refresh();
          }
        }}
      >
        {t("withdraw")}
      </button>
      <FormError message={error} />
    </div>
  );
}
