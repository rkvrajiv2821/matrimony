import { MemberCard } from "@/components/profile/member-card";
import { Link } from "@/i18n/navigation";
import { apiGet } from "@/lib/api-server";
import { loadManagedProfile } from "@/lib/profile";
import type { Schemas } from "@vaibhav/api-client";
import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function PreviewPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  await loadManagedProfile(id, locale); // 404 unless the caller manages this profile
  const member = await apiGet<Schemas["MemberProfileOut"]>(`/profiles/${id}/preview`);
  const t = await getTranslations("previewPage");
  const tp = await getTranslations("profile");
  return (
    <div className="space-y-5">
      <h1 className="font-serif text-3xl font-bold text-primary">{t("title")}</h1>
      <p role="note" className="rounded-md bg-accent-soft px-4 py-3 text-sm text-ink">{t("banner")}</p>
      <MemberCard m={member} />
      <Link href={`/app/profile/${id}`} className="inline-flex min-h-11 items-center font-medium text-primary underline">
        {tp("back")}
      </Link>
    </div>
  );
}
