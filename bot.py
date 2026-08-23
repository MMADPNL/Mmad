import os
import re
import random
import sqlite3
import logging
import threading
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
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

DB_FILE = "bot.db"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DEFAULT_REFERRAL_REWARD = 50

# Game
GAME_ENTRY = 500
GAME_WINNER_PRIZE = 900
GAME_OWNER_FEE = 50

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

db_lock = threading.RLock()


def execute(query, params=(), fetchone=False, fetchall=False):
    with db_lock:
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
            phone_verified INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # Migration for old databases
    columns = execute(
        "PRAGMA table_info(users)",
        fetchall=True,
    )

    column_names = {row["name"] for row in columns}

    if "phone_verified" not in column_names:
        execute(
            "ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0"
        )

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

    execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER,
            creator_id INTEGER NOT NULL,
            opponent_id INTEGER,
            entry INTEGER NOT NULL,
            winner_id INTEGER,
            loser_id INTEGER,
            owner_fee INTEGER DEFAULT 0,
            status TEXT DEFAULT 'waiting',
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

    # Internal game wallet of owner
    game_wallet = execute(
        "SELECT value FROM settings WHERE key='game_wallet'",
        fetchone=True,
    )

    if not game_wallet:
        execute(
            "INSERT INTO settings(key,value) VALUES('game_wallet','0')"
        )


# =========================================================
# SETTINGS
# =========================================================

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


def get_game_wallet():
    row = execute(
        "SELECT value FROM settings WHERE key='game_wallet'",
        fetchone=True,
    )
    return int(row["value"])


def set_game_wallet(amount):
    execute(
        "UPDATE settings SET value=? WHERE key='game_wallet'",
        (str(max(0, amount)),),
    )


def add_game_wallet(amount):
    set_game_wallet(get_game_wallet() + amount)


