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

# قفل بازی برای جلوگیری از دوبار کلیک
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
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        loaded = json.loads(json.dumps(DEFAULT_DATA))

    if not isinstance(loaded, dict):
        loaded = json.loads(json.dumps(DEFAULT_DATA))

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


data = load_data()


def save_data():
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print("SAVE ERROR:", e)

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass


# =========================================================
# USER SYSTEM
# =========================================================

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
        u["username"] = user.username or ""
        u["name"] = user.first_name or ""

    save_data()

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

    save_data()

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
# OWNER
# =========================================================

def get_owner_id():
    try:
        return int(
            data.get(
                "owner_id",
                OWNER_ID
            )
        )
    except Exception:
        return OWNER_ID


def is_owner(user_id):
    try:
        return int(user_id) == get_owner_id()
    except Exception:
        return False


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
    channel = data["settings"].get(
        "force_channel",
        ""
    )

    group = data["settings"].get(
        "force_group",
        ""
    )

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

            if member.status in (
                "left",
                "kicked"
            ):
                return False

        except Exception:
            return False

    return True


async def send_force_join(update, context):
    channel = data["settings"].get(
        "force_channel",
        ""
    )

    group = data["settings"].get(
        "force_group",
        ""
    )

    buttons = []

    if channel:
        url = (
            channel
            if channel.startswith("http")
            else "https://t.me/" + channel.replace("@", "")
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
            else "https://t.me/" + group.replace("@", "")
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
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard(user_id):
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
                "👥 زیرمجموعه",
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

    if is_owner(user_id):
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

    # زیرمجموعه
    if context.args:
        try:
            ref_id = int(context.args[0])

            current_user = get_user(user.id)
            ref_user = get_user(ref_id)

            if (
                ref_id != user.id
                and ref_user
                and current_user.get("referred_by") is None
            ):
                data["users"][str(user.id)]["referred_by"] = ref_id

                if user.id not in ref_user["referrals"]:
                    ref_user["referrals"].append(user.id)

                    add_balance(
                        ref_id,
                        REF_REWARD
                    )

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

                save_data(data)

        except Exception:
            pass

    if not await check_membership(
        user.id,
        context
    ):
        await send_force_join(
            update,
            context
        )
        return

    if (
        not bot_enabled()
        and not is_owner(user.id)
    ):
        await update.message.reply_text(
            "⛔ ربات در حال حاضر خاموش است."
        )
        return

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
    uid = query.from_user.id
    user = get_user(uid)

    if not user:
        await query.answer(
            "❌ کاربر پیدا نشد.",
            show_alert=True
        )
        return

    username = user.get(
        "username",
        ""
    )

    username_text = (
        "@" + username
        if username
        else "ندارد"
    )

    referrals = len(
        user.get(
            "referrals",
            []
        )
    )

    text = (
        "👤 پروفایل شما\n\n"
        f"📝 نام: {user.get('name', '')}\n"
        f"🆔 آیدی: {uid}\n"
        f"🔗 یوزرنیم: {username_text}\n\n"
        f"💰 موجودی: "
        f"{get_balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه: {referrals}\n"
        f"🎁 پاداش هر نفر: {REF_REWARD} DOGS"
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
    uid = query.from_user.id

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}?start={uid}"
    )

    user = get_user(uid)

    count = len(
        user.get("referrals", [])
    ) if user else 0

    text = (
        "👥 زیرمجموعه‌گیری\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{link}\n\n"
        f"👤 تعداد زیرمجموعه: {count}\n"
        f"🎁 هر زیرمجموعه: {REF_REWARD} DOGS\n\n"
        "با ارسال لینک به دوستانتان، "
        "به‌صورت خودکار پاداش دریافت می‌کنید."
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
                    "🔵 صرافی",
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
    context.user_data.clear()
    context.user_data["state"] = "deposit_ultra"

    await query.edit_message_text(
        "🟢 واریز اولترا\n\n"
        f"👤 آیدی: {ULTRA_USERNAME}\n\n"
        "به این آیدی DOGS را بزنید.\n"
        "سپس شات خود یا پیام تراکنش را همینجا ارسال کنید.\n\n"
        "⏳ رسید توسط مالک بررسی و تأیید یا رد می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="deposit"
                )
            ]
        ])
    )


