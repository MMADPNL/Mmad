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

# سهم ثابت مالک از هر بازی
GAME_OWNER_FEE = 50

# حداقل بازی
MIN_GAME_BET = 500

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
            phone_verified INTEGER DEFAULT 0,
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

    # بازی‌ها
    execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            message_id INTEGER,
            creator_id INTEGER NOT NULL,
            opponent_id INTEGER,
            bet INTEGER NOT NULL,
            status TEXT DEFAULT 'waiting',
            winner_id INTEGER,
            loser_id INTEGER,
            owner_fee INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # جلوگیری از بازی همزمان کاربر
    execute("""
        CREATE TABLE IF NOT EXISTS game_players (
            user_id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL
        )
    """)

    # owner
    owner = execute(
        "SELECT value FROM settings WHERE key='owner_id'",
        fetchone=True,
    )

    if not owner:
        execute(
            "INSERT INTO settings(key,value) VALUES('owner_id',?)",
            (str(INITIAL_OWNER_ID),),
        )

    # referral
    reward = execute(
        "SELECT value FROM settings WHERE key='referral_reward'",
        fetchone=True,
    )

    if not reward:
        execute(
            "INSERT INTO settings(key,value) VALUES('referral_reward',?)",
            (str(DEFAULT_REFERRAL_REWARD),),
        )

    # bot status
    status = execute(
        "SELECT value FROM settings WHERE key='bot_enabled'",
        fetchone=True,
    )

    if not status:
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
# USERS
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

    # رفرال
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
                VALUES (?, ?, ?, ?, ?)
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

    return bool(
        user and user["blocked"]
    )


def is_verified(user_id):
    user = get_user(user_id)

    return bool(
        user and user["phone_verified"]
    )


def user_name(user):

    if not user:
        return "کاربر"

    if user["username"]:
        return f"@{user['username']}"

    return user["first_name"] or str(user["id"])


# =========================================================
# BOT ACCESS
# =========================================================

def owner(user_id):
    return user_id == get_owner_id()


async def check_user_access(update):

    if not update.effective_user:
        return False

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:

        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🚫 حساب شما مسدود شده است."
                )
            except Exception:
                pass

        return False

    return True


