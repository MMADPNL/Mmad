import json
import os
import random
import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"
ULTRA_USERNAME = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

GAME_GROUP = "https://t.me/TAK_B_ET"

MIN_WITHDRAW = 10000
MIN_DEPOSIT = 5000
REF_REWARD = 50

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "bot_data.json"

# قفل ضد اجرای همزمان بازی
GAME_LOCKS = {}


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "users": {},
    "pending_deposits": {},
    "pending_withdrawals": {},
    "games": {},
    "settings": {
        "bot_enabled": True,
        "force_channel": "",
        "force_group": "",
    },
    "owner_id": OWNER_ID,
}


# =========================================================
# DATABASE
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            loaded = {}

    except Exception:
        loaded = {}

    loaded.setdefault("users", {})
    loaded.setdefault("pending_deposits", {})
    loaded.setdefault("pending_withdrawals", {})
    loaded.setdefault("games", {})
    loaded.setdefault("settings", {})

    loaded["settings"].setdefault("bot_enabled", True)
    loaded["settings"].setdefault("force_channel", "")
    loaded["settings"].setdefault("force_group", "")
    loaded.setdefault("owner_id", OWNER_ID)

    return loaded


def save_data(data):
    temp = DATA_FILE + ".tmp"

    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp, DATA_FILE)

    except Exception as e:
        print("ERROR SAVING DATA:", e)

        try:
            if os.path.exists(temp):
                os.remove(temp)
        except Exception:
            pass


data = load_data()


# =========================================================
# USER SYSTEM
# =========================================================

def get_owner_id():
    try:
        return int(data.get("owner_id", OWNER_ID))
    except Exception:
        return OWNER_ID


def is_owner(user_id):
    try:
        return int(user_id) == get_owner_id()
    except Exception:
        return False


def ensure_user(user):
    uid = str(user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "username": user.username or "",
            "name": user.first_name or "",
            "balance": 0,
            "referrals": [],
            "referred_by": None,
            "created_at": datetime.now().isoformat(),
        }

        save_data(data)

    else:
        u = data["users"][uid]

        u.setdefault("balance", 0)
        u.setdefault("referrals", [])
        u.setdefault("referred_by", None)
        u.setdefault(
            "created_at",
            datetime.now().isoformat()
        )

        u["id"] = user.id
        u["username"] = user.username or u.get("username", "")
        u["name"] = user.first_name or u.get("name", "")

        save_data(data)

    return data["users"][uid]


def get_user(user_id):
    return data["users"].get(str(user_id))


def get_balance(user_id):
    user = get_user(user_id)

    if not user:
        return 0

    try:
        return int(user.get("balance", 0))
    except Exception:
        return 0


def set_balance(user_id, amount):
    uid = str(user_id)

    if uid not in data["users"]:
        return False

    try:
        amount = int(amount)
    except Exception:
        return False

    data["users"][uid]["balance"] = max(0, amount)
    save_data(data)

    return True


def add_balance(user_id, amount):
    try:
        amount = int(amount)
    except Exception:
        return False

    return set_balance(
        user_id,
        get_balance(user_id) + amount
    )


def remove_balance(user_id, amount):
    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        return False

    current = get_balance(user_id)

    if current < amount:
        return False

    return set_balance(
        user_id,
        current - amount
    )


# =========================================================
# BOT STATUS
# =========================================================

def bot_enabled():
    return bool(
        data["settings"].get(
            "bot_enabled",
            True
        )
    )


# =========================================================
# FORCE JOIN
# =========================================================

