import os
import re
import random
import sqlite3
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

INITIAL_OWNER_ID = 8552447077

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000
DEFAULT_REFERRAL_REWARD = 50

DB_FILE = "bot.db"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(
    DB_FILE,
    check_same_thread=False,
)

db.row_factory = sqlite3.Row


def execute(query, params=(), fetchone=False, fetchall=False):
    cur = db.cursor()
    cur.execute(query, params)
    db.commit()

    if fetchone:
        return cur.fetchone()

    if fetchall:
        return cur.fetchall()

    return None


def init_db():
    execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            referrer_id INTEGER,
            blocked INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            receipt_type TEXT,
            receipt_text TEXT,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            destination TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER UNIQUE NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT,
            created_at TEXT
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT,
            file_id TEXT,
            file_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    owner = execute(
        "SELECT value FROM settings WHERE key='owner_id'",
        fetchone=True,
    )

    if not owner:
        execute(
            "INSERT INTO settings(key,value) VALUES('owner_id',?)",
            (str(INITIAL_OWNER_ID),),
        )

    reward = execute(
        "SELECT value FROM settings WHERE key='referral_reward'",
        fetchone=True,
    )

    if not reward:
        execute(
            "INSERT INTO settings(key,value) VALUES('referral_reward',?)",
            (str(DEFAULT_REFERRAL_REWARD),),
        )


def get_owner_id():
    row = execute(
        "SELECT value FROM settings WHERE key='owner_id'",
        fetchone=True,
    )
    return int(row["value"])


def set_owner_id(user_id):
    execute(
        "UPDATE settings SET value=? WHERE key='owner_id'",
        (str(user_id),),
    )


def get_referral_reward():
    row = execute(
        "SELECT value FROM settings WHERE key='referral_reward'",
        fetchone=True,
    )
    return int(row["value"])


def set_referral_reward(amount):
    execute(
        "UPDATE settings SET value=? WHERE key='referral_reward'",
        (str(amount),),
    )


# =========================================================
# USER FUNCTIONS
# =========================================================

def get_user(user_id):
    return execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,),
        fetchone=True,
    )


def get_user_by_username(username):
    username = username.lstrip("@")

    return execute(
        """
        SELECT * FROM users
        WHERE LOWER(username)=LOWER(?)
        """,
        (username,),
        fetchone=True,
    )


def create_or_update_user(tg_user, referrer_id=None):
    existing = get_user(tg_user.id)

    if existing:
        execute(
            """
            UPDATE users
            SET username=?, first_name=?
            WHERE id=?
            """,
            (
                tg_user.username,
                tg_user.first_name,
                tg_user.id,
            ),
        )

        return get_user(tg_user.id)

    valid_referrer = None

    if referrer_id and referrer_id != tg_user.id:
        referrer = get_user(referrer_id)

        if referrer:
            valid_referrer = referrer_id

    execute(
        """
        INSERT INTO users
        (id, username, first_name, balance, referrer_id, blocked, created_at)
        VALUES (?, ?, ?, 0, ?, 0, ?)
        """,
        (
            tg_user.id,
            tg_user.username,
            tg_user.first_name,
            valid_referrer,
            datetime.now().isoformat(),
        ),
    )

    if valid_referrer:
        reward = get_referral_reward()

        # UNIQUE باعث می‌شود یک رفرال دوبار ثبت نشود.
        try:
            execute(
                """
                INSERT INTO referrals
                (referrer_id, referred_id, reward, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    valid_referrer,
                    tg_user.id,
                    reward,
                    datetime.now().isoformat(),
                ),
            )

            execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    reward,
                    valid_referrer,
                ),
            )

            execute(
                """
                INSERT INTO transactions
                (user_id,type,amount,description,created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    valid_referrer,
                    "referral",
                    reward,
                    f"Referral reward: {tg_user.id}",
                    datetime.now().isoformat(),
                ),
            )

        except sqlite3.IntegrityError:
            pass

    return get_user(tg_user.id)