async def deposit_exchange(query, context):
    context.user_data.clear()
    context.user_data["state"] = "deposit_exchange"

    await query.edit_message_text(
        "🔵 واریز صرافی\n\n"
        f"{DOGS_WALLET}\n\n"
        "به این ولت DOGS را بزنید.\n"
        "سپس شات خود یا لینک تراکنش را همینجا ارسال کنید.\n\n"
        "⏳ رسید توسط مالک بررسی و تأیید یا رد می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="deposit"
                )
            ]
        ])
    )


# =========================================================
# WITHDRAW
# =========================================================

async def show_withdraw(query, context):
    context.user_data.clear()
    context.user_data["state"] = "withdraw_amount"

    await query.edit_message_text(
        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "تعداد DOGS را وارد کنید:"
    )


# =========================================================
# SUPPORT
# =========================================================

async def show_support(query, context):
    context.user_data.clear()
    context.user_data["state"] = "support"

    await query.edit_message_text(
        "🎧 پشتیبانی\n\n"
        f"👤 پشتیبانی: {SUPPORT_USERNAME}\n\n"
        "پیام خود را همینجا ارسال کنید.",
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
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    status_text = (
        "🔴 خاموش کردن ربات"
        if bot_enabled()
        else "🟢 روشن کردن ربات"
    )

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                status_text,
                callback_data="admin_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="admin_group"
            ),
            InlineKeyboardButton(
                "📢 چنل اجباری",
                callback_data="admin_channel"
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
                "👑 انتقال مالکیت",
                callback_data="admin_owner"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="home"
            )
        ]
    ])


async def show_admin(query):
    if not is_owner(query.from_user.id):
        await query.answer(
            "دسترسی ندارید",
            show_alert=True
        )
        return

    status = (
        "🟢 روشن"
        if bot_enabled()
        else "🔴 خاموش"
    )

    await query.edit_message_text(
        "⚙️ پنل مدیریت\n\n"
        f"🤖 وضعیت ربات: {status}\n"
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
                "❌ لغو",
                callback_data=f"cancel_game:{game_id}"
            )
        ]
    ])


def game_creator_keyboard(game_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید ورود",
                callback_data=f"approve_join:{game_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_join:{game_id}"
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

async def handle_group_game(update, context):
    if not update.message:
        return

    user = update.effective_user
    ensure_user(user)

    text = (
        update.message.text or ""
    ).strip()

    if not text:
        return

    parts = text.split()

    if len(parts) != 2:
        if text.lower().startswith("بازی"):
            await update.message.reply_text(
                "❌ فرمت صحیح:\n\n"
                "بازی 500"
            )
        return

    if parts[0].lower() != "بازی":
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

    if not remove_balance(
        user.id,
        amount
    ):
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
        "join_request": None,
        "join_request_name": "",
        "joined": None,
        "joined_name": "",
        "status": "waiting",
        "group_id": update.effective_chat.id,
        "message_id": None,
        "winner": None,
        "paid": False,
        "created_at": datetime.now().isoformat()
    }

    save_data()

    try:
        msg = await update.message.reply_text(
            "🎮 بازی جدید!\n\n"
            f"👤 سازنده: {user.first_name}\n"
            f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
            "یک نفر روی «🎮 بازی با دوستان» بزند.\n"
            "سازنده باید ورود او را تأیید کند.",
            reply_markup=game_keyboard(game_id)
        )

        data["games"][game_id]["message_id"] = msg.message_id
        save_data()

    except Exception:
        data["games"].pop(game_id, None)
        add_balance(
            user.id,
            amount
        )

        await update.message.reply_text(
            "❌ ساخت بازی انجام نشد و مبلغ برگشت خورد."
        )


# =========================================================
# JOIN REQUEST
# =========================================================

