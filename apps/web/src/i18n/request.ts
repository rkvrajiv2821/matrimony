import { DISPLAY_TIME_ZONE, isLocale, type Locale } from "@vaibhav/localization";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

const loaders: Record<Locale, () => Promise<{ default: Record<string, unknown> }>> = {
  en: () => import("@vaibhav/localization/messages/en.json"),
  ta: () => import("@vaibhav/localization/messages/ta.json"),
  "ta-Latn": () => import("@vaibhav/localization/messages/ta-Latn.json"),
};

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale: Locale = requested && isLocale(requested) ? requested : routing.defaultLocale;
  return {
    locale,
    timeZone: DISPLAY_TIME_ZONE,
    messages: (await loaders[locale]()).default,
  };
});
