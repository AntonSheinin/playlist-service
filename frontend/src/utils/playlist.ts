export function buildPlaylistUrl(playlistName: string): string {
  return `${window.location.origin}/${encodeURIComponent(playlistName)}.m3u8`;
}