async def check_membership(user_id, context):
    channel = data["settings"].get("force_channel", "")
    group = data["settings"].get("force_group", "")

    checks = []

    if channel:
        checks.append(channel)

    if group:
        checks.append(group)

    if not checks:
        return True

    for chat in checks:
        try:
            member = await context.bot.get_chat_member(
                chat_id=chat,
                user_id=user_id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception:
            return False

    return True


async def force_join_message(update, context):
    channel = data["settings"].get("force_channel", "")
    group = data["settings"].get("force_group", "")

    buttons = []

    if channel:
        url = (
            channel
            if channel.startswith("http")
            else f"https://t.me/{channel.replace('@', '')}"
        )

        buttons.append([
            InlineKeyboardButton(
                "📢 عضویت در کانال",
                url=url
            )
        ])

    if group:
        url = (
            group
            if group.startswith("http")
            else f"https://t.me/{group.replace('@', '')}"
        )

        buttons.append([
            InlineKeyboardButton(
                "👥 عضویت در گپ",
                url=url
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_join"
        )
    ])

    text = (
        "⚠️ برای استفاده از ربات ابتدا عضو شوید.\n\n"
        "بعد از عضویت روی «بررسی عضویت» بزنید."
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard(user_id=None):
    rows = [
        [
            InlineKeyboardButton(
                "💰 برداشت",
                callback_data="withdraw"
            ),
            InlineKeyboardButton(
                "💳 واریز",
                callback_data="deposit"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 زیر مجموعه",
                callback_data="referral"
            ),
            InlineKeyboardButton(
                "👤 پروفایل",
                callback_data="profile"
            )
        ],
        [
            InlineKeyboardButton(
                "🎧 پشتیبانی",
                callback_data="support"
            )
        ]
    ]

    if user_id is not None and is_owner(user_id):
        rows.append([
            InlineKeyboardButton(
                "⚙️ پنل مدیریت",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(rows)


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    ensure_user(user)

    if not await check_membership(user.id, context):
        await force_join_message(update, context)
        return

    if context.args:
        try:
            ref_id = int(context.args[0])

            current = get_user(user.id)

            if (
                ref_id != user.id
                and get_user(ref_id)
                and current.get("referred_by") is None
            ):
                data["users"][str(user.id)]["referred_by"] = ref_id

                if user.id not in data["users"][str(ref_id)]["referrals"]:
                    data["users"][str(ref_id)]["referrals"].append(user.id)

                add_balance(ref_id, REF_REWARD)

                save_data(data)

                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            "🎉 زیرمجموعه جدید!\n\n"
                            f"👤 کاربر: {user.first_name}\n"
                            f"🎁 پاداش: {REF_REWARD} DOGS"
                        )
                    )
                except Exception:
                    pass

        except Exception:
            pass

    await update.message.reply_text(
        "🤖 به ربات خوش آمدید.\n\n"
        f"💰 موجودی شما: "
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# PROFILE
# =========================================================

async def show_profile(query):
    user_id = query.from_user.id
    user = get_user(user_id)

    if not user:
        await query.answer(
            "❌ کاربر پیدا نشد.",
            show_alert=True
        )
        return

    username = user.get("username", "")
    username_text = f"@{username}" if username else "ندارد"

    referrals = len(
        user.get("referrals", [])
    )

    text = (
        "👤 پروفایل شما\n\n"
        f"📝 نام: {user.get('name', '')}\n"
        f"🆔 آیدی: {user_id}\n"
        f"🔗 یوزرنیم: {username_text}\n\n"
        f"💰 موجودی: {get_balance(user_id):,} DOGS\n"
        f"👥 تعداد زیرمجموعه: {referrals}\n"
        f"🎁 پاداش هر زیرمجموعه: {REF_REWARD} DOGS"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# REFERRAL
# =========================================================

async def show_referral(query, context):
    user_id = query.from_user.id
    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={user_id}"

    user = get_user(user_id)

    count = len(
        user.get("referrals", [])
    ) if user else 0

    text = (
        "👥 سیستم زیرمجموعه‌گیری\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{link}\n\n"
        f"👤 تعداد زیرمجموعه: {count}\n"
        f"🎁 پاداش هر زیرمجموعه: {REF_REWARD} DOGS"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="home"
                )
            ]
        ])
    )


# =========================================================
# DEPOSIT
# =========================================================

async def show_deposit(query):
    await query.edit_message_text(
        "💳 روش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🟢 اولترا",
                    callback_data="deposit_ultra"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔵 صراف",
                    callback_data="deposit_exchange"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="home"
                )
            ]
        ])
    )


async def deposit_ultra(query, context):
    context.user_data["state"] = "deposit_ultra"

    await query.edit_message_text(
        "🟢 واریز از طریق اولترا\n\n"
        f"👤 آیدی واریز: {ULTRA_USERNAME}\n\n"
        "به این آیدی واریز کنید.\n"
        "سپس شات یا پیامک واریز را همینجا ارسال کنید.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS"
    )


