export const locales = ["en", "ta", "ta-Latn"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";

/** URL prefix for each locale. Tanglish uses a readable slug instead of `ta-Latn`. */
export const localePrefixes: Record<Locale, string> = {
  en: "/en",
  ta: "/ta",
  "ta-Latn": "/tanglish",
};

/** `lang` attribute / Intl locale for formatting. Tanglish formats like English (India). */
export const htmlLang: Record<Locale, string> = {
  en: "en-IN",
  ta: "ta-IN",
  "ta-Latn": "ta-Latn-IN",
};

export const intlLocale: Record<Locale, string> = {
  en: "en-IN",
  ta: "ta-IN",
  "ta-Latn": "en-IN",
};

export const DISPLAY_TIME_ZONE = "Asia/Kolkata";

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value);
}