async def check_bot_enabled(update):

    if owner(update.effective_user.id):
        return True

    if not bot_enabled():

        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🔴 ربات موقتاً خاموش است.\n\n"
                    "لطفاً بعداً دوباره تلاش کنید."
                )
            except Exception:
                pass

        return False

    return True


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id):

    rows = [
        ["💸 برداشت", "💰 واریزی"],
        ["💳 موجودی", "🔄 انتقال"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
        ["📱 تأیید شماره"],
    ]

    if owner(user_id):
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
                    "📱 ارسال شماره و تأیید",
                    request_contact=True,
                )
            ],
            ["❌ لغو"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def admin_keyboard():

    status = (
        "🟢 ربات روشن"
        if bot_enabled()
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
                "🎧 پیام‌های پشتیبانی",
                callback_data="admin_support",
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
                status,
                callback_data="admin_toggle_bot",
            )
        ],
    ])


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

    await update.message.reply_text(
        "سلام 👋\n\n"
        "به ربات خوش آمدید ❤️\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# PHONE VERIFICATION
# =========================================================

async def phone_start(update, context):

    user = create_or_update_user(
        update.effective_user
    )

    if user["blocked"]:
        return

    if not await check_bot_enabled(update):
        return

    if user["phone_verified"]:

        await update.message.reply_text(
            "✅ شماره شما قبلاً تأیید شده است.",
            reply_markup=main_keyboard(user["id"]),
        )

        return

    await update.message.reply_text(
        "📱 برای تأیید حساب، روی دکمه زیر بزنید "
        "و شماره خودتان را ارسال کنید.",
        reply_markup=phone_keyboard(),
    )


async def contact_handler(update, context):

    if not update.message or not update.message.contact:
        return

    contact = update.message.contact
    tg_user = update.effective_user

    if contact.user_id and contact.user_id != tg_user.id:

        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را ارسال کنید."
        )

        return

    user = create_or_update_user(tg_user)

    execute(
        """
        UPDATE users
        SET phone_verified=1,
            phone=?
        WHERE id=?
        """,
        (
            contact.phone_number,
            tg_user.id,
        ),
    )

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تأیید شد.",
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update, context):

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        "💳 موجودی شما:\n\n"
        f"💰 {user['balance']:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update, context):

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    context.user_data.clear()
    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        f"💰 مبلغ واریزی را وارد کنید.\n\n"
        f"حداقل واریزی: {MIN_DEPOSIT:,} DOGS",
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
            f"❌ حداقل واریزی "
            f"{MIN_DEPOSIT:,} DOGS است."
        )

        return

    context.user_data["deposit_amount"] = amount
    context.user_data["state"] = "deposit_receipt"

    await update.message.reply_text(
        f"💰 مبلغ واریزی: {amount:,} DOGS\n\n"
        "لطفاً مبلغ را واریز کنید:\n\n"
        f"ULTRA {amount} DOGS @CyyFr\n\n"
        "بعد از واریز، رسید را همینجا ارسال کنید.\n"
        "🖼 عکس یا 📝 متن رسید هر دو قابل قبول است.",
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

    if not bot_enabled() and not owner(
        update.effective_user.id
    ):
        context.user_data.clear()

        await update.message.reply_text(
            "🔴 ربات خاموش است."
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
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (
            user["id"],
            amount,
            receipt_type,
            receipt_text,
            receipt_file_id,
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
                text=(
                    caption +
                    f"\n\n📝 رسید:\n{receipt_text}"
                ),
                reply_markup=keyboard,
            )

    except Exception as e:

        logger.exception(
            "Could not send deposit to owner: %s",
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

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    user = get_user(update.effective_user.id)

    if user["balance"] < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
            f"موجودی شما: {user['balance']:,} DOGS"
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
            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."
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
        "آیدی عددی:\n"
        "123456789\n\n"
        "یا یوزرنیم:\n"
        "@username",
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

    user = get_user(
        update.effective_user.id
    )

    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست منقضی شده."
        )

        return

    # ضد باگ:
    # برداشت فقط اگر واقعاً موجودی کافی باشد رزرو می‌شود.
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
            "❌ موجودی کافی نیست."
        )

        context.user_data.clear()

        return

    db.commit()

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
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (
            user["id"],
            amount,
            destination,
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
# TRANSFER
# =========================================================

async def transfer_start(update, context):

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    context.user_data.clear()
    context.user_data["state"] = "transfer_destination"

    await update.message.reply_text(
        "🔄 مقصد انتقال را وارد کنید.\n\n"
        "مثال:\n"
        "@username\n"
        "یا\n"
        "123456789\n\n"
        "همچنین می‌توانید روی پیام کاربر Reply "
        "کنید و مبلغ را بفرستید.",
        reply_markup=cancel_keyboard(),
    )


def find_transfer_receiver(update, text):

    if update.message.reply_to_message:

        replied = (
            update.message.reply_to_message.from_user
        )

        if replied and not replied.is_bot:

            return get_user(replied.id)

    if text.isdigit():
        return get_user(int(text))

    if text.startswith("@"):
        return get_user_by_username(text)

    return None


async def transfer_destination(update, context):

    text = update.message.text.strip()

    receiver = find_transfer_receiver(
        update,
        text,
    )

    # reply + مبلغ
    if (
        not receiver
        and update.message.reply_to_message
        and text.isdigit()
    ):

        replied = (
            update.message.reply_to_message.from_user
        )

        receiver = get_user(replied.id)

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
            "❌ کاربر پیدا نشد."
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


async def transfer_amount(update, context):

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )

        return

    amount = int(text)

    receiver_id = context.user_data.get(
        "transfer_receiver"
    )

    if not receiver_id:

        context.user_data.clear()
        return

    await complete_transfer(
        update,
        context,
        receiver_id,
        amount,
    )


async def complete_transfer(
    update,
    context,
    receiver_id,
    amount,
):

    if not await check_bot_enabled(update):
        return

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
            "❌ انتقال به خودتان ممکن نیست."
        )

        return

    # ضد race condition
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

    db.commit()

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
        VALUES (?, ?, ?, ?)
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
        VALUES (?, ?, ?, ?, ?)
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
        VALUES (?, ?, ?, ?, ?)
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
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 مقصد: {user_name(receiver)}",
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
# REFERRALS
# =========================================================

