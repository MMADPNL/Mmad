# ============================================================
# DOGS BOT - COMPLETE bot.py
# ============================================================

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

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

INITIAL_OWNER_ID = 8552447077

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DEFAULT_REFERRAL_REWARD = 50

# سهم ثابت مالک از هر بازی
GAME_OWNER_FEE = 50

# حداقل مبلغ بازی
GAME_MIN = 500

DB_FILE = "bot.db"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("DOGS-BOT")

# ============================================================
# DATABASE
# ============================================================

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
            verified INTEGER DEFAULT 0,
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

    execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
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

    execute("""
        CREATE TABLE IF NOT EXISTS verified_contacts (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            verified_at TEXT
        )
    """)

    # اضافه کردن ستون‌های قدیمی در صورت وجود دیتابیس قبلی
    try:
        execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Owner
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

    bot_status = execute(
        "SELECT value FROM settings WHERE key='bot_enabled'",
        fetchone=True,
    )

    if not bot_status:
        execute(
            "INSERT INTO settings(key,value) VALUES('bot_enabled','1')"
        )


# ============================================================
# SETTINGS
# ============================================================

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


def is_bot_enabled():
    return get_setting("bot_enabled", "1") == "1"


def set_bot_enabled(value):
    set_setting(
        "bot_enabled",
        "1" if value else "0",
    )