async def deposit_exchange(query, context):
    context.user_data["state"] = "deposit_exchange"

    await query.edit_message_text(
        "🔵 واریز از طریق صراف\n\n"
        f"آدرس کیف پول DOGS:\n\n{DOGS_WALLET}\n\n"
        "سپس لینک تراکنش یا شات را همینجا ارسال کنید.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS"
    )


# =========================================================
# WITHDRAW
# =========================================================

async def show_withdraw(query, context):
    context.user_data["state"] = "withdraw_amount"

    await query.edit_message_text(
        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "تعداد DOGS موردنظر را وارد کنید:"
    )


# =========================================================
# SUPPORT
# =========================================================

async def show_support(query, context):
    context.user_data["state"] = "support"

    await query.edit_message_text(
        "🎧 پشتیبانی\n\n"
        f"👤 پشتیبانی: {SUPPORT_USERNAME}\n\n"
        "پیام خود را همینجا ارسال کنید."
    )


# =========================================================
# ADMIN
# =========================================================

def admin_keyboard():
    status = (
        "🔴 خاموش کردن ربات"
        if bot_enabled()
        else "🟢 روشن کردن ربات"
    )

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 شارژ موجودی",
                callback_data="admin_charge"
            )
        ],
        [
            InlineKeyboardButton(
                status,
                callback_data="admin_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 کانال اجباری",
                callback_data="admin_channel"
            ),
            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="admin_group"
            )
        ],
        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_owner"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ]
    ])


async def show_admin(query, context):
    if not is_owner(query.from_user.id):
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    status = "🟢 روشن" if bot_enabled() else "🔴 خاموش"

    await query.edit_message_text(
        "⚙️ پنل مدیریت\n\n"
        f"وضعیت: {status}\n"
        f"👑 مالک: {get_owner_id()}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# GAME HELPERS
# =========================================================

def create_game_id():
    while True:
        game_id = str(
            random.randint(
                10000000,
                99999999
            )
        )

        if game_id not in data["games"]:
            return game_id


def get_game_lock(game_id):
    if game_id not in GAME_LOCKS:
        GAME_LOCKS[game_id] = asyncio.Lock()

    return GAME_LOCKS[game_id]


def game_keyboard(game_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=f"join_game:{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو بازی",
                callback_data=f"cancel_game:{game_id}"
            )
        ]
    ])


# =========================================================
# GROUP GAME
# =========================================================

async def handle_group_message(update, context):
    user = update.effective_user

    text = (
        update.message.text
        or ""
    ).strip()

    if not text:
        return

    text_lower = text.lower()

    if not text_lower.startswith("بازی"):
        return

    ensure_user(user)

    parts = text_lower.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount < MIN_GAME:
        await update.message.reply_text(
            f"❌ حداقل بازی {MIN_GAME:,} DOGS است."
        )
        return

    if amount > MAX_GAME:
        await update.message.reply_text(
            f"❌ حداکثر بازی {MAX_GAME:,} DOGS است."
        )
        return

    if get_balance(user.id) < amount:
        await update.message.reply_text(
            "❌ موجودی شما کافی نیست.\n\n"
            f"💰 موجودی: {get_balance(user.id):,} DOGS"
        )
        return

    if not remove_balance(user.id, amount):
        await update.message.reply_text(
            "❌ کسر موجودی انجام نشد."
        )
        return

    game_id = create_game_id()

    data["games"][game_id] = {
        "id": game_id,
        "creator": user.id,
        "creator_name": user.first_name or "",
        "creator_username": user.username or "",
        "amount": amount,
        "joined": None,
        "joined_name": "",
        "status": "waiting",
        "group_id": update.effective_chat.id,
        "message_id": None,
        "winner": None,
        "paid": False,
        "created_at": datetime.now().isoformat()
    }

    save_data(data)

    try:
        msg = await update.message.reply_text(
            "🎮 بازی جدید!\n\n"
            f"👤 سازنده: {user.first_name}\n"
            f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
            "یک نفر دیگر روی «🎮 بازی با دوستان» بزند.\n\n"
            "سازنده می‌تواند قبل از ورود نفر دوم "
            "بازی را لغو کند.",
            reply_markup=game_keyboard(game_id)
        )

        data["games"][game_id]["message_id"] = msg.message_id
        save_data(data)

    except Exception:
        # اگر ارسال پیام بازی شکست خورد، پول سازنده برگردد
        data["games"].pop(game_id, None)
        add_balance(user.id, amount)

        await update.message.reply_text(
            "❌ ساخت بازی انجام نشد و مبلغ به موجودی شما برگشت."
        )


