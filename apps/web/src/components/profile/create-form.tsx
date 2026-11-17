"use client";

import { FormError, RadioCards, TextField, primaryButton, useSave } from "@/components/form";
import { useRouter } from "@/i18n/navigation";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useChoices } from "./labels";

const CREATED_FOR = ["self", "son", "daughter", "brother", "sister", "relative", "friend"];

export function CreateProfileForm({ hasOwnProfile }: { hasOwnProfile: boolean }) {
  const t = useTranslations("profile");
  const { options } = useChoices();
  const router = useRouter();
  const { busy, error, invalid, save } = useSave();
  const choices = options("created_for", hasOwnProfile ? CREATED_FOR.slice(1) : CREATED_FOR);
  const [createdFor, setCreatedFor] = useState<string>(hasOwnProfile ? "son" : "self");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [gender, setGender] = useState<string | null>(null);
  const forSelf = createdFor === "self";

  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={async (e) => {
        e.preventDefault();
        const p = await save<Schemas["ProfileManageOut"]>(
          "/api/v1/profiles",
          {
            created_for: createdFor,
            subject_name: name,
            subject_phone: forSelf ? null : phone,
            gender: gender,
          },
          "POST",
        );
        if (p) {
          router.push(forSelf ? `/app/profile/${p.id}/edit/basic` : `/app/profile/${p.id}`);
          router.refresh();
        }
      }}
    >
      <RadioCards legend={t("createIntro")} name="created_for" value={createdFor} onChange={setCreatedFor} choices={choices} columns={3} />
      <TextField label={t("subjectName")} hint={t("subjectNameHint")} name="subject_name" value={name} onChange={setName} invalid={invalid.has("subject_name")} maxLength={100} autoComplete={forSelf ? "name" : "off"} />
      <RadioCards legend={t("gender")} name="gender" value={gender} onChange={setGender} choices={options("gender", ["male", "female"])} />
      {!forSelf && (
        <TextField label={t("subjectPhone")} hint={t("subjectPhoneHint")} name="subject_phone" type="tel" inputMode="tel" value={phone} onChange={setPhone} invalid={invalid.has("subject_phone")} maxLength={20} />
      )}
      <FormError message={error} />
      <button type="submit" disabled={busy || name.trim().length < 2} className={primaryButton} data-testid="create-profile">
        {busy ? t("creating") : t("create")}
      </button>
    </form>
  );
}
