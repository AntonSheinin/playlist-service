# Changelog

## Unreleased

### Added

- Added editable, persistent playlist URL names in user details and migration
  `007` to preserve existing filenames with case-insensitive uniqueness.
- Added a per-user Propy portal permission, editable in the admin user form and
  visible in user responses from the admin and Integration APIs.
- Added a sortable Portal allowed column to the users table. Sorting returns to
  page 1 and uses stable ordering for users with equal permissions.
- Added migration `006` to initialize existing users with portal access denied.
  New users also default to denied.

### Changed

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

- Fixed unrelated user edits changing validity times. Playlist-name-only edits
  now preserve exact validity timestamps and do not trigger Auth synchronization.
- Fixed successful playlist renames leaving the old URL displayed when the
  background refresh fails. The saved URL now updates immediately after saving.
- Corrected the user PATCH OpenAPI schema so portal permission has no misleading
  null default. Omitting the field preserves its value; explicit null is rejected.
