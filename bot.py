import os
import re
import random
import sqlite3
import logging
import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
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

# سهم مالک بازی از موجودی خود ربات
OWNER_GAME_FEE = 50

# جایزه بازی:
# ورودی 500 => برنده 900 و 50 DOGS سهم مالک
# یعنی 50 DOGS از موجودی خود ربات پرداخت می‌شود.
GAME_WINNER_MULTIPLIER = 1.8

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
    timeout=30,
)
db.row_factory = sqlite3.Row

db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA busy_timeout=30000")


def execute(query, params=(), fetchone=False, fetchall=False):
    cur = db.cursor()
    cur.execute(query, params)
    db.commit()

    if fetchone:
        return cur.fetchone()

    if fetchall:
        return cur.fetchall()

    return None


def column_exists(table, column):
    row = execute(
        f"PRAGMA table_info({table})",
        fetchall=True,
    )

    return any(x["name"] == column for x in row)


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
            phone TEXT,
            created_at TEXT
        )
    """)

    # Migration برای DB قبلی
    if not column_exists("users", "phone_verified"):
        execute(
            "ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0"
        )

    if not column_exists("users", "phone"):
        execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
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
            group_chat_id INTEGER NOT NULL,
            message_id INTEGER,
            creator_id INTEGER NOT NULL,
            opponent_id INTEGER,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'waiting',
            winner_id INTEGER,
            loser_id INTEGER,
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

    enabled = execute(
        "SELECT value FROM settings WHERE key='bot_enabled'",
        fetchone=True,
    )

    if not enabled:
        execute(
            "INSERT INTO settings(key,value) VALUES('bot_enabled','1')"
        )


# =========================================================
# SETTINGS
# =========================================================

def get_setting(key, default=None):
    row = execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
        fetchone=True,
    )

    if not row:
        return default

    return row["value"]


def set_setting(key, value):
    execute(
        """
        INSERT INTO settings(key,value)
        VALUES(?,?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
        """,
        (key, str(value)),
    )


def get_owner_id():
    return int(get_setting("owner_id", INITIAL_OWNER_ID))


def set_owner_id(user_id):
    set_setting("owner_id", user_id)


def get_referral_reward():
    return int(get_setting(
        "referral_reward",
        DEFAULT_REFERRAL_REWARD,
    ))


def set_referral_reward(amount):
    set_setting("referral_reward", amount)


def bot_enabled():
    return get_setting("bot_enabled", "1") == "1"


def set_bot_enabled(value):
    set_setting("bot_enabled", "1" if value else "0")


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
        (id,username,first_name,balance,referrer_id,
         blocked,phone_verified,phone,created_at)
        VALUES (?, ?, ?, 0, ?, 0, 0, NULL, ?)
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
                (referrer_id,referred_id,reward,created_at)
                VALUES (?,?,?,?)
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
                (reward, valid_referrer),
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


def user_name(user):
    if not user:
        return "-"

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


def is_blocked(user_id):
    user = get_user(user_id)
    return bool(user and user["blocked"])


def is_verified(user_id):
    user = get_user(user_id)
    return bool(user and user["phone_verified"])


# =========================================================
# PHONE VERIFICATION
# =========================================================

def phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 تأیید شماره",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def ask_phone(update, context):
    await update.message.reply_text(
        "🔐 برای استفاده از ربات ابتدا باید شماره تلفن خود را تأیید کنید.\n\n"
        "روی دکمه زیر بزنید و شماره خودتان را ارسال کنید:",
        reply_markup=phone_keyboard(),
    )


async def contact_handler(update, context):
    contact = update.message.contact
    tg_user = update.effective_user

    if not contact:
        return

    if contact.user_id != tg_user.id:
        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را با دکمه تأیید ارسال کنید."
        )
        return

    create_or_update_user(tg_user)

    execute(
        """
        UPDATE users
        SET phone_verified=1, phone=?
        WHERE id=?
        """,
        (
            contact.phone_number,
            tg_user.id,
        ),
    )

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تأیید شد.\n\n"
        "به ربات خوش آمدید ❤️",
        reply_markup=main_keyboard(tg_user.id),
    )


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
    status = "🟢 روشن" if bot_enabled() else "🔴 خاموش"

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
        [
            InlineKeyboardButton(
                status,
                callback_data="admin_toggle_bot",
            )
        ],
    ])


# =========================================================
# GLOBAL CHECK
# =========================================================

async def allowed_user(update):
    tg_user = update.effective_user

    if not tg_user:
        return None

    user = create_or_update_user(tg_user)

    if user["blocked"]:
        if update.message:
            await update.message.reply_text(
                "🚫 حساب شما مسدود شده است."
            )
        return None

    # مالک همیشه دسترسی دارد
    if tg_user.id != get_owner_id():
        if not user["phone_verified"]:
            if update.message:
                await ask_phone(update, None)
            return None

        if not bot_enabled():
            if update.message:
                await update.message.reply_text(
                    "🔴 ربات در حال حاضر خاموش است.\n"
                    "لطفاً بعداً دوباره تلاش کنید."
                )
            return None

    return user


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    referrer_id = None

    if context.args:
        value = context.args[0]

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

    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await ask_phone(update, context)
        return

    if (
        user["id"] != get_owner_id()
        and not bot_enabled()
    ):
        await update.message.reply_text(
            "🔴 ربات خاموش است."
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

async def balance(update, context):
    user = await allowed_user(update)

    if not user:
        return

    await update.message.reply_text(
        "💳 موجودی شما\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update, context):
    user = await allowed_user(update)

    if not user:
        return

    context.user_data.clear()
    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        f"💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def deposit_amount(update, context):
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
        "لطفاً مبلغ را واریز کنید:\n\n"
        f"فرمت:\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از واریز رسید را بفرستید.\n"
        "🖼 عکس، فایل یا 📝 متن قبول است.",
        reply_markup=cancel_keyboard(),
    )


async def deposit_receipt(update, context):
    amount = context.user_data.get("deposit_amount")

    if not amount:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست منقضی شده است."
        )
        return

    user = get_user(update.effective_user.id)

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
        (user_id,amount,receipt_type,receipt_text,
         receipt_file_id,status,created_at)
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

    try:
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
    except Exception as e:
        logger.exception("Could not send deposit to owner: %s", e)

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n"
        "در انتظار بررسی مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update, context):
    user = await allowed_user(update)

    if not user:
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


async def withdraw_amount(update, context):
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


async def withdraw_destination(update, context):
    destination = update.message.text.strip()

    if not (
        destination.isdigit()
        or re.fullmatch(r"@[A-Za-z0-9_]{5,32}", destination)
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

    # ضد دوباره‌کاری + رزرو اتمیک موجودی
    cur = db.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

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
                "❌ موجودی کافی نیست یا درخواست قبلاً پردازش شده."
            )
            return

        cur.execute(
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

        withdrawal_id = cur.lastrowid

        db.commit()

    except Exception:
        db.rollback()

        await update.message.reply_text(
            "❌ خطا در ثبت برداشت. دوباره تلاش کنید."
        )
        return

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
# TRANSFER - ONLY REPLY
# =========================================================

async def transfer_start(update, context):
    user = await allowed_user(update)

    if not user:
        return

    context.user_data.clear()
    context.user_data["state"] = "transfer"

    await update.message.reply_text(
        "🔄 انتقال فقط با Reply انجام می‌شود.\n\n"
        "روی پیام کاربر Reply کنید و فقط مبلغ را بنویسید.\n\n"
        "مثال:\n"
        "5000",
        reply_markup=cancel_keyboard(),
    )


async def transfer_reply(update, context):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ برای انتقال باید روی پیام کاربر Reply کنید."
        )
        return

    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ فقط مبلغ را وارد کنید.\nمثال: 5000"
        )
        return

    amount = int(text)

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    sender_id = update.effective_user.id
    replied_user = update.message.reply_to_message.from_user

    if not replied_user or replied_user.is_bot:
        await update.message.reply_text(
            "❌ کاربر مقصد معتبر نیست."
        )
        return

    receiver_id = replied_user.id

    if sender_id == receiver_id:
        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    sender = get_user(sender_id)
    receiver = get_user(receiver_id)

    if not receiver:
        await update.message.reply_text(
            "❌ کاربر مقصد هنوز ربات را /start نکرده است."
        )
        return

    # انتقال اتمیک
    try:
        cur = db.cursor()
        cur.execute("BEGIN IMMEDIATE")

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
                "❌ موجودی کافی نیست یا انتقال قبلاً انجام شده."
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

        now = datetime.now().isoformat()

        cur.execute(
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

        cur.execute(
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

        cur.execute(
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

        db.commit()

    except Exception:
        db.rollback()

        await update.message.reply_text(
            "❌ انتقال انجام نشد. دوباره تلاش کنید."
        )
        return

    context.user_data.clear()

    await update.message.reply_text(
        "✅ انتقال با موفقیت انجام شد.\n\n"
        f"👤 مقصد: {user_name(receiver)}\n"
        f"💰 مبلغ: {amount:,} DOGS",
        reply_markup=main_keyboard(sender_id),
    )

    try:
        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💰 انتقال جدید دریافت کردید.\n\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"👤 از: {user_name(sender)}"
            ),
        )
    except Exception:
        pass


# =========================================================
# REFERRAL
# =========================================================

async def referrals(update, context):
    user = await allowed_user(update)

    if not user:
        return

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start=ref_{user['id']}"
    )

    count = execute(
        """
        SELECT COUNT(*) AS count
        FROM referrals
        WHERE referrer_id=?
        """,
        (user["id"],),
        fetchone=True,
    )["count"]

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"👤 تعداد رفرال‌ها: {count}\n"
        f"🎁 پاداش هر رفرال: "
        f"{get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update, context):
    user = await allowed_user(update)

    if not user:
        return

    context.user_data.clear()
    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را برای پشتیبانی بفرستید.\n\n"
        "متن، عکس یا فایل قابل ارسال است.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(update, context):
    user = get_user(update.effective_user.id)

    if not user:
        return

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

    # دکمه پاسخ برای مالک
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 پاسخ",
                callback_data=f"support_reply:{support_id}",
            )
        ]
    ])

    try:
        if file_type == "photo":
            await context.bot.send_photo(
                chat_id=get_owner_id(),
                photo=file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        elif file_type == "document":
            await context.bot.send_document(
                chat_id=get_owner_id(),
                document=file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        else:
            await context.bot.send_message(
                chat_id=get_owner_id(),
                text=caption + f"\n\n📝 {text}",
                reply_markup=keyboard,
            )
    except Exception:
        pass

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما سریع برای مالک ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(update, context):
    user = await allowed_user(update)

    if not user:
        return

    if user["id"] != get_owner_id():
        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )
        return

    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        f"وضعیت ربات: "
        f"{'🟢 روشن' if bot_enabled() else '🔴 خاموش'}",
        reply_markup=admin_keyboard(),
    )


def admin_only(user_id):
    return user_id == get_owner_id()


# =========================================================
# CALLBACK
# =========================================================

async def callback_handler(update, context):
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user_id = query.from_user.id
    data = query.data or ""

    # =====================================================
    # GAME CALLBACKS
    # =====================================================

    if data.startswith("game_join:"):
        await game_join(query, context)
        return

    if data.startswith("game_cancel:"):
        await game_cancel(query, context)
        return

    # =====================================================
    # SUPPORT REPLY
    # =====================================================

    if data.startswith("support_reply:"):

        if not admin_only(user_id):
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        support_id = int(data.split(":")[1])

        row = execute(
            "SELECT * FROM support_messages WHERE id=?",
            (support_id,),
            fetchone=True,
        )

        if not row:
            await query.answer(
                "پیام پیدا نشد.",
                show_alert=True,
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "support_admin_reply"
        context.user_data["support_id"] = support_id
        context.user_data["support_user_id"] = row["user_id"]

        await query.message.reply_text(
            "💬 پاسخ خود را ارسال کنید."
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

        action, id_text = data.split(":", 1)

        try:
            deposit_id = int(id_text)
        except ValueError:
            await query.answer(
                "درخواست نامعتبر.",
                show_alert=True,
            )
            return

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

            cur = db.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                cur.execute(
                    """
                    UPDATE deposits
                    SET status='approved'
                    WHERE id=? AND status='pending'
                    """,
                    (deposit_id,),
                )

                if cur.rowcount != 1:
                    db.rollback()
                    await query.answer(
                        "قبلاً پردازش شده.",
                        show_alert=True,
                    )
                    return

                cur.execute(
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

                cur.execute(
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

                db.commit()

            except Exception:
                db.rollback()
                await query.answer(
                    "خطا در تأیید.",
                    show_alert=True,
                )
                return

            try:
                await query.edit_message_reply_markup(
                    reply_markup=None
                )
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=deposit["user_id"],
                    text=(
                        "✅ واریزی شما تأیید شد.\n\n"
                        f"💰 {deposit['amount']:,} DOGS"
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

            try:
                await query.edit_message_reply_markup(
                    reply_markup=None
                )
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=deposit["user_id"],
                    text=(
                        "❌ واریزی شما رد شد.\n\n"
                        f"💰 {deposit['amount']:,} DOGS"
                    ),
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

        action, id_text = data.split(":", 1)

        try:
            withdrawal_id = int(id_text)
        except ValueError:
            return

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
                "قبلاً بررسی شده.",
                show_alert=True,
            )
            return

        if action == "withdraw_approve":

            cur = db.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='approved'
                    WHERE id=? AND status='pending'
                    """,
                    (withdrawal_id,),
                )

                if cur.rowcount != 1:
                    db.rollback()
                    return

                db.commit()

            except Exception:
                db.rollback()
                return

            try:
                await query.edit_message_reply_markup(
                    reply_markup=None
                )
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=withdrawal["user_id"],
                    text=(
                        "✅ برداشت شما تأیید شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS\n"
                        f"📍 {withdrawal['destination']}"
                    ),
                )
            except Exception:
                pass

        else:

            cur = db.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='rejected'
                    WHERE id=? AND status='pending'
                    """,
                    (withdrawal_id,),
                )

                if cur.rowcount != 1:
                    db.rollback()
                    return

                cur.execute(
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

                db.commit()

            except Exception:
                db.rollback()
                return

            try:
                await query.edit_message_reply_markup(
                    reply_markup=None
                )
            except Exception:
                pass

            try:
                await context.bot.send_message(
                    chat_id=withdrawal["user_id"],
                    text=(
                        "❌ برداشت رد شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS "
                        "به موجودی شما برگشت."
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

    if data == "admin_toggle_bot":

        new_value = not bot_enabled()
        set_bot_enabled(new_value)

        await query.answer(
            "وضعیت تغییر کرد.",
            show_alert=False,
        )

        try:
            await query.edit_message_text(
                "🛠 پنل مدیریت\n\n"
                f"وضعیت ربات: "
                f"{'🟢 روشن' if new_value else '🔴 خاموش'}",
                reply_markup=admin_keyboard(),
            )
        except Exception:
            pass

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
            await query.message.reply_text(
                "هیچ کاربری ثبت نشده."
            )
            return

        text = "👥 موجودی کاربران\n\n"

        for u in users:
            line = (
                f"👤 {u['first_name'] or '-'}\n"
                f"🔢 {u['id']}\n"
                f"💰 {u['balance']:,} DOGS\n"
                f"📱 {'✅' if u['phone_verified'] else '❌'}\n\n"
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

        refs = execute(
            "SELECT COUNT(*) AS c FROM referrals",
            fetchone=True,
        )["c"]

        games = execute(
            "SELECT COUNT(*) AS c FROM games WHERE status='finished'",
            fetchone=True,
        )["c"]

        await query.message.reply_text(
            "📊 آمار\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"👥 رفرال: {refs}\n"
            f"🎮 بازی انجام‌شده: {games}\n"
            f"🎁 رفرال: {get_referral_reward():,} DOGS\n"
            f"🎮 سهم مالک بازی: {OWNER_GAME_FEE} DOGS\n"
            f"🤖 وضعیت: "
            f"{'روشن' if bot_enabled() else 'خاموش'}"
        )
        return

    if data == "admin_referral_reward":

        context.user_data.clear()
        context.user_data["state"] = "admin_referral_reward"

        await query.message.reply_text(
            f"🎁 جایزه فعلی: "
            f"{get_referral_reward():,} DOGS\n\n"
            "مقدار جدید را وارد کنید:"
        )
        return

    if data == "admin_transfer_owner":

        context.user_data.clear()
        context.user_data["state"] = "admin_transfer_owner"

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را وارد کنید:"
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
            "🚫 آیدی کاربر را وارد کنید:"
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
# ADMIN STATE
# =========================================================

async def admin_state_handler(update, context):

    user = get_user(update.effective_user.id)

    if not user:
        return False

    if user["id"] != get_owner_id():
        return False

    state = context.user_data.get("state")

    if not state:
        return False

    text = update.message.text.strip()

    # -----------------------------------------------------
    # SUPPORT ADMIN REPLY
    # -----------------------------------------------------

    if state == "support_admin_reply":

        support_id = context.user_data.get("support_id")
        target_id = context.user_data.get("support_user_id")

        if not support_id or not target_id:
            context.user_data.clear()
            return True

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎧 پاسخ پشتیبانی\n\n"
                    f"💬 {text}"
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

            await update.message.reply_text(
                "✅ پاسخ برای کاربر ارسال شد.",
                reply_markup=main_keyboard(user["id"]),
            )

        except Exception:
            await update.message.reply_text(
                "❌ ارسال پاسخ ناموفق بود."
            )

        context.user_data.clear()
        return True

    # -----------------------------------------------------
    # REFERRAL
    # -----------------------------------------------------

    if state == "admin_referral_reward":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )
            return True

        amount = int(text)

        if amount < 0:
            await update.message.reply_text(
                "❌ مقدار نامعتبر."
            )
            return True

        set_referral_reward(amount)
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ جایزه رفرال شد {amount:,} DOGS",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    if state == "admin_transfer_owner":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ آیدی باید عدد باشد."
            )
            return True

        new_owner = int(text)

        if not get_user(new_owner):
            await update.message.reply_text(
                "❌ این کاربر هنوز /start نکرده است."
            )
            return True

        old_owner = get_owner_id()

        set_owner_id(new_owner)

        context.user_data.clear()

        await update.message.reply_text(
            f"👑 مالکیت منتقل شد.\n"
            f"مالک جدید: {new_owner}"
        )

        try:
            await context.bot.send_message(
                chat_id=new_owner,
                text="👑 شما مالک جدید ربات شدید.",
                reply_markup=main_keyboard(new_owner),
            )
        except Exception:
            pass

        logger.info(
            "Owner changed: %s -> %s",
            old_owner,
            new_owner,
        )

        return True

    # -----------------------------------------------------
    # ADD / REMOVE
    # -----------------------------------------------------

    if state in (
        "admin_add_balance",
        "admin_remove_balance",
    ):

        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text(
                "❌ فرمت:\n123456789 5000"
            )
            return True

        if not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text(
                "❌ ID و مبلغ باید عدد باشند."
            )
            return True

        target_id = int(parts[0])
        amount = int(parts[1])

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ نامعتبر."
            )
            return True

        target = get_user(target_id)

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
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
                f"✅ {amount:,} DOGS "
                f"به {target_id} اضافه شد."
            )

        else:

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

            transaction_amount = -amount
            transaction_type = "admin_remove"

            message = (
                f"✅ {amount:,} DOGS "
                f"از {target_id} کم شد."
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

    # -----------------------------------------------------
    # BLOCK
    # -----------------------------------------------------

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
            "✅ کاربر "
            f"{'مسدود' if new_status else 'آزاد'} شد.",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    # -----------------------------------------------------
    # BROADCAST
    # -----------------------------------------------------

    if state == "admin_broadcast":

        users = execute(
            """
            SELECT id FROM users
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