async def referrals(update, context):

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
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
        f"👤 تعداد: {row['count']}\n"
        f"🎁 پاداش هر نفر: "
        f"{get_referral_reward():,} DOGS\n\n"
        f"🔗 لینک دعوت:\n{link}"
    )


# =========================================================
# SUPPORT
# =========================================================

async def support_start(update, context):

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    context.user_data.clear()
    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پیام خود را ارسال کنید.\n\n"
        "متن، عکس یا فایل قابل ارسال است.\n\n"
        "برای لغو روی ❌ لغو بزنید.",
        reply_markup=cancel_keyboard(),
    )


async def support_message(update, context):

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
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (
            user["id"],
            text,
            file_id,
            file_type,
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
        "↩️ برای پاسخ، روی همین پیام Reply کنید."
    )

    try:

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
                text=(
                    caption +
                    f"\n\n📝 {text}"
                ),
            )

    except Exception as e:

        logger.exception(
            "Support send error: %s",
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

async def owner_reply_handler(update, context):

    if not update.message:
        return False

    if not owner(update.effective_user.id):
        return False

    replied = update.message.reply_to_message

    if not replied:
        return False

    # پیدا کردن support id از متن کپشن/پیام
    source_text = (
        replied.caption
        or replied.text
        or ""
    )

    match = re.search(
        r"🆔\s*#(\d+)",
        source_text,
    )

    if not match:
        return False

    support_id = int(match.group(1))

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
        await update.message.reply_text(
            "❌ پیام پشتیبانی پیدا نشد."
        )

        return True

    target_id = support["user_id"]

    try:

        if update.message.text:

            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎧 پاسخ پشتیبانی:\n\n"
                    f"{update.message.text}"
                ),
            )

        elif update.message.photo:

            await context.bot.send_photo(
                chat_id=target_id,
                photo=update.message.photo[-1].file_id,
                caption=(
                    "🎧 پاسخ پشتیبانی:\n\n"
                    f"{update.message.caption or ''}"
                ),
            )

        elif update.message.document:

            await context.bot.send_document(
                chat_id=target_id,
                document=update.message.document.file_id,
                caption=(
                    "🎧 پاسخ پشتیبانی:\n\n"
                    f"{update.message.caption or ''}"
                ),
            )

        else:

            return False

        execute(
            """
            UPDATE support_messages
            SET status='answered'
            WHERE id=?
            """,
            (support_id,),
        )

        await update.message.reply_text(
            "✅ پاسخ برای کاربر ارسال شد."
        )

    except Exception as e:

        logger.exception(
            "Support reply error: %s",
            e,
        )

        await update.message.reply_text(
            "❌ ارسال پاسخ ناموفق بود."
        )

    return True


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update, context):

    if not owner(update.effective_user.id):

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

    if not await check_bot_enabled(update):
        return

    if amount < MIN_GAME_BET:

        await update.effective_message.reply_text(
            f"❌ حداقل بازی "
            f"{MIN_GAME_BET:,} DOGS است."
        )

        return

    user = get_user(update.effective_user.id)

    if not user:

        return

    # کاربر نباید همزمان بازی دیگری داشته باشد
    existing = execute(
        """
        SELECT *
        FROM game_players
        WHERE user_id=?
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:

        await update.effective_message.reply_text(
            "❌ شما در یک بازی دیگر هستید."
        )

        return

    if user["balance"] < amount:

        await update.effective_message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی: {user['balance']:,} DOGS"
        )

        return

    # رزرو موجودی بازیکن اول
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

        await update.effective_message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    db.commit()

    execute(
        """
        INSERT INTO games
        (
            group_id,
            creator_id,
            bet,
            status,
            created_at
        )
        VALUES (?, ?, ?, 'waiting', ?)
        """,
        (
            update.effective_chat.id,
            user["id"],
            amount,
            datetime.now().isoformat(),
        ),
    )

    game_id = execute(
        "SELECT last_insert_rowid() AS id",
        fetchone=True,
    )["id"]

    execute(
        """
        INSERT INTO game_players(user_id,game_id)
        VALUES (?,?)
        """,
        (
            user["id"],
            game_id,
        ),
    )

    msg = await update.effective_message.reply_text(
        "🎮 بازی جدید\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"👤 سازنده: {user_name(user)}\n\n"
        "یک نفر می‌تواند وارد بازی شود.\n\n"
        "با ورود نفر دوم، بازی خودکار انجام می‌شود.",
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

    if not bot_enabled():

        await query.answer(
            "🔴 ربات خاموش است.",
            show_alert=True,
        )

        return

    user = get_user(query.from_user.id)

    if not user:

        user = create_or_update_user(
            query.from_user
        )

    if user["blocked"]:

        await query.answer(
            "🚫 حساب شما مسدود است.",
            show_alert=True,
        )

        return

    game = execute(
        """
        SELECT *
        FROM games
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
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True,
        )

        return

    if game["creator_id"] == user["id"]:

        await query.answer(
            "❌ خودتان نمی‌توانید وارد بازی خودتان شوید.",
            show_alert=True,
        )

        return

    # چک بازی همزمان
    existing = execute(
        """
        SELECT *
        FROM game_players
        WHERE user_id=?
        """,
        (user["id"],),
        fetchone=True,
    )

    if existing:

        await query.answer(
            "❌ شما در یک بازی دیگر هستید.",
            show_alert=True,
        )

        return

    bet = game["bet"]

    if user["balance"] < bet:

        await query.answer(
            "❌ موجودی کافی نیست.",
            show_alert=True,
        )

        return

    # رزرو مبلغ نفر دوم
    cur = db.cursor()

    cur.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=? AND balance>=?
        """,
        (
            bet,
            user["id"],
            bet,
        ),
    )

    if cur.rowcount != 1:

        db.commit()

        await query.answer(
            "❌ موجودی کافی نیست.",
            show_alert=True,
        )

        return

    db.commit()

    # ثبت بازیکن دوم
    execute(
        """
        INSERT INTO game_players(user_id,game_id)
        VALUES (?,?)
        """,
        (
            user["id"],
            game_id,
        ),
    )

    # تغییر وضعیت
    cur = db.cursor()

    cur.execute(
        """
        UPDATE games
        SET opponent_id=?,
            status='playing'
        WHERE id=? AND status='waiting'
        """,
        (
            user["id"],
            game_id,
        ),
    )

    if cur.rowcount != 1:

        db.commit()

        # اگر به هر دلیل بازی قبلاً شروع شده، پول را برگردان
        execute(
            """
            UPDATE users
            SET balance=balance+?
            WHERE id=?
            """,
            (
                bet,
                user["id"],
            ),
        )

        await query.answer(
            "❌ این بازی قبلاً شروع شده.",
            show_alert=True,
        )

        return

    db.commit()

    await query.answer(
        "🎮 وارد بازی شدید!"
    )

    # اجرای بازی
    await run_game(
        context,
        game_id,
    )


async def run_game(context, game_id):

    game = execute(
        """
        SELECT *
        FROM games
        WHERE id=?
        """,
        (game_id,),
        fetchone=True,
    )

    if not game:
        return

    if game["status"] != "playing":
        return

    creator_id = game["creator_id"]
    opponent_id = game["opponent_id"]
    bet = game["bet"]

    if not opponent_id:
        return

    # نتیجه تصادفی
    winner_id = random.choice(
        [
            creator_id,
            opponent_id,
        ]
    )

    loser_id = (
        opponent_id
        if winner_id == creator_id
        else creator_id
    )

    # مجموع پول
    pot = bet * 2

    # سهم مالک ثابت 50
    owner_fee = GAME_OWNER_FEE

    # جایزه برنده
    winner_reward = pot - owner_fee

    if winner_reward < 0:
        winner_reward = 0

    # اول وضعیت بازی را نهایی می‌کنیم
    # تا دوباره اجرا نشود.
    cur = db.cursor()

    cur.execute(
        """
        UPDATE games
        SET status='finished',
            winner_id=?,
            loser_id=?,
            owner_fee=?
        WHERE id=? AND status='playing'
        """,
        (
            winner_id,
            loser_id,
            owner_fee,
            game_id,
        ),
    )

    if cur.rowcount != 1:

        db.commit()
        return

    db.commit()

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
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            winner_id,
            "game_win",
            winner_reward,
            f"Game #{game_id}",
            datetime.now().isoformat(),
        ),
    )

    # سهم مالک
    execute(
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
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            get_owner_id(),
            "game_fee",
            owner_fee,
            f"Game fee #{game_id}",
            datetime.now().isoformat(),
        ),
    )

    # پاک کردن بازیکنان فعال
    execute(
        """
        DELETE FROM game_players
        WHERE game_id=?
        """,
        (game_id,),
    )

    creator = get_user(creator_id)
    opponent = get_user(opponent_id)

    # پیام گروه
    try:

        await context.bot.edit_message_text(
            chat_id=game["group_id"],
            message_id=game["message_id"],
            text=(
                "🎮 بازی انجام شد!\n\n"
                f"💰 مبلغ بازی: {bet:,} DOGS\n\n"
                f"🏆 برنده: {user_name(get_user(winner_id))}\n"
                f"🎁 جایزه: {winner_reward:,} DOGS\n\n"
                f"❌ بازنده: {user_name(get_user(loser_id))}\n\n"
                f"👑 سهم مالک: {owner_fee:,} DOGS"
            ),
        )

    except Exception as e:

        logger.exception(
            "Could not edit game message: %s",
            e,
        )

    # پی وی برنده
    try:

        await context.bot.send_message(
            chat_id=winner_id,
            text=(
                "🏆 شما برنده بازی شدید!\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 مبلغ بازی: {bet:,} DOGS\n"
                f"🎁 جایزه شما: {winner_reward:,} DOGS"
            ),
        )

    except Exception:
        pass

    # پی وی بازنده
    try:

        await context.bot.send_message(
            chat_id=loser_id,
            text=(
                "❌ شما بازی را باختید.\n\n"
                f"🎮 بازی #{game_id}\n"
                f"💰 مبلغ بازی: {bet:,} DOGS"
            ),
        )

    except Exception:
        pass


async def cancel_game(query, context, game_id):

    if not owner(query.from_user.id):

        game = execute(
            """
            SELECT *
            FROM games
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

        if game["creator_id"] != query.from_user.id:

            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند لغو کند.",
                show_alert=True,
            )

            return

    else:

        game = execute(
            """
            SELECT *
            FROM games
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
            "❌ بازی قبلاً شروع یا لغو شده.",
            show_alert=True,
        )

        return

    cur = db.cursor()

    cur.execute(
        """
        UPDATE games
        SET status='cancelled'
        WHERE id=? AND status='waiting'
        """,
        (game_id,),
    )

    if cur.rowcount != 1:

        db.commit()

        await query.answer(
            "❌ این بازی قبلاً بررسی شده.",
            show_alert=True,
        )

        return

    db.commit()

    # برگشت مبلغ سازنده
    execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE id=?
        """,
        (
            game["bet"],
            game["creator_id"],
        ),
    )

    execute(
        """
        DELETE FROM game_players
        WHERE game_id=?
        """,
        (game_id,),
    )

    await query.answer(
        "✅ بازی لغو شد."
    )

    try:

        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {game['bet']:,} DOGS "
            "به سازنده برگشت."
        )

    except Exception:
        pass


