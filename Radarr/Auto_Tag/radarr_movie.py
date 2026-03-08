#!/usr/bin/env python3
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import requests
except ImportError:
    requests = None


# ======= Configuration (loaded from environment) =======
RADARR_URL = None
RADARR_API_KEY = None
PLEX_URL = None
PLEX_TOKEN = None
WATCHED_TAG_LABEL = "watched"
KEEP_TAG_LABEL = "keep"
DELETION_DELAY_SECONDS = 7200
REQUEST_TIMEOUT_SECONDS = 10
# ======================================================

QUEUE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "radarr_movie.pending.json"
)
QUEUE_LOCK_FILE = f"{QUEUE_FILE}.lock"


def normalize_url(url):
    if url is None:
        return None
    return str(url).strip().rstrip("/")


def get_required_env(name):
    value = os.getenv(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return str(value).strip()


def get_env_int(name, default):
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return default

    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be an integer, got '{value}'."
        ) from exc


def load_config_from_env(require_plex):
    global RADARR_URL
    global RADARR_API_KEY
    global PLEX_URL
    global PLEX_TOKEN
    global WATCHED_TAG_LABEL
    global KEEP_TAG_LABEL
    global DELETION_DELAY_SECONDS
    global REQUEST_TIMEOUT_SECONDS

    RADARR_URL = normalize_url(get_required_env("RADARR_URL"))
    RADARR_API_KEY = get_required_env("RADARR_API_KEY")
    WATCHED_TAG_LABEL = (
        os.getenv("WATCHED_TAG_LABEL", WATCHED_TAG_LABEL).strip() or "watched"
    )
    KEEP_TAG_LABEL = os.getenv("KEEP_TAG_LABEL", KEEP_TAG_LABEL).strip() or "keep"
    DELETION_DELAY_SECONDS = get_env_int("DELETION_DELAY_SECONDS", 7200)
    REQUEST_TIMEOUT_SECONDS = get_env_int("REQUEST_TIMEOUT_SECONDS", 10)

    if require_plex:
        PLEX_URL = normalize_url(get_required_env("PLEX_URL"))
        PLEX_TOKEN = get_required_env("PLEX_TOKEN")
    else:
        plex_url = os.getenv("PLEX_URL")
        plex_token = os.getenv("PLEX_TOKEN")
        PLEX_URL = normalize_url(plex_url) if plex_url and plex_url.strip() else None
        PLEX_TOKEN = plex_token.strip() if plex_token and plex_token.strip() else None


def get_headers():
    return {"X-Api-Key": RADARR_API_KEY}


class StdlibHttpResponse:
    def __init__(self, status_code, body, headers=None, url=None, reason=None):
        self.status_code = status_code
        self._body = body or b""
        self.headers = headers or {}
        self.url = url
        self.reason = reason or ""

    @property
    def text(self):
        return self._body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if 200 <= self.status_code < 300:
            return

        message = f"HTTP {self.status_code}"
        if self.reason:
            message = f"{message} {self.reason}"
        if self.url:
            message = f"{message} for {self.url}"
        raise RuntimeError(message)


def http_request(method, url, *, headers=None, params=None, json_body=None, timeout=10):
    request_headers = dict(headers or {})

    if requests is not None:
        request_kwargs = {
            "headers": request_headers,
            "timeout": timeout,
        }
        if params:
            request_kwargs["params"] = params
        if json_body is not None:
            request_kwargs["json"] = json_body

        return requests.request(method.upper(), url, **request_kwargs)

    if params:
        query = urllib_parse.urlencode(params, doseq=True)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib_request.Request(
        url=url,
        data=data,
        headers=request_headers,
        method=method.upper(),
    )

    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            return StdlibHttpResponse(
                status_code=response.status,
                body=response.read(),
                headers=dict(response.headers),
                url=response.geturl(),
                reason=response.reason,
            )
    except urllib_error.HTTPError as exc:
        return StdlibHttpResponse(
            status_code=exc.code,
            body=exc.read(),
            headers=dict(exc.headers or {}),
            url=exc.geturl(),
            reason=exc.reason,
        )
    except urllib_error.URLError as exc:
        raise RuntimeError(f"HTTP request failed for {url}: {exc.reason}") from exc


def utc_now():
    return datetime.now(timezone.utc)


