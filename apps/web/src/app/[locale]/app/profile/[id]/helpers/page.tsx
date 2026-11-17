import { HelpersManager } from "@/components/profile/delegation";
import { Link } from "@/i18n/navigation";
import { apiGet } from "@/lib/api-server";
import { loadManagedProfile } from "@/lib/profile";
import type { Schemas } from "@vaibhav/api-client";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

export default async function HelpersPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const profile = await loadManagedProfile(id, locale);
  if (profile.my_role !== "owner") notFound();
  const delegates = await apiGet<Schemas["DelegateSummary"][]>(`/profiles/${id}/delegates`);
  const t = await getTranslations("delegation");
  const tp = await getTranslations("profile");
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-bold text-primary">{t("helpersTitle")}</h1>
      <p className="text-muted">{t("helpersIntro")}</p>
      <div className="rounded-card-lg border border-line bg-surface p-6 shadow-card">
        <HelpersManager profileId={id} delegates={delegates} />
      </div>
      <Link href={`/app/profile/${id}`} className="inline-flex min-h-11 items-center font-medium text-primary underline">
        {tp("back")}
      </Link>
    </div>
  );
}