def is_blocked(user_id):
    user = get_user(user_id)
    return bool(user and user["blocked"])


def user_name(user):
    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id):
    rows = [
        ["💸 برداشت", "💰 واریزی"],
        ["💳 موجودی", "🔄 انتقال"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
    ]

    if user_id == get_owner_id():
        rows.append(["🛠 پنل مدیریت"])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["❌ لغو"]],
        resize_keyboard=True,
    )


def admin_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👥 موجودی کاربران",
                callback_data="admin_balances",
            )
        ],
        [
            InlineKeyboardButton(
                "💰 واریزی‌ها",
                callback_data="admin_deposits",
            ),
            InlineKeyboardButton(
                "💸 برداشت‌ها",
                callback_data="admin_withdrawals",
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ افزایش موجودی",
                callback_data="admin_add_balance",
            ),
            InlineKeyboardButton(
                "➖ کاهش موجودی",
                callback_data="admin_remove_balance",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎁 جایزه رفرال",
                callback_data="admin_referral_reward",
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats",
            ),
        ],
        [
            InlineKeyboardButton(
                "🚫 مسدود / آزاد",
                callback_data="admin_block",
            ),
        ],
        [
            InlineKeyboardButton(
                "📢 همگانی",
                callback_data="admin_broadcast",
            ),
        ],
        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_transfer_owner",
            ),
        ],
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    referrer_id = None

    if args:
        value = args[0]

        if value.startswith("ref_"):
            try:
                referrer_id = int(value[4:])
            except ValueError:
                pass

    user = create_or_update_user(
        update.effective_user,
        referrer_id,
    )

    if user["blocked"]:
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به ربات خوش آمدید ❤️\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    await update.message.reply_text(
        f"💳 موجودی\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    context.user_data.clear()
    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        f"💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    amount = int(text)

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریزی {MIN_DEPOSIT:,} DOGS است."
        )
        return

    context.user_data["deposit_amount"] = amount
    context.user_data["state"] = "deposit_receipt"

    await update.message.reply_text(
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"لطفاً مبلغ را واریز کنید:\n\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از واریز، رسید را بفرستید.\n"
        "🖼 عکس یا 📝 متن هر دو قبول است.",
        reply_markup=cancel_keyboard(),
    )


