import "server-only";

import type { Schemas } from "@vaibhav/api-client";
import { notFound, redirect } from "next/navigation";
import { ApiError, apiGet } from "./api-server";

export type ManagedProfile = Schemas["ProfileManageOut"];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** A profile the signed-in user manages, or 404. */
export async function loadManagedProfile(id: string, locale: string): Promise<ManagedProfile> {
  if (!UUID.test(id)) notFound();
  try {
    const p = await apiGet<ManagedProfile | Schemas["MemberProfileOut"]>(`/profiles/${id}`);
    if (!("my_role" in p)) notFound(); // someone else's profile: not editable here
    return p;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && e.status === 401) {
      redirect(`/api/auth/expired?locale=${encodeURIComponent(locale)}`);
    }
    throw e;
  }
}