# =========================================================
# JOIN GAME
# =========================================================

async def join_game(query, context, game_id):
    user = query.from_user

    ensure_user(user)

    lock = get_game_lock(game_id)

    async with lock:

        game = data["games"].get(game_id)

        # ضدباگ بازی حذف شده
        if not game:
            await query.answer(
                "❌ این بازی دیگر وجود ندارد.",
                show_alert=True
            )
            return

        # ضدباگ بازی تمام شده
        if game.get("status") != "waiting":
            await query.answer(
                "❌ این بازی قبلاً تکمیل یا لغو شده.",
                show_alert=True
            )
            return

        # جلوگیری از ورود سازنده
        if user.id == game.get("creator"):
            await query.answer(
                "❌ شما سازنده این بازی هستید.",
                show_alert=True
            )
            return

        # جلوگیری از خراب شدن بازی
        if game.get("joined") is not None:
            await query.answer(
                "❌ یک نفر قبلاً وارد این بازی شده.",
                show_alert=True
            )
            return

        amount = int(game.get("amount", 0))

        if amount <= 0:
            game["status"] = "cancelled"
            save_data(data)

            await query.answer(
                "❌ مبلغ بازی نامعتبر است.",
                show_alert=True
            )
            return

        # بررسی موجودی نفر دوم
        if get_balance(user.id) < amount:
            await query.answer(
                "❌ موجودی شما کافی نیست.",
                show_alert=True
            )
            return

        # کسر مبلغ نفر دوم
        if not remove_balance(user.id, amount):
            await query.answer(
                "❌ کسر موجودی انجام نشد.",
                show_alert=True
            )
            return

        # ثبت ورود
        game["joined"] = user.id
        game["joined_name"] = user.first_name or ""
        game["status"] = "playing"

        save_data(data)

        await query.answer(
            "🎮 وارد بازی شدید!"
        )

        # انتخاب برنده
        players = [
            game["creator"],
            user.id
        ]

        winner = random.choice(players)

        loser = (
            user.id
            if winner == game["creator"]
            else game["creator"]
        )

        prize = amount * 2

        # ضد پرداخت دوباره
        if not game.get("paid", False):

            add_balance(
                winner,
                prize
            )

            game["winner"] = winner
            game["loser"] = loser
            game["paid"] = True
            game["status"] = "finished"

            save_data(data)

        winner_name = (
            game["creator_name"]
            if winner == game["creator"]
            else user.first_name
        )

        loser_name = (
            user.first_name
            if loser == user.id
            else game["creator_name"]
        )

        result_text = (
            "🎮 بازی انجام شد!\n\n"
            f"👤 بازیکن اول: {game['creator_name']}\n"
            f"👤 بازیکن دوم: {user.first_name}\n\n"
            f"🏆 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"
            f"💰 جایزه برنده: {prize:,} DOGS"
        )

        try:
            await query.edit_message_text(
                result_text
            )
        except Exception:
            # اگر پیام قبلاً ویرایش شده، خطا نده
            try:
                await context.bot.send_message(
                    chat_id=game["group_id"],
                    text=result_text
                )
            except Exception:
                pass

        # پاک کردن lock بعداً
        GAME_LOCKS.pop(game_id, None)


# =========================================================
# CANCEL GAME
# =========================================================

