# Changelog

## 2026-03-14

### Initial release

- First repository release of `monitor_sab_speed` as a host-side throughput
  monitoring and recovery automation helper.
- Added:
  - `monitor_sab_speed.sh`
  - `README.md`
  - `CHANGELOG.md`
  - `.env.example`
- Added host-side monitoring, maintenance automation, and recovery support for:
  - shared Komodo stacks
  - split Komodo stacks
  - Komodo procedures
  - direct Docker container recovery
  - optional Uptime Kuma maintenance handling
- Added documentation for shared `.env` configuration, host scheduling,
  testing, and operational logging with Unraid User Scripts and plain cron.
