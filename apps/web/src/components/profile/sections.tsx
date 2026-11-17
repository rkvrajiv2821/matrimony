"use client";

import {
  CheckboxChips,
  FormError,
  RadioCards,
  SelectField,
  TextArea,
  TextField,
  primaryButton,
  useSave,
  widen,
} from "@/components/form";
import { Link } from "@/i18n/navigation";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { useState, type FormEvent, type ReactNode } from "react";
import { useChoices, usePlaceName } from "./labels";
import { HEIGHTS_CM, heightLabel } from "./steps";

type Profile = Schemas["ProfileManageOut"];
type Place = Schemas["LocationOut"];
type Community = Schemas["CommunityOut"];

export interface Reference {
  options: Schemas["OptionsOut"];
  countries: Place[];
  states: Place[];
  tnDistricts: Place[];
  cities: Place[];
  community: Community[];
}

interface StepProps {
  profile: Profile;
  reference: Reference;
  onSaved: (p: Profile) => void;
  backHref: string | null;
  isLast: boolean;
}

function StepForm({
  children,
  onSubmit,
  busy,
  error,
  backHref,
  isLast,
}: {
  children: ReactNode;
  onSubmit: () => void;
  busy: boolean;
  error: string | null;
  backHref: string | null;
  isLast: boolean;
}) {
  const t = useTranslations("profile");
  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      {children}
      <FormError message={error} />
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
        {backHref ? (
          <Link href={backHref} className="min-h-11 px-2 py-3 font-medium text-primary underline">
            {t("back")}
          </Link>
        ) : (
          <span />
        )}
        <button type="submit" disabled={busy} className={primaryButton} data-testid="step-save">
          {busy ? t("saving") : isLast ? t("saveFinish") : t("saveContinue")}
        </button>
      </div>
    </form>
  );
}

function VisibilityField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const t = useTranslations("profile");
  const { options } = useChoices();
  return (
    <RadioCards
      legend={t("whoCanSee")}
      name="visibility"
      value={value}
      onChange={onChange}
      choices={options("visibility", ["members", "connections", "hidden"])}
      columns={3}
    />
  );
}

// --------------------------------------------------------------------------- basic

