"use client";

import { useRouter } from "@/i18n/navigation";
import { postJson } from "@/lib/errors";
import type { Schemas } from "@vaibhav/api-client";
import { DISPLAY_TIME_ZONE, intlLocale, type Locale } from "@vaibhav/localization";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

type Session = Schemas["SessionOut"];

/** Turn a raw user-agent into something a person recognises. */
function describe(label: string | null | undefined): string | null {
  if (!label) return null;
  const browser = /Edg\//.test(label)
    ? "Edge"
    : /Chrome\//.test(label)
      ? "Chrome"
      : /Firefox\//.test(label)
        ? "Firefox"
        : /Safari\//.test(label)
          ? "Safari"
          : null;
  const os = /Android/.test(label)
    ? "Android"
    : /iPhone|iPad/.test(label)
      ? "iOS"
      : /Windows/.test(label)
        ? "Windows"
        : /Mac OS X/.test(label)
          ? "macOS"
          : /Linux/.test(label)
            ? "Linux"
            : null;
  if (browser || os) return [browser, os].filter(Boolean).join(" · ");
  return label.slice(0, 60);
}

export function SessionList({ sessions }: { sessions: Session[] }) {
  const t = useTranslations("settings");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const [busyId, setBusyId] = useState<string | null>(null);
  const fmt = new Intl.DateTimeFormat(intlLocale[locale], {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: DISPLAY_TIME_ZONE,
  });

  return (
    <ul className="divide-y divide-line" data-testid="session-list">
      {sessions.map((s) => (
        <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div>
            <p className="font-medium text-ink">
              {describe(s.device_label) ?? t("unknownDevice")}
              {s.current && (
                <span className="ml-2 rounded-full bg-success-soft px-2 py-0.5 text-xs font-medium text-success">
                  {t("thisDevice")}
                </span>
              )}
            </p>
            {s.last_used_at && (
              <p className="text-sm text-subtle">
                {t("lastActive", { date: fmt.format(new Date(s.last_used_at)) })}
              </p>
            )}
          </div>
          {!s.current && (
            <button
              type="button"
              disabled={busyId === s.id}
              onClick={async () => {
                setBusyId(s.id);
                await postJson(`/api/v1/auth/sessions/${s.id}`, undefined, "DELETE");
                router.refresh();
              }}
              className="min-h-11 rounded-full px-4 text-sm font-medium text-primary hover:bg-primary-soft"
            >
              {t("logoutDevice")}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