def format_local_timestamp(dt: datetime) -> str:
    return dt.astimezone().strftime("%d.%m.%Y %H:%M:%S %Z%z")


def parse_iso_datetime(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@contextmanager
def queue_lock():
    os.makedirs(os.path.dirname(QUEUE_LOCK_FILE), exist_ok=True)

    with open(QUEUE_LOCK_FILE, "w", encoding="utf-8") as lock_handle:
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def load_queue_unlocked():
    if not os.path.exists(QUEUE_FILE):
        return []

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Unable to read deletion queue '{QUEUE_FILE}': {exc}")
        return []

    if isinstance(payload, dict):
        tasks = payload.get("tasks") or []
    elif isinstance(payload, list):
        tasks = payload
    else:
        print(f"[WARN] Unexpected queue format in '{QUEUE_FILE}'. Resetting queue.")
        return []

    return [task for task in tasks if isinstance(task, dict)]


def save_queue_unlocked(tasks):
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)

    payload = {"version": 1, "tasks": tasks}
    tmp_path = f"{QUEUE_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    os.replace(tmp_path, QUEUE_FILE)


def delete_movie_file(file_id, title):
    try:
        response = http_request(
            "DELETE",
            f"{RADARR_URL}/api/v3/moviefile/{file_id}",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"[ERROR] Failed to delete queued file for '{title}': {exc}")
        return False

    if response.status_code == 404:
        print(
            f"[INFO] Queued deletion for '{title}' skipped because file ID {file_id} "
            "is already gone."
        )
        return True

    try:
        response.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Failed to delete queued file for '{title}': {exc}")
        return False

    print(f"[INFO] Deleted queued movie file for '{title}' (file ID {file_id}).")
    return True


def process_pending_deletions():
    now = utc_now()
    processed_count = 0

    with queue_lock():
        tasks = load_queue_unlocked()
        if not tasks:
            return 0

        remaining_tasks = []

        for task in tasks:
            title = task.get("title") or "<unknown>"
            file_id = task.get("file_id")
            delete_after = parse_iso_datetime(task.get("delete_after"))

            if not file_id:
                print(f"[WARN] Dropping invalid queue entry without file_id for '{title}'.")
                continue

            if delete_after is None:
                print(
                    f"[WARN] Dropping invalid queue entry without valid delete_after "
                    f"for '{title}' (file ID {file_id})."
                )
                continue

            if delete_after > now:
                remaining_tasks.append(task)
                continue

            if delete_movie_file(file_id, title):
                processed_count += 1
            else:
                remaining_tasks.append(task)

        save_queue_unlocked(remaining_tasks)

    return processed_count


def queue_movie_deletion(file_id, movie_id, title):
    delete_after = utc_now() + timedelta(seconds=DELETION_DELAY_SECONDS)
    task = {
        "created_at": utc_now().isoformat(),
        "delete_after": delete_after.isoformat(),
        "file_id": int(file_id),
        "movie_id": movie_id,
        "title": title,
    }

    with queue_lock():
        tasks = load_queue_unlocked()
        tasks = [entry for entry in tasks if entry.get("file_id") != int(file_id)]
        tasks.append(task)
        tasks.sort(key=lambda entry: entry.get("delete_after", ""))
        save_queue_unlocked(tasks)

    return delete_after


