#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

import requests

# ======= Configuration =======
RADARR_URL = ""
RADARR_API_KEY = ""

# Plex server base URL and token (required for rating_key-based lookups)
PLEX_URL = ""
PLEX_TOKEN = ""

WATCHED_TAG_LABEL = "watched"  # Label of the Radarr tag to apply
KEEP_TAG_LABEL = "keep"  # Label that prevents deletion

# Delay before deleting the file. 3600 seconds = 1h
DELETION_DELAY_SECONDS = 3600
# =============================


def get_headers():
    return {"X-Api-Key": RADARR_API_KEY}


def fetch_tag_map():
    """
    Fetch all Radarr tags and return a mapping {label_lowercase: id}.
    """
    resp = requests.get(f"{RADARR_URL.rstrip('/')}/api/v3/tag", headers=get_headers())
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
        raise RuntimeError("PLEX_URL and PLEX_TOKEN must be set inside the script.")

    params = {"includeGuids": "1", "X-Plex-Token": PLEX_TOKEN}
    headers = {"Accept": "application/json"}

    url = f"{PLEX_URL.rstrip('/')}/library/metadata/{rating_key}"
    resp = requests.get(url, params=params, headers=headers, timeout=10)
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
    # Expected arguments:
    #   sys.argv[1] = rating_key
    #   sys.argv[2] = optional title override
    #   sys.argv[3] = optional year override
    if len(sys.argv) < 2:
        print(
            "[ERROR] Missing rating key. Usage: radarr_movie.py <RATING_KEY> [<TITLE> <YEAR>]"
        )
        sys.exit(2)

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
        all_movies = requests.get(
            f"{RADARR_URL.rstrip('/')}/api/v3/movie", headers=get_headers()
        ).json()
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

    try:
        requests.put(
            f"{RADARR_URL.rstrip('/')}/api/v3/movie/{movie_id}",
            headers=get_headers(),
            json=updated,
        )
        print(f"[INFO] Tag '{WATCHED_TAG_LABEL}' applied to '{title}'.")
    except Exception as e:
        print(f"[ERROR] Failed to apply tag: {e}")
        sys.exit(1)

    if keep_tag_id is not None and keep_tag_id in updated_tags:
        print(f"[INFO] Keep-tag present. Skipping deletion for '{title}'.")
        sys.exit(0)

    if not movie_file or "id" not in movie_file:
        print(f"[WARN] Radarr shows no movieFile for '{title}'. Unable to delete.")
        sys.exit(0)

    file_id = movie_file["id"]

    deletion_time = datetime.now().astimezone() + timedelta(
        seconds=DELETION_DELAY_SECONDS
    )
    delete_cmd = (
        f"sleep {DELETION_DELAY_SECONDS} && "
        f"curl -sS -X DELETE '{RADARR_URL.rstrip('/')}/api/v3/moviefile/{file_id}' "
        f"-H 'X-Api-Key: {RADARR_API_KEY}'"
    )

    try:
        subprocess.Popen(
            ["/bin/sh", "-c", delete_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(
            f"[INFO] '{title}' will be deleted on "
            f"{deletion_time.strftime('%d.%m.%Y')} at "
            f"{deletion_time.strftime('%H:%M:%S %Z%z')}."
        )
    except Exception as e:
        print(f"[ERROR] Failed to start deletion process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