async def join_game(query, context, game_id):
    user = query.from_user
    ensure_user(user)

    lock = get_game_lock(game_id)

    async with lock:
        game = data["games"].get(game_id)

        if not game:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        if game.get("status") != "waiting":
            await query.answer(
                "❌ این بازی دیگر قابل ورود نیست.",
                show_alert=True
            )
            return

        if user.id == game.get("creator"):
            await query.answer(
                "❌ شما سازنده بازی هستید.",
                show_alert=True
            )
            return

        if game.get("join_request") is not None:
            await query.answer(
                "❌ یک نفر قبلاً درخواست ورود داده است.",
                show_alert=True
            )
            return

        if get_balance(user.id) < game["amount"]:
            await query.answer(
                "❌ موجودی شما کافی نیست.",
                show_alert=True
            )
            return

        game["join_request"] = user.id
        game["join_request_name"] = (
            user.first_name or ""
        )

        save_data()

        await query.answer(
            "✅ درخواست ورود برای سازنده ارسال شد."
        )

        try:
            await context.bot.send_message(
                chat_id=game["creator"],
                text=(
                    "🎮 درخواست ورود به بازی\n\n"
                    f"👤 بازیکن: {user.first_name}\n"
                    f"🆔 آیدی: {user.id}\n"
                    f"💰 مبلغ: {game['amount']:,} DOGS\n\n"
                    "آیا ورود این بازیکن را تأیید می‌کنید؟"
                ),
                reply_markup=game_creator_keyboard(game_id)
            )
        except Exception:
            game["join_request"] = None
            game["join_request_name"] = ""
            save_data()

            await query.answer(
                "❌ ارسال درخواست به سازنده انجام نشد.",
                show_alert=True
            )


# =========================================================
# APPROVE JOIN
# =========================================================

async def approve_join(query, context, game_id):
    user = query.from_user

    if not is_owner(user.id):
        pass

    lock = get_game_lock(game_id)

    async with lock:
        game = data["games"].get(game_id)

        if not game:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        if user.id != game.get("creator"):
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند تأیید کند.",
                show_alert=True
            )
            return

        if game.get("status") != "waiting":
            await query.answer(
                "❌ بازی دیگر قابل تأیید نیست.",
                show_alert=True
            )
            return

        joiner_id = game.get("join_request")

        if not joiner_id:
            await query.answer(
                "❌ درخواست ورودی وجود ندارد.",
                show_alert=True
            )
            return

        if get_balance(joiner_id) < game["amount"]:
            game["join_request"] = None
            game["join_request_name"] = ""
            save_data()

            await query.answer(
                "❌ موجودی بازیکن دیگر کافی نیست.",
                show_alert=True
            )
            return

        # کسر مبلغ نفر دوم
        if not remove_balance(
            joiner_id,
            game["amount"]
        ):
            await query.answer(
                "❌ کسر موجودی بازیکن دوم انجام نشد.",
                show_alert=True
            )
            return

        game["joined"] = joiner_id
        game["joined_name"] = game.get(
            "join_request_name",
            ""
        )
        game["join_request"] = None
        game["join_request_name"] = ""
        game["status"] = "playing"

        save_data()

        await query.answer(
            "✅ ورود بازیکن تأیید شد."
        )

        # انتخاب خودکار برنده
        players = [
            game["creator"],
            game["joined"]
        ]

        winner = random.choice(players)

        loser = (
            game["joined"]
            if winner == game["creator"]
            else game["creator"]
        )

        amount = int(game["amount"])

        # طبق درخواست:
        # بازنده = 500-
        # برنده = 900+
        # مالک = 100+
        winner_prize = int(
            amount * 0.9
        )

        owner_fee = int(
            amount * 0.1
        )

        # برای بازی 500 دقیقاً 900 و 100
        if amount == 500:
            winner_prize = 900
            owner_fee = 100

        # پرداخت فقط یک بار
        if not game.get("paid", False):
            add_balance(
                winner,
                winner_prize
            )

            add_balance(
                get_owner_id(),
                owner_fee
            )

            game["winner"] = winner
            game["loser"] = loser
            game["winner_prize"] = winner_prize
            game["owner_fee"] = owner_fee
            game["paid"] = True
            game["status"] = "finished"

            save_data()

        creator_name = game.get(
            "creator_name",
            ""
        )

        joined_name = game.get(
            "joined_name",
            ""
        )

        winner_name = (
            creator_name
            if winner == game["creator"]
            else joined_name
        )

        loser_name = (
            creator_name
            if loser == game["creator"]
            else joined_name
        )

        result_text = (
            "🎮 بازی تمام شد!\n\n"
            f"👤 بازیکن اول: {creator_name}\n"
            f"👤 بازیکن دوم: {joined_name}\n\n"
            f"🏆 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"
            f"💰 دریافتی برنده: {winner_prize:,} DOGS\n"
            f"👑 کارمزد مالک: {owner_fee:,} DOGS"
        )

        try:
            await context.bot.edit_message_text(
                chat_id=game["group_id"],
                message_id=game["message_id"],
                text=result_text
            )
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=game["group_id"],
                    text=result_text
                )
            except Exception:
                pass

        GAME_LOCKS.pop(
            game_id,
            None
        )


