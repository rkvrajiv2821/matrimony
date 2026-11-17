"use client";

import type { Choice } from "@/components/form";
import type { Locale } from "@vaibhav/localization";
import { useLocale, useTranslations } from "next-intl";

export interface Named {
  code: string;
  name_en: string;
  name_ta: string;
}

/** Location / community names: Tamil script for `ta`, English letters otherwise (incl. Tanglish). */
export function usePlaceName() {
  const locale = useLocale() as Locale;
  return (p: Named | null | undefined) => (p ? (locale === "ta" ? p.name_ta : p.name_en) : "");
}

export function useChoices() {
  const t = useTranslations("options");
  const placeName = usePlaceName();
  return {
    label: (group: string, code: string | null | undefined) => (code ? t(`${group}.${code}`) : ""),
    options: (group: string, codes: readonly string[]): Choice[] =>
      codes.map((c) => ({ value: c, label: t(`${group}.${c}`) })),
    places: (items: Named[]): Choice[] => items.map((p) => ({ value: p.code, label: placeName(p) })),
  };
}
