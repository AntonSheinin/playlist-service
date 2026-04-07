import { get } from "./client";
import type {
  GroupLookup,
  PackageLookup,
  TariffLookup,
  ChannelLookup,
} from "./types";

export function lookupGroups(): Promise<GroupLookup[]> {
  return get<GroupLookup[]>("/api/v1/lookup/groups");
}

export function lookupPackages(): Promise<PackageLookup[]> {
  return get<PackageLookup[]>("/api/v1/lookup/packages");
}

export function lookupTariffs(): Promise<TariffLookup[]> {
  return get<TariffLookup[]>("/api/v1/lookup/tariffs");
}

export function lookupChannels(
  search = "",
  limit = 50,
  source?: "flussonic" | "nimble"
): Promise<ChannelLookup[]> {
  const sp = new URLSearchParams();
  if (search) sp.set("search", search);
  sp.set("limit", String(limit));
  if (source) sp.set("source", source);
  return get<ChannelLookup[]>(`/api/v1/lookup/channels?${sp.toString()}`);
}