# =========================================================
# REJECT JOIN
# =========================================================

async def reject_join(query, context, game_id):
    user = query.from_user

    lock = get_game_lock(game_id)

    async with lock:
        game = data["games"].get(game_id)

        if not game:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        if user.id != game.get("creator"):
            await query.answer(
                "⛔ فقط سازنده بازی.",
                show_alert=True
            )
            return

        if game.get("status") != "waiting":
            await query.answer(
                "❌ بازی دیگر در انتظار نیست.",
                show_alert=True
            )
            return

        joiner_id = game.get("join_request")

        game["join_request"] = None
        game["join_request_name"] = ""

        save_data()

        await query.answer(
            "❌ درخواست ورود رد شد."
        )

        if joiner_id:
            try:
                await context.bot.send_message(
                    chat_id=joiner_id,
                    text="❌ سازنده درخواست ورود شما به بازی را رد کرد."
                )
            except Exception:
                pass

        try:
            await query.edit_message_text(
                "❌ درخواست ورود به بازی رد شد."
            )
        except Exception:
            pass


# =========================================================
# CANCEL GAME
# =========================================================

async def cancel_game(query, context, game_id):
    user = query.from_user

    lock = get_game_lock(game_id)

    async with lock:
        game = data["games"].get(game_id)

        if not game:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
            return

        if user.id != game.get("creator"):
            await query.answer(
                "⛔ فقط سازنده بازی می‌تواند لغو کند.",
                show_alert=True
            )
            return

        if game.get("status") != "waiting":
            await query.answer(
                "❌ بازی دیگر قابل لغو نیست.",
                show_alert=True
            )
            return

        amount = int(
            game.get(
                "amount",
                0
            )
        )

        # فقط مبلغ سازنده برگشت می‌خورد
        add_balance(
            user.id,
            amount
        )

        joiner_id = game.get(
            "join_request"
        )

        game["status"] = "cancelled"
        game["cancelled_by"] = user.id
        game["cancelled_at"] = datetime.now().isoformat()

        # درخواست نفر دوم فقط درخواست بوده و پولی از او کم نشده
        game["join_request"] = None
        game["join_request_name"] = ""

        save_data()

        await query.answer(
            "✅ بازی لغو شد و مبلغ کامل برگشت خورد."
        )

        if joiner_id:
            try:
                await context.bot.send_message(
                    chat_id=joiner_id,
                    text="❌ بازی توسط سازنده لغو شد."
                )
            except Exception:
                pass

        try:
            await context.bot.edit_message_text(
                chat_id=game["group_id"],
                message_id=game["message_id"],
                text=(
                    "❌ بازی لغو شد.\n\n"
                    f"💰 مبلغ {amount:,} DOGS "
                    "به سازنده برگشت داده شد.\n"
                    "👑 هیچ کارمزدی گرفته نشد."
                )
            )
        except Exception:
            try:
                await query.edit_message_text(
                    "❌ بازی لغو شد و مبلغ کامل برگشت خورد."
                )
            except Exception:
                pass

        GAME_LOCKS.pop(
            game_id,
            None
        )


