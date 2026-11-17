"use client";

import { FormError, primaryButton, useSave } from "@/components/form";
import { Link } from "@/i18n/navigation";
import { errorKey, type ApiErrorJson } from "@/lib/errors";
import type { Schemas } from "@vaibhav/api-client";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { useChoices } from "./labels";

type Photo = Schemas["PhotoOut"];
const MAX = 6;
const MAX_BYTES = 8 * 1024 * 1024;

const badge: Record<string, string> = {
  pending: "bg-accent-soft text-accent",
  approved: "bg-success-soft text-success",
  rejected: "bg-danger-soft text-danger",
};

export function PhotoManager({
  profileId,
  initial,
  nextHref,
  backHref,
}: {
  profileId: string;
  initial: Photo[];
  nextHref: string;
  backHref: string | null;
}) {
  const t = useTranslations("photos");
  const tp = useTranslations("profile");
  const tErr = useTranslations("errors");
  const { options, label } = useChoices();
  const { save, error, setError } = useSave();
  const [photos, setPhotos] = useState<Photo[]>(initial);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function reload() {
    const res = await fetch(`/api/v1/profiles/${profileId}`, { cache: "no-store" });
    if (res.ok) setPhotos(((await res.json()) as { photos: Photo[] }).photos);
  }

  async function upload(file: File) {
    setError(null);
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError(tErr("invalid_image"));
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(tErr("image_too_large"));
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("visibility", "members");
    try {
      const res = await fetch(`/api/uploads/photo?profile=${profileId}`, { method: "POST", body: form });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as ApiErrorJson;
        setError(tErr(errorKey(body.error?.code)));
      } else {
        await reload();
      }
    } catch {
      setError(tErr("network"));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <p className="text-muted">{t("intro")}</p>
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3" data-testid="photo-grid">
        {photos.map((p) => (
          <li key={p.id} className="overflow-hidden rounded-card border border-line bg-surface">
            <div className="relative aspect-[4/5] bg-bg">
              {/* eslint-disable-next-line @next/next/no-img-element -- private, authenticated image */}
              <img src={p.thumb_url} alt="" className="size-full object-cover" />
              {p.is_primary && (
                <span className="absolute left-2 top-2 rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-white">
                  {t("primary")}
                </span>
              )}
            </div>
            <div className="space-y-2 p-3 text-sm">
              <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${badge[p.moderation_status]}`}>
                {t(`status.${p.moderation_status}`)}
              </span>
              {p.moderation_reason && (
                <p className="text-xs text-danger">{label("review_reason", p.moderation_reason)}</p>
              )}
              <label className="block">
                <span className="sr-only">{t("visibleTo")}</span>
                <select
                  value={p.visibility}
                  className="min-h-11 w-full rounded-md border border-line bg-white px-2 text-sm"
                  onChange={async (e) => {
                    const r = await save<Photo>(`/api/v1/profiles/${profileId}/photos/${p.id}`, { visibility: e.target.value }, "PATCH");
                    if (r) await reload();
                  }}
                >
                  {options("visibility", ["members", "connections", "hidden"]).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex flex-wrap gap-x-3">
                {!p.is_primary && (
                  <button
                    type="button"
                    className="min-h-11 font-medium text-primary underline"
                    onClick={async () => {
                      if (await save(`/api/v1/profiles/${profileId}/photos/${p.id}`, { is_primary: true }, "PATCH")) await reload();
                    }}
                  >
                    {t("makePrimary")}
                  </button>
                )}
                <button
                  type="button"
                  className="min-h-11 font-medium text-danger underline"
                  onClick={async () => {
                    if (!window.confirm(t("confirmDelete"))) return;
                    await save(`/api/v1/profiles/${profileId}/photos/${p.id}`, undefined, "DELETE");
                    await reload();
                  }}
                >
                  {t("delete")}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {photos.length < MAX ? (
        <div className="space-y-2">
          <label className={`${primaryButton} cursor-pointer ${uploading ? "pointer-events-none opacity-60" : ""}`}>
            {uploading ? t("uploading") : t("add")}
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              data-testid="photo-input"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void upload(f);
              }}
            />
          </label>
          <p className="text-sm text-subtle">{t("hint")}</p>
        </div>
      ) : (
        <p className="text-sm text-muted">{t("limit")}</p>
      )}
      <FormError message={error} />

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
        {backHref ? (
          <Link href={backHref} className="min-h-11 px-2 py-3 font-medium text-primary underline">
            {tp("back")}
          </Link>
        ) : (
          <span />
        )}
        <Link href={nextHref} className={primaryButton} data-testid="step-save">
          {tp("continue")}
        </Link>
      </div>
    </div>
  );
}
