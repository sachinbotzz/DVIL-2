
import re
from datetime import datetime
from plugins.Dreamxfutures.Imdbposter import get_movie_details, fetch_image
from database.users_chats_db import db
from pyrogram import Client, filters, enums
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, GRP_LNK
from database.ia_filterdb import save_file, get_search_results
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp


CAPTION_LANGUAGES = ["Bhojpuri", "Hindi", "Bengali", "Tamil", "English", "Bangla", "Telugu", "Malayalam", "Kannada", "Marathi", "Punjabi", "Bengoli", "Gujrati", "Korean", "Gujarati", "Spanish", "French", "German", "Chinese", "Arabic", "Portuguese", "Russian", "Japanese", "Odia", "Assamese", "Urdu"]

OTT_PLATFORMS = {
    "nf": "Netflix",
    "netflix": "Netflix",
    "sonyliv": "SonyLiv",
    "sony": "SonyLiv",
    "sliv": "SonyLiv",
    "amzn": "Amazon Prime Video",
    "prime": "Amazon Prime Video",
    "primevideo": "Amazon Prime Video",
    "hotstar": "Disney+ Hotstar",
    "zee5": "Zee5",
    "jio": "JioHotstar",
    "jhs": "JioHotstar",
    "aha": "Aha",
    "hbo": "HBO Max",
    "paramount": "Paramount+",
    "apple": "Apple TV+",
    "hoichoi": "Hoichoi",
    "sunnxt": "Sun NXT",
    "viki": "Viki",
}

media_filter = filters.document | filters.video | filters.audio

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return
    media.file_type = file_type
    media.caption = message.caption
    success, dreamxbotz = await save_file(media)
    try:  
        if success and dreamxbotz == 1 and await db.movie_update_status(bot.me.id):            
            await send_msg(bot, filename=media.file_name, caption=media.caption)
    except Exception as e:
        print(f"Error In Movie Update - {e}")
        pass