# =========================================================
# CALLBACK HANDLER
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
            f"💰 موجودی: "
            f"{get_balance(user.id):,} DOGS",
            reply_markup=main_keyboard(user.id)
        )
        return

    # FORCE JOIN
    if action == "check_join":
        if await check_membership(
            user.id,
            context
        ):
            await query.edit_message_text(
                "✅ عضویت شما تأیید شد.\n\n"
                "🤖 منوی اصلی",
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
        await show_referral(
            query,
            context
        )
        return

    # DEPOSIT
    if action == "deposit":
        await show_deposit(query)
        return

    if action == "deposit_ultra":
        await deposit_ultra(
            query,
            context
        )
        return

    if action == "deposit_exchange":
        await deposit_exchange(
            query,
            context
        )
        return

    # WITHDRAW
    if action == "withdraw":
        await show_withdraw(
            query,
            context
        )
        return

    # SUPPORT
    if action == "support":
        await show_support(
            query,
            context
        )
        return

    # ADMIN
    if action == "admin":
        await show_admin(query)
        return

    # ADMIN TOGGLE
    if action == "admin_toggle":
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        data["settings"]["bot_enabled"] = (
            not bot_enabled()
        )

        save_data()

        await show_admin(query)
        return

    # ADMIN GROUP
    if action == "admin_group":
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_group"

        await query.edit_message_text(
            "👥 گپ اجباری\n\n"
            "آیدی یا لینک گپ را ارسال کنید.\n\n"
            "برای خاموش کردن:\n"
            "off"
        )
        return

    # ADMIN CHANNEL
    if action == "admin_channel":
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_channel"

        await query.edit_message_text(
            "📢 چنل اجباری\n\n"
            "آیدی یا لینک چنل را ارسال کنید.\n\n"
            "برای خاموش کردن:\n"
            "off"
        )
        return

    # ADMIN OWNER
    if action == "admin_owner":
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
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
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        total_users = len(
            data["users"]
        )

        total_balance = 0

        for u in data["users"].values():
            try:
                total_balance += int(
                    u.get("balance", 0)
                )
            except Exception:
                pass

        await query.edit_message_text(
            "📊 آمار ربات\n\n"
            f"👤 کاربران: {total_users:,}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
            f"💳 واریزهای در انتظار: "
            f"{len(data['pending_deposits'])}\n"
            f"💸 برداشت‌های در انتظار: "
            f"{len(data['pending_withdrawals'])}\n"
            f"🎮 تعداد بازی‌ها: "
            f"{len(data['games'])}",
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
        game_id = action.split(
            ":",
            1
        )[1]

        await join_game(
            query,
            context,
            game_id
        )
        return

    # GAME APPROVE
    if action.startswith("approve_join:"):
        game_id = action.split(
            ":",
            1
        )[1]

        await approve_join(
            query,
            context,
            game_id
        )
        return

    # GAME REJECT
    if action.startswith("reject_join:"):
        game_id = action.split(
            ":",
            1
        )[1]

        await reject_join(
            query,
            context,
            game_id
        )
        return

    # GAME CANCEL
    if action.startswith("cancel_game:"):
        game_id = action.split(
            ":",
            1
        )[1]

        await cancel_game(
            query,
            context,
            game_id
        )
        return

    # APPROVE DEPOSIT
    if action.startswith("approve_deposit:"):
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        did = action.split(
            ":",
            1
        )[1]

        dep = data["pending_deposits"].get(
            did
        )

        if not dep or dep.get("status") != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        context.user_data.clear()
        context.user_data["state"] = "deposit_amount"
        context.user_data["approve_deposit_id"] = did

        await query.message.reply_text(
            "💰 مقدار واریزی را وارد کنید:"
        )
        return

    # REJECT DEPOSIT
    if action.startswith("reject_deposit:"):
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        did = action.split(
            ":",
            1
        )[1]

        dep = data["pending_deposits"].get(
            did
        )

        if not dep or dep.get("status") != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        dep["status"] = "rejected"

        save_data()

        try:
            await context.bot.send_message(
                chat_id=dep["user_id"],
                text="❌ واریز شما توسط مالک رد شد."
            )
        except Exception:
            pass

        try:
            await query.edit_message_text(
                "❌ واریز رد شد."
            )
        except Exception:
            pass

        return

    # APPROVE WITHDRAW
    if action.startswith("approve_withdraw:"):
        if not is_owner(user.id):
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        wid = action.split(
            ":",
            1
        )[1]

        wd = data["pending_withdrawals"].get(
            wid
        )

        if not wd or wd.get("status") != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        wd["status"] = "approved"

        save_data()

        try:
            await context.bot.send_message(
                chat_id=wd["user_id"],
                text=(
                    "✅ برداشت شما تأیید شد.\n\n"
                    f"💰 مقدار: "
                    f"{wd['amount']:,} DOGS\n"
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
            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )
            return

        wid = action.split(
            ":",
            1
        )[1]

        wd = data["pending_withdrawals"].get(
            wid
        )

        if not wd or wd.get("status") != "pending":
            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )
            return

        wd["status"] = "rejected"

        add_balance(
            wd["user_id"],
            wd["amount"]
        )

        save_data()

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
            "❌ برداشت رد شد و مبلغ برگشت خورد."
        )
        return


# =========================================================
# TRANSFER
# =========================================================

async def handle_transfer(update, context, text):
    user = update.effective_user

    parts = text.strip().split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "انتقال 500\n\n"
            "باید روی پیام کاربر ریپلای کنید."
        )
        return True

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return True

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )
        return True

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ برای انتقال باید روی پیام کاربر ریپلای کنید.\n\n"
            "مثال:\n"
            "انتقال 500"
        )
        return True

    target = update.message.reply_to_message.from_user

    if not target:
        await update.message.reply_text(
            "❌ کاربر مقصد پیدا نشد."
        )
        return True

    if target.id == user.id:
        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return True

    ensure_user(target)

    if get_balance(user.id) < amount:
        await update.message.reply_text(
            "❌ موجودی شما کافی نیست.\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(user.id):,} DOGS"
        )
        return True

    if not remove_balance(
        user.id,
        amount
    ):
        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )
        return True

    add_balance(
        target.id,
        amount
    )

    await update.message.reply_text(
        "✅ انتقال با موفقیت انجام شد.\n\n"
        f"👤 فرستنده: {user.first_name}\n"
        f"👤 گیرنده: {target.first_name}\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"💵 موجودی شما: "
        f"{get_balance(user.id):,} DOGS"
    )

    try:
        await context.bot.send_message(
            chat_id=target.id,
            text=(
                "💰 انتقال دریافت شد.\n\n"
                f"👤 از طرف: {user.first_name}\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"💵 موجودی جدید: "
                f"{get_balance(target.id):,} DOGS"
            )
        )
    except Exception:
        pass

    return True


