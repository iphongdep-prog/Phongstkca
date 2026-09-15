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

REQUIRED_CHANNELS = [
    "@hocviennghiencobac",
    "@conmuamenmenl",
    "@Sankhuyenmaionline",
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
        raise RuntimeError(
            "Chưa cấu hình DATABASE_URL trên Railway."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=tuple_row,
        connect_timeout=15,
    )


def init_db():
    conn = get_db()

    try:
        cursor = conn.cursor()

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # TRANSACTIONS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GROUPS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                chat_id BIGINT PRIMARY KEY
            )
            """
        )

        # ----------------------------------------------------
        # SETTINGS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # INDEX
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CHỐNG THƯỞNG REF TRÙNG
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_unique_referral_reward
            ON transactions(user_id, type, details)
            WHERE type = 'Thưởng Mời Bạn'
            """
        )

        conn.commit()

        logger.info(
            "Database PostgreSQL đã sẵn sàng."
        )

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
    return datetime.now(TIMEZONE).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# KEYBOARD
# ============================================================

def get_main_keyboard():
    keyboard = [
        [
            KeyboardButton("Tài Khoản"),
            KeyboardButton("Mời Bạn Bè"),
        ],
        [
            KeyboardButton("Rút Tiền"),
            KeyboardButton("Nhóm Hỗ Trợ"),
        ],
        [
            KeyboardButton("Lịch Sử"),
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

    return bool(
        res and res[0] == "1"
    )


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

            if member.status in (
                "left",
                "kicked",
            ):
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

    if (
        not user
        or user.id == ADMIN_ID
        or not message
    ):
        return False

    now = datetime.now()

    ban_until = temp_bans.get(user.id)

    if ban_until:

        if now < ban_until:

            remaining_seconds = max(
                0,
                int(
                    (ban_until - now).total_seconds()
                ),
            )

            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60

            await message.reply_text(
                f"🚫 Bạn đang bị cấm sử dụng bot "
                f"trong {minutes} phút {seconds} giây nữa!\n"
                f"Lý do: Spam tin nhắn."
            )

            return True

        temp_bans.pop(user.id, None)

    times = user_msg_tracker[user.id]

    times.append(now)

    cutoff = now - timedelta(
        seconds=SPAM_WINDOW_SECONDS
    )

    user_msg_tracker[user.id] = [
        t for t in times
        if t >= cutoff
    ]

    if len(user_msg_tracker[user.id]) >= SPAM_MAX_MESSAGES:

        temp_bans[user.id] = (
            now
            + timedelta(minutes=TEMP_BAN_MINUTES)
        )

        user_msg_tracker[user.id].clear()

        await message.reply_text(
            f"🚫 Bạn đã bị cấm sử dụng bot "
            f"trong {TEMP_BAN_MINUTES} phút!\n"
            f"Lý do: Spam {SPAM_MAX_MESSAGES} tin nhắn "
            f"trong {SPAM_WINDOW_SECONDS} giây."
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
            (
                current_username,
                user.id,
            ),
            commit=True,
        )

    return row


async def require_private_user(update: Update):

    if (
        not update.effective_chat
        or update.effective_chat.type != "private"
    ):
        return False

    user = update.effective_user

    if not user:
        return False

    row = await ensure_user_exists(update)

    if row and row[3] == 1:

        await update.effective_message.reply_text(
            "🚫 Tài khoản của bạn đã bị cấm vĩnh viễn."
        )

        return False

    if not row:

        db_query(
            """
            INSERT INTO users
                (
                    user_id,
                    username,
                    balance,
                    joined_at
                )
            VALUES
                (
                    %s,
                    %s,
                    0,
                    %s
                )
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                user.id,
                user.username or "",
                get_now_str(),
            ),
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

    if await handle_anti_spam(
        update,
        context,
    ):
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    # --------------------------------------------------------
    # GROUP
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BẢO TRÌ
    # --------------------------------------------------------

    if (
        is_maintenance()
        and user.id != ADMIN_ID
    ):

        await update.message.reply_text(
            "🔴 Hệ thống đang bảo trì, "
            "vui lòng quay lại sau!"
        )

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

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
            "🚫 Tài khoản của bạn đã bị cấm vĩnh viễn."
        )

        return

    # --------------------------------------------------------
    # REFERRER
    # --------------------------------------------------------

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

        except (
            ValueError,
            TypeError,
        ):
            pass

    # --------------------------------------------------------
    # TẠO USER
    # --------------------------------------------------------

    if not db_user:

        db_query(
            """
            INSERT INTO users
                (
                    user_id,
                    username,
                    balance,
                    referrer_id,
                    joined_at
                )
            VALUES
                (
                    %s,
                    %s,
                    0,
                    %s,
                    %s
                )
            ON CONFLICT (user_id) DO NOTHING
            """,
            (
                user.id,
                user.username or "",
                referrer_id,
                get_now_str(),
            ),
            commit=True,
        )

    else:

        db_query(
            """
            UPDATE users
            SET username=%s
            WHERE user_id=%s
            """,
            (
                user.username or "",
                user.id,
            ),
            commit=True,
        )

    # --------------------------------------------------------
    # KIỂM TRA KÊNH
    # --------------------------------------------------------

    is_joined = await check_channel_membership(
        context.bot,
        user.id,
    )

    if not is_joined:

        buttons = [

            [
                InlineKeyboardButton(
                    "1. Học Viện Nghiện Cờ Bạc",
                    url="https://t.me/hocviennghiencobac",
                )
            ],

            [
                InlineKeyboardButton(
                    "2. Cơn Mưa Mèn Mén",
                    url="https://t.me/conmuamenmenl",
                )
            ],

            [
                InlineKeyboardButton(
                    "3. Săn Khuyến Mãi Online",
                    url="https://t.me/Sankhuyenmaionline",
                )
            ],

            [
                InlineKeyboardButton(
                    "4. TBCK 2026",
                    url="https://t.me/tbck2026",
                )
            ],

            [
                InlineKeyboardButton(
                    "5. Chừng Nào Mới Đủ",
                    url="https://t.me/chungnaomoidu",
                )
            ],

            [
                InlineKeyboardButton(
                    "🟢 Xác Nhận Đã Tham Gia",
                    callback_data="verify_join",
                )
            ],
        ]

        await update.message.reply_text(
            "⚠️ *Vui lòng tham gia đầy đủ các kênh "
            "bên dưới để sử dụng bot:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # CHÀO MỪNG
    # --------------------------------------------------------

    await update.message.reply_text(
        "🎉 CHÀO MỪNG BẠN ĐẾN VỚI BOT!",
        reply_markup=get_main_keyboard(),
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
                str(opt),
                callback_data=f"captcha_{opt}",
            )
        )

        if len(row) == 2:

            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    caption = (
        f"{message_text}\n\n"
        if message_text
        else ""
    )

    caption += (
        "🧩 *XÁC MINH CAPTCHA CON NGƯỜI*\n\n"
        "Vui lòng giải phép tính sau để tiếp tục:\n"
        f"👉 *{a} + {b} = ?*"
    )

    if hasattr(
        update_or_query,
        "edit_message_text",
    ):

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

    if (
        is_maintenance()
        and user.id != ADMIN_ID
    ):

        try:
            await query.answer(
                "Hệ thống đang bảo trì.",
                show_alert=True,
            )
        except Exception:
            pass

        return

    is_joined = await check_channel_membership(
        context.bot,
        user.id,
    )

    if not is_joined:

        try:
            await query.answer(
                "❌ Bạn chưa tham gia đủ các kênh bắt buộc!",
                show_alert=True,
            )
        except Exception:
            pass

        return

    await send_captcha_challenge(
        query,
        context,
    )


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

        selected_ans = int(
            data.split("_")[1]
        )

    except (
        IndexError,
        ValueError,
    ):
        return

    correct_ans = context.user_data.get(
        "captcha_ans"
    )

    if selected_ans != correct_ans:

        try:
            await query.answer(
                "❌ Phép tính sai! Vui lòng chọn lại.",
                show_alert=True,
            )
        except Exception:
            pass

        await send_captcha_challenge(
            query,
            context,
            message_text="❌ *Bạn đã chọn sai kết quả!*",
        )

        return

    # --------------------------------------------------------
    # CAPTCHA ĐÚNG
    # --------------------------------------------------------

    context.user_data.pop(
        "captcha_ans",
        None,
    )

    try:
        await query.answer(
            "✅ Xác minh CAPTCHA thành công!"
        )
    except Exception:
        pass

    # --------------------------------------------------------
    # THƯỞNG REFERRER
    # --------------------------------------------------------

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
                        (
                            user_id,
                            type,
                            amount,
                            status,
                            created_at,
                            details
                        )
                    VALUES
                        (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
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
                    (
                        REFERRAL_REWARD,
                        ref_id,
                    ),
                )

                return True

            rewarded = db_transaction(
                reward_referrer
            )

            if rewarded:

                username_str = (
                    f"@{user.username}"
                    if user.username
                    else str(user.id)
                )

                try:

                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"🎉 Bạn nhận được "
                            f"+{REFERRAL_REWARD:,}đ "
                            f"từ việc giới thiệu người dùng "
                            f"{username_str} thành công!"
                        ),
                    )

                except Exception as exc:

                    logger.warning(
                        "Không gửi được thông báo referrer: %s",
                        exc,
                    )

        except Exception as exc:

            logger.exception(
                "Lỗi transaction thưởng giới thiệu: %s",
                exc,
            )

    # --------------------------------------------------------
    # XÓA CAPTCHA
    # --------------------------------------------------------

    try:
        await query.delete_message()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "✅ *Xác minh CAPTCHA thành công!*\n"
            "🎉 CHÀO MỪNG BẠN ĐẾN VỚI BOT!"
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

    # Bấm menu thì hủy trạng thái rút
    user_withdraw_state.pop(
        user.id,
        None,
    )

    if (
        is_maintenance()
        and user.id != ADMIN_ID
    ):

        await message.reply_text(
            "🔴 Hệ thống đang bảo trì, "
            "vui lòng quay lại sau!"
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
            "🚫 Bạn không có quyền sử dụng bot."
        )

        return

    # --------------------------------------------------------
    # KIỂM TRA KÊNH
    # --------------------------------------------------------

    if user.id != ADMIN_ID:

        if not await check_channel_membership(
            context.bot,
            user.id,
        ):

            await message.reply_text(
                "⚠️ Bạn chưa tham gia đủ các kênh bắt buộc.\n"
                "Gõ /start để nhận lại danh sách nhóm."
            )

            return

    text = (
        message.text or ""
    ).strip()

    # ========================================================
    # TÀI KHOẢN
    # ========================================================

    if text == "Tài Khoản":

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
            "👤 *THÔNG TIN TÀI KHOẢN*\n\n"
            f"🆔 *ID:* `{user.id}`\n"
            f"💰 *Số dư hiện có:* {balance:,}đ\n"
            f"👥 *Tổng số bạn bè đã mời:* "
            f"{invited_count} người\n"
            f"💸 *Tổng rút đã duyệt:* "
            f"{total_withdraw:,}đ"
        )

        await message.reply_text(
            msg,
            parse_mode="Markdown",
        )

    # ========================================================
    # MỜI BẠN
    # ========================================================

    elif text == "Mời Bạn Bè":

        try:

            bot_info = await context.bot.get_me()
            bot_username = bot_info.username

        except Exception as exc:

            logger.exception(
                "Không lấy được username bot: %s",
                exc,
            )

            await message.reply_text(
                "❌ Không lấy được thông tin bot. "
                "Vui lòng thử lại."
            )

            return

        if not bot_username:

            await message.reply_text(
                "❌ Bot chưa có username, "
                "không thể tạo link mời."
            )

            return

        ref_link = (
            f"https://t.me/"
            f"{bot_username}"
            f"?start={user.id}"
        )

        msg = (
            "🔗 *LINK MỜI BẠN BÈ CỦA BẠN:*\n"
            f"`{ref_link}`\n\n"
            "🎁 *Thể lệ:*\n"
            f"- 🎯 Mời 1 bạn bè thành công nhận: "
            f"*+{REFERRAL_REWARD:,}đ*\n"
            "- 📌 Người được mời phải tham gia đủ "
            "nhóm và hoàn thành CAPTCHA thì bạn "
            "mới nhận được tiền.\n"
            f"- 💳 Min Rút tiền: *{MIN_WITHDRAW:,}đ*\n"
            f"- 🔝 Rút Tối đa: *{MAX_WITHDRAW:,}đ*"
        )

        await message.reply_text(
            msg,
            parse_mode="Markdown",
        )

    # ========================================================
    # NHÓM HỖ TRỢ
    # ========================================================

    elif text == "Nhóm Hỗ Trợ":

        await message.reply_text(
            f"💬 *Nhóm Hỗ Trợ:* {SUPPORT_GROUP}",
            parse_mode="Markdown",
        )

    # ========================================================
    # LỊCH SỬ
    # ========================================================

    elif text == "Lịch Sử":

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

            await message.reply_text(
                "📜 Bạn chưa có giao dịch nào."
            )

            return

        msg = (
            "📜 *LỊCH SỬ GIAO DỊCH GẦN ĐÂY* "
            "(Giờ VN):\n\n"
        )

        for (
            tx_type,
            amount,
            status,
            created_at,
        ) in txs:

            icon = (
                "✅"
                if status == "Thành công"
                else (
                    "❌"
                    if status == "Từ chối"
                    else "⏳"
                )
            )

            msg += (
                f"{icon} *{tx_type}*: "
                f"{amount:,}đ | {status}\n"
                f"🕒 `{created_at}`\n"
                "---------------------\n"
            )

        await message.reply_text(
            msg,
            parse_mode="Markdown",
        )

    # ========================================================
    # RÚT TIỀN
    # ========================================================

    elif text == "Rút Tiền":

        if db_user[4] == 1:

            await message.reply_text(
                "🚫 Bạn đã bị cấm tính năng rút tiền!"
            )

            return

        bank_info = db_user[2]

        if not bank_info:

            await message.reply_text(
                "⚠️ Bạn chưa liên kết tài khoản ngân hàng.\n\n"
                "Vui lòng gửi câu lệnh theo cú pháp:\n"
                "`/lk STK Tên_Ngân_Hàng Tên_Chủ_Thẻ`\n\n"
                "Ví dụ:\n"
                "`/lk 1068030300 VCB NGUYEN CA NGU`",
                parse_mode="Markdown",
            )

        else:

            user_withdraw_state[user.id] = (
                "WAITING_AMOUNT"
            )

            cancel_btn = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "❌ Hủy Rút Tiền",
                        callback_data="cancel_withdraw",
                    )
                ]
            ])

            await message.reply_text(
                f"💳 *Tài khoản thụ hưởng:* "
                f"`{bank_info}`\n"
                f"💰 *Số dư:* {db_user[1]:,}đ\n"
                f"📌 *Min rút:* {MIN_WITHDRAW:,}đ "
                f"- *Max rút:* {MAX_WITHDRAW:,}đ\n\n"
                "👉 *Vui lòng nhập số tiền "
                "bạn muốn rút:*\n"
                "*(Hoặc bấm nút Hủy Rút Tiền "
                "bên dưới / gõ 'hủy' để thoát)*",
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

    user_withdraw_state.pop(
        user.id,
        None,
    )

    try:

        await query.answer(
            "Đã hủy thao tác rút tiền!"
        )

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

    if await handle_anti_spam(
        update,
        context,
    ):
        return

    if not await require_private_user(update):
        return

    user = update.effective_user

    if (
        is_maintenance()
        and user.id != ADMIN_ID
    ):

        await update.message.reply_text(
            "🔴 Hệ thống đang bảo trì, "
            "vui lòng quay lại sau!"
        )

        return

    if (
        not context.args
        or len(context.args) < 3
    ):

        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Ví dụ đúng:\n"
            "`/lk 1068030300 VCB NGUYEN CA NGU`",
            parse_mode="Markdown",
        )

        return

    bank_str = " ".join(
        context.args
    ).strip()

    if len(bank_str) > 300:

        await update.message.reply_text(
            "❌ Thông tin ngân hàng quá dài."
        )

        return

    db_query(
        """
        UPDATE users
        SET bank_info=%s
        WHERE user_id=%s
        """,
        (
            bank_str,
            user.id,
        ),
        commit=True,
    )

    await update.message.reply_text(
        f"✅ *Liên kết thành công!*\n"
        f"Thông tin của bạn: `{bank_str}`",
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
            "❌ Sai cú pháp.\n\n"
            "Dùng:\n"
            "`/resetbank USER_ID`\n\n"
            "Ví dụ:\n"
            "`/resetbank 123456789`",
            parse_mode="Markdown",
        )

        return

    try:
        target_id = int(args[0])

    except (
        ValueError,
        TypeError,
    ):

        await message.reply_text(
            "❌ USER_ID không hợp lệ."
        )

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

        await message.reply_text(
            f"❌ Không tìm thấy user `{target_id}` "
            "trong database.",
            parse_mode="Markdown",
        )

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

    # Nếu người đó đang trong trạng thái nhập tiền rút
    user_withdraw_state.pop(
        target_id,
        None,
    )

    await message.reply_text(
        f"✅ Đã reset thông tin ngân hàng của "
        f"ID `{target_id}`.\n\n"
        f"🏦 Bank cũ: "
        f"`{old_bank or 'Chưa liên kết'}`\n\n"
        "Người dùng cần dùng `/lk` để liên kết "
        "ngân hàng mới.",
        parse_mode="Markdown",
    )

    # Thông báo cho user
    try:

        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "⚠️ *Thông tin ngân hàng của bạn "
                "đã được Admin reset.*\n\n"
                "Vui lòng liên kết lại ngân hàng bằng lệnh:\n"
                "`/lk STK NGAN_HANG TEN_CHU_TAI_KHOAN`"
            ),
            parse_mode="Markdown",
        )

    except Exception as exc:

        logger.warning(
            "Không gửi được thông báo reset bank "
            "cho user %s: %s",
            target_id,
            exc,
        )


# ============================================================
# RÚT TIỀN
# ============================================================

async def handle_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return False

    if update.effective_chat.type != "private":
        return False

    if (
        user_withdraw_state.get(user.id)
        != "WAITING_AMOUNT"
    ):
        return False

    raw_text = (
        message.text or ""
    ).strip()

    text = (
        raw_text
        .replace(",", "")
        .replace(".", "")
    )

    # --------------------------------------------------------
    # HỦY
    # --------------------------------------------------------

    if text.lower() in [
        "hủy",
        "huy",
        "cancel",
        "❌ hủy",
        "❌ hủy rút tiền",
    ]:

        user_withdraw_state.pop(
            user.id,
            None,
        )

        await message.reply_text(
            "❌ *Đã hủy thao tác rút tiền.*",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )

        return True

    # --------------------------------------------------------
    # KIỂM TRA SỐ
    # --------------------------------------------------------

    if not text.isdigit():

        await message.reply_text(
            "❌ Số tiền phải là chữ số hợp lệ. "
            "Vui lòng nhập lại "
            "(hoặc gõ *hủy* để thoát):",
            parse_mode="Markdown",
        )

        return True

    amount = int(text)

    if amount <= 0:

        await message.reply_text(
            "❌ Số tiền không hợp lệ."
        )

        return True

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    db_user = db_query(
        """
        SELECT
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

    if not db_user:

        user_withdraw_state.pop(
            user.id,
            None,
        )

        await message.reply_text(
            "❌ Không tìm thấy tài khoản. "
            "Vui lòng /start lại."
        )

        return True

    (
        balance,
        bank_info,
        is_banned,
        is_withdraw_banned,
    ) = db_user

    if is_banned:

        user_withdraw_state.pop(
            user.id,
            None,
        )

        await message.reply_text(
            "🚫 Tài khoản của bạn đã bị cấm."
        )

        return True

    if is_withdraw_banned:

        user_withdraw_state.pop(
            user.id,
            None,
        )

        await message.reply_text(
            "🚫 Bạn đã bị cấm tính năng rút tiền."
        )

        return True

    if not bank_info:

        user_withdraw_state.pop(
            user.id,
            None,
        )

        await message.reply_text(
            "⚠️ Bạn chưa liên kết ngân hàng. "
            "Vui lòng dùng /lk trước."
        )

        return True

    # --------------------------------------------------------
    # GIỚI HẠN
    # --------------------------------------------------------

    if (
        amount < MIN_WITHDRAW
        or amount > MAX_WITHDRAW
    ):

        await message.reply_text(
            f"❌ Số tiền rút phải từ "
            f"{MIN_WITHDRAW:,}đ đến "
            f"{MAX_WITHDRAW:,}đ!"
        )

        return True

    # --------------------------------------------------------
    # TẠO LỆNH RÚT
    # --------------------------------------------------------

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
                (
                    amount,
                    user.id,
                    amount,
                ),
            )

            if cursor.rowcount != 1:
                return None

            cursor.execute(
                """
                INSERT INTO transactions
                    (
                        user_id,
                        type,
                        amount,
                        status,
                        created_at,
                        details
                    )
                VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                RETURNING id
                """,
                (
                    user.id,
                    "Rút Tiền",
                    amount,
                    "Chờ duyệt",
                    get_now_str(),
                    bank_info,
                ),
            )

            return cursor.fetchone()[0]

        tx_id = db_transaction(
            create_withdraw
        )

    except Exception as exc:

        logger.exception(
            "Lỗi tạo lệnh rút: %s",
            exc,
        )

        await message.reply_text(
            "❌ Có lỗi cơ sở dữ liệu khi tạo "
            "lệnh rút. Vui lòng thử lại."
        )

        return True

    if not tx_id:

        await message.reply_text(
            "❌ Số dư không đủ hoặc tài khoản "
            "không được phép rút."
        )

        return True

    user_withdraw_state.pop(
        user.id,
        None,
    )

    await message.reply_text(
        "⏳ Đã gửi yêu cầu rút tiền thành công! "
        "Vui lòng chờ Admin duyệt.",
        reply_markup=get_main_keyboard(),
    )

    # --------------------------------------------------------
    # GỬI ADMIN
    # --------------------------------------------------------

    admin_buttons = [
        [
            InlineKeyboardButton(
                "✅ Duyệt",
                callback_data=f"approve_{tx_id}",
            ),
            InlineKeyboardButton(
                "❌ Từ chối",
                callback_data=f"reject_{tx_id}",
            ),
        ]
    ]

    username_str = (
        f"@{user.username}"
        if user.username
        else str(user.id)
    )

    admin_msg = (
        f"🚨 *YÊU CẦU RÚT TIỀN MỚI (#{tx_id})*\n\n"
        f"👤 *Người rút:* {username_str} "
        f"(`{user.id}`)\n"
        f"💵 *Số tiền:* {amount:,}đ\n"
        f"🏦 *Thông tin:* `{bank_info}`\n"
        f"🕒 *Thời gian:* `{get_now_str()}`"
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(
                admin_buttons
            ),
            parse_mode="Markdown",
        )

    except Exception as exc:

        logger.exception(
            "Không gửi được yêu cầu rút #%s "
            "cho admin: %s",
            tx_id,
            exc,
        )

        await message.reply_text(
            "⚠️ Lệnh rút đã được ghi nhận "
            "nhưng bot chưa gửi được thông báo "
            "cho Admin."
        )

    return True


# ============================================================
# DUYỆT / TỪ CHỐI
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
            await query.answer(
                "❌ Bạn không có quyền.",
                show_alert=True,
            )
        except Exception:
            pass

        return

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""

    try:

        action, tx_id_str = data.split(
            "_",
            1,
        )

        tx_id = int(tx_id_str)

    except (
        ValueError,
        TypeError,
    ):

        try:
            await query.answer(
                "❌ Mã giao dịch không hợp lệ.",
                show_alert=True,
            )
        except Exception:
            pass

        return

    tx = db_query(
        """
        SELECT
            user_id,
            amount,
            status,
            details
        FROM transactions
        WHERE id=%s
        AND type='Rút Tiền'
        """,
        (tx_id,),
        fetchone=True,
    )

    if not tx:

        try:
            await query.edit_message_text(
                "❌ Không tìm thấy giao dịch này."
            )
        except Exception:
            pass

        return

    (
        user_id,
        amount,
        status,
        bank_info,
    ) = tx

    if status != "Chờ duyệt":

        try:
            await query.edit_message_text(
                f"{query.message.text or ''}\n\n"
                "⚠️ Giao dịch này đã được "
                "xử lý trước đó!"
            )
        except Exception:
            pass

        return

    # ========================================================
    # DUYỆT
    # ========================================================

    if action == "approve":

        try:

            def approve(cursor):

                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Thành công'
                    WHERE id=%s
                    AND status='Chờ duyệt'
                    """,
                    (tx_id,),
                )

                return cursor.rowcount == 1

            changed = db_transaction(
                approve
            )

        except Exception as exc:

            logger.exception(
                "Lỗi duyệt giao dịch #%s: %s",
                tx_id,
                exc,
            )

            try:
                await query.answer(
                    "❌ Lỗi database.",
                    show_alert=True,
                )
            except Exception:
                pass

            return

        if not changed:

            try:
                await query.answer(
                    "⚠️ Giao dịch đã được xử lý.",
                    show_alert=True,
                )
            except Exception:
                pass

            return

        try:

            await query.edit_message_text(
                f"{query.message.text or ''}\n\n"
                "✅ *TRẠNG THÁI: ĐÃ DUYỆT RÚT*",
                parse_mode="Markdown",
            )

        except Exception:
            pass

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 Admin đã *duyệt* "
                    f"yêu cầu rút {amount:,}đ của bạn!"
                ),
                parse_mode="Markdown",
            )

        except Exception as exc:

            logger.warning(
                "Không báo được user %s khi duyệt: %s",
                user_id,
                exc,
            )

    # ========================================================
    # TỪ CHỐI
    # ========================================================

    elif action == "reject":

        try:

            def reject(cursor):

                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Từ chối'
                    WHERE id=%s
                    AND status='Chờ duyệt'
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
                    (
                        amount,
                        user_id,
                    ),
                )

                return True

            changed = db_transaction(
                reject
            )

        except Exception as exc:

            logger.exception(
                "Lỗi từ chối giao dịch #%s: %s",
                tx_id,
                exc,
            )

            try:
                await query.answer(
                    "❌ Lỗi database.",
                    show_alert=True,
                )
            except Exception:
                pass

            return

        if not changed:

            try:
                await query.answer(
                    "⚠️ Giao dịch đã được xử lý.",
                    show_alert=True,
                )
            except Exception:
                pass

            return

        try:

            await query.edit_message_text(
                f"{query.message.text or ''}\n\n"
                "❌ *TRẠNG THÁI: ĐÃ TỪ CHỐI*",
                parse_mode="Markdown",
            )

        except Exception:
            pass

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ Admin đã *từ chối* "
                    f"yêu cầu rút {amount:,}đ của bạn.\n"
                    "Số tiền đã được hoàn lại số dư!"
                ),
                parse_mode="Markdown",
            )

        except Exception as exc:

            logger.warning(
                "Không báo được user %s khi từ chối: %s",
                user_id,
                exc,
            )


# ============================================================
# ADMIN
# ============================================================

def is_admin(update: Update):

    return bool(
        update.effective_user
        and update.effective_user.id == ADMIN_ID
    )


async def admin_commands(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_admin(update):
        return

    message = update.effective_message

    if not message:
        return

    cmd = (
        (message.text or "")
        .split()[0]
        .split("@")[0]
        .lower()
    )

    args = context.args or []

    try:

        # ====================================================
        # /TB
        # ====================================================

        if cmd == "/tb":

            if not args:

                await message.reply_text(
                    "Cú pháp:\n"
                    "`/tb Nội dung thông báo`",
                    parse_mode="Markdown",
                )

                return

            content = " ".join(args).strip()

            if not content:

                await message.reply_text(
                    "❌ Nội dung thông báo đang trống."
                )

                return

            users = db_query(
                """
                SELECT user_id
                FROM users
                WHERE is_banned=0
                """,
                fetchall=True,
            )

            groups = db_query(
                """
                SELECT chat_id
                FROM groups
                """,
                fetchall=True,
            )

            count = 0

            for (target_id,) in users:

                try:

                    await context.bot.send_message(
                        chat_id=target_id,
                        text=(
                            "📢 *THÔNG BÁO:*\n\n"
                            f"{content}"
                        ),
                        parse_mode="Markdown",
                    )

                    count += 1

                except Exception as exc:

                    logger.warning(
                        "Broadcast user %s lỗi: %s",
                        target_id,
                        exc,
                    )

                await asyncio.sleep(0.05)

            for (chat_id,) in groups:

                try:

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "📢 *THÔNG BÁO:*\n\n"
                            f"{content}"
                        ),
                        parse_mode="Markdown",
                    )

                    count += 1

                except Exception as exc:

                    logger.warning(
                        "Broadcast group %s lỗi: %s",
                        chat_id,
                        exc,
                    )

                await asyncio.sleep(0.05)

            await message.reply_text(
                f"✅ Đã gửi thông báo tới "
                f"{count} người dùng / nhóm."
            )

        # ====================================================
        # /INFO
        # ====================================================

        elif cmd == "/info":

            if len(args) < 1:

                await message.reply_text(
                    "Cú pháp: `/info USER_ID`",
                    parse_mode="Markdown",
                )

                return

            target_id = int(args[0])

            u = db_query(
                """
                SELECT *
                FROM users
                WHERE user_id=%s
                """,
                (target_id,),
                fetchone=True,
            )

            if not u:

                await message.reply_text(
                    "❌ Không tìm thấy user này."
                )

                return

            username = (
                f"@{u[1]}"
                if u[1]
                else "Không username"
            )

            bank = (
                u[3]
                if u[3]
                else "Chưa liên kết"
            )

            referrer = (
                u[4]
                if u[4] is not None
                else "Không có"
            )

            msg = (
                f"🔍 *INFO USER:* `{u[0]}`\n"
                f"👤 Username: {username}\n"
                f"💰 Số dư: {u[2]:,}đ\n"
                f"🏦 Bank: `{bank}`\n"
                f"🔗 Người giới thiệu: `{referrer}`\n"
                f"🚫 Cấm dùng: "
                f"{'Có' if u[5] else 'Không'}\n"
                f"🚫 Cấm rút: "
                f"{'Có' if u[6] else 'Không'}\n"
                f"🕒 Ngày tham gia: `{u[7]}`"
            )

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

        # ====================================================
        # /BAN
        # ====================================================

        elif cmd == "/ban":

            if len(args) < 1:

                await message.reply_text(
                    "Cú pháp: `/ban USER_ID`",
                    parse_mode="Markdown",
                )

                return

            target_id = int(args[0])

            db_query(
                """
                UPDATE users
                SET is_banned=1
                WHERE user_id=%s
                """,
                (target_id,),
                commit=True,
            )

            user_withdraw_state.pop(
                target_id,
                None,
            )

            await message.reply_text(
                f"✅ Đã cấm người dùng "
                f"`{target_id}` vĩnh viễn.",
                parse_mode="Markdown",
            )

        # ====================================================
        # /CAM
        # ====================================================

        elif cmd == "/cam":

            if len(args) < 1:

                await message.reply_text(
                    "Cú pháp: `/cam USER_ID`",
                    parse_mode="Markdown",
                )

                return

            target_id = int(args[0])

            db_query(
                """
                UPDATE users
                SET is_withdraw_banned=1
                WHERE user_id=%s
                """,
                (target_id,),
                commit=True,
            )

            user_withdraw_state.pop(
                target_id,
                None,
            )

            await message.reply_text(
                f"✅ Đã cấm người dùng "
                f"`{target_id}` rút tiền.",
                parse_mode="Markdown",
            )

        # ====================================================
        # /NAP /TRU
        # ====================================================

        elif cmd in ("/nap", "/tru"):

            if len(args) < 2:

                await message.reply_text(
                    f"Cú pháp: `{cmd} USER_ID SO_TIEN`",
                    parse_mode="Markdown",
                )

                return

            target_id = int(args[0])
            amount = int(args[1])

            if amount <= 0:

                await message.reply_text(
                    "❌ Số tiền phải lớn hơn 0."
                )

                return

            exists = db_query(
                """
                SELECT user_id
                FROM users
                WHERE user_id=%s
                """,
                (target_id,),
                fetchone=True,
            )

            if not exists:

                await message.reply_text(
                    "❌ User chưa tồn tại trong database."
                )

                return

            # ------------------------------------------------
            # NẠP
            # ------------------------------------------------

            if cmd == "/nap":

                def add_money(cursor):

                    cursor.execute(
                        """
                        UPDATE users
                        SET balance=balance+%s
                        WHERE user_id=%s
                        """,
                        (
                            amount,
                            target_id,
                        ),
                    )

                    cursor.execute(
                        """
                        INSERT INTO transactions
                            (
                                user_id,
                                type,
                                amount,
                                status,
                                created_at,
                                details
                            )
                        VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """,
                        (
                            target_id,
                            "Nạp Tiền (Admin)",
                            amount,
                            "Thành công",
                            get_now_str(),
                            "Cộng tiền từ Admin",
                        ),
                    )

                    return True

                db_transaction(add_money)

                await message.reply_text(
                    f"✅ Đã cộng "
                    f"{amount:,}đ cho ID "
                    f"`{target_id}`.",
                    parse_mode="Markdown",
                )

            # ------------------------------------------------
            # TRỪ
            # ------------------------------------------------

            else:

                def deduct(cursor):

                    cursor.execute(
                        """
                        UPDATE users
                        SET balance=balance-%s
                        WHERE user_id=%s
                        AND balance>=%s
                        """,
                        (
                            amount,
                            target_id,
                            amount,
                        ),
                    )

                    if cursor.rowcount != 1:
                        return False

                    cursor.execute(
                        """
                        INSERT INTO transactions
                            (
                                user_id,
                                type,
                                amount,
                                status,
                                created_at,
                                details
                            )
                        VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """,
                        (
                            target_id,
                            "Trừ Tiền (Admin)",
                            amount,
                            "Thành công",
                            get_now_str(),
                            "Trừ tiền từ Admin",
                        ),
                    )

                    return True

                ok = db_transaction(
                    deduct
                )

                if not ok:

                    await message.reply_text(
                        "❌ Số dư user không đủ để trừ."
                    )

                    return

                await message.reply_text(
                    f"✅ Đã trừ "
                    f"{amount:,}đ của ID "
                    f"`{target_id}`.",
                    parse_mode="Markdown",
                )

        # ====================================================
        # /RUTLS
        # ====================================================

        elif cmd == "/rutls":

            txs = db_query(
                """
                SELECT
                    id,
                    user_id,
                    amount,
                    details,
                    created_at
                FROM transactions
                WHERE type='Rút Tiền'
                AND status='Chờ duyệt'
                ORDER BY id ASC
                """,
                fetchall=True,
            )

            if not txs:

                await message.reply_text(
                    "🎉 Không có yêu cầu rút tiền "
                    "nào đang chờ duyệt!"
                )

                return

            for (
                tx_id,
                target_id,
                amount,
                details,
                created_at,
            ) in txs:

                btns = [
                    [
                        InlineKeyboardButton(
                            "✅ Duyệt",
                            callback_data=f"approve_{tx_id}",
                        ),
                        InlineKeyboardButton(
                            "❌ Từ chối",
                            callback_data=f"reject_{tx_id}",
                        ),
                    ]
                ]

                await message.reply_text(
                    f"🆔 *Mã Lệnh:* #{tx_id}\n"
                    f"👤 *User:* `{target_id}`\n"
                    f"💵 *Số tiền:* {amount:,}đ\n"
                    f"🏦 *Bank:* "
                    f"`{details or 'Không có'}`\n"
                    f"🕒 *Thời gian:* `{created_at}`",
                    reply_markup=InlineKeyboardMarkup(btns),
                    parse_mode="Markdown",
                )

        # ====================================================
        # /RUTTC
        # ====================================================

        elif cmd == "/ruttc":

            txs = db_query(
                """
                SELECT
                    id,
                    user_id,
                    amount,
                    created_at
                FROM transactions
                WHERE type='Rút Tiền'
                AND status='Thành công'
                ORDER BY id DESC
                LIMIT 15
                """,
                fetchall=True,
            )

            if not txs:

                await message.reply_text(
                    "📜 Chưa có lệnh rút nào được duyệt."
                )

                return

            msg = (
                "📜 *CÁC LỆNH RÚT ĐÃ DUYỆT "
                "GẦN ĐÂY:*\n\n"
            )

            for (
                tx_id,
                target_id,
                amount,
                created_at,
            ) in txs:

                msg += (
                    f"✅ #{tx_id} | "
                    f"User: `{target_id}` | "
                    f"{amount:,}đ | "
                    f"`{created_at}`\n"
                )

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

        # ====================================================
        # /LSGD
        # ====================================================

        elif cmd == "/lsgd":

            if len(args) < 1:

                await message.reply_text(
                    "Cú pháp: `/lsgd USER_ID`",
                    parse_mode="Markdown",
                )

                return

            target_id = int(args[0])

            invited_users = db_query(
                """
                SELECT
                    user_id,
                    username
                FROM users
                WHERE referrer_id=%s
                ORDER BY joined_at DESC
                """,
                (target_id,),
                fetchall=True,
            )

            msg = (
                f"👥 *DANH SÁCH BẠN BÈ "
                f"ĐÃ MỜI CỦA ID `{target_id}`:*\n"
            )

            if invited_users:

                for invited_id, username in invited_users:

                    uname = (
                        f"@{username}"
                        if username
                        else "Không username"
                    )

                    msg += (
                        f"- ID: `{invited_id}` "
                        f"({uname})\n"
                    )

            else:

                msg += "- Chưa có người được mời.\n"

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
                (target_id,),
                fetchall=True,
            )

            msg += (
                "\n📜 *LỊCH SỬ GIAO DỊCH:*\n"
            )

            if txs:

                for (
                    tx_type,
                    amount,
                    status,
                    created_at,
                ) in txs:

                    msg += (
                        f"- {tx_type}: "
                        f"{amount:,}đ "
                        f"[{status}] "
                        f"lúc `{created_at}`\n"
                    )

            else:

                msg += "- Chưa có giao dịch.\n"

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

        # ====================================================
        # /BAOTRI
        # ====================================================

        elif cmd == "/baotri":

            curr = is_maintenance()

            new_val = (
                "0"
                if curr
                else "1"
            )

            db_query(
                """
                UPDATE settings
                SET value=%s
                WHERE key='maintenance'
                """,
                (new_val,),
                commit=True,
            )

            status_str = (
                "BẮT ĐẦU BẢO TRÌ 🔴"
                if new_val == "1"
                else "TẮT BẢO TRÌ 🟢"
            )

            await message.reply_text(
                f"⚙️ Đã thay đổi trạng thái hệ thống: "
                f"*{status_str}*",
                parse_mode="Markdown",
            )

    except (
        ValueError,
        TypeError,
    ):

        await message.reply_text(
            "❌ Tham số không hợp lệ. "
            "Vui lòng kiểm tra lại cú pháp."
        )

    except Exception as exc:

        logger.exception(
            "Lỗi admin command %s: %s",
            cmd,
            exc,
        )

        await message.reply_text(
            "❌ Đã xảy ra lỗi khi xử lý lệnh."
        )


# ============================================================
# TEXT DISPATCHER
# ============================================================

async def text_message_dispatcher(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_message:
        return

    if await handle_anti_spam(
        update,
        context,
    ):
        return

    handled = await handle_withdraw_amount(
        update,
        context,
    )

    if handled:
        return

    await menu_handler(
        update,
        context,
    )


# ============================================================
# ERROR
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Exception khi xử lý update: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "Chưa cấu hình BOT_TOKEN."
        )

    if not DATABASE_URL:

        raise RuntimeError(
            "Chưa cấu hình DATABASE_URL."
        )

    # Tạo bảng nếu chưa có
    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "lk",
            link_bank_command,
        )
    )

    # Lệnh reset bank mới
    app.add_handler(
        CommandHandler(
            "resetbank",
            reset_bank_command,
        )
    )

    # --------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            verify_join_callback,
            pattern=r"^verify_join$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            captcha_callback,
            pattern=r"^captcha_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            cancel_withdraw_callback,
            pattern=r"^cancel_withdraw$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(approve|reject)_\d+$",
        )
    )

    # --------------------------------------------------------
    # ADMIN COMMANDS
    # --------------------------------------------------------

    admin_cmds = [
        "tb",
        "info",
        "ban",
        "cam",
        "rutls",
        "ruttc",
        "nap",
        "tru",
        "lsgd",
        "baotri",
    ]

    for command in admin_cmds:

        app.add_handler(
            CommandHandler(
                command,
                admin_commands,
            )
        )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message_dispatcher,
        )
    )

    # --------------------------------------------------------
    # ERROR
    # --------------------------------------------------------

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "🤖 Bot đang chạy..."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
