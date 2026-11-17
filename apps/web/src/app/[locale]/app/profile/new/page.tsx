import { CreateProfileForm } from "@/components/profile/create-form";
import { apiGet } from "@/lib/api-server";
import type { Schemas } from "@vaibhav/api-client";
import { getTranslations, setRequestLocale } from "next-intl/server";

export default async function NewProfilePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("profile");
  const managed = await apiGet<Schemas["ProfileSummaryOut"][]>("/profiles/managed");
  const hasOwn = managed.some((m) => m.my_role === "owner");
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-bold text-primary">{t("createTitle")}</h1>
      <div className="rounded-card-lg border border-line bg-surface p-6 shadow-card">
        <CreateProfileForm hasOwnProfile={hasOwn} />
      </div>
    </div>
  );
}
