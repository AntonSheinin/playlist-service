import { get, post, patch, del } from "./client";
import type { TariffWithCount } from "./types";

export function listTariffs(): Promise<TariffWithCount[]> {
  return get<TariffWithCount[]>("/api/v1/tariffs");
}

export function createTariff(data: {
  name: string;
  description?: string | null;
  package_ids: number[];
}): Promise<TariffWithCount> {
  return post<TariffWithCount>("/api/v1/tariffs", data);
}

export function updateTariff(
  id: number,
  data: {
    name?: string;
    description?: string | null;
    package_ids?: number[];
  }
): Promise<TariffWithCount> {
  return patch<TariffWithCount>(`/api/v1/tariffs/${id}`, data);
}

export function deleteTariff(id: number): Promise<void> {
  return del<void>(`/api/v1/tariffs/${id}`);
}