async def deposit_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = context.user_data.get("deposit_amount")

    if not amount:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست منقضی شده است."
        )
        return

    user = create_or_update_user(update.effective_user)

    receipt_type = None
    receipt_text = None
    receipt_file_id = None

    if update.message.photo:
        receipt_type = "photo"
        receipt_file_id = update.message.photo[-1].file_id

    elif update.message.document:
        receipt_type = "document"
        receipt_file_id = update.message.document.file_id

    elif update.message.text:
        receipt_type = "text"
        receipt_text = update.message.text

    else:
        await update.message.reply_text(
            "❌ فقط عکس یا متن رسید ارسال کنید."
        )
        return

    execute(
        """
        INSERT INTO deposits
        (user_id,amount,receipt_type,receipt_text,receipt_file_id,status,created_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            user["id"],
            amount,
            receipt_type,
            receipt_text,
            receipt_file_id,
            "pending",
            datetime.now().isoformat(),
        ),
    )

    deposit_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    owner_id = get_owner_id()

    caption = (
        "💰 درخواست واریزی\n\n"
        f"🆔 #{deposit_id}\n"
        f"👤 {user['first_name']}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}\n"
        f"💰 مبلغ: {amount:,} DOGS"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"deposit_approve:{deposit_id}",
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"deposit_reject:{deposit_id}",
            ),
        ]
    ])

    if receipt_type == "photo":
        await context.bot.send_photo(
            chat_id=owner_id,
            photo=receipt_file_id,
            caption=caption,
            reply_markup=keyboard,
        )

    elif receipt_type == "document":
        await context.bot.send_document(
            chat_id=owner_id,
            document=receipt_file_id,
            caption=caption,
            reply_markup=keyboard,
        )

    else:
        await context.bot.send_message(
            chat_id=owner_id,
            text=caption + f"\n\n📝 رسید:\n{receipt_text}",
            reply_markup=keyboard,
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n"
        "در انتظار بررسی مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if user["balance"] < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n\n"
            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
            f"موجودی: {user['balance']:,} DOGS"
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "withdraw_amount"

    await update.message.reply_text(
        f"💸 مبلغ برداشت را وارد کنید.\n\n"
        f"حداقل: {MIN_WITHDRAW:,} DOGS\n"
        f"موجودی: {user['balance']:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    amount = int(text)
    user = get_user(update.effective_user.id)

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    if amount > user["balance"]:
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    context.user_data["withdraw_amount"] = amount
    context.user_data["state"] = "withdraw_destination"

    await update.message.reply_text(
        "📍 مقصد برداشت را وارد کنید:\n\n"
        "یا آیدی عددی:\n"
        "123456789\n\n"
        "یا یوزرنیم:\n"
        "@username",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    destination = update.message.text.strip()

    if not (
        destination.isdigit()
        or re.fullmatch(
            r"@[A-Za-z0-9_]{5,32}",
            destination,
        )
    ):
        await update.message.reply_text(
            "❌ مقصد نامعتبر است.\n"
            "آیدی عددی یا @username وارد کنید."
        )
        return

    amount = context.user_data.get("withdraw_amount")
    user = get_user(update.effective_user.id)

    if not amount:
        context.user_data.clear()
        return

    if amount > user["balance"]:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # رزرو موجودی تا زمان تصمیم مالک
    execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=? AND balance>=?
        """,
        (
            amount,
            user["id"],
            amount,
        ),
    )

    execute(
        """
        INSERT INTO withdrawals
        (user_id,amount,destination,status,created_at)
        VALUES (?,?,?,?,?)
        """,
        (
            user["id"],
            amount,
            destination,
            "pending",
            datetime.now().isoformat(),
        ),
    )

    withdrawal_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید برداشت",
                callback_data=f"withdraw_approve:{withdrawal_id}",
            ),
            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"withdraw_reject:{withdrawal_id}",
            ),
        ]
    ])

    await context.bot.send_message(
        chat_id=get_owner_id(),
        text=(
            "💸 درخواست برداشت جدید\n\n"
            f"🆔 #{withdrawal_id}\n"
            f"👤 {user['first_name']}\n"
            f"🔢 ID: {user['id']}\n"
            f"📱 {user_name(user)}\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"📍 مقصد: {destination}"
        ),
        reply_markup=keyboard,
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n"
        "در انتظار بررسی مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# TRANSFER
# =========================================================

async def transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    context.user_data.clear()
    context.user_data["state"] = "transfer_destination"

    await update.message.reply_text(
        "🔄 مقصد انتقال را وارد کنید.\n\n"
        "می‌توانید آیدی عددی یا @username وارد کنید.\n"
        "همچنین می‌توانید روی پیام کاربر Reply کنید و فقط مبلغ را بفرستید.",
        reply_markup=cancel_keyboard(),
    )


def find_transfer_receiver(update, text):
    # Reply
    if update.message.reply_to_message:
        replied = update.message.reply_to_message.from_user

        if replied and not replied.is_bot:
            return get_user(replied.id)

    # ID
    if text.isdigit():
        return get_user(int(text))

    # Username
    if text.startswith("@"):
        return get_user_by_username(text)

    return None


async def transfer_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    receiver = find_transfer_receiver(update, text)

    if not receiver:
        # اگر ریپلای باشد و کاربر فقط مقصد نیست، پیام مبلغ است
        if update.message.reply_to_message and text.isdigit():
            receiver = get_user(
                update.message.reply_to_message.from_user.id
            )

            if receiver:
                amount = int(text)

                if amount <= 0:
                    await update.message.reply_text(
                        "❌ مبلغ نامعتبر است."
                    )
                    return

                await complete_transfer(
                    update,
                    context,
                    receiver["id"],
                    amount,
                )
                return

        await update.message.reply_text(
            "❌ کاربر پیدا نشد.\n\n"
            "آیدی عددی یا @username وارد کنید، "
            "یا روی پیام کاربر Reply کنید."
        )
        return

    if receiver["id"] == update.effective_user.id:
        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    context.user_data["transfer_receiver"] = receiver["id"]
    context.user_data["state"] = "transfer_amount"

    await update.message.reply_text(
        f"👤 مقصد: {user_name(receiver)}\n\n"
        "💰 مبلغ انتقال را وارد کنید:",
        reply_markup=cancel_keyboard(),
    )


async def transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    amount = int(text)
    receiver_id = context.user_data.get("transfer_receiver")

    if not receiver_id:
        context.user_data.clear()
        return

    await complete_transfer(
        update,
        context,
        receiver_id,
        amount,
    )


async def complete_transfer(update, context, receiver_id, amount):
    sender_id = update.effective_user.id

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    sender = get_user(sender_id)
    receiver = get_user(receiver_id)

    if not sender or not receiver:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )
        return

    if sender["balance"] < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    if sender_id == receiver_id:
        await update.message.reply_text(
            "❌ انتقال به خودتان ممکن نیست."
        )
        return

    now = datetime.now().isoformat()

    execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=? AND balance>=?
        """,
        (
            amount,
            sender_id,
            amount,
        ),
    )

    execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE id=?
        """,
        (
            amount,
            receiver_id,
        ),
    )

    execute(
        """
        INSERT INTO transfers
        (sender_id,receiver_id,amount,created_at)
        VALUES (?,?,?,?)
        """,
        (
            sender_id,
            receiver_id,
            amount,
            now,
        ),
    )

    execute(
        """
        INSERT INTO transactions
        (user_id,type,amount,description,created_at)
        VALUES (?,?,?,?,?)
        """,
        (
            sender_id,
            "transfer_out",
            -amount,
            f"To {receiver_id}",
            now,
        ),
    )

    execute(
        """
        INSERT INTO transactions
        (user_id,type,amount,description,created_at)
        VALUES (?,?,?,?,?)
        """,
        (
            receiver_id,
            "transfer_in",
            amount,
            f"From {sender_id}",
            now,
        ),
    )

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 مقصد: {user_name(receiver)}",
        reply_markup=main_keyboard(sender_id),
    )

    try:
        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💰 انتقال جدید دریافت کردید.\n\n"
                f"مبلغ: {amount:,} DOGS\n"
                f"از: {user_name(sender)}"
            ),
        )
    except Exception:
        pass


