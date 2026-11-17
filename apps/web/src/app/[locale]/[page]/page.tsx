/**
 * Public information pages. Content lives in the localization catalogues for now;
 * Phase 5 moves it to the admin-managed CMS (content_pages).
 */
import { routing } from "@/i18n/routing";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

const PAGES = {
  about: "about",
  "how-it-works": "howItWorks",
  safety: "safety",
  faq: "faq",
  contact: "contact",
  eligibility: "eligibility",
  terms: "terms",
  privacy: "privacy",
} as const;

type Slug = keyof typeof PAGES;
const isSlug = (s: string): s is Slug => s in PAGES;

export const dynamicParams = false;

export function generateStaticParams() {
  return routing.locales.flatMap((locale) => Object.keys(PAGES).map((page) => ({ locale, page })));
}

type Props = { params: Promise<{ locale: string; page: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, page } = await params;
  if (!isSlug(page)) return {};
  const t = await getTranslations({ locale, namespace: `pages.${PAGES[page]}` });
  return { title: t("title") };
}

export default async function InfoPage({ params }: Props) {
  const { locale, page } = await params;
  if (!isSlug(page)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations(`pages.${PAGES[page]}`);
  const common = await getTranslations("common");
  const isDraft = ["terms", "privacy", "contact", "eligibility"].includes(page);

  return (
    <article className="mx-auto max-w-3xl px-4 py-14">
      <h1 className="mb-6 font-serif text-4xl font-bold text-primary">{t("title")}</h1>
      {isDraft && (
        <p role="note" className="mb-6 rounded-md bg-accent-soft px-4 py-3 text-sm text-ink">
          {common("draftNotice")}
        </p>
      )}
      <p className="text-lg text-muted">{t("body")}</p>
    </article>
  );
}
