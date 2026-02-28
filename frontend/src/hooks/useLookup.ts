import { useQuery } from "@tanstack/react-query";
import {
  lookupGroups,
  lookupPackages,
  lookupTariffs,
  lookupChannels,
} from "../api/lookup";
import { queryKeys } from "./queryKeys";

export function useLookupGroups() {
  return useQuery({
    queryKey: queryKeys.lookup.groups(),
    queryFn: lookupGroups,
    staleTime: 30_000,
  });
}

export function useLookupPackages() {
  return useQuery({
    queryKey: queryKeys.lookup.packages(),
    queryFn: lookupPackages,
    staleTime: 30_000,
  });
}

export function useLookupTariffs() {
  return useQuery({
    queryKey: queryKeys.lookup.tariffs(),
    queryFn: lookupTariffs,
    staleTime: 30_000,
  });
}

export function useLookupChannels() {
  return useQuery({
    queryKey: queryKeys.lookup.channels(),
    queryFn: () => lookupChannels(),
    staleTime: 30_000,
  });
}
