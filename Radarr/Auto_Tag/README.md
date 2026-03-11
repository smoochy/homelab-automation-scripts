# Radarr Auto Tag for Tautulli

This script marks watched Plex movies in Radarr and schedules movie file
deletion through a persistent queue.

## What the script does

When Tautulli sends a Plex `rating_key`, the script:

1. Loads Plex metadata for the watched movie.
2. Matches the movie in Radarr.
3. Adds the `watched` tag.
4. Sets `monitored=false` if the movie does not have the `keep` tag.
5. Queues the movie file for delayed deletion.
6. Processes any due queue entries before handling the current event.

## Matching order

The Radarr movie lookup uses this order:

1. TMDb ID from Plex metadata
2. IMDb ID from Plex metadata
3. Folder path
4. Title and year fallback

## Features

- Uses the Plex `rating_key` from Tautulli.
- Persists delayed deletions in `radarr_movie.pending.json`.
- Supports queue-only processing with `--run-pending`.
- Loads configuration from container environment variables.
- Also loads a local `.env` file next to the script for manual runs.
- Supports overriding the `.env` path with `AUTO_TAG_ENV_FILE`.
- Falls back to the Python standard library when `requests` is not installed.
- Works well in Linux-based Tautulli containers and on Unraid hosts.

## Files

- `radarr_movie.py`
  Main script.
- `.env.example`
  Example environment file.
- `radarr_movie.pending.json`
  Persistent deletion queue.
- `radarr_movie.pending.json.lock`
  Advisory queue lock file used on platforms with `fcntl` support.

## Configuration

The script reads these environment variables:

- `RADARR_URL`
- `RADARR_API_KEY`
- `PLEX_URL`
- `PLEX_TOKEN`
- `WATCHED_TAG_LABEL`
- `KEEP_TAG_LABEL`
- `DELETION_DELAY_SECONDS`
- `REQUEST_TIMEOUT_SECONDS`
- `AUTO_TAG_ENV_FILE` (optional)

Typical values:

```env
RADARR_URL=http://radar:7878
RADARR_API_KEY=your_radarr_api_key
PLEX_URL=http://plex:32400
PLEX_TOKEN=your_plex_token
WATCHED_TAG_LABEL=watched
KEEP_TAG_LABEL=keep
DELETION_DELAY_SECONDS=7200
REQUEST_TIMEOUT_SECONDS=10
```

Notes:

- `RADARR_URL` and `RADARR_API_KEY` are always required.
- `PLEX_URL` and `PLEX_TOKEN` are required for normal watch-event runs.
- `PLEX_URL` and `PLEX_TOKEN` are not required for `--run-pending`.
- If present, a local `.env` file is loaded automatically from the script directory.
- `AUTO_TAG_ENV_FILE` can point to a different `.env` file for manual runs.
- Tautulli does not load `.env` files by itself. For container use, inject the
  variables through your Compose stack or container configuration.

## Setup

### Prerequisites

- Tautulli is installed and connected to Plex.
- Radarr is running and API access is enabled.
- You know your Plex token.
- `radarr_movie.py` is available inside the Tautulli container.
- The required environment variables are available to the script.

Plex token reference:
[Finding an authentication token / X-Plex-Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

### 1. Create the Radarr tags

Create these tags in Radarr before using the script:

- `watched`
- `keep`

`watched` is required. `keep` is used to prevent unmonitoring and deletion for
selected movies.

### 2. Place the script

Recommended Tautulli path:

```bash
/config/scripts/auto_tag/
```

Copy these files there:

- `radarr_movie.py`
- `.env.example` as your template for environment values

### 3. Provide configuration

Recommended container-based approach:

1. Copy the values from `.env.example`.
2. Add them to your Tautulli Compose stack or referenced env file.
3. Recreate or redeploy the Tautulli container.

Optional manual-run approach:

1. Keep a `.env` file next to `radarr_movie.py`.
2. Or set `AUTO_TAG_ENV_FILE` to another env file path.

### 4. Configure the Tautulli notification agent

1. Open Tautulli.
2. Go to `Settings > Notification Agents`.
3. Add a new agent of type `Script`.
4. In `Configuration`, set the script folder to:

```bash
/config/scripts/auto_tag/
```

5. Select `radarr_movie.py`.
6. In `Triggers`, enable `Watched`.
7. In `Conditions`, add:

- `Media Type is not Episode`

8. In `Arguments`, use:

```bash
{rating_key}
```

9. Save the notification agent.

The script still accepts optional title and year override arguments:

```bash
python3 radarr_movie.py <rating_key> [title] [year]
```

For the normal Tautulli workflow, only `{rating_key}` is needed.

### 5. Align the watched threshold

Make Plex and Tautulli use the same watched threshold so both systems agree on
when the script should run.

Example:

- Plex: `Settings > Library > Video played threshold`
- Tautulli: `Settings > General > Movie Watched Percentage`

### 6. Optional queue processing schedule

If you want queued deletions processed without waiting for the next watch event,
schedule:

```bash
docker exec tautulli python3 /config/scripts/auto_tag/radarr_movie.py --run-pending
```

## Usage

### Handle a watch event

```bash
python3 /config/scripts/auto_tag/radarr_movie.py <rating_key>
```

Optional override arguments:

```bash
python3 /config/scripts/auto_tag/radarr_movie.py <rating_key> "<title>" <year>
```

### Process pending deletions only

```bash
python3 /config/scripts/auto_tag/radarr_movie.py --run-pending
```

From the Unraid host, the recommended command is:

```bash
docker exec tautulli python3 /config/scripts/auto_tag/radarr_movie.py --run-pending
```

## Queue behavior

- Queue data is stored in `radarr_movie.pending.json`.
- Entries survive Tautulli container restarts.
- New queue entries replace older entries for the same `file_id`.
- Queue timestamps are stored in UTC.
- Log timestamps are shown in local time.
- If Radarr has already removed the file, the queue entry is treated as done on
  the next run.

Current queue payload format:

```json
{
  "version": 1,
  "tasks": [
    {
      "created_at": "2026-03-08T12:00:00+00:00",
      "delete_after": "2026-03-08T14:00:00+00:00",
      "file_id": 123,
      "movie_id": 456,
      "title": "Example Movie"
    }
  ]
}
```

## Cron example

Daily at `04:00`:

```cron
0 4 * * * docker exec tautulli python3 /config/scripts/auto_tag/radarr_movie.py --run-pending
```

If you want deletions to happen closer to `DELETION_DELAY_SECONDS`, use a more
frequent schedule such as every 5 or 10 minutes.

## Verification

After watching a movie past the configured watched threshold:

- Tautulli should show the script run in its logs.
- Movies with the `keep` tag should be tagged as watched and not queued for deletion.
- Movies without the `keep` tag should be tagged, unmonitored, and queued.

Example log output when a movie is kept:

![Tautulli log when a movie is kept](assets/example_keep.png)

Example log output when a movie is queued for deletion:

![Tautulli log when a movie is queued for deletion](assets/example_delete.png)

## Notes

- The script exits with an error if the configured watched tag does not exist in Radarr.
- If the keep tag does not exist, the script cannot use it to protect movies from deletion.
- If no `movieFile` is present in Radarr, the script skips deletion.
