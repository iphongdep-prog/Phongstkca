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
    filters,
)


# ============================================================
# CẤU HÌNH
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

ADMIN_ID = 5633649201

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

# Đã cập nhật kênh mới @khuyenmaionline
REQUIRED_CHANNELS = [
    "@hocviennghiencobac",
    "@conmuamenmenl",
    "@khuyenmaionline",
    "@tbck2026",
    "@chungnaomoidu",
]

SUPPORT_GROUP = "https://t.me/conmuamenmenl"

MIN_WITHDRAW = 5000
MAX_WITHDRAW = 300000
REFERRAL_REWARD = 1000


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

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_unique_referral_reward
            ON transactions(user_id, type, details)
            WHERE type = 'Thưởng Mời Bạn'
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
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id,
            )

            if member.status in ("left", "kicked"):
                return False

        except Exception as exc:
            logger.warning(
                "Không kiểm tra được user %s trong %s: %s",
                user_id,
                channel,
                exc,
            )
            return False

    return True


# ============================================================
# ANTI SPAM
# ============================================================

async def handle_anti_spam(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user = update.effective_user
    message = update.effective_message

    if not user or user.id == ADMIN_ID or not message:
        return False

    now = datetime.now()
    ban_until = temp_bans.get(user.id)

    if ban_until:
        if now < ban_until:
            remaining_seconds = max(0, int((ban_until - now).total_seconds()))
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60

            await message.reply_text(
                f"🚫 *BẠN ĐÃ BỊ TẠM CẤM!*\n\n"
                f"⏳ Vui lòng chờ: *{minutes} phút {seconds} giây*\n"
                f"⚠️ Lý do: *Spam tin nhắn quá nhanh.*",
                parse_mode="Markdown"
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
            f"🚫 *CẢNH BÁO ANTI-SPAM*\n\n"
            f"❌ Bạn đã bị cấm *{TEMP_BAN_MINUTES} phút*!\n"
            f"⚠️ Lý do: Gửi quá *{SPAM_MAX_MESSAGES} tin nhắn* trong *{SPAM_WINDOW_SECONDS}s*.",
            parse_mode="Markdown"
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
            "🚫 *Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!*",
            parse_mode="Markdown"
        )
        return False

    if not row:
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

    # GROUP
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

    # BẢO TRÌ
    if is_maintenance() and user.id != ADMIN_ID:
        await update.message.reply_text(
            "🔴 *HỆ THỐNG ĐANG BẢO TRÌ*\n\n"
            "🛠️ Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!",
            parse_mode="Markdown"
        )
        return

    # USER
    db_user = db_query(
        """
        SELECT user_id, is_banned
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[1] == 1:
        await update.message.reply_text(
            "🚫 *Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!*",
            parse_mode="Markdown"
        )
        return

    # REFERRER
    referrer_id = None
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                ref_exists = db_query(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id=%s
                    """,
                    (ref_id,),
                    fetchone=True,
                )
                if ref_exists:
                    referrer_id = ref_id
        except (ValueError, TypeError):
            pass

    # TẠO USER
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
        db_query(
            """
            UPDATE users
            SET username=%s
            WHERE user_id=%s
            """,
            (user.username or "", user.id),
            commit=True,
        )

    # KIỂM TRA KÊNH (Đã cập nhật link Sankhuyenmaionline -> khuyenmaionline)
    is_joined = await check_channel_membership(context.bot, user.id)

    if not is_joined:
        buttons = [
            [
                InlineKeyboardButton(
                    "🎓 1. Học Viện Nghiện Cờ Bạc",
                    url="https://t.me/hocviennghiencobac",
                )
            ],
            [
                InlineKeyboardButton(
                    "🌧️ 2. Cơn Mưa Mèn Mén",
                    url="https://t.me/conmuamenmenl",
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍️ 3. Săn Khuyến Mãi Online",
                    url="https://t.me/khuyenmaionline",
                )
            ],
            [
                InlineKeyboardButton(
                    "📈 4. TBCK 2026",
                    url="https://t.me/tbck2026",
                )
            ],
            [
                InlineKeyboardButton(
                    "💎 5. Chừng Nào Mới Đủ",
                    url="https://t.me/chungnaomoidu",
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
            "👑 *CHÀO MỪNG BẠN ĐẾN VỚI HỆ THỐNG*\n\n"
            "📌 *Vui lòng tham gia đầy đủ 5 kênh đối tác bên dưới để tiếp tục:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    # CHÀO MỪNG
    await update.message.reply_text(
        "✨ *CHÀO MỪNG BẠN TRỞ LẠI HỆ THỐNG!*\n\n"
        "💎 Hãy chọn một tính năng trong menu bên dưới:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
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
        "🧩 *XÁC MINH CAPTCHA BẢO MẬT*\n\n"
        "Vui lòng giải phép tính bên dưới để hoàn tất đăng ký:\n"
        f"👉 *{a} + {b} = ?*"
    )

    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
    else:
        await context.bot.send_message(
            chat_id=update_or_query.from_user.id,
            text=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
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

    if is_maintenance() and user.id != ADMIN_ID:
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
            message_text="❌ *Bạn đã chọn sai kết quả! Vui lòng tính lại.*",
        )
        return

    # CAPTCHA ĐÚNG
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
                cursor.execute(
                    """
                    SELECT user_id
                    FROM users
                    WHERE user_id=%s
                    """,
                    (ref_id,),
                )
                if not cursor.fetchone():
                    return False

                details = f"Mời {user.id}"
                cursor.execute(
                    """
                    INSERT INTO transactions
                        (user_id, type, amount, status, created_at, details)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
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

                if cursor.rowcount != 1:
                    return False

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
                            f"🎉 *THƯỞNG MỜI BẠN BÈ!*\n\n"
                            f"💰 Bạn nhận được *+{REFERRAL_REWARD:,}đ*\n"
                            f"👤 Từ người dùng: *{username_str}*"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo referrer: %s", exc)

        except Exception as exc:
            logger.exception("Lỗi transaction thưởng giới thiệu: %s", exc)

    # XÓA CAPTCHA & CHÀO MỪNG
    try:
        await query.delete_message()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "🎉 *XÁC MINH THÀNH CÔNG!*\n\n"
            "👑 *Chào mừng bạn đã gia nhập hệ thống Bot VIP!*"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
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

    user_withdraw_state.pop(user.id, None)

    if is_maintenance() and user.id != ADMIN_ID:
        await message.reply_text(
            "🔴 *HỆ THỐNG ĐANG BẢO TRÌ*\n\n"
            "🛠️ Vui lòng quay lại sau!",
            parse_mode="Markdown"
        )
        return

    db_user = db_query(
        """
        SELECT
            user_id,
            balance,
            bank_info,
            is_banned,
            is_withdraw_banned
        FROM users
        WHERE user_id=%s
        """,
        (user.id,),
        fetchone=True,
    )

    if not db_user or db_user[3] == 1:
        await message.reply_text(
            "🚫 *Bạn không có quyền sử dụng bot này.*",
            parse_mode="Markdown"
        )
        return

    # KIỂM TRA KÊNH
    if user.id != ADMIN_ID:
        if not await check_channel_membership(context.bot, user.id):
            await message.reply_text(
                "⚠️ *Bạn chưa tham gia đủ các kênh bắt buộc!*\n"
                "👉 Vui lòng gõ /start để nhận danh sách kênh.",
                parse_mode="Markdown"
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
            "🏛️ *THÔNG TIN TÀI KHOẢN VIP*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 *ID:* `{user.id}`\n"
            f"💵 *Số dư:* `{balance:,}đ`\n"
            f"👥 *Đã mời:* `{invited_count}` người\n"
            f"💸 *Đã rút:* `{total_withdraw:,}đ`"
        )

        await message.reply_text(msg, parse_mode="Markdown")

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
            "🎁 *CHƯƠNG TRÌNH MỜI BẠN BÈ*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔗 *Link giới thiệu của bạn:*\n"
            f"`{ref_link}`\n\n"
            "📜 *Thể lệ nhận thưởng:*\n"
            f"• 🎯 Nhận ngay: *+{REFERRAL_REWARD:,}đ* / lượt mời thành công.\n"
            "• 📌 Bạn bè phải tham gia đủ kênh & hoàn thành CAPTCHA.\n"
            f"• 💳 Min rút: *{MIN_WITHDRAW:,}đ*\n"
            f"• 🔝 Max rút: *{MAX_WITHDRAW:,}đ*"
        )

        await message.reply_text(msg, parse_mode="Markdown")

    # NHÓM HỖ TRỢ
    elif text in ["Nhóm Hỗ Trợ", "💬 Nhóm Hỗ Trợ"]:
        await message.reply_text(
            f"💬 *NHÓM HỖ TRỢ CHÍNH THỨC:*\n👉 {SUPPORT_GROUP}",
            parse_mode="Markdown",
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
            await message.reply_text("📜 *Bạn chưa có giao dịch nào.*", parse_mode="Markdown")
            return

        msg = "📜 *LỊCH SỬ GIAO DỊCH GẦN ĐÂY*\n━━━━━━━━━━━━━━━━━━\n\n"

        for tx_type, amount, status, created_at in txs:
            icon = "✅" if status == "Thành công" else ("❌" if status == "Từ chối" else "⏳")
            msg += (
                f"{icon} *{tx_type}*: `{amount:,}đ`\n"
                f"📊 Trạng thái: *{status}*\n"
                f"🕒 Thời gian: `{created_at}`\n"
                "----------------------------------\n"
            )

        await message.reply_text(msg, parse_mode="Markdown")

    # RÚT TIỀN
    elif text in ["Rút Tiền", "💳 Rút Tiền"]:
        if db_user[4] == 1:
            await message.reply_text("🚫 *Tài khoản của bạn đã bị CẤM RÚT TIỀN!*", parse_mode="Markdown")
            return

        bank_info = db_user[2]

        if not bank_info:
            await message.reply_text(
                "⚠️ *BẠN CHƯA LIÊN KẾT NGÂN HÀNG*\n\n"
                "👉 Vui lòng gửi lệnh liên kết theo cú pháp:\n"
                "`/lk STK Tên_Ngân_Hàng Tên_Chủ_Thẻ`\n\n"
                "💡 *Ví dụ:* `/lk 1068030300 VCB NGUYEN CA NGU`",
                parse_mode="Markdown",
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
                "💳 *LỆNH RÚT TIỀN VIP*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🏦 *Tài khoản nhận:* `{bank_info}`\n"
                f"💰 *Số dư hiện tại:* `{db_user[1]:,}đ`\n"
                f"📌 *Hạn mức:* `{MIN_WITHDRAW:,}đ` - `{MAX_WITHDRAW:,}đ`\n\n"
                "👉 *Vui lòng nhập số tiền bạn muốn rút:*\n"
                "_(Nhập 'hủy' hoặc bấm nút bên dưới để thoát)_",
                reply_markup=cancel_btn,
                parse_mode="Markdown",
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
        text="❌ *Đã hủy thao tác rút tiền.*",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
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

    if is_maintenance() and user.id != ADMIN_ID:
        await message.reply_text("🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!")
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ *Sai cú pháp liên kết!*\n\n"
            "👉 Ví dụ đúng:\n"
            "`/lk 1068030300 VCB NGUYEN CA NGU`",
            parse_mode="Markdown",
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
        f"✅ *LIÊN KẾT THÀNH CÔNG!*\n\n"
        f"🏦 Thông tin lưu trữ: `{bank_str}`",
        parse_mode="Markdown",
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
            "❌ *Sai cú pháp!*\nCú pháp: `/resetbank USER_ID`",
            parse_mode="Markdown",
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
        await message.reply_text(f"❌ Không tìm thấy user `{target_id}`.", parse_mode="Markdown")
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
        f"✅ *ĐÃ RESET NGÂN HÀNG CỦA USER:* `{target_id}`\n\n"
        f"🏦 Bank cũ: `{old_bank or 'Chưa liên kết'}`",
        parse_mode="Markdown",
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "⚠️ *Thông tin ngân hàng của bạn đã được Admin reset.*\n\n"
                "Vui lòng dùng `/lk STK NGAN_HANG TEN_CHU_TAI_KHOAN` để cài đặt lại."
            ),
            parse_mode="Markdown",
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
            "❌ *Đã hủy thao tác rút tiền.*",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        return True

    if not text.isdigit():
        await message.reply_text(
            "❌ *Số tiền phải là số nguyên hợp lệ!*\nVui lòng nhập lại (hoặc nhập *hủy* để thoát):",
            parse_mode="Markdown",
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
            f"❌ Số tiền rút phải từ *{MIN_WITHDRAW:,}đ* đến *{MAX_WITHDRAW:,}đ*!",
            parse_mode="Markdown"
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
        "⏳ *YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC GỬI!*\n\n"
        "Vui lòng chờ Admin kiểm tra và duyệt tiền.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    # GỬI CẢNH BÁO CHO ADMIN
    admin_buttons = [
        [
            InlineKeyboardButton("✅ DUYỆT", callback_data=f"approve_{tx_id}"),
            InlineKeyboardButton("❌ TỪ CHỐI", callback_data=f"reject_{tx_id}"),
        ]
    ]

    username_str = f"@{user.username}" if user.username else str(user.id)
    admin_msg = (
        f"🚨 *LỆNH RÚT TIỀN MỚI (# {tx_id})*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Khách hàng:* {username_str} (`{user.id}`)\n"
        f"💵 *Số tiền:* `{amount:,}đ`\n"
        f"🏦 *Ngân hàng:* `{bank_info}`\n"
        f"🕒 *Thời gian:* `{get_now_str()}`"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(admin_buttons),
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("Không gửi được yêu cầu rút cho admin: %s", exc)

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

    if query.from_user.id != ADMIN_ID:
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

    if status != "Chờ duyệt":
        try:
            await query.edit_message_text(f"{query.message.text}\n\n⚠️ *GIAO DỊCH ĐÃ XỬ LÝ TRƯỚC ĐÓ!*")
        except Exception:
            pass
        return

    # DUYỆT
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
                await query.edit_message_text(f"{query.message.text}\n\n✅ *TRẠNG THÁI: ĐÃ DUYỆT RÚT TIỀN*")
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 *RÚT TIỀN THÀNH CÔNG!*\n\nAdmin đã duyệt yêu cầu rút *{amount:,}đ* của bạn.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    # TỪ CHỐI
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
                await query.edit_message_text(f"{query.message.text}\n\n❌ *TRẠNG THÁI: ĐÃ TỪ CHỐI*")
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ *YÊU CẦU RÚT TIỀN BỊ TỪ CHỐI*\n\nSố tiền *{amount:,}đ* đã được hoàn trả lại số dư.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass


# ============================================================
# ADMIN COMMANDS
# ============================================================

def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)


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
        # /TB - THÔNG BÁO
        if cmd == "/tb":
            if not args:
                await message.reply_text("Cú pháp: `/tb Nội dung thông báo`", parse_mode="Markdown")
                return

            content = " ".join(args).strip()
            users = db_query("SELECT user_id FROM users WHERE is_banned=0", fetchall=True)
            groups = db_query("SELECT chat_id FROM groups", fetchall=True)

            count = 0
            for (target_id,) in users:
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"📢 *THÔNG BÁO HỆ THỐNG*\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="Markdown",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)

            for (chat_id,) in groups:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"📢 *THÔNG BÁO HỆ THỐNG*\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="Markdown",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)

            await message.reply_text(f"✅ Đã phát thông báo tới *{count}* người dùng/nhóm.")

        # /INFO
        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text("Cú pháp: `/info USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            u = db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)

            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return

            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            bank = u[3] if u[3] else "Chưa liên kết"
            referrer = u[4] if u[4] is not None else "Không có"

            msg = (
                f"🔍 *THÔNG TIN CHI TIẾT USER*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 ID: `{u[0]}`\n"
                f"👤 Username: {username}\n"
                f"💰 Số dư: `{u[2]:,}đ`\n"
                f"🏦 Ngân hàng: `{bank}`\n"
                f"🔗 Khách giới thiệu: `{referrer}`\n"
                f"🚫 Khóa TK: *{'CÓ' if u[5] else 'KHÔNG'}*\n"
                f"🚫 Cấm rút: *{'CÓ' if u[6] else 'KHÔNG'}*\n"
                f"🕒 Tham gia: `{u[7]}`"
            )
            await message.reply_text(msg, parse_mode="Markdown")

        # /BAN
        elif cmd == "/ban":
            if len(args) < 1:
                await message.reply_text("Cú pháp: `/ban USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"✅ Đã cấm vĩnh viễn user `{target_id}`.", parse_mode="Markdown")

        # /MOBAN (MỞ BAN TÀI KHOẢN)
        elif cmd == "/moban":
            if len(args) < 1:
                await message.reply_text("📌 *Cú pháp:* `/moban USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"✅ *Đã mở ban tài khoản cho ID:* `{target_id}`", parse_mode="Markdown")

        # /CAM (CẤM RÚT TIỀN)
        elif cmd == "/cam":
            if len(args) < 1:
                await message.reply_text("Cú pháp: `/cam USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"✅ Đã cấm rút tiền ID `{target_id}`.", parse_mode="Markdown")

        # /MOCAM (MỞ CẤM RÚT TIỀN)
        elif cmd == "/mocam":
            if len(args) < 1:
                await message.reply_text("📌 *Cú pháp:* `/mocam USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            db_query("UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"✅ *Đã mở cấm rút tiền cho ID:* `{target_id}`", parse_mode="Markdown")

        # /NAP & /TRU
        elif cmd in ("/nap", "/tru"):
            if len(args) < 2:
                await message.reply_text(f"Cú pháp: `{cmd} USER_ID SO_TIEN`", parse_mode="Markdown")
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
                await message.reply_text(f"✅ Đã cộng *+{amount:,}đ* cho ID `{target_id}`.", parse_mode="Markdown")

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
                await message.reply_text(f"✅ Đã trừ *-{amount:,}đ* của ID `{target_id}`.", parse_mode="Markdown")

        # /RUTLS
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
                await message.reply_text("🎉 Không có yêu cầu rút tiền nào đang chờ duyệt!")
                return

            for tx_id, target_id, amount, details, created_at in txs:
                btns = [
                    [
                        InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tx_id}"),
                        InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tx_id}"),
                    ]
                ]
                await message.reply_text(
                    f"🆔 *Lệnh:* #{tx_id}\n"
                    f"👤 *User:* `{target_id}`\n"
                    f"💵 *Số tiền:* `{amount:,}đ`\n"
                    f"🏦 *Bank:* `{details or 'N/A'}`\n"
                    f"🕒 *Thời gian:* `{created_at}`",
                    reply_markup=InlineKeyboardMarkup(btns),
                    parse_mode="Markdown",
                )

        # /RUTTC
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

            msg = "📜 *LỆNH RÚT ĐÃ DUYỆT GẦN ĐÂY:*\n\n"
            for tx_id, target_id, amount, created_at in txs:
                msg += f"✅ #{tx_id} | `{target_id}` | `{amount:,}đ` | `{created_at}`\n"

            await message.reply_text(msg, parse_mode="Markdown")

        # /LSGD
        elif cmd == "/lsgd":
            if len(args) < 1:
                await message.reply_text("Cú pháp: `/lsgd USER_ID`", parse_mode="Markdown")
                return

            target_id = int(args[0])
            invited_users = db_query(
                "SELECT user_id, username FROM users WHERE referrer_id=%s ORDER BY joined_at DESC",
                (target_id,),
                fetchall=True,
            )

            msg = f"👥 *DANH SÁCH MỜI CỦA USER `{target_id}`:*\n"
            if invited_users:
                for invited_id, username in invited_users:
                    uname = f"@{username}" if username else "N/A"
                    msg += f"• `{invited_id}` ({uname})\n"
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

            msg += "\n📜 *LỊCH SỬ GIAO DỊCH:*\n"
            if txs:
                for tx_type, amount, status, created_at in txs:
                    msg += f"• {tx_type}: `{amount:,}đ` [{status}] - `{created_at}`\n"
            else:
                msg += "• Chưa có giao dịch.\n"

            await message.reply_text(msg, parse_mode="Markdown")

        # /BAOTRI - TOGGLE BẢO TRÌ
        elif cmd == "/baotri":
            curr = is_maintenance()
            new_val = "0" if curr else "1"
            db_query("UPDATE settings SET value=%s WHERE key='maintenance'", (new_val,), commit=True)
            status_str = "BẮT ĐẦU BẢO TRÌ 🔴" if new_val == "1" else "TẮT BẢO TRÌ 🟢"
            await message.reply_text(f"⚙️ Trạng thái hệ thống: *{status_str}*", parse_mode="Markdown")

        # /BATBT - BẬT BẢO TRÌ
        elif cmd == "/batbt":
            db_query("UPDATE settings SET value='1' WHERE key='maintenance'", commit=True)
            await message.reply_text("🔴 *ĐÃ BẬT CHẾ ĐỘ BẢO TRÌ HỆ THỐNG!*", parse_mode="Markdown")

        # /TATBT - TẮT BẢO TRÌ
        elif cmd == "/tatbt":
            db_query("UPDATE settings SET value='0' WHERE key='maintenance'", commit=True)
            await message.reply_text("🟢 *ĐÃ TẮT BẢO TRÌ HỆ THỐNG!* Bot đã mở lại bình thường.", parse_mode="Markdown")

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

    # CALLBACKS
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$"))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha_\d+$"))
    app.add_handler(CallbackQueryHandler(cancel_withdraw_callback, pattern=r"^cancel_withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_withdraw_callback, pattern=r"^(approve|reject)_\d+$"))

    # COMMANDS ADMIN
    admin_cmds = [
        "tb",
        "info",
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
