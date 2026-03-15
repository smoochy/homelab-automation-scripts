# Changelog

## 2026-03-15

### Initial release

- First repository release of `appdata_backup_kuma_maintenance` as an Unraid
  host-side helper for coordinating Uptime Kuma maintenance around
  `appdata.backup` hook execution.
- Added:
  - `appdata_backup_kuma_helper.sh`
  - `appdata_backup_kuma_pre_run.sh`
  - `appdata_backup_kuma_post_run.sh`
  - `.env.example`
  - `README.md`
  - `CHANGELOG.md`
- Added documentation for host-side installation, hook wiring, configuration,
  runtime artifacts, and readiness-based maintenance release behavior.
