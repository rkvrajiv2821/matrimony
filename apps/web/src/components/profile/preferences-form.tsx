"use client";

import { CheckboxChips, FormError, primaryButton, useSave } from "@/components/form";
import { Link, useRouter } from "@/i18n/navigation";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { useId, useState, type ReactNode } from "react";
import { useChoices, usePlaceName } from "./labels";
import type { Reference } from "./sections";
import { HEIGHTS_CM, heightLabel } from "./steps";

type Pref = Schemas["PreferenceOut"];
type Criterion = NonNullable<Pref["must_have"]>[number];
type Importance = "must" | "preferred" | "flexible";

const AGES = Array.from({ length: 70 - 18 + 1 }, (_, i) => 18 + i);

function Importance({
  criterion,
  value,
  onChange,
}: {
  criterion: Criterion;
  value: Importance;
  onChange: (v: Importance) => void;
}) {
  const t = useTranslations("options.importance");
  const tp = useTranslations("preferences");
  return (
    <div role="radiogroup" aria-label={tp("importance")} className="inline-flex overflow-hidden rounded-full border border-line text-xs">
      {(["must", "preferred", "flexible"] as const).map((imp) => (
        <button
          key={imp}
          type="button"
          role="radio"
          aria-checked={value === imp}
          data-testid={`importance-${criterion}-${imp}`}
          onClick={() => onChange(imp)}
          className={`min-h-9 px-3 font-medium ${value === imp ? "bg-primary text-white" : "bg-white text-muted hover:bg-primary-soft"}`}
        >
          {t(imp)}
        </button>
      ))}
    </div>
  );
}

function Block({
  title,
  criterion,
  importance,
  setImportance,
  children,
}: {
  title: string;
  criterion: Criterion;
  importance: Record<Criterion, Importance>;
  setImportance: (c: Criterion, v: Importance) => void;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3 rounded-card border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-ink">{title}</h3>
        <Importance criterion={criterion} value={importance[criterion] ?? "flexible"} onChange={(v) => setImportance(criterion, v)} />
      </div>
      {children}
    </section>
  );
}

function Range({
  label,
  values,
  min,
  max,
  onMin,
  onMax,
  format,
}: {
  label: string;
  values: number[];
  min: number | null;
  max: number | null;
  onMin: (v: number | null) => void;
  onMax: (v: number | null) => void;
  format: (n: number) => string;
}) {
  const t = useTranslations("preferences");
  const idMin = useId();
  const idMax = useId();
  const select = (id: string, value: number | null, on: (v: number | null) => void, l: string) => (
    <div className="flex-1 space-y-1">
      <label htmlFor={id} className="text-sm text-subtle">
        {l}
      </label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(e) => on(e.target.value ? Number(e.target.value) : null)}
        className="block min-h-12 w-full rounded-lg border border-line bg-white px-3"
      >
        <option value="">{t("any")}</option>
        {values.map((v) => (
          <option key={v} value={v}>
            {format(v)}
          </option>
        ))}
      </select>
    </div>
  );
  return (
    <div className="flex gap-3" aria-label={label}>
      {select(idMin, min, onMin, t("from"))}
      {select(idMax, max, onMax, t("to"))}
    </div>
  );
}