async def cancel_game(query, context, game_id):
    user = query.from_user

    ensure_user(user)

    lock = get_game_lock(game_id)

    async with lock:

        game = data["games"].get(game_id)

        if not game:
            await query.answer(
                "❌ این بازی وجود ندارد.",
                show_alert=True
            )
            return

        # فقط سازنده
        if user.id != game.get("creator"):
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند آن را لغو کند.",
                show_alert=True
            )
            return

        if game.get("status") != "waiting":
            await query.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True
            )
            return

        amount = int(
            game.get("amount", 0)
        )

        # برگرداندن پول
        add_balance(
            user.id,
            amount
        )

        game["status"] = "cancelled"
        game["cancelled_by"] = user.id
        game["cancelled_at"] = datetime.now().isoformat()

        save_data(data)

        await query.answer(
            "✅ بازی لغو شد و مبلغ برگشت خورد."
        )

        try:
            await query.edit_message_text(
                "❌ بازی لغو شد.\n\n"
                f"👤 سازنده: {game['creator_name']}\n"
                f"💰 مبلغ {amount:,} DOGS "
                "به موجودی سازنده برگشت."
            )
        except Exception:
            pass

        GAME_LOCKS.pop(game_id, None)


# =========================================================
# CALLBACK
# =========================================================

async def callback_handler(update, context):
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user = query.from_user
    ensure_user(user)

    action = query.data or ""

    # HOME
    if action == "home":
        context.user_data.clear()

        await query.edit_message_text(
            "🤖 منوی اصلی\n\n"
            f"💰 موجودی: {get_balance(user.id):,} DOGS",
            reply_markup=main_keyboard(user.id)
        )
        return

    # JOIN
    if action == "check_join":
        if await check_membership(user.id, context):
            await query.edit_message_text(
                "✅ عضویت تأیید شد.",
                reply_markup=main_keyboard(user.id)
            )
        else:
            await query.answer(
                "❌ هنوز عضو نشده‌اید.",
                show_alert=True
            )
        return

    # PROFILE
    if action == "profile":
        await show_profile(query)
        return

    # REFERRAL
    if action == "referral":
        await show_referral(query, context)
        return

    # DEPOSIT
    if action == "deposit":
        await show_deposit(query)
        return

    if action == "deposit_ultra":
        await deposit_ultra(query, context)
        return

    if action == "deposit_exchange":
        await deposit_exchange(query, context)
        return

    # WITHDRAW
    if action == "withdraw":
        await show_withdraw(query, context)
        return

    # SUPPORT
    if action == "support":
        await show_support(query, context)
        return

    # ADMIN
    if action == "admin":
        await show_admin(query, context)
        return

    # ADMIN CHARGE
    if action == "admin_charge":

        if not is_owner(user.id):
            await query.answer(
                "⛔ فقط مالک.",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_charge"

        await query.edit_message_text(
            "💰 شارژ موجودی کاربر\n\n"
            "آیدی عددی کاربر و مبلغ را در یک خط ارسال کنید.\n\n"
            "مثال:\n"
            "123456789 50000",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )
        return

    # ADMIN TOGGLE
    if action == "admin_toggle":

        if not is_owner(user.id):
            return

        data["settings"]["bot_enabled"] = not bot_enabled()
        save_data(data)

        await show_admin(query, context)
        return

    # ADMIN CHANNEL
    if action == "admin_channel":

        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_channel"

        await query.edit_message_text(
            "📢 کانال اجباری\n\n"
            "آیدی یا لینک کانال را ارسال کنید.\n\n"
            "برای خاموش کردن:\noff"
        )
        return

    # ADMIN GROUP
    if action == "admin_group":

        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_group"

        await query.edit_message_text(
            "👥 گپ اجباری\n\n"
            "آیدی یا لینک گپ را ارسال کنید.\n\n"
            "برای خاموش کردن:\noff"
        )
        return

    # ADMIN OWNER
    if action == "admin_owner":

        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_owner"

        await query.edit_message_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید."
        )
        return

    # ADMIN STATS
    if action == "admin_stats":

        if not is_owner(user.id):
            return

        total_users = len(data["users"])

        total_balance = sum(
            int(x.get("balance", 0))
            for x in data["users"].values()
        )

        await query.edit_message_text(
            "📊 آمار ربات\n\n"
            f"👤 کاربران: {total_users:,}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"⏳ واریز در انتظار: "
            f"{len(data['pending_deposits'])}\n"
            f"💸 برداشت در انتظار: "
            f"{len(data['pending_withdrawals'])}\n"
            f"🎮 بازی‌ها: {len(data['games'])}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin"
                    )
                ]
            ])
        )
        return

    # GAME JOIN
    if action.startswith("join_game:"):

        game_id = action.split(":", 1)[1]

        await join_game(
            query,
            context,
            game_id
        )

        return

    # GAME CANCEL
    if action.startswith("cancel_game:"):

        game_id = action.split(":", 1)[1]

        await cancel_game(
            query,
            context,
            game_id
        )

        return

    # APPROVE DEPOSIT
    if action.startswith("approve_deposit:"):

        if not is_owner(user.id):
            return

        did = action.split(":", 1)[1]

        dep = data["pending_deposits"].get(did)

        if not dep or dep["status"] != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["approve_deposit_id"] = did
        context.user_data["state"] = "deposit_amount"

        await query.message.reply_text(
            "💰 مقدار واریزی را وارد کنید:"
        )
        return

    # REJECT DEPOSIT
    if action.startswith("reject_deposit:"):

        if not is_owner(user.id):
            return

        did = action.split(":", 1)[1]

        dep = data["pending_deposits"].get(did)

        if not dep or dep["status"] != "pending":
            return

        dep["status"] = "rejected"

        save_data(data)

        try:
            await context.bot.send_message(
                chat_id=dep["user_id"],
                text="❌ واریز شما رد شد."
            )
        except Exception:
            pass

        try:
            await query.edit_message_text(
                "❌ درخواست واریز رد شد."
            )
        except Exception:
            pass

        return

    # APPROVE WITHDRAW
    if action.startswith("approve_withdraw:"):

        if not is_owner(user.id):
            return

        wid = action.split(":", 1)[1]

        wd = data["pending_withdrawals"].get(wid)

        if not wd or wd["status"] != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        wd["status"] = "approved"

        save_data(data)

        try:
            await context.bot.send_message(
                chat_id=wd["user_id"],
                text=(
                    "✅ برداشت شما تأیید شد.\n\n"
                    f"💰 مقدار: {wd['amount']:,} DOGS\n"
                    f"📥 مقصد: {wd['address']}"
                )
            )
        except Exception:
            pass

        await query.edit_message_text(
            "✅ برداشت تأیید شد."
        )
        return

    # REJECT WITHDRAW
    if action.startswith("reject_withdraw:"):

        if not is_owner(user.id):
            return

        wid = action.split(":", 1)[1]

        wd = data["pending_withdrawals"].get(wid)

        if not wd or wd["status"] != "pending":
            return

        wd["status"] = "rejected"

        add_balance(
            wd["user_id"],
            wd["amount"]
        )

        save_data(data)

        try:
            await context.bot.send_message(
                chat_id=wd["user_id"],
                text=(
                    "❌ برداشت شما رد شد.\n\n"
                    f"💰 مقدار {wd['amount']:,} DOGS "
                    "به موجودی شما برگشت."
                )
            )
        except Exception:
            pass

        await query.edit_message_text(
            "❌ برداشت رد شد و مبلغ برگشت داده شد."
        )
        return


