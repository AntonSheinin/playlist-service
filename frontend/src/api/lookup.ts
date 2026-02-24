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

export function lookupChannels(limit = 500): Promise<ChannelLookup[]> {
  return get<ChannelLookup[]>(`/api/v1/lookup/channels?limit=${limit}`);
}
