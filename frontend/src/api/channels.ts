import { get, post, patch, fetchMessage } from "./client";
import type {
  ChannelResponse,
  ChannelCascadeInfo,
  SyncResultResponse,
  ChannelBulkUpdateItem,
  LogoUploadResponse,
  PaginatedData,
} from "./types";

interface ListChannelsParams {
  page?: number;
  per_page?: number;
  search?: string;
  group_id?: number;
  sync_status?: string;
  sort_by?: string;
  sort_dir?: string;
}

export function listChannels(
  params: ListChannelsParams
): Promise<PaginatedData<ChannelResponse>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.per_page) searchParams.set("per_page", String(params.per_page));
  if (params.search) searchParams.set("search", params.search);
  if (params.group_id) searchParams.set("group_id", String(params.group_id));
  if (params.sync_status) searchParams.set("sync_status", params.sync_status);
  if (params.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params.sort_dir) searchParams.set("sort_dir", params.sort_dir);
  return get<PaginatedData<ChannelResponse>>(
    `/api/v1/channels?${searchParams.toString()}`
  );
}

export function getChannel(id: number): Promise<ChannelResponse> {
  return get<ChannelResponse>(`/api/v1/channels/${id}`);
}

export function updateChannel(
  id: number,
  data: { tvg_id?: string | null; tvg_logo?: string | null; channel_number?: number | null }
): Promise<ChannelResponse> {
  return patch<ChannelResponse>(`/api/v1/channels/${id}`, data);
}

export function bulkUpdateChannels(
  channels: ChannelBulkUpdateItem[]
): Promise<string> {
  return fetchMessage("/api/v1/channels", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channels }),
  });
}

export function deleteChannel(
  id: number,
  force = false
): Promise<string> {
  const url = force
    ? `/api/v1/channels/${id}?force=true`
    : `/api/v1/channels/${id}`;
  return fetchMessage(url, { method: "DELETE" });
}

export function updateChannelGroups(
  id: number,
  groupIds: number[]
): Promise<ChannelResponse> {
  return patch<ChannelResponse>(`/api/v1/channels/${id}/groups`, {
    group_ids: groupIds,
  });
}

export function updateChannelPackages(
  id: number,
  packageIds: number[]
): Promise<ChannelResponse> {
  return patch<ChannelResponse>(`/api/v1/channels/${id}/packages`, {
    package_ids: packageIds,
  });
}

export function syncChannels(): Promise<SyncResultResponse> {
  return post<SyncResultResponse>("/api/v1/channels/sync");
}

export function getCascadeInfo(id: number): Promise<ChannelCascadeInfo> {
  return get<ChannelCascadeInfo>(`/api/v1/channels/${id}/cascade-info`);
}

export async function uploadLogo(
  channelId: number,
  file: File
): Promise<LogoUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return post<LogoUploadResponse>(`/api/v1/channels/${channelId}/logo`, formData);
}

export function uploadLogoByUrl(
  channelId: number,
  url: string
): Promise<LogoUploadResponse> {
  return post<LogoUploadResponse>(`/api/v1/channels/${channelId}/logo-url`, {
    url,
  });
}

export function removeLogo(
  channelId: number,
  deleteFile: boolean
): Promise<string> {
  return fetchMessage(
    `/api/v1/channels/${channelId}/logo?delete_file=${deleteFile}`,
    { method: "DELETE" }
  );
}