# =========================================================
# REFERRAL
# =========================================================

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start=ref_{user['id']}"
    )

    row = execute(
        """
        SELECT COUNT(*) AS count
        FROM referrals
        WHERE referrer_id=?
        """,
        (user["id"],),
        fetchone=True,
    )

    count = row["count"]

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"👤 تعداد رفرال‌ها: {count}\n"
        f"🎁 پاداش هر رفرال: {get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت شما:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    context.user_data.clear()
    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را برای پشتیبانی ارسال کنید.\n\n"
        "می‌توانید متن یا عکس بفرستید.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    text = update.message.text
    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"

    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"

    elif text:
        file_type = "text"

    else:
        await update.message.reply_text(
            "❌ این نوع پیام پشتیبانی نمی‌شود."
        )
        return

    execute(
        """
        INSERT INTO support_messages
        (user_id,message,file_id,file_type,status,created_at)
        VALUES (?,?,?,?,?,?)
        """,
        (
            user["id"],
            text,
            file_id,
            file_type,
            "pending",
            datetime.now().isoformat(),
        ),
    )

    support_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    caption = (
        "🎧 پیام پشتیبانی\n\n"
        f"🆔 #{support_id}\n"
        f"👤 {user['first_name']}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}"
    )

    if file_type == "photo":
        await context.bot.send_photo(
            chat_id=get_owner_id(),
            photo=file_id,
            caption=caption,
        )

    elif file_type == "document":
        await context.bot.send_document(
            chat_id=get_owner_id(),
            document=file_id,
            caption=caption,
        )

    else:
        await context.bot.send_message(
            chat_id=get_owner_id(),
            text=caption + f"\n\n📝 {text}",
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای پشتیبانی ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["id"] != get_owner_id():
        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )
        return

    await update.message.reply_text(
        "🛠 پنل مدیریت",
        reply_markup=admin_keyboard(),
    )