# ============================================================
# USER
# ============================================================

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

    verified = 1 if tg_user.id == get_owner_id() else 0

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
            verified,
            created_at
        )
        VALUES (?, ?, ?, 0, ?, 0, ?, ?)
        """,
        (
            tg_user.id,
            tg_user.username,
            tg_user.first_name,
            valid_referrer,
            verified,
            datetime.now().isoformat(),
        ),
    )

    # Referral
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


def user_name(user):
    if not user:
        return "-"

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


def is_blocked(user_id):
    user = get_user(user_id)

    return bool(
        user and user["blocked"]
    )


def is_verified(user_id):
    if user_id == get_owner_id():
        return True

    user = get_user(user_id)

    return bool(
        user and user["verified"]
    )


def add_transaction(
    user_id,
    tx_type,
    amount,
    description,
):
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
            user_id,
            tx_type,
            amount,
            description,
            datetime.now().isoformat(),
        ),
    )


# ============================================================
# VERIFICATION
# ============================================================

def verification_keyboard():
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


async def require_verification(
    update,
    context,
):
    user = create_or_update_user(
        update.effective_user
    )

    if user["id"] == get_owner_id():
        return True

    if is_verified(user["id"]):
        return True

    if update.message:

        await update.message.reply_text(
            "🔐 برای استفاده از ربات ابتدا باید شماره تلفن خود را تأیید کنید.\n\n"
            "روی دکمه «📱 تأیید شماره» بزنید و شماره خودتان را ارسال کنید.",
            reply_markup=verification_keyboard(),
        )

    return False


async def contact_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.contact:
        return

    tg_user = update.effective_user
    contact = update.message.contact

    create_or_update_user(tg_user)

    # شماره باید متعلق به خود کاربر باشد
    if contact.user_id and contact.user_id != tg_user.id:
        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را ارسال کنید."
        )
        return

    # اگر user_id در Contact نبود، باز هم شماره ارسال‌شده ثبت می‌شود.
    # در Telegram دکمه request_contact شماره حساب فرستنده را می‌دهد.

    execute(
        """
        INSERT INTO verified_contacts
        (user_id,phone,verified_at)
        VALUES (?,?,?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            phone=excluded.phone,
            verified_at=excluded.verified_at
        """,
        (
            tg_user.id,
            contact.phone_number,
            datetime.now().isoformat(),
        ),
    )

    execute(
        """
        UPDATE users
        SET verified=1
        WHERE id=?
        """,
        (tg_user.id,),
    )

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تأیید شد.\n\n"
        "🎉 حالا می‌توانید از ربات استفاده کنید.",
        reply_markup=main_keyboard(tg_user.id),
    )


# ============================================================
# KEYBOARDS
# ============================================================

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

    status = (
        "🟢 ربات روشن"
        if is_bot_enabled()
        else "🔴 ربات خاموش"
    )

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
                "🎮 تنظیمات بازی",
                callback_data="admin_game",
            )
        ],
        [
            InlineKeyboardButton(
                status,
                callback_data="admin_toggle_bot",
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


# ============================================================
# BOT ON/OFF CHECK
# ============================================================

async def bot_access(
    update,
    context,
    allow_owner=True,
):

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:

        if update.message:
            await update.message.reply_text(
                "🚫 حساب شما مسدود شده است."
            )

        return False

    if allow_owner and user["id"] == get_owner_id():
        return True

    if not is_bot_enabled():

        if update.message:
            await update.message.reply_text(
                "🔴 ربات در حال حاضر خاموش است.\n"
                "لطفاً بعداً دوباره تلاش کنید."
            )

        return False

    return True


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

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

    if user["id"] != get_owner_id():

        if not is_bot_enabled():

            await update.message.reply_text(
                "🔴 ربات خاموش است."
            )

            return

        if not is_verified(user["id"]):

            await update.message.reply_text(
                "🔐 قبل از ورود به ربات باید شماره خود را تأیید کنید.",
                reply_markup=verification_keyboard(),
            )

            return

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به ربات خوش آمدید ❤️\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_keyboard(user["id"]),
    )


# ============================================================
# BALANCE
# ============================================================

async def balance(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        "💳 موجودی شما:\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# ============================================================
# DEPOSIT
# ============================================================

async def deposit_start(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    context.user_data.clear()

    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        f"💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def deposit_amount(
    update,
    context,
):

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
        "بعد از واریز رسید را ارسال کنید.\n"
        "🖼 عکس، فایل یا 📝 متن قبول است.",
        reply_markup=cancel_keyboard(),
    )


async def deposit_receipt(
    update,
    context,
):

    amount = context.user_data.get(
        "deposit_amount"
    )

    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست منقضی شده است."
        )

        return

    user = create_or_update_user(
        update.effective_user
    )

    receipt_type = None
    receipt_text = None
    receipt_file_id = None

    if update.message.photo:

        receipt_type = "photo"

        receipt_file_id = (
            update.message.photo[-1].file_id
        )

    elif update.message.document:

        receipt_type = "document"

        receipt_file_id = (
            update.message.document.file_id
        )

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
        f"👤 {user['first_name'] or '-'}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        "📌 وضعیت: در انتظار تأیید"
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
                text=caption + (
                    f"\n\n📝 رسید:\n{receipt_text}"
                ),
                reply_markup=keyboard,
            )

    except Exception as e:

        logger.exception(e)

        execute(
            """
            DELETE FROM deposits
            WHERE id=? AND status='pending'
            """,
            (deposit_id,),
        )

        await update.message.reply_text(
            "❌ ارسال رسید به مالک انجام نشد. دوباره تلاش کنید."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n\n"
        "در انتظار بررسی مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# ============================================================
# WITHDRAW
# ============================================================

async def withdraw_start(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    user = get_user(update.effective_user.id)

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


async def withdraw_amount(
    update,
    context,
):

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


async def withdraw_destination(
    update,
    context,
):

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

    amount = context.user_data.get(
        "withdraw_amount"
    )

    if not amount:

        context.user_data.clear()
        return

    user = get_user(update.effective_user.id)

    # تراکنش اتمیک
    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=?
            AND balance>=?
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

    try:

        await context.bot.send_message(
            chat_id=get_owner_id(),
            text=(
                "💸 درخواست برداشت جدید\n\n"
                f"🆔 #{withdrawal_id}\n"
                f"👤 {user['first_name'] or '-'}\n"
                f"🔢 ID: {user['id']}\n"
                f"📱 {user_name(user)}\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"📍 مقصد: {destination}"
            ),
            reply_markup=keyboard,
        )

    except Exception:

        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                amount,
                user["id"],
            ),
        )

        execute(
            """
            UPDATE withdrawals
            SET status='rejected'
            WHERE id=? AND status='pending'
            """,
            (withdrawal_id,),
        )

        await update.message.reply_text(
            "❌ ارسال درخواست به مالک انجام نشد."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n"
        "در انتظار بررسی مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# ============================================================
# TRANSFER - ONLY REPLY
# ============================================================

async def transfer_start(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    context.user_data.clear()

    context.user_data["state"] = "transfer_amount"

    await update.message.reply_text(
        "🔄 انتقال فقط با Reply انجام می‌شود.\n\n"
        "روی پیام کاربر Reply کنید و مبلغ را بفرستید.\n\n"
        "مثال:\n"
        "5000",
        reply_markup=cancel_keyboard(),
    )


async def transfer_amount(
    update,
    context,
):

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "❌ برای انتقال باید حتماً روی پیام گیرنده Reply کنید."
        )

        return

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ فقط مبلغ را وارد کنید.\n"
            "مثال: 5000"
        )

        return

    amount = int(text)

    if amount <= 0:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return

    replied_user = (
        update.message.reply_to_message.from_user
    )

    if not replied_user:

        await update.message.reply_text(
            "❌ گیرنده پیدا نشد."
        )

        return

    if replied_user.is_bot:

        await update.message.reply_text(
            "❌ انتقال به ربات امکان‌پذیر نیست."
        )

        return

    sender_id = update.effective_user.id
    receiver_id = replied_user.id

    if sender_id == receiver_id:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return

    receiver = get_user(receiver_id)

    # اگر گیرنده هنوز /start نکرده
    if not receiver:

        await update.message.reply_text(
            "❌ این کاربر هنوز ربات را /start نکرده است."
        )

        return

    sender = get_user(sender_id)

    if sender["balance"] < amount:

        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی: {sender['balance']:,} DOGS"
        )

        return

    # انتقال اتمیک
    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=?
            AND balance>=?
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
                "❌ موجودی تغییر کرده؛ دوباره تلاش کنید."
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

        db.commit()

    add_transaction(
        sender_id,
        "transfer_out",
        -amount,
        f"To {receiver_id}",
    )

    add_transaction(
        receiver_id,
        "transfer_in",
        amount,
        f"From {sender_id}",
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {user_name(receiver)}",
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


# ============================================================
# REFERRAL
# ============================================================

async def referrals(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    user = get_user(update.effective_user.id)

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
        f"👤 تعداد رفرال‌ها: {row['count']}\n"
        f"🎁 پاداش هر رفرال: "
        f"{get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
    )


# ============================================================
# SUPPORT
# ============================================================

async def support_start(
    update,
    context,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    context.user_data.clear()

    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را ارسال کنید.\n\n"
        "مالک پیام شما را دریافت می‌کند.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(
    update,
    context,
):

    user = get_user(update.effective_user.id)

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
        f"👤 {user['first_name'] or '-'}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}\n\n"
        "↩️ برای پاسخ به کاربر، روی همین پیام Reply کنید."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 پاسخ به کاربر",
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
                text=caption + (
                    f"\n\n📝 {text}"
                ),
                reply_markup=keyboard,
            )

    except Exception:

        await update.message.reply_text(
            "❌ ارسال به مالک انجام نشد."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای مالک ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# ============================================================
# SUPPORT OWNER REPLY
# ============================================================

async def handle_owner_reply(
    update,
    context,
):

    if update.effective_user.id != get_owner_id():
        return False

    message = update.message

    if not message.reply_to_message:
        return False

    replied = message.reply_to_message

    # پیدا کردن ID کاربر از متن پیام مالک
    match = re.search(
        r"ID:\s*(\d+)",
        replied.caption or replied.text or "",
    )

    if not match:
        return False

    target_id = int(match.group(1))

    try:

        if message.photo:

            await context.bot.send_photo(
                chat_id=target_id,
                photo=message.photo[-1].file_id,
                caption=(
                    "🎧 پاسخ پشتیبانی\n\n"
                    f"{message.caption or ''}"
                ),
            )

        elif message.document:

            await context.bot.send_document(
                chat_id=target_id,
                document=message.document.file_id,
                caption=(
                    "🎧 پاسخ پشتیبانی\n\n"
                    f"{message.caption or ''}"
                ),
            )

        elif message.text:

            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎧 پاسخ پشتیبانی\n\n"
                    f"{message.text}"
                ),
            )

        else:

            return False

        await message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

        return True

    except Exception as e:

        logger.exception(e)

        await message.reply_text(
            "❌ ارسال پاسخ انجام نشد."
        )

        return True


# ============================================================
# GAME
# ============================================================

async def game_create(
    update,
    context,
    amount,
):

    if not await bot_access(update, context):
        return

    if not await require_verification(update, context):
        return

    # بازی فقط گروه
    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی را باید داخل گروه شروع کنید."
        )

        return

    if amount < GAME_MIN:

        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی {GAME_MIN:,} DOGS است."
        )

        return

    user = get_user(update.effective_user.id)

    if user["balance"] < amount:

        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی: {user['balance']:,} DOGS"
        )

        return

    # جلوگیری از چند بازی همزمان سازنده
    existing = execute(
        """
        SELECT *
        FROM games
        WHERE creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:

        await update.message.reply_text(
            "❌ شما همین الان یک بازی منتظر دارید."
        )

        return

    # مبلغ هنگام ساخت بازی رزرو می‌شود
    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=?
            AND balance>=?
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
            (
                chat_id,
                creator_id,
                amount,
                status,
                created_at
            )
            VALUES (?,?,?,?,?)
            """,
            (
                update.effective_chat.id,
                user["id"],
                amount,
                "waiting",
                datetime.now().isoformat(),
            ),
        )

        game_id = cur.lastrowid

        db.commit()

    # اگر پیام ساخته شد، message_id ذخیره می‌شود
    try:

        sent = await update.message.reply_text(
            "🎮 بازی DOGS\n\n"
            f"💰 مبلغ بازی: {amount:,} DOGS\n"
            f"👤 سازنده: {user_name(user)}\n\n"
            "یک نفر می‌تواند وارد بازی شود.\n"
            "با ورود نفر دوم بازی خودکار شروع می‌شود.",
            reply_markup=game_keyboard(game_id),
        )

        execute(
            """
            UPDATE games
            SET message_id=?
            WHERE id=?
            AND status='waiting'
            """,
            (
                sent.message_id,
                game_id,
            ),
        )

    except Exception:

        # اگر ارسال پیام نشد، پول رزرو شده برگردد
        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                amount,
                user["id"],
            ),
        )

        execute(
            """
            UPDATE games
            SET status='cancelled'
            WHERE id=?
            """,
            (game_id,),
        )


async def game_join(
    query,
    context,
    game_id,
):

    player_id = query.from_user.id

    if not is_bot_enabled():

        await query.answer(
            "🔴 ربات خاموش است.",
            show_alert=True,
        )

        return

    if not is_verified(player_id):

        await query.answer(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            show_alert=True,
        )

        return

    player = get_user(player_id)

    if not player:

        await query.answer(
            "ابتدا /start را بزنید.",
            show_alert=True,
        )

        return

    if player["blocked"]:

        await query.answer(
            "🚫 حساب شما مسدود است.",
            show_alert=True,
        )

        return

    # قفل منطقی برای جلوگیری از دو کلیک همزمان
    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            SELECT *
            FROM games
            WHERE id=?
            """,
            (game_id,),
        )

        game = cur.fetchone()

        if not game:

            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True,
            )

            return

        if game["status"] != "waiting":

            await query.answer(
                "❌ این بازی دیگر قابل ورود نیست.",
                show_alert=True,
            )

            return

        if game["creator_id"] == player_id:

            await query.answer(
                "❌ نمی‌توانید با خودتان بازی کنید.",
                show_alert=True,
            )

            return

        amount = game["amount"]

        cur.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=?
            AND balance>=?
            """,
            (
                amount,
                player_id,
                amount,
            ),
        )

        if cur.rowcount != 1:

            db.rollback()

            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True,
            )

            return

        cur.execute(
            """
            UPDATE games
            SET
                opponent_id=?,
                status='playing'
            WHERE id=?
            AND status='waiting'
            """,
            (
                player_id,
                game_id,
            ),
        )

        if cur.rowcount != 1:

            db.rollback()

            await query.answer(
                "❌ شخص دیگری وارد بازی شد.",
                show_alert=True,
            )

            return

        db.commit()

    creator = get_user(game["creator_id"])
    opponent = get_user(player_id)

    # بازی شروع می‌شود
    winner_id = random.choice([
        creator["id"],
        opponent["id"],
    ])

    loser_id = (
        opponent["id"]
        if winner_id == creator["id"]
        else creator["id"]
    )

    total = amount * 2

    # 50 DOGS سهم مالک
    owner_fee = GAME_OWNER_FEE

    # اگر مبلغ کل کمتر از سهم مالک باشد
    if total < owner_fee:
        owner_fee = 0

    winner_prize = total - owner_fee

    owner_id = get_owner_id()

    # نتیجه بازی را اتمیک ثبت می‌کنیم
    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            UPDATE games
            SET
                status='finished',
                winner_id=?,
                loser_id=?
            WHERE id=?
            AND status='playing'
            """,
            (
                winner_id,
                loser_id,
                game_id,
            ),
        )

        if cur.rowcount != 1:

            db.rollback()

            # اگر somehow قبلاً تمام شده، مبلغ نفر دوم برگردد
            cur.execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    amount,
                    player_id,
                ),
            )

            db.commit()

            await query.answer(
                "❌ این بازی قبلاً تمام شده.",
                show_alert=True,
            )

            return

        # جایزه برنده
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

        # سهم مالک جداگانه به مالک داده می‌شود
        if owner_fee > 0:

            cur.execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    owner_fee,
                    owner_id,
                ),
            )

        db.commit()

    add_transaction(
        winner_id,
        "game_win",
        winner_prize,
        f"Game #{game_id} win",
    )

    add_transaction(
        loser_id,
        "game_loss",
        0,
        f"Game #{game_id} loss",
    )

    if owner_fee > 0:

        add_transaction(
            owner_id,
            "game_fee",
            owner_fee,
            f"Owner fee from game #{game_id}",
        )

    # حذف دکمه‌ها
    try:

        await query.edit_message_text(
            "🎮 بازی انجام شد!\n\n"
            f"💰 مبلغ هر نفر: {amount:,} DOGS\n"
            f"🏆 برنده: {user_name(get_user(winner_id))}\n"
            f"💰 جایزه برنده: {winner_prize:,} DOGS\n"
            f"👑 سهم مالک: {owner_fee:,} DOGS"
        )

    except Exception:
        pass

    winner = get_user(winner_id)
    loser = get_user(loser_id)

    # PV برنده
    try:

        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 تبریک!\n\n"
                "🎮 شما برنده بازی شدید.\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🏆 جایزه شما: {winner_prize:,} DOGS\n\n"
                f"💳 موجودی جدید: {winner['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass

    # PV بازنده
    try:

        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "😔 شما بازی را باختید.\n\n"
                "🎮 بازی تمام شد.\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🏆 برنده: {user_name(winner)}\n\n"
                f"💳 موجودی جدید: {loser['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass

    await query.answer(
        "🎮 بازی تمام شد!",
        show_alert=False,
    )