export function BasicStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const tp = useTranslations("profile");
  const { options, places } = useChoices();
  const placeName = usePlaceName();
  const opts = reference.options.options;
  const { busy, error, invalid, save } = useSave();
  const [v, setV] = useState(widen({
    subject_name: profile.subject_name,
    display_name: profile.display_name ?? "",
    date_of_birth: profile.date_of_birth ?? "",
    gender: profile.gender ?? null,
    marital_status: profile.marital_status ?? null,
    has_children: profile.has_children ?? null,
    height_cm: profile.height_cm ?? null,
    mother_tongue: profile.mother_tongue ?? "tamil",
    current_country: profile.current_country ?? "IN",
    state_code: (profile.state?.code ?? "in-tn") as string | null,
    district_code: profile.district?.code ?? null,
    city_code: profile.city?.code ?? null,
  }));
  const set = <K extends keyof typeof v>(k: K, val: (typeof v)[K]) =>
    setV((prev) => ({ ...prev, [k]: val }));

  const districts = v.state_code === "in-tn" ? reference.tnDistricts : [];
  const cities = reference.cities.filter((c) => c.parent_code === v.district_code);
  const inIndia = v.current_country === "IN";

  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const body = {
          ...v,
          height_cm: v.height_cm ? Number(v.height_cm) : null,
          has_children: v.marital_status === "never_married" ? null : v.has_children,
          state_code: inIndia ? v.state_code : null,
          district_code: inIndia ? v.district_code : null,
          city_code: inIndia ? v.city_code : null,
        };
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/basic`, body);
        if (saved) onSaved(saved);
      }}
    >
      {profile.status === "approved" && (
        <p className="rounded-md bg-accent-soft px-4 py-3 text-sm text-ink">{tp("materialChangeWarning")}</p>
      )}
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField label={t("subjectName")} name="subject_name" value={v.subject_name} invalid={invalid.has("subject_name")} onChange={(x) => set("subject_name", x)} maxLength={100} autoComplete="name" />
        <TextField label={t("displayName")} hint={t("displayNameHint")} name="display_name" value={v.display_name} invalid={invalid.has("display_name")} onChange={(x) => set("display_name", x)} maxLength={60} />
        <TextField label={t("dob")} hint={t("dobHint")} name="date_of_birth" type="date" value={v.date_of_birth} invalid={invalid.has("date_of_birth")} onChange={(x) => set("date_of_birth", x)} />
        <SelectField label={t("height")} name="height_cm" value={v.height_cm ? String(v.height_cm) : null} invalid={invalid.has("height_cm")} placeholder={t("select")} onChange={(x) => set("height_cm", x ? Number(x) : null)} choices={HEIGHTS_CM.map((h) => ({ value: String(h), label: heightLabel(h) }))} />
      </div>
      <RadioCards legend={tp("gender")} name="gender" value={v.gender} onChange={(x) => set("gender", x)} choices={options("gender", opts.gender!)} />
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("maritalStatus")} name="marital_status" value={v.marital_status} invalid={invalid.has("marital_status")} placeholder={t("select")} onChange={(x) => set("marital_status", x)} choices={options("marital_status", opts.marital_status!)} />
        {v.marital_status && v.marital_status !== "never_married" && (
          <SelectField label={t("hasChildren")} name="has_children" value={v.has_children === null ? null : String(v.has_children)} placeholder={t("select")} onChange={(x) => set("has_children", x === null ? null : x === "true")} choices={[{ value: "true", label: t("yes") }, { value: "false", label: t("no") }]} />
        )}
        <SelectField label={t("motherTongue")} name="mother_tongue" value={v.mother_tongue} onChange={(x) => set("mother_tongue", x)} choices={options("language", opts.language!)} />
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("country")} name="current_country" value={v.current_country} onChange={(x) => setV((p) => ({ ...p, current_country: x ?? "IN", state_code: x === "IN" ? p.state_code : null, district_code: null, city_code: null }))} choices={reference.countries.map((c) => ({ value: c.code, label: placeName(c) }))} />
        {inIndia && (
          <SelectField label={t("state")} name="state_code" value={v.state_code} invalid={invalid.has("state_code")} placeholder={t("select")} onChange={(x) => setV((p) => ({ ...p, state_code: x, district_code: null, city_code: null }))} choices={places(reference.states)} />
        )}
        {inIndia && districts.length > 0 && (
          <SelectField label={t("district")} name="district_code" value={v.district_code} invalid={invalid.has("district_code")} placeholder={t("select")} onChange={(x) => setV((p) => ({ ...p, district_code: x, city_code: null }))} choices={places(districts)} />
        )}
        {inIndia && cities.length > 0 && (
          <SelectField label={t("city")} name="city_code" value={v.city_code} invalid={invalid.has("city_code")} placeholder={t("select")} onChange={(x) => set("city_code", x)} choices={places(cities)} />
        )}
      </div>
    </StepForm>
  );
}

// --------------------------------------------------------------------------- community

export function CommunityStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const placeName = usePlaceName();
  const { busy, error, save } = useSave();
  const subs = reference.community.filter((c) => c.type === "sub_community");
  const [sub, setSub] = useState(profile.community?.sub_community_code ?? null);
  const [visibility, setVisibility] = useState<string>(profile.community?.visibility ?? "members");
  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/community`, {
          sub_community_code: sub,
          visibility,
        });
        if (saved) onSaved(saved);
      }}
    >
      <div className="rounded-lg border border-line bg-bg px-4 py-3">
        <p className="text-sm text-subtle">{t("community")}</p>
        <p className="font-medium text-ink">
          {profile.community_label ? placeName(profile.community_label) : "—"}
        </p>
      </div>
      <SelectField
        label={t("subCommunity")}
        hint={t("subCommunityHint")}
        name="sub_community_code"
        value={sub}
        placeholder={t("select")}
        onChange={setSub}
        choices={subs.map((c) => ({ value: c.code, label: placeName({ code: c.code, name_en: c.label_en, name_ta: c.label_ta }) }))}
      />
      <VisibilityField value={visibility} onChange={setVisibility} />
    </StepForm>
  );
}

// --------------------------------------------------------------------------- education

