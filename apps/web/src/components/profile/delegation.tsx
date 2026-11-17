"use client";

import { CheckboxChips, FormError, SelectField, TextField, primaryButton, secondaryButton, useSave } from "@/components/form";
import { useRouter } from "@/i18n/navigation";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useChoices } from "./labels";

const SCOPES = ["edit_profile", "manage_photos", "manage_preferences"];

export function InvitationCard({ invite }: { invite: Schemas["InvitationOut"] }) {
  const t = useTranslations("delegation");
  const { options, label } = useChoices();
  const router = useRouter();
  const { busy, error, save } = useSave();
  const [scopes, setScopes] = useState<string[]>(invite.proposed_scopes);
  const subject = invite.kind === "subject_consent";
  const inviter = invite.invited_by_phone_masked ?? "";

  return (
    <article className="space-y-3 rounded-card-lg border border-gold/60 bg-accent-soft/50 p-5" data-testid="invitation">
      <h3 className="font-serif text-lg font-semibold text-ink">
        {subject ? t("subjectInvite", { inviter }) : t("helperInvite", { name: invite.profile_display_name ?? invite.subject_name })}
      </h3>
      <p className="text-sm text-muted">
        {subject
          ? t("subjectInviteBody")
          : t("helperInviteBody", { scopes: invite.proposed_scopes.map((s) => label("scope", s)).join(", ") })}
      </p>
      {subject && (
        <CheckboxChips legend={t("chooseScopes")} name="scope" values={scopes} onChange={setScopes} choices={options("scope", SCOPES)} />
      )}
      <FormError message={error} />
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className={primaryButton}
          disabled={busy}
          data-testid="accept-invitation"
          onClick={async () => {
            const r = await save<{ profile_id: string }>(
              `/api/v1/delegations/${invite.id}/accept`,
              subject ? { scopes } : {},
              "POST",
            );
            if (r) {
              router.push(`/app/profile/${r.profile_id}`);
              router.refresh();
            }
          }}
        >
          {t("accept")}
        </button>
        <button
          type="button"
          className={secondaryButton}
          disabled={busy}
          data-testid="decline-invitation"
          onClick={async () => {
            if ((await save(`/api/v1/delegations/${invite.id}/decline`, undefined, "POST")) !== null) router.refresh();
          }}
        >
          {t("decline")}
        </button>
      </div>
    </article>
  );
}

export function HelpersManager({
  profileId,
  delegates,
}: {
  profileId: string;
  delegates: Schemas["DelegateSummary"][];
}) {
  const t = useTranslations("delegation");
  const tf = useTranslations("profile.fields");
  const { options, label } = useChoices();
  const router = useRouter();
  const { busy, error, invalid, save } = useSave();
  const [phone, setPhone] = useState("");
  const [relationship, setRelationship] = useState<string | null>("relative");
  const [scopes, setScopes] = useState<string[]>(["edit_profile", "manage_photos"]);

  return (
    <div className="space-y-6">
      {delegates.length === 0 ? (
        <p className="text-muted">{t("noHelpers")}</p>
      ) : (
        <ul className="divide-y divide-line" data-testid="helpers-list">
          {delegates.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium text-ink">
                  {d.phone_masked} · {label("created_for", d.relationship)}
                </p>
                <p className="text-sm text-subtle">
                  {d.status === "invited" ? t("invited") : t("active")} — {d.scopes.map((s) => label("scope", s)).join(", ")}
                </p>
              </div>
              <button
                type="button"
                className="min-h-11 font-medium text-danger underline"
                onClick={async () => {
                  if ((await save(`/api/v1/delegates/${d.id}`, undefined, "DELETE")) !== null) router.refresh();
                }}
              >
                {d.is_me ? t("leave") : t("remove")}
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        noValidate
        className="space-y-4 rounded-card border border-line p-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const r = await save(`/api/v1/profiles/${profileId}/delegates`, { phone, relationship, scopes }, "POST");
          if (r) {
            setPhone("");
            router.refresh();
          }
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label={t("invitePhone")} name="helper_phone" type="tel" inputMode="tel" value={phone} onChange={setPhone} invalid={invalid.has("phone")} />
          <SelectField label={t("relationship")} name="relationship" value={relationship} placeholder={tf("select")} onChange={setRelationship} choices={options("created_for", ["son", "daughter", "brother", "sister", "relative", "friend"])} />
        </div>
        <CheckboxChips legend={t("chooseScopes")} name="helper-scope" values={scopes} onChange={setScopes} choices={options("scope", SCOPES)} />
        <FormError message={error} />
        <button type="submit" className={primaryButton} disabled={busy || !phone || !relationship}>
          {t("invite")}
        </button>
      </form>
    </div>
  );
}
