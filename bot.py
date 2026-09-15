import asyncio
import logging
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

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
# CẤU HÌNH BOT
# ============================================================
# KHÔNG dán token thật trực tiếp vào mã nguồn.
# Linux/Termux: export BOT_TOKEN="TOKEN_CUA_BAN"
# Windows PowerShell: $env:BOT_TOKEN="TOKEN_CUA_BAN"
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADMIN_ID = 5633649201
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")
DB_FILE = "bot_database.db"

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

# Anti-spam
SPAM_WINDOW_SECONDS = 4
SPAM_MAX_MESSAGES = 10
TEMP_BAN_MINUTES = 2

user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ============================================================
# DATABASE
# ============================================================
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=15)
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                bank_info TEXT,
                referrer_id INTEGER,
                is_banned INTEGER NOT NULL DEFAULT 0,
                is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                details TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', '0')"
        )

        # Index để truy vấn lịch sử nhanh hơn
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_user "
            "ON transactions(user_id, id DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_withdraw "
            "ON transactions(type, status, id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_referrer "
            "ON users(referrer_id)"
        )

        conn.commit()
    finally:
        conn.close()


def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
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
    finally:
        conn.close()


def db_transaction(callback):
    """
    Chạy nhiều thao tác SQLite trong cùng một transaction.
    callback(cursor) phải trả về giá trị cần dùng.
    """
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
# HELPER
# ============================================================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Tài Khoản"), KeyboardButton("Mời Bạn Bè")],
        [KeyboardButton("Rút Tiền"), KeyboardButton("Nhóm Hỗ Trợ")],
        [KeyboardButton("Lịch Sử")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def is_maintenance():
    res = db_query(
        "SELECT value FROM settings WHERE key='maintenance'",
        fetchone=True,
    )
    return bool(res and res[0] == "1")


async def check_channel_membership(bot, user_id):
    """
    Kiểm tra tất cả kênh bắt buộc.
    Lưu ý: bot cần có quyền phù hợp trong các kênh để Telegram
    cho phép get_chat_member hoạt động ổn định.
    """
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
                "Không kiểm tra được thành viên %s trong %s: %s",
                user_id,
                channel,
                exc,
            )
            return False

    return True


async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    message = update.effective_message

    if not user or user.id == ADMIN_ID or not message:
        return False

    now = datetime.now()

    # Đang bị cấm tạm thời
    ban_until = temp_bans.get(user.id)
    if ban_until:
        if now < ban_until:
            remaining_seconds = max(
                0, int((ban_until - now).total_seconds())
            )
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60

            await message.reply_text(
                f"🚫 Bạn đang bị cấm sử dụng bot trong "
                f"{minutes} phút {seconds} giây nữa!\n"
                f"Lý do: Spam tin nhắn."
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
            f"🚫 Bạn đã bị cấm sử dụng bot trong "
            f"{TEMP_BAN_MINUTES} phút!\n"
            f"Lý do: Spam {SPAM_MAX_MESSAGES} tin nhắn "
            f"trong {SPAM_WINDOW_SECONDS} giây."
        )
        return True

    return False


async def ensure_user_exists(update: Update):
    """
    Đảm bảo user có trong DB.
    Trả về bản ghi users hoặc None nếu bị cấm.
    """
    user = update.effective_user
    if not user:
        return None

    row = db_query(
        "SELECT user_id, balance, bank_info, is_banned, "
        "is_withdraw_banned, referrer_id "
        "FROM users WHERE user_id=?",
        (user.id,),
        fetchone=True,
    )

    if row:
        # Cập nhật username nếu user đổi username
        current_username = user.username or ""
        db_query(
            "UPDATE users SET username=? WHERE user_id=?",
            (current_username, user.id),
            commit=True,
        )

    return row


async def require_private_user(update: Update) -> bool:
    """
    True nếu có thể tiếp tục xử lý user ở private chat.
    """
    if not update.effective_chat or update.effective_chat.type != "private":
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

    return True


