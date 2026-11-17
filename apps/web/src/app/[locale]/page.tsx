import { Link } from "@/i18n/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

const PILLARS = [
  { key: "free", icon: "M12 2 4 6v6c0 5 3.4 8.6 8 10 4.6-1.4 8-5 8-10V6l-8-4Zm-1 14-4-4 1.4-1.4L11 13.2l4.6-4.6L17 10l-6 6Z" },
  { key: "safe", icon: "M12 1a5 5 0 0 0-5 5v3H5v13h14V9h-2V6a5 5 0 0 0-5-5Zm-3 5a3 3 0 1 1 6 0v3H9V6Zm3 7a2 2 0 0 1 1 3.7V19h-2v-2.3A2 2 0 0 1 12 13Z" },
  { key: "verified", icon: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2Z" },
  { key: "family", icon: "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 2c-2.7 0-8 1.3-8 4v3h16v-3c0-2.7-5.3-4-8-4Zm8 0-1 .1c1.2.9 2 2 2 3.9v3h7v-3c0-2.7-5.3-4-8-4Z" },
] as const;

const STEPS = ["one", "two", "three", "four"] as const;

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("home");

  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-soft/60 to-bg">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 md:grid-cols-[3fr_2fr] md:py-20">
          <div className="space-y-6">
            <h1
              className={`font-serif font-bold leading-tight text-primary ${
                locale === "ta" ? "text-3xl md:text-4xl" : "text-4xl md:text-5xl"
              }`}
            >
              {t("title")}
            </h1>
            <p className="max-w-2xl text-lg text-muted">{t("subtitle")}</p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/login"
                className="inline-flex min-h-12 items-center rounded-full bg-primary px-6 font-semibold text-white shadow-card hover:bg-primary-hover"
              >
                {t("ctaPrimary")}
              </Link>
              <Link
                href="/how-it-works"
                className="inline-flex min-h-12 items-center rounded-full border border-primary px-6 font-semibold text-primary hover:bg-primary-soft"
              >
                {t("ctaSecondary")}
              </Link>
            </div>
          </div>
          <div aria-hidden="true" className="hidden items-center justify-center md:flex">
            <svg viewBox="0 0 200 200" className="w-72 max-w-full">
              <g fill="none" stroke="var(--vb-gold-500)" strokeWidth="2">
                <rect x="40" y="40" width="120" height="120" rx="16" transform="rotate(45 100 100)" />
                <rect x="65" y="65" width="70" height="70" rx="10" transform="rotate(45 100 100)" />
                {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
                  <circle key={a} cx={100 + 88 * Math.cos((a * Math.PI) / 180)} cy={100 + 88 * Math.sin((a * Math.PI) / 180)} r="5" />
                ))}
              </g>
              <circle cx="100" cy="100" r="14" fill="var(--vb-primary)" />
            </svg>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-14 pt-4">
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p) => (
            <li key={p.key} className="rounded-card border border-line bg-surface p-6 shadow-card">
              <svg aria-hidden="true" viewBox="0 0 24 24" className="mb-4 size-8 fill-accent">
                <path d={p.icon} />
              </svg>
              <h2 className="mb-2 font-serif text-lg font-semibold text-ink">
                {t(`pillars.${p.key}Title`)}
              </h2>
              <p className="text-sm text-muted">{t(`pillars.${p.key}Body`)}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-6">
        <h2 className="mb-8 text-center font-serif text-3xl font-bold text-primary">
          {t("stepsTitle")}
        </h2>
        <ol className="grid gap-5 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-start gap-4 rounded-card bg-accent-soft/60 p-5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary font-serif text-lg font-bold text-white">
                {i + 1}
              </span>
              <span className="pt-1.5 font-medium text-ink">{t(`steps.${s}`)}</span>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