# =========================================================
# ADMIN STATES
# =========================================================

async def handle_admin_states(update, context):
    user = update.effective_user
    state = context.user_data.get("state")

    if not is_owner(user.id):
        return False

    # CHARGE
    if state == "admin_charge":

        parts = (
            update.message.text
            or ""
        ).strip().split()

        if len(parts) != 2:
            await update.message.reply_text(
                "❌ فرمت اشتباه.\n\n"
                "مثال:\n"
                "123456789 50000"
            )
            return True

        try:
            target_id = int(parts[0])
            amount = int(
                parts[1].replace(",", "")
            )
        except Exception:
            await update.message.reply_text(
                "❌ آیدی و مبلغ باید عدد باشند."
            )
            return True

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ باید بیشتر از صفر باشد."
            )
            return True

        if not get_user(target_id):
            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را استارت نکرده است."
            )
            return True

        old = get_balance(target_id)

        if not add_balance(target_id, amount):
            await update.message.reply_text(
                "❌ شارژ انجام نشد."
            )
            return True

        new = get_balance(target_id)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ موجودی با موفقیت شارژ شد.\n\n"
            f"🆔 کاربر: {target_id}\n"
            f"💰 شارژ: {amount:,} DOGS\n"
            f"💵 قبلی: {old:,} DOGS\n"
            f"💵 جدید: {new:,} DOGS"
        )

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "🎉 موجودی شما توسط مدیریت شارژ شد.\n\n"
                    f"💰 مبلغ: {amount:,} DOGS\n"
                    f"💵 موجودی جدید: {new:,} DOGS"
                )
            )
        except Exception:
            pass

        return True

    # DEPOSIT AMOUNT
    if state == "deposit_amount":

        try:
            amount = int(
                update.message.text
                .replace(",", "")
                .strip()
            )
        except Exception:
            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )
            return True

        did = context.user_data.get(
            "approve_deposit_id"
        )

        dep = data["pending_deposits"].get(did)

        if not dep or dep["status"] != "pending":
            context.user_data.clear()

            await update.message.reply_text(
                "❌ درخواست پیدا نشد."
            )
            return True

        if not add_balance(
            dep["user_id"],
            amount
        ):
            await update.message.reply_text(
                "❌ اضافه کردن موجودی انجام نشد."
            )
            return True

        dep["status"] = "approved"
        dep["amount"] = amount

        save_data(data)

        try:
            await context.bot.send_message(
                chat_id=dep["user_id"],
                text=(
                    "✅ واریز شما تأیید شد.\n\n"
                    f"💰 مبلغ: {amount:,} DOGS\n"
                    f"💵 موجودی جدید: "
                    f"{get_balance(dep['user_id']):,} DOGS"
                )
            )
        except Exception:
            pass

        context.user_data.clear()

        await update.message.reply_text(
            "✅ واریز تأیید شد."
        )

        return True

    # CHANNEL
    if state == "admin_channel":

        value = (
            update.message.text
            or ""
        ).strip()

        data["settings"]["force_channel"] = (
            ""
            if value.lower() == "off"
            else value
        )

        save_data(data)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ کانال اجباری ذخیره شد."
        )

        return True

    # GROUP
    if state == "admin_group":

        value = (
            update.message.text
            or ""
        ).strip()

        data["settings"]["force_group"] = (
            ""
            if value.lower() == "off"
            else value
        )

        save_data(data)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد."
        )

        return True

    # OWNER
    if state == "admin_owner":

        try:
            new_owner = int(
                update.message.text.strip()
            )
        except Exception:
            await update.message.reply_text(
                "❌ آیدی معتبر نیست."
            )
            return True

        if not get_user(new_owner):
            await update.message.reply_text(
                "⚠️ این کاربر هنوز ربات را استارت نکرده است."
            )
            return True

        old_owner = get_owner_id()

        data["owner_id"] = new_owner
        save_data(data)

        context.user_data.clear()

        await update.message.reply_text(
            "👑 مالکیت منتقل شد.\n\n"
            f"👤 مالک قبلی: {old_owner}\n"
            f"👑 مالک جدید: {new_owner}"
        )

        return True

    return False