def admin_only(user_id):
    return user_id == get_owner_id()


# =========================================================
# ADMIN CALLBACKS
# =========================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # -------------------------
    # Deposit approve/reject
    # -------------------------

    if data.startswith("deposit_"):
        if not admin_only(user_id):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        action, id_text = data.split(":")
        deposit_id = int(id_text)

        deposit = execute(
            "SELECT * FROM deposits WHERE id=?",
            (deposit_id,),
            fetchone=True,
        )

        if not deposit:
            await query.answer(
                "درخواست پیدا نشد.",
                show_alert=True,
            )
            return

        if deposit["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )
            return

        if action == "deposit_approve":

            execute(
                """
                UPDATE deposits
                SET status='approved'
                WHERE id=? AND status='pending'
                """,
                (deposit_id,),
            )

            execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    deposit["amount"],
                    deposit["user_id"],
                ),
            )

            execute(
                """
                INSERT INTO transactions
                (user_id,type,amount,description,created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    deposit["user_id"],
                    "deposit",
                    deposit["amount"],
                    f"Deposit #{deposit_id}",
                    datetime.now().isoformat(),
                ),
            )

            await query.edit_message_reply_markup(
                reply_markup=None
            )

            try:
                await context.bot.send_message(
                    chat_id=deposit["user_id"],
                    text=(
                        "✅ واریزی شما تأیید شد.\n\n"
                        f"💰 مبلغ: {deposit['amount']:,} DOGS"
                    ),
                )
            except Exception:
                pass

        else:

            execute(
                """
                UPDATE deposits
                SET status='rejected'
                WHERE id=? AND status='pending'
                """,
                (deposit_id,),
            )

            await query.edit_message_reply_markup(
                reply_markup=None
            )

            try:
                await context.bot.send_message(
                    chat_id=deposit["user_id"],
                    text=(
                        "❌ واریزی شما رد شد.\n\n"
                        f"💰 مبلغ: {deposit['amount']:,} DOGS"
                    ),
                )
            except Exception:
                pass

        return

    # -------------------------
    # Withdrawal
    # -------------------------

    if data.startswith("withdraw_"):
        if not admin_only(user_id):
            await query.answer("⛔ دسترسی ندارید.", show_alert=True)
            return

        action, id_text = data.split(":")
        withdrawal_id = int(id_text)

        withdrawal = execute(
            "SELECT * FROM withdrawals WHERE id=?",
            (withdrawal_id,),
            fetchone=True,
        )

        if not withdrawal:
            await query.answer(
                "درخواست پیدا نشد.",
                show_alert=True,
            )
            return

        if withdrawal["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )
            return

        if action == "withdraw_approve":

            execute(
                """
                UPDATE withdrawals
                SET status='approved'
                WHERE id=? AND status='pending'
                """,
                (withdrawal_id,),
            )

            await query.edit_message_reply_markup(
                reply_markup=None
            )

            try:
                await context.bot.send_message(
                    chat_id=withdrawal["user_id"],
                    text=(
                        "✅ برداشت شما تأیید شد.\n\n"
                        f"💰 مبلغ: {withdrawal['amount']:,} DOGS\n"
                        f"📍 مقصد: {withdrawal['destination']}"
                    ),
                )
            except Exception:
                pass

        else:

            execute(
                """
                UPDATE withdrawals
                SET status='rejected'
                WHERE id=? AND status='pending'
                """,
                (withdrawal_id,),
            )

            # برگرداندن موجودی
            execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    withdrawal["amount"],
                    withdrawal["user_id"],
                ),
            )

            await query.edit_message_reply_markup(
                reply_markup=None
            )

            try:
                await context.bot.send_message(
                    chat_id=withdrawal["user_id"],
                    text=(
                        "❌ برداشت شما رد شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS"
                        " به موجودی شما برگشت."
                    ),
                )
            except Exception:
                pass

        return

    # -------------------------
    # Admin menu
    # -------------------------

    if not admin_only(user_id):
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )
        return

    if data == "admin_balances":
        users = execute(
            """
            SELECT * FROM users
            ORDER BY balance DESC
            """,
            fetchall=True,
        )

        if not users:
            await query.edit_message_text(
                "هیچ کاربری ثبت نشده."
            )
            return

        lines = ["👥 موجودی کاربران\n"]

        for u in users:
            lines.append(
                f"👤 {u['first_name'] or '-'}\n"
                f"🔢 ID: {u['id']}\n"
                f"📱 {('@' + u['username']) if u['username'] else '-'}\n"
                f"💰 {u['balance']:,} DOGS\n"
            )

        # تلگرام محدودیت طول پیام دارد
        text = ""

        for line in lines:
            if len(text) + len(line) > 3800:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                )
                text = ""

            text += line

        if text:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
            )

        return

    if data == "admin_deposits":
        rows = execute(
            """
            SELECT * FROM deposits
            ORDER BY id DESC
            LIMIT 20
            """,
            fetchall=True,
        )

        if not rows:
            await query.message.reply_text(
                "💰 واریزی‌ای وجود ندارد."
            )
            return

        text = "💰 آخرین واریزی‌ها\n\n"

        for d in rows:
            text += (
                f"#{d['id']} | "
                f"{d['amount']:,} DOGS | "
                f"{d['status']} | "
                f"ID: {d['user_id']}\n"
            )

        await query.message.reply_text(text)
        return

    if data == "admin_withdrawals":
        rows = execute(
            """
            SELECT * FROM withdrawals
            ORDER BY id DESC
            LIMIT 20
            """,
            fetchall=True,
        )

        if not rows:
            await query.message.reply_text(
                "💸 برداشتی وجود ندارد."
            )
            return

        text = "💸 آخرین برداشت‌ها\n\n"

        for w in rows:
            text += (
                f"#{w['id']} | "
                f"{w['amount']:,} DOGS | "
                f"{w['status']} | "
                f"ID: {w['user_id']}\n"
            )

        await query.message.reply_text(text)
        return

    if data == "admin_stats":
        users = execute(
            "SELECT COUNT(*) AS c FROM users",
            fetchone=True,
        )["c"]

        total_balance = execute(
            "SELECT COALESCE(SUM(balance),0) AS s FROM users",
            fetchone=True,
        )["s"]

        referrals_count = execute(
            "SELECT COUNT(*) AS c FROM referrals",
            fetchone=True,
        )["c"]

        await query.message.reply_text(
            "📊 آمار\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"👥 رفرال‌ها: {referrals_count}\n"
            f"🎁 جایزه فعلی رفرال: {get_referral_reward():,} DOGS"
        )

        return

    if data == "admin_referral_reward":
        context.user_data.clear()
        context.user_data["state"] = "admin_referral_reward"

        await query.message.reply_text(
            f"🎁 جایزه فعلی: {get_referral_reward():,} DOGS\n\n"
            "مقدار جدید را به صورت عدد وارد کنید:"
        )

        return

    if data == "admin_transfer_owner":
        context.user_data.clear()
        context.user_data["state"] = "admin_transfer_owner"

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را وارد کنید.\n\n"
            "انتقال مستقیم انجام می‌شود."
        )

        return

    if data == "admin_add_balance":
        context.user_data.clear()
        context.user_data["state"] = "admin_add_balance"

        await query.message.reply_text(
            "➕ به این شکل ارسال کنید:\n\n"
            "123456789 5000"
        )

        return

    if data == "admin_remove_balance":
        context.user_data.clear()
        context.user_data["state"] = "admin_remove_balance"

        await query.message.reply_text(
            "➖ به این شکل ارسال کنید:\n\n"
            "123456789 5000"
        )

        return

    if data == "admin_block":
        context.user_data.clear()
        context.user_data["state"] = "admin_block"

        await query.message.reply_text(
            "🚫 برای مسدود/آزاد کردن:\n\n"
            "123456789"
        )

        return

    if data == "admin_broadcast":
        context.user_data.clear()
        context.user_data["state"] = "admin_broadcast"

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید."
        )

        return


# =========================================================
# ADMIN TEXT ACTIONS
# =========================================================

async def admin_state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if not user or user["id"] != get_owner_id():
        return False

    state = context.user_data.get("state")

    if not state:
        return False

    text = update.message.text.strip()

    if state == "admin_referral_reward":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )
            return True

        amount = int(text)

        if amount < 0:
            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return True

        set_referral_reward(amount)
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 مقدار جدید: {amount:,} DOGS",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    if state == "admin_transfer_owner":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        new_owner = int(text)

        if not get_user(new_owner):
            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را /start نکرده است."
            )
            return True

        old_owner = get_owner_id()

        set_owner_id(new_owner)
        context.user_data.clear()

        await update.message.reply_text(
            f"👑 مالکیت منتقل شد.\n\n"
            f"مالک جدید: {new_owner}"
        )

        try:
            await context.bot.send_message(
                chat_id=new_owner,
                text=(
                    "👑 شما مالک جدید ربات شدید.\n"
                    "پنل مدیریت برای شما فعال شد."
                ),
                reply_markup=main_keyboard(new_owner),
            )
        except Exception:
            pass

        logger.info(
            "Ownership transferred from %s to %s",
            old_owner,
            new_owner,
        )

        return True

    if state in ("admin_add_balance", "admin_remove_balance"):

        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text(
                "❌ فرمت صحیح:\n123456789 5000"
            )
            return True

        if not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text(
                "❌ ID و مبلغ باید عدد باشند."
            )
            return True

        target_id = int(parts[0])
        amount = int(parts[1])

        target = get_user(target_id)

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return True

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ نامعتبر است."
            )
            return True

        if state == "admin_add_balance":

            execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    amount,
                    target_id,
                ),
            )

            transaction_amount = amount
            transaction_type = "admin_add"

            message = (
                f"✅ {amount:,} DOGS به موجودی "
                f"{target_id} اضافه شد."
            )

        else:

            if target["balance"] < amount:
                await update.message.reply_text(
                    "❌ موجودی کاربر کافی نیست."
                )
                return True

            execute(
                """
                UPDATE users
                SET balance=balance-?
                WHERE id=?
                """,
                (
                    amount,
                    target_id,
                ),
            )

            transaction_amount = -amount
            transaction_type = "admin_remove"

            message = (
                f"✅ {amount:,} DOGS از موجودی "
                f"{target_id} کم شد."
            )

        execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                target_id,
                transaction_type,
                transaction_amount,
                "Admin balance change",
                datetime.now().isoformat(),
            ),
        )

        context.user_data.clear()

        await update.message.reply_text(
            message,
            reply_markup=main_keyboard(user["id"]),
        )

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=message,
            )
        except Exception:
            pass

        return True

    if state == "admin_block":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ ID عددی وارد کنید."
            )
            return True

        target_id = int(text)
        target = get_user(target_id)

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return True

        new_status = 0 if target["blocked"] else 1

        execute(
            """
            UPDATE users
            SET blocked=?
            WHERE id=?
            """,
            (
                new_status,
                target_id,
            ),
        )

        context.user_data.clear()

        status_text = (
            "مسدود شد"
            if new_status
            else "آزاد شد"
        )

        await update.message.reply_text(
            f"✅ کاربر {target_id} {status_text}.",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    if state == "admin_broadcast":

        users = execute(
            "SELECT id FROM users WHERE blocked=0",
            fetchall=True,
        )

        sent = 0

        for target in users:
            try:
                await context.bot.copy_message(
                    chat_id=target["id"],
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )

                sent += 1

            except Exception:
                pass

        context.user_data.clear()

        await update.message.reply_text(
            f"📢 پیام همگانی ارسال شد.\n"
            f"👥 ارسال موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    return False


# =========================================================
# CANCEL
# =========================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    context.user_data.clear()

    await update.message.reply_text(
        "❌ لغو شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    # Admin states
    if await admin_state_handler(update, context):
        return

    state = context.user_data.get("state")

    if state == "deposit_amount":
        await deposit_amount(update, context)
        return

    if state == "deposit_receipt":
        await deposit_receipt(update, context)
        return

    if state == "withdraw_amount":
        await withdraw_amount(update, context)
        return

    if state == "withdraw_destination":
        await withdraw_destination(update, context)
        return

    if state == "transfer_destination":
        await transfer_destination(update, context)
        return

    if state == "transfer_amount":
        await transfer_amount(update, context)
        return

    if state == "support":
        await support_message(update, context)
        return

    # Main buttons
    text = update.message.text.strip()

    if text == "💳 موجودی" or text == "موجودی":
        await balance(update, context)
        return

    if text == "💰 واریزی":
        await deposit_start(update, context)
        return

    if text == "💸 برداشت":
        await withdraw_start(update, context)
        return

    if text == "🔄 انتقال":
        await transfer_start(update, context)
        return

    if text == "👥 زیرمجموعه":
        await referrals(update, context)
        return

    if text == "🎧 پشتیبانی":
        await support_start(update, context)
        return

    if text == "🛠 پنل مدیریت":
        await admin_panel(update, context)
        return

    # Group commands
    if text.startswith("انتقال "):
        parts = text.split(maxsplit=2)

        if len(parts) == 2 and update.message.reply_to_message:
            amount_text = parts[1]

            if amount_text.isdigit():
                receiver = get_user(
                    update.message.reply_to_message.from_user.id
                )

                if receiver:
                    await complete_transfer(
                        update,
                        context,
                        receiver["id"],
                        int(amount_text),
                    )
                    return

        if len(parts) == 3:
            destination = parts[1]
            amount_text = parts[2]

            if amount_text.isdigit():
                receiver = find_transfer_receiver(
                    update,
                    destination,
                )

                if receiver:
                    await complete_transfer(
                        update,
                        context,
                        receiver["id"],
                        int(amount_text),
                    )
                    return

        await update.message.reply_text(
            "❌ فرمت انتقال:\n\n"
            "انتقال @username 5000\n"
            "یا\n"
            "انتقال 123456789 5000\n\n"
            "یا روی پیام کاربر Reply کنید:\n"
            "انتقال 5000"
        )


# =========================================================
# MAIN
# =========================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            deposit_or_support_media,
        )
    )

    logger.info("BOT STARTED")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


async def deposit_or_support_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    state = context.user_data.get("state")

    if state == "deposit_receipt":
        await deposit_receipt(update, context)
        return

    if state == "support":
        await support_message(update, context)
        return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


if __name__ == "__main__":
    main()