# =========================================================
# USER
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
        (
            id,
            username,
            first_name,
            balance,
            referrer_id,
            blocked,
            phone_verified,
            created_at
        )
        VALUES (?, ?, ?, 0, ?, 0, 0, ?)
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

        try:

            execute(
                """
                INSERT INTO referrals
                (
                    referrer_id,
                    referred_id,
                    reward,
                    created_at
                )
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
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
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


def is_verified(user_id):
    user = get_user(user_id)

    return bool(user and user["phone_verified"])


def user_name(user):

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


# =========================================================
# PHONE VERIFICATION
# =========================================================

def phone_keyboard():

    keyboard = [
        [
            KeyboardButton(
                "📱 تأیید شماره تلفن",
                request_contact=True,
            )
        ]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_keyboard(user_id):

    rows = [
        ["💸 برداشت", "💰 واریزی"],
        ["💳 موجودی", "🔄 انتقال"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
        ["🎮 بازی"],
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


# =========================================================
# PHONE CONTACT
# =========================================================

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.contact:
        return

    tg_user = update.effective_user
    contact = update.message.contact

    user = create_or_update_user(tg_user)

    if contact.user_id != tg_user.id:
        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را با دکمه تأیید کنید."
        )
        return

    execute(
        """
        UPDATE users
        SET phone_verified=1
        WHERE id=?
        """,
        (tg_user.id,),
    )

    await update.message.reply_text(
        "✅ شماره تلفن شما با موفقیت تأیید شد.",
        reply_markup=main_keyboard(user["id"]),
    )


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

    if not user["phone_verified"]:

        await update.message.reply_text(
            "سلام 👋\n\n"
            "برای استفاده از ربات ابتدا شماره تلفن خود را تأیید کنید.",
            reply_markup=phone_keyboard(),
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
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    await update.message.reply_text(
        "💳 موجودی شما\n\n"
        f"🐶 {user['balance']:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if not is_verified(user["id"]):
        await update.message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.",
            reply_markup=phone_keyboard(),
        )
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
        "لطفاً مبلغ را واریز کنید و سپس رسید را ارسال کنید.\n\n"
        "🖼 عکس یا 📝 متن رسید قبول است.",
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
            "❌ فقط عکس، فایل یا متن رسید ارسال کنید."
        )
        return

    execute(
        """
        INSERT INTO deposits
        (
            user_id,
            amount,
            receipt_type,
            receipt_text,
            receipt_file_id,
            status,
            created_at
        )
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

    owner_id = get_owner_id()

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

    if not is_verified(user["id"]):

        await update.message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.",
            reply_markup=phone_keyboard(),
        )
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
        "آیدی عددی یا @username",
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
            "❌ مقصد نامعتبر است."
        )
        return

    amount = context.user_data.get("withdraw_amount")

    user = get_user(update.effective_user.id)

    if not amount:

        context.user_data.clear()
        return

    # Atomic reserve
    cur = db.cursor()

    with db_lock:

        cur.execute(
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

        if cur.rowcount != 1:

            db.rollback()

            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )
            return

        cur.execute(
            """
            INSERT INTO withdrawals
            (
                user_id,
                amount,
                destination,
                status,
                created_at
            )
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

        withdrawal_id = cur.lastrowid

        db.commit()

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

    if not is_verified(user["id"]):

        await update.message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.",
            reply_markup=phone_keyboard(),
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "transfer_destination"

    await update.message.reply_text(
        "🔄 مقصد انتقال را وارد کنید.\n\n"
        "@username یا ID عددی\n\n"
        "یا روی پیام کاربر Reply کنید و مبلغ را بفرستید.",
        reply_markup=cancel_keyboard(),
    )


def find_transfer_receiver(update, text):

    if update.message.reply_to_message:

        replied = update.message.reply_to_message.from_user

        if replied and not replied.is_bot:

            return get_user(replied.id)

    if text.isdigit():

        return get_user(int(text))

    if text.startswith("@"):

        return get_user_by_username(text)

    return None


async def transfer_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    receiver = find_transfer_receiver(update, text)

    # Reply + amount
    if update.message.reply_to_message and text.isdigit():

        receiver = get_user(
            update.message.reply_to_message.from_user.id
        )

        if receiver:

            await complete_transfer(
                update,
                context,
                receiver["id"],
                int(text),
            )
            return

    if not receiver:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد.\n\n"
            "ID یا @username وارد کنید."
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

    receiver_id = context.user_data.get("transfer_receiver")

    if not receiver_id:

        context.user_data.clear()
        return

    await complete_transfer(
        update,
        context,
        receiver_id,
        int(text),
    )


async def complete_transfer(
    update,
    context,
    receiver_id,
    amount,
):

    sender_id = update.effective_user.id

    if amount <= 0:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    receiver = get_user(receiver_id)

    if not receiver:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )
        return

    if receiver_id == sender_id:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    if receiver["blocked"]:

        await update.message.reply_text(
            "❌ مقصد مسدود است."
        )
        return

    # Atomic transfer
    with db_lock:

        cur = db.cursor()

        try:

            cur.execute("BEGIN")

            cur.execute(
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

            if cur.rowcount != 1:

                db.rollback()

                await update.message.reply_text(
                    "❌ موجودی کافی نیست."
                )
                return

            cur.execute(
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

            cur.execute(
                """
                INSERT INTO transfers
                (
                    sender_id,
                    receiver_id,
                    amount,
                    created_at
                )
                VALUES (?,?,?,?)
                """,
                (
                    sender_id,
                    receiver_id,
                    amount,
                    datetime.now().isoformat(),
                ),
            )

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    sender_id,
                    "transfer_out",
                    -amount,
                    f"To {receiver_id}",
                    datetime.now().isoformat(),
                ),
            )

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    receiver_id,
                    "transfer_in",
                    amount,
                    f"From {sender_id}",
                    datetime.now().isoformat(),
                ),
            )

            db.commit()

        except Exception:

            db.rollback()

            logger.exception("Transfer failed")

            await update.message.reply_text(
                "❌ انتقال انجام نشد."
            )
            return

    sender = get_user(sender_id)

    context.user_data.clear()

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"🐶 مبلغ: {amount:,} DOGS\n"
        f"👤 مقصد: {user_name(receiver)}\n"
        f"💳 موجودی جدید: {sender['balance']:,} DOGS",
        reply_markup=main_keyboard(sender_id),
    )

    try:

        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💰 انتقال جدید دریافت کردید.\n\n"
                f"🐶 مبلغ: {amount:,} DOGS\n"
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

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"👤 تعداد: {row['count']}\n"
        f"🎁 پاداش هر نفر: {get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
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
        "متن، عکس یا فایل قابل ارسال است.",
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
        (
            user_id,
            message,
            file_id,
            file_type,
            status,
            created_at
        )
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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 پاسخ",
                callback_data=f"support_reply:{support_id}",
            ),
            InlineKeyboardButton(
                "✅ بسته شد",
                callback_data=f"support_close:{support_id}",
            ),
        ]
    ])

    owner_id = get_owner_id()

    if file_type == "photo":

        await context.bot.send_photo(
            chat_id=owner_id,
            photo=file_id,
            caption=caption,
            reply_markup=keyboard,
        )

    elif file_type == "document":

        await context.bot.send_document(
            chat_id=owner_id,
            document=file_id,
            caption=caption,
            reply_markup=keyboard,
        )

    else:

        await context.bot.send_message(
            chat_id=owner_id,
            text=caption + f"\n\n📝 {text}",
            reply_markup=keyboard,
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای مالک ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# GAME
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=f"game_join:{game_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"game_cancel:{game_id}",
            )
        ],
    ])


async def game_create(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if not is_verified(user["id"]):

        await update.message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.",
            reply_markup=phone_keyboard(),
        )
        return

    if user["balance"] < GAME_ENTRY:

        await update.message.reply_text(
            f"❌ برای بازی حداقل "
            f"{GAME_ENTRY:,} DOGS لازم دارید.\n\n"
            f"موجودی شما: {user['balance']:,} DOGS"
        )
        return

    # Prevent multiple active games by same creator
    active = execute(
        """
        SELECT id
        FROM games
        WHERE creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if active:

        await update.message.reply_text(
            "❌ شما یک بازی در انتظار ورود بازیکن دارید."
        )
        return

    game_id = execute(
        """
        INSERT INTO games
        (
            chat_id,
            message_id,
            creator_id,
            entry,
            status,
            created_at
        )
        VALUES (?,?,?,?,?,?)
        """,
        (
            update.effective_chat.id,
            None,
            user["id"],
            GAME_ENTRY,
            "waiting",
            datetime.now().isoformat(),
        ),
    )

    # Last insert
    game_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    message = await update.message.reply_text(
        "🎮 بازی 500 DOGS\n\n"
        f"👤 سازنده: {user_name(user)}\n"
        f"💰 ورود: {GAME_ENTRY:,} DOGS\n"
        "🏆 جایزه برنده: 900 DOGS\n"
        f"👑 سهم مالک: {GAME_OWNER_FEE:,} DOGS\n\n"
        "یک نفر برای ورود روی دکمه بزند.",
        reply_markup=game_keyboard(game_id),
    )

    execute(
        """
        UPDATE games
        SET message_id=?
        WHERE id=?
        """,
        (
            message.message_id,
            game_id,
        ),
    )


async def game_join(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):

    query = update.callback_query
    user = create_or_update_user(query.from_user)

    if user["blocked"]:

        await query.answer(
            "🚫 حساب شما مسدود است.",
            show_alert=True,
        )
        return

    if not is_verified(user["id"]):

        await query.answer(
            "ابتدا شماره خود را تأیید کنید.",
            show_alert=True,
        )
        return

    with db_lock:

        cur = db.cursor()

        try:

            cur.execute("BEGIN IMMEDIATE")

            game = cur.execute(
                """
                SELECT *
                FROM games
                WHERE id=?
                """,
                (game_id,),
            ).fetchone()

            if not game:

                db.rollback()

                await query.answer(
                    "بازی پیدا نشد.",
                    show_alert=True,
                )
                return

            if game["status"] != "waiting":

                db.rollback()

                await query.answer(
                    "این بازی قبلاً شروع شده یا تمام شده.",
                    show_alert=True,
                )
                return

            if game["creator_id"] == user["id"]:

                db.rollback()

                await query.answer(
                    "نمی‌توانید وارد بازی خودتان شوید.",
                    show_alert=True,
                )
                return

            # Check balance of both
            creator = cur.execute(
                "SELECT * FROM users WHERE id=?",
                (game["creator_id"],),
            ).fetchone()

            opponent = cur.execute(
                "SELECT * FROM users WHERE id=?",
                (user["id"],),
            ).fetchone()

            if not creator or not opponent:

                db.rollback()

                await query.answer(
                    "کاربر پیدا نشد.",
                    show_alert=True,
                )
                return

            if creator["balance"] < GAME_ENTRY:

                cur.execute(
                    """
                    UPDATE games
                    SET status='cancelled'
                    WHERE id=? AND status='waiting'
                    """,
                    (game_id,),
                )

                db.commit()

                await query.answer(
                    "موجودی سازنده بازی کافی نیست.",
                    show_alert=True,
                )

                return

            if opponent["balance"] < GAME_ENTRY:

                db.rollback()

                await query.answer(
                    f"حداقل {GAME_ENTRY:,} DOGS لازم دارید.",
                    show_alert=True,
                )
                return

            # Reserve both entries
            cur.execute(
                """
                UPDATE users
                SET balance=balance-?
                WHERE id=? AND balance>=?
                """,
                (
                    GAME_ENTRY,
                    creator["id"],
                    GAME_ENTRY,
                ),
            )

            if cur.rowcount != 1:

                db.rollback()

                await query.answer(
                    "موجودی سازنده کافی نیست.",
                    show_alert=True,
                )
                return

            cur.execute(
                """
                UPDATE users
                SET balance=balance-?
                WHERE id=? AND balance>=?
                """,
                (
                    GAME_ENTRY,
                    opponent["id"],
                    GAME_ENTRY,
                ),
            )

            if cur.rowcount != 1:

                db.rollback()

                await query.answer(
                    "موجودی شما کافی نیست.",
                    show_alert=True,
                )
                return

            # Random winner
            winner_id, loser_id = random.sample(
                [creator["id"], opponent["id"]],
                2,
            )

            # Winner gets 900
            cur.execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    GAME_WINNER_PRIZE,
                    winner_id,
                ),
            )

            # Owner gets 50 internal points
            owner_id = get_owner_id()

            cur.execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    GAME_OWNER_FEE,
                    owner_id,
                ),
            )

            # Game wallet accounting
            current_wallet = get_game_wallet()

            # 50 from game pool goes to owner.
            # Since 1000 entered and 950 distributed,
            # 50 remains system reserve.
            cur.execute(
                """
                UPDATE games
                SET
                    opponent_id=?,
                    winner_id=?,
                    loser_id=?,
                    owner_fee=?,
                    status='finished'
                WHERE id=? AND status='waiting'
                """,
                (
                    opponent["id"],
                    winner_id,
                    loser_id,
                    GAME_OWNER_FEE,
                    game_id,
                ),
            )

            if cur.rowcount != 1:

                db.rollback()

                await query.answer(
                    "بازی همزمان توسط درخواست دیگری شروع شد.",
                    show_alert=True,
                )
                return

            # Transactions
            now = datetime.now().isoformat()

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    creator["id"],
                    "game_entry",
                    -GAME_ENTRY,
                    f"Game #{game_id}",
                    now,
                ),
            )

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    opponent["id"],
                    "game_entry",
                    -GAME_ENTRY,
                    f"Game #{game_id}",
                    now,
                ),
            )

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    winner_id,
                    "game_win",
                    GAME_WINNER_PRIZE,
                    f"Game #{game_id}",
                    now,
                ),
            )

            cur.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    owner_id,
                    "game_owner_fee",
                    GAME_OWNER_FEE,
                    f"Game #{game_id}",
                    now,
                ),
            )

            db.commit()

        except Exception:

            db.rollback()

            logger.exception("Game failed")

            await query.answer(
                "❌ خطا در اجرای بازی.",
                show_alert=True,
            )
            return

    winner = get_user(winner_id)
    loser = get_user(loser_id)

    await query.answer("🎮 بازی شروع شد!")

    try:

        await query.edit_message_text(
            "🎮 بازی تمام شد!\n\n"
            f"🏆 برنده: {user_name(winner)}\n"
            f"😔 بازنده: {user_name(loser)}\n\n"
            f"🏆 جایزه برنده: {GAME_WINNER_PRIZE:,} DOGS\n"
            f"👑 سهم مالک: {GAME_OWNER_FEE:,} DOGS"
        )

    except Exception:
        pass

    # PV winner
    try:

        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 تبریک!\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 جایزه: {GAME_WINNER_PRIZE:,} DOGS\n"
                f"💳 موجودی فعلی: {winner['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass

    # PV loser
    try:

        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "😔 شما در بازی باختید.\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 مبلغ بازی: {GAME_ENTRY:,} DOGS\n"
                f"💳 موجودی فعلی: {loser['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass


