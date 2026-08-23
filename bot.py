# =========================================================
# TAK BET - bot.py
# Python 3.10+
# python-telegram-bot 20+
# =========================================================

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

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DEFAULT_REFERRAL_REWARD = 50

GAME_MIN = 500
GAME_OWNER_FEE = 50

DB_FILE = "bot.db"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("takbet")

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

        try:
            cur.execute(query, params)
            db.commit()

            if fetchone:
                return cur.fetchone()

            if fetchall:
                return cur.fetchall()

            return None

        except Exception:
            db.rollback()
            raise


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
            phone TEXT,
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
            owner_message_id INTEGER,
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
            owner_message_id INTEGER,
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

    # -------------------------
    # USERS MIGRATION
    # -------------------------

    columns = execute(
        "PRAGMA table_info(users)",
        fetchall=True,
    )

    names = {x["name"] for x in columns}

    if "verified" not in names:
        execute(
            "ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0"
        )

    if "phone" not in names:
        execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
        )

    # -------------------------
    # DEPOSITS MIGRATION
    # -------------------------

    columns = execute(
        "PRAGMA table_info(deposits)",
        fetchall=True,
    )

    names = {x["name"] for x in columns}

    if "owner_message_id" not in names:
        execute(
            "ALTER TABLE deposits ADD COLUMN owner_message_id INTEGER"
        )

    # -------------------------
    # SUPPORT MIGRATION
    # -------------------------

    columns = execute(
        "PRAGMA table_info(support_messages)",
        fetchall=True,
    )

    names = {x["name"] for x in columns}

    if "owner_message_id" not in names:
        execute(
            "ALTER TABLE support_messages ADD COLUMN owner_message_id INTEGER"
        )

    # -------------------------
    # SETTINGS
    # -------------------------

    if not execute(
        "SELECT value FROM settings WHERE key='owner_id'",
        fetchone=True,
    ):
        execute(
            "INSERT INTO settings(key,value) VALUES('owner_id',?)",
            (str(INITIAL_OWNER_ID),),
        )

    if not execute(
        "SELECT value FROM settings WHERE key='referral_reward'",
        fetchone=True,
    ):
        execute(
            "INSERT INTO settings(key,value) VALUES('referral_reward',?)",
            (str(DEFAULT_REFERRAL_REWARD),),
        )

    if not execute(
        "SELECT value FROM settings WHERE key='bot_enabled'",
        fetchone=True,
    ):
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

    try:
        return int(
            get_setting(
                "owner_id",
                INITIAL_OWNER_ID,
            )
        )
    except Exception:
        return INITIAL_OWNER_ID


def set_owner_id(user_id):
    set_setting("owner_id", user_id)


def get_referral_reward():

    try:
        return int(
            get_setting(
                "referral_reward",
                DEFAULT_REFERRAL_REWARD,
            )
        )
    except Exception:
        return DEFAULT_REFERRAL_REWARD


def set_referral_reward(amount):
    set_setting("referral_reward", amount)


def bot_enabled():
    return get_setting("bot_enabled", "1") == "1"


def set_bot_enabled(enabled):
    set_setting(
        "bot_enabled",
        "1" if enabled else "0",
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

    if not tg_user:
        return None

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
            verified,
            phone,
            created_at
        )
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
        return "@" + user["username"]

    return user["first_name"] or str(user["id"])


def is_blocked(user_id):

    user = get_user(user_id)

    return bool(
        user and user["blocked"]
    )


def is_verified(user_id):

    user = get_user(user_id)

    return bool(
        user and user["verified"]
    )


def admin_only(user_id):
    return user_id == get_owner_id()


# =========================================================
# ACCESS
# =========================================================

def operation_allowed(user_id):

    if not bot_enabled():

        if admin_only(user_id):
            return True

        return False

    return True


# =========================================================
# KEYBOARDS
# =========================================================

def verification_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 تایید شماره",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_keyboard(user_id):

    rows = [
        ["💳 موجودی", "💰 واریزی"],
        ["💸 برداشت", "🔄 انتقال"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
    ]

    if admin_only(user_id):
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
        "🟢 ربات روشن است"
        if bot_enabled()
        else "🔴 ربات خاموش است"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    status,
                    callback_data="admin_toggle_bot",
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_transfer_owner",
                )
            ],
            [
                InlineKeyboardButton(
                    "➕ شارژ موجودی",
                    callback_data="admin_add_balance",
                ),
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="admin_remove_balance",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎁 جایزه زیرمجموعه",
                    callback_data="admin_referral_reward",
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
                    "👥 کاربران",
                    callback_data="admin_balances",
                ),
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats",
                ),
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
        ]
    )


# =========================================================
# SAFE CALLBACK
# =========================================================

async def safe_query_answer(query, text=None, alert=False):

    if not query:
        return

    try:

        if text:
            await query.answer(
                text=text,
                show_alert=alert,
            )
        else:
            await query.answer()

    except Exception:
        pass


# =========================================================
# START
# =========================================================

async def start(update, context):

    if not update.effective_user:
        return

    # ضد state قدیمی
    context.user_data.clear()

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if user["blocked"]:

        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 برای استفاده از ربات ابتدا شماره خود را تأیید کنید.\n\n"
            "روی دکمه «📱 تایید شماره» بزنید.",
            reply_markup=verification_keyboard(),
        )

        return

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به ربات خوش آمدید ❤️\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# CONTACT
# =========================================================