def fetch_tag_map():
    """
    Fetch all Radarr tags and return a mapping {label_lowercase: id}.
    """
    resp = http_request(
        "GET",
        f"{RADARR_URL}/api/v3/tag",
        headers=get_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    tags = resp.json() or []
    return {
        str(t.get("label", "")).lower(): t.get("id")
        for t in tags
        if "label" in t and "id" in t
    }


def label_to_id(tag_map, label):
    """
    Convert a label to a Radarr tag ID (case-insensitive).
    """
    if not label:
        return None
    return tag_map.get(str(label).strip().lower())


def normalize_title(title: str) -> str:
    """
    Normalize titles for comparison:
    - lowercase
    - strip subtitles (" - xxx", " – xxx", ": xxx")
    - remove non-alphanumeric chars
    """
    if not title:
        return ""
    t = str(title).lower().strip()

    for sep in (" - ", " – ", ": "):
        if sep in t:
            t = t.split(sep, 1)[0]

    t = re.sub(r"[^a-z0-9]+", "", t)
    return t


def find_movie(movies, title, year_int):
    """
    Basic fallback match by normalized title + year.
    """
    target_title_norm = normalize_title(title)

    for m in movies:
        title_candidates = set()

        if m.get("title"):
            title_candidates.add(m["title"])
        if m.get("originalTitle"):
            title_candidates.add(m["originalTitle"])
        if m.get("cleanTitle"):
            title_candidates.add(m["cleanTitle"])

        for alt in m.get("alternateTitles", []):
            t = alt.get("title")
            if t:
                title_candidates.add(t)

        for t in title_candidates:
            if normalize_title(t) == target_title_norm:
                y = m.get("year")
                sy = m.get("secondaryYear")
                if y == year_int or (sy is not None and sy == year_int):
                    return m

    return None


def plex_get_metadata(rating_key: str) -> dict:
    """
    Fetch metadata for a Plex item via /library/metadata/<ratingKey>.
    Uses PLEX_URL + PLEX_TOKEN and the rating_key from Tautulli.
    """
    if not PLEX_URL or not PLEX_TOKEN:
        raise RuntimeError("PLEX_URL and PLEX_TOKEN must be set via environment.")

    params = {"includeGuids": "1", "X-Plex-Token": PLEX_TOKEN}
    headers = {"Accept": "application/json"}

    url = f"{PLEX_URL}/library/metadata/{rating_key}"
    resp = http_request(
        "GET",
        url,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict) and "MediaContainer" in data:
        meta = data["MediaContainer"].get("Metadata") or []
        if not meta:
            raise RuntimeError("Plex returned no Metadata.")
        return meta[0]

    return data


def extract_ids_and_path_from_plex(plex_item: dict):
    """
    Extract tmdbId, imdbId and folder path from Plex metadata.
    - TMDb/IMDb from Guids (tmdb://, imdb://)
    - Folder path from Media/Part/file
    """
    tmdb_id = None
    imdb_id = None
    folder_path = None

    for g in plex_item.get("Guid", []):
        gid = g.get("id") or ""
        if gid.startswith("tmdb://"):
            v = gid.split("://", 1)[1]
            try:
                tmdb_id = int(v)
            except ValueError:
                pass
        elif gid.startswith("imdb://"):
            imdb_id = gid.split("://", 1)[1]

    media = plex_item.get("Media") or []
    if media:
        parts = media[0].get("Part") or []
        if parts:
            file_path = parts[0].get("file")
            if file_path:
                folder_path = os.path.dirname(file_path)

    return tmdb_id, imdb_id, folder_path


def find_movie_advanced(
    movies, title, year_int, tmdb_id=None, imdb_id=None, folder_path=None
):
    """
    Advanced matching:
    1. TMDb ID
    2. IMDb ID
    3. Folder path
    4. Title + Year fallback
    """
    # 1) TMDb ID
    if tmdb_id is not None:
        for m in movies:
            if m.get("tmdbId") == tmdb_id:
                print(f"[INFO] Match found via TMDb ID: {tmdb_id}")
                return m

    # 2) IMDb ID
    if imdb_id:
        imdb_lower = imdb_id.lower()
        for m in movies:
            if str(m.get("imdbId", "")).lower() == imdb_lower:
                print(f"[INFO] Match found via IMDb ID: {imdb_id}")
                return m

    # 3) Folder path (Plex folder vs Radarr path)
    if folder_path:
        folder_norm = folder_path.rstrip("/").rstrip("\\")
        for m in movies:
            radarr_path = str(m.get("path", "")).rstrip("/").rstrip("\\")
            if radarr_path == folder_norm:
                print(f"[INFO] Match found via folder path: {folder_norm}")
                return m

    # 4) Fallback: title/year
    print(f"[INFO] Falling back to title/year matching for '{title}' ({year_int})")
    return find_movie(movies, title, year_int)


def main():
    if len(sys.argv) < 2:
        print(
            "[ERROR] Missing rating key. Usage: radarr_movie.py <RATING_KEY> [<TITLE> <YEAR>]"
        )
        sys.exit(2)

    run_pending_only = sys.argv[1] == "--run-pending"

    try:
        load_config_from_env(require_plex=not run_pending_only)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    if run_pending_only:
        processed_count = process_pending_deletions()
        print(f"[INFO] Pending deletion run completed. Processed {processed_count} item(s).")
        sys.exit(0)

    processed_count = process_pending_deletions()
    if processed_count:
        print(
            f"[INFO] Processed {processed_count} queued deletion(s) before handling "
            "the current watch event."
        )

    # Expected arguments:
    #   sys.argv[1] = rating_key
    #   sys.argv[2] = optional title override
    #   sys.argv[3] = optional year override
    rating_key = sys.argv[1]
    title_override = sys.argv[2] if len(sys.argv) >= 3 else None
    year_override = sys.argv[3] if len(sys.argv) >= 4 else None

    try:
        plex_item = plex_get_metadata(rating_key)
    except Exception as e:
        print(f"[ERROR] Unable to fetch Plex metadata: {e}")
        sys.exit(1)

    plex_title = plex_item.get("title") or plex_item.get("originalTitle") or ""
    plex_year = plex_item.get("year")

    title = title_override or plex_title
    year_val = year_override or plex_year

    if year_val is None:
        print("[ERROR] No year detected from Plex or CLI.")
        sys.exit(1)

    try:
        year_int = int(year_val)
    except ValueError:
        print(f"[ERROR] Invalid year value: {year_val}")
        sys.exit(1)

    tmdb_id, imdb_id, folder_path = extract_ids_and_path_from_plex(plex_item)

    print(
        f"[INFO] Plex metadata: Title='{plex_title}', "
        f"Year={plex_year}, TMDb={tmdb_id}, IMDb={imdb_id}, Folder='{folder_path}'"
    )

    try:
        tag_map = fetch_tag_map()
    except Exception as e:
        print(f"[ERROR] Unable to fetch Radarr tags: {e}")
        sys.exit(1)

    tag_id = label_to_id(tag_map, WATCHED_TAG_LABEL)
    keep_tag_id = label_to_id(tag_map, KEEP_TAG_LABEL)

    if tag_id is None:
        print(f"[ERROR] Tag '{WATCHED_TAG_LABEL}' not found in Radarr.")
        sys.exit(1)

    try:
        response = http_request(
            "GET",
            f"{RADARR_URL}/api/v3/movie",
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        all_movies = response.json()
    except Exception as e:
        print(f"[ERROR] Unable to fetch Radarr movies: {e}")
        sys.exit(1)

    movie = find_movie_advanced(
        all_movies,
        title,
        year_int,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        folder_path=folder_path,
    )

    if not movie:
        print(f"[WARN] No matching Radarr movie found for '{title}' ({year_int}).")
        sys.exit(0)

    movie_id = movie.get("id")
    movie_file = movie.get("movieFile")

    updated = dict(movie)
    updated_tags = list(updated.get("tags", []))

    if tag_id not in updated_tags:
        updated_tags.append(tag_id)
    updated["tags"] = updated_tags

    # Set monitored to false when deleting file, otherwise movie might get upgraded unnecessarily
    if keep_tag_id not in updated_tags:
        updated["monitored"] = False

    try:
        response = http_request(
            "PUT",
            f"{RADARR_URL}/api/v3/movie/{movie_id}",
            headers=get_headers(),
            json_body=updated,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        if keep_tag_id not in updated_tags:
            print(
                f"[INFO] Tag '{WATCHED_TAG_LABEL}' applied to '{title}' & unmonitored."
            )
        else:
            print(f"[INFO] Tag '{WATCHED_TAG_LABEL}' applied to '{title}'.")
    except Exception as e:
        print(f"[ERROR] Failed to apply tag & unmonitor: {e}")
        sys.exit(1)

    if keep_tag_id is not None and keep_tag_id in updated_tags:
        print(
            f"[INFO] Keep-tag present. Skipping deletion for '{title}'  & keeping monitored."
        )
        sys.exit(0)

    if not movie_file or "id" not in movie_file:
        print(f"[WARN] Radarr shows no movieFile for '{title}'. Unable to delete.")
        sys.exit(0)

    file_id = movie_file["id"]

    try:
        deletion_time = queue_movie_deletion(file_id, movie_id, title)
        print(
            f"[INFO] '{title}' queued for deletion at "
            f"{format_local_timestamp(deletion_time)}."
        )
    except Exception as e:
        print(f"[ERROR] Failed to queue deletion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