# =========================================================
# ADMIN CALLBACKS
# =========================================================

async def callback_handler(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    data = query.data
    user_id = query.from_user.id

    # -------------------------------
    # GAME
    # -------------------------------

    if data.startswith("game_join:"):

        game_id = int(data.split(":")[1])

        await join_game(
            query,
            context,
            game_id,
        )

        return

    if data.startswith("game_cancel:"):

        game_id = int(data.split(":")[1])

        await cancel_game(
            query,
            context,
            game_id,
        )

        return

    # -------------------------------
    # DEPOSIT
    # -------------------------------

    if data.startswith("deposit_"):

        if not owner(user_id):

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
                "❌ دکمه نامعتبر.",
                show_alert=True,
            )

            return

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
                "❌ درخواست پیدا نشد.",
                show_alert=True,
            )

            return

        # ضد دوباره‌کاری
        if deposit["status"] != "pending":

            await query.answer(
                "⚠️ این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )

            return

        if action == "deposit_approve":

            cur = db.cursor()

            cur.execute(
                """
                UPDATE deposits
                SET status='approved'
                WHERE id=? AND status='pending'
                """,
                (deposit_id,),
            )

            if cur.rowcount != 1:

                db.commit()

                await query.answer(
                    "⚠️ قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            db.commit()

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
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    deposit["user_id"],
                    "deposit",
                    deposit["amount"],
                    f"Deposit #{deposit_id}",
                    datetime.now().isoformat(),
                ),
            )

            await query.answer(
                "✅ واریزی تأیید شد."
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
                        f"💰 مبلغ: "
                        f"{deposit['amount']:,} DOGS"
                    ),
                )

            except Exception:
                pass

        elif action == "deposit_reject":

            cur = db.cursor()

            cur.execute(
                """
                UPDATE deposits
                SET status='rejected'
                WHERE id=? AND status='pending'
                """,
                (deposit_id,),
            )

            if cur.rowcount != 1:

                db.commit()

                await query.answer(
                    "⚠️ قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            db.commit()

            await query.answer(
                "❌ واریزی رد شد."
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
                        f"💰 مبلغ: "
                        f"{deposit['amount']:,} DOGS"
                    ),
                )

            except Exception:
                pass

        return

    # -------------------------------
    # WITHDRAW
    # -------------------------------

    if data.startswith("withdraw_"):

        if not owner(user_id):

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True,
            )

            return

        try:

            action, id_text = data.split(":")

            withdrawal_id = int(id_text)

        except Exception:

            await query.answer(
                "❌ دکمه نامعتبر.",
                show_alert=True,
            )

            return

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
                "❌ درخواست پیدا نشد.",
                show_alert=True,
            )

            return

        if withdrawal["status"] != "pending":

            await query.answer(
                "⚠️ این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )

            return

        if action == "withdraw_approve":

            cur = db.cursor()

            cur.execute(
                """
                UPDATE withdrawals
                SET status='approved'
                WHERE id=? AND status='pending'
                """,
                (withdrawal_id,),
            )

            if cur.rowcount != 1:

                db.commit()

                await query.answer(
                    "⚠️ قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            db.commit()

            await query.answer(
                "✅ برداشت تأیید شد."
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
                        f"💰 مبلغ: "
                        f"{withdrawal['amount']:,} DOGS\n"
                        f"📍 مقصد: "
                        f"{withdrawal['destination']}"
                    ),
                )

            except Exception:
                pass

        elif action == "withdraw_reject":

            cur = db.cursor()

            cur.execute(
                """
                UPDATE withdrawals
                SET status='rejected'
                WHERE id=? AND status='pending'
                """,
                (withdrawal_id,),
            )

            if cur.rowcount != 1:

                db.commit()

                await query.answer(
                    "⚠️ قبلاً بررسی شده.",
                    show_alert=True,
                )

                return

            db.commit()

            # برگشت موجودی فقط یک بار
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
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    withdrawal["user_id"],
                    "withdraw_refund",
                    withdrawal["amount"],
                    f"Withdraw rejected #{withdrawal_id}",
                    datetime.now().isoformat(),
                ),
            )

            await query.answer(
                "❌ برداشت رد شد و موجودی برگشت."
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
                        f"💰 مبلغ "
                        f"{withdrawal['amount']:,} DOGS "
                        "به موجودی شما برگشت."
                    ),
                )

            except Exception:
                pass

        return

    # -------------------------------
    # ADMIN
    # -------------------------------

    if not owner(user_id):

        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True,
        )

        return

    if data == "admin_toggle_bot":

        new_status = not bot_enabled()

        set_bot_enabled(new_status)

        status_text = (
            "🟢 روشن"
            if new_status
            else "🔴 خاموش"
        )

        await query.answer(
            f"وضعیت: {status_text}"
        )

        try:

            await query.edit_message_reply_markup(
                reply_markup=admin_keyboard()
            )

        except Exception:
            pass

        try:

            await query.message.reply_text(
                f"✅ وضعیت ربات تغییر کرد:\n\n"
                f"{status_text}"
            )

        except Exception:
            pass

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
                "هیچ کاربری وجود ندارد."
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

        text = "💰 آخرین واریزی‌ها\n\n"

        for d in rows:

            text += (
                f"#{d['id']} | "
                f"{d['amount']:,} DOGS | "
                f"{d['status']} | "
                f"ID: {d['user_id']}\n"
            )

        await query.message.reply_text(
            text or "واریزی‌ای وجود ندارد."
        )

        return

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

        text = "💸 آخرین برداشت‌ها\n\n"

        for w in rows:

            text += (
                f"#{w['id']} | "
                f"{w['amount']:,} DOGS | "
                f"{w['status']} | "
                f"ID: {w['user_id']}\n"
            )

        await query.message.reply_text(
            text or "برداشتی وجود ندارد."
        )

        return

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
            f"💰 مجموع موجودی: "
            f"{total_balance:,} DOGS\n"
            f"👥 رفرال‌ها: {referrals_count}\n"
            f"🎮 بازی‌های انجام‌شده: {games}\n"
            f"🎁 جایزه رفرال: "
            f"{get_referral_reward():,} DOGS\n"
            f"👑 سهم بازی مالک: "
            f"{GAME_OWNER_FEE:,} DOGS\n"
            f"🤖 وضعیت: "
            f"{'🟢 روشن' if bot_enabled() else '🔴 خاموش'}"
        )

        return

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

    if data == "admin_transfer_owner":

        context.user_data.clear()
        context.user_data["state"] = (
            "admin_transfer_owner"
        )

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را وارد کنید:"
        )

        return

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

    if data == "admin_block":

        context.user_data.clear()
        context.user_data["state"] = (
            "admin_block"
        )

        await query.message.reply_text(
            "🚫 آیدی کاربر را وارد کنید:"
        )

        return

    if data == "admin_broadcast":

        context.user_data.clear()
        context.user_data["state"] = (
            "admin_broadcast"
        )

        await query.message.reply_text(
            "📢 پیام همگانی را ارسال کنید:"
        )

        return

    if data == "admin_support":

        rows = execute(
            """
            SELECT *
            FROM support_messages
            ORDER BY id DESC
            LIMIT 20
            """,
            fetchall=True,
        )

        if not rows:

            await query.message.reply_text(
                "🎧 پیام پشتیبانی وجود ندارد."
            )

            return

        text = "🎧 پیام‌های پشتیبانی\n\n"

        for s in rows:

            text += (
                f"#{s['id']} | "
                f"ID: {s['user_id']} | "
                f"{s['status']}\n"
            )

        await query.message.reply_text(
            text
        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_state_handler(update, context):

    user = get_user(update.effective_user.id)

    if not user:
        return False

    if not owner(user["id"]):
        return False

    state = context.user_data.get("state")

    if not state:
        return False

    if not update.message.text:
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
                "❌ مقدار نامعتبر."
            )

            return True

        set_referral_reward(amount)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 {amount:,} DOGS",
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
                "❌ این کاربر هنوز ربات را /start نکرده."
            )

            return True

        old_owner = get_owner_id()

        set_owner_id(new_owner)

        context.user_data.clear()

        await update.message.reply_text(
            "👑 مالکیت منتقل شد.\n\n"
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

        if (
            not parts[0].isdigit()
            or not parts[1].isdigit()
        ):

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

            tx_amount = amount
            tx_type = "admin_add"

            msg = (
                f"✅ {amount:,} DOGS "
                f"به {target_id} اضافه شد."
            )

        else:

            cur = db.cursor()

            cur.execute(
                """
                UPDATE users
                SET balance=balance-?
                WHERE id=? AND balance>=?
                """,
                (
                    amount,
                    target_id,
                    amount,
                ),
            )

            if cur.rowcount != 1:

                db.commit()

                await update.message.reply_text(
                    "❌ موجودی کاربر کافی نیست."
                )

                return True

            db.commit()

            tx_amount = -amount
            tx_type = "admin_remove"

            msg = (
                f"✅ {amount:,} DOGS "
                f"از {target_id} کم شد."
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
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                target_id,
                tx_type,
                tx_amount,
                "Admin balance change",
                datetime.now().isoformat(),
            ),
        )

        context.user_data.clear()

        await update.message.reply_text(
            msg,
            reply_markup=main_keyboard(user["id"]),
        )

        try:

            await context.bot.send_message(
                chat_id=target_id,
                text=msg,
            )

        except Exception:
            pass

        return True

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
            "📢 پیام همگانی ارسال شد.\n\n"
            f"👥 موفق: {sent}",
            reply_markup=main_keyboard(user["id"]),
        )

        return True

    return False


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
        reply_markup=main_keyboard(user["id"]),
    )


