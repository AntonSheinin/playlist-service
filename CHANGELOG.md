# Changelog

## Unreleased

### Added

- Added separate Auth and Proxy Portal sync indicators to the users table and
  account details, with **Sync Auth** and **Sync Portal** retry actions.
- Added direct Portal Proxy synchronization for account changes, playlist
  assignments, suspension, and deletion. Staff can resync a saved account, and
  operators can check payload sizes and backfill existing accounts.
- Added **Max Portal Devices** for accounts with Portal access. The limit
  defaults to 1. Migrations `008` and `009` add sync tracking and the device limit.
- Added editable, persistent playlist URL names in user details and migration
  `007` to preserve existing filenames with case-insensitive uniqueness.
- Added a per-user Propy portal permission, editable in the admin user form and
  visible in user responses from the admin and Integration APIs.
- Added a sortable Portal allowed column to the users table. Sorting returns to
  page 1 and uses stable ordering for users with equal permissions.
- Added migration `006` to initialize existing users with portal access denied.
  New users also default to denied.

### Changed

- Admin saves now show a warning when Auth sync fails and keep the account
  available for retry. Account deletion waits for Auth token revocation.
- Moved service contract documentation into the README and removed the separate
  specification.
- Renamed Playlist Service to RuTV Middleware in the admin UI, API
  documentation, and MCP. Existing playlist links keep working.
- Unified public playlist delivery, admin downloads, and previews in an internal
  playlist service, replacing the full-user filename scan with indexed lookup.
- Personal-detail edits now preserve playlist names. Explicit renames replace
  the public URL immediately; configured players must be updated. No previous-name
  aliases are retained. Lookup now uses PostgreSQL `lower()` semantics.
- Kept portal permission independent of playback access, account status, and
  validity dates. Propy reads and enforces the permission.
- Excluded local media, scratch folders, environment files, and caches from Git
  and Docker build contexts. Removed previously tracked media and local Claude
  settings from the repository while preserving working copies.
- Stopped uploading media during deployment. Media is provisioned separately on
  each host, and existing server media is preserved.

### Fixed

- Deployments now complete database migrations before starting the updated
  middleware and MCP services.
- Fixed Auth retries failing to clear a removed validity date and token rotation
  retries leaving the previous token active.
- Fixed unrelated user edits changing validity times. Playlist-name-only edits
  now preserve exact validity timestamps and do not trigger Auth synchronization.
- Fixed successful playlist renames leaving the old URL displayed when the
  background refresh fails. The saved URL now updates immediately after saving.
- Corrected the user PATCH OpenAPI schema so portal permission has no misleading
  null default. Omitting the field preserves its value; explicit null is rejected.