# =========================================================
# ADMIN STATES
# =========================================================

async def handle_admin_states(update, context):
    user = update.effective_user

    if not is_owner(user.id):
        return False

    state = context.user_data.get(
        "state"
    )

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

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ نامعتبر است."
            )
            return True

        did = context.user_data.get(
            "approve_deposit_id"
        )

        dep = data["pending_deposits"].get(
            did
        )

        if not dep or dep.get("status") != "pending":
            context.user_data.clear()

            await update.message.reply_text(
                "❌ درخواست پیدا نشد."
            )
            return True

        add_balance(
            dep["user_id"],
            amount
        )

        dep["status"] = "approved"
        dep["amount"] = amount

        save_data()

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

    # FORCE GROUP
    if state == "admin_group":
        value = (
            update.message.text or ""
        ).strip()

        if value.lower() == "off":
            value = ""

        data["settings"]["force_group"] = value

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد."
        )

        return True

    # FORCE CHANNEL
    if state == "admin_channel":
        value = (
            update.message.text or ""
        ).strip()

        if value.lower() == "off":
            value = ""

        data["settings"]["force_channel"] = value

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ چنل اجباری ذخیره شد."
        )

        return True

    # OWNER TRANSFER
    if state == "admin_owner":
        try:
            new_owner = int(
                update.message.text.strip()
            )
        except Exception:
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        if not get_user(new_owner):
            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را استارت نکرده است."
            )
            return True

        old_owner = get_owner_id()

        data["owner_id"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "👑 مالکیت منتقل شد.\n\n"
            f"👤 مالک قبلی: {old_owner}\n"
            f"👑 مالک جدید: {new_owner}"
        )

        return True

    return False


