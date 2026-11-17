import { defaultLocale, localePrefixes, locales } from "@vaibhav/localization";
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix: { mode: "always", prefixes: localePrefixes },
  localeCookie: { name: "VB_LOCALE", maxAge: 60 * 60 * 24 * 365 },
});
