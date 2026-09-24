import asyncio
import logging
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import tuple_row
import pytz

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
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

# Danh sách ID Admin (Đã giữ ID 5633649201)
ADMIN_IDS = [5633649201]

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

# Kênh/Nhóm kiểm tra tham gia (Đã thêm @sanhugame)
REQUIRED_CHECK_CHANNELS = [
    "@sanhugame",
    "@chungnaomoidu",
    "@khuyenmaionline",
    "@sancode22",
    "@xombao247",
    "@thongbaohit88",
]

SUPPORT_GROUP = "https://t.me/conmuamenmenl"

MIN_WITHDRAW = 5000
MAX_WITHDRAW = 300000
REFERRAL_REWARD = 1000


# ============================================================
# DANH SÁCH EMOJI
# ============================================================
E = {
    "CROWN": '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
    "REFRESH": '<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>',
    "TOP": '<tg-emoji emoji-id="5415655814079723871">🔝</tg-emoji>',
    "EYES": '<tg-emoji emoji-id="5210956306952758910">👀</tg-emoji>',
    "LIGHTNING": '<tg-emoji emoji-id="5456140674028019486">⚡️</tg-emoji>',
    "COMET": '<tg-emoji emoji-id="5224607267797606837">☄️</tg-emoji>',
    "STOP": '<tg-emoji emoji-id="5260293700088511294">⛔️</tg-emoji>',
    "BAN": '<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji>',
    "WARN1": '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji>',
    "WARN2": '<tg-emoji emoji-id="5440660757194744323">‼️</tg-emoji>',
    "WARN3": '<tg-emoji emoji-id="5314504236132747481">⁉️</tg-emoji>',
    "QUESTION": '<tg-emoji emoji-id="5436113877181941026">❓</tg-emoji>',
    "ALERT1": '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>',
    "ALERT2": '<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji>',
    "CHART": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "UP": '<tg-emoji emoji-id="5449683594425410231">🔼</tg-emoji>',
    "DOWN": '<tg-emoji emoji-id="5447183459602669338">🔽</tg-emoji>',
    "MEDAL1": '<tg-emoji emoji-id="5440539497383087970">🥇</tg-emoji>',
    "MEDAL2": '<tg-emoji emoji-id="5447203607294265305">🥈</tg-emoji>',
    "MEDAL3": '<tg-emoji emoji-id="5453902265922376865">🥉</tg-emoji>',
    "FREE": '<tg-emoji emoji-id="5406756500108501710">🆓</tg-emoji>',
    "PENCIL": '<tg-emoji emoji-id="5395444784611480792">✏️</tg-emoji>',
    "CALENDAR": '<tg-emoji emoji-id="5413879192267805083">🗓</tg-emoji>',
    "DROP": '<tg-emoji emoji-id="5393512611968995988">💧</tg-emoji>',
    "SNOW": '<tg-emoji emoji-id="5449449325434266744">❄️</tg-emoji>',
    "SUN": '<tg-emoji emoji-id="5402477260982731644">☀️</tg-emoji>',
    "ARROW_DOWN": '<tg-emoji emoji-id="5406745015365943482">⬇️</tg-emoji>',
    "MAIL": '<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji>',
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
}


# ============================================================
# ANTI SPAM
# ============================================================

SPAM_WINDOW_SECONDS = 4
SPAM_MAX_MESSAGES = 10
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

def get_db():
    if not DATABASE_URL:
        raise RuntimeError("Chưa cấu hình DATABASE_URL trên Railway.")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=tuple_row,
        connect_timeout=15,
    )


def init_db():
    conn = get_db()

    try:
        cursor = conn.cursor()

        # USERS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                balance BIGINT NOT NULL DEFAULT 0,
                bank_info TEXT,
                referrer_id BIGINT,
                is_banned INTEGER NOT NULL DEFAULT 0,
                is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT
            )
            """
        )

        # TRANSACTIONS
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

        # GROUPS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                chat_id BIGINT PRIMARY KEY
            )
            """
        )

        # SETTINGS
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO settings (key, value)
            VALUES ('maintenance', '0')
            ON CONFLICT (key) DO NOTHING
            """
        )

        # INDEXES
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_user
            ON transactions(user_id, id DESC)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_withdraw
            ON transactions(type, status, id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_referrer
            ON users(referrer_id)
            """
        )

        conn.commit()
        logger.info("Database PostgreSQL đã sẵn sàng.")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def db_query(
    query,
    params=(),
    fetchone=False,
    fetchall=False,
    commit=False,
):
    conn = get_db()

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)

        if fetchone:
            return cursor.fetchone()

        if fetchall:
            return cursor.fetchall()

        if commit:
            conn.commit()

        return None

    except Exception:
        if commit:
            conn.rollback()
        raise

    finally:
        conn.close()


def db_transaction(callback):
    conn = get_db()

    try:
        cursor = conn.cursor()
        result = callback(cursor)
        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# KEYBOARD
# ============================================================