async def game_command(update, context):

    if update.effective_chat.type not in (
        "group",
        "supergroup",
    ):
        await update.message.reply_text(
            "🎮 بازی فقط داخل گروه قابل اجراست."
        )
        return

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await update.message.reply_text(
            "❌ ابتدا در PV ربات شماره خود را تأیید کنید."
        )
        return

    if not bot_enabled():
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    args = context.args

    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500\n\n"
            f"حداقل بازی: {500:,} DOGS"
        )
        return

    amount = int(args[0])

    if amount < 500:
        await update.message.reply_text(
            "❌ حداقل مبلغ بازی 500 DOGS است."
        )
        return

    if user["balance"] < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # برای جلوگیری از چند بازی همزمان
    existing = execute(
        """
        SELECT id FROM games
        WHERE creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:
        await update.message.reply_text(
            "❌ شما یک بازی در انتظار ورود دارید."
        )
        return

    # مبلغ سازنده رزرو می‌شود
    cur = db.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

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
            INSERT INTO games
            (group_chat_id,message_id,creator_id,
             opponent_id,amount,status,created_at)
            VALUES (?,?,?,?,?,'waiting',?)
            """,
            (
                update.effective_chat.id,
                None,
                user["id"],
                None,
                amount,
                datetime.now().isoformat(),
            ),
        )

        game_id = cur.lastrowid

        db.commit()

    except Exception:
        db.rollback()

        await update.message.reply_text(
            "❌ خطا در ساخت بازی."
        )
        return

    message = await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"👤 سازنده: {user_name(user)}\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"🏆 جایزه برنده: "
        f"{int(amount * GAME_WINNER_MULTIPLIER):,} DOGS\n"
        f"👑 سهم مالک: {OWNER_GAME_FEE} DOGS\n\n"
        "یک نفر می‌تواند وارد بازی شود.",
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


