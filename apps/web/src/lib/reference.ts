import "server-only";

import type { Schemas } from "@vaibhav/api-client";
import { API_URL } from "./api-server";

export type Options = Schemas["OptionsOut"];
export type Place = Schemas["LocationOut"];
export type Community = Schemas["CommunityOut"];

/** Public, cacheable reference data (no auth). Revalidated hourly. */
async function getPublic<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}/api/v1/reference${path}`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`reference ${path}: ${res.status}`);
  return (await res.json()) as T;
}

export const getOptions = () => getPublic<Options>("/options");
export const getCountries = () => getPublic<Place[]>("/locations");
export const getIndianStates = () => getPublic<Place[]>("/locations?parent=IN");
export const getTnDistricts = () => getPublic<Place[]>("/locations?parent=in-tn");
export const getAllCities = () => getPublic<Place[]>("/locations?type=city");
export const getCommunity = () => getPublic<Community[]>("/community");

export interface ReferenceBundle {
  options: Options;
  countries: Place[];
  states: Place[];
  tnDistricts: Place[];
  cities: Place[];
  community: Community[];
}

export async function getReferenceBundle(): Promise<ReferenceBundle> {
  const [options, countries, states, tnDistricts, cities, community] = await Promise.all([
    getOptions(),
    getCountries(),
    getIndianStates(),
    getTnDistricts(),
    getAllCities(),
    getCommunity(),
  ]);
  return { options, countries, states, tnDistricts, cities, community };
}