async def game_cancel(
    query,
    context,
    game_id,
):

    user_id = query.from_user.id

    if not is_bot_enabled():

        await query.answer(
            "🔴 ربات خاموش است.",
            show_alert=True,
        )

        return

    with db_lock:

        cur = db.cursor()

        cur.execute(
            """
            SELECT *
            FROM games
            WHERE id=?
            """,
            (game_id,),
        )

        game = cur.fetchone()

        if not game:

            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True,
            )

            return

        if game["status"] != "waiting":

            await query.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True,
            )

            return

        if game["creator_id"] != user_id:

            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند لغو کند.",
                show_alert=True,
            )

            return

        cur.execute(
            """
            UPDATE games
            SET status='cancelled'
            WHERE id=?
            AND status='waiting'
            """,
            (game_id,),
        )

        if cur.rowcount != 1:

            db.rollback()

            await query.answer(
                "❌ بازی قبلاً تغییر کرده.",
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
                game["amount"],
                game["creator_id"],
            ),
        )

        db.commit()

    try:

        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 {game['amount']:,} DOGS به موجودی سازنده برگشت."
        )

    except Exception:
        pass

    await query.answer(
        "بازی لغو شد."
    )


# ============================================================
# ADMIN PANEL
# ============================================================

async def admin_panel(
    update,
    context,
):

    user = get_user(update.effective_user.id)

    if not user or user["id"] != get_owner_id():

        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )

        return

    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        reply_markup=admin_keyboard(),
    )


