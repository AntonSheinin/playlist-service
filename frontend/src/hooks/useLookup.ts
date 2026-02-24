import { useQuery } from "@tanstack/react-query";
import {
  lookupGroups,
  lookupPackages,
  lookupTariffs,
  lookupChannels,
} from "../api/lookup";

export function useLookupGroups() {
  return useQuery({
    queryKey: ["lookup", "groups"],
    queryFn: lookupGroups,
    staleTime: 30_000,
  });
}

export function useLookupPackages() {
  return useQuery({
    queryKey: ["lookup", "packages"],
    queryFn: lookupPackages,
    staleTime: 30_000,
  });
}

export function useLookupTariffs() {
  return useQuery({
    queryKey: ["lookup", "tariffs"],
    queryFn: lookupTariffs,
    staleTime: 30_000,
  });
}

export function useLookupChannels() {
  return useQuery({
    queryKey: ["lookup", "channels"],
    queryFn: () => lookupChannels(),
    staleTime: 30_000,
  });
}
