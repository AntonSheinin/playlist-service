export type SyncStatus = "synced" | "orphaned";
export type UserStatus = "enabled" | "disabled";

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Auth
export interface AdminResponse {
  id: number;
  username: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

// Dashboard
export interface DashboardStats {
  channels_total: number;
  channels_synced: number;
  channels_orphaned: number;
  groups: number;
  packages: number;
  tariffs: number;
  users: number;
  users_enabled: number;
  users_disabled: number;
  last_sync: string | null;
}

// Lookup types (used in dropdowns and nested responses)
export interface GroupLookup {
  id: number;
  name: string;
}

export interface PackageLookup {
  id: number;
  name: string;
}

export interface TariffLookup {
  id: number;
  name: string;
}

export interface ChannelLookup {
  id: number;
  stream_name: string;
  display_name: string | null;
  tvg_name: string | null;
}

// Group
export interface GroupWithCount {
  id: number;
  name: string;
  sort_order: number;
  channel_count: number;
  created_at: string;
  updated_at: string;
}

// Package
export interface PackageWithCount {
  id: number;
  name: string;
  description: string | null;
  channel_count: number;
  created_at: string;
  updated_at: string;
}

export interface PackageDetail {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  channels: ChannelLookup[];
}

// Tariff
export interface TariffWithCount {
  id: number;
  name: string;
  description: string | null;
  packages: PackageLookup[];
  package_count: number;
  created_at: string;
  updated_at: string;
}

export interface TariffDeleteInfo {
  users: number;
}

// Channel
export interface ChannelResponse {
  id: number;
  stream_name: string;
  tvg_name: string | null;
  display_name: string | null;
  catchup_days: number | null;
  tvg_id: string | null;
  tvg_logo: string | null;
  channel_number: number | null;
  sort_order: number;
  sync_status: SyncStatus;
  groups: GroupLookup[];
  packages: PackageLookup[];
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelCascadeInfo {
  packages: number;
  users: number;
}

export interface SyncResultResponse {
  total: number;
  new: number;
  updated: number;
  orphaned: number;
}

export interface ChannelBulkUpdateItem {
  id: number;
  tvg_id?: string | null;
  tvg_logo?: string | null;
  channel_number?: number | null;
}

export interface LogoUploadResponse {
  url: string;
}

// User
export interface UserListItem {
  id: number;
  first_name: string;
  last_name: string;
  agreement_number: string;
  status: UserStatus;
  max_sessions: number;
  created_at: string;
  tariffs: TariffLookup[];
}

export interface UserResponse {
  id: number;
  first_name: string;
  last_name: string;
  agreement_number: string;
  max_sessions: number;
  status: UserStatus;
  valid_from: string | null;
  valid_until: string | null;
  token: string;
  auth_token_id: number | null;
  tariffs: TariffLookup[];
  packages: PackageLookup[];
  channels: ChannelLookup[];
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  first_name: string;
  last_name: string;
  agreement_number: string;
  max_sessions: number;
  status: UserStatus;
  valid_from?: string | null;
  valid_until?: string | null;
  tariff_ids: number[];
  package_ids: number[];
  channel_ids: number[];
}

export interface UserUpdate {
  first_name?: string;
  last_name?: string;
  agreement_number?: string;
  max_sessions?: number;
  status?: UserStatus;
  valid_from?: string | null;
  valid_until?: string | null;
  clear_valid_from?: boolean;
  clear_valid_until?: boolean;
  tariff_ids?: number[];
  package_ids?: number[];
  channel_ids?: number[];
}

export interface ResolvedChannel {
  id: number;
  stream_name: string;
  display_name: string | null;
  tvg_name: string | null;
  group_names: string[];
}

export interface PlaylistPreview {
  filename: string;
  content: string;
  channel_count: number;
}

// Session / Access log (fields from Auth Service, mapped)
export interface SessionEntry {
  started_at: string;
  ended_at: string | null;
  duration: number | null;
  ip: string | null;
  channel: string | null;
  user_agent: string | null;
}

export interface AccessLogEntry {
  accessed_at: string;
  ip: string | null;
  channel: string | null;
  action: string | null;
  user_agent: string | null;
}
