import type { UserCreate, UserResponse, UserUpdate } from "../api/types";

function sameAssignments(ids: number[], saved: { id: number }[]): boolean {
  return ids.length === saved.length && saved.every((item) => ids.includes(item.id));
}

export function buildUserUpdate(
  user: UserResponse,
  values: UserCreate & { playlist_name: string }
): UserUpdate {
  const update: UserUpdate = {};
  if (values.first_name !== user.first_name) update.first_name = values.first_name;
  if (values.last_name !== user.last_name) update.last_name = values.last_name;
  if (values.agreement_number !== user.agreement_number) update.agreement_number = values.agreement_number;
  if (values.playlist_name !== user.playlist_name) update.playlist_name = values.playlist_name;
  if (values.max_sessions !== user.max_sessions) update.max_sessions = values.max_sessions;
  if (values.status !== user.status) update.status = values.status;
  if (values.portal_allowed !== user.portal_allowed) update.portal_allowed = values.portal_allowed;

  if (!sameAssignments(values.tariff_ids, user.tariffs)) update.tariff_ids = values.tariff_ids;
  if (!sameAssignments(values.package_ids, user.packages)) update.package_ids = values.package_ids;
  if (!sameAssignments(values.channel_ids, user.channels)) update.channel_ids = values.channel_ids;

  // The form edits dates only. Omit unchanged dates to preserve their exact timestamps.
  if (values.valid_from?.split("T")[0] !== user.valid_from?.split("T")[0]) {
    if (values.valid_from) update.valid_from = values.valid_from;
    else update.clear_valid_from = true;
  }
  if (values.valid_until?.split("T")[0] !== user.valid_until?.split("T")[0]) {
    if (values.valid_until) update.valid_until = values.valid_until;
    else update.clear_valid_until = true;
  }
  return update;
}