# =========================================================
# PRIVATE MESSAGE HANDLER
# =========================================================

async def private_message_handler(update, context):
    if not update.message:
        return

    user = update.effective_user

    ensure_user(user)

    # خاموش بودن ربات
    if (
        not bot_enabled()
        and not is_owner(user.id)
    ):
        await update.message.reply_text(
            "⛔ ربات در حال حاضر خاموش است."
        )
        return

    # انتقال
    text = (
        update.message.text or ""
    ).strip()

    if text.startswith("انتقال"):
        await handle_transfer(
            update,
            context,
            text
        )
        return

    # FORCE JOIN
    if not await check_membership(
        user.id,
        context
    ):
        await send_force_join(
            update,
            context
        )
        return

    # ADMIN STATES
    if is_owner(user.id):
        handled = await handle_admin_states(
            update,
            context
        )

        if handled:
            return

    state = context.user_data.get(
        "state"
    )

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
                f"❌ حداقل برداشت "
                f"{MIN_WITHDRAW:,} DOGS است."
            )
            return

        if get_balance(user.id) < amount:
            await update.message.reply_text(
                "❌ موجودی شما کافی نیست."
            )
            return

        context.user_data["withdraw_amount"] = amount
        context.user_data["state"] = "withdraw_address"

        await update.message.reply_text(
            "✅ مقدار ثبت شد.\n\n"
            "📥 آدرس کیف پول یا آیدی دریافت‌کننده را ارسال کنید:"
        )
        return

    # WITHDRAW ADDRESS
    if state == "withdraw_address":
        amount = context.user_data.get(
            "withdraw_amount"
        )

        address = (
            update.message.text or ""
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

        save_data()

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
        except Exception as e:
            print(
                "OWNER WITHDRAW MESSAGE ERROR:",
                e
            )

        return

    # DEPOSIT
    if state in (
        "deposit_ultra",
        "deposit_exchange"
    ):
        deposit_type = (
            "اولترا"
            if state == "deposit_ultra"
            else "صرافی"
        )

        did = str(
            random.randint(
                10000000,
                99999999
            )
        )

        if update.message.photo:
            content_type = "photo"
            content = update.message.photo[-1].file_id
        elif update.message.document:
            content_type = "document"
            content = update.message.document.file_id
        else:
            content_type = "text"
            content = (
                update.message.text or ""
            )

        data["pending_deposits"][did] = {
            "id": did,
            "user_id": user.id,
            "username": user.username or "",
            "type": deposit_type,
            "content_type": content_type,
            "content": content,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ رسید واریز ثبت شد.\n\n"
            "⏳ توسط مالک بررسی می‌شود."
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
                    photo=content,
                    caption=owner_text,
                    reply_markup=keyboard
                )

            elif content_type == "document":
                await context.bot.send_document(
                    chat_id=get_owner_id(),
                    document=content,
                    caption=owner_text,
                    reply_markup=keyboard
                )

            else:
                await context.bot.send_message(
                    chat_id=get_owner_id(),
                    text=(
                        owner_text
                        + "\n\n📎 رسید:\n"
                        + content
                    ),
                    reply_markup=keyboard
                )

        except Exception as e:
            print(
                "OWNER DEPOSIT MESSAGE ERROR:",
                e
            )

        return

    # SUPPORT
    if state == "support":
        message_text = (
            update.message.text or ""
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
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه: "
        f"{len(get_user(user.id).get('referrals', []))}",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# GROUP MESSAGE HANDLER
# =========================================================

async def group_message_handler(update, context):
    if not update.message:
        return

    text = (
        update.message.text or ""
    ).strip()

    # فقط بازی در گپ
    if text.startswith("بازی"):
        await handle_group_game(
            update,
            context
        )
        return


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
        print(
            "❌ BOT_TOKEN پیدا نشد."
        )
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

    # پیام‌های گروه فقط برای بازی
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.TEXT
            & ~filters.COMMAND,
            group_message_handler
        )
    )

    # پیام‌های خصوصی
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & ~filters.COMMAND,
            private_message_handler
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