async def contact_handler(update, context):

    if not update.message or not update.effective_user:
        return

    contact = update.message.contact
    tg_user = update.effective_user

    if not contact:
        return

    if contact.user_id != tg_user.id:

        await update.message.reply_text(
            "❌ باید شماره خودتان را ارسال کنید."
        )
        return

    create_or_update_user(tg_user)

    execute(
        """
        UPDATE users
        SET verified=1, phone=?
        WHERE id=?
        """,
        (
            contact.phone_number,
            tg_user.id,
        ),
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تأیید شد.\n\n"
        "🎉 حالا می‌توانید از ربات استفاده کنید.",
        reply_markup=main_keyboard(tg_user.id),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if user["blocked"]:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    await update.message.reply_text(
        "💳 موجودی شما:\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    if not user:
        return

    if user["blocked"]:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    if not operation_allowed(user["id"]):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )
        return

    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        "💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل واریزی: {MIN_DEPOSIT:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def deposit_amount(update, context):

    if not update.message.text:
        return

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    try:
        amount = int(text)
    except (ValueError, OverflowError):

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(
            f"❌ حداقل واریزی {MIN_DEPOSIT:,} DOGS است."
        )
        return

    context.user_data["deposit_amount"] = amount
    context.user_data["state"] = "deposit_receipt"

    await update.message.reply_text(
        "💰 مبلغ واریزی:\n"
        f"{amount:,} DOGS\n\n"
        "فرمت واریز:\n\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از پرداخت، رسید را به صورت عکس یا متن ارسال کنید.",
        reply_markup=cancel_keyboard(),
    )


async def deposit_receipt(update, context):

    amount = context.user_data.get(
        "deposit_amount"
    )

    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست منقضی شده است.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
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
        receipt_file_id = update.message.photo[-1].file_id

    elif update.message.document:

        receipt_type = "document"
        receipt_file_id = update.message.document.file_id

    elif update.message.text:

        receipt_type = "text"
        receipt_text = update.message.text

    else:

        await update.message.reply_text(
            "❌ عکس یا متن رسید ارسال کنید."
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

    deposit = execute(
        """
        SELECT * FROM deposits
        ORDER BY id DESC
        LIMIT 1
        """,
        fetchone=True,
    )

    deposit_id = deposit["id"]

    caption = (
        "💰 درخواست واریزی\n\n"
        f"🆔 #{deposit_id}\n"
        f"👤 {user['first_name'] or '-'}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}\n"
        f"💰 مبلغ: {amount:,} DOGS"
    )

    keyboard = InlineKeyboardMarkup(
        [
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
        ]
    )

    try:

        if receipt_type == "photo":

            sent = await context.bot.send_photo(
                chat_id=get_owner_id(),
                photo=receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        elif receipt_type == "document":

            sent = await context.bot.send_document(
                chat_id=get_owner_id(),
                document=receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        else:

            sent = await context.bot.send_message(
                chat_id=get_owner_id(),
                text=caption + f"\n\n📝 رسید:\n{receipt_text}",
                reply_markup=keyboard,
            )

        execute(
            """
            UPDATE deposits
            SET owner_message_id=?
            WHERE id=?
            """,
            (
                sent.message_id,
                deposit_id,
            ),
        )

    except Exception as e:

        logger.exception(
            "Could not send deposit to owner: %s",
            e,
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ در انتظار تأیید مالک هستید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    if not user:
        return

    if user["blocked"]:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    if not operation_allowed(user["id"]):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )
        return

    if user["balance"] < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n\n"
            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
            f"موجودی شما: {user['balance']:,} DOGS"
        )
        return

    context.user_data["state"] = "withdraw_amount"

    await update.message.reply_text(
        f"💸 مبلغ برداشت را وارد کنید.\n\n"
        f"حداقل: {MIN_WITHDRAW:,} DOGS\n"
        f"موجودی: {user['balance']:,} DOGS",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_amount(update, context):

    if not update.message.text:
        return

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    try:
        amount = int(text)
    except (ValueError, OverflowError):

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    user = get_user(
        update.effective_user.id
    )

    if not user or user["balance"] < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    context.user_data["withdraw_amount"] = amount
    context.user_data["state"] = "withdraw_destination"

    await update.message.reply_text(
        "📍 مقصد برداشت را وارد کنید:\n\n"
        "مثال:\n"
        "@username\n"
        "یا\n"
        "123456789",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_destination(update, context):

    if not update.message.text:
        return

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

        await update.message.reply_text(
            "❌ درخواست منقضی شده است.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )
        return

    user_id = update.effective_user.id

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
                user_id,
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
                user_id,
                amount,
                destination,
                "pending",
                datetime.now().isoformat(),
            ),
        )

        withdrawal_id = cur.lastrowid

        db.commit()

    user = get_user(user_id)

    keyboard = InlineKeyboardMarkup(
        [
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
        ]
    )

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

    except Exception as e:

        logger.exception(
            "withdraw owner notify failed: %s",
            e,
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n"
        "⏳ در انتظار بررسی مالک.",
        reply_markup=main_keyboard(user_id),
    )


# =========================================================
# TRANSFER
# =========================================================

async def transfer_by_reply(update, context):

    message = update.message

    if not message.reply_to_message:

        await message.reply_text(
            "❌ انتقال فقط با Reply انجام می‌شود.\n\n"
            "روی پیام کاربر Reply کنید و بنویسید:\n"
            "انتقال 500"
        )
        return

    if not message.text:
        return

    match = re.fullmatch(
        r"\s*انتقال\s+(\d+)\s*",
        message.text,
    )

    if not match:
        return

    try:
        amount = int(match.group(1))
    except (ValueError, OverflowError):

        await message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    if amount <= 0:

        await message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    sender_id = update.effective_user.id
    receiver_tg = message.reply_to_message.from_user

    if not receiver_tg or receiver_tg.is_bot:

        await message.reply_text(
            "❌ این کاربر قابل انتقال نیست."
        )
        return

    sender = get_user(sender_id)
    receiver = get_user(receiver_tg.id)

    if not sender or not sender["verified"]:

        await message.reply_text(
            "🔐 ابتدا در خصوصی ربات شماره خود را تأیید کنید."
        )
        return

    if not receiver:
        receiver = create_or_update_user(receiver_tg)

    if not receiver["verified"]:

        await message.reply_text(
            "❌ گیرنده هنوز شماره خود را تأیید نکرده است."
        )
        return

    if sender_id == receiver_tg.id:

        await message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    if not operation_allowed(sender_id):

        await message.reply_text(
            "🔴 ربات خاموش است؛ موجودی کسر نشد."
        )
        return

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

            await message.reply_text(
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
                receiver_tg.id,
            ),
        )

        now = datetime.now().isoformat()

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
                receiver_tg.id,
                amount,
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
                sender_id,
                "transfer_out",
                -amount,
                f"To {receiver_tg.id}",
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
                receiver_tg.id,
                "transfer_in",
                amount,
                f"From {sender_id}",
                now,
            ),
        )

        db.commit()

    await message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {user_name(receiver)}"
    )

    try:

        await context.bot.send_message(
            chat_id=receiver_tg.id,
            text=(
                "💰 انتقال جدید دریافت کردید.\n\n"
                f"مبلغ: {amount:,} DOGS\n"
                f"از: {user_name(sender)}"
            ),
        )

    except Exception:
        pass


