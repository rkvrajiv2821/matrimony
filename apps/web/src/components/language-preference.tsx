"use client";

import { usePathname, useRouter } from "@/i18n/navigation";
import { errorKey, postJson } from "@/lib/errors";
import { locales, type Locale } from "@vaibhav/localization";
import { useTranslations } from "next-intl";
import { useState } from "react";

export function LanguagePreference({ current }: { current: Locale }) {
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();
  const [value, setValue] = useState<Locale>(current);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(next: Locale) {
    setValue(next);
    setBusy(true);
    setError(null);
    const r = await postJson("/api/v1/users/me", { preferred_language: next }, "PATCH");
    setBusy(false);
    if (!r.ok) {
      setValue(current);
      setError(t(`errors.${errorKey(r.error?.code)}`));
      return;
    }
    router.replace(pathname, { locale: next });
    router.refresh();
  }

  return (
    <fieldset disabled={busy}>
      <legend className="sr-only">{t("settings.languageTitle")}</legend>
      <div className="grid gap-3 sm:grid-cols-3">
        {locales.map((l) => (
          <label
            key={l}
            className="flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-line px-4 has-[:checked]:border-primary has-[:checked]:bg-primary-soft"
          >
            <input
              type="radio"
              name="language"
              value={l}
              checked={value === l}
              onChange={() => save(l)}
              className="size-4 accent-[var(--vb-primary)]"
              data-testid={`pref-${l}`}
            />
            <span className="font-medium text-ink">{t(`common.languages.${l}`)}</span>
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
    </fieldset>
  );
}
