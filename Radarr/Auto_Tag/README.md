# Auto Tag & optionally delete movie

## What it does

With the help of Tautulli, this will automatically tag a movie after it has been
watched, unmonitor it in Radarr and deletes the movie file afterwards. If the movie has a second tag, the script
optionally keeps the movie file, unmonitors and tags it as watched.

The script will not be triggered, if manually setting a movie to watched in Plex.
<br><br>

## Useful in which situation

I am not keeping any watched movies on my drives, but I want to keep a history, if I already
watched a movie or not. For that I added a `watched` label in Radarr.

And also sometimes I want to keep a movie,
after I watched it - or my daughter wants to see a certain movie for the 5th time...
<br><br>

## Requirements

- Completely set up Plex instance
- Completely set up Radarr instance
- Completely set up Tautulli instance, connected to your Plex instance
<br><br>

## Setup

1. Add watched and keep tag to 1 movie in Radarr:
   1. Click on a movie.
   2. Click on edit.
   3. In the tags section add i.e. `watched` and `keep` as two tags and click on `Save`.
      1. If you now go to `Settings` -> `Tags` you should see both tags linked to 1 movie.
   4. Click on the same movie and remove both tags and click on `Save`.
      1. If you now go to `Settings` -> `Tags` you should see both tags but no linked movie.
   5. If you then add a movie via Overseerr or Jellyseerr, you can already assign the
      `keep` tag to the movie. Or do it later in Radarr.
2. Download `radarr_movie.py`.
3. Modify `radarr_movie.py`:
   1. Add URL and Port of your Radarr instance in line 9.
   2. Add Radarr API Key in line 10.
   3. Edit name of tag for watched movies (i.e. `watched`)in line 12.
   4. Edit name of tag for movies to keep (i.e. `keep`)in line 13.
   5. Edit time in seconds after which movies should be deleted in line 16.
4. Copy `radarr_movie.py` into the Tautulli `Config` folder - next to `tautulli.db` and `config.ini`.
5. In Tautulli, go to gear icon -> `Settings` -> `Notifications Agents`
6. Click on `Add new notification agent`.
7. In the list, select `Script`.
8. `Configuration` tab:
   1. For `Script Folder` click on `Browse` and select the `Config` folder of Tautulli you copied `radarr_movie.py` into.
   2. Click for `Script File` into the dropdown menu and select `radarr_movie.py`.
   3. For `Description` chose something of your liking (i.ie `Radarr 'watched' and delete in 1h`).
9. `Triggers`tab:
   1. Select `Watched`.
10. `Conditions` tab:
    1. `Condition {1}` should be set to: `Media Type is not Episode`. You need to enter
       `Episode` manually.
11. `Arguments` tab:
    1. Click on `Watched`and add `{title} {year}` to the `Script Arguments`.
12. Click on `Save` and close the `Script Settings` window.
13. Adjust movie played threshold:
    1. In Plex go to `Settings` -> `Settings` -> `Library` and adjust `Video played threshold` to your liking. I have set it to 95%.
    2. In Tautulli go to `Settings` -> `General` and set `Movie Watched Percentage` to
       the same value.
    3. Basically this setting tells Plex when to say that a movie has been completely
       watched and Tautulli grabs this information and then runs the script.
<br><br>

## How to check if it worked

1. Watch a movie, skip Credits.
2. In Tautulli go to gear icon -> `View Logs`.
3. In the `Tautulli Logs` section you should see something like this, if you have the
   `keep` tag on a movie: ![Tautulli log if a movie should be kept](example_keep.png)
4. If you have not set a `keep` tag, it would be shown as:![Tautulli log if a movie should be kept](example_delete.png)