# =========================================================
# REFERRALS
# =========================================================

async def referrals(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    bot = await context.bot.get_me()

    count = execute(
        """
        SELECT COUNT(*) AS c
        FROM referrals
        WHERE referrer_id=?
        """,
        (user["id"],),
        fetchone=True,
    )["c"]

    link = (
        f"https://t.me/{bot.username}"
        f"?start=ref_{user['id']}"
    )

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"👤 تعداد: {count}\n"
        f"🎁 جایزه هر نفر: {get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    if not user:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را ارسال کنید.\n\n"
        "متن، عکس یا فایل قابل ارسال است.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(update, context):

    user = create_or_update_user(
        update.effective_user
    )

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
            "❌ این نوع پیام پشتیبانی پشتیبانی نمی‌شود."
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

    support = execute(
        """
        SELECT * FROM support_messages
        ORDER BY id DESC
        LIMIT 1
        """,
        fetchone=True,
    )

    support_id = support["id"]

    caption = (
        "🎧 پیام پشتیبانی\n\n"
        f"🆔 #{support_id}\n"
        f"👤 {user['first_name'] or '-'}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}\n\n"
        "↩️ برای پاسخ، روی همین پیام Reply کنید."
    )

    try:

        if file_type == "photo":

            sent = await context.bot.send_photo(
                chat_id=get_owner_id(),
                photo=file_id,
                caption=caption,
            )

        elif file_type == "document":

            sent = await context.bot.send_document(
                chat_id=get_owner_id(),
                document=file_id,
                caption=caption,
            )

        else:

            sent = await context.bot.send_message(
                chat_id=get_owner_id(),
                text=caption + f"\n\n📝 {text}",
            )

        execute(
            """
            UPDATE support_messages
            SET owner_message_id=?
            WHERE id=?
            """,
            (
                sent.message_id,
                support_id,
            ),
        )

    except Exception as e:

        logger.exception(
            "support notify failed: %s",
            e,
        )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای مالک ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# OWNER SUPPORT REPLY
# =========================================================

async def owner_reply_support(update, context):

    if not admin_only(update.effective_user.id):
        return False

    if not update.message.reply_to_message:
        return False

    replied_id = update.message.reply_to_message.message_id

    support = execute(
        """
        SELECT * FROM support_messages
        WHERE owner_message_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (replied_id,),
        fetchone=True,
    )

    if not support:
        return False

    if not update.message.text:
        return False

    answer = update.message.text.strip()

    if not answer:
        return True

    try:

        await context.bot.send_message(
            chat_id=support["user_id"],
            text=(
                "🎧 پاسخ پشتیبانی\n\n"
                f"{answer}"
            ),
        )

        execute(
            """
            UPDATE support_messages
            SET status='answered'
            WHERE id=?
            """,
            (support["id"],),
        )

        await update.message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

    except Exception:

        await update.message.reply_text(
            "❌ ارسال پاسخ انجام نشد."
        )

    return True


# =========================================================
# GAME
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup(
        [
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
        ]
    )


async def create_game(update, context, amount):

    if update.effective_chat.type not in (
        "group",
        "supergroup",
    ):

        await update.message.reply_text(
            "❌ بازی باید داخل گروه ساخته شود."
        )
        return

    user = get_user(
        update.effective_user.id
    )

    if not user or not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا در خصوصی ربات /start را بزنید و شماره خود را تأیید کنید."
        )
        return

    if user["blocked"]:
        return

    if not operation_allowed(user["id"]):

        await update.message.reply_text(
            "🔴 ربات خاموش است؛ هیچ موجودی کسر نمی‌شود."
        )
        return

    if amount < GAME_MIN:

        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی {GAME_MIN:,} DOGS است."
        )
        return

    if user["balance"] < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    existing = execute(
        """
        SELECT * FROM games
        WHERE creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:

        await update.message.reply_text(
            "❌ شما یک بازی در انتظار ورود بازیکن دارید."
        )
        return

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

    try:

        sent = await update.message.reply_text(
            "🎮 بازی جدید\n\n"
            f"💰 مبلغ ورود: {amount:,} DOGS\n"
            f"👤 سازنده: {user_name(user)}\n\n"
            "یک نفر می‌تواند وارد بازی شود.\n"
            "بعد از ورود، بازی فوراً انجام می‌شود.",
            reply_markup=game_keyboard(game_id),
        )

    except Exception:

        # اگر ارسال پیام بازی شکست خورد، پول برگردد
        with db_lock:

            cur = db.cursor()

            cur.execute(
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

            cur.execute(
                """
                UPDATE games
                SET status='cancelled'
                WHERE id=?
                AND status='waiting'
                """,
                (game_id,),
            )

            db.commit()

        raise

    execute(
        """
        UPDATE games
        SET message_id=?
        WHERE id=?
        """,
        (
            sent.message_id,
            game_id,
        ),
    )


async def finish_game(game_id, opponent_id, context):

    with db_lock:

        game = execute(
            """
            SELECT * FROM games
            WHERE id=?
            """,
            (game_id,),
            fetchone=True,
        )

        if not game:
            return False

        if game["status"] != "waiting":
            return False

        creator_id = game["creator_id"]
        amount = game["amount"]

        if creator_id == opponent_id:
            return False

        opponent = execute(
            """
            SELECT * FROM users
            WHERE id=?
            """,
            (opponent_id,),
            fetchone=True,
        )

        if not opponent or opponent["balance"] < amount:
            return False

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
                opponent_id,
                amount,
            ),
        )

        if cur.rowcount != 1:

            db.rollback()
            return False

        winner_id, loser_id = random.sample(
            [creator_id, opponent_id],
            2,
        )

        total = amount * 2
        owner_fee = GAME_OWNER_FEE
        winner_prize = total - owner_fee

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
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                owner_fee,
                get_owner_id(),
            ),
        )

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
                winner_id,
                "game_win",
                winner_prize,
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
                loser_id,
                "game_loss",
                -amount,
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
                get_owner_id(),
                "game_fee",
                owner_fee,
                f"Game fee #{game_id}",
                now,
            ),
        )

        cur.execute(
            """
            UPDATE games
            SET
                opponent_id=?,
                status='finished',
                winner_id=?,
                loser_id=?
            WHERE id=?
            AND status='waiting'
            """,
            (
                opponent_id,
                winner_id,
                loser_id,
                game_id,
            ),
        )

        if cur.rowcount != 1:

            db.rollback()
            return False

        db.commit()

    try:

        await context.bot.edit_message_text(
            chat_id=game["chat_id"],
            message_id=game["message_id"],
            text=(
                "🎮 بازی انجام شد!\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🏆 برنده: {winner_id}\n"
                f"❌ بازنده: {loser_id}\n\n"
                f"🎁 جایزه برنده: {winner_prize:,} DOGS\n"
                f"👑 سهم مالک: {owner_fee:,} DOGS"
            ),
        )

    except Exception:

        try:

            await context.bot.edit_message_reply_markup(
                chat_id=game["chat_id"],
                message_id=game["message_id"],
                reply_markup=None,
            )

        except Exception:
            pass

    try:

        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 شما برنده بازی شدید!\n\n"
                f"💰 مبلغ ورود: {amount:,} DOGS\n"
                f"🎁 جایزه: {winner_prize:,} DOGS"
            ),
        )

    except Exception:
        pass

    try:

        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "❌ شما بازی را باختید.\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS"
            ),
        )

    except Exception:
        pass

    try:

        await context.bot.send_message(
            chat_id=get_owner_id(),
            text=(
                "🎮 بازی جدید تمام شد.\n\n"
                f"🆔 بازی: #{game_id}\n"
                f"🏆 برنده: {winner_id}\n"
                f"❌ بازنده: {loser_id}\n"
                f"👑 سهم مالک: {owner_fee:,} DOGS"
            ),
        )

    except Exception:
        pass

    return True


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(update, context):

    query = update.callback_query

    if not query:
        return

    user_id = query.from_user.id
    data = query.data or ""

    # =====================================================
    # GAME JOIN
    # =====================================================

    if data.startswith("game_join:"):

        try:

            game_id = int(
                data.split(":", 1)[1]
            )

        except (ValueError, TypeError, IndexError):

            await safe_query_answer(
                query,
                "❌ دکمه نامعتبر است.",
                True,
            )
            return

        user = get_user(user_id)

        if not user or not user["verified"]:

            await safe_query_answer(
                query,
                "🔐 ابتدا شماره خود را در خصوصی تأیید کنید.",
                True,
            )
            return

        if user["blocked"]:

            await safe_query_answer(
                query,
                "🚫 حساب شما مسدود است.",
                True,
            )
            return

        if not bot_enabled():

            await safe_query_answer(
                query,
                "🔴 ربات خاموش است و موجودی کسر نمی‌شود.",
                True,
            )
            return

        game = execute(
            """
            SELECT * FROM games
            WHERE id=?
            """,
            (game_id,),
            fetchone=True,
        )

        if not game:

            await safe_query_answer(
                query,
                "❌ بازی پیدا نشد.",
                True,
            )
            return

        if game["status"] != "waiting":

            await safe_query_answer(
                query,
                "❌ این بازی قبلاً وارد شده یا تمام شده.",
                True,
            )
            return

        if game["creator_id"] == user_id:

            await safe_query_answer(
                query,
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                True,
            )
            return

        if user["balance"] < game["amount"]:

            await safe_query_answer(
                query,
                "❌ موجودی شما کافی نیست.",
                True,
            )
            return

        success = await finish_game(
            game_id,
            user_id,
            context,
        )

        if success:

            await safe_query_answer(
                query,
                "🎮 بازی انجام شد!",
                False,
            )

        else:

            await safe_query_answer(
                query,
                "❌ بازی دیگر قابل ورود نیست.",
                True,
            )

        return

    # =====================================================
    # GAME CANCEL
    # =====================================================

    if data.startswith("game_cancel:"):

        try:

            game_id = int(
                data.split(":", 1)[1]
            )

        except (ValueError, TypeError, IndexError):

            await safe_query_answer(
                query,
                "❌ دکمه نامعتبر است.",
                True,
            )
            return

        game = execute(
            """
            SELECT * FROM games
            WHERE id=?
            """,
            (game_id,),
            fetchone=True,
        )

        if not game:

            await safe_query_answer(
                query,
                "❌ بازی پیدا نشد.",
                True,
            )
            return

        if game["creator_id"] != user_id:

            await safe_query_answer(
                query,
                "⛔ فقط سازنده می‌تواند بازی را لغو کند.",
                True,
            )
            return

        with db_lock:

            cur = db.cursor()

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

                await safe_query_answer(
                    query,
                    "❌ بازی قبلاً لغو یا وارد شده.",
                    True,
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
                    user_id,
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
                    user_id,
                    "game_cancel",
                    game["amount"],
                    f"Game #{game_id}",
                    datetime.now().isoformat(),
                ),
            )

            db.commit()

        await safe_query_answer(
            query,
            "❌ بازی لغو شد.",
            False,
        )

        try:

            await query.edit_message_text(
                "❌ بازی لغو شد.\n\n"
                f"💰 {game['amount']:,} DOGS به موجودی سازنده برگشت."
            )

        except Exception:
            pass

        return

    # =====================================================
    # OWNER CHECK
    # =====================================================

    if not admin_only(user_id):

        await safe_query_answer(
            query,
            "⛔ دسترسی ندارید.",
            True,
        )
        return

    # =====================================================
    # TOGGLE BOT
    # =====================================================

    if data == "admin_toggle_bot":

        new_status = not bot_enabled()

        set_bot_enabled(new_status)

        status = (
            "🟢 ربات روشن شد."
            if new_status
            else
            "🔴 ربات خاموش شد.\n\n"
            "هیچ موجودی در حالت خاموش کسر نمی‌شود."
        )

        await safe_query_answer(
            query,
            "انجام شد.",
            False,
        )

        try:

            await query.edit_message_text(
                status,
                reply_markup=admin_keyboard(),
            )

        except Exception:

            try:

                await query.message.reply_text(
                    status,
                    reply_markup=admin_keyboard(),
                )

            except Exception:
                pass

        return

    # =====================================================
    # DEPOSIT
    # =====================================================

    if data.startswith("deposit_"):

        try:

            action, id_text = data.split(":", 1)
            deposit_id = int(id_text)

        except (ValueError, TypeError):

            await safe_query_answer(
                query,
                "❌ دکمه نامعتبر است.",
                True,
            )
            return

        deposit = execute(
            """
            SELECT * FROM deposits
            WHERE id=?
            """,
            (deposit_id,),
            fetchone=True,
        )

        if not deposit:

            await safe_query_answer(
                query,
                "❌ درخواست پیدا نشد.",
                True,
            )
            return

        if deposit["status"] != "pending":

            await safe_query_answer(
                query,
                "⚠️ این درخواست قبلاً بررسی شده.",
                True,
            )
            return

        if action == "deposit_approve":

            with db_lock:

                cur = db.cursor()

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

                    await safe_query_answer(
                        query,
                        "⚠️ قبلاً بررسی شده.",
                        True,
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

                db.commit()

            await safe_query_answer(
                query,
                "✅ واریزی تأیید شد.",
                False,
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
                        "✅ واریزی شما تأیید شد.\n\n"
                        f"💰 {deposit['amount']:,} DOGS"
                    ),
                )

            except Exception:
                pass

        elif action == "deposit_reject":

            with db_lock:

                cur = db.cursor()

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

                    await safe_query_answer(
                        query,
                        "⚠️ قبلاً بررسی شده.",
                        True,
                    )
                    return

                db.commit()

            await safe_query_answer(
                query,
                "❌ واریزی رد شد.",
                False,
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

        try:

            action, id_text = data.split(":", 1)
            withdrawal_id = int(id_text)

        except (ValueError, TypeError):

            await safe_query_answer(
                query,
                "❌ دکمه نامعتبر است.",
                True,
            )
            return

        withdrawal = execute(
            """
            SELECT * FROM withdrawals
            WHERE id=?
            """,
            (withdrawal_id,),
            fetchone=True,
        )

        if not withdrawal:

            await safe_query_answer(
                query,
                "❌ درخواست پیدا نشد.",
                True,
            )
            return

        if withdrawal["status"] != "pending":

            await safe_query_answer(
                query,
                "⚠️ قبلاً بررسی شده.",
                True,
            )
            return

        if action == "withdraw_approve":

            with db_lock:

                cur = db.cursor()

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

                    await safe_query_answer(
                        query,
                        "⚠️ قبلاً بررسی شده.",
                        True,
                    )
                    return

                db.commit()

            await safe_query_answer(
                query,
                "✅ برداشت تأیید شد.",
                False,
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
                    text=(
                        "✅ برداشت شما تأیید شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS\n"
                        f"📍 مقصد: {withdrawal['destination']}"
                    ),
                )

            except Exception:
                pass

        elif action == "withdraw_reject":

            with db_lock:

                cur = db.cursor()

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

                    await safe_query_answer(
                        query,
                        "⚠️ قبلاً بررسی شده.",
                        True,
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

            await safe_query_answer(
                query,
                "❌ برداشت رد شد و موجودی برگشت.",
                False,
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
                    text=(
                        "❌ برداشت شما رد شد.\n\n"
                        f"💰 {withdrawal['amount']:,} DOGS "
                        "به موجودی شما برگشت."
                    ),
                )

            except Exception:
                pass

        return

    # =====================================================
    # ADMIN ACTIONS
    # =====================================================

    if data == "admin_transfer_owner":

        context.user_data.clear()
        context.user_data["state"] = "admin_transfer_owner"

        await safe_query_answer(
            query,
            "مرحله انتقال مالکیت فعال شد.",
            False,
        )

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را ارسال کنید.",
            reply_markup=cancel_keyboard(),
        )

        return

    if data == "admin_add_balance":

        context.user_data.clear()
        context.user_data["state"] = "admin_add_balance"

        await safe_query_answer(
            query,
            "مرحله شارژ فعال شد.",
            False,
        )

        await query.message.reply_text(
            "➕ فرمت:\n\n"
            "123456789 5000",
            reply_markup=cancel_keyboard(),
        )

        return

    if data == "admin_remove_balance":

        context.user_data.clear()
        context.user_data["state"] = "admin_remove_balance"

        await safe_query_answer(
            query,
            "مرحله کسر موجودی فعال شد.",
            False,
        )

        await query.message.reply_text(
            "➖ فرمت:\n\n"
            "123456789 5000",
            reply_markup=cancel_keyboard(),
        )

        return

    if data == "admin_referral_reward":

        context.user_data.clear()
        context.user_data["state"] = "admin_referral_reward"

        await safe_query_answer(
            query,
            "مرحله جایزه فعال شد.",
            False,
        )

        await query.message.reply_text(
            f"🎁 جایزه فعلی: {get_referral_reward():,} DOGS\n\n"
            "مقدار جدید را وارد کنید:",
            reply_markup=cancel_keyboard(),
        )

        return

    if data == "admin_block":

        context.user_data.clear()
        context.user_data["state"] = "admin_block"

        await safe_query_answer(
            query,
            "مرحله مسدود/آزاد فعال شد.",
            False,
        )

        await query.message.reply_text(
            "🚫 آیدی کاربر را وارد کنید:",
            reply_markup=cancel_keyboard(),
        )

        return

    if data == "admin_broadcast":

        context.user_data.clear()
        context.user_data["state"] = "admin_broadcast"

        await safe_query_answer(
            query,
            "مرحله پیام همگانی فعال شد.",
            False,
        )

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید.",
            reply_markup=cancel_keyboard(),
        )

        return

    # =====================================================
    # ADMIN BALANCES
    # =====================================================

    if data == "admin_balances":

        context.user_data.clear()

        users = execute(
            """
            SELECT * FROM users
            ORDER BY balance DESC
            LIMIT 100
            """,
            fetchall=True,
        )

        if not users:

            await safe_query_answer(
                query,
                "کاربری وجود ندارد.",
                False,
            )

            await query.message.reply_text(
                "هیچ کاربری وجود ندارد."
            )
            return

        text = "👥 کاربران\n\n"

        for u in users:

            line = (
                f"👤 {u['first_name'] or '-'}\n"
                f"🔢 {u['id']}\n"
                f"📱 {user_name(u)}\n"
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

        await safe_query_answer(
            query,
            "✅ لیست کاربران ارسال شد.",
            False,
        )

        return

    # =====================================================
    # ADMIN DEPOSITS
    # =====================================================

    if data == "admin_deposits":

        context.user_data.clear()

        rows = execute(
            """
            SELECT * FROM deposits
            ORDER BY id DESC
            LIMIT 30
            """,
            fetchall=True,
        )

        if not rows:

            await safe_query_answer(
                query,
                "واریزی‌ای وجود ندارد.",
                False,
            )

            await query.message.reply_text(
                "💰 واریزی‌ای وجود ندارد."
            )
            return

        text = "💰 واریزی‌های اخیر\n\n"

        for d in rows:

            text += (
                f"#{d['id']} | "
                f"{d['amount']:,} | "
                f"{d['status']} | "
                f"ID {d['user_id']}\n"
            )

        await safe_query_answer(
            query,
            "✅ انجام شد.",
            False,
        )

        await query.message.reply_text(text)
        return

    # =====================================================
    # ADMIN WITHDRAWALS
    # =====================================================

    if data == "admin_withdrawals":

        context.user_data.clear()

        rows = execute(
            """
            SELECT * FROM withdrawals
            ORDER BY id DESC
            LIMIT 30
            """,
            fetchall=True,
        )

        if not rows:

            await safe_query_answer(
                query,
                "برداشتی وجود ندارد.",
                False,
            )

            await query.message.reply_text(
                "💸 برداشتی وجود ندارد."
            )
            return

        text = "💸 برداشت‌های اخیر\n\n"

        for w in rows:

            text += (
                f"#{w['id']} | "
                f"{w['amount']:,} | "
                f"{w['status']} | "
                f"ID {w['user_id']}\n"
            )

        await safe_query_answer(
            query,
            "✅ انجام شد.",
            False,
        )

        await query.message.reply_text(text)
        return

    # =====================================================
    # ADMIN STATS
    # =====================================================

    if data == "admin_stats":

        context.user_data.clear()

        users = execute(
            """
            SELECT COUNT(*) AS c
            FROM users
            """,
            fetchone=True,
        )["c"]

        total_balance = execute(
            """
            SELECT COALESCE(SUM(balance),0) AS s
            FROM users
            """,
            fetchone=True,
        )["s"]

        refs = execute(
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

        await safe_query_answer(
            query,
            "📊 آمار آماده شد.",
            False,
        )

        await query.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"👥 رفرال: {refs}\n"
            f"🎮 بازی‌های انجام‌شده: {games}\n"
            f"🎁 جایزه رفرال: {get_referral_reward():,} DOGS\n"
            f"🤖 وضعیت: {'روشن' if bot_enabled() else 'خاموش'}"
        )

        return

    await safe_query_answer(
        query,
        "❌ دکمه ناشناخته است.",
        True,
    )


# =========================================================
# ADMIN TEXT STATES
# =========================================================

async def admin_state_handler(update, context):

    if not admin_only(update.effective_user.id):
        return False

    state = context.user_data.get("state")

    if not state or not state.startswith("admin_"):
        return False

    if not update.message.text:
        return False

    text = update.message.text.strip()

    # =====================================================
    # TRANSFER OWNER
    # =====================================================

    if state == "admin_transfer_owner":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        try:
            new_owner = int(text)
        except (ValueError, OverflowError):

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )
            return True

        if not get_user(new_owner):

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را شروع نکرده است."
            )
            return True

        old_owner = get_owner_id()

        set_owner_id(new_owner)

        context.user_data.clear()

        await update.message.reply_text(
            "👑 مالکیت منتقل شد.\n\n"
            f"مالک جدید: {new_owner}",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        try:

            await context.bot.send_message(
                chat_id=new_owner,
                text=(
                    "👑 شما مالک جدید ربات شدید.\n\n"
                    "پنل مدیریت برای شما فعال شد."
                ),
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

    # =====================================================
    # ADD BALANCE
    # =====================================================

    if state == "admin_add_balance":

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "❌ فرمت صحیح:\n123456789 5000"
            )
            return True

        if (
            not parts[0].isdigit()
            or not parts[1].isdigit()
        ):

            await update.message.reply_text(
                "❌ ID و مبلغ باید عدد باشند."
            )
            return True

        try:

            target_id = int(parts[0])
            amount = int(parts[1])

        except (ValueError, OverflowError):

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return True

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
            f"✅ {amount:,} DOGS به کاربر {target_id} اضافه شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "💰 موجودی شما توسط مالک افزایش یافت.\n\n"
                    f"➕ {amount:,} DOGS"
                ),
            )

        except Exception:
            pass

        return True

    # =====================================================
    # REMOVE BALANCE
    # =====================================================

    if state == "admin_remove_balance":

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "❌ فرمت صحیح:\n123456789 5000"
            )
            return True

        if (
            not parts[0].isdigit()
            or not parts[1].isdigit()
        ):

            await update.message.reply_text(
                "❌ ID و مبلغ باید عدد باشند."
            )
            return True

        try:

            target_id = int(parts[0])
            amount = int(parts[1])

        except (ValueError, OverflowError):

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return True

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
                    target_id,
                    "admin_remove",
                    -amount,
                    "Admin balance remove",
                    datetime.now().isoformat(),
                ),
            )

            db.commit()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ {amount:,} DOGS از کاربر {target_id} کسر شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "💰 موجودی شما توسط مالک کاهش یافت.\n\n"
                    f"➖ {amount:,} DOGS"
                ),
            )

        except Exception:
            pass

        return True

    # =====================================================
    # REFERRAL REWARD
    # =====================================================

    if state == "admin_referral_reward":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )
            return True

        try:
            amount = int(text)
        except (ValueError, OverflowError):

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return True

        if amount < 0:

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return True

        set_referral_reward(amount)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ جایزه زیرمجموعه تغییر کرد.\n\n"
            f"🎁 {amount:,} DOGS",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        return True

    # =====================================================
    # BLOCK
    # =====================================================

    if state == "admin_block":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ آیدی عددی وارد کنید."
            )
            return True

        try:
            target_id = int(text)
        except (ValueError, OverflowError):

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )
            return True

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

        status = (
            "مسدود شد"
            if new_status
            else "آزاد شد"
        )

        await update.message.reply_text(
            f"✅ کاربر {target_id} {status}.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        return True

    # =====================================================
    # BROADCAST
    # =====================================================

    if state == "admin_broadcast":

        users = execute(
            """
            SELECT id
            FROM users
            WHERE blocked=0
            """,
            fetchall=True,
        )

        sent_count = 0

        for u in users:

            try:

                await context.bot.copy_message(
                    chat_id=u["id"],
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )

                sent_count += 1

            except Exception:
                pass

        context.user_data.clear()

        await update.message.reply_text(
            f"📢 پیام همگانی ارسال شد.\n\n"
            f"👥 ارسال موفق: {sent_count}",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        return True

    return False


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update, context):

    if not admin_only(update.effective_user.id):

        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )
        return

    context.user_data.clear()

    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        "از گزینه‌های زیر استفاده کنید:",
        reply_markup=admin_keyboard(),
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    # مهم:
    # همین اول state کاملاً پاک می‌شود.
    context.user_data.clear()

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# GROUP BALANCE
# =========================================================

