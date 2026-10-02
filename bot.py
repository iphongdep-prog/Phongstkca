import asyncio
import json
import logging
import os
import random
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool
import pytz

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ChatMemberHandler,
    filters,
)

# ============================================================
# CẤU HÌNH
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://iphongdep-prog.github.io/Phongstkca/").strip()

ADMIN_IDS = [5633649201]

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

REQUIRED_CHECK_CHANNELS = [
    "@sanhugame",
    "@sancode22",
    "@xombao247",
    "@thongbaohit88",
    "@sancodehit88",
    "@vtc345",
    "@vtc567",
    "@hocviencbm",
    "@chungnaomoidu",
    "@khuyenmaionline",
]

OPTIONAL_DISPLAY_CHANNELS = []

SUPPORT_GROUP = "https://t.me/conmuamenmenl"

MIN_WITHDRAW = 15000
MAX_WITHDRAW = 300000
REFERRAL_REWARD = 1000

# ============================================================
# EMOJI
# ============================================================
E = {
    "CROWN": '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
    "REFRESH": '<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>',
    "TOP": '<tg-emoji emoji-id="5415655814079723871">🔝</tg-emoji>',
    "EYES": '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji>',
    "LIGHTNING": '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>',
    "COMET": '<tg-emoji emoji-id="5224607267797606837">☄️</tg-emoji>',
    "STOP": '<tg-emoji emoji-id="5260293700088511294">⛔</tg-emoji>',
    "BAN": '<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji>',
    "WARN1": '<tg-emoji emoji-id="5274099962655816924">❗</tg-emoji>',
    "WARN2": '<tg-emoji emoji-id="5440660757194744323">‼️</tg-emoji>',
    "WARN3": '<tg-emoji emoji-id="5314504236132747481">⁉️</tg-emoji>',
    "QUESTION": '<tg-emoji emoji-id="5436113877181941026">❓</tg-emoji>',
    "ALERT1": '<tg-emoji emoji-id="5420323339723881652">⚠</tg-emoji>',
    "ALERT2": '<tg-emoji emoji-id="5420323339723881652">⚠</tg-emoji>',
    "CHART": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "UP": '<tg-emoji emoji-id="5449683594425410231">🔼</tg-emoji>',
    "DOWN": '<tg-emoji emoji-id="5447183459602669338">🔽</tg-emoji>',
    "MEDAL1": '<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>',
    "MEDAL2": '<tg-emoji emoji-id="5447203607294265305">🥈</tg-emoji>',
    "MEDAL3": '<tg-emoji emoji-id="5453902265922376865">🥉</tg-emoji>',
    "CHECK_ANIMATED": '<tg-emoji emoji-id="5206607081334906820">✔</tg-emoji>',
    "FREE": '<tg-emoji emoji-id="5406756500108501710">🆓</tg-emoji>',
    "PENCIL": '<tg-emoji emoji-id="5395444784611480792">✏️</tg-emoji>',
    "CALENDAR": '<tg-emoji emoji-id="5413879192267805083">🗓</tg-emoji>',
    "DROP": '<tg-emoji emoji-id="5393512611968995988">💧</tg-emoji>',
    "SNOW": '<tg-emoji emoji-id="5449449325434266744">❄️</tg-emoji>',
    "SUN": '<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji>',
    "ARROW_DOWN": '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji>',
    "MAIL": '<tg-emoji emoji-id="5253742260054409879">✉</tg-emoji>',
    "LOCK": '<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji>',
    "GAME": '<tg-emoji emoji-id="5361741454685256344">🎮</tg-emoji>',
    "GEAR": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>',
    "SURPRISE": '<tg-emoji emoji-id="5303479226882603449">😮</tg-emoji>',
    "CLIP": '<tg-emoji emoji-id="5305265301917549162">📎</tg-emoji>',
    "SPEAKER": '<tg-emoji emoji-id="5388632425314140043">🔈</tg-emoji>',
    "LAUGH1": '<tg-emoji emoji-id="5406913184810409829">😂</tg-emoji>',
    "SMILE1": '<tg-emoji emoji-id="5386587088873331829">😄</tg-emoji>',
    "LAUGH2": '<tg-emoji emoji-id="5375135722514685501">😆</tg-emoji>',
    "SMIRK": '<tg-emoji emoji-id="5375170473095077321">😏</tg-emoji>',
    "SWEAT": '<tg-emoji emoji-id="5384209107215456745">😅</tg-emoji>',
    "KISS": '<tg-emoji emoji-id="5368475679937534380">😘</tg-emoji>',
    "CRAZY": '<tg-emoji emoji-id="5393197898240369117">🤪</tg-emoji>',
    "THUMB": '<tg-emoji emoji-id="5219872564569972166">👍</tg-emoji>',
    "YUM": '<tg-emoji emoji-id="5348205856661969976">😋</tg-emoji>',
    "COOL": '<tg-emoji emoji-id="5368562433981947135">😎</tg-emoji>',
    "CRY1": '<tg-emoji emoji-id="5416039998904345140">😭</tg-emoji>',
    "CRY2": '<tg-emoji emoji-id="5400000868739193368">😭</tg-emoji>',
    "NEUTRAL": '<tg-emoji emoji-id="5368376088235875736">😐</tg-emoji>',
    "LOVE": '<tg-emoji emoji-id="5323470315370585285">😍</tg-emoji>',
    "CRY3": '<tg-emoji emoji-id="5379656338802482888">😭</tg-emoji>',
    "ROLL": '<tg-emoji emoji-id="5429300173559832620">🙄</tg-emoji>',
    "SIX": '<tg-emoji emoji-id="5305642863902604489">6️⃣</tg-emoji>',
    "PHONE": '<tg-emoji emoji-id="5431445208531215160">📱</tg-emoji>',
    "PRAY": '<tg-emoji emoji-id="5228878926306101271">🙏</tg-emoji>',
    "MONEY": '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>',
    "FLASH": '<tg-emoji emoji-id="5411590687663608498">⚡</tg-emoji>',
}

# ============================================================
# ANTI SPAM
# ============================================================

SPAM_WINDOW_SECONDS = 3
SPAM_MAX_MESSAGES = 6
TEMP_BAN_MINUTES = 2

user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}

# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE POSTGRESQL
# ============================================================

db_pool = None

def get_pool():
    global db_pool
    if db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("Chưa cấu hình DATABASE_URL trên VPS/Railway.")
        db_pool = ConnectionPool(
            DATABASE_URL,
            min_size=2,
            max_size=20,
            kwargs={"row_factory": tuple_row},
            open=True
        )
    return db_pool

def _db_query_sync(query, params=(), fetchone=False, fetchall=False, commit=False):
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