async def send_msg(bot, filename, caption): 
    try:
        clean_name = clean_mentions_links(filename).title()        
        clean_cap = clean_mentions_links(caption).lower()          
        
        year_match = re.search(r"\b(19|20)\d{2}\b", clean_cap) or re.search(r"\b(19|20)\d{2}\b", clean_name)
        extracted_year = year_match.group(0) if year_match else ""

        season_match = re.search(r"(?i)(?:s|season)0*(\d{1,2})", clean_cap) or re.search(r"(?i)(?:s|season)0*(\d{1,2})", clean_name)
        season = season_match.group(1) if season_match else None 

        search_title = clean_name
        if extracted_year and extracted_year in search_title:
            search_title = search_title[: search_title.find(extracted_year) + 4]  
        elif season and season in search_title:
            search_title = search_title[: search_title.find(season) + 1]
            
        clean_title = re.sub(r"[()\[\]{}:;'\-!,.?_\"]", " ", search_title)  
        clean_title = re.sub(r"\s+", " ", clean_title).strip()

        qualities_str = await get_qualities(f"{clean_name} {clean_cap}")
        
        languages = []
        for lang in CAPTION_LANGUAGES:
            if lang.lower() in clean_cap or lang.lower() in clean_name.lower():
                if lang not in languages:
                    languages.append(lang)
        
        ott_platform = extract_ott_platform(f"{clean_name} {clean_cap}")
        
        rating = "N/A"
        duration = "N/A"
        genres = "N/A"
        imdb_url = None
        resized_poster = None
        movie_name_display = clean_title
        year_display = extracted_year

        if await db.add_name(clean_title):
            imdb = await get_movie_details(clean_title)
            if imdb:
                if imdb.get('title'):
                    movie_name_display = imdb.get('title')
                if imdb.get('year'):
                    year_display = str(imdb.get('year'))
                if imdb.get('genres'):
                    genres = imdb.get('genres')
                if imdb.get('rating'):
                    rating = format_rating(imdb.get('rating'))
                if imdb.get('runtime'):
                    duration = format_runtime(imdb.get('runtime'))
                if imdb.get('languages') and not languages:
                    imdb_langs = imdb.get('languages')
                    if isinstance(imdb_langs, str):
                        languages = [l.strip() for l in imdb_langs.split(",") if l.strip()]
                    elif isinstance(imdb_langs, list):
                        languages = imdb_langs
                
                imdb_url = imdb.get('url') or (f"https://www.imdb.com/title/{imdb.get('imdb_id')}" if imdb.get('imdb_id') else None)
                
                poster_url = imdb.get('poster_url')
                if poster_url:
                    resized_poster = await fetch_image(poster_url)
            
            if imdb_url:
                imdb_info_text = f'<a href="{imdb_url}">IMDB INFO</a>'
            else:
                imdb_info_text = "N/A"

            audio_text = ", ".join(languages) if languages else "N/A"

            title_year_str = movie_name_display
            if year_display and str(year_display) not in movie_name_display:
                title_year_str = f"{movie_name_display} {year_display}"

            current_time = datetime.now().strftime("%d %b %Y | %I:%M %p")

            text = (
                f"📥 NEW FILE ADDED ✅\n\n"
                f"🎬 {title_year_str} ║ ⭐ {imdb_info_text}\n\n"
                f"🎭 GENRES : {genres}\n"
                f"🌐 OTT : {ott_platform}\n\n"
                f"🎥 QUALITY : {qualities_str}\n\n"
                f"🔊 AUDIO : {audio_text}\n\n"
                f"🎞️ RATING : {rating}\n"
                f"⏱️ DURATION : {duration}\n\n"
                f"⚡ Powered by - <a href=\"https://t.me/MovieHuntZone\">Movie Hunt Zone</a>\n\n"
                f"🕒 {current_time}"
            )

            search_movie = clean_title.replace(" ", '-')
            
            db_files = []
            try:
                db_files, _, _ = await get_search_results(chat_id=None, query=clean_title, max_results=30)
            except Exception:
                pass
            
            combined_qualities_text = f"{clean_name} {clean_cap} " + " ".join([f"{f.file_name} {getattr(f, 'caption', '') or ''}" for f in db_files])
            combined_qualities_text = combined_qualities_text.lower()

            quality_buttons = []
            if re.search(r'\b480p?\b', combined_qualities_text):
                quality_buttons.append(InlineKeyboardButton('🟢 480p', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}-480p"))
            if re.search(r'\b720p?\b', combined_qualities_text):
                quality_buttons.append(InlineKeyboardButton('🔵 720p', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}-720p"))
            if re.search(r'\b1080p?\b', combined_qualities_text):
                quality_buttons.append(InlineKeyboardButton('🟣 1080p', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}-1080p"))
            if re.search(r'\b(2160p?|4k)\b', combined_qualities_text):
                quality_buttons.append(InlineKeyboardButton('🟠 4K', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}-4k"))

            if not quality_buttons:
                if qualities_str != "N/A":
                    quality_buttons.append(InlineKeyboardButton(f'🟢 {qualities_str}', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}"))
                else:
                    quality_buttons.append(InlineKeyboardButton('🟢 720p', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}"))

            btn = [
                [InlineKeyboardButton('🎬 Available Quality', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{search_movie}")],
                quality_buttons,
                [InlineKeyboardButton('♻️ Movie Search Group', url=GRP_LNK or f"https://telegram.me/{temp.U_NAME}")]
            ]

            if resized_poster:
                await bot.send_photo(
                    chat_id=MOVIE_UPDATE_CHANNEL,
                    photo=resized_poster,
                    caption=text,
                    has_spoiler=True,
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await bot.send_message(
                    chat_id=MOVIE_UPDATE_CHANNEL,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=enums.ParseMode.HTML
                )
    except Exception as e:
        print(f"Error in send_msg: {e}")
        pass

def clean_mentions_links(text: str) -> str:
    return re.sub(r'@[^ \n\r\t.,:;!?()\[\]{}<>\\/"\'=_%]+|\bwww\.[^\s\]\)]+|\([\@^]+\)|\[[\@^]+\]', '', text).strip()

def format_runtime(runtime_raw):
    if not runtime_raw or str(runtime_raw).strip() in ("", "N/A", "None"):
        return "N/A"
    first_rt = str(runtime_raw).split(",")[0].strip()
    digits = re.findall(r"\d+", first_rt)
    if digits:
        try:
            total_mins = int(digits[0])
            hours = total_mins // 60
            mins = total_mins % 60
            if hours > 0 and mins > 0:
                return f"{hours}h {mins}m"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{mins}m"
        except Exception:
            pass
    return str(runtime_raw)

def format_rating(rating_raw):
    if not rating_raw or str(rating_raw).strip() in ("", "N/A", "None"):
        return "N/A"
    match = re.search(r"(\d+(?:\.\d+)?)", str(rating_raw))
    if match:
        return match.group(1)
    return str(rating_raw)

async def get_qualities(text):
    quality_map = [
        ("480p", ["480p", "480"]),
        ("720p", ["720p", "720"]),
        ("1080p", ["1080p", "1080"]),
        ("2160p", ["2160p", "2160", "4k"]),
        ("HDRip", ["hdrip"]),
        ("HDCAM", ["hdcam", "camrip"]),
        ("HQ", ["hq"]),
        ("WEB-DL", ["web-dl", "webrip"]),
    ]
    found = []
    text_lower = text.lower()
    for std_name, patterns in quality_map:
        for p in patterns:
            if re.search(r'\b' + re.escape(p) + r'\b', text_lower):
                if std_name not in found:
                    found.append(std_name)
                break
    if found:
        return ", ".join(found)
    return "N/A"

def extract_ott_platform(text):
    text_lower = text.lower()
    found = set()
    for key, platform in OTT_PLATFORMS.items():
        if key in text_lower:
            found.add(platform)
    if found:
        return ", ".join(sorted(found))
    return "N/A"

def media_tag(filename, caption):
    text = f"{filename} {caption}".lower()
    pattern = r'(?:s|season)[\s\-_]*0*\d{1,2}'
    if re.search(pattern, text, re.IGNORECASE):
        return '#TV_SERIES'
    return '#MOVIE'