async def game_join(query, context):

    try:
        game_id = int(query.data.split(":")[1])
    except Exception:
        await query.answer(
            "بازی نامعتبر.",
            show_alert=True,
        )
        return

    user = create_or_update_user(query.from_user)

    if user["blocked"]:
        await query.answer(
            "حساب شما مسدود است.",
            show_alert=True,
        )
        return

    if not bot_enabled() and user["id"] != get_owner_id():
        await query.answer(
            "ربات خاموش است.",
            show_alert=True,
        )
        return

    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await query.answer(
            "ابتدا شماره خود را تأیید کنید.",
            show_alert=True,
        )
        return

    cur = db.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

        game = cur.execute(
            """
            SELECT * FROM games
            WHERE id=? AND status='waiting'
            """,
            (game_id,),
        ).fetchone()

        if not game:
            db.rollback()

            await query.answer(
                "این بازی قبلاً شروع یا لغو شده.",
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

        amount = game["amount"]

        # بازیکن دوم هم باید مبلغ بازی را داشته باشد
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

            await query.answer(
                "❌ موجودی کافی ندارید.",
                show_alert=True,
            )
            return

        # قرعه‌کشی
        winner_id = random.choice([
            game["creator_id"],
            user["id"],
        ])

        loser_id = (
            user["id"]
            if winner_id == game["creator_id"]
            else game["creator_id"]
        )

        # جایزه برنده
        winner_prize = int(
            amount * GAME_WINNER_MULTIPLIER
        )

        # جایزه از موجودی ربات پرداخت می‌شود.
        # 50 DOGS سهم مالک است و از بازنده کم نمی‌شود.
        owner_fee = OWNER_GAME_FEE

        # موجودی مالک/ربات باید 50 DOGS برای هزینه داشته باشد.
        owner_id = get_owner_id()

        cur.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=? AND balance>=?
            """,
            (
                owner_fee,
                owner_id,
                owner_fee,
            ),
        )

        if cur.rowcount != 1:
            # اگر موجودی مالک برای سهم 50 کم باشد،
            # بازی انجام نمی‌شود و مبلغ بازیکن دوم برمی‌گردد.
            db.rollback()

            await query.answer(
                "❌ موجودی ربات برای پرداخت سهم مالک کافی نیست.",
                show_alert=True,
            )
            return

        # پرداخت جایزه به برنده
        cur.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                winner_prize,
                winner_id,
            ),
        )

        cur.execute(
            """
            UPDATE games
            SET opponent_id=?,
                status='finished',
                winner_id=?,
                loser_id=?
            WHERE id=? AND status='waiting'
            """,
            (
                user["id"],
                winner_id,
                loser_id,
                game_id,
            ),
        )

        if cur.rowcount != 1:
            db.rollback()

            await query.answer(
                "❌ بازی قبلاً پردازش شده.",
                show_alert=True,
            )
            return

        now = datetime.now().isoformat()

        # تراکنش بازیکن بازنده
        cur.execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                loser_id,
                "game_loss",
                -amount,
                f"Game #{game_id}",
                now,
            ),
        )

        # تراکنش برنده
        cur.execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                winner_id,
                "game_win",
                winner_prize,
                f"Game #{game_id}",
                now,
            ),
        )

        # سهم مالک از موجودی ربات
        cur.execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                owner_id,
                "game_owner_fee",
                -owner_fee,
                f"Game #{game_id} owner fee",
                now,
            ),
        )

        db.commit()

    except Exception as e:
        db.rollback()

        logger.exception("Game error: %s", e)

        await query.answer(
            "❌ خطا در شروع بازی.",
            show_alert=True,
        )
        return

    creator = get_user(game["creator_id"])
    opponent = get_user(user["id"])
    winner = get_user(winner_id)
    loser = get_user(loser_id)

    try:
        await query.edit_message_text(
            "🎮 بازی تمام شد!\n\n"
            f"👤 بازیکن ۱: {user_name(creator)}\n"
            f"👤 بازیکن ۲: {user_name(opponent)}\n\n"
            f"🏆 برنده: {user_name(winner)}\n"
            f"💰 جایزه: {winner_prize:,} DOGS\n"
            f"❌ بازنده: {user_name(loser)}\n\n"
            f"👑 سهم مالک: {owner_fee} DOGS"
        )
    except Exception:
        pass

    # نتیجه در PV هر دو
    try:
        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 تبریک! شما برنده بازی شدید.\n\n"
                f"🎮 بازی: #{game_id}\n"
                f"💰 جایزه: {winner_prize:,} DOGS\n"
                f"💳 موجودی جدید: "
                f"{get_user(winner_id)['balance']:,} DOGS"
            ),
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "❌ شما بازی را باختید.\n\n"
                f"🎮 بازی: #{game_id}\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"💳 موجودی جدید: "
                f"{get_user(loser_id)['balance']:,} DOGS"
            ),
        )
    except Exception:
        pass


async def game_cancel(query, context):

    try:
        game_id = int(query.data.split(":")[1])
    except Exception:
        return

    user_id = query.from_user.id

    cur = db.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

        game = cur.execute(
            """
            SELECT * FROM games
            WHERE id=? AND status='waiting'
            """,
            (game_id,),
        ).fetchone()

        if not game:
            db.rollback()

            await query.answer(
                "این بازی دیگر قابل لغو نیست.",
                show_alert=True,
            )
            return

        if game["creator_id"] != user_id:
            db.rollback()

            await query.answer(
                "فقط سازنده بازی می‌تواند لغو کند.",
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

        if cur.rowcount != 1:
            db.rollback()
            return

        # برگشت پول سازنده
        cur.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                game["amount"],
                game["creator_id"],
            ),
        )

        cur.execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                game["creator_id"],
                "game_cancel",
                game["amount"],
                f"Game #{game_id} cancelled",
                datetime.now().isoformat(),
            ),
        )

        db.commit()

    except Exception:
        db.rollback()

        await query.answer(
            "❌ خطا در لغو بازی.",
            show_alert=True,
        )
        return

    try:
        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 {game['amount']:,} DOGS "
            "به موجودی سازنده برگشت."
        )
    except Exception:
        pass


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):
    user = create_or_update_user(update.effective_user)

    context.user_data.clear()

    await update.message.reply_text(
        "❌ لغو شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# TEXT ROUTER - ONE ROUTER ONLY
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    text = (update.message.text or "").strip()

    if not text:
        return

    user = create_or_update_user(update.effective_user)

    # شماره قبلاً تأیید نشده
    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await ask_phone(update, context)
        return

    # بلاک
    if user["blocked"]:
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    # خاموش
    if (
        user["id"] != get_owner_id()
        and not bot_enabled()
    ):
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    # -----------------------------------------------------
    # CANCEL ALWAYS
    # -----------------------------------------------------

    if text == "❌ لغو":
        await cancel(update, context)
        return

    # -----------------------------------------------------
    # ADMIN STATES
    # -----------------------------------------------------

    if await admin_state_handler(update, context):
        return

    state = context.user_data.get("state")

    # -----------------------------------------------------
    # STATES
    # -----------------------------------------------------

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

    if state == "transfer":
        # انتقال فقط Reply
        await transfer_reply(update, context)
        return

    if state == "support":
        await support_message(update, context)
        return

    # -----------------------------------------------------
    # MAIN BUTTONS
    # -----------------------------------------------------

    if text in ("💳 موجودی", "موجودی"):
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

    # -----------------------------------------------------
    # TRANSFER OUTSIDE MENU IS ALSO ONLY REPLY
    # -----------------------------------------------------

    if update.message.reply_to_message and text.isdigit():
        await transfer_reply(update, context)
        return

    # -----------------------------------------------------
    # UNKNOWN
    # -----------------------------------------------------

    await update.message.reply_text(
        "❓ دستور نامعتبر است.\n\n"
        "از دکمه‌های منو استفاده کنید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# MEDIA ROUTER - SAME FLOW
# =========================================================

async def media_router(update, context):

    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await ask_phone(update, context)
        return

    if (
        user["id"] != get_owner_id()
        and not bot_enabled()
    ):
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    state = context.user_data.get("state")

    if state == "deposit_receipt":
        await deposit_receipt(update, context)
        return

    if state == "support":
        await support_message(update, context)
        return

    if state == "admin_broadcast" and admin_only(user["id"]):

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
            f"📢 ارسال شد.\n"
            f"👥 موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):
    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
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

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # /game
    application.add_handler(
        CommandHandler(
            "game",
            game_command,
        )
    )

    # فارسی: بازی 500
    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^بازی(?:\s+)?[0-9]+$"
            ),
            game_text_command,
        )
    )

    # callbackها
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # Contact - قبل از متن
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # عکس / فایل
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            media_router,
        )
    )

    # تمام پیام‌های متنی فقط از یک Router
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    application.add_error_handler(error_handler)

    logger.info("BOT STARTED")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# PERSIAN GAME COMMAND
# =========================================================

async def game_text_command(update, context):

    if update.effective_chat.type not in (
        "group",
        "supergroup",
    ):
        await update.message.reply_text(
            "🎮 بازی فقط در گروه است."
        )
        return

    match = re.fullmatch(
        r"بازی\s+([0-9]+)",
        update.message.text.strip(),
    )

    if not match:
        await update.message.reply_text(
            "❌ مثال:\nبازی 500"
        )
        return

    amount = int(match.group(1))

    # همان منطق /game بدون نیاز به command args
    user = create_or_update_user(update.effective_user)

    if user["blocked"]:
        return

    if (
        user["id"] != get_owner_id()
        and not user["phone_verified"]
    ):
        await update.message.reply_text(
            "❌ ابتدا در PV شماره خود را تأیید کنید."
        )
        return

    if not bot_enabled():
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    if amount < 500:
        await update.message.reply_text(
            "❌ حداقل بازی 500 DOGS است."
        )
        return

    if user["balance"] < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    existing = execute(
        """
        SELECT id FROM games
        WHERE creator_id=? AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:
        await update.message.reply_text(
            "❌ شما یک بازی در انتظار دارید."
        )
        return

    cur = db.cursor()

    try:
        cur.execute("BEGIN IMMEDIATE")

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
            INSERT INTO games
            (group_chat_id,message_id,creator_id,
             opponent_id,amount,status,created_at)
            VALUES (?,?,?,?,?,'waiting',?)
            """,
            (
                update.effective_chat.id,
                None,
                user["id"],
                None,
                amount,
                datetime.now().isoformat(),
            ),
        )

        game_id = cur.lastrowid

        db.commit()

    except Exception:
        db.rollback()

        await update.message.reply_text(
            "❌ خطا در ساخت بازی."
        )
        return

    winner_prize = int(
        amount * GAME_WINNER_MULTIPLIER
    )

    message = await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"👤 سازنده: {user_name(user)}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"🏆 جایزه برنده: {winner_prize:,} DOGS\n"
        f"👑 سهم مالک: {OWNER_GAME_FEE} DOGS\n\n"
        "یک نفر می‌تواند وارد شود:",
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


if __name__ == "__main__":
    main()
