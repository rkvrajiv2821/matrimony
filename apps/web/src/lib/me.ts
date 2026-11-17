import "server-only";

import type { Schemas } from "@vaibhav/api-client";
import { redirect } from "next/navigation";
import { cache } from "react";
import { ApiError, apiGet } from "./api-server";

export type Me = Schemas["MeOut"];

/** The signed-in member, or a redirect to login. Cached per request. */
export const requireMe = cache(async (locale: string): Promise<Me> => {
  try {
    return await apiGet<Me>("/users/me");
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      redirect(`/api/auth/expired?locale=${encodeURIComponent(locale)}`);
    }
    throw e;
  }
});