export function EducationStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const { options } = useChoices();
  const opts = reference.options.options;
  const { busy, error, invalid, save } = useSave();
  const e = profile.education;
  const [v, setV] = useState(widen({
    qualification: e?.qualification ?? null,
    field_of_study: e?.field_of_study ?? null,
    institution: e?.institution ?? "",
    year_completed: e?.year_completed ? String(e.year_completed) : "",
    visibility: e?.visibility ?? "members",
  }));
  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/education`, {
          ...v,
          institution: v.institution || null,
          year_completed: v.year_completed ? Number(v.year_completed) : null,
        });
        if (saved) onSaved(saved);
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("qualification")} name="qualification" value={v.qualification} invalid={invalid.has("qualification")} placeholder={t("select")} onChange={(x) => setV({ ...v, qualification: x })} choices={options("education_level", opts.education_level!)} />
        <SelectField label={t("fieldOfStudy")} name="field_of_study" value={v.field_of_study} placeholder={t("select")} onChange={(x) => setV({ ...v, field_of_study: x })} choices={options("field_of_study", opts.field_of_study!)} />
        <TextField label={t("institution")} name="institution" value={v.institution} invalid={invalid.has("institution")} onChange={(x) => setV({ ...v, institution: x })} maxLength={150} />
        <TextField label={t("yearCompleted")} name="year_completed" value={v.year_completed} inputMode="numeric" maxLength={4} invalid={invalid.has("year_completed")} onChange={(x) => setV({ ...v, year_completed: x.replace(/\D/g, "") })} />
      </div>
      <VisibilityField value={v.visibility ?? "members"} onChange={(x) => setV({ ...v, visibility: x })} />
    </StepForm>
  );
}

// --------------------------------------------------------------------------- career

export function CareerStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const { options, places } = useChoices();
  const opts = reference.options.options;
  const { busy, error, invalid, save } = useSave();
  const c = profile.career;
  const [v, setV] = useState(widen({
    employment_type: c?.employment_type ?? null,
    occupation: c?.occupation ?? "",
    industry: c?.industry ?? null,
    employer: c?.employer ?? "",
    work_city_code: c?.work_city_code ?? null,
    income_band: c?.income_band ?? null,
    visibility: c?.visibility ?? "members",
  }));
  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/career`, {
          ...v,
          occupation: v.occupation || null,
          employer: v.employer || null,
        });
        if (saved) onSaved(saved);
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("employmentType")} name="employment_type" value={v.employment_type} invalid={invalid.has("employment_type")} placeholder={t("select")} onChange={(x) => setV({ ...v, employment_type: x })} choices={options("employment_type", opts.employment_type!)} />
        <TextField label={t("occupation")} name="occupation" placeholder={t("occupationPlaceholder")} value={v.occupation} invalid={invalid.has("occupation")} onChange={(x) => setV({ ...v, occupation: x })} maxLength={100} />
        <SelectField label={t("industry")} name="industry" value={v.industry} placeholder={t("select")} onChange={(x) => setV({ ...v, industry: x })} choices={options("industry", opts.industry!)} />
        <TextField label={t("employer")} name="employer" value={v.employer} invalid={invalid.has("employer")} onChange={(x) => setV({ ...v, employer: x })} maxLength={150} />
        <SelectField label={t("workCity")} name="work_city_code" value={v.work_city_code} placeholder={t("select")} onChange={(x) => setV({ ...v, work_city_code: x })} choices={places(reference.cities)} />
        <SelectField label={t("incomeBand")} hint={t("incomeHint")} name="income_band" value={v.income_band} placeholder={t("preferNotToSay")} onChange={(x) => setV({ ...v, income_band: x })} choices={options("income_band", opts.income_band!)} />
      </div>
      <VisibilityField value={v.visibility ?? "members"} onChange={(x) => setV({ ...v, visibility: x })} />
    </StepForm>
  );
}

// --------------------------------------------------------------------------- family

