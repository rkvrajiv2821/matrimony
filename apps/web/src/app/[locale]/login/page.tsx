import { LoginFlow } from "@/components/login-flow";
import { redirect } from "@/i18n/navigation";
import { REFRESH_COOKIE } from "@/lib/session";
import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { cookies } from "next/headers";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "auth" });
  return { title: t("loginTitle"), robots: { index: false } };
}

export default async function LoginPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  if ((await cookies()).has(REFRESH_COOKIE)) redirect({ href: "/app", locale });
  const t = await getTranslations("auth");

  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <div className="rounded-card-lg border border-line bg-surface p-6 shadow-card sm:p-8">
        <h1 className="mb-2 font-serif text-3xl font-bold text-primary">{t("loginTitle")}</h1>
        <p className="mb-6 text-muted">{t("loginSubtitle")}</p>
        <LoginFlow />
      </div>
    </div>
  );
}
