import asyncio
import logging
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

# ================= CẤU HÌNH BOT =================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Thay Token Bot của bạn vào đây
ADMIN_ID = 5633649201
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

# Danh sách các kênh bắt buộc tham gia
REQUIRED_CHANNELS = [
    "@hocviennghiencobac",
    "@conmuamenmenl",
    "@Sankhuyenmaionline",
    "@tbck2026",
    "@chungnaomoidu",
]
SUPPORT_GROUP = "https://t.me/conmuamenmenl"

# Cấu hình rút tiền
MIN_WITHDRAW = 5000
MAX_WITHDRAW = 300000
REFERRAL_REWARD = 1000

# Bộ nhớ tạm xử lý Anti-Spam & Nhập tiền rút
user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ================= CƠ SỞ DỮ LIỆU (SQLITE) =================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Bảng người dùng
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            bank_info TEXT,
            referrer_id INTEGER,
            is_banned INTEGER DEFAULT 0,
            is_withdraw_banned INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)
    
    # Bảng lịch sử giao dịch
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount INTEGER,
            status TEXT,
            created_at TEXT,
            details TEXT
        )
    """)
    
    # Bảng lưu thông tin nhóm bot tham gia (dùng cho lệnh /tb)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    
    # Bảng cấu hình hệ thống (bảo trì)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance', '0')")
    
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone:
        res = cursor.fetchone()
    elif fetchall:
        res = cursor.fetchall()
    if commit:
        conn.commit()
    conn.close()
    return res

def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

# ================= HELPER FUNCTIONS =================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Tài Khoản"), KeyboardButton("Mời Bạn Bè")],
        [KeyboardButton("Rút Tiền"), KeyboardButton("Nhóm Hỗ Trợ")],
        [KeyboardButton("Lịch Sử")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def check_channel_membership(bot, user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def is_maintenance():
    res = db_query("SELECT value FROM settings WHERE key='maintenance'", fetchone=True)
    return res and res[0] == "1"

# Anti-Spam Middleware Check
async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or user.id == ADMIN_ID:
        return False
    
    now = datetime.now()
    
    # Check nếu đang bị cấm tạm thời
    if user.id in temp_bans:
        ban_until = temp_bans[user.id]
        if now < ban_until:
            remaining_seconds = int((ban_until - now).total_seconds())
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            await update.effective_message.reply_text(
                f"🚫 Bạn đang bị cấm sử dụng bot trong {minutes} phút {seconds} giây nữa!\nLý do: Spam tin nhắn."
            )
            return True
        else:
            del temp_bans[user.id]
            
    # Ghi nhận thời gian tin nhắn
    user_msg_tracker[user.id].append(now)
    # Lọc các tin nhắn trong vòng 4 giây gần nhất
    user_msg_tracker[user.id] = [
        t for t in user_msg_tracker[user.id] if (now - t).total_seconds() <= 4
    ]
    
    # Kiểm tra điều kiện cấm (10 tin nhắn trong 4 giây)
    if len(user_msg_tracker[user.id]) >= 10:
        temp_bans[user.id] = now + timedelta(minutes=2)
        user_msg_tracker[user.id].clear()
        await update.effective_message.reply_text(
            "🚫 Bạn đã bị cấm sử dụng bot trong 2 phút!\nLý do: Spam 10 tin nhắn trong 4 giây."
        )
        return True
    return False

# ================= USER HANDLERS =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context): return
    
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    if chat_type != "private":
        # Lưu ID nhóm vào DB để phục vụ thông báo
        db_query("INSERT OR IGNORE INTO groups VALUES (?)", (update.effective_chat.id,), commit=True)
        return

    if is_maintenance() and user.id != ADMIN_ID:
        await update.message.reply_text("🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!")
        return

    # Check người dùng trong DB
    db_user = db_query("SELECT user_id, is_banned FROM users WHERE user_id=?", (user.id,), fetchone=True)
    
    if db_user and db_user[1] == 1:
        await update.message.reply_text("🚫 Tài khoản của bạn đã bị cấm vĩnh viễn.")
        return

    # Xử lý Mã Giới Thiệu
    referrer_id = None
    if context.args and len(context.args) > 0:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referrer_id = ref_id
        except ValueError:
            pass

    if not db_user:
        db_query(
            "INSERT INTO users (user_id, username, balance, referrer_id, joined_at) VALUES (?, ?, ?, ?, ?)",
            (user.id, user.username or "", 0, referrer_id, get_now_str()),
            commit=True,
        )

    # Kiểm tra tham gia nhóm
    is_joined = await check_channel_membership(context.bot, user.id)
    if not is_joined:
        buttons = [
            [InlineKeyboardButton("1. Học Viện Nghiện Cờ Bạc", url="https://t.me/hocviennghiencobac")],
            [InlineKeyboardButton("2. Cơn Mưa Mèn Mén", url="https://t.me/conmuamenmenl")],
            [InlineKeyboardButton("3. Săn Khuyến Mãi Online", url="https://t.me/Sankhuyenmaionline")],
            [InlineKeyboardButton("4. TBCK 2026", url="https://t.me/tbck2026")],
            [InlineKeyboardButton("5. Chừng Nào Mới Đủ", url="https://t.me/chungnaomoidu")],
            [InlineKeyboardButton("🟢 Xác Nhận Đã Tham Gia", callback_data="verify_join")],
        ]
        await update.message.reply_text(
            "⚠️ **Vui lòng tham gia đầy đủ các kênh bên dưới để sử dụng bot:**",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("🎉 CHÀO MỪNG BẠN ĐẾN VỚI BOT!", reply_markup=get_main_keyboard())

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    is_joined = await check_channel_membership(context.bot, user.id)
    if not is_joined:
        await query.edit_message_text(
            "❌ Bạn chưa tham gia đủ các kênh bắt buộc! Vui lòng kiểm tra lại.",
            reply_markup=query.message.reply_markup
        )
        return

    # Xử lý cộng tiền cho người giới thiệu nếu lần đầu xác nhận thành công
    db_user = db_query("SELECT referrer_id FROM users WHERE user_id=?", (user.id,), fetchone=True)
    if db_user and db_user[0]:
        ref_id = db_user[0]
        # Kiểm tra xem người giới thiệu đã từng nhận quà từ ID này chưa
        invited = db_query("SELECT * FROM transactions WHERE user_id=? AND details=?", (ref_id, f"Mời {user.id}"), fetchone=True)
        if not invited:
            # Cộng tiền cho người giới thiệu
            db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (REFERRAL_REWARD, ref_id), commit=True)
            db_query(
                "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (?, ?, ?, ?, ?, ?)",
                (ref_id, "Thưởng Mời Bạn", REFERRAL_REWARD, "Thành công", get_now_str(), f"Mời {user.id}"),
                commit=True
            )
            # Thông báo cho người giới thiệu
            try:
                username_str = f"@{user.username}" if user.username else str(user.id)
                await context.bot.send_message(
                    chat_id=ref_id,
                    text=f"🎉 Bạn nhận được +{REFERRAL_REWARD}đ từ việc giới thiệu người dùng {username_str} thành công!"
                )
            except Exception:
                pass

    await query.delete_message()
    await context.bot.send_message(
        chat_id=user.id,
        text="✅ Bạn đã xác nhận thành công! Hãy chọn các mục ở menu bên dưới.",
        reply_markup=get_main_keyboard()
    )

# ================= MENU FUNCTION HANDLERS =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context): return
    
    text = update.message.text
    user = update.effective_user

    if is_maintenance() and user.id != ADMIN_ID:
        await update.message.reply_text("🔴 Hệ thống đang bảo trì, vui lòng quay lại sau!")
        return

    # Kiểm tra cấm vĩnh viễn
    db_user = db_query("SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned FROM users WHERE user_id=?", (user.id,), fetchone=True)
    if not db_user or db_user[3] == 1:
        await update.message.reply_text("🚫 Bạn không có quyền sử dụng bot.")
        return

    # Kiểm tra đã join channel chưa
    if not await check_channel_membership(context.bot, user.id):
        await update.message.reply_text("⚠️ Bạn chưa tham gia đủ các kênh bắt buộc. Gõ /start để nhận lại danh sách nhóm.")
        return

    if text == "Tài Khoản":
        balance = db_user[1]
        # Tổng số bạn đã mời
        invited_count = db_query("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user.id,), fetchone=True)[0]
        # Tổng rút thành công
        total_withdraw = db_query(
            "SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='Rút Tiền' AND status='Thành công'",
            (user.id,), fetchone=True
        )[0] or 0

        msg = (
            f"👤 **THÔNG TIN TÀI KHOẢN**\n\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"💰 **Số dư hiện có:** {balance:,}đ\n"
            f"👥 **Tổng số bạn bè đã mời:** {invited_count} người\n"
            f"💸 **Tổng rút đã duyệt:** {total_withdraw:,}đ"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "Mời Bạn Bè":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user.id}"
        msg = (
            f"🔗 **LINK MỜI BẠN BÈ CỦA BẠN:**\n`{ref_link}`\n\n"
            f"🎁 **Thể lệ:**\n"
            f"- 🎯 Mời 1 bạn bè thành công nhận: **+{REFERRAL_REWARD:,}đ** (1F=1K)\n"
            f"- 📌 Người được mời phải tham gia đủ nhóm và ấn nút Xác Nhận thì bạn mới nhận được tiền.\n"
            f"- 💳 Min Rút tiền : **{MIN_WITHDRAW:,}đ**\n"
            f"- 🔝 Rút Tối đa : **{MAX_WITHDRAW:,}đ**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "Nhóm Hỗ Trợ":
        await update.message.reply_text(f"💬 **Nhóm Hỗ Trợ:** {SUPPORT_GROUP}")

    elif text == "Lịch Sử":
        txs = db_query(
            "SELECT type, amount, status, created_at FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user.id,), fetchall=True
        )
        if not txs:
            await update.message.reply_text("📜 Bạn chưa có giao dịch nào.")
            return

        msg = "📜 **LỊCH SỬ GIAO DỊCH GẦN ĐÂY** (Giờ VN):\n\n"
        for tx in txs:
            status_icon = "✅" if tx[2] == "Thành công" else ("❌" if tx[2] == "Từ chối" else "⏳")
            msg += f"{status_icon} **{tx[0]}**: {tx[1]:,}đ | {tx[2]}\n🕒 `{tx[3]}`\n---------------------\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "Rút Tiền":
        if db_user[4] == 1:
            await update.message.reply_text("🚫 Bạn đã bị cấm tính năng rút tiền!")
            return

        bank_info = db_user[2]
        if not bank_info:
            await update.message.reply_text(
                "⚠️ Bạn chưa liên kết tài khoản ngân hàng.\n"
                "Vui lòng gửi câu lệnh liên kết theo cú pháp bên dưới:\n\n"
                "`/lk STK Tên_Ngân_Hàng Tên_Chủ_Thẻ`\n\n"
                "Ví dụ: `/lk 1068030300 VCB NGUYEN CA NGU`",
                parse_mode="Markdown"
            )
        else:
            user_withdraw_state[user.id] = "WAITING_AMOUNT"
            await update.message.reply_text(
                f"💳 **Tài khoản thụ hưởng:** `{bank_info}`\n"
                f"💰 **Số dư:** {db_user[1]:,}đ\n"
                f"📌 **Min rút:** {MIN_WITHDRAW:,}đ - **Max rút:** {MAX_WITHDRAW:,}đ\n\n"
                f"👉 **Vui lòng nhập số tiền bạn muốn rút:**",
                parse_mode="Markdown"
            )

# ================= XỬ LÝ LIÊN KẾT & RÚT TIỀN =================
async def link_bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context): return
    user = update.effective_user
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text("❌ Sai cú pháp! Ví dụ đúng: `/lk 1068030300 VCB NGUYEN CA NGU`", parse_mode="Markdown")
        return

    bank_str = " ".join(context.args)
    db_query("UPDATE users SET bank_info=? WHERE user_id=?", (bank_str, user.id), commit=True)
    await update.message.reply_text(f"✅ **Liên kết thành công!**\nThông tin của bạn: `{bank_str}`", parse_mode="Markdown")

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in user_withdraw_state or user_withdraw_state[user.id] != "WAITING_AMOUNT":
        return False

    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("❌ Số tiền phải là chữ số hợp lệ. Vui lòng nhập lại:")
        return True

    amount = int(text)
    db_user = db_query("SELECT balance, bank_info FROM users WHERE user_id=?", (user.id,), fetchone=True)
    balance, bank_info = db_user[0], db_user[1]

    if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
        await update.message.reply_text(f"❌ Số tiền rút phải từ {MIN_WITHDRAW:,}đ đến {MAX_WITHDRAW:,}đ!")
        return True

    if amount > balance:
        await update.message.reply_text("❌ Số dư của bạn không đủ để thực hiện giao dịch!")
        return True

    # Trừ số dư tạm thời & Tạo lệnh chờ
    db_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user.id), commit=True)
    
    # Thêm vào giao dịch
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (?, ?, ?, ?, ?, ?)",
        (user.id, "Rút Tiền", amount, "Chờ duyệt", get_now_str(), bank_info)
    )
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()

    del user_withdraw_state[user.id]
    await update.message.reply_text("⏳ Đã gửi yêu cầu rút tiền thành công! Vui lòng chờ Admin duyệt.")

    # Gửi yêu cầu duyệt đến Admin
    admin_buttons = [
        [
            InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tx_id}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tx_id}")
        ]
    ]
    username_str = f"@{user.username}" if user.username else str(user.id)
    admin_msg = (
        f"🚨 **YÊU CẦU RÚT TIỀN MỚI (#{tx_id})**\n\n"
        f"👤 **Người rút:** {username_str} (`{user.id}`)\n"
        f"💵 **Số tiền:** {amount:,}đ\n"
        f"🏦 **Thông tin:** `{bank_info}`\n"
        f"🕒 **Thời gian:** `{get_now_str()}`"
    )
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_msg,
        reply_markup=InlineKeyboardMarkup(admin_buttons),
        parse_mode="Markdown"
    )
    return True

# Callback duyệt/từ chối của Admin
async def admin_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data
    action, tx_id = data.split("_")
    tx_id = int(tx_id)

    tx = db_query("SELECT user_id, amount, status FROM transactions WHERE id=?", (tx_id,), fetchone=True)
    if not tx or tx[2] != "Chờ duyệt":
        await query.edit_message_text(f"{query.message.text}\n\n⚠️ Giao dịch này đã được xử lý trước đó!")
        return

    user_id, amount = tx[0], tx[1]

    if action == "approve":
        db_query("UPDATE transactions SET status='Thành công' WHERE id=?", (tx_id,), commit=True)
        await query.edit_message_text(f"{query.message.text}\n\n✅ **TRẠNG THÁI: ĐÃ DUYỆT RÚT**", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=user_id, text=f"🎉 Admin đã **duyệt** yêu cầu rút tiền {amount:,}đ của bạn!", parse_mode="Markdown")
        except Exception:
            pass

    elif action == "reject":
        # Hoàn lại tiền cho user
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id), commit=True)
        db_query("UPDATE transactions SET status='Từ chối' WHERE id=?", (tx_id,), commit=True)
        await query.edit_message_text(f"{query.message.text}\n\n❌ **TRẠNG THÁI: ĐÃ TỪ CHỐI**", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=user_id, text=f"❌ Admin đã **từ chối** yêu cầu rút tiền {amount:,}đ của bạn. Số tiền đã được hoàn lại số dư!", parse_mode="Markdown")
        except Exception:
            pass

# ================= ADMIN COMMANDS =================
async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    cmd = update.message.text.split()[0]
    args = context.args

    if cmd == "/tb":
        if not args:
            await update.message.reply_text("Cú pháp: `/tb Nội dung thông báo`", parse_mode="Markdown")
            return
        content = update.message.text[4:]
        users = db_query("SELECT user_id FROM users", fetchall=True)
        groups = db_query("SELECT chat_id FROM groups", fetchall=True)

        count = 0
        for u in users:
            try:
                await context.bot.send_message(chat_id=u[0], text=f"📢 **THÔNG BÁO:**\n\n{content}", parse_mode="Markdown")
                count += 1
                await asyncio.sleep(0.05)
            except Exception: pass

        for g in groups:
            try:
                await context.bot.send_message(chat_id=g[0], text=f"📢 **THÔNG BÁO:**\n\n{content}", parse_mode="Markdown")
                count += 1
                await asyncio.sleep(0.05)
            except Exception: pass

        await update.message.reply_text(f"✅ Đã gửi thông báo thành công tới {count} người dùng / nhóm!")

    elif cmd == "/info":
        if not args: return
        target_id = int(args[0])
        u = db_query("SELECT * FROM users WHERE user_id=?", (target_id,), fetchone=True)
        if not u:
            await update.message.reply_text("❌ Không tìm thấy user này.")
            return
        msg = (
            f"🔍 **INFO USER:** `{u[0]}`\n"
            f"👤 Username: @{u[1]}\n"
            f"💰 Số dư: {u[2]:,}đ\n"
            f"🏦 Bank: `{u[3]}`\n"
            f"🔗 Người giới thiệu: `{u[4]}`\n"
            f"🚫 Cấm Dùng: {'Có' if u[5] else 'Không'}\n"
            f"🚫 Cấm Rút: {'Có' if u[6] else 'Không'}\n"
            f"🕒 Ngày tham gia: `{u[7]}`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif cmd == "/ban":
        if not args: return
        target_id = int(args[0])
        db_query("UPDATE users SET is_banned=1 WHERE user_id=?", (target_id,), commit=True)
        await update.message.reply_text(f"✅ Đã cấm người dùng `{target_id}` vĩnh viễn.", parse_mode="Markdown")

    elif cmd == "/cam":
        if not args: return
        target_id = int(args[0])
        db_query("UPDATE users SET is_withdraw_banned=1 WHERE user_id=?", (target_id,), commit=True)
        await update.message.reply_text(f"✅ Đã cấm người dùng `{target_id}` rút tiền.", parse_mode="Markdown")

    elif cmd == "/nap":
        if len(args) < 2: return
        target_id, amount = int(args[0]), int(args[1])
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_id), commit=True)
        db_query("INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (?, ?, ?, ?, ?, ?)",
                 (target_id, "Nạp Tiền (Admin)", amount, "Thành công", get_now_str(), "Cộng tiền từ Admin"), commit=True)
        await update.message.reply_text(f"✅ Đã cộng {amount:,}đ cho ID `{target_id}`.", parse_mode="Markdown")

    elif cmd == "/tru":
        if len(args) < 2: return
        target_id, amount = int(args[0]), int(args[1])
        db_query("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, target_id), commit=True)
        db_query("INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (?, ?, ?, ?, ?, ?)",
                 (target_id, "Trừ Tiền (Admin)", amount, "Thành công", get_now_str(), "Trừ tiền từ Admin"), commit=True)
        await update.message.reply_text(f"✅ Đã trừ {amount:,}đ của ID `{target_id}`.", parse_mode="Markdown")

    elif cmd == "/rutls":
        txs = db_query("SELECT id, user_id, amount, details FROM transactions WHERE type='Rút Tiền' AND status='Chờ duyệt'", fetchall=True)
        if not txs:
            await update.message.reply_text("🎉 Không có yêu cầu rút tiền nào đang chờ duyệt!")
            return
        for tx in txs:
            btns = [[InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tx[0]}"), InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tx[0]}")]]
            await update.message.reply_text(f"🆔 **Mã Lệnh:** #{tx[0]}\n👤 **User:** `{tx[1]}`\n💵 **Số tiền:** {tx[2]:,}đ\n🏦 **Bank:** `{tx[3]}`", reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

    elif cmd == "/ruttc":
        txs = db_query("SELECT id, user_id, amount, created_at FROM transactions WHERE type='Rút Tiền' AND status='Thành công' ORDER BY id DESC LIMIT 15", fetchall=True)
        msg = "📜 **CÁC LỆNH RÚT ĐÃ DUYỆT GẦN ĐÂY:**\n\n"
        for tx in txs:
            msg += f"✅ #{tx[0]} | User: `{tx[1]}` | {tx[2]:,}đ | `{tx[3]}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif cmd == "/lsgd":
        if not args: return
        target_id = int(args[0])
        # Lấy danh sách mời
        invited_users = db_query("SELECT user_id, username FROM users WHERE referrer_id=?", (target_id,), fetchall=True)
        msg = f"👥 **DANH SÁCH BẠN BÈ ĐÃ MỜI CỦA ID `{target_id}`:**\n"
        for iu in invited_users:
            uname = f"@{iu[1]}" if iu[1] else "Không username"
            msg += f"- ID: `{iu[0]}` ({uname})\n"
        
        # Lịch sử giao dịch
        txs = db_query("SELECT type, amount, status, created_at FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (target_id,), fetchall=True)
        msg += "\n📜 **LỊCH SỬ GIAO DỊCH:**\n"
        for tx in txs:
            msg += f"- {tx[0]}: {tx[1]:,}đ [{tx[2]}] lúc `{tx[3]}`\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif cmd == "/baotri":
        curr = is_maintenance()
        new_val = "0" if curr else "1"
        db_query("UPDATE settings SET value=? WHERE key='maintenance'", (new_val,), commit=True)
        status_str = "BẮT ĐẦU BẢO TRÌ 🔴" if new_val == "1" else "TẮT BẢO TRÌ 🟢"
        await update.message.reply_text(f"⚙️ Đã thay đổi trạng thái hệ thống: **{status_str}**", parse_mode="Markdown")

# ================= TEXT DISPATCHER =================
async def text_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kiểm tra xem người dùng có đang trong trạng thái nhập số tiền rút không
    is_withdrawing = await handle_withdraw_amount(update, context)
    if not is_withdrawing:
        await menu_handler(update, context)

# ================= MAIN FUNCTION =================
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("lk", link_bank_command))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(admin_withdraw_callback, pattern="^(approve|reject)_"))

    # Admin Command Handlers
    admin_cmds = ["tb", "info", "ban", "cam", "rutls", "ruttc", "nap", "tru", "lsgd", "baotri"]
    for c in admin_cmds:
        app.add_handler(CommandHandler(c, admin_commands))

    # Catch All Messages Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
