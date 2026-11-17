"use client";

import { Link, useRouter } from "@/i18n/navigation";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { PhotoManager } from "./photo-manager";
import { PreferencesForm } from "./preferences-form";
import {
  BasicStep,
  CareerStep,
  CommunityStep,
  EducationStep,
  FamilyStep,
  LifestyleStep,
  type Reference,
} from "./sections";
import { STEPS, STEP_COMPLETION, type Step } from "./steps";

type Profile = Schemas["ProfileManageOut"];

const FORMS = {
  basic: BasicStep,
  community: CommunityStep,
  education: EducationStep,
  career: CareerStep,
  family: FamilyStep,
  lifestyle: LifestyleStep,
} as const;

export function Wizard({
  profile,
  step,
  reference,
  preference,
}: {
  profile: Profile;
  step: Step;
  reference: Reference;
  preference: Schemas["PreferenceOut"] | null;
}) {
  const t = useTranslations("profile");
  const router = useRouter();
  const index = STEPS.indexOf(step);
  const base = `/app/profile/${profile.id}`;
  const href = (s: Step) => `${base}/edit/${s}`;
  const next = index < STEPS.length - 1 ? href(STEPS[index + 1]!) : base;
  const back = index > 0 ? href(STEPS[index - 1]!) : base;
  const isLast = index === STEPS.length - 1;
  const done = (s: Step) => STEP_COMPLETION[s].every((k) => profile.completion.sections[k]);

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <p className="text-sm text-subtle">{t("stepOf", { current: index + 1, total: STEPS.length })}</p>
        <h1 className="font-serif text-3xl font-bold text-primary">{t(`sections.${step}`)}</h1>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={profile.completion.percent}
          aria-label={t("complete", { percent: profile.completion.percent })}
          className="h-2 overflow-hidden rounded-full bg-line"
        >
          <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${profile.completion.percent}%` }} />
        </div>
        <nav aria-label={t("sectionsTitle")} className="-mx-1 flex gap-1 overflow-x-auto pb-1">
          {STEPS.map((s, i) => (
            <Link
              key={s}
              href={href(s)}
              aria-current={s === step ? "step" : undefined}
              className={`inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-full px-3 text-sm ${
                s === step ? "bg-primary text-white" : "bg-surface text-muted hover:bg-primary-soft"
              }`}
            >
              <span aria-hidden="true">{done(s) ? "✓" : i + 1}</span>
              {t(`sections.${s}`)}
            </Link>
          ))}
        </nav>
      </div>

      <div className="rounded-card-lg border border-line bg-surface p-5 shadow-card sm:p-6">
        {step === "photos" ? (
          <PhotoManager profileId={profile.id} initial={profile.photos} nextHref={next} backHref={back} />
        ) : step === "preferences" ? (
          <PreferencesForm profileId={profile.id} existing={preference} reference={reference} doneHref={base} backHref={back} />
        ) : (
          (() => {
            const Form = FORMS[step];
            return (
              <Form
                profile={profile}
                reference={reference}
                backHref={back}
                isLast={isLast}
                onSaved={() => {
                  router.push(next);
                  router.refresh();
                }}
              />
            );
          })()
        )}
      </div>
    </div>
  );
}
