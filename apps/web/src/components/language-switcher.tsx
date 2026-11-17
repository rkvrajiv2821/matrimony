"use client";

import { usePathname, useRouter } from "@/i18n/navigation";
import { locales, type Locale } from "@vaibhav/localization";
import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

export function LanguageSwitcher() {
  const t = useTranslations("common");
  const locale = useLocale() as Locale;
  const pathname = usePathname();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <label className="inline-flex items-center gap-2 text-sm text-muted">
      <span className="sr-only">{t("language")}</span>
      <svg aria-hidden="true" viewBox="0 0 20 20" className="size-4 fill-current">
        <path d="M10 1.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm5.9 7.75h-2.6a13 13 0 0 0-1.1-5 7 7 0 0 1 3.7 5ZM10 3.1c.7.9 1.6 2.9 1.8 6.15H8.2C8.4 6 9.3 4 10 3.1Zm-2.2 1.15a13 13 0 0 0-1.1 5H4.1a7 7 0 0 1 3.7-5Zm-3.7 6.5h2.6a13 13 0 0 0 1.1 5 7 7 0 0 1-3.7-5Zm5.9 6.15c-.7-.9-1.6-2.9-1.8-6.15h3.6c-.2 3.25-1.1 5.25-1.8 6.15Zm2.2-1.15a13 13 0 0 0 1.1-5h2.6a7 7 0 0 1-3.7 5Z" />
      </svg>
      <select
        value={locale}
        disabled={pending}
        onChange={(e) =>
          startTransition(() => router.replace(pathname, { locale: e.target.value as Locale }))
        }
        className="min-h-11 cursor-pointer rounded-md border border-line bg-surface px-2 py-1 text-sm text-ink"
        data-testid="language-switcher"
      >
        {locales.map((l) => (
          <option key={l} value={l}>
            {t(`languages.${l}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