# =========================================================
# UNIVERSAL MESSAGE
# =========================================================

async def universal_message(update, context):
    if not update.message:
        return

    # گروه
    if update.effective_chat.type in [
        "group",
        "supergroup"
    ]:
        await handle_group_message(
            update,
            context
        )
        return

    user = update.effective_user

    ensure_user(user)

    if (
        not bot_enabled()
        and not is_owner(user.id)
    ):
        await update.message.reply_text(
            "⛔ ربات در حال حاضر خاموش است."
        )
        return

    if not await check_membership(
        user.id,
        context
    ):
        await force_join_message(
            update,
            context
        )
        return

    # ADMIN
    if is_owner(user.id):

        handled = await handle_admin_states(
            update,
            context
        )

        if handled:
            return

    state = context.user_data.get("state")

    # WITHDRAW AMOUNT
    if state == "withdraw_amount":

        try:
            amount = int(
                update.message.text
                .replace(",", "")
                .strip()
            )
        except Exception:
            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )
            return

        if amount < MIN_WITHDRAW:
            await update.message.reply_text(
                f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
            )
            return

        if get_balance(user.id) < amount:
            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )
            return

        context.user_data["withdraw_amount"] = amount
        context.user_data["state"] = "withdraw_address"

        await update.message.reply_text(
            "📥 مقدار ثبت شد.\n\n"
            "آدرس کیف پول یا آیدی دریافت‌کننده را ارسال کنید:"
        )
        return

    # WITHDRAW ADDRESS
    if state == "withdraw_address":

        amount = context.user_data.get(
            "withdraw_amount"
        )

        address = (
            update.message.text
            or ""
        ).strip()

        if not amount:
            context.user_data.clear()
            return

        if not remove_balance(
            user.id,
            amount
        ):
            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )
            return

        wid = str(
            random.randint(
                10000000,
                99999999
            )
        )

        data["pending_withdrawals"][wid] = {
            "id": wid,
            "user_id": user.id,
            "username": user.username or "",
            "amount": amount,
            "address": address,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

        save_data(data)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ درخواست برداشت ثبت شد.\n\n"
            f"💰 مقدار: {amount:,} DOGS\n"
            f"📥 مقصد: {address}\n\n"
            "⏳ منتظر تأیید مالک باشید."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ تأیید برداشت",
                    callback_data=f"approve_withdraw:{wid}"
                ),
                InlineKeyboardButton(
                    "❌ رد برداشت",
                    callback_data=f"reject_withdraw:{wid}"
                )
            ]
        ])

        try:
            await context.bot.send_message(
                chat_id=get_owner_id(),
                text=(
                    "💰 درخواست برداشت جدید\n\n"
                    f"👤 کاربر: {user.first_name}\n"
                    f"🆔 آیدی: {user.id}\n"
                    f"💰 مقدار: {amount:,} DOGS\n"
                    f"📥 مقصد: {address}\n"
                    f"🆔 درخواست: {wid}"
                ),
                reply_markup=keyboard
            )
        except Exception:
            pass

        return

    # DEPOSIT
    if state in [
        "deposit_ultra",
        "deposit_exchange"
    ]:

        deposit_type = (
            "اولترا"
            if state == "deposit_ultra"
            else "صراف"
        )

        text = (
            update.message.text
            or ""
        )

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            content_type = "photo"
        else:
            file_id = text
            content_type = "text"

        did = str(
            random.randint(
                10000000,
                99999999
            )
        )

        data["pending_deposits"][did] = {
            "id": did,
            "user_id": user.id,
            "username": user.username or "",
            "type": deposit_type,
            "content": file_id,
            "content_type": content_type,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

        save_data(data)
        context.user_data.clear()

        await update.message.reply_text(
            "✅ درخواست واریز ثبت شد.\n\n"
            "⏳ منتظر تأیید مالک باشید."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"approve_deposit:{did}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"reject_deposit:{did}"
                )
            ]
        ])

        owner_text = (
            "💳 درخواست واریز جدید\n\n"
            f"👤 کاربر: {user.first_name}\n"
            f"🆔 آیدی: {user.id}\n"
            f"💳 روش: {deposit_type}\n"
            f"🆔 درخواست: {did}"
        )

        try:
            if content_type == "photo":
                await context.bot.send_photo(
                    chat_id=get_owner_id(),
                    photo=file_id,
                    caption=owner_text,
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_message(
                    chat_id=get_owner_id(),
                    text=owner_text + "\n\n📎 رسید:\n" + text,
                    reply_markup=keyboard
                )
        except Exception:
            pass

        return

    # SUPPORT
    if state == "support":

        message_text = (
            update.message.text
            or ""
        )

        try:
            await context.bot.send_message(
                chat_id=get_owner_id(),
                text=(
                    "🎧 پیام جدید پشتیبانی\n\n"
                    f"👤 کاربر: {user.first_name}\n"
                    f"🆔 آیدی: {user.id}\n\n"
                    f"💬 پیام:\n{message_text}"
                )
            )
        except Exception:
            pass

        context.user_data.clear()

        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد."
        )
        return

    await update.message.reply_text(
        "از دکمه‌های منوی ربات استفاده کنید.",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# PROFILE COMMAND
# =========================================================

async def cmd_profile(update, context):
    user = update.effective_user

    ensure_user(user)

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"📝 نام: {user.first_name}\n"
        f"🆔 آیدی: {user.id}\n"
        f"💰 موجودی: {get_balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه: "
        f"{len(get_user(user.id).get('referrals', []))}",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):
    print(
        "BOT ERROR:",
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد.")
        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "profile",
            cmd_profile
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            universal_message
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "🤖 Telegram Bot Started..."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
