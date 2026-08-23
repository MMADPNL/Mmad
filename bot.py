# ==========================================
# DOGS BOT - bot.py
# ==========================================

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

# سهم ثابت مالک در هر بازی
OWNER_GAME_FEE = 50

# درصد پرداخت به برنده
WINNER_PERCENT = 90

DB_FILE = "bot.db"

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

db_lock = asyncio.Lock()


def execute(query, params=(), fetchone=False, fetchall=False):
    cur = db.cursor()
    cur.execute(query, params)

    if fetchone:
        result = cur.fetchone()
        db.commit()
        return result

    if fetchall:
        result = cur.fetchall()
        db.commit()
        return result

    db.commit()
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

    # ---------------- GAME TABLE ----------------

    execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER,
            creator_id INTEGER NOT NULL,
            player2_id INTEGER,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'waiting',
            winner_id INTEGER,
            loser_id INTEGER,
            owner_fee INTEGER DEFAULT 0,
            winner_reward INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # ---------------- SETTINGS ----------------

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
    return int(
        get_setting(
            "referral_reward",
            DEFAULT_REFERRAL_REWARD,
        )
    )


def set_referral_reward(amount):
    set_setting("referral_reward", amount)


def bot_enabled():
    return get_setting("bot_enabled", "1") == "1"


def set_bot_enabled(value):
    set_setting(
        "bot_enabled",
        "1" if value else "0",
    )


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
            verified,
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


def user_name(user):

    if not user:
        return "کاربر"

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


def is_verified(user):
    if not user:
        return False

    # مالک نیازی به تأیید شماره ندارد
    if user["id"] == get_owner_id():
        return True

    return bool(user["verified"])


# =========================================================
# MAIN KEYBOARDS
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


def admin_keyboard():

    status = "🟢 روشن" if bot_enabled() else "🔴 خاموش"

    return InlineKeyboardMarkup([
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
            ),
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
            ),
        ],
        [
            InlineKeyboardButton(
                "👥 موجودی کاربران",
                callback_data="admin_balances",
            ),
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
    ])


# =========================================================
# VERIFICATION
# =========================================================

async def request_verification(update, context):

    await update.effective_message.reply_text(
        "🔐 برای استفاده از ربات ابتدا شماره خود را تأیید کنید.\n\n"
        "روی دکمه زیر بزنید و شماره همین حساب تلگرام را ارسال کنید.",
        reply_markup=phone_keyboard(),
    )


async def contact_handler(update, context):

    if not update.message or not update.message.contact:
        return

    contact = update.message.contact
    tg_user = update.effective_user

    if contact.user_id != tg_user.id:
        await update.message.reply_text(
            "❌ فقط شماره متصل به همین حساب تلگرام قابل تأیید است."
        )
        return

    user = create_or_update_user(tg_user)

    execute(
        """
        UPDATE users
        SET verified=1
        WHERE id=?
        """,
        (tg_user.id,),
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تأیید شد.\n\n"
        "اکنون می‌توانید از ربات استفاده کنید.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# START
# =========================================================

async def start(update, context):

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

    # مالک همیشه دسترسی دارد
    if not is_verified(user):

        await request_verification(
            update,
            context,
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

    user = create_or_update_user(
        update.effective_user
    )

    if not is_verified(user):

        await request_verification(update, context)
        return

    if user["blocked"]:
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

    if not is_verified(user):

        await request_verification(update, context)
        return

    if user["blocked"]:
        return

    if not bot_enabled():

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )

        return

    context.user_data.clear()

    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        f"💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS\n\n"
        "فرمت پرداخت:\n"
        "ULTRA 5000 DOGS @CyyFr",
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
        f"لطفاً مبلغ را واریز کنید:\n\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از واریز رسید را ارسال کنید.\n"
        "🖼 عکس / فایل / 📝 متن قابل قبول است.",
        reply_markup=cancel_keyboard(),
    )