export function PreferencesForm({
  profileId,
  existing,
  reference,
  doneHref,
  backHref,
}: {
  profileId: string;
  existing: Pref | null;
  reference: Reference;
  doneHref: string;
  backHref: string | null;
}) {
  const t = useTranslations("preferences");
  const tc = useTranslations("options.criterion");
  const tp = useTranslations("profile");
  const { options, places } = useChoices();
  const placeName = usePlaceName();
  const opts = reference.options.options;
  const { busy, error, save } = useSave();
  const router = useRouter();
  const [saved, setSaved] = useState(false);

  const initialImportance = {} as Record<Criterion, Importance>;
  for (const c of ["age", "height", "marital_status", "location", "education", "employment", "income", "diet", "mother_tongue", "community"] as Criterion[]) {
    initialImportance[c] = existing?.must_have?.includes(c) ? "must" : existing?.preferred?.includes(c) ? "preferred" : "flexible";
  }
  const [importance, setImp] = useState(initialImportance);
  const setImportance = (c: Criterion, v: Importance) => setImp((p) => ({ ...p, [c]: v }));

  const [v, setV] = useState({
    age_min: existing?.age_min ?? null,
    age_max: existing?.age_max ?? null,
    height_min_cm: existing?.height_min_cm ?? null,
    height_max_cm: existing?.height_max_cm ?? null,
    marital_statuses: (existing?.marital_statuses ?? []) as string[],
    district_codes: existing?.district_codes ?? [],
    education_levels: (existing?.education_levels ?? []) as string[],
    employment_types: (existing?.employment_types ?? []) as string[],
    income_bands: (existing?.income_bands ?? []) as string[],
    diets: (existing?.diets ?? []) as string[],
    mother_tongues: (existing?.mother_tongues ?? []) as string[],
    sub_community_codes: existing?.sub_community_codes ?? [],
  });
  const set = <K extends keyof typeof v>(k: K) => (val: (typeof v)[K]) => setV((p) => ({ ...p, [k]: val }));
  const subs = reference.community.filter((c) => c.type === "sub_community");
  const blockProps = { importance, setImportance };

  async function submit() {
    setSaved(false);
    const entries = Object.entries(importance) as [Criterion, Importance][];
    const body = {
      ...v,
      name: "Default",
      is_default: true,
      must_have: entries.filter(([, i]) => i === "must").map(([c]) => c),
      preferred: entries.filter(([, i]) => i === "preferred").map(([c]) => c),
    };
    const result = existing
      ? await save<Pref>(`/api/v1/preferences/${existing.id}`, body, "PUT")
      : await save<Pref>(`/api/v1/profiles/${profileId}/preferences`, body, "POST");
    if (result) {
      setSaved(true);
      router.push(doneHref);
      router.refresh();
    }
  }

  return (
    <form
      noValidate
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <p className="text-muted">{t("intro")}</p>
      <Block title={t("ageRange")} criterion="age" {...blockProps}>
        <Range label={t("ageRange")} values={AGES} min={v.age_min} max={v.age_max} onMin={set("age_min")} onMax={set("age_max")} format={String} />
      </Block>
      <Block title={t("heightRange")} criterion="height" {...blockProps}>
        <Range label={t("heightRange")} values={HEIGHTS_CM.filter((h) => h % 2 === 0)} min={v.height_min_cm} max={v.height_max_cm} onMin={set("height_min_cm")} onMax={set("height_max_cm")} format={heightLabel} />
      </Block>
      <Block title={tc("marital_status")} criterion="marital_status" {...blockProps}>
        <CheckboxChips legend={t("maritalStatuses")} name="pref-marital" values={v.marital_statuses} onChange={set("marital_statuses")} choices={options("marital_status", opts.marital_status!)} hint={t("anyHint")} />
      </Block>
      <Block title={tc("location")} criterion="location" {...blockProps}>
        <div className="max-h-60 overflow-y-auto rounded-md border border-line p-2">
          <CheckboxChips legend={t("districts")} name="pref-district" values={v.district_codes} onChange={set("district_codes")} choices={places(reference.tnDistricts)} />
        </div>
      </Block>
      <Block title={tc("education")} criterion="education" {...blockProps}>
        <CheckboxChips legend={t("education")} name="pref-education" values={v.education_levels} onChange={set("education_levels")} choices={options("education_level", opts.education_level!)} />
      </Block>
      <Block title={tc("employment")} criterion="employment" {...blockProps}>
        <CheckboxChips legend={t("employment")} name="pref-employment" values={v.employment_types} onChange={set("employment_types")} choices={options("employment_type", opts.employment_type!)} />
      </Block>
      <Block title={tc("income")} criterion="income" {...blockProps}>
        <CheckboxChips legend={t("income")} name="pref-income" values={v.income_bands} onChange={set("income_bands")} choices={options("income_band", opts.income_band!)} />
      </Block>
      <Block title={tc("diet")} criterion="diet" {...blockProps}>
        <CheckboxChips legend={t("diets")} name="pref-diet" values={v.diets} onChange={set("diets")} choices={options("diet", opts.diet!)} />
      </Block>
      <Block title={tc("mother_tongue")} criterion="mother_tongue" {...blockProps}>
        <CheckboxChips legend={t("motherTongues")} name="pref-tongue" values={v.mother_tongues} onChange={set("mother_tongues")} choices={options("language", opts.language!)} />
      </Block>
      <Block title={tc("community")} criterion="community" {...blockProps}>
        <CheckboxChips legend={t("subCommunities")} name="pref-community" values={v.sub_community_codes} onChange={set("sub_community_codes")} choices={subs.map((c) => ({ value: c.code, label: placeName({ code: c.code, name_en: c.label_en, name_ta: c.label_ta }) }))} />
      </Block>
      <FormError message={error} />
      {saved && <p role="status" className="text-sm text-success">{tp("saved")}</p>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
        {backHref ? (
          <Link href={backHref} className="min-h-11 px-2 py-3 font-medium text-primary underline">
            {tp("back")}
          </Link>
        ) : (
          <span />
        )}
        <button type="submit" disabled={busy} className={primaryButton} data-testid="step-save">
          {busy ? tp("saving") : tp("saveFinish")}
        </button>
      </div>
    </form>
  );
}