export function FamilyStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const { options, places } = useChoices();
  const opts = reference.options.options;
  const { busy, error, invalid, save } = useSave();
  const f = profile.family;
  const num = (n: number | null | undefined) => (n === null || n === undefined ? "" : String(n));
  const [v, setV] = useState(widen({
    family_type: f?.family_type ?? null,
    family_values: f?.family_values ?? null,
    native_district_code: f?.native_district_code ?? null,
    father_occupation: f?.father_occupation ?? "",
    mother_occupation: f?.mother_occupation ?? "",
    siblings_count: num(f?.siblings_count),
    siblings_married: num(f?.siblings_married),
    family_description: f?.family_description ?? "",
    visibility: f?.visibility ?? "members",
  }));
  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/family`, {
          ...v,
          father_occupation: v.father_occupation || null,
          mother_occupation: v.mother_occupation || null,
          family_description: v.family_description || null,
          siblings_count: v.siblings_count === "" ? null : Number(v.siblings_count),
          siblings_married: v.siblings_married === "" ? null : Number(v.siblings_married),
        });
        if (saved) onSaved(saved);
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("familyType")} name="family_type" value={v.family_type} placeholder={t("select")} onChange={(x) => setV({ ...v, family_type: x })} choices={options("family_type", opts.family_type!)} />
        <SelectField label={t("familyValues")} name="family_values" value={v.family_values} placeholder={t("select")} onChange={(x) => setV({ ...v, family_values: x })} choices={options("family_values", opts.family_values!)} />
        <SelectField label={t("nativeDistrict")} name="native_district_code" value={v.native_district_code} placeholder={t("select")} onChange={(x) => setV({ ...v, native_district_code: x })} choices={places(reference.tnDistricts)} />
        <TextField label={t("fatherOccupation")} name="father_occupation" value={v.father_occupation} invalid={invalid.has("father_occupation")} onChange={(x) => setV({ ...v, father_occupation: x })} maxLength={100} />
        <TextField label={t("motherOccupation")} name="mother_occupation" value={v.mother_occupation} invalid={invalid.has("mother_occupation")} onChange={(x) => setV({ ...v, mother_occupation: x })} maxLength={100} />
        <TextField label={t("siblings")} name="siblings_count" inputMode="numeric" maxLength={2} value={v.siblings_count} onChange={(x) => setV({ ...v, siblings_count: x.replace(/\D/g, "") })} />
        <TextField label={t("siblingsMarried")} name="siblings_married" inputMode="numeric" maxLength={2} value={v.siblings_married} onChange={(x) => setV({ ...v, siblings_married: x.replace(/\D/g, "") })} />
      </div>
      <TextArea label={t("familyDescription")} name="family_description" value={v.family_description} invalid={invalid.has("family_description")} onChange={(x) => setV({ ...v, family_description: x })} />
      <VisibilityField value={v.visibility ?? "members"} onChange={(x) => setV({ ...v, visibility: x })} />
    </StepForm>
  );
}

// --------------------------------------------------------------------------- lifestyle

export function LifestyleStep({ profile, reference, onSaved, backHref, isLast }: StepProps) {
  const t = useTranslations("profile.fields");
  const { options } = useChoices();
  const opts = reference.options.options;
  const { busy, error, invalid, save } = useSave();
  const l = profile.lifestyle;
  const [v, setV] = useState(widen({
    physical_status: l?.physical_status ?? null,
    languages: (l?.languages ?? []) as string[],
    diet: l?.diet ?? null,
    smoking: l?.smoking ?? null,
    drinking: l?.drinking ?? null,
    interests: (l?.interests ?? []) as string[],
    about_me: l?.about_me ?? "",
  }));
  return (
    <StepForm
      busy={busy}
      error={error}
      backHref={backHref}
      isLast={isLast}
      onSubmit={async () => {
        const saved = await save<Profile>(`/api/v1/profiles/${profile.id}/lifestyle`, {
          ...v,
          about_me: v.about_me || null,
        });
        if (saved) onSaved(saved);
      }}
    >
      <TextArea label={t("aboutMe")} hint={t("aboutMeHint")} name="about_me" value={v.about_me} invalid={invalid.has("about_me")} onChange={(x) => setV({ ...v, about_me: x })} />
      <div className="grid gap-5 sm:grid-cols-2">
        <SelectField label={t("diet")} name="diet" value={v.diet} placeholder={t("select")} onChange={(x) => setV({ ...v, diet: x })} choices={options("diet", opts.diet!)} />
        <SelectField label={t("physicalStatus")} name="physical_status" value={v.physical_status} placeholder={t("select")} onChange={(x) => setV({ ...v, physical_status: x })} choices={options("physical_status", opts.physical_status!)} />
        <SelectField label={t("smoking")} name="smoking" value={v.smoking} placeholder={t("select")} onChange={(x) => setV({ ...v, smoking: x })} choices={options("habit", opts.habit!)} />
        <SelectField label={t("drinking")} name="drinking" value={v.drinking} placeholder={t("select")} onChange={(x) => setV({ ...v, drinking: x })} choices={options("habit", opts.habit!)} />
      </div>
      <CheckboxChips legend={t("languages")} name="languages" values={v.languages} onChange={(x) => setV({ ...v, languages: x })} choices={options("language", opts.language!)} />
      <CheckboxChips legend={t("interests")} name="interests" values={v.interests} onChange={(x) => setV({ ...v, interests: x })} choices={options("interest", opts.interest!)} />
    </StepForm>
  );
}
