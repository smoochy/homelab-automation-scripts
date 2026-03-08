# Changelog

## 2026-03-08

### Previous behavior

- The script applied the `watched` tag and started a delayed
  `sleep ... && DELETE` process inside the running Tautulli
  container.
- If the Tautulli container was restarted before the delay expired,
  the pending deletion was lost.
- Configuration values were hardcoded directly in the script.

### Current behavior

- The script applies the `watched` tag and stores delayed deletions
  in `radarr_movie.pending.json`.
- Queue entries survive Tautulli container restarts and are
  processed on later runs.
- A dedicated `--run-pending` mode allows queue processing without
  a playback event.
- Configuration is provided through environment variables injected
  into the Tautulli container.
- The script can also run on the Unraid host without the
  `requests` package by using the Python standard library
  fallback.
