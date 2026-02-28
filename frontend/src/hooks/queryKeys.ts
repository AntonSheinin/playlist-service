export const queryKeys = {
  dashboard: {
    stats: () => ["dashboard-stats"] as const,
  },
  channels: {
    all: () => ["channels"] as const,
    list: (params: unknown) => ["channels", params] as const,
    cascade: (channelId: number | null) => ["channel-cascade", channelId] as const,
  },
  groups: {
    all: () => ["groups"] as const,
  },
  packages: {
    all: () => ["packages"] as const,
    detail: (id: number | undefined) => ["packages", id] as const,
  },
  tariffs: {
    all: () => ["tariffs"] as const,
  },
  lookup: {
    all: () => ["lookup"] as const,
    groups: () => ["lookup", "groups"] as const,
    packages: () => ["lookup", "packages"] as const,
    tariffs: () => ["lookup", "tariffs"] as const,
    channels: () => ["lookup", "channels"] as const,
  },
  users: {
    all: () => ["users"] as const,
    list: (params: unknown) => ["users", params] as const,
    detail: (id: number | undefined) => ["users", id] as const,
    resolvedChannels: (userId: number | undefined) =>
      ["users", userId, "channels"] as const,
    playlist: (userId: number | undefined) =>
      ["users", userId, "playlist"] as const,
    sessions: (userId: number | undefined, params: unknown) =>
      ["users", userId, "sessions", params] as const,
    accessLogs: (userId: number | undefined, params: unknown) =>
      ["users", userId, "access-logs", params] as const,
  },
} as const;
