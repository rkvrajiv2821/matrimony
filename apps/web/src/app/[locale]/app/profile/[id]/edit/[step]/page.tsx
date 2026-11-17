import { isStep } from "@/components/profile/steps";
import { Wizard } from "@/components/profile/wizard";
import { loadManagedProfile } from "@/lib/profile";
import { apiGet } from "@/lib/api-server";
import { getReferenceBundle } from "@/lib/reference";
import type { Schemas } from "@vaibhav/api-client";
import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

export default async function EditStepPage({
  params,
}: {
  params: Promise<{ locale: string; id: string; step: string }>;
}) {
  const { locale, id, step } = await params;
  setRequestLocale(locale);
  if (!isStep(step)) notFound();
  const [profile, reference] = await Promise.all([loadManagedProfile(id, locale), getReferenceBundle()]);
  const preference =
    step === "preferences"
      ? ((await apiGet<Schemas["PreferenceOut"][]>(`/profiles/${id}/preferences`))[0] ?? null)
      : null;
  return <Wizard profile={profile} step={step} reference={reference} preference={preference} />;
}