async def group_balance(update, context):

    user = get_user(
        update.effective_user.id
    )

    if not user:

        await update.message.reply_text(
            "🔐 ابتدا در خصوصی ربات /start را بزنید."
        )
        return

    if not user["verified"]:

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را در خصوصی تأیید کنید."
        )
        return

    await update.message.reply_text(
        f"💳 موجودی {user_name(user)}:\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# =========================================================
# TEXT ROUTER - MAIN ANTI BUG
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    if not update.effective_user:
        return

    text = (
        update.message.text.strip()
        if update.message.text
        else ""
    )

    # =====================================================
    # GROUP
    # =====================================================

    if update.effective_chat.type in (
        "group",
        "supergroup",
    ):

        if text in (
            "موجودی",
            "💳 موجودی",
        ):

            await group_balance(
                update,
                context,
            )
            return

        if re.fullmatch(
            r"\s*انتقال\s+\d+\s*",
            text,
        ):

            await transfer_by_reply(
                update,
                context,
            )
            return

        match = re.fullmatch(
            r"\s*بازی\s+(\d+)\s*",
            text,
        )

        if match:

            try:
                amount = int(match.group(1))
            except (ValueError, OverflowError):

                await update.message.reply_text(
                    "❌ مبلغ نامعتبر است."
                )
                return

            await create_game(
                update,
                context,
                amount,
            )

            return

        return

    # =====================================================
    # PRIVATE
    # =====================================================

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if user["blocked"]:

        context.user_data.clear()

        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    # =====================================================
    # IMPORTANT:
    # EVERY MAIN BUTTON HAS ABSOLUTE PRIORITY.
    # OLD STATE CANNOT CATCH THE BUTTON.
    # =====================================================

    # -------------------------
    # CANCEL
    # -------------------------

    if text == "❌ لغو":

        await cancel(
            update,
            context,
        )

        return

    # -------------------------
    # BALANCE
    # -------------------------

    if text in (
        "💳 موجودی",
        "موجودی",
    ):

        context.user_data.clear()

        await balance(
            update,
            context,
        )

        return

    # -------------------------
    # DEPOSIT
    # -------------------------

    if text == "💰 واریزی":

        context.user_data.clear()

        await deposit_start(
            update,
            context,
        )

        return

    # -------------------------
    # WITHDRAW
    # -------------------------

    if text == "💸 برداشت":

        context.user_data.clear()

        await withdraw_start(
            update,
            context,
        )

        return

    # -------------------------
    # TRANSFER
    # -------------------------

    if text == "🔄 انتقال":

        context.user_data.clear()

        if not user["verified"]:

            await update.message.reply_text(
                "🔐 ابتدا شماره خود را تأیید کنید.",
                reply_markup=verification_keyboard(),
            )
            return

        await update.message.reply_text(
            "🔄 انتقال فقط در گروه انجام می‌شود.\n\n"
            "روی پیام کاربر Reply کنید و بنویسید:\n"
            "انتقال 500",
            reply_markup=main_keyboard(user["id"]),
        )

        return

    # -------------------------
    # REFERRALS
    # -------------------------

    if text == "👥 زیرمجموعه":

        context.user_data.clear()

        await referrals(
            update,
            context,
        )

        return

    # -------------------------
    # SUPPORT
    # -------------------------

    if text == "🎧 پشتیبانی":

        context.user_data.clear()

        await support_start(
            update,
            context,
        )

        return

    # -------------------------
    # ADMIN PANEL
    # -------------------------

    if text == "🛠 پنل مدیریت":

        context.user_data.clear()

        await admin_panel(
            update,
            context,
        )

        return

    # =====================================================
    # CONTACT
    # =====================================================

    if update.message.contact:
        return

    # =====================================================
    # VERIFICATION
    # =====================================================

    if not user["verified"]:

        context.user_data.clear()

        await update.message.reply_text(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )

        return

    # =====================================================
    # OWNER SUPPORT REPLY
    # =====================================================

    if await owner_reply_support(
        update,
        context,
    ):
        return

    # =====================================================
    # ADMIN STATES
    # =====================================================

    state = context.user_data.get("state")

    if state and state.startswith("admin_"):

        handled = await admin_state_handler(
            update,
            context,
        )

        if handled:
            return

    # =====================================================
    # NORMAL STATES
    # =====================================================

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

    if state == "support":

        await support_message(
            update,
            context,
        )
        return

    # =====================================================
    # UNKNOWN
    # =====================================================

    context.user_data.clear()

    await update.message.reply_text(
        "❌ گزینه نامعتبر است.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(update, context):

    if not update.effective_user:
        return

    if update.effective_chat.type != "private":
        return

    user = create_or_update_user(
        update.effective_user
    )

    if not user:
        return

    if user["blocked"]:
        return

    if not user["verified"]:

        context.user_data.clear()

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

    # عکس بدون عملیات فعال
    context.user_data.clear()

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    logger.exception(
        "Unhandled bot error:",
        exc_info=context.error,
    )

    # خطای یک دکمه نباید باعث توقف ربات شود
    try:

        if isinstance(update, Update):

            if update.callback_query:

                await safe_query_answer(
                    update.callback_query,
                    "❌ خطایی رخ داد؛ دوباره تلاش کنید.",
                    True,
                )

    except Exception:
        pass


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

    # Inline callbacks
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # Contact
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # Photo / Documents
    application.add_handler(
        MessageHandler(
            (
                filters.PHOTO
                | filters.Document.ALL
            )
            & ~filters.COMMAND,
            media_router,
        )
    )

    # Text
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router,
        )
    )

    # Global error handler
    application.add_error_handler(
        error_handler
    )

    logger.info(
        "TAK BET BOT STARTED"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
