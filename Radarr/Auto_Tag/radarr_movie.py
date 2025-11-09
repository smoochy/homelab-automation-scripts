#!/usr/bin/env python3
import subprocess
import sys
from datetime import datetime, timedelta

import requests

# ======= Configuration =======
RADARR_URL = ""
RADARR_API_KEY = ""

WATCHED_TAG_LABEL = "watched"   # Tag label in Radarr to be applied
KEEP_TAG_LABEL = "keep"         # Tag label in Radarr that prevents deletion

# Delay before deleting the file. 3600 seconds = 1h
DELETION_DELAY_SECONDS = 3600
# =============================


def get_headers():
    return {"X-Api-Key": RADARR_API_KEY}


def fetch_tag_map():
    """
    Fetches all tags from Radarr and returns a mapping:
    { label_lowercase: id }
    """
    resp = requests.get(f"{RADARR_URL}/api/v3/tag", headers=get_headers())
    resp.raise_for_status()
    tags = resp.json() or []
    return {str(t.get("label", "")).strip().lower(): t.get("id") for t in tags if "label" in t and "id" in t}


def label_to_id(tag_map, label):
    """
    Returns the tag ID for a given label (case-insensitive), or None if not found.
    """
    if not label:
        return None
    return tag_map.get(str(label).strip().lower())


def find_movie(movies, title, year_int):
    """
    Finds a movie by title (case-insensitive) and year (year or secondaryYear).
    """
    title_lower = title.lower()
    for m in movies:
        if str(m.get("title", "")).lower() != title_lower:
            continue
        y = m.get("year")
        sy = m.get("secondaryYear")
        if y == year_int or (sy is not None and sy == year_int):
            return m
    return None


def main():
    if len(sys.argv) < 3:
        print("Usage: radarr_movie.py <TITLE> <YEAR>")
        sys.exit(2)

    title = sys.argv[1]
    year = sys.argv[2]

    try:
        year_int = int(year)
    except ValueError:
        print(f"[ERROR] Invalid year: {year}")
        sys.exit(2)

    # Fetch tags and resolve labels to IDs
    try:
        tag_map = fetch_tag_map()
    except requests.RequestException as e:
        print(f"[ERROR] Could not fetch tags from Radarr: {e}")
        sys.exit(1)

    tag_id = label_to_id(tag_map, WATCHED_TAG_LABEL)
    keep_tag_id = label_to_id(tag_map, KEEP_TAG_LABEL)

    if tag_id is None:
        print(f"[ERROR] Tag label '{WATCHED_TAG_LABEL}' not found in Radarr. Please create it or update the script.")
        sys.exit(1)

    if keep_tag_id is None:
        print(f"[WARN] Keep-tag label '{KEEP_TAG_LABEL}' not found in Radarr. Keep logic will be skipped.")

    # Fetch all movies
    try:
        all_movies = requests.get(f"{RADARR_URL}/api/v3/movie", headers=get_headers()).json()
    except requests.RequestException as e:
        print(f"[ERROR] Could not load movies: {e}")
        sys.exit(1)

    movie = find_movie(all_movies, title, year_int)

    if not movie:
        print(f"[ERROR] Movie '{title} ({year})' not found in Radarr.")
        sys.exit(0)

    # Info output
    print(f"[INFO] Movie Info: Title: '{title}' & Year: {year}.")
    if "secondaryYear" in movie:
        print(f"[INFO] Radarr Info: Title: '{movie.get('title')}' & Year: {movie.get('year')} & SecondaryYear: {movie.get('secondaryYear')}.")
    else:
        print(f"[INFO] Radarr Info: Title: '{movie.get('title')}' & Year: {movie.get('year')}.")
    
    # Get internal Radarr movie ID
    movie_id = movie.get("id")
    # Get internal Radarr file ID of that movie
    movie_file = movie.get("movieFile")

    if not movie_file or "id" not in movie_file:
        print(f"[WARN] No movie file associated with '{title}' in Radarr – nothing to delete.")
        # Still tag the movie if needed
        updated = dict(movie)
        updated_tags = list(updated.get("tags", []))
        if tag_id not in updated_tags:
            updated_tags.append(tag_id)
            updated["tags"] = updated_tags
            try:
                requests.put(f"{RADARR_URL}/api/v3/movie/{movie_id}", headers=get_headers(), json=updated)
                print(f"[INFO] '{title}' tagged with '{WATCHED_TAG_LABEL}'.")
            except requests.RequestException as e:
                print(f"[ERROR] Failed to set tag: {e}")
        sys.exit(0)

    file_id = movie_file["id"]

    # Add tag (if not already set)
    updated = dict(movie)
    updated_tags = list(updated.get("tags", []))
    if tag_id not in updated_tags:
        updated_tags.append(tag_id)
    updated["tags"] = updated_tags

    try:
        requests.put(f"{RADARR_URL}/api/v3/movie/{movie_id}", headers=get_headers(), json=updated)
        print(f"[INFO] '{title}' tagged with '{WATCHED_TAG_LABEL}'.")
    except requests.RequestException as e:
        print(f"[ERROR] Failed to set tag: {e}")
        sys.exit(1)

    # Keep logic: skip deletion if keep-tag is present
    if keep_tag_id is not None and keep_tag_id in updated["tags"]:
        print(f"[INFO] '{title}' will not be deleted because '{KEEP_TAG_LABEL}' is set.")
        sys.exit(0)

    # Schedule file deletion
    deletion_time = datetime.now().astimezone() + timedelta(seconds=DELETION_DELAY_SECONDS)
    delete_cmd = (
        f"sleep {DELETION_DELAY_SECONDS} && "
        f"curl -sS -X DELETE '{RADARR_URL}/api/v3/moviefile/{file_id}' "
        f"-H 'X-Api-Key: {RADARR_API_KEY}'"
    )

    try:
        subprocess.Popen(
            ["/bin/sh", "-c", delete_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"[INFO] '{title}' will be deleted on {deletion_time.strftime('%d-%m-%Y')} at {deletion_time.strftime('%H:%M:%S %Z%z')}.")
    except Exception as e:
        print(f"[ERROR] Failed to start deletion process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()