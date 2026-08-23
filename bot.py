# =========================================================
# DOGS INTERNAL POINT BOT - bot.py
# =========================================================

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

# سهم مالک از طرف خود ربات
GAME_OWNER_REWARD = 50

# برای بازی 500:
# برنده 900 می‌گیرد
# یعنی ضریب 1.8
GAME_WIN_MULTIPLIER = 1.8

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

db_lock = asyncio.Lock()


async def execute(query, params=(), fetchone=False, fetchall=False):
    async with db_lock:
        cur = db.cursor()
        cur.execute(query, params)
        db.commit()

        if fetchone:
            return cur.fetchone()

        if fetchall:
            return cur.fetchall()

        return None


async def init_db():
    await execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    await execute("""
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

    await execute("""
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

    await execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            destination TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    await execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT
        )
    """)

    await execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER UNIQUE NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT
        )
    """)

    await execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT,
            created_at TEXT
        )
    """)

    await execute("""
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

    await execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            opponent_id INTEGER,
            amount INTEGER NOT NULL,
            winner_id INTEGER,
            status TEXT DEFAULT 'waiting',
            chat_id INTEGER,
            message_id INTEGER,
            created_at TEXT
        )
    """)

    await execute("""
        CREATE TABLE IF NOT EXISTS support_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            support_id INTEGER,
            owner_id INTEGER,
            user_id INTEGER,
            message TEXT,
            created_at TEXT
        )
    """)

    owner = await execute(
        "SELECT value FROM settings WHERE key='owner_id'",
        fetchone=True,
    )

    if not owner:
        await execute(
            "INSERT INTO settings(key,value) VALUES('owner_id',?)",
            (str(INITIAL_OWNER_ID),),
        )

    reward = await execute(
        "SELECT value FROM settings WHERE key='referral_reward'",
        fetchone=True,
    )

    if not reward:
        await execute(
            "INSERT INTO settings(key,value) VALUES('referral_reward',?)",
            (str(DEFAULT_REFERRAL_REWARD),),
        )

    bot_status = await execute(
        "SELECT value FROM settings WHERE key='bot_enabled'",
        fetchone=True,
    )

    if not bot_status:
        await execute(
            "INSERT INTO settings(key,value) VALUES('bot_enabled','1')"
        )


async def get_setting(key, default=None):
    row = await execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
        fetchone=True,
    )

    if not row:
        return default

    return row["value"]


async def set_setting(key, value):
    await execute(
        """
        INSERT INTO settings(key,value)
        VALUES(?,?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
        """,
        (key, str(value)),
    )


async def get_owner_id():
    value = await get_setting(
        "owner_id",
        str(INITIAL_OWNER_ID),
    )
    return int(value)


async def set_owner_id(user_id):
    await set_setting("owner_id", user_id)


async def get_referral_reward():
    value = await get_setting(
        "referral_reward",
        DEFAULT_REFERRAL_REWARD,
    )
    return int(value)


async def set_referral_reward(amount):
    await set_setting(
        "referral_reward",
        amount,
    )


async def bot_enabled():
    value = await get_setting("bot_enabled", "1")
    return value == "1"


async def set_bot_enabled(enabled):
    await set_setting(
        "bot_enabled",
        "1" if enabled else "0",
    )


# =========================================================
# USER
# =========================================================

async def get_user(user_id):
    return await execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,),
        fetchone=True,
    )


async def get_user_by_username(username):
    username = username.lstrip("@")

    return await execute(
        """
        SELECT * FROM users
        WHERE LOWER(username)=LOWER(?)
        """,
        (username,),
        fetchone=True,
    )


async def create_or_update_user(tg_user, referrer_id=None):
    existing = await get_user(tg_user.id)

    if existing:
        await execute(
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

        return await get_user(tg_user.id)

    valid_referrer = None

    if referrer_id and referrer_id != tg_user.id:
        referrer = await get_user(referrer_id)

        if referrer:
            valid_referrer = referrer_id

    await execute(
        """
        INSERT INTO users
        (id,username,first_name,balance,referrer_id,blocked,verified,created_at)
        VALUES (?,?,?,0,?,0,0,?)
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
        reward = await get_referral_reward()

        try:
            await execute(
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

            await execute(
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

            await execute(
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

    return await get_user(tg_user.id)


async def is_blocked(user_id):
    user = await get_user(user_id)
    return bool(user and user["blocked"])


def user_name(user):
    if not user:
        return "کاربر"

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


# =========================================================
# VERIFICATION
# =========================================================

def verification_keyboard():
    button = KeyboardButton(
        "📱 تأیید شماره",
        request_contact=True,
    )

    return ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


async def verify_user(update: Update):
    user = await get_user(update.effective_user.id)

    if not user:
        user = await create_or_update_user(
            update.effective_user
        )

    if user["verified"]:
        return True

    contact = update.message.contact if update.message else None

    if contact:
        if contact.user_id != update.effective_user.id:
            await update.message.reply_text(
                "❌ لطفاً شماره خودتان را ارسال کنید.",
                reply_markup=verification_keyboard(),
            )
            return False

        await execute(
            """
            UPDATE users
            SET verified=1
            WHERE id=?
            """,
            (update.effective_user.id,),
        )

        await update.message.reply_text(
            "✅ شماره شما با موفقیت تأیید شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            ),
        )

        return True

    await update.message.reply_text(
        "🔐 برای استفاده از ربات ابتدا شماره خود را تأیید کنید.",
        reply_markup=verification_keyboard(),
    )

    return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id):
    rows = [
        ["💳 موجودی", "💰 واریزی"],
        ["💸 برداشت", "🔄 انتقال"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
    ]

    # بازی فقط در گروه استفاده می‌شود
    if user_id == INITIAL_OWNER_ID:
        pass

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [["❌ لغو"]],
        resize_keyboard=True,
    )


def admin_keyboard(enabled=True):
    status = "🟢 ربات روشن" if enabled else "🔴 ربات خاموش"

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
                status,
                callback_data="admin_toggle_bot",
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


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    args = context.args

    referrer_id = None

    if args:
        value = args[0]

        if value.startswith("ref_"):
            try:
                referrer_id = int(value[4:])
            except ValueError:
                pass

    user = await create_or_update_user(
        update.effective_user,
        referrer_id,
    )

    if user["blocked"]:
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    if not user["verified"]:
        await update.message.reply_text(
            "👋 سلام\n\n"
            "برای ورود به ربات ابتدا شماره خود را تأیید کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    if not await bot_enabled() and user["id"] != await get_owner_id():
        await update.message.reply_text(
            "🔴 ربات موقتاً خاموش است."
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
    user = await create_or_update_user(
        update.effective_user
    )

    if not user["verified"]:
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
    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"] or not user["verified"]:
        return

    if not await bot_enabled():
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
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
        "لطفاً مبلغ را به این آدرس/فرمت واریز کنید:\n\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از واریز رسید را ارسال کنید.\n"
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

    user = await create_or_update_user(
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

    await execute(
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

    row = await execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )

    deposit_id = row["id"]

    owner_id = await get_owner_id()

    caption = (
        "💰 درخواست واریزی\n\n"
        f"🆔 #{deposit_id}\n"
        f"👤 {user['first_name'] or '-'}\n"
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
        logger.error("Deposit owner notification error: %s", e)

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
    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"] or not user["verified"]:
        return

    if not await bot_enabled():
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
    user = await get_user(update.effective_user.id)

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

    if not amount:
        context.user_data.clear()
        return

    user = await get_user(update.effective_user.id)

    if not user or user["balance"] < amount:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # رزرو امن موجودی
    async with db_lock:
        cur = db.cursor()

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
            db.commit()

            await update.message.reply_text(
                "❌ موجودی تغییر کرده است. دوباره تلاش کنید."
            )
            context.user_data.clear()
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
        chat_id=await get_owner_id(),
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
    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"] or not user["verified"]:
        return

    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "🔄 انتقال فقط با Reply انجام می‌شود.\n\n"
            "روی پیام کاربر ریپلای کنید و بنویسید:\n"
            "انتقال ۵۰۰"
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "transfer_amount"

    await update.message.reply_text(
        "🔄 برای انتقال:\n\n"
        "روی پیام کاربر Reply کنید و مبلغ را بفرستید.\n\n"
        "مثال:\n"
        "انتقال ۵۰۰",
        reply_markup=cancel_keyboard(),
    )


def normalize_digits(text):
    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )

    return text.translate(table)


async def transfer_by_reply(update, context, amount):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ باید روی پیام کاربر Reply کنید."
        )
        return

    replied = update.message.reply_to_message.from_user

    if not replied or replied.is_bot:
        await update.message.reply_text(
            "❌ نمی‌توانید به ربات انتقال دهید."
        )
        return

    sender_id = update.effective_user.id
    receiver_id = replied.id

    if sender_id == receiver_id:
        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    sender = await get_user(sender_id)
    receiver = await get_user(receiver_id)

    if not sender:
        return

    if not receiver:
        # کاربر باید حداقل یک بار ربات را استارت کرده باشد
        await update.message.reply_text(
            "❌ این کاربر هنوز ربات را /start نکرده است."
        )
        return

    if not receiver["verified"]:
        await update.message.reply_text(
            "❌ گیرنده هنوز شماره خود را تأیید نکرده است."
        )
        return

    if sender["balance"] < amount:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی شما: {sender['balance']:,} DOGS"
        )
        return

    now = datetime.now().isoformat()

    # تراکنش اتمیک برای جلوگیری از دوبار کم شدن موجودی
    async with db_lock:
        cur = db.cursor()

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
            db.commit()

            await update.message.reply_text(
                "❌ انتقال انجام نشد؛ موجودی تغییر کرده است."
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

    context.user_data.clear()

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {user_name(receiver)}"
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

async def referrals(update, context):
    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"] or not user["verified"]:
        return

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start=ref_{user['id']}"
    )

    row = await execute(
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
        f"{await get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update, context):
    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"] or not user["verified"]:
        return

    context.user_data.clear()
    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را برای پشتیبانی ارسال کنید.\n\n"
        "متن، عکس یا فایل قبول است.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(update, context):
    user = await create_or_update_user(
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
            "❌ نوع پیام پشتیبانی قابل قبول نیست."
        )
        return

    await execute(
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

    row = await execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )

    support_id = row["id"]

    owner_id = await get_owner_id()

    caption = (
        "🎧 پیام پشتیبانی\n\n"
        f"🆔 #{support_id}\n"
        f"👤 {user['first_name'] or '-'}\n"
        f"🔢 ID: {user['id']}\n"
        f"📱 {user_name(user)}"
    )

    # دکمه پاسخ
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

    except Exception as e:
        logger.error("Support notify error: %s", e)

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای مالک ارسال شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# GAME
# =========================================================

async def create_game(update, context, amount):
    user = await get_user(update.effective_user.id)

    if not user or not user["verified"]:
        return

    if user["blocked"]:
        return

    if not await bot_enabled():
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    if amount < 500:
        await update.message.reply_text(
            "❌ حداقل مبلغ بازی ۵۰۰ DOGS است."
        )
        return

    if user["balance"] < amount:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"موجودی: {user['balance']:,} DOGS"
        )
        return

    # فقط یک بازی فعال برای هر سازنده
    active = await execute(
        """
        SELECT * FROM games
        WHERE creator_id=?
        AND status='waiting'
        LIMIT 1
        """,
        (user["id"],),
        fetchone=True,
    )

    if active:
        await update.message.reply_text(
            "❌ شما همین حالا یک بازی در انتظار دارید."
        )
        return

    # رزرو مبلغ سازنده
    async with db_lock:
        cur = db.cursor()

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
            db.commit()

            await update.message.reply_text(
                "❌ موجودی کافی نیست یا قبلاً استفاده شده."
            )
            return

        cur.execute(
            """
            INSERT INTO games
            (creator_id,opponent_id,amount,winner_id,status,chat_id,message_id,created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                user["id"],
                None,
                amount,
                None,
                "waiting",
                update.effective_chat.id,
                None,
                datetime.now().isoformat(),
            ),
        )

        game_id = cur.lastrowid

        db.commit()

    keyboard = game_keyboard(game_id)

    message = await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"👤 سازنده: {user_name(user)}\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
        "یک نفر می‌تواند وارد بازی شود.\n"
        "بعد از ورود نفر دوم، بازی خودکار شروع می‌شود.",
        reply_markup=keyboard,
    )

    await execute(
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


async def game_join(update, context, game_id):
    query = update.callback_query

    user = await get_user(query.from_user.id)

    if not user:
        await query.answer(
            "❌ ابتدا /start را بزنید.",
            show_alert=True,
        )
        return

    if not user["verified"]:
        await query.answer(
            "🔐 ابتدا شماره خود را تأیید کنید.",
            show_alert=True,
        )
        return

    if user["blocked"]:
        await query.answer(
            "🚫 حساب شما مسدود است.",
            show_alert=True,
        )
        return

    if not await bot_enabled():
        await query.answer(
            "🔴 ربات خاموش است.",
            show_alert=True,
        )
        return

    game = await execute(
        """
        SELECT * FROM games
        WHERE id=?
        """,
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
            "❌ این بازی قبلاً شروع یا تمام شده است.",
            show_alert=True,
        )
        return

    if game["creator_id"] == user["id"]:
        await query.answer(
            "❌ شما سازنده بازی هستید.",
            show_alert=True,
        )
        return

    amount = game["amount"]

    # اتمیک:
    # 1) چک موجودی
    # 2) کم کردن مبلغ
    # 3) ثبت بازیکن
    async with db_lock:
        cur = db.cursor()

        cur.execute(
            """
            SELECT status, creator_id, opponent_id, amount
            FROM games
            WHERE id=?
            """,
            (game_id,),
        )

        current = cur.fetchone()

        if not current or current["status"] != "waiting":
            db.commit()

            await query.answer(
                "❌ این بازی قبلاً گرفته شده است.",
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
                amount,
                user["id"],
                amount,
            ),
        )

        if cur.rowcount != 1:
            db.commit()

            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True,
            )
            return

        cur.execute(
            """
            UPDATE games
            SET opponent_id=?,
                status='playing'
            WHERE id=?
            AND status='waiting'
            """,
            (
                user["id"],
                game_id,
            ),
        )

        if cur.rowcount != 1:
            # برگشت مبلغ در صورت race
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

            db.commit()

            await query.answer(
                "❌ شخص دیگری زودتر وارد بازی شد.",
                show_alert=True,
            )
            return

        db.commit()

    await query.answer(
        "🎮 وارد بازی شدید!",
        show_alert=False,
    )

    # پیام بازی را آپدیت می‌کنیم
    try:
        await query.edit_message_text(
            "🎮 بازی شروع شد!\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"👤 بازیکن اول: {game['creator_id']}\n"
            f"👤 بازیکن دوم: {user['id']}\n\n"
            "⏳ در حال تعیین برنده..."
        )
    except Exception:
        pass

    # تأخیر کوتاه برای حالت واقعی بازی
    await asyncio.sleep(2)

    # انتخاب برنده
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
    winner_reward = int(
        round(amount * GAME_WIN_MULTIPLIER)
    )

    # سهم مالک از طرف خود ربات
    owner_reward = GAME_OWNER_REWARD

    # ضد دوباره اجرا شدن
    async with db_lock:
        cur = db.cursor()

        cur.execute(
            """
            SELECT status
            FROM games
            WHERE id=?
            """,
            (game_id,),
        )

        state = cur.fetchone()

        if not state or state["status"] != "playing":
            db.commit()
            return

        cur.execute(
            """
            UPDATE games
            SET winner_id=?,
                status='finished'
            WHERE id=?
            AND status='playing'
            """,
            (
                winner_id,
                game_id,
            ),
        )

        if cur.rowcount != 1:
            db.commit()
            return

        # جایزه برنده از طرف ربات
        cur.execute(
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

        # سهم مالک کاملاً جدا از بازیکنان
        owner_id = await get_owner_id()

        cur.execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                owner_reward,
                owner_id,
            ),
        )

        now = datetime.now().isoformat()

        cur.execute(
            """
            INSERT INTO transactions
            (user_id,type,amount,description,created_at)
            VALUES (?,?,?,?,?)
            """,
            (
                winner_id,
                "game_win",
                winner_reward,
                f"Game #{game_id}",
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
                loser_id,
                "game_loss",
                0,
                f"Game #{game_id}",
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
                owner_id,
                "game_owner_reward",
                owner_reward,
                f"Owner reward Game #{game_id}",
                now,
            ),
        )

        db.commit()

    winner = await get_user(winner_id)
    loser = await get_user(loser_id)

    try:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            text=(
                "🏁 بازی تمام شد!\n\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
                f"🏆 برنده: {user_name(winner)}\n"
                f"🎁 جایزه: {winner_reward:,} DOGS\n\n"
                f"👤 بازنده: {user_name(loser)}\n\n"
                f"👑 سهم مالک: {owner_reward:,} DOGS"
            ),
        )
    except Exception:
        pass

    # نتیجه برنده
    try:
        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 شما برنده شدید!\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n"
                f"🎁 جایزه شما: {winner_reward:,} DOGS"
            ),
        )
    except Exception:
        pass

    # نتیجه بازنده
    try:
        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "😔 شما باختید.\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
                "امیدواریم در بازی بعدی برنده شوید ❤️"
            ),
        )
    except Exception:
        pass


async def game_cancel(update, context, game_id):
    query = update.callback_query

    user = await get_user(query.from_user.id)

    if not user:
        await query.answer(
            "❌ کاربر پیدا نشد.",
            show_alert=True,
        )
        return

    if user["id"] != await get_owner_id():
        pass

    game = await execute(
        """
        SELECT * FROM games
        WHERE id=?
        """,
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
            "❌ این بازی دیگر قابل لغو نیست.",
            show_alert=True,
        )
        return

    if game["creator_id"] != user["id"] and user["id"] != await get_owner_id():
        await query.answer(
            "⛔ فقط سازنده بازی می‌تواند آن را لغو کند.",
            show_alert=True,
        )
        return

    async with db_lock:
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
            db.commit()

            await query.answer(
                "❌ بازی قبلاً لغو شده.",
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

    await query.answer(
        "✅ بازی لغو شد."
    )

    try:
        await query.edit_message_text(
            "❌ این بازی لغو شد.\n\n"
            f"💰 {game['amount']:,} DOGS به موجودی سازنده برگشت."
        )
    except Exception:
        pass


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(update, context):
    user = await get_user(update.effective_user.id)

    if not user or user["id"] != await get_owner_id():
        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )
        return

    await update.message.reply_text(
        "🛠 پنل مدیریت\n\n"
        f"وضعیت: {'🟢 روشن' if await bot_enabled() else '🔴 خاموش'}",
        reply_markup=admin_keyboard(
            await bot_enabled()
        ),
    )


async def admin_only(user_id):
    return user_id == await get_owner_id()


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def callback_handler(update, context):
    query = update.callback_query

    data = query.data or ""

    # ---------------------------------------
    # GAME CALLBACKS
    # ---------------------------------------

    if data.startswith("game_join:"):
        try:
            game_id = int(data.split(":")[1])
        except Exception:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        await game_join(
            update,
            context,
            game_id,
        )
        return

    if data.startswith("game_cancel:"):
        try:
            game_id = int(data.split(":")[1])
        except Exception:
            await query.answer(
                "❌ درخواست نامعتبر.",
                show_alert=True,
            )
            return

        await game_cancel(
            update,
            context,
            game_id,
        )
        return

    # ---------------------------------------
    # SUPPORT REPLY
    # ---------------------------------------

    if data.startswith("support_reply:"):
        if not await admin_only(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )
            return

        try:
            support_id = int(data.split(":")[1])
        except Exception:
            await query.answer(
                "❌ نامعتبر.",
                show_alert=True,
            )
            return

        support = await execute(
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
        context.user_data["state"] = "admin_support_reply"
        context.user_data["support_id"] = support_id
        context.user_data["support_user_id"] = support["user_id"]

        await query.answer()

        await query.message.reply_text(
            "💬 پاسخ خود را ارسال کنید.\n\n"
            "این پیام برای همان کاربر ارسال می‌شود."
        )

        return

    # ---------------------------------------
    # ADMIN AUTH
    # ---------------------------------------

    if not await admin_only(query.from_user.id):
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )
        return

    await query.answer()

    # ---------------------------------------
    # BOT TOGGLE
    # ---------------------------------------

    if data == "admin_toggle_bot":
        current = await bot_enabled()

        await set_bot_enabled(not current)

        try:
            await query.edit_message_text(
                "🛠 پنل مدیریت\n\n"
                f"وضعیت ربات: "
                f"{'🟢 روشن' if not current else '🔴 خاموش'}",
                reply_markup=admin_keyboard(not current),
            )
        except Exception:
            pass

        return

    # ---------------------------------------
    # DEPOSIT
    # ---------------------------------------

    if data.startswith("deposit_"):
        try:
            action, id_text = data.split(":")
            deposit_id = int(id_text)
        except Exception:
            return

        deposit = await execute(
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
                "❌ این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )
            return

        # تغییر وضعیت اتمیک
        if action == "deposit_approve":

            async with db_lock:
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
                    db.commit()

                    await query.answer(
                        "❌ قبلاً بررسی شده.",
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

            try:
                await query.edit_message_reply_markup(
                    reply_markup=None
                )
            except Exception:
                pass

            await context.bot.send_message(
                chat_id=deposit["user_id"],
                text=(
                    "✅ واریزی شما تأیید شد.\n\n"
                    f"💰 {deposit['amount']:,} DOGS"
                ),
            )

            return

        if action == "deposit_reject":

            await execute(
                """
                UPDATE deposits
                SET status='rejected'
                WHERE id=?
                AND status='pending'
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

    # ---------------------------------------
    # WITHDRAW
    # ---------------------------------------

    if data.startswith("withdraw_"):
        try:
            action, id_text = data.split(":")
            withdrawal_id = int(id_text)
        except Exception:
            return

        withdrawal = await execute(
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
                "❌ قبلاً بررسی شده.",
                show_alert=True,
            )
            return

        if action == "withdraw_approve":

            await execute(
                """
                UPDATE withdrawals
                SET status='approved'
                WHERE id=?
                AND status='pending'
                """,
                (withdrawal_id,),
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

            return

        if action == "withdraw_reject":

            async with db_lock:
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
                    db.commit()

                    await query.answer(
                        "❌ قبلاً بررسی شده.",
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

    # ---------------------------------------
    # ADMIN MENU
    # ---------------------------------------

    if data == "admin_balances":

        users = await execute(
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
                f"📱 {('@' + u['username']) if u['username'] else '-'}\n"
                f"💰 {u['balance']:,} DOGS\n\n"
            )

            if len(text) + len(line) > 3800:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=text,
                )
                text = ""

            text += line

        if text:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=text,
            )

        return

    if data == "admin_deposits":

        rows = await execute(
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

        text = "💰 واریزی‌ها\n\n"

        for d in rows:
            text += (
                f"#{d['id']} | "
                f"{d['amount']:,} | "
                f"{d['status']} | "
                f"ID: {d['user_id']}\n"
            )

        await query.message.reply_text(text)
        return

    if data == "admin_withdrawals":

        rows = await execute(
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

        text = "💸 برداشت‌ها\n\n"

        for w in rows:
            text += (
                f"#{w['id']} | "
                f"{w['amount']:,} | "
                f"{w['status']} | "
                f"ID: {w['user_id']}\n"
            )

        await query.message.reply_text(text)
        return

    if data == "admin_stats":

        users = await execute(
            "SELECT COUNT(*) AS c FROM users",
            fetchone=True,
        )

        total_balance = await execute(
            "SELECT COALESCE(SUM(balance),0) AS s FROM users",
            fetchone=True,
        )

        refs = await execute(
            "SELECT COUNT(*) AS c FROM referrals",
            fetchone=True,
        )

        games = await execute(
            "SELECT COUNT(*) AS c FROM games",
            fetchone=True,
        )

        await query.message.reply_text(
            "📊 آمار\n\n"
            f"👥 کاربران: {users['c']}\n"
            f"💰 مجموع موجودی: {total_balance['s']:,} DOGS\n"
            f"👥 رفرال: {refs['c']}\n"
            f"🎮 بازی‌ها: {games['c']}\n"
            f"🎁 جایزه رفرال: "
            f"{await get_referral_reward():,} DOGS\n"
            f"👑 سهم مالک بازی: "
            f"{GAME_OWNER_REWARD:,} DOGS"
        )

        return

    if data == "admin_referral_reward":

        context.user_data.clear()
        context.user_data["state"] = "admin_referral_reward"

        await query.message.reply_text(
            f"🎁 جایزه فعلی: "
            f"{await get_referral_reward():,} DOGS\n\n"
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
            "🚫 آیدی کاربر:"
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
# ADMIN STATES
# =========================================================

async def admin_state_handler(update, context):

    user = await get_user(update.effective_user.id)

    if not user:
        return False

    if user["id"] != await get_owner_id():
        return False

    state = context.user_data.get("state")

    if not state:
        return False

    text = update.message.text.strip()

    # ---------------------------------------
    # SUPPORT REPLY
    # ---------------------------------------

    if state == "admin_support_reply":

        support_user_id = context.user_data.get(
            "support_user_id"
        )

        support_id = context.user_data.get(
            "support_id"
        )

        if not support_user_id:
            context.user_data.clear()
            return True

        try:
            await context.bot.send_message(
                chat_id=support_user_id,
                text=(
                    "💬 پاسخ پشتیبانی:\n\n"
                    f"{text}"
                ),
            )

            await execute(
                """
                INSERT INTO support_replies
                (support_id,owner_id,user_id,message,created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    support_id,
                    user["id"],
                    support_user_id,
                    text,
                    datetime.now().isoformat(),
                ),
            )

            await update.message.reply_text(
                "✅ پاسخ برای کاربر ارسال شد."
            )

        except Exception:
            await update.message.reply_text(
                "❌ ارسال پاسخ انجام نشد."
            )

        context.user_data.clear()
        return True

    # ---------------------------------------
    # REFERRAL
    # ---------------------------------------

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

        await set_referral_reward(amount)

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 {amount:,} DOGS",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    # ---------------------------------------
    # OWNER
    # ---------------------------------------

    if state == "admin_transfer_owner":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        new_owner = int(text)

        if not await get_user(new_owner):
            await update.message.reply_text(
                "❌ این کاربر هنوز /start نکرده است."
            )
            return True

        old_owner = await get_owner_id()

        await set_owner_id(new_owner)

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
            "Owner transferred %s -> %s",
            old_owner,
            new_owner,
        )

        return True

    # ---------------------------------------
    # ADD / REMOVE
    # ---------------------------------------

    if state in (
        "admin_add_balance",
        "admin_remove_balance",
    ):

        parts = normalize_digits(text).split()

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

        target = await get_user(target_id)

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return True

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ نامعتبر."
            )
            return True

        if state == "admin_add_balance":

            await execute(
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

            await execute(
                """
                INSERT INTO transactions
                (user_id,type,amount,description,created_at)
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

            message = (
                f"✅ {amount:,} DOGS به کاربر "
                f"{target_id} اضافه شد."
            )

        else:

            if target["balance"] < amount:
                await update.message.reply_text(
                    "❌ موجودی کاربر کافی نیست."
                )
                return True

            await execute(
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

            await execute(
                """
                INSERT INTO transactions
                (user_id,type,amount,description,created_at)
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

            message = (
                f"✅ {amount:,} DOGS از کاربر "
                f"{target_id} کم شد."
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

    # ---------------------------------------
    # BLOCK
    # ---------------------------------------

    if state == "admin_block":

        if not text.isdigit():
            await update.message.reply_text(
                "❌ ID عددی وارد کنید."
            )
            return True

        target_id = int(text)

        target = await get_user(target_id)

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return True

        new_status = 0 if target["blocked"] else 1

        await execute(
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

    # ---------------------------------------
    # BROADCAST
    # ---------------------------------------

    if state == "admin_broadcast":

        users = await execute(
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
            f"📢 پیام همگانی ارسال شد.\n"
            f"👥 ارسال موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    return False


# =========================================================
# CANCEL
# =========================================================

async def cancel(update, context):

    user = await create_or_update_user(
        update.effective_user
    )

    context.user_data.clear()

    await update.message.reply_text(
        "❌ لغو شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    if not update.message or not update.message.text:
        return

    user = await create_or_update_user(
        update.effective_user
    )

    # لغو همیشه فعال
    if update.message.text.strip() == "❌ لغو":
        await cancel(update, context)
        return

    # شماره تأیید
    if (
        update.message.contact
        and update.message.contact.user_id
        == update.effective_user.id
    ):
        await verify_user(update)
        return

    # بلاک
    if user["blocked"]:
        await update.message.reply_text(
            "🚫 حساب شما مسدود شده است."
        )
        return

    # تأیید شماره
    if not user["verified"]:
        await verify_user(update)
        return

    # ---------------------------------------
    # ADMIN STATE
    # ---------------------------------------

    if await admin_state_handler(
        update,
        context,
    ):
        return

    # ---------------------------------------
    # STATE
    # ---------------------------------------

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

    if state == "transfer_amount":

        text = normalize_digits(
            update.message.text.strip()
        )

        match = re.fullmatch(
            r"انتقال\s+(\d+)",
            text,
        )

        if not match:
            await update.message.reply_text(
                "❌ فرمت صحیح:\n\n"
                "روی پیام کاربر Reply کنید:\n"
                "انتقال ۵۰۰"
            )
            return

        amount = int(match.group(1))

        await transfer_by_reply(
            update,
            context,
            amount,
        )
        return

    if state == "support":
        await support_message(update, context)
        return

    # ---------------------------------------
    # MAIN BUTTONS
    # ---------------------------------------

    text = update.message.text.strip()

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

    # ---------------------------------------
    # TRANSFER DIRECT COMMAND IN GROUP
    # ONLY REPLY
    # ---------------------------------------

    normalized = normalize_digits(text)

    match = re.fullmatch(
        r"انتقال\s+(\d+)",
        normalized,
    )

    if match:

        amount = int(match.group(1))

        await transfer_by_reply(
            update,
            context,
            amount,
        )

        return

    # ---------------------------------------
    # GAME COMMAND
    # ---------------------------------------

    game_match = re.fullmatch(
        r"بازی\s+(\d+)",
        normalized,
    )

    if game_match:

        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "🎮 بازی فقط در گروه قابل ساخت است."
            )
            return

        amount = int(game_match.group(1))

        await create_game(
            update,
            context,
            amount,
        )

        return


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(update, context):

    if not update.message:
        return

    user = await create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:
        return

    if not user["verified"]:
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

    if state == "admin_broadcast":
        if await admin_state_handler(
            update,
            context,
        ):
            return

    await update.message.reply_text(
        "❌ ابتدا یک عملیات را انتخاب کنید."
    )


# =========================================================
# CONTACT ROUTER
# =========================================================

async def contact_router(update, context):

    if not update.message:
        return

    contact = update.message.contact

    if not contact:
        return

    if contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را ارسال کنید.",
            reply_markup=verification_keyboard(),
        )
        return

    await create_or_update_user(
        update.effective_user
    )

    await execute(
        """
        UPDATE users
        SET verified=1
        WHERE id=?
        """,
        (update.effective_user.id,),
    )

    await update.message.reply_text(
        "✅ شماره با موفقیت تأیید شد.\n\n"
        "🎉 حالا می‌توانید از ربات استفاده کنید.",
        reply_markup=main_keyboard(
            update.effective_user.id
        ),
    )


# =========================================================
# MAIN
# =========================================================

async def post_init(application):
    await init_db()
    logger.info("DATABASE INITIALIZED")


def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # فقط یک CommandHandler برای start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # همه دکمه‌های Inline
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # شماره تأیید
    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_router,
        )
    )

    # عکس / فایل
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            media_router,
        )
    )

    # متن
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