async def deposit_receipt(update, context):

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

    try:

        if receipt_type == "photo":

            await context.bot.send_photo(
                chat_id=get_owner_id(),
                photo=receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        elif receipt_type == "document":

            await context.bot.send_document(
                chat_id=get_owner_id(),
                document=receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        else:

            await context.bot.send_message(
                chat_id=get_owner_id(),
                text=caption + f"\n\n📝 رسید:\n{receipt_text}",
                reply_markup=keyboard,
            )

    except Exception as e:

        logger.error(
            "Deposit owner notification error: %s",
            e,
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

async def withdraw_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if not is_verified(user):

        await request_verification(update, context)
        return

    if user["blocked"]:
        return

    if not bot_enabled():

        await update.message.reply_text(
            "🔴 ربات خاموش است."
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
        "@username\n"
        "یا آیدی عددی",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_destination(update, context):

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

    user = get_user(update.effective_user.id)

    if not amount:

        context.user_data.clear()
        return

    # ضد دوباره‌خرج کردن موجودی
    changed = execute(
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

    if changed is None:
        pass

    check = get_user(user["id"])

    if check["balance"] < 0:

        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (amount, user["id"]),
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    execute(
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
            f"💰 {amount:,} DOGS\n"
            f"📍 {destination}"
        ),
        reply_markup=keyboard,
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# TRANSFER - ONLY REPLY
# =========================================================

async def transfer_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if not is_verified(user):

        await request_verification(update, context)
        return

    if user["blocked"]:
        return

    context.user_data.clear()

    context.user_data["state"] = "transfer_amount"

    await update.message.reply_text(
        "🔄 برای انتقال فقط روی پیام کاربر Reply کنید "
        "و بنویسید:\n\n"
        "انتقال 500\n\n"
        "یا فقط:\n"
        "500",
        reply_markup=cancel_keyboard(),
    )


async def transfer_amount(update, context):

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "❌ انتقال فقط با Reply به پیام کاربر انجام می‌شود."
        )

        return

    text = update.message.text.strip()

    if text.startswith("انتقال"):

        parts = text.split()

        if len(parts) != 2 or not parts[1].isdigit():

            await update.message.reply_text(
                "❌ فرمت صحیح:\nانتقال 500"
            )

            return

        amount = int(parts[1])

    else:

        if not text.isdigit():

            await update.message.reply_text(
                "❌ مبلغ نامعتبر است."
            )

            return

        amount = int(text)

    target = update.message.reply_to_message.from_user

    if not target or target.is_bot:

        await update.message.reply_text(
            "❌ مقصد نامعتبر است."
        )

        return

    receiver = get_user(target.id)

    if not receiver:

        receiver = create_or_update_user(target)

    await complete_transfer(
        update,
        context,
        receiver["id"],
        amount,
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

    sender = get_user(sender_id)
    receiver = get_user(receiver_id)

    if not sender or not receiver:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )

        return

    if sender_id == receiver_id:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return

    # اتمیک
    changed = execute(
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

    sender_after = get_user(sender_id)

    if sender_after["balance"] < 0:

        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (amount, sender_id),
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

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

    now = datetime.now().isoformat()

    execute(
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
            now,
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
            now,
        ),
    )

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ انتقال انجام شد.\n\n"
        f"💰 {amount:,} DOGS\n"
        f"👤 مقصد: {user_name(receiver)}",
        reply_markup=main_keyboard(sender_id),
    )

    try:

        await context.bot.send_message(
            chat_id=receiver_id,
            text=(
                "💰 انتقال دریافت کردید.\n\n"
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

    if not is_verified(user):

        await request_verification(update, context)
        return

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start=ref_{user['id']}"
    )

    count = execute(
        """
        SELECT COUNT(*) AS c
        FROM referrals
        WHERE referrer_id=?
        """,
        (user["id"],),
        fetchone=True,
    )["c"]

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"👤 تعداد: {count}\n"
        f"🎁 پاداش: {get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if not is_verified(user):

        await request_verification(update, context)
        return

    context.user_data.clear()

    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را بفرستید.\n"
        "متن، عکس یا فایل قابل قبول است.",
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
            "❌ نوع پیام پشتیبانی نمی‌شود."
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
        f"👤 {user_name(user)}\n"
        f"🔢 {user['id']}"
    )

    reply_keyboard = InlineKeyboardMarkup([
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
                reply_markup=reply_keyboard,
            )

        elif file_type == "document":

            await context.bot.send_document(
                chat_id=get_owner_id(),
                document=file_id,
                caption=caption,
                reply_markup=reply_keyboard,
            )

        else:

            await context.bot.send_message(
                chat_id=get_owner_id(),
                text=caption + f"\n\n📝 {text}",
                reply_markup=reply_keyboard,
            )

    except Exception as e:

        logger.error(
            "Support send error: %s",
            e,
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


async def create_game(update, context, amount):

    user = create_or_update_user(
        update.effective_user
    )

    if not is_verified(user):

        await update.message.reply_text(
            "🔐 ابتدا در پیوی ربات شماره خود را تأیید کنید."
        )

        return

    if user["blocked"]:

        await update.message.reply_text(
            "🚫 حساب شما مسدود است."
        )

        return

    if not bot_enabled():

        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )

        return

    if amount < 500:

        await update.message.reply_text(
            "❌ حداقل مبلغ بازی 500 DOGS است."
        )

        return

    if user["balance"] < amount:

        await update.message.reply_text(
            "❌ موجودی شما کافی نیست.\n\n"
            f"موجودی: {user['balance']:,} DOGS"
        )

        return

    # فقط یک بازی باز برای هر سازنده در همان گروه
    old = execute(
        """
        SELECT id FROM games
        WHERE chat_id=?
        AND creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (
            update.effective_chat.id,
            user["id"],
        ),
        fetchone=True,
    )

    if old:

        await update.message.reply_text(
            "❌ شما همین الان یک بازی در انتظار دارید."
        )

        return

    # مبلغ از سازنده هنگام ساخت رزرو می‌شود
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

    check = get_user(user["id"])

    if check["balance"] < 0:

        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (amount, user["id"]),
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    execute(
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

    game_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    msg = await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 سازنده: {user_name(user)}\n\n"
        "یک نفر برای ورود روی دکمه زیر بزند.",
        reply_markup=game_keyboard(game_id),
    )

    execute(
        """
        UPDATE games
        SET message_id=?
        WHERE id=?
        """,
        (
            msg.message_id,
            game_id,
        ),
    )


async def join_game(query, context, game_id):

    async with db_lock:

        game = execute(
            "SELECT * FROM games WHERE id=?",
            (game_id,),
            fetchone=True,
        )

        if not game:

            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True,
            )

            return

        if game["status"] != "waiting":

            await query.answer(
                "❌ این بازی قبلاً شروع شده.",
                show_alert=True,
            )

            return

        player2_id = query.from_user.id

        if player2_id == game["creator_id"]:

            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True,
            )

            return

        player2 = get_user(player2_id)

        if not player2:

            player2 = create_or_update_user(
                query.from_user
            )

        if not is_verified(player2):

            await query.answer(
                "🔐 ابتدا شماره خود را در پیوی ربات تأیید کنید.",
                show_alert=True,
            )

            return

        if player2["blocked"]:

            await query.answer(
                "🚫 حساب شما مسدود است.",
                show_alert=True,
            )

            return

        if not bot_enabled():

            await query.answer(
                "🔴 ربات خاموش است.",
                show_alert=True,
            )

            return

        amount = game["amount"]

        if player2["balance"] < amount:

            await query.answer(
                "❌ موجودی شما کافی نیست.",
                show_alert=True,
            )

            return

        # اول بازی را قفل می‌کنیم
        changed = execute(
            """
            UPDATE games
            SET player2_id=?,
                status='playing'
            WHERE id=?
            AND status='waiting'
            """,
            (
                player2_id,
                game_id,
            ),
        )

        # بررسی دوباره
        game = execute(
            "SELECT * FROM games WHERE id=?",
            (game_id,),
            fetchone=True,
        )

        if game["status"] != "playing" or game["player2_id"] != player2_id:

            await query.answer(
                "❌ شخص دیگری وارد بازی شد.",
                show_alert=True,
            )

            return

        # کسر مبلغ نفر دوم
        execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=? AND balance>=?
            """,
            (
                amount,
                player2_id,
                amount,
            ),
        )

        player2_after = get_user(player2_id)

        if player2_after["balance"] < 0:

            execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    amount,
                    player2_id,
                ),
            )

            execute(
                """
                UPDATE games
                SET status='waiting',
                    player2_id=NULL
                WHERE id=?
                """,
                (game_id,),
            )

            await query.answer(
                "❌ موجودی شما کافی نیست.",
                show_alert=True,
            )

            return

        # -------------------------------
        # شروع فوری بازی
        # -------------------------------

        creator = get_user(game["creator_id"])
        player2 = get_user(player2_id)

        # انتخاب تصادفی برنده
        winner_id = random.choice([
            creator["id"],
            player2["id"],
        ])

        loser_id = (
            player2["id"]
            if winner_id == creator["id"]
            else creator["id"]
        )

        # مبلغ کل دو بازیکن
        total = amount * 2

        # برنده 90 درصد کل مبلغ
        winner_reward = (total * WINNER_PERCENT) // 100

        # سهم مالک 50 DOGS از موجودی ربات
        owner_fee = OWNER_GAME_FEE

        owner_id = get_owner_id()

        owner = get_user(owner_id)

        # مالک فقط از موجودی خودش 50 می‌گیرد
        # و این مبلغ از برنده کسر نمی‌شود.
        if owner and owner["balance"] >= owner_fee:

            execute(
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
                    owner_id,
                    "game_owner_fee",
                    -owner_fee,
                    f"Game #{game_id} owner fee",
                    datetime.now().isoformat(),
                ),
            )

        else:

            # اگر مالک 50 DOGS موجودی نداشته باشد،
            # سهم مالک از هیچ بازیکنی گرفته نمی‌شود.
            owner_fee = 0

        # پرداخت برنده
        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                winner_reward,
                winner_id,
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
                winner_id,
                "game_win",
                winner_reward,
                f"Game #{game_id}",
                datetime.now().isoformat(),
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
                loser_id,
                "game_loss",
                -amount,
                f"Game #{game_id}",
                datetime.now().isoformat(),
            ),
        )

        execute(
            """
            UPDATE games
            SET status='finished',
                winner_id=?,
                loser_id=?,
                owner_fee=?,
                winner_reward=?
            WHERE id=?
            AND status='playing'
            """,
            (
                winner_id,
                loser_id,
                owner_fee,
                winner_reward,
                game_id,
            ),
        )

    # -------------------------------
    # اعلام فوری در گروه
    # -------------------------------

    winner = get_user(winner_id)
    loser = get_user(loser_id)

    result_text = (
        "🎮 بازی تمام شد!\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"👤 بازیکن ۱: {user_name(creator)}\n"
        f"👤 بازیکن ۲: {user_name(player2)}\n\n"
        f"🏆 برنده: {user_name(winner)}\n"
        f"🎁 جایزه برنده: {winner_reward:,} DOGS\n"
        f"💸 سهم مالک: {owner_fee:,} DOGS\n\n"
        "⚡ نتیجه فوری اعلام شد."
    )

    try:

        await query.edit_message_text(
            result_text
        )

    except Exception:

        try:

            await context.bot.send_message(
                chat_id=game["chat_id"],
                text=result_text,
            )

        except Exception:
            pass

    await query.answer(
        "🎮 بازی شروع و نتیجه مشخص شد!",
        show_alert=False,
    )

    # -------------------------------
    # پیوی برنده
    # -------------------------------

    try:

        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 شما برنده بازی شدید!\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🎁 جایزه: {winner_reward:,} DOGS\n\n"
                f"💳 موجودی جدید: "
                f"{get_user(winner_id)['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass

    # -------------------------------
    # پیوی بازنده
    # -------------------------------

    try:

        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "😔 شما بازی را باختید.\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🏆 برنده: {user_name(winner)}\n\n"
                f"💳 موجودی جدید: "
                f"{get_user(loser_id)['balance']:,} DOGS"
            ),
        )

    except Exception:
        pass


