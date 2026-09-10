"""Series-aware movie update formatting.

Keeps normal movie notifications unchanged while making TV-series updates
use the series title/season format and render the existing episode summary.
The existing episode-button plugin remains responsible for episode buttons.
"""

import re

from Script import script
from plugins import channel as channel_plugin
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx


# Add the existing episode summary to the notification template.
script.MOVIE_UPDATE_NOTIFY_TXT = """
<blockquote><b>📥 NEW FILE ADDED ✅</b></blockquote>

<b>🎬 {filename} {year} ║ ⭐ <a href=\"{imdb_url}\">IMDB INFO</a></b>

<b>🎭 GENRES : {genres}</b>
<b>🌐 OTT : {ott}</b>

<b>🎥 QUALITY : {quality}</b>

<b>🔊 AUDIO : {language}</b>

<b>🎞️ RATING : {rating}</b>
<b>⏱️ DURATION : {runtime}</b>

{episodes}

<blockquote><b>⚡ Powered by - <a href=\"https://t.me/+k1ZDXVZXlKEwZTg1\">सचिन रिक्वेस्ट मूवी ग्रुप</a></b></blockquote>

<b>🕒 {date}</b>
"""


_original_generate_movie_message = channel_plugin.generate_movie_message
_original_send_movie_update = channel_plugin.send_movie_update
_original_update_movie_message = channel_plugin.update_movie_message

_series_cache = {}


def _is_series_kind(details):
    kind = str(
        (details or {}).get("media_type")
        or (details or {}).get("kind")
        or ""
    ).lower().strip()
    return kind in {"tv", "series", "tv series", "tvseries"}


def _season_numbers(raw):
    numbers = []
    if isinstance(raw, (list, tuple)):
        values = raw
    elif raw:
        values = [raw]
    else:
        values = []

    for item in values:
        value = item.get("season_number") if isinstance(item, dict) else item
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            numbers.append(number)
    return sorted(set(numbers))


async def _prepare_series_metadata(base_name):
    """Use TMDB TV metadata as a fallback for titles without SxxExx tokens."""
    movie_doc = await channel_plugin.db.movie_updates.find_one({"_id": base_name})
    if not movie_doc:
        return

    already_series = movie_doc.get("tag") == "#SERIES" or any(
        f.get("tag") == "#SERIES" for f in movie_doc.get("files", [])
    )

    details = None
    if already_series:
        cached = _series_cache.get(base_name)
        if cached is not None:
            details = cached
        elif not movie_doc.get("seasons"):
            try:
                details = await get_movie_detailsx(base_name)
                _series_cache[base_name] = details or {}
            except Exception:
                details = None
    else:
        cached = _series_cache.get(base_name)
        if cached is None:
            try:
                details = await get_movie_detailsx(base_name)
                _series_cache[base_name] = details or {}
            except Exception:
                details = None
        else:
            details = cached

        if not _is_series_kind(details):
            return

        already_series = True

    if not already_series:
        return

    update_fields = {"tag": "#SERIES"}
    seasons = (details or {}).get("seasons")
    if seasons:
        update_fields["seasons"] = seasons
    total_episodes = (details or {}).get("total_episodes")
    if total_episodes:
        update_fields["total_episodes"] = total_episodes

    await channel_plugin.db.movie_updates.update_one(
        {"_id": base_name},
        {"$set": update_fields},
    )

    # Convert existing files to series metadata only when TMDB confirms TV.
    if details and _is_series_kind(details):
        await channel_plugin.db.movie_updates.update_one(
            {"_id": base_name},
            {"$set": {"files.$[].tag": "#SERIES"}},
        )


def _format_series_episode_block(text):
    """Convert the internal episode summary to the requested display format."""
    pattern = re.compile(
        r"📺 ᴇᴘɪsᴏᴅᴇs : <b>\n(?P<body>.*?)</b>",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text

    lines = []
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        season_match = re.match(r"S(\d+)\s*:\s*(.+)$", line, re.IGNORECASE)
        if season_match:
            season = int(season_match.group(1))
            episodes = season_match.group(2).strip()
            lines.append(f"S{season:02d}: E ➜ {episodes}")
        elif line:
            lines.append(line)

    if not lines:
        return text

    replacement = "🎞️ ᴇᴘɪsᴏᴅᴇs : <b>" + "\n".join(lines) + "</b>"
    return text[:match.start()] + replacement + text[match.end():]


def generate_series_aware_message(movie_doc, base_name):
    is_series = movie_doc.get("tag") == "#SERIES" or any(
        f.get("tag") == "#SERIES" for f in movie_doc.get("files", [])
    )

    if not is_series:
        return _original_generate_movie_message(movie_doc, base_name)

    # Build the season label from actual uploaded episode metadata first.
    seasons = set()
    for file_data in movie_doc.get("files", []):
        season = file_data.get("season")
        if season:
            try:
                seasons.add(int(season))
            except (TypeError, ValueError):
                pass

    # If files don't contain SxxExx yet, use TMDB's season list saved by the
    # async metadata preparation step. Prefer Season 1 for a fresh TV title.
    if not seasons:
        tmdb_seasons = _season_numbers(movie_doc.get("seasons"))
        if tmdb_seasons:
            seasons.add(tmdb_seasons[0])

    title = re.sub(r"\s+(?:19|20)\d{2}\s*$", "", str(base_name).strip())
    if seasons:
        title += " " + " ".join(f"S{season:02d}" for season in sorted(seasons))

    # Hide the movie year for TV series while retaining the movie format for
    # normal titles. A shallow copy prevents any DB mutation here.
    series_doc = dict(movie_doc)
    series_doc["year"] = ""

    text = _original_generate_movie_message(series_doc, title)
    text = _format_series_episode_block(text)
    text = re.sub(r"\s+║", " ║", text)
    return text


async def _series_aware_send_movie_update(bot, base_name):
    await _prepare_series_metadata(base_name)
    return await _original_send_movie_update(bot, base_name)


async def _series_aware_update_movie_message(bot, base_name):
    await _prepare_series_metadata(base_name)
    return await _original_update_movie_message(bot, base_name)


channel_plugin.generate_movie_message = generate_series_aware_message
channel_plugin.send_movie_update = _series_aware_send_movie_update
channel_plugin.update_movie_message = _series_aware_update_movie_message