# =========================================================
# GROUP GAME COMMAND
# =========================================================

async def game_command(update, context):

    if not update.effective_chat:
        return

    # بازی فقط گروه
    if update.effective_chat.type not in (
        "group",
        "supergroup",
    ):

        await update.message.reply_text(
            "🎮 بازی را باید داخل گروه اجرا کنید."
        )

        return

    if not await check_user_access(update):
        return

    if not await check_bot_enabled(update):
        return

    if not context.args:

        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500"
        )

        return

    value = context.args[0].replace(",", "")

    if not value.isdigit():

        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد.\n\n"
            "مثال:\n"
            "بازی 500"
        )

        return

    amount = int(value)

    await create_game(
        update,
        context,
        amount,
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    # اول پاسخ مالک به پشتیبانی
    if await owner_reply_handler(
        update,
        context,
    ):
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

    # بازی در گروه
    text = update.message.text.strip()

    if re.fullmatch(
        r"بازی\s+[0-9,]+",
        text,
    ):

        parts = text.split()

        fake_args = parts[1]

        context.args = [
            fake_args
        ]

        await game_command(
            update,
            context,
        )

        context.args = []

        return

    # admin states
    if await admin_state_handler(
        update,
        context,
    ):
        return

    state = context.user_data.get("state")

    if state == "deposit_amount":

        if not await check_bot_enabled(update):
            return

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

        if not await check_bot_enabled(update):
            return

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

    if state == "transfer_destination":

        await transfer_destination(
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

    # Main buttons
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

    if text == "📱 تأیید شماره":

        await phone_start(
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

    # انتقال سریع
    if text.startswith("انتقال "):

        parts = text.split()

        if (
            len(parts) == 2
            and update.message.reply_to_message
            and parts[1].isdigit()
        ):

            receiver = get_user(
                update.message.reply_to_message
                .from_user.id
            )

            if receiver:

                await complete_transfer(
                    update,
                    context,
                    receiver["id"],
                    int(parts[1]),
                )

                return

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
            "❌ فرمت:\n\n"
            "انتقال @username 5000\n"
            "یا\n"
            "انتقال 123456789 5000\n\n"
            "یا Reply:\n"
            "انتقال 5000"
        )


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(update, context):

    user = create_or_update_user(
        update.effective_user
    )

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

    # پشتیبانی مستقیم با عکس بدون state
    await update.message.reply_text(
        "❌ ابتدا از منوی 🎧 پشتیبانی استفاده کنید."
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

    # start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # بازی /game 500
    application.add_handler(
        CommandHandler(
            "game",
            game_command,
        )
    )

    # callbacks
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # contact
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

    # متن
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    logger.info(
        "BOT STARTED | enabled=%s | owner=%s",
        bot_enabled(),
        get_owner_id(),
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