async def cancel_game(query, context, game_id):

    game = execute(
        "SELECT * FROM games WHERE id=?",
        (game_id,),
        fetchone=True,
    )

    if not game:

        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True,
        )

        return

    if game["status"] != "waiting":

        await query.answer(
            "❌ بازی قابل لغو نیست.",
            show_alert=True,
        )

        return

    if query.from_user.id != game["creator_id"]:

        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند لغو کند.",
            show_alert=True,
        )

        return

    execute(
        """
        UPDATE games
        SET status='cancelled'
        WHERE id=?
        AND status='waiting'
        """,
        (game_id,),
    )

    # برگرداندن مبلغ رزرو شده
    execute(
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


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(query, context):

    data = query.data

    if data.startswith("game_join:"):

        try:
            game_id = int(
                data.split(":", 1)[1]
            )
        except Exception:

            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )

            return

        await join_game(
            query,
            context,
            game_id,
        )

        return

    if data.startswith("game_cancel:"):

        try:
            game_id = int(
                data.split(":", 1)[1]
            )
        except Exception:

            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )

            return

        await cancel_game(
            query,
            context,
            game_id,
        )

        return


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if user["id"] != get_owner_id():

        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )

        return

    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        "مدیریت کامل ربات:",
        reply_markup=admin_keyboard(),
    )


