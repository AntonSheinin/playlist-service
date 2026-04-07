import type { ChannelLookup, ChannelResponse, ResolvedChannel, StreamSource } from "../api/types";

type ChannelIdentity = Pick<ChannelLookup, "source" | "stream_name" | "display_name" | "tvg_name">;
type ChannelLike = ChannelIdentity | Pick<ChannelResponse, "source" | "stream_name" | "display_name" | "tvg_name"> | Pick<ResolvedChannel, "source" | "stream_name" | "display_name" | "tvg_name">;

export function formatStreamSource(source: StreamSource): string {
  return source === "flussonic" ? "Flussonic" : "Nimble";
}

export function formatChannelPrimary(channel: ChannelLike): string {
  return channel.display_name || channel.tvg_name || channel.stream_name;
}

export function formatChannelSecondary(channel: ChannelLike): string {
  return `${formatStreamSource(channel.source)} • ${channel.stream_name}`;
}

export function formatChannelOptionLabel(channel: ChannelLike): string {
  return `${formatChannelPrimary(channel)} [${formatStreamSource(channel.source)}]`;
}
