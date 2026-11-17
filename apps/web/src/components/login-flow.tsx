"use client";

import { Link, useRouter } from "@/i18n/navigation";
import { errorKey, postJson } from "@/lib/errors";
import type { Locale } from "@vaibhav/localization";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";

interface Challenge {
  challenge_id: string;
  expires_in: number;
  resend_after: number;
  phone_masked: string;
  debug_code?: string | null;
}

const inputClass =
  "block w-full min-h-12 rounded-lg border border-line bg-white px-4 text-lg text-ink placeholder:text-subtle aria-[invalid=true]:border-danger";
const buttonClass =
  "inline-flex min-h-12 w-full items-center justify-center rounded-full bg-primary px-6 font-semibold text-white hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60";

export function LoginFlow() {
  const t = useTranslations("auth");
  const tErr = useTranslations("errors");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const ids = { phone: useId(), phoneHint: useId(), err: useId(), otp: useId(), terms: useId() };

  const [phone, setPhone] = useState("");
  const [terms, setTerms] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const otpRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  useEffect(() => {
    if (challenge) otpRef.current?.focus();
  }, [challenge]);

  function showError(e: { code?: string; details?: Record<string, unknown> | null } | undefined) {
    setError(tErr(errorKey(e?.code)));
    const retry = Number(e?.details?.retry_after);
    if (e?.code === "otp_cooldown" && retry > 0) setCooldown(retry);
  }

  async function requestOtp(ev: FormEvent) {
    ev.preventDefault();
    if (!terms) {
      setError(tErr("consent_required"));
      return;
    }
    setBusy(true);
    setError(null);
    const r = await postJson<Challenge>("/api/auth/request-otp", { phone, language: locale });
    setBusy(false);
    if (!r.ok) return showError(r.error);
    setChallenge(r.data);
    setCode("");
    setCooldown(r.data.resend_after);
  }

  async function resend() {
    if (!challenge || cooldown > 0) return;
    setBusy(true);
    setError(null);
    const r = await postJson<Challenge>("/api/auth/resend-otp", {
      challenge_id: challenge.challenge_id,
    });
    setBusy(false);
    if (!r.ok) {
      if (r.error?.code === "otp_expired") setChallenge(null);
      return showError(r.error);
    }
    setChallenge(r.data);
    setCode("");
    setCooldown(r.data.resend_after);
  }

  async function verify(ev: FormEvent) {
    ev.preventDefault();
    if (!challenge) return;
    setBusy(true);
    setError(null);
    const r = await postJson<{ is_new_user: boolean; preferred_language: Locale }>(
      "/api/auth/verify-otp",
      {
        challenge_id: challenge.challenge_id,
        code,
        language: locale,
        consents: { terms, privacy: terms, marketing },
      },
    );
    if (!r.ok) {
      setBusy(false);
      if (r.error?.code === "otp_expired" || r.error?.code === "otp_too_many_attempts") {
        setChallenge(null);
      }
      return showError(r.error);
    }
    const target = r.data.is_new_user ? "/app?welcome=1" : "/app";
    router.replace(target, { locale: r.data.preferred_language });
    router.refresh();
  }

  const errorBox = error && (
    <p id={ids.err} role="alert" data-testid="form-error" className="rounded-md bg-danger-soft px-4 py-3 text-sm text-danger">
      {error}
    </p>
  );

  if (!challenge) {
    return (
      <form onSubmit={requestOtp} className="space-y-5" noValidate>
        <div className="space-y-2">
          <label htmlFor={ids.phone} className="block font-medium text-ink">
            {t("phoneLabel")}
          </label>
          <div className="flex items-stretch gap-2">
            <span className="inline-flex min-h-12 items-center rounded-lg border border-line bg-bg px-3 text-lg text-muted">
              +91
            </span>
            <input
              id={ids.phone}
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel-national"
              required
              placeholder={t("phonePlaceholder")}
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-describedby={`${ids.phoneHint}${error ? ` ${ids.err}` : ""}`}
              aria-invalid={error ? true : undefined}
              className={inputClass}
              data-testid="phone-input"
            />
          </div>
          <p id={ids.phoneHint} className="text-sm text-subtle">
            {t("phoneHint")}
          </p>
        </div>

        <div className="space-y-3 text-sm">
          <label className="flex items-start gap-3">
            <input
              id={ids.terms}
              type="checkbox"
              checked={terms}
              onChange={(e) => setTerms(e.target.checked)}
              className="mt-1 size-5 shrink-0 accent-[var(--vb-primary)]"
              data-testid="consent-terms"
            />
            <span className="text-ink">
              {t.rich("consentTerms", {
                terms: (c) => (
                  <Link href="/terms" target="_blank" className="font-medium text-primary underline">
                    {c}
                  </Link>
                ),
                privacy: (c) => (
                  <Link href="/privacy" target="_blank" className="font-medium text-primary underline">
                    {c}
                  </Link>
                ),
              })}
            </span>
          </label>
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={marketing}
              onChange={(e) => setMarketing(e.target.checked)}
              className="mt-1 size-5 shrink-0 accent-[var(--vb-primary)]"
            />
            <span className="text-muted">{t("consentMarketing")}</span>
          </label>
        </div>

        {errorBox}
        <button type="submit" disabled={busy || cooldown > 0} className={buttonClass} data-testid="send-code">
          {busy ? t("sending") : cooldown > 0 ? t("resendIn", { seconds: cooldown }) : t("sendCode")}
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={verify} className="space-y-5" noValidate>
      <div className="space-y-1">
        <h2 className="font-serif text-2xl font-semibold text-ink">{t("otpTitle")}</h2>
        <p className="text-muted">{t("otpSubtitle", { phone: challenge.phone_masked })}</p>
      </div>
      {challenge.debug_code && (
        <p className="rounded-md border border-dashed border-gold bg-accent-soft px-4 py-2 text-sm text-ink" data-testid="dev-code">
          {t("devCode", { code: challenge.debug_code })}
        </p>
      )}
      <div className="space-y-2">
        <label htmlFor={ids.otp} className="block font-medium text-ink">
          {t("otpLabel")}
        </label>
        <input
          ref={otpRef}
          id={ids.otp}
          name="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="\d*"
          maxLength={6}
          required
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          aria-describedby={error ? ids.err : undefined}
          aria-invalid={error ? true : undefined}
          className={`${inputClass} text-center font-mono tracking-[0.5em]`}
          data-testid="otp-input"
        />
      </div>
      <p className="text-sm text-subtle">{t("neverShare")}</p>
      {errorBox}
      <button type="submit" disabled={busy || code.length < 6} className={buttonClass} data-testid="verify">
        {busy ? t("verifying") : t("verify")}
      </button>
      <div className="flex flex-wrap justify-between gap-2 text-sm">
        <button
          type="button"
          onClick={() => {
            setChallenge(null);
            setError(null);
          }}
          className="min-h-11 font-medium text-primary underline"
        >
          {t("changeNumber")}
        </button>
        <button
          type="button"
          onClick={resend}
          disabled={busy || cooldown > 0}
          className="min-h-11 font-medium text-primary underline disabled:text-subtle disabled:no-underline"
        >
          {cooldown > 0 ? t("resendIn", { seconds: cooldown }) : t("resend")}
        </button>
      </div>
    </form>
  );
}