def admin_only(user_id):
    return user_id == get_owner_id()


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update,
    context,
):

    query = update.callback_query

    # ابتدا پاسخ سریع به callback
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data or ""

    user_id = query.from_user.id

    # ========================================================
    # GAME CALLBACKS
    # ========================================================

    if data.startswith("game_join:"):

        try:
            game_id = int(data.split(":")[1])
        except Exception:

            await query.answer(
                "❌ بازی نامعتبر است.",
                show_alert=True,
            )

            return

        await game_join(
            query,
            context,
            game_id,
        )

        return

    if data.startswith("game_cancel:"):

        try:
            game_id = int(data.split(":")[1])
        except Exception:

            await query.answer(
                "❌ بازی نامعتبر است.",
                show_alert=True,
            )

            return

        await game_cancel(
            query,
            context,
            game_id,
        )

        return

    # ========================================================
    # SUPPORT REPLY
    # ========================================================

    if data.startswith("support_reply:"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )

            return

        try:
            support_id = int(data.split(":")[1])
        except Exception:
            return

        row = execute(
            """
            SELECT *
            FROM support_messages
            WHERE id=?
            """,
            (support_id,),
            fetchone=True,
        )

        if not row:
            await query.answer(
                "❌ پیام پیدا نشد.",
                show_alert=True,
            )
            return

        context.user_data.clear()

        context.user_data["state"] = "support_admin_reply"

        context.user_data["support_user_id"] = row["user_id"]

        await query.message.reply_text(
            "💬 پاسخ پشتیبانی\n\n"
            f"کاربر: {row['user_id']}\n\n"
            "متن پاسخ را ارسال کنید.",
            reply_markup=cancel_keyboard(),
        )

        return

    # ========================================================
    # DEPOSIT
    # ========================================================

    if data.startswith("deposit_"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )

            return

        try:

            action, id_text = data.split(":")

            deposit_id = int(id_text)

        except Exception:

            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )

            return

        with db_lock:

            cur = db.cursor()

            cur.execute(
                """
                SELECT *
                FROM deposits
                WHERE id=?
                """,
                (deposit_id,),
            )

            deposit = cur.fetchone()

            if not deposit:

                await query.answer(
                    "❌ درخواست پیدا نشد.",
                    show_alert=True,
                )

                return

            if deposit["status"] != "pending":

                await query.answer(
                    "⚠️ این درخواست قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            if action == "deposit_approve":

                cur.execute(
                    """
                    UPDATE deposits
                    SET status='approved'
                    WHERE id=?
                    AND status='pending'
                    """,
                    (deposit_id,),
                )

                if cur.rowcount != 1:

                    db.rollback()

                    await query.answer(
                        "⚠️ قبلاً پردازش شده.",
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

                db.commit()

                message = (
                    "✅ واریزی تأیید شد.\n\n"
                    f"💰 {deposit['amount']:,} DOGS"
                )

            else:

                cur.execute(
                    """
                    UPDATE deposits
                    SET status='rejected'
                    WHERE id=?
                    AND status='pending'
                    """,
                    (deposit_id,),
                )

                if cur.rowcount != 1:

                    db.rollback()

                    await query.answer(
                        "⚠️ قبلاً پردازش شده.",
                        show_alert=True,
                    )

                    return

                db.commit()

                message = (
                    "❌ واریزی رد شد.\n\n"
                    f"💰 {deposit['amount']:,} DOGS"
                )

        if action == "deposit_approve":

            add_transaction(
                deposit["user_id"],
                "deposit",
                deposit["amount"],
                f"Deposit #{deposit_id}",
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
                text=message,
            )

        except Exception:
            pass

        await query.answer(
            "✅ انجام شد.",
            show_alert=False,
        )

        return

    # ========================================================
    # WITHDRAW
    # ========================================================

    if data.startswith("withdraw_"):

        if not admin_only(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )

            return

        try:

            action, id_text = data.split(":")

            withdrawal_id = int(id_text)

        except Exception:

            return

        with db_lock:

            cur = db.cursor()

            cur.execute(
                """
                SELECT *
                FROM withdrawals
                WHERE id=?
                """,
                (withdrawal_id,),
            )

            withdrawal = cur.fetchone()

            if not withdrawal:

                await query.answer(
                    "❌ درخواست پیدا نشد.",
                    show_alert=True,
                )

                return

            if withdrawal["status"] != "pending":

                await query.answer(
                    "⚠️ قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            if action == "withdraw_approve":

                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='approved'
                    WHERE id=?
                    AND status='pending'
                    """,
                    (withdrawal_id,),
                )

                if cur.rowcount != 1:

                    db.rollback()

                    await query.answer(
                        "⚠️ قبلاً پردازش شده.",
                        show_alert=True,
                    )

                    return

                db.commit()

                message = (
                    "✅ برداشت شما تأیید شد.\n\n"
                    f"💰 مبلغ: {withdrawal['amount']:,} DOGS\n"
                    f"📍 مقصد: {withdrawal['destination']}"
                )

            else:

                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='rejected'
                    WHERE id=?
                    AND status='pending'
                    """,
                    (withdrawal_id,),
                )

                if cur.rowcount != 1:

                    db.rollback()

                    await query.answer(
                        "⚠️ قبلاً پردازش شده.",
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
                        withdrawal["amount"],
                        withdrawal["user_id"],
                    ),
                )

                db.commit()

                message = (
                    "❌ برداشت شما رد شد.\n\n"
                    f"💰 {withdrawal['amount']:,} DOGS "
                    "به موجودی شما برگشت."
                )

        try:

            await query.edit_message_reply_markup(
                reply_markup=None
            )

        except Exception:
            pass

        try:

            await context.bot.send_message(
                chat_id=withdrawal["user_id"],
                text=message,
            )

        except Exception:
            pass

        await query.answer(
            "✅ انجام شد.",
            show_alert=False,
        )

        return

    # ========================================================
    # ADMIN ONLY BELOW
    # ========================================================

    if not admin_only(user_id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    # ========================================================
    # BALANCES
    # ========================================================

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
                f"💰 {u['balance']:,} DOGS\n\n"
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

    # ========================================================
    # DEPOSITS LIST
    # ========================================================

    if data == "admin_deposits":

        rows = execute(
            """
            SELECT *
            FROM deposits
            ORDER BY id DESC
            LIMIT 30
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

    # ========================================================
    # WITHDRAWALS LIST
    # ========================================================

    if data == "admin_withdrawals":

        rows = execute(
            """
            SELECT *
            FROM withdrawals
            ORDER BY id DESC
            LIMIT 30
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

    # ========================================================
    # STATS
    # ========================================================

    if data == "admin_stats":

        users = execute(
            "SELECT COUNT(*) AS c FROM users",
            fetchone=True,
        )["c"]

        total_balance = execute(
            """
            SELECT COALESCE(SUM(balance),0) AS s
            FROM users
            """,
            fetchone=True,
        )["s"]

        referrals_count = execute(
            """
            SELECT COUNT(*) AS c
            FROM referrals
            """,
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
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"👥 رفرال‌ها: {referrals_count}\n"
            f"🎮 بازی‌های انجام‌شده: {games}\n"
            f"🎁 رفرال: {get_referral_reward():,} DOGS\n"
            f"👑 سهم مالک بازی: {GAME_OWNER_FEE:,} DOGS\n"
            f"🎮 حداقل بازی: {GAME_MIN:,} DOGS\n"
            f"🔘 وضعیت ربات: "
            f"{'روشن' if is_bot_enabled() else 'خاموش'}"
        )

        return

    # ========================================================
    # GAME SETTINGS
    # ========================================================

    if data == "admin_game":

        await query.message.reply_text(
            "🎮 تنظیمات بازی\n\n"
            f"حداقل بازی: {GAME_MIN:,} DOGS\n"
            "حداکثر: ندارد\n"
            f"سهم مالک: {GAME_OWNER_FEE:,} DOGS\n\n"
            "مثال داخل گروه:\n"
            "بازی 500"
        )

        return

    # ========================================================
    # TOGGLE BOT
    # ========================================================

    if data == "admin_toggle_bot":

        new_status = not is_bot_enabled()

        set_bot_enabled(new_status)

        status = (
            "🟢 روشن"
            if new_status
            else "🔴 خاموش"
        )

        try:

            await query.edit_message_text(
                f"⚙️ وضعیت ربات تغییر کرد.\n\n"
                f"وضعیت فعلی: {status}",
                reply_markup=admin_keyboard(),
            )

        except Exception:

            await query.message.reply_text(
                f"وضعیت فعلی: {status}",
                reply_markup=admin_keyboard(),
            )

        return

    # ========================================================
    # REFERRAL REWARD
    # ========================================================

    if data == "admin_referral_reward":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_referral_reward"
        )

        await query.message.reply_text(
            f"🎁 جایزه فعلی: "
            f"{get_referral_reward():,} DOGS\n\n"
            "مقدار جدید را وارد کنید:"
        )

        return

    # ========================================================
    # TRANSFER OWNER
    # ========================================================

    if data == "admin_transfer_owner":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_transfer_owner"
        )

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را وارد کنید."
        )

        return

    # ========================================================
    # ADD BALANCE
    # ========================================================

    if data == "admin_add_balance":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_add_balance"
        )

        await query.message.reply_text(
            "➕ فرمت:\n\n"
            "123456789 5000"
        )

        return

    # ========================================================
    # REMOVE BALANCE
    # ========================================================

    if data == "admin_remove_balance":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_remove_balance"
        )

        await query.message.reply_text(
            "➖ فرمت:\n\n"
            "123456789 5000"
        )

        return

    # ========================================================
    # BLOCK
    # ========================================================

    if data == "admin_block":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_block"
        )

        await query.message.reply_text(
            "🚫 آیدی کاربر را وارد کنید:"
        )

        return

    # ========================================================
    # BROADCAST
    # ========================================================

    if data == "admin_broadcast":

        context.user_data.clear()

        context.user_data["state"] = (
            "admin_broadcast"
        )

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید."
        )

        return


