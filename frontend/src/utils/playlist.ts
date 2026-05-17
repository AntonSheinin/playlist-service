export function sanitizePlaylistPart(value: string): string {
  if (!value) return "";
  const withUnderscores = value.replace(/ /g, "_");
  return Array.from(withUnderscores)
    .filter((char) => /[\p{L}\p{N}_-]/u.test(char))
    .join("");
}

export function buildPlaylistFilename(
  firstName: string,
  lastName: string,
  agreementNumber: string
): string {
  const safeFirst = sanitizePlaylistPart(firstName);
  const safeLast = sanitizePlaylistPart(lastName);
  const safeAgreement = sanitizePlaylistPart(agreementNumber);
  if (!safeFirst || !safeLast || !safeAgreement) return "";
  return `${safeLast}_${safeFirst}_${safeAgreement}.m3u8`;
}

export function buildPlaylistUrl(
  firstName: string,
  lastName: string,
  agreementNumber: string
): string {
  const filename = buildPlaylistFilename(firstName, lastName, agreementNumber);
  if (!filename) return "";
  return `${window.location.origin}/${filename}`;
}
