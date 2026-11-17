import { Link } from "@/i18n/navigation";
import { REFRESH_COOKIE } from "@/lib/session";
import { getTranslations } from "next-intl/server";
import { cookies } from "next/headers";
import { LanguageSwitcher } from "./language-switcher";
import { Logo } from "./logo";

export async function SiteHeader() {
  const t = await getTranslations("common.nav");
  const signedIn = (await cookies()).has(REFRESH_COOKIE);

  const nav = [
    { href: "/how-it-works", label: t("howItWorks") },
    { href: "/safety", label: t("safety") },
    { href: "/about", label: t("about") },
  ] as const;

  return (
    <header className="border-b border-line bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" aria-label="VAIBHAV" className="min-w-0 rounded-md">
          <Logo />
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-6 text-sm md:flex">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} className="text-muted hover:text-primary">
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <LanguageSwitcher />
          <Link
            href={signedIn ? "/app" : "/login"}
            aria-label={signedIn ? t("dashboard") : t("login")}
            className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-primary px-3 text-sm font-semibold text-white hover:bg-primary-hover sm:px-4"
          >
            <svg aria-hidden="true" viewBox="0 0 20 20" className="size-5 fill-current sm:hidden">
              <path d="M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-3.3 0-7 1.7-7 4v2h14v-2c0-2.3-3.7-4-7-4Z" />
            </svg>
            <span className="hidden sm:inline">{signedIn ? t("dashboard") : t("login")}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
