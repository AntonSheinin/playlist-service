export function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

export function formatDateTime(isoString: string | null): string {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleString();
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function truncateText(
  text: string | null | undefined,
  maxLength: number
): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}
