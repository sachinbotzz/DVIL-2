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


def _episode_sort_key(item):
    season, episode = item
    try:
        return int(season), int(str(episode).split("-", 1)[0])
    except (TypeError, ValueError):
        return int(season or 0), 999999


def _episode_label(season, episode, multiple_seasons):
    text = str(episode).strip()
    if "-" in text:
        parts = text.split("-", 1)
        try:
            text = f"E{int(parts[0]):02d}-E{int(parts[1]):02d}"
        except (ValueError, TypeError):
            text = f"E{text}"
    else:
        try:
            text = f"E{int(text):02d}"
        except (ValueError, TypeError):
            text = f"E{text}"

    if multiple_seasons:
        try:
            return f"S{int(season):02d}{text}"
        except (ValueError, TypeError):
            return f"S{season}{text}"
    return text


def _episode_query(base_name, season, episode, multiple_seasons):
    # The existing /start getfile route converts '-' to spaces before calling
    # auto_filter. Keep the query simple so it works with the current search.
    title = re.sub(r"\s+", " ", str(base_name).strip()).replace(" ", "-")
    if multiple_seasons:
        try:
            marker = f"S{int(season):02d}E{int(str(episode).split('-', 1)[0]):02d}"
        except (ValueError, TypeError):
            marker = f"S{season}E{episode}"
    else:
        ep_text = str(episode).strip()
        if "-" in ep_text:
            parts = ep_text.split("-", 1)
            try:
                marker = f"E{int(parts[0]):02d}-{int(parts[1]):02d}"
            except (ValueError, TypeError):
                marker = f"E{ep_text}"
        else:
            try:
                marker = f"E{int(ep_text):02d}"
            except (ValueError, TypeError):
                marker = f"E{ep_text}"
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
        # Fall back to the original movie builder when no episode metadata is
        # available. This keeps old documents fully compatible.
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


# Keep a reference to the original implementation before replacing it.
if not hasattr(channel_plugin, "_original_build_movie_update_buttons"):
    channel_plugin._original_build_movie_update_buttons = channel_plugin.build_movie_update_buttons
    channel_plugin.build_movie_update_buttons = build_series_episode_buttons