def admin_only(user_id):
    return user_id == get_owner_id()


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(query, context):

    user_id = query.from_user.id

    if not admin_only(user_id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    data = query.data

    # روشن خاموش
    if data == "admin_toggle_bot":

        new_status = not bot_enabled()

        set_bot_enabled(new_status)

        await query.answer(
            "🟢 ربات روشن شد."
            if new_status
            else "🔴 ربات خاموش شد."
        )

        try:

            await query.edit_message_reply_markup(
                reply_markup=admin_keyboard()
            )

        except Exception:
            pass

        return

    if data == "admin_transfer_owner":

        context.user_data.clear()

        context.user_data["state"] = "admin_transfer_owner"

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را ارسال کنید."
        )

        return

    if data == "admin_add_balance":

        context.user_data.clear()

        context.user_data["state"] = "admin_add_balance"

        await query.message.reply_text(
            "➕ شارژ موجودی\n\n"
            "فرمت:\n"
            "123456789 5000"
        )

        return

    if data == "admin_remove_balance":

        context.user_data.clear()

        context.user_data["state"] = "admin_remove_balance"

        await query.message.reply_text(
            "➖ کسر موجودی\n\n"
            "فرمت:\n"
            "123456789 5000"
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

    if data == "admin_block":

        context.user_data.clear()

        context.user_data["state"] = "admin_block"

        await query.message.reply_text(
            "🚫 آیدی کاربر را ارسال کنید:"
        )

        return

    if data == "admin_broadcast":

        context.user_data.clear()

        context.user_data["state"] = "admin_broadcast"

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید."
        )

        return

    if data == "admin_balances":

        rows = execute(
            """
            SELECT * FROM users
            ORDER BY balance DESC
            """,
            fetchall=True,
        )

        if not rows:

            await query.message.reply_text(
                "هیچ کاربری وجود ندارد."
            )

            return

        text = "👥 موجودی کاربران\n\n"

        for u in rows:

            line = (
                f"👤 {user_name(u)}\n"
                f"🔢 {u['id']}\n"
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

    if data == "admin_deposits":

        rows = execute(
            """
            SELECT * FROM deposits
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
                f"{d['amount']:,} | "
                f"{d['status']} | "
                f"{d['user_id']}\n"
            )

        await query.message.reply_text(text)

        return

    if data == "admin_withdrawals":

        rows = execute(
            """
            SELECT * FROM withdrawals
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
                f"{w['amount']:,} | "
                f"{w['status']} | "
                f"{w['user_id']}\n"
            )

        await query.message.reply_text(text)

        return

    if data == "admin_stats":

        users = execute(
            "SELECT COUNT(*) AS c FROM users",
            fetchone=True,
        )["c"]

        total = execute(
            "SELECT COALESCE(SUM(balance),0) AS s FROM users",
            fetchone=True,
        )["s"]

        games = execute(
            """
            SELECT COUNT(*) AS c
            FROM games
            WHERE status='finished'
            """,
            fetchone=True,
        )["c"]

        refs = execute(
            "SELECT COUNT(*) AS c FROM referrals",
            fetchone=True,
        )["c"]

        await query.message.reply_text(
            "📊 آمار\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total:,} DOGS\n"
            f"🎮 بازی‌های انجام‌شده: {games}\n"
            f"👥 رفرال‌ها: {refs}\n"
            f"🎁 جایزه رفرال: "
            f"{get_referral_reward():,} DOGS\n"
            f"💸 سهم مالک هر بازی: "
            f"{OWNER_GAME_FEE} DOGS"
        )

        return


# =========================================================
# SUPPORT REPLY
# =========================================================

async def support_reply_start(query, context):

    if not admin_only(query.from_user.id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    try:

        support_id = int(
            query.data.split(":", 1)[1]
        )

    except Exception:

        await query.answer(
            "❌ درخواست نامعتبر.",
            show_alert=True,
        )

        return

    support = execute(
        """
        SELECT * FROM support_messages
        WHERE id=?
        """,
        (support_id,),
        fetchone=True,
    )

    if not support:

        await query.answer(
            "❌ پیام پیدا نشد.",
            show_alert=True,
        )

        return

    context.user_data.clear()

    context.user_data["state"] = "support_reply"
    context.user_data["support_user_id"] = support["user_id"]
    context.user_data["support_id"] = support_id

    await query.message.reply_text(
        "💬 پاسخ خود را ارسال کنید:"
    )

    await query.answer()


# =========================================================
# ADMIN STATES
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

    # -------------------------
    # Support reply
    # -------------------------

    if state == "support_reply":

        target_id = context.user_data.get(
            "support_user_id"
        )

        if not target_id:
            context.user_data.clear()
            return True

        try:

            await context.bot.copy_message(
                chat_id=target_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )

            await update.message.reply_text(
                "✅ پاسخ برای کاربر ارسال شد."
            )

            execute(
                """
                UPDATE support_messages
                SET status='answered'
                WHERE id=?
                """,
                (
                    context.user_data.get(
                        "support_id"
                    ),
                ),
            )

        except Exception as e:

            await update.message.reply_text(
                f"❌ ارسال پاسخ انجام نشد.\n{e}"
            )

        context.user_data.clear()

        return True

    text = (
        update.message.text.strip()
        if update.message.text
        else ""
    )

    # -------------------------
    # Referral
    # -------------------------

    if state == "admin_referral_reward":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )

            return True

        amount = int(text)

        set_referral_reward(amount)

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ جایزه زیرمجموعه تغییر کرد:\n"
            f"{amount:,} DOGS",
            reply_markup=main_keyboard(
                user["id"]
            ),
        )

        return True

    # -------------------------
    # Owner transfer
    # -------------------------

    if state == "admin_transfer_owner":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return True

        new_owner = int(text)

        target = get_user(new_owner)

        if not target:

            await update.message.reply_text(
                "❌ کاربر ابتدا باید /start بزند."
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
                reply_markup=main_keyboard(
                    new_owner
                ),
            )

        except Exception:
            pass

        logger.info(
            "Owner changed: %s -> %s",
            old_owner,
            new_owner,
        )

        return True

    # -------------------------
    # Add / remove
    # -------------------------

    if state in (
        "admin_add_balance",
        "admin_remove_balance",
    ):

        parts = text.split()

        if (
            len(parts) != 2
            or not parts[0].isdigit()
            or not parts[1].isdigit()
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

            msg = (
                f"✅ {amount:,} DOGS به کاربر "
                f"{target_id} اضافه شد."
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

            msg = (
                f"✅ {amount:,} DOGS از کاربر "
                f"{target_id} کم شد."
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
                transaction_type,
                transaction_amount,
                "Admin balance change",
                datetime.now().isoformat(),
            ),
        )

        context.user_data.clear()

        await update.message.reply_text(
            msg,
            reply_markup=main_keyboard(
                user["id"]
            ),
        )

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=msg,
            )

        except Exception:
            pass

        return True

    # -------------------------
    # Block
    # -------------------------

    if state == "admin_block":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ آیدی عددی وارد کنید."
            )

            return True

        target_id = int(text)

        target = get_user(target_id)

        if not target:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )

            return True

        new_status = (
            0
            if target["blocked"]
            else 1
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

        await update.message.reply_text(
            "✅ کاربر "
            f"{'مسدود شد' if new_status else 'آزاد شد'}.",
            reply_markup=main_keyboard(
                user["id"]
            ),
        )

        return True

    # -------------------------
    # Broadcast
    # -------------------------

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
            reply_markup=main_keyboard(
                user["id"]
            ),
        )

        return True

    return False


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update, context):

    query = update.callback_query

    data = query.data or ""

    # بازی
    if data.startswith("game_"):

        await game_callback(
            query,
            context,
        )

        return

    # پشتیبانی
    if data.startswith("support_reply:"):

        await support_reply_start(
            query,
            context,
        )

        return

    # مالک
    if data.startswith("admin_"):

        await query.answer()

        await admin_callback(
            query,
            context,
        )

        return

    # واریزی / برداشت
    if data.startswith("deposit_"):

        await deposit_callback(
            query,
            context,
        )

        return

    if data.startswith("withdraw_"):

        await withdrawal_callback(
            query,
            context,
        )

        return

    await query.answer(
        "❌ دکمه نامعتبر است.",
        show_alert=True,
    )