# ============================================================
# /START
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context):
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    # Nếu /start được gọi trong group -> lưu group ID
    if chat.type != "private":
        db_query(
            "INSERT OR IGNORE INTO groups(chat_id) VALUES(?)",
            (chat.id,),
            commit=True,
        )
        return

    if is_maintenance() and user.id != ADMIN_ID:
        await update.message.reply_text(
            "🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!"
        )
        return

    db_user = db_query(
        "SELECT user_id, is_banned FROM users WHERE user_id=?",
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[1] == 1:
        await update.message.reply_text(
            "🚫 Tài khoản của bạn đã bị cấm vĩnh viễn."
        )
        return

    # --------------------------------------------------------
    # Xử lý mã giới thiệu
    # --------------------------------------------------------
    referrer_id = None

    if context.args:
        try:
            ref_id = int(context.args[0])

            if ref_id != user.id:
                # Chỉ nhận referrer nếu referrer thực sự tồn tại
                ref_exists = db_query(
                    "SELECT user_id FROM users WHERE user_id=?",
                    (ref_id,),
                    fetchone=True,
                )
                if ref_exists:
                    referrer_id = ref_id

        except (ValueError, TypeError):
            pass

    if not db_user:
        db_query(
            """
            INSERT INTO users
                (user_id, username, balance, referrer_id, joined_at)
            VALUES (?, ?, 0, ?, ?)
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
        # Nếu user cũ chưa có referrer thì không tự ý ghi đè.
        db_query(
            "UPDATE users SET username=? WHERE user_id=?",
            (user.username or "", user.id),
            commit=True,
        )

    # --------------------------------------------------------
    # Kiểm tra tham gia kênh
    # --------------------------------------------------------
    is_joined = await check_channel_membership(context.bot, user.id)

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
            "⚠️ *Vui lòng tham gia đầy đủ các kênh bên dưới "
            "để sử dụng bot:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        "🎉 CHÀO MỪNG BẠN ĐẾN VỚI BOT!",
        reply_markup=get_main_keyboard(),
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
        await query.answer(
            "Hệ thống đang bảo trì.",
            show_alert=True,
        )
        return

    is_joined = await check_channel_membership(context.bot, user.id)

    if not is_joined:
        try:
            await query.answer(
                "❌ Bạn chưa tham gia đủ các kênh bắt buộc!",
                show_alert=True,
            )
        except Exception:
            pass
        return

    # --------------------------------------------------------
    # Thưởng người giới thiệu - chống nhận thưởng 2 lần
    # --------------------------------------------------------
    db_user = db_query(
        "SELECT referrer_id FROM users WHERE user_id=?",
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[0]:
        ref_id = db_user[0]

        invited = db_query(
            """
            SELECT id FROM transactions
            WHERE user_id=?
              AND type='Thưởng Mời Bạn'
              AND details=?
            LIMIT 1
            """,
            (ref_id, f"Mời {user.id}"),
            fetchone=True,
        )

        if not invited:
            def reward_referrer(cursor):
                # Chỉ cộng nếu referrer vẫn tồn tại
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id=?",
                    (ref_id,),
                )
                if not cursor.fetchone():
                    return False

                cursor.execute(
                    "UPDATE users SET balance=balance+? WHERE user_id=?",
                    (REFERRAL_REWARD, ref_id),
                )

                cursor.execute(
                    """
                    INSERT INTO transactions
                        (user_id, type, amount, status, created_at, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ref_id,
                        "Thưởng Mời Bạn",
                        REFERRAL_REWARD,
                        "Thành công",
                        get_now_str(),
                        f"Mời {user.id}",
                    ),
                )
                return True

            try:
                rewarded = db_transaction(reward_referrer)

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
                                f"🎉 Bạn nhận được +{REFERRAL_REWARD:,}đ "
                                f"từ việc giới thiệu người dùng "
                                f"{username_str} thành công!"
                            ),
                        )
                    except Exception as exc:
                        logger.warning(
                            "Không gửi được thông báo thưởng referrer: %s",
                            exc,
                        )

            except sqlite3.Error as exc:
                logger.exception(
                    "Lỗi transaction thưởng giới thiệu: %s",
                    exc,
                )

    # Xóa nút cũ nếu có thể, rồi gửi menu mới
    try:
        await query.delete_message()
    except Exception:
        try:
            await query.edit_message_text(
                "✅ Bạn đã xác nhận tham gia thành công!"
            )
        except Exception:
            pass

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "✅ Bạn đã xác nhận thành công!\n"
                "Hãy chọn các mục ở menu bên dưới."
            ),
            reply_markup=get_main_keyboard(),
        )
    except Exception as exc:
        logger.warning(
            "Không gửi được menu sau verify cho %s: %s",
            user.id,
            exc,
        )


