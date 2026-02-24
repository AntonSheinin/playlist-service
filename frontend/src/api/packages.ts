import { get, post, patch, del, fetchMessage } from "./client";
import type { PackageWithCount, PackageDetail } from "./types";

export function listPackages(): Promise<PackageWithCount[]> {
  return get<PackageWithCount[]>("/api/v1/packages");
}

export function getPackage(id: number): Promise<PackageDetail> {
  return get<PackageDetail>(`/api/v1/packages/${id}`);
}

export function createPackage(data: {
  name: string;
  description?: string | null;
}): Promise<PackageWithCount> {
  return post<PackageWithCount>("/api/v1/packages", data);
}

export function updatePackage(
  id: number,
  data: { name?: string; description?: string | null }
): Promise<PackageWithCount> {
  return patch<PackageWithCount>(`/api/v1/packages/${id}`, data);
}

export function deletePackage(id: number): Promise<void> {
  return del<void>(`/api/v1/packages/${id}`);
}

export function removeChannelFromPackage(
  packageId: number,
  channelId: number
): Promise<string> {
  return fetchMessage(`/api/v1/packages/${packageId}/channels/${channelId}`, {
    method: "DELETE",
  });
}