async def game_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game_id,
):

    query = update.callback_query
    user = create_or_update_user(query.from_user)

    with db_lock:

        cur = db.cursor()

        game = cur.execute(
            """
            SELECT *
            FROM games
            WHERE id=?
            """,
            (game_id,),
        ).fetchone()

        if not game:

            await query.answer(
                "بازی پیدا نشد.",
                show_alert=True,
            )
            return

        if game["status"] != "waiting":

            await query.answer(
                "این بازی قبلاً شروع شده.",
                show_alert=True,
            )
            return

        if game["creator_id"] != user["id"]:

            await query.answer(
                "فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True,
            )
            return

        cur.execute(
            """
            UPDATE games
            SET status='cancelled'
            WHERE id=? AND status='waiting'
            """,
            (game_id,),
        )

        db.commit()

    await query.answer("لغو شد.")

    try:

        await query.edit_message_text(
            "❌ بازی توسط سازنده لغو شد."
        )

    except Exception:
        pass


# =========================================================
# ADMIN KEYBOARD
# =========================================================

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
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 مسدود / آزاد",
                callback_data="admin_block",
            )
        ],
        [
            InlineKeyboardButton(
                "📢 همگانی",
                callback_data="admin_broadcast",
            )
        ],
        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_transfer_owner",
            )
        ],
    ])


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
# CALLBACK
# =========================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # =====================================================
    # GAME
    # =====================================================

    if data.startswith("game_join:"):

        game_id = int(data.split(":")[1])

        await game_join(
            update,
            context,
            game_id,
        )
        return

    if data.startswith("game_cancel:"):

        game_id = int(data.split(":")[1])

        await game_cancel(
            update,
            context,
            game_id,
        )
        return

    # =====================================================
    # SUPPORT
    # =====================================================

    if data.startswith("support_reply:"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        support_id = int(data.split(":")[1])

        support = execute(
            """
            SELECT *
            FROM support_messages
            WHERE id=?
            """,
            (support_id,),
            fetchone=True,
        )

        if not support:

            await query.answer(
                "پیام پیدا نشد.",
                show_alert=True,
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "support_admin_reply"
        context.user_data["support_id"] = support_id
        context.user_data["support_user_id"] = support["user_id"]

        await query.message.reply_text(
            f"💬 پاسخ به پیام #{support_id}\n\n"
            "پاسخ خود را ارسال کنید:"
        )
        return

    if data.startswith("support_close:"):

        if not admin_only(user_id):
            return

        support_id = int(data.split(":")[1])

        execute(
            """
            UPDATE support_messages
            SET status='closed'
            WHERE id=?
            """,
            (support_id,),
        )

        await query.edit_message_reply_markup(
            reply_markup=None
        )

        return

    # =====================================================
    # DEPOSIT
    # =====================================================

    if data.startswith("deposit_"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        action, id_text = data.split(":")
        deposit_id = int(id_text)

        deposit = execute(
            """
            SELECT *
            FROM deposits
            WHERE id=?
            """,
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

            updated = execute(
                """
                UPDATE deposits
                SET status='approved'
                WHERE id=? AND status='pending'
                """,
                (deposit_id,),
            )

            if not updated:

                await query.answer(
                    "قبلاً بررسی شده.",
                    show_alert=True,
                )
                return

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
                (
                    user_id,
                    type,
                    amount,
                    description,
                    created_at
                )
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
                        "✅ واریزی تأیید شد.\n\n"
                        f"🐶 {deposit['amount']:,} DOGS"
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
                    text="❌ واریزی شما رد شد.",
                )

            except Exception:
                pass

        return

    # =====================================================
    # WITHDRAW
    # =====================================================

    if data.startswith("withdraw_"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        action, id_text = data.split(":")
        withdrawal_id = int(id_text)

        withdrawal = execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id=?
            """,
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
                "قبلاً بررسی شده.",
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
                        "✅ برداشت تأیید شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS\n"
                        f"📍 {withdrawal['destination']}"
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
                        "❌ برداشت رد شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS "
                        "به موجودی برگشت."
                    ),
                )

            except Exception:
                pass

        return

    # =====================================================
    # ADMIN
    # =====================================================

    if not admin_only(user_id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )
        return

    if data == "admin_balances":

        users = execute(
            """
            SELECT *
            FROM users
            ORDER BY balance DESC
            """,
            fetchall=True,
        )

        if not users:

            await query.message.reply_text(
                "هیچ کاربری ثبت نشده."
            )
            return

        text = "👥 موجودی کاربران\n\n"

        for u in users:

            line = (
                f"👤 {u['first_name'] or '-'}\n"
                f"🔢 {u['id']}\n"
                f"📱 {('@' + u['username']) if u['username'] else '-'}\n"
                f"🐶 {u['balance']:,} DOGS\n\n"
            )

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
            SELECT *
            FROM deposits
            ORDER BY id DESC
            LIMIT 20
            """,
            fetchall=True,
        )

        text = "💰 واریزی‌های اخیر\n\n"

        for d in rows:

            text += (
                f"#{d['id']} | "
                f"{d['amount']:,} DOGS | "
                f"{d['status']} | "
                f"ID:{d['user_id']}\n"
            )

        await query.message.reply_text(text)
        return

    if data == "admin_withdrawals":

        rows = execute(
            """
            SELECT *
            FROM withdrawals
            ORDER BY id DESC
            LIMIT 20
            """,
            fetchall=True,
        )

        text = "💸 برداشت‌های اخیر\n\n"

        for w in rows:

            text += (
                f"#{w['id']} | "
                f"{w['amount']:,} DOGS | "
                f"{w['status']} | "
                f"ID:{w['user_id']}\n"
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

        games = execute(
            """
            SELECT COUNT(*) AS c
            FROM games
            WHERE status='finished'
            """,
            fetchone=True,
        )["c"]

        await query.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {users}\n"
            f"🐶 مجموع موجودی: {total_balance:,} DOGS\n"
            f"👥 رفرال: {referrals_count}\n"
            f"🎮 بازی‌های انجام‌شده: {games}\n"
            f"🎁 جایزه رفرال: {get_referral_reward():,} DOGS\n"
            f"👑 سهم مالک هر بازی: {GAME_OWNER_FEE:,} DOGS"
        )

        return

    if data == "admin_referral_reward":

        context.user_data.clear()
        context.user_data["state"] = "admin_referral_reward"

        await query.message.reply_text(
            f"🎁 مقدار فعلی: {get_referral_reward():,}\n\n"
            "مقدار جدید را وارد کنید:"
        )

        return

    if data == "admin_add_balance":

        context.user_data.clear()
        context.user_data["state"] = "admin_add_balance"

        await query.message.reply_text(
            "➕ فرمت:\n\n"
            "123456789 5000"
        )

        return

    if data == "admin_remove_balance":

        context.user_data.clear()
        context.user_data["state"] = "admin_remove_balance"

        await query.message.reply_text(
            "➖ فرمت:\n\n"
            "123456789 5000"
        )

        return

    if data == "admin_block":

        context.user_data.clear()
        context.user_data["state"] = "admin_block"

        await query.message.reply_text(
            "🚫 ID کاربر را وارد کنید:"
        )

        return

    if data == "admin_broadcast":

        context.user_data.clear()
        context.user_data["state"] = "admin_broadcast"

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید:"
        )

        return

    if data == "admin_transfer_owner":

        context.user_data.clear()
        context.user_data["state"] = "admin_transfer_owner"

        await query.message.reply_text(
            "👑 ID مالک جدید:"
        )

        return


# =========================================================
# ADMIN STATE
# =========================================================

async def admin_state_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = get_user(update.effective_user.id)

    if not user:
        return False

    state = context.user_data.get("state")

    # Support admin reply can be used by owner only
    if state == "support_admin_reply":

        if user["id"] != get_owner_id():
            context.user_data.clear()
            return False

        target_id = context.user_data.get(
            "support_user_id"
        )

        support_id = context.user_data.get(
            "support_id"
        )

        if not target_id or not support_id:
            context.user_data.clear()
            return False

        text = update.message.text

        if not text:
            await update.message.reply_text(
                "❌ فعلاً فقط پاسخ متنی ارسال کنید."
            )
            return True

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎧 پاسخ پشتیبانی\n\n"
                    f"{text}"
                ),
            )

            execute(
                """
                UPDATE support_messages
                SET status='answered'
                WHERE id=?
                """,
                (support_id,),
            )

            context.user_data.clear()

            await update.message.reply_text(
                "✅ پاسخ ارسال شد.",
                reply_markup=main_keyboard(user["id"]),
            )

        except Exception:

            await update.message.reply_text(
                "❌ ارسال پاسخ انجام نشد."
            )

        return True

    if user["id"] != get_owner_id():
        return False

    if not state:
        return False

    text = update.message.text.strip()

    if state == "admin_referral_reward":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ فقط عدد."
            )
            return True

        amount = int(text)

        set_referral_reward(amount)

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ جایزه رفرال شد {amount:,} DOGS",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    if state == "admin_add_balance":

        parts = text.split()

        if len(parts) != 2 or not all(
            p.isdigit() for p in parts
        ):

            await update.message.reply_text(
                "❌ فرمت:\n123456789 5000"
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

        execute(
            """
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                created_at
            )
            VALUES (?,?,?,?,?)
            """,
            (
                target_id,
                "admin_add",
                amount,
                "Admin balance add",
                datetime.now().isoformat(),
            ),
        )

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ {amount:,} DOGS اضافه شد.",
            reply_markup=main_keyboard(user["id"]),
        )

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=f"💰 {amount:,} DOGS به موجودی شما اضافه شد.",
            )

        except Exception:
            pass

        return True

    if state == "admin_remove_balance":

        parts = text.split()

        if len(parts) != 2 or not all(
            p.isdigit() for p in parts
        ):

            await update.message.reply_text(
                "❌ فرمت:\n123456789 5000"
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

        if target["balance"] < amount:

            await update.message.reply_text(
                "❌ موجودی کافی نیست."
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

        execute(
            """
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                created_at
            )
            VALUES (?,?,?,?,?)
            """,
            (
                target_id,
                "admin_remove",
                -amount,
                "Admin balance remove",
                datetime.now().isoformat(),
            ),
        )

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ {amount:,} DOGS کم شد.",
            reply_markup=main_keyboard(user["id"]),
        )

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

        await update.message.reply_text(
            "✅ کاربر " +
            ("مسدود شد." if new_status else "آزاد شد."),
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    if state == "admin_transfer_owner":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ ID باید عددی باشد."
            )
            return True

        new_owner = int(text)

        if not get_user(new_owner):

            await update.message.reply_text(
                "❌ این کاربر ابتدا باید /start کند."
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
                    "👑 شما مالک جدید ربات شدید."
                ),
                reply_markup=main_keyboard(new_owner),
            )

        except Exception:
            pass

        logger.info(
            "Owner changed %s -> %s",
            old_owner,
            new_owner,
        )

        return True

    if state == "admin_broadcast":

        users = execute(
            """
            SELECT id
            FROM users
            WHERE blocked=0
            """,
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
            f"📢 ارسال شد.\n"
            f"👥 موفق: {sent}",
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

async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.text:
        return

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:

        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    text = update.message.text.strip()

    # Cancel
    if text == "❌ لغو":

        await cancel(update, context)
        return

    # Admin states first
    if await admin_state_handler(
        update,
        context,
    ):
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

    # =====================================================
    # BALANCE COMMANDS
    # =====================================================

    balance_commands = {
        "💳 موجودی",
        "موجودی",
        "موجودی من",
        "موجودیم",
        "موجودی‌م",
        "موجودی من چقدره",
        "موجودی چقدره",
        "موجودی من؟",
        "موجودیم؟",
    }

    if text in balance_commands:

        await balance(update, context)
        return

    # =====================================================
    # MAIN
    # =====================================================

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

    if text in ("🎮 بازی", "بازی"):

        await game_create(update, context)
        return

    if text == "🛠 پنل مدیریت":

        await admin_panel(update, context)
        return

    # =====================================================
    # GROUP GAME
    # =====================================================

    if re.fullmatch(
        r"بازی(?:\s+500)?",
        text,
    ):

        await game_create(update, context)
        return

    # =====================================================
    # TRANSFER COMMAND
    # =====================================================

    if text.startswith("انتقال"):

        parts = text.split()

        # Reply:
        # انتقال 500
        if (
            len(parts) == 2
            and parts[1].isdigit()
            and update.message.reply_to_message
        ):

            receiver = get_user(
                update.message.reply_to_message.from_user.id
            )

            if receiver:

                await complete_transfer(
                    update,
                    context,
                    receiver["id"],
                    int(parts[1]),
                )

                return

        # انتقال @user 500
        if len(parts) == 3:

            destination = parts[1]
            amount = parts[2]

            if amount.isdigit():

                receiver = find_transfer_receiver(
                    update,
                    destination,
                )

                if receiver:

                    await complete_transfer(
                        update,
                        context,
                        receiver["id"],
                        int(amount),
                    )

                    return

        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "انتقال @username 500\n"
            "یا\n"
            "انتقال 123456789 500\n\n"
            "یا روی پیام کاربر Reply کنید:\n"
            "انتقال 500"
        )

        return


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    state = context.user_data.get("state")

    if state == "deposit_receipt":

        await deposit_receipt(
            update,
            context,
        )
        return

    if state == "support":

        await support_message(
            update,
            context,
        )
        return

    if state == "admin_broadcast":

        if user["id"] != get_owner_id():
            return

        users = execute(
            """
            SELECT id
            FROM users
            WHERE blocked=0
            """,
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
            f"👥 موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


# =========================================================
# COMMANDS
# =========================================================

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await balance(update, context)


async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await game_create(update, context)


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

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "balance",
            balance_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "game",
            game_command,
        )
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # Contact verification
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # Media
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            media_router,
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    logger.info("BOT STARTED")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