def get_main_keyboard():
    keyboard = [
        [
            KeyboardButton("👤 Tài Khoản"),
            KeyboardButton("🎁 Mời Bạn Bè"),
        ],
        [
            KeyboardButton("💳 Rút Tiền"),
            KeyboardButton("💬 Nhóm Hỗ Trợ"),
        ],
        [
            KeyboardButton("📜 Lịch Sử Giao Dịch"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


# ============================================================
# MAINTENANCE
# ============================================================

def is_maintenance():
    res = db_query(
        """
        SELECT value
        FROM settings
        WHERE key='maintenance'
        """,
        fetchone=True,
    )

    return bool(res and res[0] == "1")


# ============================================================
# CAPTCHA
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


# ============================================================
# KIỂM TRA THAM GIA KÊNH
# ============================================================

async def check_channel_membership(bot, user_id):
    for channel in REQUIRED_CHECK_CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id,
            )

            if member.status in ("left", "kicked"):
                return False

        except Exception as exc:
            logger.warning(
                "Không thể kiểm tra user %s trong %s (Lỗi: %s). Bỏ qua kiểm tra kênh này.",
                user_id,
                channel,
                exc,
            )
            continue

    return True


# ============================================================
# XỬ LÝ KHI NGƯỜI DÙNG RỜI HOẶC THAM GIA LẠI NHÓM/KÊNH
# ============================================================

async def chat_member_updated_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    result = update.chat_member or update.my_chat_member
    if not result:
        return

    old_state = result.old_chat_member.status
    new_state = result.new_chat_member.status

    user = result.new_chat_member.user

    # Lấy thông tin referrer_id của người dùng này
    user_info = db_query(
        "SELECT referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )

    if not user_info or not user_info[0]:
        return

    ref_id = user_info[0]
    username_str = f"@{user.username}" if user.username else str(user.id)

    # TH1: BẠN BÈ RỜI KÊNH/NHÓM
    if old_state in ("member", "administrator", "creator") and new_state in ("left", "kicked"):
        db_query(
            "UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s",
            (ref_id,),
            commit=True,
        )

        user_withdraw_state.pop(ref_id, None)

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"{E['BAN']} <b>THÔNG BÁO TỪ HỆ THỐNG</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['STOP']} Bạn đã rời khỏi nhóm/kênh đối tác bắt buộc.\n"
                    f"{E['ALERT1']} Tài khoản của bạn và người giới thiệu bạn đã bị hạn chế các tính năng rút tiền!"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Không gửi được thông báo cho người rời nhóm %s: %s", user.id, exc)

        try:
            await context.bot.send_message(
                chat_id=ref_id,
                text=(
                    f"{E['BAN']} <b>CẢNH BÁO KHÓA RÚT TIỀN!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['STOP']} Thành viên được bạn mời (<b>{username_str}</b> - <code>{user.id}</code>) đã rời khỏi nhóm/kênh đối tác.\n"
                    f"{E['ALERT1']} <b>Lý do bị khóa:</b> Người được bạn mời đã rời nhóm nên hệ thống tiến hành khoá tính năng rút tiền của bạn!"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Không gửi được thông báo khóa rút tiền cho referrer %s: %s", ref_id, exc)

    # TH2: BẠN BÈ THAM GIA LẠI KÊNH/NHÓM
    elif old_state in ("left", "kicked") and new_state in ("member", "administrator", "creator"):
        # Kiểm tra xem người dùng đã tham gia đủ tất cả kênh bắt buộc chưa
        is_fully_joined = await check_channel_membership(context.bot, user.id)

        if is_fully_joined:
            # Kiểm tra xem những người dùng khác mà ref_id này từng mời có ai còn đang rời kênh không
            invited_users = db_query(
                "SELECT user_id FROM users WHERE referrer_id=%s",
                (ref_id,),
                fetchall=True,
            )

            all_friends_joined = True
            if invited_users:
                for (inv_id,) in invited_users:
                    if not await check_channel_membership(context.bot, inv_id):
                        all_friends_joined = False
                        break

            # Nếu tất cả những người được mời đã tham gia đủ kênh -> Mở khóa rút tiền
            if all_friends_joined:
                db_query(
                    "UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s",
                    (ref_id,),
                    commit=True,
                )

                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"{E['THUMB']} <b>THÔNG BÁO MỞ KHÓA RÚT TIỀN!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{E['LIGHTNING']} Thành viên được bạn mời (<b>{username_str}</b> - <code>{user.id}</code>) đã tham gia lại nhóm/kênh đối tác.\n"
                            f"{E['UP']} <b>Hệ thống đã tự động mở khóa tính năng rút tiền cho bạn!</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo mở khóa rút tiền cho referrer %s: %s", ref_id, exc)


# ============================================================
# ANTI SPAM
# ============================================================

async def handle_anti_spam(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user = update.effective_user
    message = update.effective_message

    if not user or user.id in ADMIN_IDS or not message:
        return False

    now = datetime.now()
    ban_until = temp_bans.get(user.id)

    if ban_until:
        if now < ban_until:
            remaining_seconds = max(0, int((ban_until - now).total_seconds()))
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60

            await message.reply_text(
                f"{E['BAN']} <b>BẠN ĐÃ BỊ TẠM CẤM!</b>\n"
                f"{E['CALENDAR']} Vui lòng chờ: <b>{minutes} phút {seconds} giây</b>\n"
                f"{E['ALERT1']} Lý do: <b>Spam tin nhắn quá nhanh.</b>",
                parse_mode="HTML"
            )
            return True

        temp_bans.pop(user.id, None)

    times = user_msg_tracker[user.id]
    times.append(now)

    cutoff = now - timedelta(seconds=SPAM_WINDOW_SECONDS)
    user_msg_tracker[user.id] = [t for t in times if t >= cutoff]

    if len(user_msg_tracker[user.id]) >= SPAM_MAX_MESSAGES:
        temp_bans[user.id] = now + timedelta(minutes=TEMP_BAN_MINUTES)
        user_msg_tracker[user.id].clear()

        await message.reply_text(
            f"{E['BAN']} <b>CẢNH BÁO ANTI-SPAM</b>\n"
            f"{E['STOP']} Bạn đã bị cấm <b>{TEMP_BAN_MINUTES} phút</b>!\n"
            f"{E['ALERT1']} Lý do: Gửi quá <b>{SPAM_MAX_MESSAGES} tin nhắn</b> trong <b>{SPAM_WINDOW_SECONDS}s</b>.",
            parse_mode="HTML"
        )
        return True

    return False


# ============================================================
# USER
# ============================================================

async def ensure_user_exists(update: Update):
    user = update.effective_user
    if not user:
        return None

    row = db_query(
        """
        SELECT
            user_id,
            balance,
            bank_info,
            is_banned,
            is_withdraw_banned,
            referrer_id
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

    if row:
        current_username = user.username or ""
        db_query(
            """
            UPDATE users
            SET username=%s
            WHERE user_id=%s
            """,
            (current_username, user.id),
            commit=True,
        )
    else:
        # TỰ ĐỘNG TẠO USER MỚI NẾU KHÔNG TỒN TẠI TRONG DB
        db_query(
            """
            INSERT INTO users
                (user_id, username, balance, joined_at)
            VALUES
                (%s, %s, 0, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user.id, user.username or "", get_now_str()),
            commit=True,
        )
        row = db_query(
            """
            SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned, referrer_id
            FROM users WHERE user_id=%s
            """,
            (user.id,),
            fetchone=True,
        )

    return row


async def require_private_user(update: Update):
    if not update.effective_chat or update.effective_chat.type != "private":
        return False

    user = update.effective_user
    if not user:
        return False

    row = await ensure_user_exists(update)

    if row and row[3] == 1:
        await update.effective_message.reply_text(
            f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return False

    return True


# ============================================================
# START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if await handle_anti_spam(update, context):
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    if chat.type != "private":
        db_query(
            """
            INSERT INTO groups(chat_id)
            VALUES(%s)
            ON CONFLICT (chat_id) DO NOTHING
            """,
            (chat.id,),
            commit=True,
        )
        return

    if is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(
            f"{E['STOP']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"{E['GEAR']} Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!",
            parse_mode="HTML"
        )
        return

    db_user = db_query(
        """
        SELECT user_id, is_banned, referrer_id
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[1] == 1:
        await update.message.reply_text(
            f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return

    # MỜI BẠN BÈ
    referrer_id = None
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referrer_id = ref_id
        except (ValueError, TypeError):
            pass

    if not db_user:
        db_query(
            """
            INSERT INTO users
                (user_id, username, balance, referrer_id, joined_at)
            VALUES
                (%s, %s, 0, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user.id, user.username or "", referrer_id, get_now_str()),
            commit=True,
        )
    else:
        # CHO PHÉP CẬP NHẬT LẠI NẾU ĐÃ RESET TÀI KHOẢN HOẶC CHƯA CÓ MỜI
        if referrer_id is not None:
            db_query(
                """
                UPDATE users
                SET username=%s, referrer_id=%s
                WHERE user_id=%s
                """,
                (user.username or "", referrer_id, user.id),
                commit=True,
            )
        else:
            db_query(
                """
                UPDATE users
                SET username=%s
                WHERE user_id=%s
                """,
                (user.username or "", user.id),
                commit=True,
            )

    # CHECK JOIN KÊNH BẮT BUỘC
    is_joined = await check_channel_membership(context.bot, user.id)

    if not is_joined:
        buttons = [
            [
                InlineKeyboardButton(
                    "🎮 1. Săn Hũ Game",
                    url="https://t.me/sanhugame",
                )
            ],
            [
                InlineKeyboardButton(
                    "🎓 2. Chừng Nào Mới Đủ",
                    url="https://t.me/chungnaomoidu",
                )
            ],
            [
                InlineKeyboardButton(
                    "🌧️ 3. Khuyến Mãi Online",
                    url="https://t.me/khuyenmaionline",
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍️ 4. Săn Code 22",
                    url="https://t.me/sancode22",
                )
            ],
            [
                InlineKeyboardButton(
                    "📈 5. Xóm Báo 247",
                    url="https://t.me/xombao247",
                )
            ],
            [
                InlineKeyboardButton(
                    "💎 6. Thông Báo Hit88",
                    url="https://t.me/thongbaohit88",
                )
            ],
            [
                InlineKeyboardButton(
                    "❇️ XÁC NHẬN ĐÃ THAM GIA ❇️",
                    callback_data="verify_join",
                )
            ],
        ]

        await update.message.reply_text(
            f"{E['CROWN']} <b>CHÀO MỪNG BẠN ĐẾN VỚI HỆ THỐNG</b>\n"
            f"{E['CLIP']} <b>Vui lòng tham gia đầy đủ các kênh/nhóm đối tác bên dưới để tiếp tục:</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        f"{E['LIGHTNING']} <b>CHÀO MỪNG BẠN TRỜ LẠI HỆ THỐNG!</b>\n"
        f"{E['MEDAL1']} Hãy chọn một tính năng trong menu bên dưới:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# GỬI CAPTCHA
# ============================================================

async def send_captcha_challenge(
    update_or_query,
    context: ContextTypes.DEFAULT_TYPE,
    message_text="",
):
    a, b, correct_ans, options = generate_captcha()
    context.user_data["captcha_ans"] = correct_ans

    buttons = []
    row = []

    for opt in options:
        row.append(
            InlineKeyboardButton(
                f"🔹 {opt}",
                callback_data=f"captcha_{opt}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    caption = (f"{message_text}\n\n" if message_text else "")
    caption += (
        f"{E['GAME']} <b>XÁC MINH CAPTCHA BẢO MẬT</b>\n"
        f"{E['PENCIL']} Vui lòng giải phép tính bên dưới để hoàn tất đăng ký:\n"
        f"{E['QUESTION']} <b>{a} + {b} = ?</b>"
    )

    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
    else:
        await context.bot.send_message(
            chat_id=update_or_query.from_user.id,
            text=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )


# ============================================================
# VERIFY JOIN
# ============================================================

async def verify_join_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    user = query.from_user

    try:
        await query.answer()
    except Exception:
        pass

    if is_maintenance() and user.id not in ADMIN_IDS:
        try:
            await query.answer("🔴 Hệ thống đang bảo trì.", show_alert=True)
        except Exception:
            pass
        return

    is_joined = await check_channel_membership(context.bot, user.id)

    if not is_joined:
        try:
            await query.answer(
                "❌ Bạn chưa tham gia đầy đủ các kênh bắt buộc! Vui lòng kiểm tra lại.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    await send_captcha_challenge(query, context)


# ============================================================
# CAPTCHA CALLBACK
# ============================================================

async def captcha_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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

        await send_captcha_challenge(
            query,
            context,
            message_text=f"{E['WARN1']} <b>Bạn đã chọn sai kết quả! Vui lòng tính lại.</b>",
        )
        return

    context.user_data.pop("captcha_ans", None)

    try:
        await query.answer("✅ Xác minh CAPTCHA thành công!")
    except Exception:
        pass

    # THƯỞNG REFERRER
    db_user = db_query(
        """
        SELECT referrer_id
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[0]:
        ref_id = db_user[0]
        try:
            def reward_referrer(cursor):
                details = f"Mời {user.id}"

                cursor.execute(
                    """
                    INSERT INTO transactions
                        (user_id, type, amount, status, created_at, details)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        ref_id,
                        "Thưởng Mời Bạn",
                        REFERRAL_REWARD,
                        "Thành công",
                        get_now_str(),
                        details,
                    ),
                )

                cursor.execute(
                    """
                    UPDATE users
                    SET balance = balance + %s
                    WHERE user_id=%s
                    """,
                    (REFERRAL_REWARD, ref_id),
                )
                return True

            rewarded = db_transaction(reward_referrer)

            if rewarded:
                username_str = f"@{user.username}" if user.username else str(user.id)
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"{E['LOVE']} <b>THƯỞNG MỜI BẠN BÈ!</b>\n"
                            f"{E['UP']} Bạn nhận được <b>+{REFERRAL_REWARD:,}đ</b>\n"
                            f"{E['EYES']} Từ người dùng: <b>{username_str}</b>"
                        ),
                        parse_mode="HTML"
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo referrer: %s", exc)

        except Exception as exc:
            logger.exception("Lỗi transaction thưởng giới thiệu: %s", exc)

    try:
        await query.delete_message()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"{E['LAUGH1']} <b>XÁC MINH THÀNH CÔNG!</b>\n"
            f"{E['CROWN']} <b>Chào mừng bạn đã gia nhập hệ thống Bot VIP!</b>"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# MENU
# ============================================================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if update.effective_chat.type != "private":
        return

    db_user = await ensure_user_exists(update)

    user_withdraw_state.pop(user.id, None)

    if is_maintenance() and user.id not in ADMIN_IDS:
        await message.reply_text(
            f"{E['STOP']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"{E['GEAR']} Vui lòng quay lại sau!",
            parse_mode="HTML"
        )
        return

    if not db_user or db_user[3] == 1:
        await message.reply_text(
            f"{E['BAN']} <b>Tài khoản của bạn đã bị cấm khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return

    if user.id not in ADMIN_IDS:
        if not await check_channel_membership(context.bot, user.id):
            await message.reply_text(
                f"{E['ALERT1']} <b>Bạn chưa tham gia đủ các kênh bắt buộc!</b>\n"
                f"{E['ARROW_DOWN']} Vui lòng gõ /start để nhận danh sách kênh.",
                parse_mode="HTML"
            )
            return

    text = (message.text or "").strip()

    # TÀI KHOẢN
    if text in ["Tài Khoản", "👤 Tài Khoản"]:
        balance = db_user[1]
        invited_count = db_query(
            """
            SELECT COUNT(*)
            FROM users
            WHERE referrer_id=%s
            """,
            (user.id,),
            fetchone=True,
        )[0]

        total_withdraw = db_query(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE user_id=%s
            AND type='Rút Tiền'
            AND status='Thành công'
            """,
            (user.id,),
            fetchone=True,
        )[0]

        msg = (
            f"{E['CROWN']} <b>THÔNG TIN TÀI KHOẢN VIP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['EYES']} <b>ID:</b> <code>{user.id}</code>\n"
            f"{E['UP']} <b>Số dư:</b> <code>{balance:,}đ</code>\n"
            f"{E['COOL']} <b>Đã mời:</b> <code>{invited_count}</code> người\n"
            f"{E['DOWN']} <b>Đã rút:</b> <code>{total_withdraw:,}đ</code>"
        )

        await message.reply_text(msg, parse_mode="HTML")

    # MỜI BẠN
    elif text in ["Mời Bạn Bè", "🎁 Mời Bạn Bè"]:
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
            f"{E['FREE']} <b>CHƯƠNG TRÌNH MỜI BẠN BÈ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['CLIP']} <b>Link giới thiệu của bạn:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"{E['CALENDAR']} <b>Thể lệ nhận thưởng:</b>\n"
            f"• {E['LIGHTNING']} Nhận ngay: <b>+{REFERRAL_REWARD:,}đ</b> / lượt mời thành công.\n"
            f"• {E['CLIP']} Bạn bè phải tham gia đủ kênh & hoàn thành CAPTCHA.\n"
            f"• {E['DOWN']} Min rút: <b>{MIN_WITHDRAW:,}đ</b>\n"
            f"• {E['TOP']} Max rút: <b>{MAX_WITHDRAW:,}đ</b>"
        )

        await message.reply_text(msg, parse_mode="HTML")

    # NHÓM HỖ TRỢ
    elif text in ["Nhóm Hỗ Trợ", "💬 Nhóm Hỗ Trợ"]:
        await message.reply_text(
            f"{E['SPEAKER']} <b>NHÓM HỖ TRỢ CHÍNH THỨC:</b>\n👉 {SUPPORT_GROUP}",
            parse_mode="HTML",
        )

    # LỊCH SỬ
    elif text in ["Lịch Sử", "Lịch Sử Giao Dịch", "📜 Lịch Sử Giao Dịch"]:
        txs = db_query(
            """
            SELECT
                type,
                amount,
                status,
                created_at
            FROM transactions
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT 10
            """,
            (user.id,),
            fetchall=True,
        )

        if not txs:
            await message.reply_text(f"{E['CALENDAR']} <b>Bạn chưa có giao dịch nào.</b>", parse_mode="HTML")
            return

        msg = f"{E['CHART']} <b>LỊCH SỬ GIAO DỊCH GẦN ĐÂY</b>\n━━━━━━━━━━━━━━━━━━\n\n"

        for tx_type, amount, status, created_at in txs:
            icon = E['THUMB'] if status == "Thành công" else (E['BAN'] if status == "Từ chối" else E['CALENDAR'])
            msg += (
                f"{icon} <b>{tx_type}</b>: <code>{amount:,}đ</code>\n"
                f"{E['CHART']} Trạng thái: <b>{status}</b>\n"
                f"{E['CALENDAR']} Thời gian: <code>{created_at}</code>\n"
                "----------------------------------\n"
            )

        await message.reply_text(msg, parse_mode="HTML")

    # RÚT TIỀN
    elif text in ["Rút Tiền", "💳 Rút Tiền"]:
        if db_user[4] == 1:
            await message.reply_text(f"{E['BAN']} <b>Tài khoản của bạn đã bị CẤM RÚT TIỀN!</b>", parse_mode="HTML")
            return

        bank_info = db_user[2]

        if not bank_info:
            await message.reply_text(
                f"{E['ALERT1']} <b>BẠN CHƯA LIÊN KẾT NGÂN HÀNG</b>\n"
                f"{E['ARROW_DOWN']} Vui lòng gửi lệnh liên kết theo cú pháp:\n"
                f"<code>/lk STK Tên_Ngân_Hàng Tên_Chủ_Thẻ</code>\n\n"
                f"{E['LIGHTNING']} <b>Ví dụ:</b> <code>/lk 1068030300 VCB NGUYEN CA NGU</code>",
                parse_mode="HTML",
            )
        else:
            user_withdraw_state[user.id] = "WAITING_AMOUNT"
            cancel_btn = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "❌ HỦY THAO TÁC",
                        callback_data="cancel_withdraw",
                    )
                ]
            ])

            await message.reply_text(
                f"{E['TOP']} <b>LỆNH RÚT TIỀN VIP</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['LOCK']} <b>Tài khoản nhận:</b> <code>{bank_info}</code>\n"
                f"{E['UP']} <b>Số dư hiện tại:</b> <code>{db_user[1]:,}đ</code>\n"
                f"{E['CLIP']} <b>Hạn mức:</b> <code>{MIN_WITHDRAW:,}đ</code> - <code>{MAX_WITHDRAW:,}đ</code>\n\n"
                f"{E['ARROW_DOWN']} <b>Vui lòng nhập số tiền bạn muốn rút:</b>\n"
                f"<i>(Nhập 'hủy' hoặc bấm nút bên dưới để thoát)</i>",
                reply_markup=cancel_btn,
                parse_mode="HTML",
            )


# ============================================================
# HỦY RÚT
# ============================================================

async def cancel_withdraw_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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

    await context.bot.send_message(
        chat_id=user.id,
        text=f"{E['BAN']} <b>Đã hủy thao tác rút tiền.</b>",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# LIÊN KẾT NGÂN HÀNG
# ============================================================

async def link_bank_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if await handle_anti_spam(update, context):
        return

    if not await require_private_user(update):
        return

    user = update.effective_user

    if is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(f"{E['STOP']} Hệ thống đang bảo trì, vui lòng quay lại sau!")
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            f"{E['BAN']} <b>Sai cú pháp liên kết!</b>\n"
            f"{E['ARROW_DOWN']} Ví dụ đúng:\n"
            f"<code>/lk 1068030300 VCB NGUYEN CA NGU</code>",
            parse_mode="HTML",
        )
        return

    bank_str = " ".join(context.args).strip()

    if len(bank_str) > 300:
        await update.message.reply_text("❌ Thông tin ngân hàng quá dài.")
        return

    db_query(
        """
        UPDATE users
        SET bank_info=%s
        WHERE user_id=%s
        """,
        (bank_str, user.id),
        commit=True,
    )

    await update.message.reply_text(
        f"{E['THUMB']} <b>LIÊN KẾT THÀNH CÔNG!</b>\n"
        f"{E['LOCK']} Thông tin lưu trữ: <code>{bank_str}</code>",
        parse_mode="HTML",
    )


# ============================================================
# RESET BANK - ADMIN
# ============================================================

async def reset_bank_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    if not message:
        return

    args = context.args or []

    if len(args) < 1:
        await message.reply_text(
            f"{E['BAN']} <b>Sai cú pháp!</b>\nCú pháp: <code>/resetbank USER_ID</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(args[0])
    except (ValueError, TypeError):
        await message.reply_text("❌ USER_ID không hợp lệ.")
        return

    user_exists = db_query(
        """
        SELECT user_id, bank_info
        FROM users
        WHERE user_id=%s
        """,
        (target_id,),
        fetchone=True,
    )

    if not user_exists:
        await message.reply_text(f"❌ Không tìm thấy user <code>{target_id}</code>.", parse_mode="HTML")
        return

    old_bank = user_exists[1]

    db_query(
        """
        UPDATE users
        SET bank_info=NULL
        WHERE user_id=%s
        """,
        (target_id,),
        commit=True,
    )

    user_withdraw_state.pop(target_id, None)

    await message.reply_text(
        f"{E['THUMB']} <b>ĐÃ RESET NGÂN HÀNG CỦA USER:</b> <code>{target_id}</code>\n"
        f"{E['LOCK']} Bank cũ: <code>{old_bank or 'Chưa liên kết'}</code>",
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"{E['ALERT1']} <b>Thông tin ngân hàng của bạn đã được Admin reset.</b>\n"
                f"{E['ARROW_DOWN']} Vui lòng dùng <code>/lk STK NGAN_HANG TEN_CHU_TAI_KHOAN</code> để cài đặt lại."
            ),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Không gửi được thông báo reset bank cho user %s: %s", target_id, exc)


# ============================================================
# RÚT TIỀN (SỐ TIỀN)
# ============================================================

async def handle_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user = update.effective_user
    message = update.effective_message

    if not user or not message or update.effective_chat.type != "private":
        return False

    if user_withdraw_state.get(user.id) != "WAITING_AMOUNT":
        return False

    raw_text = (message.text or "").strip()
    text = raw_text.replace(",", "").replace(".", "")

    if text.lower() in ["hủy", "huy", "cancel", "❌ hủy", "❌ hủy rút tiền"]:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            f"{E['BAN']} <b>Đã hủy thao tác rút tiền.</b>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
        return True

    if not text.isdigit():
        await message.reply_text(
            f"{E['BAN']} <b>Số tiền phải là số nguyên hợp lệ!</b>\nVui lòng nhập lại (hoặc nhập <b>hủy</b> để thoát):",
            parse_mode="HTML",
        )
        return True

    amount = int(text)

    if amount <= 0:
        await message.reply_text("❌ Số tiền không hợp lệ.")
        return True

    db_user = db_query(
        """
        SELECT balance, bank_info, is_banned, is_withdraw_banned
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

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
        await message.reply_text(
            f"{E['BAN']} Số tiền rút phải từ <b>{MIN_WITHDRAW:,}đ</b> đến <b>{MAX_WITHDRAW:,}đ</b>!",
            parse_mode="HTML"
        )
        return True

    try:
        def create_withdraw(cursor):
            cursor.execute(
                """
                UPDATE users
                SET balance = balance - %s
                WHERE user_id=%s
                AND balance >= %s
                AND is_banned=0
                AND is_withdraw_banned=0
                """,
                (amount, user.id, amount),
            )

            if cursor.rowcount != 1:
                return None

            cursor.execute(
                """
                INSERT INTO transactions
                    (user_id, type, amount, status, created_at, details)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user.id, "Rút Tiền", amount, "Chờ duyệt", get_now_str(), bank_info),
            )
            return cursor.fetchone()[0]

        tx_id = db_transaction(create_withdraw)

    except Exception as exc:
        logger.exception("Lỗi tạo lệnh rút: %s", exc)
        await message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại sau.")
        return True

    if not tx_id:
        await message.reply_text("❌ Số dư không đủ hoặc tài khoản đang bị hạn chế.")
        return True

    user_withdraw_state.pop(user.id, None)

    await message.reply_text(
        f"{E['CALENDAR']} <b>YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC GỬI!</b>\n"
        f"{E['GEAR']} Vui lòng chờ Admin kiểm tra và duyệt tiền.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

    admin_buttons = [
        [
            InlineKeyboardButton("✅ DUYỆT", callback_data=f"approve_{tx_id}"),
            InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"reject_{tx_id}"),
        ]
    ]

    username_str = f"@{user.username}" if user.username else str(user.id)
    admin_msg = (
        f"{E['ALERT1']} <b>LỆNH RÚT TIỀN MỚI (# {tx_id})</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['EYES']} <b>Khách hàng:</b> {username_str} (<code>{user.id}</code>)\n"
        f"{E['UP']} <b>Số tiền:</b> <code>{amount:,}đ</code>\n"
        f"{E['LOCK']} <b>Ngân hàng:</b> <code>{bank_info}</code>\n"
        f"{E['CALENDAR']} <b>Thời gian:</b> <code>{get_now_str()}</code>"
    )

    msg_refs = context.bot_data.setdefault(f"tx_msgs_{tx_id}", [])

    for admin_id in ADMIN_IDS:
        try:
            sent_msg = await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(admin_buttons),
                parse_mode="HTML",
            )
            msg_refs.append({
                "chat_id": admin_id,
                "message_id": sent_msg.message_id,
                "base_text": admin_msg
            })
        except Exception as exc:
            logger.exception("Không gửi được yêu cầu rút cho admin %s: %s", admin_id, exc)

    return True


# ============================================================
# DUYỆT / TỪ CHỐI LỆNH RÚT
# ============================================================

async def admin_withdraw_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    admin_user = query.from_user

    if admin_user.id not in ADMIN_IDS:
        try:
            await query.answer("❌ Quyền truy cập bị từ chối.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""

    try:
        action, tx_id_str = data.split("_", 1)
        tx_id = int(tx_id_str)
    except (ValueError, TypeError):
        return

    tx = db_query(
        """
        SELECT user_id, amount, status, details
        FROM transactions
        WHERE id=%s AND type='Rút Tiền'
        """,
        (tx_id,),
        fetchone=True,
    )

    if not tx:
        try:
            await query.edit_message_text("❌ Không tìm thấy giao dịch này.")
        except Exception:
            pass
        return

    user_id, amount, status, bank_info = tx
    admin_name_str = f"@{admin_user.username}" if admin_user.username else f"<code>{admin_user.id}</code>"

    if status != "Chờ duyệt":
        try:
            await query.answer("⚠️ Giao dịch này đã được xử lý trước đó!", show_alert=True)
            status_text = "✅ ĐÃ DUYỆT" if status == "Thành công" else "❌ ĐÃ TỪ CHỐI"
            await query.edit_message_text(
                f"{query.message.text}\n\n⚠️ <b>GIAO DỊCH ĐÃ ĐƯỢC XỬ LÝ TRƯỚC ĐÓ!</b> ({status_text})",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    if action == "approve":
        try:
            def approve(cursor):
                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Thành công'
                    WHERE id=%s AND status='Chờ duyệt'
                    """,
                    (tx_id,),
                )
                return cursor.rowcount == 1

            changed = db_transaction(approve)
        except Exception as exc:
            logger.exception("Lỗi duyệt: %s", exc)
            return

        if changed:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"{E['LOVE']} <b>RÚT TIỀN THÀNH CÔNG!</b>\nAdmin đã duyệt yêu cầu rút <b>{amount:,}đ</b> của bạn.",
                    parse_mode="HTML",
                )
            except Exception:
                pass

            refs = context.bot_data.pop(f"tx_msgs_{tx_id}", [])
            query_edited = False

            for ref in refs:
                update_text = f"{ref['base_text']}\n\n{E['THUMB']} <b>TRẠNG THÁI: ĐÃ DUYỆT RÚT TIỀN</b> (Bởi Admin {admin_name_str})"
                try:
                    await context.bot.edit_message_text(
                        chat_id=ref["chat_id"],
                        message_id=ref["message_id"],
                        text=update_text,
                        parse_mode="HTML"
                    )
                    if ref["chat_id"] == query.message.chat_id and ref["message_id"] == query.message.message_id:
                        query_edited = True
                except Exception:
                    pass

            if not query_edited:
                try:
                    await query.edit_message_text(
                        f"{query.message.text}\n\n{E['THUMB']} <b>TRẠNG THÁI: ĐÃ DUYỆT RÚT TIỀN</b> (Bởi Admin {admin_name_str})",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    elif action == "reject":
        try:
            def reject(cursor):
                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Từ chối'
                    WHERE id=%s AND status='Chờ duyệt'
                    """,
                    (tx_id,),
                )
                if cursor.rowcount != 1:
                    return False

                cursor.execute(
                    """
                    UPDATE users
                    SET balance = balance + %s
                    WHERE user_id=%s
                    """,
                    (amount, user_id),
                )
                return True

            changed = db_transaction(reject)
        except Exception as exc:
            logger.exception("Lỗi từ chối: %s", exc)
            return

        if changed:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"{E['BAN']} <b>YÊU CẦU RÚT TIỀN BỊ TỪ CHỐI</b>\n\nSố tiền <b>{amount:,}đ</b> đã được hoàn trả lại số dư.",
                    parse_mode="HTML",
                )
            except Exception:
                pass

            refs = context.bot_data.pop(f"tx_msgs_{tx_id}", [])
            query_edited = False

            for ref in refs:
                update_text = f"{ref['base_text']}\n\n{E['BAN']} <b>TRẠNG THÁI: ĐÃ TỪ CHỐI</b> (Bởi Admin {admin_name_str})"
                try:
                    await context.bot.edit_message_text(
                        chat_id=ref["chat_id"],
                        message_id=ref["message_id"],
                        text=update_text,
                        parse_mode="HTML"
                    )
                    if ref["chat_id"] == query.message.chat_id and ref["message_id"] == query.message.message_id:
                        query_edited = True
                except Exception:
                    pass

            if not query_edited:
                try:
                    await query.edit_message_text(
                        f"{query.message.text}\n\n{E['BAN']} <b>TRẠNG THÁI: ĐÃ TỪ CHỐI</b> (Bởi Admin {admin_name_str})",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass


# ============================================================
# ADMIN USER INFO
# ============================================================

async def admin_userinfo_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    if query.from_user.id not in ADMIN_IDS:
        try:
            await query.answer("❌ Quyền truy cập bị từ chối.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""
    try:
        target_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        return

    u = db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)

    if not u:
        try:
            await query.answer("❌ Không tìm thấy thông tin user này.", show_alert=True)
        except Exception:
            pass
        return

    invited_count = db_query(
        "SELECT COUNT(*) FROM users WHERE referrer_id=%s",
        (target_id,),
        fetchone=True,
    )[0]

    username = f"@{u[1]}" if u[1] else "Chưa đặt"
    bank = u[3] if u[3] else "Chưa liên kết"
    referrer = u[4] if u[4] is not None else "Không có"

    msg = (
        f"{E['EYES']} <b>THÔNG TIN CHI TIẾT USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['EYES']} ID: <code>{u[0]}</code>\n"
        f"{E['COOL']} Username: {username}\n"
        f"{E['UP']} Số dư: <code>{u[2]:,}đ</code>\n"
        f"{E['LOCK']} Ngân hàng: <code>{bank}</code>\n"
        f"{E['CLIP']} Khách giới thiệu: <code>{referrer}</code>\n"
        f"{E['COOL']} Tổng đã mời: <code>{invited_count}</code> người\n"
        f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
        f"{E['STOP']} Cấm rút: <b>{'CÓ' if u[6] else 'KHÔNG'}</b>\n"
        f"{E['CALENDAR']} Tham gia: <code>{u[7]}</code>"
    )

    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=msg,
        parse_mode="HTML",
    )


# ============================================================
# ADMIN COMMANDS
# ============================================================

def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)


async def admin_commands(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    if not message:
        return

    cmd = (message.text or "").split()[0].split("@")[0].lower()
    args = context.args or []

    try:
        if cmd == "/resetall":
            db_query("TRUNCATE TABLE users, transactions RESTART IDENTITY", commit=True)
            user_msg_tracker.clear()
            temp_bans.clear()
            user_withdraw_state.clear()

            db_query(
                """
                INSERT INTO users (user_id, username, balance, joined_at)
                VALUES (%s, %s, 0, %s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (message.from_user.id, message.from_user.username or "", get_now_str()),
                commit=True
            )

            await message.reply_text(
                f"{E['REFRESH']} <b>ĐÃ RESET TOÀN BỘ HỆ THỐNG!</b>\n"
                f"• Toàn bộ người dùng & lịch sử giao dịch đã được xóa hoàn toàn.\n"
                f"• Bạn và người dùng cũ giờ đây đã có thể ấn nút hoặc dùng lại link ref bình thường.",
                parse_mode="HTML"
            )

        elif cmd == "/tong":
            total_users = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
            users = db_query("SELECT user_id, username FROM users ORDER BY joined_at DESC LIMIT 50", fetchall=True)

            msg = (
                f"{E['CHART']} <b>THỐNG KÊ TỔNG NGUỜI DÙNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
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

            await message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
                parse_mode="HTML",
            )

        elif cmd == "/tongrut":
            res = db_query(
                """
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM transactions
                WHERE type='Rút Tiền' AND status='Thành công'
                """,
                fetchone=True,
            )
            total_amount, total_count = res[0], res[1]

            msg = (
                f"{E['DOWN']} <b>TỔNG TOÀN BỘ SỐ TIỀN ĐÃ RÚT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['UP']} <b>Tổng số tiền đã rút:</b> <code>{total_amount:,}đ</code>\n"
                f"{E['CHART']} <b>Tổng số lệnh thành công:</b> <code>{total_count:,}</code> lệnh"
            )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/rutid":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/rutid USER_ID</code>", parse_mode="HTML")
                return

            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return

            u = db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return

            stats = db_query(
                """
                SELECT 
                    COUNT(*),
                    COALESCE(SUM(CASE WHEN status='Thành công' THEN amount ELSE 0 END), 0),
                    COUNT(CASE WHEN status='Thành công' THEN 1 END),
                    COUNT(CASE WHEN status='Chờ duyệt' THEN 1 END),
                    COUNT(CASE WHEN status='Từ chối' THEN 1 END)
                FROM transactions
                WHERE user_id=%s AND type='Rút Tiền'
                """,
                (target_id,),
                fetchone=True
            )

            total_attempts, success_amount, success_count, pending_count, reject_count = stats

            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            bank = u[3] if u[3] else "Chưa liên kết"
            referrer = u[4] if u[4] is not None else "Không có"

            withdraw_txs = db_query(
                """
                SELECT id, amount, status, created_at
                FROM transactions
                WHERE user_id=%s AND type='Rút Tiền'
                ORDER BY id DESC LIMIT 10
                """,
                (target_id,),
                fetchall=True
            )

            msg = (
                f"{E['EYES']} <b>THÔNG TIN RÚT TIỀN CỦA USER <code>{target_id}</code></b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['COOL']} Username: {username}\n"
                f"{E['UP']} Số dư hiện tại: <code>{u[2]:,}đ</code>\n"
                f"{E['LOCK']} Ngân hàng: <code>{bank}</code>\n"
                f"{E['CLIP']} Người giới thiệu: <code>{referrer}</code>\n"
                f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[5] else 'KHÔNG'}</b> | Cấm rút: <b>{'CÓ' if u[6] else 'KHÔNG'}</b>\n"
                f"{E['CALENDAR']} Ngày tham gia: <code>{u[7]}</code>\n\n"
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

        elif cmd == "/tb":
            if not args:
                await message.reply_text(f"Cú pháp: <code>/tb Nội dung thông báo</code>", parse_mode="HTML")
                return

            content = " ".join(args).strip()
            users = db_query("SELECT user_id FROM users WHERE is_banned=0", fetchall=True)
            groups = db_query("SELECT chat_id FROM groups", fetchall=True)

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

            for (chat_id,) in groups:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"{E['SPEAKER']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)

            await message.reply_text(f"{E['THUMB']} Đã phát thông báo tới <b>{count}</b> người dùng/nhóm.", parse_mode="HTML")

        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/info USER_ID</code>", parse_mode="HTML")
                return

            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return

            u = db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)

            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return

            invited_count = db_query(
                "SELECT COUNT(*) FROM users WHERE referrer_id=%s",
                (target_id,),
                fetchone=True,
            )[0]

            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            bank = u[3] if u[3] else "Chưa liên kết"
            referrer = u[4] if u[4] is not None else "Không có"

            msg = (
                f"{E['EYES']} <b>THÔNG TIN CHI TIẾT USER</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['EYES']} ID: <code>{u[0]}</code>\n"
                f"{E['COOL']} Username: {username}\n"
                f"{E['UP']} Số dư: <code>{u[2]:,}đ</code>\n"
                f"{E['LOCK']} Ngân hàng: <code>{bank}</code>\n"
                f"{E['CLIP']} Khách giới thiệu: <code>{referrer}</code>\n"
                f"{E['COOL']} Tổng đã mời: <code>{invited_count}</code> người\n"
                f"{E['BAN']} Khóa TK: <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
                f"{E['STOP']} Cấm rút: <b>{'CÓ' if u[6] else 'KHÔNG'}</b>\n"
                f"{E['CALENDAR']} Tham gia: <code>{u[7]}</code>"
            )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/bb":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/bb USER_ID</code>", parse_mode="HTML")
                return

            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return

            invited_users = db_query(
                "SELECT user_id, username, joined_at FROM users WHERE referrer_id=%s ORDER BY joined_at DESC",
                (target_id,),
                fetchall=True,
            )

            total_invited = len(invited_users)

            msg = f"{E['COOL']} <b>DANH SÁCH BẠN BÈ MỜI CỦA USER <code>{target_id}</code></b> (Tổng: <code>{total_invited}</code> người):\n━━━━━━━━━━━━━━━━━━\n\n"

            if invited_users:
                for invited_id, username, joined_at in invited_users:
                    uname = f"@{username}" if username else "Chưa đặt username"
                    msg += f"• ID: <code>{invited_id}</code> | Name: {uname} | Ngày: <code>{joined_at}</code>\n"
            else:
                msg += "❌ Người dùng này chưa mời được ai.\n"

            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/ban":
            if len(args) < 1:
                await message.reply_text("Cú pháp: <code>/ban USER_ID</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['BAN']} Đã cấm vĩnh viễn user <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/moban":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/moban USER_ID</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['THUMB']} <b>Đã mở ban tài khoản cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

        elif cmd == "/cam":
            if len(args) < 1:
                await message.reply_text("Cú pháp: <code>/cam USER_ID</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['STOP']} Đã cấm rút tiền ID <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/mocam":
            if len(args) < 1:
                await message.reply_text(f"{E['CLIP']} <b>Cú pháp:</b> <code>/mocam USER_ID</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['THUMB']} <b>Đã mở cấm rút tiền cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")

        elif cmd in ("/nap", "/tru"):
            if len(args) < 2:
                await message.reply_text(f"Cú pháp: <code>{cmd} USER_ID SO_TIEN</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            amount = int(args[1])

            if amount <= 0:
                await message.reply_text("❌ Số tiền phải lớn hơn 0.")
                return

            exists = db_query("SELECT user_id FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not exists:
                await message.reply_text("❌ User chưa tồn tại.")
                return

            if cmd == "/nap":
                def add_money(cursor):
                    cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, target_id))
                    cursor.execute(
                        """
                        INSERT INTO transactions (user_id, type, amount, status, created_at, details)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (target_id, "Nạp Tiền (Admin)", amount, "Thành công", get_now_str(), "Cộng từ Admin"),
                    )
                    return True

                db_transaction(add_money)
                await message.reply_text(f"{E['THUMB']} Đã cộng <b>+{amount:,}đ</b> cho ID <code>{target_id}</code>.", parse_mode="HTML")

            else:
                def deduct(cursor):
                    cursor.execute(
                        "UPDATE users SET balance=balance-%s WHERE user_id=%s AND balance>=%s",
                        (amount, target_id, amount),
                    )
                    if cursor.rowcount != 1:
                        return False
                    cursor.execute(
                        """
                        INSERT INTO transactions (user_id, type, amount, status, created_at, details)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (target_id, "Trừ Tiền (Admin)", amount, "Thành công", get_now_str(), "Trừ từ Admin"),
                    )
                    return True

                ok = db_transaction(deduct)
                if not ok:
                    await message.reply_text("❌ Số dư user không đủ để trừ.")
                    return
                await message.reply_text(f"{E['BAN']} Đã trừ <b>-{amount:,}đ</b> của ID <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/rutls":
            txs = db_query(
                """
                SELECT id, user_id, amount, details, created_at
                FROM transactions
                WHERE type='Rút Tiền' AND status='Chờ duyệt'
                ORDER BY id ASC
                """,
                fetchall=True,
            )

            if not txs:
                await message.reply_text(f"{E['LOVE']} Không có yêu cầu rút tiền nào đang chờ duyệt!")
                return

            for tx_id, target_id, amount, details, created_at in txs:
                btns = [
                    [
                        InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tx_id}"),
                        InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tx_id}"),
                    ]
                ]
                msg_text = (
                    f"{E['EYES']} <b>Lệnh:</b> #{tx_id}\n"
                    f"{E['COOL']} <b>User:</b> <code>{target_id}</code>\n"
                    f"{E['UP']} <b>Số tiền:</b> <code>{amount:,}đ</code>\n"
                    f"{E['LOCK']} <b>Bank:</b> <code>{details or 'N/A'}</code>\n"
                    f"{E['CALENDAR']} <b>Thời gian:</b> <code>{created_at}</code>"
                )
                
                sent_msg = await message.reply_text(
                    msg_text,
                    reply_markup=InlineKeyboardMarkup(btns),
                    parse_mode="HTML",
                )

                refs = context.bot_data.setdefault(f"tx_msgs_{tx_id}", [])
                refs.append({
                    "chat_id": message.chat_id,
                    "message_id": sent_msg.message_id,
                    "base_text": msg_text
                })

        elif cmd == "/ruttc":
            txs = db_query(
                """
                SELECT id, user_id, amount, created_at
                FROM transactions
                WHERE type='Rút Tiền' AND status='Thành công'
                ORDER BY id DESC LIMIT 15
                """,
                fetchall=True,
            )

            if not txs:
                await message.reply_text("📜 Chưa có lệnh rút nào được duyệt.")
                return

            msg = f"{E['CHART']} <b>LỆNH RÚT ĐÃ DUYỆT GẦN ĐÂY:</b>\n\n"
            for tx_id, target_id, amount, created_at in txs:
                msg += f"{E['THUMB']} #{tx_id} | <code>{target_id}</code> | <code>{amount:,}đ</code> | <code>{created_at}</code>\n"

            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/lsgd":
            if len(args) < 1:
                await message.reply_text("Cú pháp: <code>/lsgd USER_ID</code>", parse_mode="HTML")
                return

            target_id = int(args[0])
            invited_users = db_query(
                "SELECT user_id, username FROM users WHERE referrer_id=%s ORDER BY joined_at DESC",
                (target_id,),
                fetchall=True,
            )

            msg = f"{E['COOL']} <b>DANH SÁCH MỜI CỦA USER <code>{target_id}</code>:</b>\n"
            if invited_users:
                for invited_id, username in invited_users:
                    uname = f"@{username}" if username else "N/A"
                    msg += f"• <code>{invited_id}</code> ({uname})\n"
            else:
                msg += "• Chưa mời được ai.\n"

            txs = db_query(
                """
                SELECT type, amount, status, created_at
                FROM transactions
                WHERE user_id=%s
                ORDER BY id DESC LIMIT 10
                """,
                (target_id,),
                fetchall=True,
            )

            msg += f"\n{E['CHART']} <b>LỊCH SỬ GIAO DỊCH:</b>\n"
            if txs:
                for tx_type, amount, status, created_at in txs:
                    msg += f"• {tx_type}: <code>{amount:,}đ</code> [{status}] - <code>{created_at}</code>\n"
            else:
                msg += "• Chưa có giao dịch.\n"

            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/baotri":
            curr = is_maintenance()
            new_val = "0" if curr else "1"
            db_query("UPDATE settings SET value=%s WHERE key='maintenance'", (new_val,), commit=True)
            status_str = "BẮT ĐẦU BẢO TRÌ 🔴" if new_val == "1" else "TẮT BẢO TRÌ 🟢"
            await message.reply_text(f"{E['GEAR']} Trạng thái hệ thống: <b>{status_str}</b>", parse_mode="HTML")

        elif cmd == "/batbt":
            db_query("UPDATE settings SET value='1' WHERE key='maintenance'", commit=True)
            await message.reply_text(f"{E['STOP']} <b>ĐÃ BẬT CHẾ ĐỘ BẢO TRÌ HỆ THỐNG!</b>", parse_mode="HTML")

        elif cmd == "/tatbt":
            db_query("UPDATE settings SET value='0' WHERE key='maintenance'", commit=True)
            await message.reply_text(f"{E['LIGHTNING']} <b>ĐÃ TẮT BẢO TRÌ HỆ THỐNG!</b> Bot đã mở lại bình thường.", parse_mode="HTML")

    except Exception as exc:
        logger.exception("Lỗi admin command %s: %s", cmd, exc)
        await message.reply_text("❌ Đã xảy ra lỗi khi xử lý lệnh.")


# ============================================================
# DISPATCHER
# ============================================================

async def text_message_dispatcher(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_message:
        return

    if await handle_anti_spam(update, context):
        return

    handled = await handle_withdraw_amount(update, context)
    if handled:
        return

    await menu_handler(update, context)


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error("Exception khi xử lý update: %s", context.error, exc_info=context.error)


# ============================================================
# MAIN
# ============================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN.")

    if not DATABASE_URL:
        raise RuntimeError("Chưa cấu hình DATABASE_URL.")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # COMMANDS USER
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("lk", link_bank_command))

    # HANDLER KIỂM TRA THÀNH VIÊN RỜI/THAM GIA LẠI NHÓM/KÊNH
    app.add_handler(ChatMemberHandler(chat_member_updated_handler, ChatMemberHandler.CHAT_MEMBER))

    # CALLBACKS USER & DUYỆT RÚT
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$"))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_withdraw_callback, pattern=r"^cancel_withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_withdraw_callback, pattern=r"^(approve|reject)_\d+$"))
    
    # CALLBACK XEM THÔNG TIN USER TỪ LỆNH /TONG
    app.add_handler(CallbackQueryHandler(admin_userinfo_callback, pattern=r"^userinfo_\d+$"))

    # COMMANDS ADMIN
    admin_cmds = [
        "resetall",
        "tong",
        "tongrut",
        "rutid",
        "tb",
        "info",
        "bb",
        "ban",
        "moban",
        "cam",
        "mocam",
        "rutls",
        "ruttc",
        "nap",
        "tru",
        "lsgd",
        "baotri",
        "batbt",
        "tatbt",
        "resetbank",
    ]

    for command in admin_cmds:
        app.add_handler(CommandHandler(command, admin_commands))

    # TEXT DISPATCHER
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))

    # ERROR HANDLER
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