async def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance BIGINT NOT NULL DEFAULT 0,
                    bank_info TEXT,
                    referrer_id BIGINT,
                    phone_number TEXT,
                    ref_rewarded INTEGER NOT NULL DEFAULT 0,
                    is_captcha_passed INTEGER NOT NULL DEFAULT 0,
                    is_text_verified INTEGER NOT NULL DEFAULT 1,
                    is_phone_verified INTEGER NOT NULL DEFAULT 0,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT,
                    ip_address TEXT,
                    skip_ip_check INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_rewarded INTEGER NOT NULL DEFAULT 0;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_captcha_passed INTEGER NOT NULL DEFAULT 0;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_text_verified INTEGER NOT NULL DEFAULT 1;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_phone_verified INTEGER NOT NULL DEFAULT 0;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_withdraw_banned INTEGER NOT NULL DEFAULT 0;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bank_info TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_id BIGINT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS joined_at TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_address TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS skip_ip_check INTEGER NOT NULL DEFAULT 0;")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT
                )
                """
            )
            cursor.execute("CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY);")
            cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);")
            
            defaults = [
                ('maintenance', '0'),
                ('check_channels', '1'),
                ('check_captcha', '1'),
                ('check_phone', '1'),
                ('check_ip', '1'),
                ('enable_withdraw', '1')
            ]
            for key, val in defaults:
                cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING;", (key, val))

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, id DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_withdraw ON transactions(type, status, id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)")
        conn.commit()
        logger.info("Database PostgreSQL đã sẵn sàng.")

async def init_db():
    await asyncio.to_thread(_init_db_sync)

def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

# ============================================================
# CẤU HÌNH SETTINGS
# ============================================================

async def get_setting(key: str, default="1") -> bool:
    res = await db_query("SELECT value FROM settings WHERE key=%s", (key,), fetchone=True)
    return (res[0] == "1") if res else (default == "1")

async def set_setting(key: str, value: str):
    await db_query("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value), commit=True)

async def is_maintenance():
    return await get_setting("maintenance", "0")

# ============================================================
# UTILS & VIETQR
# ============================================================

def generate_vietqr_url(bank_info: str, amount: int, memo: str = "lixi trung thu") -> str:
    if not bank_info:
        return ""
    parts = bank_info.strip().split()
    if len(parts) < 2:
        return ""
    
    stk = parts[0]
    bank_code = parts[1].upper()
    
    bank_mapping = {
        "VCB": "vietcombank", "VIETCOMBANK": "vietcombank", "TCB": "techcombank",
        "TECHCOMBANK": "techcombank", "MB": "mbbank", "MBBANK": "mbbank",
        "STB": "sacombank", "SACOMBANK": "sacombank", "ACB": "acb",
        "VPB": "vpbank", "VPBANK": "vpbank", "TPB": "tpbank",
        "TPBANK": "tpbank", "BIDV": "bidv", "CTG": "vietinbank",
        "VIETINBANK": "vietinbank", "AGRIBANK": "agribank", "VIB": "vib",
        "SHB": "shb", "MSB": "msb", "LPB": "lienvietpostbank",
        "LPBANK": "lienvietpostbank", "OCB": "ocb", "HDB": "hdbank", "HDBANK": "hdbank",
    }
    
    code = bank_mapping.get(bank_code, bank_code.lower())
    encoded_memo = urllib.parse.quote(memo)
    return f"https://img.vietqr.io/image/{code}-{stk}-compact2.png?amount={amount}&addInfo={encoded_memo}"

# ============================================================
# KEYBOARD
# ============================================================

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("👤 Tài Khoản"), KeyboardButton("🎁 Mời Bạn Bè")],
        [KeyboardButton("💳 Rút Tiền"), KeyboardButton("🔝 Top")],
        [KeyboardButton("💬 Nhóm Hỗ Trợ"), KeyboardButton("📜 Lịch Sử Giao Dịch")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================
# CAPTCHA & CHECK IP & PHONE VERIFICATION
# ============================================================

def generate_captcha():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    correct_ans = a + b
    options = {correct_ans}
    while len(options) < 4:
        wrong = correct_ans + random.randint(-5, 5)
        if wrong > 0 and wrong != correct_ans:
            options.add(wrong)
    opts_list = list(options)
    random.shuffle(opts_list)
    return a, b, correct_ans, opts_list

async def send_phone_verification_challenge(update_or_message, context: ContextTypes.DEFAULT_TYPE):
    user_id = update_or_message.effective_user.id if hasattr(update_or_message, "effective_user") else update_or_message.from_user.id
    caption = (
        f"{E['LOCK']} <b>XÁC MINH SỐ ĐIỆN THOẠI</b>\n\n"
        f"{E['ALERT1']} <b>Yêu cầu tài khoản hợp lệ:</b>\n"
        f"{E['CHECK_ANIMATED']} Số điện thoại Việt Nam (+84)\n"
        f"{E['CHECK_ANIMATED']} Tên hiển thị không quá 20 ký tự\n"
        f"{E['CHECK_ANIMATED']} Có username (@)\n"
        f"{E['CHECK_ANIMATED']} Có ảnh đại diện\n"
        f"{E['ARROW_DOWN']} Nhấn nút bên dưới để chia sẻ số điện thoại:"
    )
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Chia sẻ số điện thoại", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    if hasattr(update_or_message, "reply_text"):
        await update_or_message.reply_text(caption, parse_mode="HTML", reply_markup=kb)
    else:
        await context.bot.send_message(chat_id=user_id, text=caption, parse_mode="HTML", reply_markup=kb)

async def send_ip_verification_challenge(update_or_message, context: ContextTypes.DEFAULT_TYPE):
    user_id = update_or_message.effective_user.id if hasattr(update_or_message, "effective_user") else update_or_message.from_user.id
    caption = (
        f"{E['ALERT1']} <b>BƯỚC XÁC MINH MẠNG (CHECK IP MINIAPP)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Vui lòng nhấn vào nút <b>🌐 XÁC MINH IP QUA MINIAPP</b> ở bàn phím bên dưới để xác minh địa chỉ IP của bạn:\n"
        f"<i>(Lưu ý: Mỗi tài khoản chỉ được dùng 1 IP duy nhất. Tài khoản trùng IP sẽ bị khóa vĩnh viễn!)</i>"
    )
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("🌐 XÁC MINH IP QUA MINIAPP", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    if hasattr(update_or_message, "reply_text"):
        await update_or_message.reply_text(caption, parse_mode="HTML", reply_markup=kb)
    else:
        await context.bot.send_message(chat_id=user_id, text=caption, parse_mode="HTML", reply_markup=kb)

# ============================================================
# KIỂM TRA LUỒNG XÁC MINH CHUNG (SĐT -> IP -> CAPTCHA)
# ============================================================

async def process_user_verification_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    db_user = await get_fresh_user(user_id)
    if not db_user:
        return False

    if await get_setting("check_channels"):
        missing_channels = await get_missing_channels(context.bot, user_id)
        if missing_channels:
            buttons = build_channel_buttons(missing_channels)
            missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
            msg = (
                f"{E['ALERT1']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['STOP']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n{missing_text}\n\n"
                f"{E['CLIP']} Vui lòng tham gia đầy đủ rồi bấm nút <b>XÁC NHẬN ĐÃ THAM GIA</b> bên dưới!"
            )
            if update.effective_message:
                await update.effective_message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
            return False

    if await get_setting("check_phone") and not db_user[9]:
        await send_phone_verification_challenge(update.effective_message or update, context)
        return False

    if await get_setting("check_ip") and not db_user[13] and db_user[14] == 0:
        await send_ip_verification_challenge(update.effective_message or update, context)
        return False

    if await get_setting("check_captcha") and not db_user[7]:
        await send_captcha_challenge(update, context, message_text=f"{E['ALERT1']} <b>Vui lòng giải CAPTCHA để tiếp tục:</b>")
        return False

    return True

async def trigger_referral_reward_if_eligible(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    db_user = await get_fresh_user(user_id)
    if not db_user:
        return

    referrer_id, ref_rewarded = db_user[4], db_user[6]

    check_cap = not await get_setting("check_captcha") or db_user[7] == 1
    check_phn = not await get_setting("check_phone") or db_user[9] == 1
    check_ip_cond = not await get_setting("check_ip") or db_user[13] is not None or db_user[14] == 1

    if referrer_id and ref_rewarded == 0 and check_cap and check_phn and check_ip_cond:
        try:
            def reward_referrer(cursor):
                cursor.execute("SELECT ref_rewarded FROM users WHERE user_id=%s", (user_id,))
                res = cursor.fetchone()
                if res and res[0] == 1:
                    return False

                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                    (referrer_id, "Thưởng Mời Bạn", REFERRAL_REWARD, "Thành công", get_now_str(), f"Mời {user_id}"),
                )
                cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (REFERRAL_REWARD, referrer_id))
                cursor.execute("UPDATE users SET ref_rewarded = 1 WHERE user_id=%s", (user_id,))
                return True

            rewarded = await db_transaction(reward_referrer)
            if rewarded:
                uname = f"@{db_user[1]}" if db_user[1] else str(user_id)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"{E['LOVE']} <b>THƯỞNG MỜI BẠN BÈ!</b>\n{E['UP']} Bạn nhận được <b>+{REFERRAL_REWARD:,}đ</b>\n{E['EYES']} Từ người dùng xác thực thành công: <b>{uname}</b>",
                        parse_mode="HTML"
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo referrer: %s", exc)
        except Exception as exc:
            logger.exception("Lỗi transaction thưởng giới thiệu: %s", exc)

# ============================================================
# KIỂM TRA THAM GIA KÊNH & CHAT MEMBER UPDATED
# ============================================================

async def chat_member_updated_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def get_missing_channels(bot, user_id):
    sem = asyncio.Semaphore(4)

    async def check_one(channel):
        async with sem:
            try:
                member = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=channel, user_id=user_id),
                    timeout=3.5
                )
                if member.status in ("left", "kicked"):
                    return channel
            except Exception as exc:
                logger.warning(f"Lỗi check kênh {channel} cho user {user_id}: {exc}")
                return channel
            return None

    tasks = [check_one(ch) for ch in REQUIRED_CHECK_CHANNELS]
    results = await asyncio.gather(*tasks)
    return [ch for ch in results if ch is not None]

def build_channel_buttons(missing_channels):
    buttons = []
    for ch in missing_channels:
        channel_url = f"https://t.me/{ch.replace('@', '')}"
        buttons.append([InlineKeyboardButton(f"👉 Tham gia: {ch}", url=channel_url)])
    for ch in OPTIONAL_DISPLAY_CHANNELS:
        channel_url = f"https://t.me/{ch.replace('@', '')}"
        buttons.append([InlineKeyboardButton(f"🌟 Tham gia: {ch} (Tham khảo)", url=channel_url)])
    buttons.append([InlineKeyboardButton("❇️ XÁC NHẬN ĐÃ THAM GIA ❇️", callback_data="verify_join")])
    return buttons

# ============================================================
# ANTI SPAM
# ============================================================

async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not chat or chat.type != "private" or not user or not message:
        return False

    if user.id in ADMIN_IDS:
        return False

    now = datetime.now()
    
    ban_until = temp_bans.get(user.id)
    if ban_until:
        if now < ban_until:
            remaining_seconds = max(0, int((ban_until - now).total_seconds()))
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            await message.reply_text(
                f"{E['BAN']} <b>BẠN ĐÃ BỊ TẠM CẤM TÍNH NĂNG!</b>\n"
                f"{E['CALENDAR']} Vui lòng chờ: <b>{minutes} phút {seconds} giây</b>\n"
                f"{E['ALERT1']} Lý do: <b>Spam thao tác quá nhanh.</b>",
                parse_mode="HTML"
            )
            return True
        else:
            temp_bans.pop(user.id, None)

    cutoff = now - timedelta(seconds=SPAM_WINDOW_SECONDS)
    user_msg_tracker[user.id] = [t for t in user_msg_tracker[user.id] if t >= cutoff]
    user_msg_tracker[user.id].append(now)

    if len(user_msg_tracker[user.id]) >= SPAM_MAX_MESSAGES:
        temp_bans[user.id] = now + timedelta(minutes=TEMP_BAN_MINUTES)
        user_msg_tracker[user.id].clear()
        await message.reply_text(
            f"{E['BAN']} <b>CẢNH BÁO ANTI-SPAM</b>\n"
            f"{E['STOP']} Bạn đã bị cấm <b>{TEMP_BAN_MINUTES} phút</b>!\n"
            f"{E['ALERT1']} Lý do: Thao tác quá <b>{SPAM_MAX_MESSAGES} lần</b> trong <b>{SPAM_WINDOW_SECONDS}s</b>.",
            parse_mode="HTML"
        )
        return True

    return False

# ============================================================
# USER QUERY
# ============================================================

USER_SELECT_QUERY = (
    "SELECT user_id, username, balance, bank_info, referrer_id, "
    "phone_number, ref_rewarded, is_captcha_passed, is_text_verified, "
    "is_phone_verified, is_banned, is_withdraw_banned, joined_at, ip_address, skip_ip_check "
    "FROM users WHERE user_id=%s"
)

async def ensure_user_exists(update: Update):
    user = update.effective_user
    if not user:
        return None
    row = await db_query(USER_SELECT_QUERY, (user.id,), fetchone=True)
    if row:
        current_username = user.username or ""
        if row[1] != current_username:
            await db_query("UPDATE users SET username=%s WHERE user_id=%s", (current_username, user.id), commit=True)
    else:
        await db_query(
            "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", get_now_str()),
            commit=True,
        )
        row = await db_query(USER_SELECT_QUERY, (user.id,), fetchone=True)
    return row

async def get_fresh_user(user_id: int):
    return await db_query(USER_SELECT_QUERY, (user_id,), fetchone=True)

async def require_private_user(update: Update):
    if not update.effective_chat or update.effective_chat.type != "private":
        return False
    user = update.effective_user
    if not user:
        return False
    row = await ensure_user_exists(update)
    if row and row[10] == 1:
        await update.effective_message.reply_text(f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!</b>", parse_mode="HTML")
        return False
    return True

# ============================================================
# START
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context):
        return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if chat.type != "private":
        await db_query("INSERT INTO groups(chat_id) VALUES(%s) ON CONFLICT (chat_id) DO NOTHING", (chat.id,), commit=True)
        return
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(f"{E['STOP']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n{E['GEAR']} Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!", parse_mode="HTML")
        return

    db_user = await ensure_user_exists(update)

    if db_user and db_user[10] == 1:
        await update.message.reply_text(f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!</b>", parse_mode="HTML")
        return

    if context.args and not db_user[4]:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                await db_query("UPDATE users SET referrer_id=%s WHERE user_id=%s AND (referrer_id IS NULL OR referrer_id=0)", (ref_id, user.id), commit=True)
        except (ValueError, TypeError):
            pass

    if not await process_user_verification_flow(update, context, user.id):
        return

    await trigger_referral_reward_if_eligible(user.id, context)

    await update.message.reply_text(
        f"{E['LIGHTNING']} <b>CHÀO MỪNG BẠN TRỞ LẠI HỆ THỐNG!</b>\n{E['MEDAL1']} Hãy chọn một tính năng trong menu bên dưới:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

# ============================================================
# XỬ LÝ CHIA SẺ SỐ ĐIỆN THOẠI (CONTACT HANDLER)
# ============================================================

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.contact or not user:
        return

    contact = message.contact
    if contact.user_id != user.id:
        await message.reply_text("❌ Số điện thoại vừa chia sẻ không khớp với tài khoản Telegram của bạn.")
        return

    phone_number = contact.phone_number.strip()
    
    normalized_phone = phone_number
    if phone_number.startswith("84"):
        normalized_phone = "+" + phone_number
    elif phone_number.startswith("0"):
        normalized_phone = "+84" + phone_number[1:]

    if not normalized_phone.startswith("+84"):
        await message.reply_text("❌ Yêu cầu tài khoản hợp lệ phải sử dụng **Số điện thoại Việt Nam (+84)**.", parse_mode="HTML")
        await send_phone_verification_challenge(message, context)
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if len(full_name) > 20:
        await message.reply_text(
            f"❌ **Tên hiển thị quá dài!**\n"
            f"Tên hiện tại của bạn có {len(full_name)} ký tự. Yêu cầu **không quá 20 ký tự** để xác minh.",
            parse_mode="HTML"
        )
        return

    if not user.username:
        await message.reply_text(
            "❌ **Chưa có Username!**\n"
            "Vui lòng thiết lập Username (@) trong cài đặt tài khoản Telegram của bạn trước khi xác minh.",
            parse_mode="HTML"
        )
        return

    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count == 0:
            await message.reply_text(
                "❌ **Chưa có ảnh đại diện!**\n"
                "Vui lòng tải lên ít nhất một ảnh đại diện (Avatar) cho tài khoản Telegram của bạn.",
                parse_mode="HTML"
            )
            return
    except Exception as exc:
        logger.warning("Không kiểm tra được avatar user %s: %s", user.id, exc)

    await db_query(
        "UPDATE users SET phone_number=%s, is_phone_verified=1 WHERE user_id=%s",
        (normalized_phone, user.id),
        commit=True
    )

    await message.reply_text(
        f"{E['CHECK_ANIMATED']} Xác minh số điện thoại thành công!\n\n"
        f"{E['REFRESH']} Đang kiểm tra điều kiện tiếp theo...",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    if await process_user_verification_flow(update, context, user.id):
        await trigger_referral_reward_if_eligible(user.id, context)
        await message.reply_text(
            f"{E['CROWN']} <b>Chào mừng bạn đã hoàn tất toàn bộ xác minh!</b>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )

# ============================================================
# GỬI CAPTCHA & CALLBACK
# ============================================================

async def send_captcha_challenge(update_or_query, context: ContextTypes.DEFAULT_TYPE, message_text=""):
    a, b, correct_ans, options = generate_captcha()
    context.user_data["captcha_ans"] = correct_ans
    buttons = []
    row = []
    for opt in options:
        row.append(InlineKeyboardButton(f"🔹 {opt}", callback_data=f"captcha_{opt}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    caption = (f"{message_text}\n\n" if message_text else "")
    caption += (
        f"{E['GAME']} <b>XÁC MINH CAPTCHA BẢO MẬT</b>\n"
        f"{E['PENCIL']} Vui lòng giải phép tính bên dưới để hoàn tất xác minh:\n"
        f"{E['QUESTION']} <b>{a} + {b} = ?</b>"
    )
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    elif hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
    else:
        user_id = update_or_query.from_user.id if hasattr(update_or_query, "from_user") else update_or_query.effective_user.id
        await context.bot.send_message(chat_id=user_id, text=caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    data = query.data or ""
    try:
        selected_ans = int(data.split("_")[1])
    except (IndexError, ValueError):
        return
    correct_ans = context.user_data.get("captcha_ans")
    if selected_ans != correct_ans:
        try:
            await query.answer("❌ Phép tính sai! Vui lòng thử lại.", show_alert=True)
        except Exception:
            pass
        await send_captcha_challenge(query, context, message_text=f"{E['WARN1']} <b>Bạn đã chọn sai kết quả! Vui lòng tính lại.</b>")
        return

    context.user_data.pop("captcha_ans", None)

    await ensure_user_exists(update)
    await db_query("UPDATE users SET is_captcha_passed=1 WHERE user_id=%s", (user.id,), commit=True)

    try:
        await query.answer("✅ Xác minh CAPTCHA thành công!")
        await query.edit_message_text(
            f"{E['CHECK_ANIMATED']} Xác minh captcha thành công!\n\n"
            f"{E['REFRESH']} Đang kiểm tra điều kiện tiếp theo...",
            parse_mode="HTML"
        )
    except Exception:
        pass

    if await process_user_verification_flow(update, context, user.id):
        await trigger_referral_reward_if_eligible(user.id, context)
        await context.bot.send_message(chat_id=user.id, text=f"{E['CROWN']} <b>Xác minh hoàn tất!</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============================================================
# VERIFY JOIN
# ============================================================

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                f"{E['ALERT1']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['STOP']} Bạn vẫn chưa tham gia đủ <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n{missing_text}\n\n"
                f"{E['CLIP']} Vui lòng tham gia đầy đủ rồi bấm nút bên dưới để xác nhận lại!",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    if await process_user_verification_flow(update, context, user.id):
        await trigger_referral_reward_if_eligible(user.id, context)
        await context.bot.send_message(chat_id=user.id, text=f"{E['LAUGH1']} <b>Bạn đã hoàn tất tất cả xác minh!</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============================================================
# MINIAPP CHECK IP
# ============================================================

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.web_app_data:
        return

    raw_data = message.web_app_data.data
    try:
        data_json = json.loads(raw_data)
        ip_addr = data_json.get("ip") or data_json.get("ip_address")
    except Exception:
        ip_addr = raw_data.strip()

    if not ip_addr:
        await message.reply_text("❌ Không thể lấy địa chỉ IP từ Miniapp, vui lòng thử lại.")
        return

    db_user = await get_fresh_user(user.id)
    if not db_user:
        return

    if db_user[14] == 1:
        await db_query("UPDATE users SET ip_address=%s WHERE user_id=%s", (ip_addr, user.id), commit=True)
        await message.reply_text(
            f"{E['CHECK_ANIMATED']} Xác minh IP thành công!\n\n"
            f"{E['REFRESH']} Đang kiểm tra điều kiện tiếp theo...",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        return

    existing_ip_user = await db_query("SELECT user_id FROM users WHERE ip_address=%s AND user_id != %s AND skip_ip_check = 0", (ip_addr, user.id), fetchone=True)

    if existing_ip_user:
        await db_query("UPDATE users SET is_banned=1 WHERE user_id=%s", (user.id,), commit=True)
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            f"{E['BAN']} <b>HỆ THỐNG PHÁT HIỆN TRÙNG IP!</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{E['STOP']} Địa chỉ IP <code>{ip_addr}</code> đã trùng với tài khoản <code>{existing_ip_user[0]}</code>.\n"
            f"{E['ALERT1']} <b>Tài khoản của bạn đã bị khóa vĩnh viễn khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return

    await db_query("UPDATE users SET ip_address=%s WHERE user_id=%s", (ip_addr, user.id), commit=True)
    
    await message.reply_text(
        f"{E['CHECK_ANIMATED']} Xác minh IP thành công!\n\n"
        f"{E['REFRESH']} Đang kiểm tra điều kiện tiếp theo...",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    if await process_user_verification_flow(update, context, user.id):
        await trigger_referral_reward_if_eligible(user.id, context)
        await message.reply_text(f"{E['CROWN']} <b>Chào mừng bạn đã gia nhập hệ thống Bot VIP!</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============================================================
# LỆNH ADMIN
# ============================================================

async def admin_menu_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    c_chan = "🟢 BẬT" if await get_setting("check_channels") else "🔴 TẮT"
    c_phn = "🟢 BẬT" if await get_setting("check_phone") else "🔴 TẮT"
    c_ip = "🟢 BẬT" if await get_setting("check_ip") else "🔴 TẮT"
    c_cap = "🟢 BẬT" if await get_setting("check_captcha") else "🔴 TẮT"
    c_wd = "🟢 BẬT" if await get_setting("enable_withdraw") else "🔴 TẮT"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"1. Check Kênh: {c_chan}", callback_data="toggle_check_channels")],
        [InlineKeyboardButton(f"2. Check SĐT (+84): {c_phn}", callback_data="toggle_check_phone")],
        [InlineKeyboardButton(f"3. Check IP Miniapp: {c_ip}", callback_data="toggle_check_ip")],
        [InlineKeyboardButton(f"4. Check Captcha: {c_cap}", callback_data="toggle_check_captcha")],
        [InlineKeyboardButton(f"💳 Tính năng Rút Tiền: {c_wd}", callback_data="toggle_enable_withdraw")],
        [InlineKeyboardButton("🔄 Xác Minh Toàn Bộ", callback_data="force_verify_all")],
    ])

    msg_text = (
        f"{E['GEAR']} <b>MENU QUẢN LÝ BẬT/TẮT HỆ THỐNG</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bấm vào các nút bên dưới để Bật hoặc Tắt nhanh tính năng tương ứng hoặc yêu cầu xác minh lại:"
    )

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(msg_text, reply_markup=kb, parse_mode="HTML")
        except Exception: pass
    else:
        await update.effective_message.reply_text(msg_text, reply_markup=kb, parse_mode="HTML")

async def admin_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or query.from_user.id not in ADMIN_IDS: return
    try: await query.answer()
    except Exception: pass

    data = query.data or ""
    key = data.replace("toggle_", "")
    curr = await get_setting(key)
    await set_setting(key, "0" if curr else "1")
    await admin_menu_panel(update, context)

async def force_verify_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or query.from_user.id not in ADMIN_IDS:
        return
    try:
        await query.answer()
    except Exception:
        pass

    await db_query(
        "UPDATE users SET is_captcha_passed=0, is_phone_verified=0, ip_address=NULL, skip_ip_check=0, ref_rewarded=0",
        commit=True
    )

    await set_setting("check_channels", "1")
    await set_setting("check_phone", "1")
    await set_setting("check_ip", "1")
    await set_setting("check_captcha", "1")

    try:
        await query.edit_message_text(
            f"{E['CHECK_ANIMATED']} <b>ĐÃ XÁC MINH LẠI TOÀN BỘ HỆ THỐNG THÀNH CÔNG!</b>\n"
            f"• Toàn bộ các bước (Kênh, SĐT +84, IP, Captcha) đã được kích hoạt bắt buộc.\n"
            f"• Thành viên khi bấm /start sẽ phải thực hiện lại từ đầu.",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def bo_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    args = context.args or []
    if not args:
        await update.effective_message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/bo USER_ID</code>", parse_mode="HTML")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.effective_message.reply_text("❌ USER_ID không hợp lệ.")
        return

    await db_query("UPDATE users SET skip_ip_check=1 WHERE user_id=%s", (target_id,), commit=True)
    await update.effective_message.reply_text(f"{E['THUMB']} <b>Đã thiết lập BỎ QUA KIỂM TRA IP cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

async def mo_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    args = context.args or []
    if not args:
        await update.effective_message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/moip USER_ID</code>", parse_mode="HTML")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.effective_message.reply_text("❌ USER_ID không hợp lệ.")
        return

    await db_query("UPDATE users SET is_banned=0, skip_ip_check=1, ip_address=NULL WHERE user_id=%s", (target_id,), commit=True)
    await update.effective_message.reply_text(f"{E['THUMB']} <b>Đã MỞ KHÓA trùng IP & BỎ QUA KIỂM TRA IP cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

# ============================================================
# MENU HANDLER
# ============================================================

def clean_menu_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text_cleaned = re.sub(r'[^\w\s]', '', raw_text).strip()
    return text_cleaned

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or update.effective_chat.type != "private":
        return

    await ensure_user_exists(update)
    db_user = await get_fresh_user(user.id)
    user_withdraw_state.pop(user.id, None)

    if await is_maintenance() and user.id not in ADMIN_IDS:
        await message.reply_text(f"{E['STOP']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n{E['GEAR']} Vui lòng quay lại sau!", parse_mode="HTML")
        return

    if not db_user or db_user[10] == 1:
        await message.reply_text(f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm khỏi hệ thống!</b>", parse_mode="HTML")
        return

    if user.id not in ADMIN_IDS:
        if not await process_user_verification_flow(update, context, user.id):
            return

    raw_text = (message.text or "").strip()
    clean_text = clean_menu_text(raw_text).lower()

    if clean_text in ["tai khoan", "tài khoản"] or "tài khoản" in raw_text.lower():
        balance = db_user[2]
        res = await db_query("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (user.id,), fetchone=True)
        invited_count = res[0]
        res_withdraw = await db_query("SELECT COALESCE(SUM(amount), 0)::BIGINT FROM transactions WHERE user_id=%s AND type='Rút Tiền' AND status='Thành công'", (user.id,), fetchone=True)
        total_withdraw = res_withdraw[0] if res_withdraw else 0
        msg = (
            f"{E['CROWN']} <b>THÔNG TIN TÀI KHOẢN VIP</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{E['EYES']} <b>ID:</b> <code>{user.id}</code>\n"
            f"{E['CHECK_ANIMATED']} <b>Xác minh:</b> <code>Đã hoàn tất</code>\n"
            f"{E['UP']} <b>Số dư:</b> <code>{balance:,}đ</code>\n"
            f"{E['COOL']} <b>Đã mời:</b> <code>{invited_count}</code> người\n"
            f"{E['DOWN']} <b>Đã rút:</b> <code>{total_withdraw:,}đ</code>"
        )
        await message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif clean_text in ["moi ban be", "mời bạn bè"] or "mời bạn" in raw_text.lower():
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as exc:
            logger.exception("Không lấy được username bot: %s", exc)
            await message.reply_text("❌ Không lấy được thông tin bot. Vui lòng thử lại.")
            return
        if not bot_username:
            await message.reply_text("❌ Bot chưa có username, không thể tạo link mời.")
            return
        ref_link = f"https://t.me/{bot_username}?start={user.id}"
        msg = (
            f"{E['FREE']} <b>CHƯƠNG TRÌNH MỜI BẠN BÈ</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"{E['CLIP']} <b>Link giới thiệu của bạn:</b>\n<code>{ref_link}</code>\n\n"
            f"{E['CALENDAR']} <b>Thể lệ nhận thưởng:</b>\n"
            f"• {E['LIGHTNING']} Nhận ngay: <b>+{REFERRAL_REWARD:,}đ</b> / lượt mời thành công.\n"
            f"• {E['CLIP']} Bạn bè phải tham gia đủ kênh, giải CAPTCHA & xác minh.\n"
            f"• {E['DOWN']} Min rút: <b>{MIN_WITHDRAW:,}đ</b>\n"
            f"• {E['TOP']} Max rút: <b>{MAX_WITHDRAW:,}đ</b>"
        )
        await message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif clean_text == "top" or "top" in raw_text.lower():
        top_users = await db_query(
            """
            SELECT u.user_id, u.username, COUNT(r.user_id) AS ref_count
            FROM users u
            LEFT JOIN users r ON r.referrer_id = u.user_id
            WHERE u.is_banned = 0
            GROUP BY u.user_id, u.username
            HAVING COUNT(r.user_id) > 0
            ORDER BY ref_count DESC
            LIMIT 10
            """,
            fetchall=True
        )
        if not top_users:
            await message.reply_text(f"{E['CHART']} <b>Hiện chưa có ai trong bảng xếp hạng Top tuyển ref!</b>", parse_mode="HTML", reply_markup=get_main_keyboard())
            return

        msg = f"{E['TOP']} <b>TOP 10 THÀNH VIÊN TUYỂN REF NHIỀU NHẤT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for idx, (top_id, top_username, ref_count) in enumerate(top_users, start=1):
            name_str = f"@{top_username}" if top_username else f"User {top_id}"
            icon = E['MEDAL1'] if idx == 1 else (E['MEDAL2'] if idx == 2 else (E['MEDAL3'] if idx == 3 else E['CHECK_ANIMATED']))
            msg += f"{icon} <b>Top {idx}:</b> {name_str} — <code>{ref_count:,}</code> bạn bè\n"

        await message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif clean_text in ["nhom ho tro", "nhóm hỗ trợ"] or "hỗ trợ" in raw_text.lower():
        await message.reply_text(f"{E['SPEAKER']} <b>NHÓM HỖ TRỢ CHÍNH THỨC:</b>\n👉 {SUPPORT_GROUP}\n\n{E['SIX']} <b>ADMIN:</b> @echcutodz", parse_mode="HTML", reply_markup=get_main_keyboard())

    elif clean_text in ["lich su", "lich su giao dịch", "lịch sử giao dịch", "lịch sử"] or "lịch sử" in raw_text.lower():
        txs = await db_query("SELECT type, amount, status, created_at FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 10", (user.id,), fetchall=True)
        if not txs:
            await message.reply_text(f"{E['CALENDAR']} <b>Bạn chưa có giao dịch nào.</b>", parse_mode="HTML", reply_markup=get_main_keyboard())
            return
        msg = f"{E['CHART']} <b>LỊCH SỬ GIAO DỊCH GẦN ĐÂY</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for tx_type, amount, status, created_at in txs:
            icon = E['THUMB'] if status == "Thành công" else (E['BAN'] if status == "Từ chối" else E['CALENDAR'])
            msg += f"{icon} <b>{tx_type}</b>: <code>{amount:,}đ</code>\n{E['CHART']} Trạng thái: <b>{status}</b>\n{E['CALENDAR']} Thời gian: <code>{created_at}</code>\n----------------------------------\n"
        await message.reply_text(msg, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif clean_text in ["rut tien", "rút tiền"] or "rút tiền" in raw_text.lower():
        if not await get_setting("enable_withdraw", "1"):
            await message.reply_text(f"{E['STOP']} <b>TÍNH NĂNG RÚT TIỀN ĐANG TẠM ĐÓNG!</b>\n{E['GEAR']} Hệ thống đang tạm ngưng chức năng rút tiền. Vui lòng quay lại sau!", parse_mode="HTML", reply_markup=get_main_keyboard())
            return

        if db_user[11] == 1:
            await message.reply_text(f"{E['BAN']} <b>Tài khoản của bạn đã bị CẤM RÚT TIỀN!</b>", parse_mode="HTML", reply_markup=get_main_keyboard())
            return
        bank_info = db_user[3]
        if not bank_info:
            await message.reply_text(f"{E['ALERT1']} <b>BẠN CHƯA LIÊN KẾT NGÂN HÀNG</b>\n{E['ARROW_DOWN']} Vui lòng gửi lệnh liên kết theo cú pháp:\n<code>/lk STK Tên_Ngân_Hàng Tên_Chủ_Thẻ</code>\n\n{E['LIGHTNING']} <b>Ví dụ:</b> <code>/lk 1068030300 VCB NGUYEN CA NGU</code>", parse_mode="HTML", reply_markup=get_main_keyboard())
        else:
            user_withdraw_state[user.id] = "WAITING_AMOUNT"
            cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ HỦY THAO TÁC", callback_data="cancel_withdraw")]])
            await message.reply_text(
                f"{E['TOP']} <b>LỆNH RÚT TIỀN VIP</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['LOCK']} <b>Tài khoản nhận:</b> <code>{bank_info}</code>\n"
                f"{E['UP']} <b>Số dư hiện tại:</b> <code>{db_user[2]:,}đ</code>\n"
                f"{E['CLIP']} <b>Hạn mức:</b> <code>{MIN_WITHDRAW:,}đ</code> - <code>{MAX_WITHDRAW:,}đ</code>\n\n"
                f"{E['ARROW_DOWN']} <b>Vui lòng nhập số tiền bạn muốn rút:</b>\n"
                f"<i>(Nhập 'hủy' hoặc bấm nút bên dưới để thoát)</i>",
                reply_markup=cancel_btn,
                parse_mode="HTML",
            )

# ============================================================
# HỦY RÚT
# ============================================================

async def cancel_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    user_withdraw_state.pop(user.id, None)
    try:
        await query.answer("Đã hủy thao tác!")
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(chat_id=user.id, text=f"{E['BAN']} <b>Đã hủy thao tác rút tiền.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ============================================================
# LIÊN KẾT NGÂN HÀNG
# ============================================================

async def link_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context) or not await require_private_user(update):
        return
    user = update.effective_user
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(f"{E['STOP']} Hệ thống đang bảo trì, vui lòng quay lại sau!")
        return
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(f"{E['BAN']} <b>Sai cú pháp liên kết!</b>\n{E['ARROW_DOWN']} Ví dụ đúng:\n<code>/lk 1068030300 VCB NGUYEN CA NGU</code>", parse_mode="HTML")
        return
    bank_str = " ".join(context.args).strip()
    if len(bank_str) > 300:
        await update.message.reply_text("❌ Thông tin ngân hàng quá dài.")
        return
    await db_query("UPDATE users SET bank_info=%s WHERE user_id=%s", (bank_str, user.id), commit=True)
    await update.message.reply_text(f"{E['THUMB']} <b>LIÊN KẾT THÀNH CÔNG!</b>\n{E['LOCK']} Thông tin lưu trữ: <code>{bank_str}</code>", parse_mode="HTML", reply_markup=get_main_keyboard())

# ============================================================
# RESET BANK - ADMIN
# ============================================================

async def reset_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    message = update.effective_message
    if not message:
        return
    args = context.args or []
    if len(args) < 1:
        await message.reply_text(f"{E['BAN']} <b>Sai cú pháp!</b>\nCú pháp: <code>/resetbank USER_ID</code>", parse_mode="HTML")
        return
    try:
        target_id = int(args[0])
    except (ValueError, TypeError):
        await message.reply_text("❌ USER_ID không hợp lệ.")
        return
    user_exists = await db_query("SELECT user_id, bank_info FROM users WHERE user_id=%s", (target_id,), fetchone=True)
    if not user_exists:
        await message.reply_text(f"❌ Không tìm thấy user <code>{target_id}</code>.", parse_mode="HTML")
        return
    old_bank = user_exists[1]
    await db_query("UPDATE users SET bank_info=NULL WHERE user_id=%s", (target_id,), commit=True)
    user_withdraw_state.pop(target_id, None)
    await message.reply_text(f"{E['THUMB']} <b>ĐÃ RESET NGÂN HÀNG CỦA USER:</b> <code>{target_id}</code>\n{E['LOCK']} Bank cũ: <code>{old_bank or 'Chưa liên kết'}</code>", parse_mode="HTML")
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"{E['ALERT1']} <b>Thông tin ngân hàng của bạn đã được Admin reset.</b>\n{E['ARROW_DOWN']} Vui lòng dùng <code>/lk STK NGAN_HANG TEN_CHU_TAI_KHOAN</code> để cài đặt lại.",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Không gửi được thông báo reset bank cho user %s: %s", target_id, exc)

# ============================================================
# RÚT TIỀN
# ============================================================

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    message = update.effective_message
    if not user or not message or update.effective_chat.type != "private" or user_withdraw_state.get(user.id) != "WAITING_AMOUNT":
        return False

    if not await get_setting("enable_withdraw", "1"):
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(f"{E['STOP']} <b>Chức năng rút tiền hiện đã bị khóa bởi Admin.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")
        return True

    raw_text = (message.text or "").strip()
    text = raw_text.replace(",", "").replace(".", "")
    if text.lower() in ["hủy", "huy", "cancel", "❌ hủy", "❌ hủy rút tiền"]:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(f"{E['BAN']} <b>Đã hủy thao tác rút tiền.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")
        return True
    if not text.isdigit():
        await message.reply_text(f"{E['BAN']} <b>Số tiền phải là số nguyên hợp lệ!</b>\nVui lòng nhập lại (hoặc nhập <b>hủy</b> để thoát):", parse_mode="HTML")
        return True
    amount = int(text)
    if amount <= 0:
        await message.reply_text("❌ Số tiền không hợp lệ.")
        return True
    db_user = await db_query("SELECT balance, bank_info, is_banned, is_withdraw_banned FROM users WHERE user_id=%s", (user.id,), fetchone=True)
    if not db_user:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text("❌ Không tìm thấy tài khoản. Vui lòng /start lại.")
        return True
    balance, bank_info, is_banned, is_withdraw_banned = db_user
    if is_banned:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text("🚫 Tài khoản của bạn đã bị cấm.")
        return True
    if is_withdraw_banned:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text("🚫 Bạn đã bị cấm rút tiền.")
        return True
    if not bank_info:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text("⚠️ Chưa liên kết ngân hàng. Dùng /lk trước.")
        return True
    if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
        await message.reply_text(f"{E['BAN']} Số tiền rút phải từ <b>{MIN_WITHDRAW:,}đ</b> đến <b>{MAX_WITHDRAW:,}đ</b>!", parse_mode="HTML")
        return True
    try:
        def create_withdraw(cursor):
            cursor.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s AND balance >= %s AND is_banned=0 AND is_withdraw_banned=0", (amount, user.id, amount))
            if cursor.rowcount != 1:
                return None
            cursor.execute("INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (user.id, "Rút Tiền", amount, "Chờ duyệt", get_now_str(), bank_info))
            return cursor.fetchone()[0]
        tx_id = await db_transaction(create_withdraw)
    except Exception as exc:
        logger.exception("Lỗi tạo lệnh rút: %s", exc)
        await message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại sau.")
        return True
    if not tx_id:
        await message.reply_text("❌ Số dư không đủ hoặc tài khoản đang bị hạn chế.")
        return True
    user_withdraw_state.pop(user.id, None)
    await message.reply_text(f"{E['CALENDAR']} <b>YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC GỬI!</b>\n{E['GEAR']} Vui lòng chờ Admin kiểm tra và duyệt tiền.", reply_markup=get_main_keyboard(), parse_mode="HTML")
    admin_buttons = [[InlineKeyboardButton("✅ DUYỆT", callback_data=f"approve_{tx_id}"), InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"reject_{tx_id}")]]
    username_str = f"@{user.username}" if user.username else str(user.id)
    admin_msg = (
        f"{E['ALERT1']} <b>LỆNH RÚT TIỀN MỚI (# {tx_id})</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"{E['EYES']} <b>Khách hàng:</b> {username_str} (<code>{user.id}</code>)\n"
        f"{E['UP']} <b>Số tiền rút:</b> <code>{amount:,}đ</code>\n"
        f"{E['LOCK']} <b>Ngân hàng:</b> <code>{bank_info}</code>\n"
        f"{E['MAIL']} <b>Nội dung chuyển:</b> <code>lixi trung thu</code>\n"
        f"{E['CALENDAR']} <b>Thời gian:</b> <code>{get_now_str()}</code>"
    )

    qr_url = generate_vietqr_url(bank_info, amount, memo="lixi trung thu")
    msg_refs = context.bot_data.setdefault(f"tx_msgs_{tx_id}", [])

    for admin_id in ADMIN_IDS:
        try:
            if qr_url:
                sent_msg = await context.bot.send_photo(chat_id=admin_id, photo=qr_url, caption=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="HTML")
            else:
                sent_msg = await context.bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="HTML")
            msg_refs.append({"chat_id": admin_id, "message_id": sent_msg.message_id, "base_text": admin_msg, "has_photo": bool(qr_url)})
        except Exception as exc:
            logger.exception("Không gửi được yêu cầu rút cho admin %s: %s", admin_id, exc)
    return True

# ============================================================
# DUYỆT / TỪ CHỐI LỆNH RÚT
# ============================================================

async def admin_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    admin_user = query.from_user
    if admin_user.id not in ADMIN_IDS:
        try: await query.answer("❌ Quyền truy cập bị từ chối.", show_alert=True)
        except Exception: pass
        return
    try: await query.answer()
    except Exception: pass
    data = query.data or ""
    try:
        action, tx_id_str = data.split("_", 1)
        tx_id = int(tx_id_str)
    except (ValueError, TypeError):
        return
    tx = await db_query("SELECT user_id, amount, status, details FROM transactions WHERE id=%s AND type='Rút Tiền'", (tx_id,), fetchone=True)
    if not tx:
        try: await query.edit_message_text("❌ Không tìm thấy giao dịch này.")
        except Exception: pass
        return
    user_id, amount, status, bank_info = tx
    admin_name_str = f"@{admin_user.username}" if admin_user.username else f"<code>{admin_user.id}</code>"
    if status != "Chờ duyệt":
        try: await query.answer("⚠ Giao dịch này đã được xử lý trước đó!", show_alert=True)
        except Exception: pass
        return

    async def update_admin_message(ref, new_text):
        try:
            if ref.get("has_photo"):
                await context.bot.edit_message_caption(chat_id=ref["chat_id"], message_id=ref["message_id"], caption=new_text, parse_mode="HTML")
            else:
                await context.bot.edit_message_text(chat_id=ref["chat_id"], message_id=ref["message_id"], text=new_text, parse_mode="HTML")
        except Exception: pass

    if action == "approve":
        try:
            def approve(cursor):
                cursor.execute("UPDATE transactions SET status='Thành công' WHERE id=%s AND status='Chờ duyệt'", (tx_id,))
                return cursor.rowcount == 1
            changed = await db_transaction(approve)
        except Exception as exc:
            logger.exception("Lỗi duyệt: %s", exc)
            return
        if changed:
            try: await context.bot.send_message(chat_id=user_id, text=f"{E['LOVE']} <b>RÚT TIỀN THÀNH CÔNG!</b>\nAdmin đã duyệt yêu cầu rút <b>{amount:,}đ</b> của bạn.", parse_mode="HTML")
            except Exception: pass
            refs = context.bot_data.pop(f"tx_msgs_{tx_id}", [])
            for ref in refs:
                update_text = f"{ref['base_text']}\n\n{E['THUMB']} <b>TRẠNG THÁI: ĐÃ DUYỆT RÚT TIỀN</b> (Bởi Admin {admin_name_str})"
                await update_admin_message(ref, update_text)

    elif action == "reject":
        try:
            def reject(cursor):
                cursor.execute("UPDATE transactions SET status='Từ chối' WHERE id=%s AND status='Chờ duyệt'", (tx_id,))
                if cursor.rowcount != 1:
                    return False
                cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (amount, user_id))
                return True
            changed = await db_transaction(reject)
        except Exception as exc:
            logger.exception("Lỗi từ chối: %s", exc)
            return
        if changed:
            try: await context.bot.send_message(chat_id=user_id, text=f"{E['BAN']} <b>YÊU CẦU RÚT TIỀN BỊ TỪ CHỐI</b>\n\nSố tiền <b>{amount:,}đ</b> đã được hoàn trả lại số dư.", parse_mode="HTML")
            except Exception: pass
            refs = context.bot_data.pop(f"tx_msgs_{tx_id}", [])
            for ref in refs:
                update_text = f"{ref['base_text']}\n\n{E['BAN']} <b>TRẠNG THÁI: ĐÃ TỪ CHỐI</b> (Bởi Admin {admin_name_str})"
                await update_admin_message(ref, update_text)

# ============================================================
# ADMIN USER INFO
# ============================================================

async def admin_userinfo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if query.from_user.id not in ADMIN_IDS:
        try: await query.answer("❌ Quyền truy cập bị từ chối.", show_alert=True)
        except Exception: pass
        return
    try: await query.answer()
    except Exception: pass
    data = query.data or ""
    try:
        target_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        return
    u = await db_query(USER_SELECT_QUERY, (target_id,), fetchone=True)
    if not u:
        try: await query.answer("❌ Không tìm thấy thông tin user này.", show_alert=True)
        except Exception: pass
        return
    res = await db_query("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (target_id,), fetchone=True)
    invited_count = res[0]
    username = f"@{u[1]}" if u[1] else "Chưa đặt"
    bank = u[3] if u[3] else "Chưa liên kết"
    referrer = u[4] if u[4] is not None else "Không có"
    msg = (
        f"{E['EYES']} <b>THÔNG TIN CHI TIẾT USER</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"{E['EYES']} ID: <code>{u[0]}</code>\n"
        f"{E['COOL']} Username: {username}\n"
        f"{E['PHONE']} SĐT: <code>{u[5] or 'Chưa xác minh'}</code>\n"
        f"{E['UP']} Số dư: <code>{u[2]:,}đ</code>\n"
        f"{E['LOCK']} Ngân hàng: <code>{bank}</code>\n"
        f"{E['CLIP']} Khách giới thiệu: <code>{referrer}</code>\n"
        f"{E['COOL']} Tổng đã mời: <code>{invited_count}</code> người\n"
        f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[10] else 'KHÔNG'}</b>\n"
        f"{E['STOP']} Cấm rút: <b>{'CÓ' if u[11] else 'KHÔNG'}</b>\n"
        f"{E['CALENDAR']} Tham gia: <code>{u[12]}</code>"
    )
    await context.bot.send_message(chat_id=query.from_user.id, text=msg, parse_mode="HTML")

# ============================================================
# ADMIN COMMANDS
# ============================================================

def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    message = update.effective_message
    if not message:
        return
    cmd = (message.text or "").split()[0].split("@")[0].lower()
    args = context.args or []
    try:
        if cmd == "/resetall":
            await db_query("TRUNCATE TABLE users, transactions RESTART IDENTITY", commit=True)
            user_msg_tracker.clear()
            temp_bans.clear()
            user_withdraw_state.clear()
            await db_query("INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING", (message.from_user.id, message.from_user.username or "", get_now_str()), commit=True)
            await message.reply_text(
                f"{E['REFRESH']} <b>ĐÃ RESET TOÀN BỘ HỆ THỐNG!</b>\n"
                f"• Toàn bộ người dùng & lịch sử giao dịch đã được xóa hoàn toàn.\n"
                f"• Bạn và người dùng cũ giờ đây đã có thể ấn nút hoặc dùng lại link ref bình thường.",
                parse_mode="HTML"
            )
        elif cmd == "/tong":
            res = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
            total_users = res[0]
            users = await db_query("SELECT user_id, username FROM users ORDER BY joined_at DESC LIMIT 50", fetchall=True)
            msg = (
                f"{E['CHART']} <b>THỐNG KÊ TỔNG NGUỜI DÙNG</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['COOL']} Tổng số người dùng trong hệ thống: <b>{total_users:,}</b>\n\n"
                f"{E['ARROW_DOWN']} <b>Bấm vào nút ID bên dưới để kiểm tra full thông tin:</b>"
            )
            buttons = []
            row = []
            for u_id, u_name in users:
                btn_text = f"🆔 {u_id}"
                if u_name:
                    btn_text += f" (@{u_name})"
                row.append(InlineKeyboardButton(btn_text, callback_data=f"userinfo_{u_id}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            await message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode="HTML")

        elif cmd == "/tongrut":
            res = await db_query("SELECT COALESCE(SUM(amount), 0)::BIGINT, COUNT(*) FROM transactions WHERE type='Rút Tiền' AND status='Thành công'", fetchone=True)
            total_amount, total_count = (res[0] if res else 0), (res[1] if res else 0)
            msg = (
                f"{E['DOWN']} <b>TỔNG TOÀN BỘ SỐ TIỀN ĐÃ RÚT THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['UP']} <b>Tổng số tiền đã rút:</b> <code>{total_amount:,}đ</code>\n"
                f"{E['CHART']} <b>Tổng số lệnh thành công:</b> <code>{total_count:,}</code> lệnh"
            )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/rutid":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/rutid USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return
            u = await db_query(USER_SELECT_QUERY, (target_id,), fetchone=True)
            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return
            
            # Đã sửa lỗi tràn số bằng cách ép kiểu ::BIGINT cho các trường SUM và COUNT
            stats = await db_query(
                """
                SELECT 
                    COALESCE(COUNT(*), 0)::BIGINT,
                    COALESCE(SUM(CASE WHEN status='Thành công' THEN amount ELSE 0 END), 0)::BIGINT,
                    COALESCE(COUNT(CASE WHEN status='Thành công' THEN 1 END), 0)::BIGINT,
                    COALESCE(COUNT(CASE WHEN status='Chờ duyệt' THEN 1 END), 0)::BIGINT,
                    COALESCE(COUNT(CASE WHEN status='Từ chối' THEN 1 END), 0)::BIGINT
                FROM transactions
                WHERE user_id=%s AND type='Rút Tiền'
                """,
                (target_id,), fetchone=True
            )
            
            if not stats:
                total_attempts, success_amount, success_count, pending_count, reject_count = 0, 0, 0, 0, 0
            else:
                total_attempts, success_amount, success_count, pending_count, reject_count = stats

            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            bank = u[3] if u[3] else "Chưa liên kết"
            referrer = u[4] if u[4] is not None else "Không có"
            withdraw_txs = await db_query("SELECT id, amount, status, created_at FROM transactions WHERE user_id=%s AND type='Rút Tiền' ORDER BY id DESC LIMIT 10", (target_id,), fetchall=True)
            
            msg = (
                f"{E['EYES']} <b>THÔNG TIN RÚT TIỀN CỦA USER <code>{target_id}</code></b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['COOL']} Username: {username}\n"
                f"{E['PHONE']} SĐT: <code>{u[5] or 'Chưa xác minh'}</code>\n"
                f"{E['UP']} Số dư hiện tại: <code>{u[2]:,}đ</code>\n"
                f"{E['LOCK']} Ngân hàng: <code>{bank}</code>\n"
                f"{E['CLIP']} Người giới thiệu: <code>{referrer}</code>\n"
                f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[10] else 'KHÔNG'}</b> | Cấm rút: <b>{'CÓ' if u[11] else 'KHÔNG'}</b>\n"
                f"{E['CALENDAR']} Ngày tham gia: <code>{u[12]}</code>\n\n"
                f"{E['CHART']} <b>THỐNG KÊ RÚT TIỀN:</b>\n"
                f"• {E['DOWN']} Tổng tiền đã rút thành công: <code>{success_amount:,}đ</code>\n"
                f"• {E['THUMB']} Số lần rút thành công: <code>{success_count}</code> lần\n"
                f"• {E['CALENDAR']} Số lần đang chờ duyệt: <code>{pending_count}</code> lần\n"
                f"• {E['BAN']} Số lần bị từ chối: <code>{reject_count}</code> lần\n"
                f"• {E['LIGHTNING']} Tổng số lần gửi yêu cầu rút: <code>{total_attempts}</code> lần\n\n"
                f"{E['CHART']} <b>LỊCH SỬ RÚT TIỀN GẦN ĐÂY:</b>\n"
            )
            if withdraw_txs:
                for tx_id, amount, status, created_at in withdraw_txs:
                    icon = E['THUMB'] if status == "Thành công" else (E['BAN'] if status == "Từ chối" else E['CALENDAR'])
                    msg += f"{icon} #{tx_id} | <code>{amount:,}đ</code> | {status} | <code>{created_at}</code>\n"
            else:
                msg += "• Chưa có giao dịch rút tiền nào.\n"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/dl":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/dl USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return

            target_user = await db_query("SELECT user_id, username FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not target_user:
                await message.reply_text("❌ Không tìm thấy ID này trong cơ sở dữ liệu.")
                return

            invited_users = await db_query("SELECT user_id, username, is_captcha_passed, is_phone_verified, ref_rewarded, joined_at FROM users WHERE referrer_id=%s ORDER BY joined_at DESC", (target_id,), fetchall=True)

            if not invited_users:
                await message.reply_text(f"{E['ALERT1']} Người dùng <code>{target_id}</code> chưa giới thiệu được ai.", parse_mode="HTML")
                return

            await message.reply_text(f"{E['REFRESH']} Đang kiểm tra danh sách {len(invited_users)} người được mời, vui lòng đợi giây lát...", parse_mode="HTML")

            msg = f"{E['CHART']} <b>DANH SÁCH CHI TIẾT NGUỜI ĐƯỢC MỜI BỞI <code>{target_id}</code></b>\n━━━━━━━━━━━━━━━━━━\n"
            msg += f"{E['COOL']} Tổng người đã giới thiệu: <b>{len(invited_users)}</b>\n\n"

            for inv_id, inv_username, is_captcha, is_phone, ref_rewarded, joined_at in invited_users:
                uname = f"@{inv_username}" if inv_username else f"<code>{inv_id}</code>"
                try: missing_ch = await get_missing_channels(context.bot, inv_id)
                except Exception: missing_ch = []

                msg += f"👤 <b>Thành viên:</b> {uname} (<code>{inv_id}</code>)\n"
                msg += f"🗓 <b>Tham gia:</b> <code>{joined_at or 'N/A'}</code>\n"
                msg += f"├ {'✅ Đã chia sẻ' if is_phone else '❌ Chưa chia sẻ'} Số điện thoại (+84)\n"
                msg += f"├ {'✅ Đã giải' if is_captcha else '❌ Chưa giải'} Captcha\n"
                if not missing_ch:
                    msg += f"└ <b>Kênh đối tác:</b> Đã tham gia ĐỦ\n"
                else:
                    msg += f"└ <b>Kênh CHƯA VÀO ({len(missing_ch)}):</b> <i>{', '.join(missing_ch)}</i>\n"

                msg += "----------------------------------\n"
                if len(msg) > 3500:
                    await message.reply_text(msg, parse_mode="HTML")
                    msg = ""
                await asyncio.sleep(0.05)

            if msg.strip():
                await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/tb":
            if not args:
                await message.reply_text(f"Cú pháp: <code>/tb Nội dung thông báo</code>", parse_mode="HTML")
                return
            content = " ".join(args).strip()
            users = await db_query("SELECT user_id FROM users WHERE is_banned=0", fetchall=True)
            groups = await db_query("SELECT chat_id FROM groups", fetchall=True)
            count = 0
            for (target_id,) in users:
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"{E['SPEAKER']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}", parse_mode="HTML")
                    count += 1
                except Exception: pass
                await asyncio.sleep(0.02)
            for (chat_id,) in groups:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=f"{E['SPEAKER']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}", parse_mode="HTML")
                    count += 1
                except Exception: pass
                await asyncio.sleep(0.02)
            await message.reply_text(f"{E['THUMB']} Đã phát thông báo tới <b>{count}</b> người dùng/nhóm.", parse_mode="HTML")

        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/info USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return
            u = await db_query(USER_SELECT_QUERY, (target_id,), fetchone=True)
            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return
            res = await db_query("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (target_id,), fetchone=True)
            msg = (
                f"{E['EYES']} <b>THÔNG TIN CHI TIẾT USER</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"{E['EYES']} ID: <code>{u[0]}</code>\n"
                f"{E['COOL']} Username: @{u[1] if u[1] else 'Chưa đặt'}\n"
                f"{E['PHONE']} SĐT: <code>{u[5] or 'Chưa xác minh'}</code>\n"
                f"{E['UP']} Số dư: <code>{u[2]:,}đ</code>\n"
                f"{E['LOCK']} Ngân hàng: <code>{u[3] or 'Chưa liên kết'}</code>\n"
                f"{E['CLIP']} Người giới thiệu: <code>{u[4] if u[4] else 'Không có'}</code>\n"
                f"{E['COOL']} Tổng đã mời: <code>{res[0]}</code> người\n"
                f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[10] else 'KHÔNG'}</b>\n"
                f"{E['STOP']} Cấm rút: <b>{'CÓ' if u[11] else 'KHÔNG'}</b>\n"
                f"{E['CALENDAR']} Tham gia: <code>{u[12]}</code>"
            )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/bb":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/bb USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return
            invited_users = await db_query("SELECT user_id, username, joined_at, ref_rewarded, is_captcha_passed, is_phone_verified FROM users WHERE referrer_id=%s ORDER BY joined_at DESC", (target_id,), fetchall=True)
            msg = f"{E['COOL']} <b>DANH SÁCH BẠN BÈ MỜI CỦA USER <code>{target_id}</code></b> (Tổng: <code>{len(invited_users)}</code> người):\n━━━━━━━━━━━━━━━━━━\n\n"
            if invited_users:
                for invited_id, username, joined_at, ref_rewarded, is_captcha_passed, is_phone_verified in invited_users:
                    uname = f"@{username}" if username else "Chưa đặt username"
                    status = "✅ Hợp lệ" if ref_rewarded == 1 else ("⏳ Chưa xác minh SĐT" if is_phone_verified == 0 else ("⏳ Chưa giải CAPTCHA" if is_captcha_passed == 0 else "⏳ Chưa hoàn tất"))
                    msg += f"• ID: <code>{invited_id}</code> | Name: {uname} | {status}\n"
            else:
                msg += "❌ Người dùng này chưa mời được ai.\n"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/ban":
            if len(args) < 1: return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['BAN']} Đã cấm vĩnh viễn user <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/moban":
            if len(args) < 1: return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['THUMB']} <b>Đã mở ban tài khoản cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

        elif cmd == "/cam":
            if len(args) < 1: return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['STOP']} Đã cấm rút tiền ID <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/mocam":
            if len(args) < 1: return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['THUMB']} <b>Đã mở cấm rút tiền cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

        elif cmd in ("/nap", "/tru"):
            if len(args) < 2: return
            target_id, amount = int(args[0]), int(args[1])
            if cmd == "/nap":
                def add_money(cursor):
                    cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, target_id))
                    cursor.execute("INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)", (target_id, "Nạp Tiền (Admin)", amount, "Thành công", get_now_str(), "Cộng từ Admin"))
                    return True
                await db_transaction(add_money)
                await message.reply_text(f"{E['THUMB']} Đã cộng <b>+{amount:,}đ</b> cho ID <code>{target_id}</code>.", parse_mode="HTML")
            else:
                def deduct(cursor):
                    cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s AND balance>=%s", (amount, target_id, amount))
                    if cursor.rowcount != 1: return False
                    cursor.execute("INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)", (target_id, "Trừ Tiền (Admin)", amount, "Thành công", get_now_str(), "Trừ từ Admin"))
                    return True
                if await db_transaction(deduct):
                    await message.reply_text(f"{E['BAN']} Đã trừ <b>-{amount:,}đ</b> của ID <code>{target_id}</code>.", parse_mode="HTML")
                else:
                    await message.reply_text("❌ Số dư user không đủ để trừ.")

        elif cmd == "/rutls":
            txs = await db_query("SELECT id, user_id, amount, details, created_at FROM transactions WHERE type='Rút Tiền' AND status='Chờ duyệt' ORDER BY id ASC", fetchall=True)
            if not txs:
                await message.reply_text(f"{E['LOVE']} Không có yêu cầu rút tiền nào đang chờ duyệt!")
                return
            
            await message.reply_text(f"{E['REFRESH']} Đang tải {len(txs)} lệnh rút tiền đang chờ duyệt...", parse_mode="HTML")
            
            for tx_id, target_id, amount, details, created_at in txs:
                btns = [[
                    InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tx_id}"),
                    InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tx_id}")
                ]]
                msg_text = f"{E['EYES']} <b>Lệnh:</b> #{tx_id}\n{E['COOL']} <b>User:</b> <code>{target_id}</code>\n{E['UP']} <b>Số tiền:</b> <code>{amount:,}đ</code>\n{E['LOCK']} <b>Bank:</b> <code>{details or 'N/A'}</code>"
                
                qr_url = generate_vietqr_url(details, amount, memo="lixi trung thu") if details else ""
                try:
                    if qr_url:
                        sent_msg = await message.reply_photo(photo=qr_url, caption=msg_text, reply_markup=InlineKeyboardMarkup(btns), parse_mode="HTML")
                    else:
                        sent_msg = await message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(btns), parse_mode="HTML")
                    
                    refs = context.bot_data.setdefault(f"tx_msgs_{tx_id}", [])
                    refs.append({"chat_id": message.chat_id, "message_id": sent_msg.message_id, "base_text": msg_text, "has_photo": bool(qr_url)})
                except Exception as exc:
                    logger.error("Lỗi gửi ảnh QR lệnh rút #%s: %s", tx_id, exc)
                    sent_msg = await message.reply_text(msg_text + f"\n\n⚠ <i>(Không tải được ảnh QR VietQR)</i>", reply_markup=InlineKeyboardMarkup(btns), parse_mode="HTML")
                    refs = context.bot_data.setdefault(f"tx_msgs_{tx_id}", [])
                    refs.append({"chat_id": message.chat_id, "message_id": sent_msg.message_id, "base_text": msg_text, "has_photo": False})
                
                await asyncio.sleep(0.15)

        elif cmd == "/ruttc":
            txs = await db_query("SELECT id, user_id, amount, created_at FROM transactions WHERE type='Rút Tiền' AND status='Thành công' ORDER BY id DESC LIMIT 15", fetchall=True)
            if not txs:
                await message.reply_text("📜 Chưa có lệnh rút nào được duyệt.")
                return
            msg = f"{E['CHART']} <b>LỆNH RÚT ĐÃ DUYỆT GẦN ĐÂY:</b>\n\n"
            for tx_id, target_id, amount, created_at in txs:
                msg += f"{E['THUMB']} #{tx_id} | <code>{target_id}</code> | <code>{amount:,}đ</code> | <code>{created_at}</code>\n"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/lsgd":
            if len(args) < 1: return
            target_id = int(args[0])
            txs = await db_query("SELECT type, amount, status, created_at FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 10", (target_id,), fetchall=True)
            msg = f"{E['CHART']} <b>LỊCH SỬ GIAO DỊCH CỦA {target_id}:</b>\n"
            if txs:
                for tx_type, amount, status, created_at in txs:
                    msg += f"• {tx_type}: <code>{amount:,}đ</code> [{status}] - <code>{created_at}</code>\n"
            else:
                msg += "• Chưa có giao dịch.\n"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/baotri":
            curr = await is_maintenance()
            await set_setting("maintenance", "0" if curr else "1")
            await message.reply_text(f"{E['GEAR']} Trạng thái hệ thống: <b>{'TẮT BẢO TRÌ 🟢' if curr else 'BẮT ĐẦU BẢO TRÌ 🔴'}</b>", parse_mode="HTML")

        elif cmd == "/batbt":
            await set_setting("maintenance", "1")
            await message.reply_text(f"{E['STOP']} <b>ĐÃ BẬT CHẾ ĐỘ BẢO TRÌ HỆ THỐNG!</b>", parse_mode="HTML")

        elif cmd == "/tatbt":
            await set_setting("maintenance", "0")
            await message.reply_text(f"{E['LIGHTNING']} <b>ĐÃ TẮT BẢO TRÌ HỆ THỐNG!</b>", parse_mode="HTML")

        elif cmd == "/resetbank":
            await reset_bank_command(update, context)

    except Exception as exc:
        logger.exception("Lỗi admin command %s: %s", cmd, exc)
        await message.reply_text("❌ Đã xảy ra lỗi khi xử lý lệnh.")

# ============================================================
# DISPATCHER
# ============================================================

async def text_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or await handle_anti_spam(update, context):
        return
    if await handle_withdraw_amount(update, context):
        return
    await menu_handler(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception khi xử lý update: %s", context.error, exc_info=context.error)

# ============================================================
# MAIN
# ============================================================

async def post_init(application: Application) -> None:
    await init_db()

def main():
    if not BOT_TOKEN or not DATABASE_URL:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN hoặc DATABASE_URL.")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("lk", link_bank_command))
    
    app.add_handler(CommandHandler("menu", admin_menu_panel))
    app.add_handler(CommandHandler("setmenu", admin_menu_panel))
    app.add_handler(CommandHandler("bo", bo_ip_command))
    app.add_handler(CommandHandler("moip", mo_ip_command))

    admin_cmds = [
        "resetall", "tong", "tongrut", "rutid", "tb", "info", "bb", "ban", "moban",
        "cam", "mocam", "rutls", "ruttc", "nap", "tru", "lsgd", "baotri", "batbt",
        "tatbt", "resetbank", "dl"
    ]
    for command in admin_cmds:
        app.add_handler(CommandHandler(command, admin_commands))

    app.add_handler(ChatMemberHandler(chat_member_updated_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$"))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_withdraw_callback, pattern=r"^cancel_withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_withdraw_callback, pattern=r"^(approve|reject)_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_userinfo_callback, pattern=r"^userinfo_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_callback, pattern=r"^toggle_"))
    app.add_handler(CallbackQueryHandler(force_verify_all_callback, pattern=r"^force_verify_all$"))

    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