# ============================================================
# ADMIN TEXT STATES
# ============================================================

async def admin_state_handler(
    update,
    context,
):

    user = get_user(update.effective_user.id)

    if not user:
        return False

    if user["id"] != get_owner_id():
        return False

    state = context.user_data.get("state")

    if not state:
        return False

    text = (
        update.message.text.strip()
        if update.message.text
        else ""
    )

    # --------------------------------------------------------
    # SUPPORT ADMIN REPLY
    # --------------------------------------------------------

    if state == "support_admin_reply":

        target_id = context.user_data.get(
            "support_user_id"
        )

        if not target_id:
            context.user_data.clear()
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
                WHERE user_id=?
                AND status='pending'
                """,
                (target_id,),
            )

            await update.message.reply_text(
                "✅ پاسخ ارسال شد.",
                reply_markup=main_keyboard(
                    user["id"]
                ),
            )

        except Exception:

            await update.message.reply_text(
                "❌ ارسال پاسخ انجام نشد."
            )

        context.user_data.clear()

        return True

    # --------------------------------------------------------
    # REFERRAL REWARD
    # --------------------------------------------------------

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
            f"🎁 {amount:,} DOGS",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    # --------------------------------------------------------
    # OWNER
    # --------------------------------------------------------

    if state == "admin_transfer_owner":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
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
            "Owner changed %s -> %s",
            old_owner,
            new_owner,
        )

        return True

    # --------------------------------------------------------
    # ADD / REMOVE
    # --------------------------------------------------------

    if state in (
        "admin_add_balance",
        "admin_remove_balance",
    ):

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "❌ فرمت صحیح:\n"
                "123456789 5000"
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
                "❌ مبلغ نامعتبر است."
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

            add_transaction(
                target_id,
                "admin_add",
                amount,
                "Admin balance add",
            )

            message = (
                f"✅ {amount:,} DOGS "
                f"به کاربر {target_id} اضافه شد."
            )

        else:

            with db_lock:

                cur = db.cursor()

                cur.execute(
                    """
                    UPDATE users
                    SET balance=balance-?
                    WHERE id=?
                    AND balance>=?
                    """,
                    (
                        amount,
                        target_id,
                        amount,
                    ),
                )

                if cur.rowcount != 1:

                    db.rollback()

                    await update.message.reply_text(
                        "❌ موجودی کاربر کافی نیست."
                    )

                    return True

                db.commit()

            add_transaction(
                target_id,
                "admin_remove",
                -amount,
                "Admin balance remove",
            )

            message = (
                f"✅ {amount:,} DOGS "
                f"از کاربر {target_id} کم شد."
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

    # --------------------------------------------------------
    # BLOCK
    # --------------------------------------------------------

    if state == "admin_block":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ ID عددی وارد کنید."
            )

            return True

        target_id = int(text)

        if target_id == get_owner_id():

            await update.message.reply_text(
                "❌ نمی‌توانید مالک را مسدود کنید."
            )

            return True

        target = get_user(target_id)

        if not target:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )

            return True

        new_status = (
            0 if target["blocked"] else 1
        )

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

        status = (
            "مسدود شد"
            if new_status
            else "آزاد شد"
        )

        await update.message.reply_text(
            f"✅ کاربر {target_id} {status}.",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    # --------------------------------------------------------
    # BROADCAST
    # --------------------------------------------------------

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
            f"📢 پیام همگانی ارسال شد.\n\n"
            f"👥 ارسال موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    return False


# ============================================================
# CANCEL
# ============================================================

async def cancel(
    update,
    context,
):

    user = create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# ============================================================
# TEXT ROUTER
# ============================================================

async def text_router(
    update,
    context,
):

    if not update.message:
        return

    user = create_or_update_user(
        update.effective_user
    )

    # --------------------------------------------------------
    # CANCEL
    # --------------------------------------------------------

    if update.message.text == "❌ لغو":

        await cancel(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # OWNER REPLY SUPPORT
    # --------------------------------------------------------

    if user["id"] == get_owner_id():

        if await handle_owner_reply(
            update,
            context,
        ):

            return

    # --------------------------------------------------------
    # CONTACT VERIFICATION
    # --------------------------------------------------------

    if not is_verified(user["id"]):

        if user["id"] != get_owner_id():

            await update.message.reply_text(
                "🔐 ابتدا شماره خود را تأیید کنید.",
                reply_markup=verification_keyboard(),
            )

            return

    # --------------------------------------------------------
    # BLOCK
    # --------------------------------------------------------

    if user["blocked"]:

        await update.message.reply_text(
            "🚫 حساب شما مسدود است."
        )

        return

    # --------------------------------------------------------
    # OWNER ADMIN STATES
    # --------------------------------------------------------

    if user["id"] == get_owner_id():

        if await admin_state_handler(
            update,
            context,
        ):

            return

    # --------------------------------------------------------
    # BOT OFF
    # --------------------------------------------------------

    if not is_bot_enabled():

        if user["id"] != get_owner_id():

            await update.message.reply_text(
                "🔴 ربات خاموش است."
            )

            return

    # --------------------------------------------------------
    # CURRENT STATE
    # --------------------------------------------------------

    state = context.user_data.get("state")

    if state == "deposit_amount":

        await deposit_amount(
            update,
            context,
        )

        return

    if state == "deposit_receipt":

        await deposit_receipt(
            update,
            context,
        )

        return

    if state == "withdraw_amount":

        await withdraw_amount(
            update,
            context,
        )

        return

    if state == "withdraw_destination":

        await withdraw_destination(
            update,
            context,
        )

        return

    if state == "transfer_amount":

        await transfer_amount(
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

    # --------------------------------------------------------
    # SUPPORT ADMIN REPLY
    # --------------------------------------------------------

    if state == "support_admin_reply":

        await admin_state_handler(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    text = update.message.text.strip()

    if text in (
        "💳 موجودی",
        "موجودی",
    ):

        await balance(
            update,
            context,
        )

        return

    if text == "💰 واریزی":

        await deposit_start(
            update,
            context,
        )

        return

    if text == "💸 برداشت":

        await withdraw_start(
            update,
            context,
        )

        return

    if text == "🔄 انتقال":

        await transfer_start(
            update,
            context,
        )

        return

    if text == "👥 زیرمجموعه":

        await referrals(
            update,
            context,
        )

        return

    if text == "🎧 پشتیبانی":

        await support_start(
            update,
            context,
        )

        return

    if text == "🛠 پنل مدیریت":

        await admin_panel(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # GAME
    # --------------------------------------------------------

    game_match = re.fullmatch(
        r"بازی\s+([0-9]+)",
        text,
    )

    if game_match:

        amount = int(
            game_match.group(1)
        )

        await game_create(
            update,
            context,
            amount,
        )

        return

    # --------------------------------------------------------
    # OLD TRANSFER COMMANDS DISABLED
    # --------------------------------------------------------

    if text.startswith("انتقال"):

        await update.message.reply_text(
            "🔄 انتقال فقط با Reply انجام می‌شود.\n\n"
            "روی پیام گیرنده Reply کنید و مبلغ را بفرستید.\n\n"
            "مثال:\n"
            "5000"
        )

        return

    # --------------------------------------------------------
    # COMMAND-LIKE TEXT
    # --------------------------------------------------------

    if text.lower() in (
        "شروع",
        "start",
    ):

        await start(
            update,
            context,
        )

        return

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    await update.message.reply_text(
        "❓ دستور نامعتبر است.\n\n"
        "از دکمه‌های ربات استفاده کنید."
    )


# ============================================================
# MEDIA ROUTER
# ============================================================

async def media_router(
    update,
    context,
):

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:
        return

    if user["id"] != get_owner_id():

        if not is_bot_enabled():
            return

        if not is_verified(user["id"]):

            await update.message.reply_text(
                "🔐 ابتدا شماره خود را تأیید کنید.",
                reply_markup=verification_keyboard(),
            )

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

    # Owner broadcast media
    if (
        user["id"] == get_owner_id()
        and state == "admin_broadcast"
    ):

        await admin_state_handler(
            update,
            context,
        )

        return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


# ============================================================
# COMMANDS
# ============================================================

async def balance_command(
    update,
    context,
):

    await balance(
        update,
        context,
    )


async def game_command(
    update,
    context,
):

    if not update.message:
        return

    if not context.args:

        await update.message.reply_text(
            "🎮 مثال:\n\n"
            "بازی 500\n\n"
            f"حداقل: {GAME_MIN:,} DOGS\n"
            "حداکثر: ندارد"
        )

        return

    try:

        amount = int(
            context.args[0]
        )

    except Exception:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return

    await game_create(
        update,
        context,
        amount,
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "BOT ERROR",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

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

    # Callback buttons
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
            filters.PHOTO
            | filters.Document.ALL,
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

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "DOGS BOT STARTED"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