# ============================================================
# MENU
# ============================================================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if update.effective_chat.type != "private":
        return

    if is_maintenance() and user.id != ADMIN_ID:
        await message.reply_text(
            "🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!"
        )
        return

    db_user = db_query(
        """
        SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned
        FROM users WHERE user_id=?
        """,
        (user.id,),
        fetchone=True,
    )

    if not db_user or db_user[3] == 1:
        await message.reply_text(
            "🚫 Bạn không có quyền sử dụng bot."
        )
        return

    # Admin được sử dụng trong bảo trì; user thường phải join
    if user.id != ADMIN_ID:
        if not await check_channel_membership(context.bot, user.id):
            await message.reply_text(
                "⚠️ Bạn chưa tham gia đủ các kênh bắt buộc.\n"
                "Gõ /start để nhận lại danh sách nhóm."
            )
            return

    text = (message.text or "").strip()

    if text == "Tài Khoản":
        balance = db_user[1]

        invited_count = db_query(
            "SELECT COUNT(*) FROM users WHERE referrer_id=?",
            (user.id,),
            fetchone=True,
        )[0]

        total_withdraw = db_query(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE user_id=?
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
            f"👥 *Tổng số bạn bè đã mời:* {invited_count} người\n"
            f"💸 *Tổng rút đã duyệt:* {total_withdraw:,}đ"
        )

        await message.reply_text(msg, parse_mode="Markdown")

    elif text == "Mời Bạn Bè":
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as exc:
            logger.exception("Không lấy được username bot: %s", exc)
            await message.reply_text(
                "❌ Không lấy được thông tin bot. Vui lòng thử lại."
            )
            return

        if not bot_username:
            await message.reply_text(
                "❌ Bot chưa có username, không thể tạo link mời."
            )
            return

        ref_link = f"https://t.me/{bot_username}?start={user.id}"

        msg = (
            "🔗 *LINK MỜI BẠN BÈ CỦA BẠN:*\n"
            f"`{ref_link}`\n\n"
            "🎁 *Thể lệ:*\n"
            f"- 🎯 Mời 1 bạn bè thành công nhận: "
            f"*+{REFERRAL_REWARD:,}đ* (1F=1K)\n"
            "- 📌 Người được mời phải tham gia đủ nhóm "
            "và ấn nút Xác Nhận thì bạn mới nhận được tiền.\n"
            f"- 💳 Min Rút tiền: *{MIN_WITHDRAW:,}đ*\n"
            f"- 🔝 Rút Tối đa: *{MAX_WITHDRAW:,}đ*"
        )

        await message.reply_text(msg, parse_mode="Markdown")

    elif text == "Nhóm Hỗ Trợ":
        await message.reply_text(
            f"💬 *Nhóm Hỗ Trợ:* {SUPPORT_GROUP}",
            parse_mode="Markdown",
        )

    elif text == "Lịch Sử":
        txs = db_query(
            """
            SELECT type, amount, status, created_at
            FROM transactions
            WHERE user_id=?
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

        msg = "📜 *LỊCH SỬ GIAO DỊCH GẦN ĐÂY* (Giờ VN):\n\n"

        for tx_type, amount, status, created_at in txs:
            if status == "Thành công":
                icon = "✅"
            elif status == "Từ chối":
                icon = "❌"
            else:
                icon = "⏳"

            msg += (
                f"{icon} *{tx_type}*: {amount:,}đ | {status}\n"
                f"🕒 `{created_at}`\n"
                "---------------------\n"
            )

        await message.reply_text(msg, parse_mode="Markdown")

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
            user_withdraw_state[user.id] = "WAITING_AMOUNT"

            await message.reply_text(
                f"💳 *Tài khoản thụ hưởng:* `{bank_info}`\n"
                f"💰 *Số dư:* {db_user[1]:,}đ\n"
                f"📌 *Min rút:* {MIN_WITHDRAW:,}đ - "
                f"*Max rút:* {MAX_WITHDRAW:,}đ\n\n"
                "👉 *Vui lòng nhập số tiền bạn muốn rút:*",
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
        await update.message.reply_text(
            "🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!"
        )
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Sai cú pháp!\n\n"
            "Ví dụ đúng:\n"
            "`/lk 1068030300 VCB NGUYEN CA NGU`",
            parse_mode="Markdown",
        )
        return

    bank_str = " ".join(context.args).strip()

    if len(bank_str) > 300:
        await update.message.reply_text(
            "❌ Thông tin ngân hàng quá dài."
        )
        return

    db_query(
        "UPDATE users SET bank_info=? WHERE user_id=?",
        (bank_str, user.id),
        commit=True,
    )

    await update.message.reply_text(
        f"✅ *Liên kết thành công!*\n"
        f"Thông tin của bạn: `{bank_str}`",
        parse_mode="Markdown",
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

    if user_withdraw_state.get(user.id) != "WAITING_AMOUNT":
        return False

    # Xóa trạng thái trước nếu có lỗi bất ngờ để tránh trạng thái treo vô hạn
    text = (message.text or "").strip().replace(",", "").replace(".", "")

    if not text.isdigit():
        await message.reply_text(
            "❌ Số tiền phải là chữ số hợp lệ. Vui lòng nhập lại:"
        )
        return True

    amount = int(text)

    if amount <= 0:
        await message.reply_text(
            "❌ Số tiền không hợp lệ."
        )
        return True

    db_user = db_query(
        """
        SELECT balance, bank_info, is_banned, is_withdraw_banned
        FROM users WHERE user_id=?
        """,
        (user.id,),
        fetchone=True,
    )

    if not db_user:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            "❌ Không tìm thấy tài khoản. Vui lòng /start lại."
        )
        return True

    balance, bank_info, is_banned, is_withdraw_banned = db_user

    if is_banned:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            "🚫 Tài khoản của bạn đã bị cấm."
        )
        return True

    if is_withdraw_banned:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            "🚫 Bạn đã bị cấm tính năng rút tiền."
        )
        return True

    if not bank_info:
        user_withdraw_state.pop(user.id, None)
        await message.reply_text(
            "⚠️ Bạn chưa liên kết ngân hàng. Vui lòng dùng /lk trước."
        )
        return True

    if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
        await message.reply_text(
            f"❌ Số tiền rút phải từ {MIN_WITHDRAW:,}đ "
            f"đến {MAX_WITHDRAW:,}đ!"
        )
        return True

    # --------------------------------------------------------
    # Trừ tiền + tạo giao dịch trong CÙNG transaction.
    # Chống trường hợp bấm/rút đồng thời làm âm số dư.
    # --------------------------------------------------------
    try:
        def create_withdraw(cursor):
            cursor.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE user_id=?
                  AND balance >= ?
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
                VALUES (?, ?, ?, ?, ?, ?)
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

            return cursor.lastrowid

        tx_id = db_transaction(create_withdraw)

    except sqlite3.Error as exc:
        logger.exception("Lỗi tạo lệnh rút: %s", exc)
        await message.reply_text(
            "❌ Có lỗi cơ sở dữ liệu khi tạo lệnh rút. Vui lòng thử lại."
        )
        return True

    if not tx_id:
        await message.reply_text(
            "❌ Số dư không đủ hoặc tài khoản không được phép rút."
        )
        return True

    user_withdraw_state.pop(user.id, None)

    await message.reply_text(
        "⏳ Đã gửi yêu cầu rút tiền thành công! "
        "Vui lòng chờ Admin duyệt."
    )

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
        f"👤 *Người rút:* {username_str} (`{user.id}`)\n"
        f"💵 *Số tiền:* {amount:,}đ\n"
        f"🏦 *Thông tin:* `{bank_info}`\n"
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
        # Lệnh đã tạo trong DB nhưng admin không nhận được Telegram.
        # Không hoàn tiền tự động ở đây vì tiền vẫn đang ở trạng thái chờ duyệt.
        logger.exception(
            "Không gửi được yêu cầu rút #%s cho admin: %s",
            tx_id,
            exc,
        )

        await message.reply_text(
            "⚠️ Lệnh rút đã được ghi nhận nhưng bot chưa gửi được "
            "thông báo cho Admin. Admin có thể dùng /rutls để kiểm tra."
        )

    return True


# ============================================================
# CALLBACK DUYỆT / TỪ CHỐI
# ============================================================
async def admin_withdraw_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    if query.from_user.id != ADMIN_ID:
        await query.answer(
            "❌ Bạn không có quyền.",
            show_alert=True,
        )
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
        await query.answer(
            "❌ Mã giao dịch không hợp lệ.",
            show_alert=True,
        )
        return

    tx = db_query(
        """
        SELECT user_id, amount, status, details
        FROM transactions
        WHERE id=? AND type='Rút Tiền'
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

    user_id, amount, status, bank_info = tx

    if status != "Chờ duyệt":
        try:
            await query.edit_message_text(
                f"{query.message.text or ''}\n\n"
                "⚠️ Giao dịch này đã được xử lý trước đó!"
            )
        except Exception:
            pass
        return

    # --------------------------------------------------------
    # Approve / reject trong transaction, chống double-click.
    # --------------------------------------------------------
    if action == "approve":
        try:
            def approve(cursor):
                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Thành công'
                    WHERE id=? AND status='Chờ duyệt'
                    """,
                    (tx_id,),
                )
                return cursor.rowcount == 1

            changed = db_transaction(approve)

        except sqlite3.Error as exc:
            logger.exception(
                "Lỗi duyệt giao dịch #%s: %s",
                tx_id,
                exc,
            )
            await query.answer(
                "❌ Lỗi database.",
                show_alert=True,
            )
            return

        if not changed:
            await query.answer(
                "⚠️ Giao dịch đã được xử lý.",
                show_alert=True,
            )
            return

        new_text = (
            f"{query.message.text or ''}\n\n"
            "✅ *TRẠNG THÁI: ĐÃ DUYỆT RÚT*"
        )

        try:
            await query.edit_message_text(
                new_text,
                parse_mode="Markdown",
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 Admin đã *duyệt* yêu cầu rút "
                    f"{amount:,}đ của bạn!"
                ),
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.warning(
                "Không báo được user %s khi duyệt: %s",
                user_id,
                exc,
            )

    elif action == "reject":
        try:
            def reject(cursor):
                # Chỉ xử lý nếu vẫn còn Chờ duyệt
                cursor.execute(
                    """
                    UPDATE transactions
                    SET status='Từ chối'
                    WHERE id=? AND status='Chờ duyệt'
                    """,
                    (tx_id,),
                )

                if cursor.rowcount != 1:
                    return False

                cursor.execute(
                    """
                    UPDATE users
                    SET balance = balance + ?
                    WHERE user_id=?
                    """,
                    (amount, user_id),
                )

                return True

            changed = db_transaction(reject)

        except sqlite3.Error as exc:
            logger.exception(
                "Lỗi từ chối giao dịch #%s: %s",
                tx_id,
                exc,
            )
            await query.answer(
                "❌ Lỗi database.",
                show_alert=True,
            )
            return

        if not changed:
            await query.answer(
                "⚠️ Giao dịch đã được xử lý.",
                show_alert=True,
            )
            return

        new_text = (
            f"{query.message.text or ''}\n\n"
            "❌ *TRẠNG THÁI: ĐÃ TỪ CHỐI*"
        )

        try:
            await query.edit_message_text(
                new_text,
                parse_mode="Markdown",
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"❌ Admin đã *từ chối* yêu cầu rút "
                    f"{amount:,}đ của bạn.\n"
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
# ADMIN COMMANDS
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

    cmd = (message.text or "").split()[0].split("@")[0].lower()
    args = context.args or []

    try:
        if cmd == "/tb":
            if not args:
                await message.reply_text(
                    "Cú pháp:\n`/tb Nội dung thông báo`",
                    parse_mode="Markdown",
                )
                return

            content = (message.text or "")[3:].strip()

            if not content:
                await message.reply_text(
                    "❌ Nội dung thông báo đang trống."
                )
                return

            users = db_query(
                "SELECT user_id FROM users WHERE is_banned=0",
                fetchall=True,
            )
            groups = db_query(
                "SELECT chat_id FROM groups",
                fetchall=True,
            )

            count = 0

            for (target_id,) in users:
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"📢 *THÔNG BÁO:*\n\n{content}",
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
                        text=f"📢 *THÔNG BÁO:*\n\n{content}",
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
                f"✅ Đã gửi thông báo tới {count} người dùng / nhóm."
            )

        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(
                    "Cú pháp: `/info USER_ID`",
                    parse_mode="Markdown",
                )
                return

            target_id = int(args[0])

            u = db_query(
                "SELECT * FROM users WHERE user_id=?",
                (target_id,),
                fetchone=True,
            )

            if not u:
                await message.reply_text(
                    "❌ Không tìm thấy user này."
                )
                return

            username = f"@{u[1]}" if u[1] else "Không username"
            bank = u[3] or "Chưa liên kết"
            referrer = u[4] if u[4] is not None else "Không có"

            msg = (
                f"🔍 *INFO USER:* `{u[0]}`\n"
                f"👤 Username: {username}\n"
                f"💰 Số dư: {u[2]:,}đ\n"
                f"🏦 Bank: `{bank}`\n"
                f"🔗 Người giới thiệu: `{referrer}`\n"
                f"🚫 Cấm dùng: {'Có' if u[5] else 'Không'}\n"
                f"🚫 Cấm rút: {'Có' if u[6] else 'Không'}\n"
                f"🕒 Ngày tham gia: `{u[7]}`"
            )

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

        elif cmd == "/ban":
            if len(args) < 1:
                await message.reply_text(
                    "Cú pháp: `/ban USER_ID`",
                    parse_mode="Markdown",
                )
                return

            target_id = int(args[0])

            changed = db_query(
                """
                UPDATE users SET is_banned=1
                WHERE user_id=?
                """,
                (target_id,),
                commit=True,
            )

            # Xóa trạng thái rút nếu đang chờ
            user_withdraw_state.pop(target_id, None)

            await message.reply_text(
                f"✅ Đã cấm người dùng `{target_id}` vĩnh viễn.",
                parse_mode="Markdown",
            )

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
                UPDATE users SET is_withdraw_banned=1
                WHERE user_id=?
                """,
                (target_id,),
                commit=True,
            )

            user_withdraw_state.pop(target_id, None)

            await message.reply_text(
                f"✅ Đã cấm người dùng `{target_id}` rút tiền.",
                parse_mode="Markdown",
            )

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
                "SELECT user_id FROM users WHERE user_id=?",
                (target_id,),
                fetchone=True,
            )

            if not exists:
                await message.reply_text(
                    "❌ User chưa tồn tại trong database."
                )
                return

            if cmd == "/nap":
                db_query(
                    """
                    UPDATE users
                    SET balance=balance+?
                    WHERE user_id=?
                    """,
                    (amount, target_id),
                    commit=True,
                )

                db_query(
                    """
                    INSERT INTO transactions
                        (user_id, type, amount, status, created_at, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_id,
                        "Nạp Tiền (Admin)",
                        amount,
                        "Thành công",
                        get_now_str(),
                        "Cộng tiền từ Admin",
                    ),
                    commit=True,
                )

                await message.reply_text(
                    f"✅ Đã cộng {amount:,}đ cho ID `{target_id}`.",
                    parse_mode="Markdown",
                )

            else:
                # Không cho /tru làm âm số dư
                def deduct(cursor):
                    cursor.execute(
                        """
                        UPDATE users
                        SET balance=balance-?
                        WHERE user_id=? AND balance>=?
                        """,
                        (amount, target_id, amount),
                    )

                    if cursor.rowcount != 1:
                        return False

                    cursor.execute(
                        """
                        INSERT INTO transactions
                            (user_id, type, amount, status,
                             created_at, details)
                        VALUES (?, ?, ?, ?, ?, ?)
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

                ok = db_transaction(deduct)

                if not ok:
                    await message.reply_text(
                        "❌ Số dư user không đủ để trừ."
                    )
                    return

                await message.reply_text(
                    f"✅ Đã trừ {amount:,}đ của ID `{target_id}`.",
                    parse_mode="Markdown",
                )

        elif cmd == "/rutls":
            txs = db_query(
                """
                SELECT id, user_id, amount, details, created_at
                FROM transactions
                WHERE type='Rút Tiền'
                  AND status='Chờ duyệt'
                ORDER BY id ASC
                """,
                fetchall=True,
            )

            if not txs:
                await message.reply_text(
                    "🎉 Không có yêu cầu rút tiền nào đang chờ duyệt!"
                )
                return

            for tx_id, target_id, amount, details, created_at in txs:
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
                    f"🏦 *Bank:* `{details or 'Không có'}`\n"
                    f"🕒 *Thời gian:* `{created_at}`",
                    reply_markup=InlineKeyboardMarkup(btns),
                    parse_mode="Markdown",
                )

        elif cmd == "/ruttc":
            txs = db_query(
                """
                SELECT id, user_id, amount, created_at
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

            msg = "📜 *CÁC LỆNH RÚT ĐÃ DUYỆT GẦN ĐÂY:*\n\n"

            for tx_id, target_id, amount, created_at in txs:
                msg += (
                    f"✅ #{tx_id} | User: `{target_id}` | "
                    f"{amount:,}đ | `{created_at}`\n"
                )

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

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
                SELECT user_id, username
                FROM users
                WHERE referrer_id=?
                ORDER BY joined_at DESC
                """,
                (target_id,),
                fetchall=True,
            )

            msg = (
                f"👥 *DANH SÁCH BẠN BÈ ĐÃ MỜI "
                f"CỦA ID `{target_id}`:*\n"
            )

            if invited_users:
                for invited_id, username in invited_users:
                    uname = (
                        f"@{username}"
                        if username
                        else "Không username"
                    )
                    msg += (
                        f"- ID: `{invited_id}` ({uname})\n"
                    )
            else:
                msg += "- Chưa có người được mời.\n"

            txs = db_query(
                """
                SELECT type, amount, status, created_at
                FROM transactions
                WHERE user_id=?
                ORDER BY id DESC
                LIMIT 10
                """,
                (target_id,),
                fetchall=True,
            )

            msg += "\n📜 *LỊCH SỬ GIAO DỊCH:*\n"

            if txs:
                for tx_type, amount, status, created_at in txs:
                    msg += (
                        f"- {tx_type}: {amount:,}đ "
                        f"[{status}] lúc `{created_at}`\n"
                    )
            else:
                msg += "- Chưa có giao dịch.\n"

            await message.reply_text(
                msg,
                parse_mode="Markdown",
            )

        elif cmd == "/baotri":
            curr = is_maintenance()
            new_val = "0" if curr else "1"

            db_query(
                """
                UPDATE settings SET value=?
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

    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Tham số không hợp lệ. Vui lòng kiểm tra lại cú pháp."
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

    # Anti-spam chỉ chạy 1 lần cho mỗi tin nhắn text.
    if await handle_anti_spam(update, context):
        return

    # Nếu đang nhập tiền rút thì ưu tiên xử lý số tiền.
    handled = await handle_withdraw_amount(update, context)

    if handled:
        return

    await menu_handler(update, context)


# ============================================================
# ERROR HANDLER
# ============================================================
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception(
        "Exception khi xử lý update: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================
def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Chưa cấu hình BOT_TOKEN. "
            "Hãy đặt biến môi trường BOT_TOKEN trước khi chạy bot."
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # /start
    app.add_handler(CommandHandler("start", start_command))

    # Liên kết ngân hàng
    app.add_handler(CommandHandler("lk", link_bank_command))

    # Verify kênh
    app.add_handler(
        CallbackQueryHandler(
            verify_join_callback,
            pattern=r"^verify_join$",
        )
    )

    # Duyệt / từ chối rút tiền
    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(approve|reject)_\d+$",
        )
    )

    # Admin commands
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
            CommandHandler(command, admin_commands)
        )

    # Tin nhắn text
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message_dispatcher,
        )
    )

    app.add_error_handler(error_handler)

    logger.info("🤖 Bot đang chạy...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
