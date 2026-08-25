"""Web-series episode buttons for channel update posts.

This plugin patches the existing channel button builder without changing
movie button behavior. Episode buttons use the bot's existing `getfile-...`
start route, so the normal search/verification/download flow is preserved.
"""

import re

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from info import GRP_LNK
from utils import temp
from plugins import channel as channel_plugin


def _episode_parts(episode):
    text = str(episode).strip()
    if "-" in text:
        first, last = text.split("-", 1)
        return first.strip(), last.strip()
    return text, None


def _episode_number(value):
    try:
        return int(str(value).strip().lstrip("E").lstrip("e"))
    except (TypeError, ValueError):
        return None


def _episode_sort_key(item):
    season, episode = item
    first, _ = _episode_parts(episode)
    number = _episode_number(first)
    try:
        season_number = int(season)
    except (TypeError, ValueError):
        season_number = 0
    return season_number, number if number is not None else 999999


def _episode_label(season, episode, multiple_seasons):
    first, last = _episode_parts(episode)
    first_num = _episode_number(first)
    last_num = _episode_number(last) if last is not None else None

    if first_num is not None:
        if last_num is not None:
            text = f"E{first_num:02d}-E{last_num:02d}"
        else:
            text = f"E{first_num:02d}"
    else:
        text = f"E{episode}"

    if multiple_seasons:
        try:
            return f"S{int(season):02d} {text}"
        except (ValueError, TypeError):
            return f"S{season} {text}"
    return text


def _episode_query(base_name, season, episode, multiple_seasons):
    # Preserve combined ranges such as E01-E17 instead of reducing them to E01.
    title = re.sub(r"\s+", " ", str(base_name).strip()).replace(" ", "-")
    first, last = _episode_parts(episode)
    first_num = _episode_number(first)
    last_num = _episode_number(last) if last is not None else None

    if first_num is not None:
        if last_num is not None:
            ep_marker = f"E{first_num:02d}-E{last_num:02d}"
        else:
            ep_marker = f"E{first_num:02d}"
    else:
        ep_marker = f"E{episode}"

    if multiple_seasons:
        try:
            season_marker = f"S{int(season):02d}"
        except (ValueError, TypeError):
            season_marker = f"S{season}"
        marker = f"{season_marker}{ep_marker}"
    else:
        marker = ep_marker

    return f"https://t.me/{temp.U_NAME}?start=getfile-{title}-{marker}"


def build_series_episode_buttons(movie_doc, base_name):
    episodes = set()
    for file_data in movie_doc.get("files", []):
        if file_data.get("tag") != "#SERIES":
            continue
        season = file_data.get("season")
        episode = file_data.get("episode")
        if season is None or episode in (None, ""):
            continue
        episodes.add((season, str(episode).strip()))

    if not episodes:
        return channel_plugin._original_build_movie_update_buttons(movie_doc, base_name)

    seasons = {season for season, _ in episodes}
    multiple_seasons = len(seasons) > 1

    rows = [[
        InlineKeyboardButton(
            "🎞️ Available Episodes",
            url=f"https://t.me/{temp.U_NAME}?start=getfile-{str(base_name).strip().replace(' ', '-')}"
        )
    ]]

    current_row = []
    for season, episode in sorted(episodes, key=_episode_sort_key):
        current_row.append(
            InlineKeyboardButton(
                _episode_label(season, episode, multiple_seasons),
                url=_episode_query(base_name, season, episode, multiple_seasons),
            )
        )
        if len(current_row) == 4:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    group_url = GRP_LNK if GRP_LNK else f"https://t.me/{temp.U_NAME}"
    rows.append([
        InlineKeyboardButton("♻️ Movie Search Group", url=group_url)
    ])
    return InlineKeyboardMarkup(rows)


if not hasattr(channel_plugin, "_original_build_movie_update_buttons"):
    channel_plugin._original_build_movie_update_buttons = channel_plugin.build_movie_update_buttons
    channel_plugin.build_movie_update_buttons = build_series_episode_buttons
