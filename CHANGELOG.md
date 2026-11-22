# Changelog

## Unreleased

### Added

- Added a per-user Propy portal permission, editable in the admin user form and
  visible in user responses from the admin and Integration APIs.
- Added a sortable Portal allowed column to the users table. Sorting returns to
  page 1 and uses stable ordering for users with equal permissions.
- Added migration `006` to initialize existing users with portal access denied.
  New users also default to denied.

### Changed

- Kept portal permission independent of playback access, account status, and
  validity dates. Propy reads and enforces the permission.
- Excluded local media, scratch folders, environment files, and caches from Git
  and Docker build contexts. Removed previously tracked media and local Claude
  settings from the repository while preserving working copies.
- Stopped uploading media during deployment. Media is provisioned separately on
  each host, and existing server media is preserved.

### Fixed

- Corrected the user PATCH OpenAPI schema so portal permission has no misleading
  null default. Omitting the field preserves its value; explicit null is rejected.
