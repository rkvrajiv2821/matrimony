"use client";

import { errorKey, postJson, type ApiErrorJson } from "@/lib/errors";
import { useTranslations } from "next-intl";
import { useId, useState, type ReactNode } from "react";

export const inputClass =
  "block w-full min-h-12 rounded-lg border border-line bg-white px-3 text-base text-ink placeholder:text-subtle aria-[invalid=true]:border-danger disabled:bg-bg";
export const primaryButton =
  "inline-flex min-h-12 items-center justify-center rounded-full bg-primary px-6 font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60";
export const secondaryButton =
  "inline-flex min-h-12 items-center justify-center rounded-full border border-primary px-6 font-semibold text-primary hover:bg-primary-soft disabled:opacity-60";
export const linkButton = "min-h-11 font-medium text-primary underline disabled:text-subtle";

/** Form state holds plain strings; the API validates codes. */
export type Widen<T> = {
  [K in keyof T]: T[K] extends string | null | undefined ? string | null : T[K];
};
export function widen<T>(value: T): Widen<T> {
  return value as Widen<T>;
}

export interface Choice {
  value: string;
  label: string;
}

export function Field({
  label,
  hint,
  invalid,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  invalid?: boolean;
  children: ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className={`block font-medium ${invalid ? "text-danger" : "text-ink"}`}>
        {label}
      </label>
      {children}
      {hint && <p className="text-sm text-subtle">{hint}</p>}
    </div>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  choices,
  hint,
  placeholder,
  invalid,
  name,
  disabled,
}: {
  label: string;
  value: string | null | undefined;
  onChange: (v: string | null) => void;
  choices: Choice[];
  hint?: string;
  placeholder?: string;
  invalid?: boolean;
  name?: string;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} invalid={invalid} htmlFor={id}>
      <select
        id={id}
        name={name}
        value={value ?? ""}
        disabled={disabled}
        aria-invalid={invalid || undefined}
        onChange={(e) => onChange(e.target.value || null)}
        className={inputClass}
        data-testid={name ? `field-${name}` : undefined}
      >
        <option value="">{placeholder ?? "—"}</option>
        {choices.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

export function TextField({
  label,
  value,
  onChange,
  hint,
  invalid,
  name,
  type = "text",
  maxLength,
  placeholder,
  inputMode,
  autoComplete,
}: {
  label: string;
  value: string | null | undefined;
  onChange: (v: string) => void;
  hint?: string;
  invalid?: boolean;
  name?: string;
  type?: string;
  maxLength?: number;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "tel";
  autoComplete?: string;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} invalid={invalid} htmlFor={id}>
      <input
        id={id}
        name={name}
        type={type}
        value={value ?? ""}
        maxLength={maxLength}
        placeholder={placeholder}
        inputMode={inputMode}
        autoComplete={autoComplete}
        aria-invalid={invalid || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
        data-testid={name ? `field-${name}` : undefined}
      />
    </Field>
  );
}

export function TextArea({
  label,
  value,
  onChange,
  hint,
  invalid,
  name,
  maxLength = 1000,
}: {
  label: string;
  value: string | null | undefined;
  onChange: (v: string) => void;
  hint?: string;
  invalid?: boolean;
  name?: string;
  maxLength?: number;
}) {
  const id = useId();
  const t = useTranslations("profile.fields");
  const left = maxLength - (value?.length ?? 0);
  return (
    <Field label={label} hint={hint} invalid={invalid} htmlFor={id}>
      <textarea
        id={id}
        name={name}
        rows={5}
        value={value ?? ""}
        maxLength={maxLength}
        aria-invalid={invalid || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={`${inputClass} py-2`}
        data-testid={name ? `field-${name}` : undefined}
      />
      <p className="text-right text-xs text-subtle" aria-live="polite">
        {t("charsLeft", { count: left })}
      </p>
    </Field>
  );
}

export function RadioCards({
  legend,
  value,
  onChange,
  choices,
  name,
  columns = 2,
}: {
  legend: string;
  value: string | null | undefined;
  onChange: (v: string) => void;
  choices: Choice[];
  name: string;
  columns?: 2 | 3;
}) {
  return (
    <fieldset className="space-y-1.5">
      <legend className="mb-1.5 font-medium text-ink">{legend}</legend>
      <div className={`grid gap-2 ${columns === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
        {choices.map((c) => (
          <label
            key={c.value}
            className="flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-line bg-white px-3 has-[:checked]:border-primary has-[:checked]:bg-primary-soft"
          >
            <input
              type="radio"
              name={name}
              value={c.value}
              checked={value === c.value}
              onChange={() => onChange(c.value)}
              className="size-4 accent-[var(--vb-primary)]"
              data-testid={`${name}-${c.value}`}
            />
            <span className="text-ink">{c.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function CheckboxChips({
  legend,
  values,
  onChange,
  choices,
  name,
  hint,
}: {
  legend: string;
  values: string[];
  onChange: (v: string[]) => void;
  choices: Choice[];
  name: string;
  hint?: string;
}) {
  return (
    <fieldset className="space-y-1.5">
      <legend className="mb-1.5 font-medium text-ink">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {choices.map((c) => {
          const checked = values.includes(c.value);
          return (
            <label
              key={c.value}
              className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-line bg-white px-3 text-sm has-[:checked]:border-primary has-[:checked]:bg-primary-soft"
            >
              <input
                type="checkbox"
                className="size-4 accent-[var(--vb-primary)]"
                checked={checked}
                data-testid={`${name}-${c.value}`}
                onChange={() =>
                  onChange(checked ? values.filter((v) => v !== c.value) : [...values, c.value])
                }
              />
              {c.label}
            </label>
          );
        })}
      </div>
      {hint && <p className="text-sm text-subtle">{hint}</p>}
    </fieldset>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" data-testid="form-error" className="rounded-md bg-danger-soft px-4 py-3 text-sm text-danger">
      {message}
    </p>
  );
}

/** Save helper that maps API error codes to localized messages and invalid field names. */
export function useSave() {
  const tErr = useTranslations("errors");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invalid, setInvalid] = useState<Set<string>>(new Set());

  async function save<T>(
    url: string,
    body: unknown,
    method: "POST" | "PUT" | "PATCH" | "DELETE" = "PUT",
  ): Promise<T | null> {
    setBusy(true);
    setError(null);
    setInvalid(new Set());
    const r = await postJson<T>(url, body, method);
    setBusy(false);
    if (r.ok) return r.data;
    showError(r.error);
    return null;
  }

  function showError(e: ApiErrorJson["error"]) {
    setError(tErr(errorKey(e?.code)));
    const fields = (e?.details?.fields as { loc: (string | number)[] }[] | undefined) ?? [];
    const named = fields.map((f) => String(f.loc[f.loc.length - 1]));
    const single = e?.details?.field;
    setInvalid(new Set([...named, ...(typeof single === "string" ? [single] : [])]));
  }

  return { busy, error, invalid, save, setError, showError };
}
