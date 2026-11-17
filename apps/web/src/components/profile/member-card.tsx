import type { Schemas } from "@vaibhav/api-client";
import type { Locale } from "@vaibhav/localization";
import { getLocale, getTranslations } from "next-intl/server";
import type { ReactNode } from "react";
import { heightLabel } from "./steps";

type Member = Schemas["MemberProfileOut"];
type Named = { name_en: string; name_ta: string } | null | undefined;

function Row({ label, children }: { label: string; children: ReactNode }) {
  if (children === null || children === undefined || children === "") return null;
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 py-1.5 text-sm">
      <dt className="text-subtle">{label}</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}

/** The profile exactly as another member receives it from the API (Phase 3 reuses this). */
export async function MemberCard({ m }: { m: Member }) {
  const t = await getTranslations("previewPage");
  const f = await getTranslations("profile.fields");
  const o = await getTranslations("options");
  const locale = (await getLocale()) as Locale;
  const name = (p: Named) => (p ? (locale === "ta" ? p.name_ta : p.name_en) : null);
  const opt = (g: string, c: string | null | undefined) => (c ? o(`${g}.${c}`) : null);
  const place = [name(m.city), name(m.district), name(m.state)]
    .filter((x, i, all): x is string => Boolean(x) && x !== all[i - 1])
    .join(", ");
  const primary = m.photos[0];

  return (
    <article className="overflow-hidden rounded-card-lg border border-line bg-surface shadow-card" data-testid="member-card">
      <div className="grid md:grid-cols-[18rem_1fr]">
        <div className="aspect-[4/5] bg-bg md:aspect-auto">
          {primary ? (
            // eslint-disable-next-line @next/next/no-img-element -- private, authenticated image
            <img src={primary.full_url} alt="" className="size-full object-cover" />
          ) : (
            <div className="flex size-full min-h-60 items-center justify-center p-6 text-center text-sm text-subtle">
              {t("noPhoto")}
            </div>
          )}
        </div>
        <div className="space-y-5 p-6">
          <header>
            <h2 className="font-serif text-2xl font-bold text-primary" data-testid="member-name">{m.display_name}</h2>
            <p className="text-muted">
              {[m.age ? t("years", { age: m.age }) : null, m.height_cm ? heightLabel(m.height_cm) : null, place]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </header>
          {m.lifestyle?.about_me && (
            <section>
              <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-accent">{t("about")}</h3>
              <p className="whitespace-pre-line text-ink">{m.lifestyle.about_me}</p>
            </section>
          )}
          <section>
            <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-accent">{t("basics")}</h3>
            <dl>
              <Row label={f("maritalStatus")}>{opt("marital_status", m.marital_status)}</Row>
              <Row label={f("motherTongue")}>{opt("language", m.mother_tongue)}</Row>
              <Row label={f("community")}>{name(m.community_label)}</Row>
              <Row label={f("subCommunity")}>{name(m.sub_community_label)}</Row>
            </dl>
          </section>
          <section>
            <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-accent">{t("educationCareer")}</h3>
            <dl>
              <Row label={f("qualification")}>{opt("education_level", m.qualification)}</Row>
              <Row label={f("fieldOfStudy")}>{opt("field_of_study", m.field_of_study)}</Row>
              <Row label={f("institution")}>{m.institution}</Row>
              <Row label={f("employmentType")}>{opt("employment_type", m.employment_type)}</Row>
              <Row label={f("occupation")}>{m.occupation}</Row>
              <Row label={f("employer")}>{m.employer}</Row>
              <Row label={f("incomeBand")}>{opt("income_band", m.income_band)}</Row>
            </dl>
          </section>
          {m.family && (
            <section>
              <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-accent">{t("family")}</h3>
              <dl>
                <Row label={f("familyType")}>{opt("family_type", m.family.family_type)}</Row>
                <Row label={f("familyValues")}>{opt("family_values", m.family.family_values)}</Row>
                <Row label={f("nativeDistrict")}>{name(m.native_district)}</Row>
                <Row label={f("familyDescription")}>{m.family.family_description}</Row>
              </dl>
            </section>
          )}
          {m.lifestyle && (
            <section>
              <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-accent">{t("lifestyle")}</h3>
              <dl>
                <Row label={f("diet")}>{opt("diet", m.lifestyle.diet)}</Row>
                <Row label={f("languages")}>{m.lifestyle.languages?.map((l) => opt("language", l)).join(", ")}</Row>
                <Row label={f("interests")}>{m.lifestyle.interests?.map((l) => opt("interest", l)).join(", ")}</Row>
              </dl>
            </section>
          )}
        </div>
      </div>
    </article>
  );
}