# =========================================================
# DEPOSIT CALLBACK
# =========================================================

async def deposit_callback(query, context):

    if not admin_only(query.from_user.id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    try:

        action, id_text = query.data.split(":")

        deposit_id = int(id_text)

    except Exception:

        await query.answer(
            "❌ درخواست نامعتبر.",
            show_alert=True,
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

    # ضد دوبار کلیک
    if action == "deposit_approve":

        execute(
            """
            UPDATE deposits
            SET status='approved'
            WHERE id=?
            AND status='pending'
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

        text = (
            "✅ واریزی تأیید شد.\n\n"
            f"💰 {deposit['amount']:,} DOGS"
        )

    else:

        execute(
            """
            UPDATE deposits
            SET status='rejected'
            WHERE id=?
            AND status='pending'
            """,
            (deposit_id,),
        )

        text = (
            "❌ واریزی رد شد.\n\n"
            f"💰 {deposit['amount']:,} DOGS"
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
            text=text,
        )

    except Exception:
        pass

    await query.answer(
        "انجام شد."
    )


# =========================================================
# WITHDRAW CALLBACK
# =========================================================

async def withdrawal_callback(query, context):

    if not admin_only(query.from_user.id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    try:

        action, id_text = query.data.split(":")

        withdrawal_id = int(id_text)

    except Exception:

        await query.answer(
            "❌ درخواست نامعتبر.",
            show_alert=True,
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

        execute(
            """
            UPDATE withdrawals
            SET status='approved'
            WHERE id=?
            AND status='pending'
            """,
            (withdrawal_id,),
        )

        text = (
            "✅ برداشت تأیید شد.\n\n"
            f"💰 {withdrawal['amount']:,} DOGS\n"
            f"📍 {withdrawal['destination']}"
        )

    else:

        execute(
            """
            UPDATE withdrawals
            SET status='rejected'
            WHERE id=?
            AND status='pending'
            """,
            (withdrawal_id,),
        )

        # برگشت مبلغ رزرو شده
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

        text = (
            "❌ برداشت رد شد.\n\n"
            f"💰 {withdrawal['amount']:,} DOGS "
            "به موجودی برگشت."
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
            text=text,
        )

    except Exception:
        pass

    await query.answer(
        "انجام شد."
    )


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    await update.message.reply_text(
        "❌ لغو شد.",
        reply_markup=main_keyboard(
            user["id"]
        ),
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    if not update.message.text:
        return

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:

        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )

        return

    # لغو
    if update.message.text.strip() == "❌ لغو":

        await cancel(
            update,
            context,
        )

        return

    # تأیید شماره
    if (
        update.message.text.strip()
        == "📱 تأیید شماره"
    ):

        await request_verification(
            update,
            context,
        )

        return

    # -------------------------
    # پیوی: verification
    # -------------------------

    if update.effective_chat.type == "private":

        if not is_verified(user):

            await request_verification(
                update,
                context,
            )

            return

    # -------------------------
    # Admin states
    # -------------------------

    if await admin_state_handler(
        update,
        context,
    ):

        return

    state = context.user_data.get(
        "state"
    )

    # -------------------------
    # Deposit
    # -------------------------

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

    # -------------------------
    # Withdraw
    # -------------------------

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

    # -------------------------
    # Transfer
    # -------------------------

    if state == "transfer_amount":

        await transfer_amount(
            update,
            context,
        )

        return

    # -------------------------
    # Support
    # -------------------------

    if state == "support":

        await support_message(
            update,
            context,
        )

        return

    # -------------------------
    # MAIN BUTTONS
    # -------------------------

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

    # -------------------------
    # GAME
    # -------------------------

    # مثال:
    # بازی 500
    game_match = re.fullmatch(
        r"بازی\s+([0-9]+)",
        text,
    )

    if game_match:

        amount = int(
            game_match.group(1)
        )

        # بازی در گروه
        if update.effective_chat.type in (
            "group",
            "supergroup",
        ):

            await create_game(
                update,
                context,
                amount,
            )

            return

        await update.message.reply_text(
            "❌ بازی را داخل گروه اجرا کنید."
        )

        return

    # -------------------------
    # انتقال فقط با Reply
    # -------------------------

    if text.startswith("انتقال"):

        if update.effective_chat.type in (
            "group",
            "supergroup",
        ):

            await transfer_amount(
                update,
                context,
            )

            return

        await update.message.reply_text(
            "❌ انتقال فقط در گروه و با Reply انجام می‌شود."
        )

        return


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:
        return

    state = context.user_data.get(
        "state"
    )

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

    if state == "support_reply":

        await admin_state_handler(
            update,
            context,
        )

        return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


# =========================================================
# COMMANDS
# =========================================================

async def command_balance(update, context):

    await balance(
        update,
        context,
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
        .concurrent_updates(True)
        .build()
    )

    # فقط یک Router برای پیام‌های متنی
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "balance",
            command_balance,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # شماره
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # متن
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    # عکس / فایل
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            media_router,
        )
    )

    logger.info(
        "================================="
    )
    logger.info(
        "DOGS BOT STARTED"
    )
    logger.info(
        "OWNER: %s",
        get_owner_id(),
    )
    logger.info(
        "BOT ENABLED: %s",
        bot_enabled(),
    )
    logger.info(
        "================================="
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
