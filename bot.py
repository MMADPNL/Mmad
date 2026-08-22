import json
import os
import random
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

GAME_FEE = 0

DATA_FILE = "bot_data.json"


# =========================
# DATABASE
# =========================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "referrals": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "mandatory_channel": "",
        "mandatory_group": "",
    },
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        for key, value in DEFAULT_DATA.items():
            if key not in loaded:
                loaded[key] = json.loads(json.dumps(value))

        for key, value in DEFAULT_DATA["settings"].items():
            if key not in loaded["settings"]:
                loaded["settings"][key] = value

        return loaded

    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# USER SYSTEM
# =========================

def create_user(user):
    uid = str(user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "date": datetime.now().isoformat(),
        }
    else:
        data["users"][uid]["name"] = user.first_name or ""
        data["users"][uid]["username"] = user.username or ""

    save_data()
    return data["users"][uid]


def get_user(uid):
    return data["users"].get(str(uid))


def balance(uid):
    user = get_user(uid)
    return int(user.get("balance", 0)) if user else 0


def add_balance(uid, amount):
    user = get_user(uid)
    if not user:
        return False

    user["balance"] = int(user.get("balance", 0)) + int(amount)
    save_data()
    return True


def remove_balance(uid, amount):
    user = get_user(uid)
    if not user:
        return False

    amount = int(amount)

    if balance(uid) < amount:
        return False

    user["balance"] -= amount
    save_data()
    return True


def is_owner(uid):
    return int(uid) == int(data.get("owner", OWNER_ID))


def user_display(uid):
    user = get_user(uid)

    if not user:
        return str(uid)

    username = user.get("username", "")
    if username:
        return f"@{username}"

    name = user.get("name", "")
    if name:
        return name

    return str(uid)


# =========================
# BOT / MEMBERSHIP CHECK
# =========================

def bot_is_on():
    return bool(data["settings"].get("bot", True))


async def mandatory_check(update, context):
    user = update.effective_user

    if not user:
        return True

    if is_owner(user.id):
        return True

    if not bot_is_on():
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "⛔ ربات در حال حاضر خاموش است."
            )
        return False

    missing = []

    channel = data["settings"].get("mandatory_channel", "").strip()
    group = data["settings"].get("mandatory_group", "").strip()

    for target, label in [
        (channel, "کانال"),
        (group, "گپ"),
    ]:
        if not target:
            continue

        try:
            member = await context.bot.get_chat_member(
                chat_id=target,
                user_id=user.id,
            )

            if member.status in ("left", "kicked"):
                missing.append((target, label))

        except Exception:
            # اگر شناسه/یوزرنیم اشتباه باشد، دسترسی کاربر را مسدود نمی‌کنیم.
            continue

    if missing and update.effective_chat.type == "private":
        buttons = []

        for target, label in missing:
            clean = target.lstrip("@")
            buttons.append([
                InlineKeyboardButton(
                    f"📢 ورود به {label}",
                    url=f"https://t.me/{clean}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="check_membership"
            )
        ])

        await update.message.reply_text(
            "🔒 برای استفاده از ربات ابتدا در موارد زیر عضو شوید:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return False

    return True


# =========================
# PRIVATE KEYBOARDS
# =========================

def main_keyboard(uid):
    rows = [
        ["💳 واریزی", "👥 زیر مجموعه"],
        ["👤 پروفایل", "💰 برداشت"],
    ]

    if is_owner(uid):
        rows.append(["⚙️ پنل مدیریت"])

    rows.append(["🎧 پشتیبانی"])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [["🔙 برگشت"]],
        resize_keyboard=True
    )


def admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🤖 روشن/خاموش ربات", "📢 کانال اجباری"],
            ["👥 گپ اجباری", "🔄 انتقال مالکیت"],
            ["📊 آمار", "🔙 برگشت"],
        ],
        resize_keyboard=True
    )


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    create_user(user)
    context.user_data.clear()

    if not await mandatory_check(update, context):
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🤖 به ربات خوش آمدید.\n\n"
            f"👤 {user.first_name}\n\n"
            f"💰 موجودی شما:\n"
            f"{balance(user.id):,} DOGS\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=main_keyboard(user.id),
        )
        return

    await update.message.reply_text(
        "🤖 ربات فعال است.\n\n"
        "🎮 برای شروع بازی در گروه بنویسید:\n"
        "بازی 500\n\n"
        f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر بازی: {MAX_GAME:,} DOGS",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================
# PROFILE
# =========================

async def show_profile(update, context):
    user = update.effective_user
    create_user(user)

    profile = get_user(user.id)
    username = profile.get("username", "")
    username_text = f"@{username}" if username else "ندارد"

    await update.message.reply_text(
        "👤 پروفایل شما\n\n"
        f"🆔 آیدی: {user.id}\n"
        f"👤 نام: {profile.get('name', '')}\n"
        f"🔹 یوزرنیم: {username_text}\n\n"
        f"💰 موجودی: {balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه‌ها: {int(profile.get('referrals', 0))}",
        reply_markup=back_keyboard(),
    )


# =========================
# REFERRALS
# =========================

async def show_referrals(update, context):
    user = update.effective_user
    create_user(user)

    bot_username = context.bot.username or "YOUR_BOT"

    referral_link = (
        f"https://t.me/{bot_username}?start=ref_{user.id}"
    )

    referrals = int(
        get_user(user.id).get("referrals", 0)
    )

    await update.message.reply_text(
        "👥 زیرمجموعه‌گیری\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"
        f"👥 تعداد زیرمجموعه‌ها: {referrals}\n\n"
        "📢 لینک بالا را برای دوستان خود ارسال کنید.",
        reply_markup=back_keyboard(),
    )


# =========================
# DEPOSIT MENU
# =========================

async def show_deposit(update, context):
    context.user_data.clear()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💎 اولترا",
                callback_data="deposit_ultra"
            ),
            InlineKeyboardButton(
                "🏦 صرافی",
                callback_data="deposit_exchange"
            ),
        ]
    ])

    await update.message.reply_text(
        "💳 بخش واریزی\n\n"
        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
        "روش واریز را انتخاب کنید:",
        reply_markup=keyboard,
    )


async def deposit_method_callback(update, context):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if not is_owner(user.id) and not bot_is_on():
        await query.answer(
            "⛔ ربات خاموش است.",
            show_alert=True
        )
        return

    if query.data == "deposit_ultra":
        method = "اولترا"
    else:
        method = "صرافی"

    context.user_data.clear()
    context.user_data["state"] = "deposit_receipt"
    context.user_data["deposit_method"] = method

    await query.message.reply_text(
        f"💳 روش انتخابی: {method}\n\n"
        "💎 آدرس کیف پول DOGS:\n\n"
        f"{DOGS_WALLET}\n\n"
        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
        "1️⃣ ابتدا DOGS را واریز کنید.\n"
        "2️⃣ عکس رسید یا لینک تراکنش را ارسال کنید.\n"
        "3️⃣ سپس مقدار DOGS را ارسال کنید.",
        reply_markup=back_keyboard(),
    )


# =========================
# DEPOSIT RECEIPT
# =========================

async def handle_deposit_receipt(update, context):
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data["receipt"] = (
            f"📸 رسید تصویری\nFile ID: {photo.file_id}"
        )

    elif update.message.text:
        text = update.message.text.strip()

        if not text:
            await update.message.reply_text(
                "❌ رسید یا لینک تراکنش را ارسال کنید."
            )
            return

        context.user_data["receipt"] = text

    else:
        await update.message.reply_text(
            "❌ لطفاً عکس رسید یا لینک تراکنش را ارسال کنید."
        )
        return

    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n\n"
        "💰 حالا مقدار DOGS واریزی را ارسال کنید.\n\n"
        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
        "مثال:\n5000",
        reply_markup=back_keyboard(),
    )


# =========================
# DEPOSIT AMOUNT
# =========================

async def handle_deposit_amount(update, context):
    user = update.effective_user

    if not update.message.text:
        await update.message.reply_text(
            "❌ مقدار DOGS را به صورت عدد ارسال کنید."
        )
        return

    try:
        amount = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید.\nمثال: 5000"
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."
        )
        return

    receipt = context.user_data.get("receipt", "بدون رسید")
    method = context.user_data.get("deposit_method", "نامشخص")

    request_id = f"{user.id}_{int(datetime.now().timestamp())}"

    data["deposits"][request_id] = {
        "id": request_id,
        "user_id": user.id,
        "name": user.first_name or "",
        "username": user.username or "",
        "amount": amount,
        "method": method,
        "receipt": receipt,
        "status": "pending",
        "date": datetime.now().isoformat(),
    }

    save_data()
    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست واریز ثبت شد.\n\n"
        f"💳 روش: {method}\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "⏳ درخواست برای مالک ارسال شد.",
        reply_markup=main_keyboard(user.id),
    )

    username = f"@{user.username}" if user.username else "ندارد"

    owner_text = (
        "💳 واریزی جدید\n\n"
        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n"
        f"💳 روش: {method}\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"📝 رسید:\n{receipt}\n\n"
        f"🆔 شناسه:\n{request_id}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"ok_dep_{request_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"no_dep_{request_id}"
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=data["owner"],
            text=owner_text,
            reply_markup=keyboard,
        )
    except Exception as e:
        print(f"❌ خطا در ارسال واریزی: {e}")


# =========================
# WITHDRAW
# =========================

async def show_withdraw(update, context):
    user = update.effective_user
    create_user(user)

    current = balance(user.id)

    if current < MIN_WITHDRAW:
        await update.message.reply_text(
            "💰 برداشت DOGS\n\n"
            f"💳 موجودی شما: {current:,} DOGS\n\n"
            f"❌ حداقل برداشت: {MIN_WITHDRAW:,} DOGS",
            reply_markup=back_keyboard(),
        )
        return

    context.user_data.clear()
    context.user_data["state"] = "withdraw_address"

    await update.message.reply_text(
        "💰 برداشت DOGS\n\n"
        f"💳 موجودی شما: {current:,} DOGS\n\n"
        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "1️⃣ آدرس کیف پول DOGS خود را ارسال کنید.",
        reply_markup=back_keyboard(),
    )


async def handle_withdraw_address(update, context):
    if not update.message.text:
        await update.message.reply_text(
            "❌ آدرس کیف پول را ارسال کنید."
        )
        return

    address = update.message.text.strip()

    if len(address) < 10:
        await update.message.reply_text(
            "❌ آدرس کیف پول معتبر نیست."
        )
        return

    context.user_data["withdraw_address"] = address
    context.user_data["state"] = "withdraw_amount"

    await update.message.reply_text(
        "✅ آدرس دریافت شد.\n\n"
        f"💳 آدرس:\n{address}\n\n"
        "2️⃣ مقدار DOGS برای برداشت را ارسال کنید.\n\n"
        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "مثال:\n10000",
        reply_markup=back_keyboard(),
    )


async def handle_withdraw_amount(update, context):
    user = update.effective_user

    if not update.message.text:
        await update.message.reply_text(
            "❌ مقدار برداشت را به صورت عدد ارسال کنید."
        )
        return

    try:
        amount = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ فقط عدد ارسال کنید.")
        return

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    if balance(user.id) < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💳 موجودی: {balance(user.id):,} DOGS\n"
            f"💰 برداشت: {amount:,} DOGS"
        )
        return

    address = context.user_data.get("withdraw_address")

    if not address:
        context.user_data["state"] = "withdraw_address"
        await update.message.reply_text(
            "❌ آدرس پیدا نشد.\nدوباره آدرس کیف پول را ارسال کنید."
        )
        return

    if not remove_balance(user.id, amount):
        await update.message.reply_text("❌ خطا در کسر موجودی.")
        return

    request_id = f"{user.id}_{int(datetime.now().timestamp())}"

    data["withdraws"][request_id] = {
        "id": request_id,
        "user_id": user.id,
        "name": user.first_name or "",
        "username": user.username or "",
        "address": address,
        "amount": amount,
        "status": "pending",
        "date": datetime.now().isoformat(),
    }

    save_data()

    new_balance = balance(user.id)
    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"💳 آدرس:\n{address}\n\n"
        f"💰 موجودی جدید: {new_balance:,} DOGS\n\n"
        "⏳ درخواست برای مالک ارسال شد.",
        reply_markup=main_keyboard(user.id),
    )

    username = f"@{user.username}" if user.username else "ندارد"

    owner_text = (
        "💰 درخواست برداشت جدید\n\n"
        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"💳 آدرس:\n{address}\n\n"
        f"💰 موجودی فعلی: {new_balance:,} DOGS\n\n"
        f"🆔 شناسه:\n{request_id}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"ok_wd_{request_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"no_wd_{request_id}"
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=data["owner"],
            text=owner_text,
            reply_markup=keyboard,
        )
    except Exception as e:
        print(f"❌ خطا در ارسال برداشت: {e}")

        add_balance(user.id, amount)

        data["withdraws"][request_id]["status"] = "failed"
        save_data()


# =========================
# SUPPORT / HOME
# =========================

async def show_support(update, context):
    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "برای ارتباط با پشتیبانی:\n\n"
        f"👤 {SUPPORT_USERNAME}",
        reply_markup=back_keyboard(),
    )


async def go_home(update, context):
    user = update.effective_user

    if not user:
        return

    create_user(user)
    context.user_data.clear()

    await update.message.reply_text(
        "🏠 منوی اصلی\n\n"
        f"💰 موجودی شما:\n{balance(user.id):,} DOGS\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_keyboard(user.id),
    )


# =========================
# GAME
# =========================

ACTIVE_GAMES = {}


async def game_command(update, context):
    user = update.effective_user

    if not user:
        return

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ بازی فقط داخل گروه قابل انجام است."
        )
        return

    if not bot_is_on() and not is_owner(user.id):
        await update.message.reply_text("⛔ ربات در حال حاضر خاموش است.")
        return

    create_user(user)

    try:
        parts = update.message.text.strip().split()
        if len(parts) != 2:
            raise ValueError
        amount = int(parts[1])
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ فرمت اشتباه است.\n\nمثال:\nبازی 500"
        )
        return

    if amount < MIN_GAME:
        await update.message.reply_text(
            f"❌ حداقل شرط بازی {MIN_GAME:,} DOGS است."
        )
        return

    if amount > MAX_GAME:
        await update.message.reply_text(
            f"❌ حداکثر شرط بازی {MAX_GAME:,} DOGS است."
        )
        return

    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_GAMES:
        await update.message.reply_text(
            "❌ در این گپ یک بازی فعال است."
        )
        return

    if balance(user.id) < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی شما: {balance(user.id):,} DOGS"
        )
        return

    if not remove_balance(user.id, amount):
        await update.message.reply_text("❌ خطا در کسر موجودی.")
        return

    ACTIVE_GAMES[chat_id] = {
        "creator": user.id,
        "amount": amount,
        "created_at": datetime.now().isoformat(),
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 ورود به بازی",
            callback_data="join_game"
        )],
        [InlineKeyboardButton(
            "❌ لغو بازی",
            callback_data="cancel_game"
        )],
    ])

    await update.message.reply_text(
        "🎮 بازی ساخته شد\n\n"
        f"👤 سازنده: {user_display(user.id)}\n\n"
        f"💰 شرط: {amount:,} DOGS\n\n"
        "👥 فقط یک نفر می‌تواند وارد بازی شود.",
        reply_markup=keyboard,
    )


async def game_callback(update, context):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat.id

    if query.data == "check_membership":
        await query.answer("عضویت دوباره بررسی شد.", show_alert=True)
        return

    await query.answer()

    if chat_id not in ACTIVE_GAMES:
        await query.answer(
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True
        )
        return

    game = ACTIVE_GAMES[chat_id]

    if query.data == "cancel_game":
        if user.id != game["creator"]:
            await query.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True
            )
            return

        add_balance(user.id, game["amount"])
        del ACTIVE_GAMES[chat_id]

        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {game['amount']:,} DOGS به سازنده برگشت داده شد."
        )
        return

    if query.data == "join_game":
        if user.id == game["creator"]:
            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )
            return

        create_user(user)
        amount = game["amount"]

        if balance(user.id) < amount:
            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )
            return

        if not remove_balance(user.id, amount):
            await query.answer(
                "❌ خطا در کسر موجودی.",
                show_alert=True
            )
            return

        winner = random.choice([game["creator"], user.id])
        loser = user.id if winner == game["creator"] else game["creator"]

        total_pot = amount * 2
        prize = total_pot - GAME_FEE

        add_balance(winner, prize)

        if GAME_FEE > 0:
            if not get_user(data["owner"]):
                data["users"][str(data["owner"])] = {
                    "id": data["owner"],
                    "name": "OWNER",
                    "username": "",
                    "balance": 0,
                    "referrals": 0,
                    "referred_by": None,
                    "date": datetime.now().isoformat(),
                }
                save_data()
            add_balance(data["owner"], GAME_FEE)

        del ACTIVE_GAMES[chat_id]

        await query.edit_message_text(
            "🎮 نتیجه بازی\n\n"
            f"🏆 برنده: {user_display(winner)}\n\n"
            f"💰 جایزه: {prize:,} DOGS\n\n"
            f"😢 بازنده: {user_display(loser)}"
        )


# =========================
# ADMIN DEPOSIT / WITHDRAW
# =========================

async def admin_callback(update, context):
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    if query.data.startswith("ok_dep_"):
        request_id = query.data[len("ok_dep_"):]
        request = data["deposits"].get(request_id)

        if not request:
            await query.edit_message_text("❌ درخواست پیدا نشد.")
            return

        if request["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )
            return

        uid = request["user_id"]
        add_balance(uid, request["amount"])

        request["status"] = "approved"
        request["approved_at"] = datetime.now().isoformat()
        save_data()

        await query.edit_message_text(
            "✅ واریز تأیید شد.\n\n"
            f"👤 کاربر: {user_display(uid)}\n"
            f"💰 مبلغ: {request['amount']:,} DOGS"
        )

        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "✅ واریز شما تأیید شد.\n\n"
                    f"💰 مبلغ اضافه‌شده: {request['amount']:,} DOGS\n\n"
                    f"💳 موجودی جدید: {balance(uid):,} DOGS"
                )
            )
        except Exception as e:
            print(f"❌ ارسال پیام تأیید واریز: {e}")
        return

    if query.data.startswith("no_dep_"):
        request_id = query.data[len("no_dep_"):]
        request = data["deposits"].get(request_id)

        if not request:
            await query.edit_message_text("❌ درخواست پیدا نشد.")
            return

        if request["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )
            return

        request["status"] = "rejected"
        request["rejected_at"] = datetime.now().isoformat()
        save_data()

        await query.edit_message_text(
            "❌ واریز رد شد.\n\n"
            f"👤 کاربر: {user_display(request['user_id'])}\n"
            f"💰 مبلغ: {request['amount']:,} DOGS"
        )

        try:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text=(
                    "❌ درخواست واریز شما رد شد.\n\n"
                    "در صورت اشتباه، با پشتیبانی تماس بگیرید."
                )
            )
        except Exception as e:
            print(f"❌ ارسال پیام رد واریز: {e}")


async def admin_withdraw_callback(update, context):
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    if query.data.startswith("ok_wd_"):
        request_id = query.data[len("ok_wd_"):]
        request = data["withdraws"].get(request_id)

        if not request:
            await query.edit_message_text("❌ درخواست پیدا نشد.")
            return

        if request["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )
            return

        request["status"] = "approved"
        request["approved_at"] = datetime.now().isoformat()
        save_data()

        await query.edit_message_text(
            "✅ برداشت تأیید شد.\n\n"
            f"👤 کاربر: {user_display(request['user_id'])}\n\n"
            f"💰 مبلغ: {request['amount']:,} DOGS\n\n"
            f"💳 آدرس:\n{request['address']}"
        )

        try:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text=(
                    "✅ درخواست برداشت شما تأیید شد.\n\n"
                    f"💰 مبلغ: {request['amount']:,} DOGS\n\n"
                    "پرداخت توسط مالک بررسی و تأیید شد."
                )
            )
        except Exception as e:
            print(f"❌ ارسال پیام تأیید برداشت: {e}")
        return

    if query.data.startswith("no_wd_"):
        request_id = query.data[len("no_wd_"):]
        request = data["withdraws"].get(request_id)

        if not request:
            await query.edit_message_text("❌ درخواست پیدا نشد.")
            return

        if request["status"] != "pending":
            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )
            return

        add_balance(request["user_id"], request["amount"])

        request["status"] = "rejected"
        request["rejected_at"] = datetime.now().isoformat()
        save_data()

        await query.edit_message_text(
            "❌ برداشت رد شد.\n\n"
            f"👤 کاربر: {user_display(request['user_id'])}\n\n"
            f"💰 مبلغ برگشت داده شد: {request['amount']:,} DOGS"
        )

        try:
            await context.bot.send_message(
                chat_id=request["user_id"],
                text=(
                    "❌ درخواست برداشت شما رد شد.\n\n"
                    f"💰 مبلغ {request['amount']:,} DOGS "
                    "به موجودی شما برگشت داده شد.\n\n"
                    f"💳 موجودی جدید: {balance(request['user_id']):,} DOGS"
                )
            )
        except Exception as e:
            print(f"❌ ارسال پیام رد برداشت: {e}")


# =========================
# ADMIN PANEL
# =========================

async def show_admin_panel(update, context):
    if not is_owner(update.effective_user.id):
        return

    status = "🟢 روشن" if bot_is_on() else "🔴 خاموش"
    channel = data["settings"].get("mandatory_channel") or "تنظیم نشده"
    group = data["settings"].get("mandatory_group") or "تنظیم نشده"

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"🤖 وضعیت ربات: {status}\n"
        f"📢 کانال اجباری: {channel}\n"
        f"👥 گپ اجباری: {group}\n\n"
        "گزینه موردنظر را انتخاب کنید:",
        reply_markup=admin_keyboard(),
    )


async def admin_stats(update, context):
    if not is_owner(update.effective_user.id):
        return

    users = len(data["users"])
    deposits = len(data["deposits"])
    withdraws = len(data["withdraws"])

    approved_deposits = sum(
        1 for x in data["deposits"].values()
        if x.get("status") == "approved"
    )

    pending_deposits = sum(
        1 for x in data["deposits"].values()
        if x.get("status") == "pending"
    )

    approved_withdraws = sum(
        1 for x in data["withdraws"].values()
        if x.get("status") == "approved"
    )

    pending_withdraws = sum(
        1 for x in data["withdraws"].values()
        if x.get("status") == "pending"
    )

    total_balance = sum(
        int(x.get("balance", 0))
        for x in data["users"].values()
    )

    await update.message.reply_text(
        "📊 آمار ربات\n\n"
        f"👥 تعداد کاربران: {users:,}\n"
        f"💰 مجموع موجودی کاربران: {total_balance:,} DOGS\n\n"
        f"💳 کل واریزی‌ها: {deposits:,}\n"
        f"✅ واریزی تأییدشده: {approved_deposits:,}\n"
        f"⏳ واریزی در انتظار: {pending_deposits:,}\n\n"
        f"💰 کل برداشت‌ها: {withdraws:,}\n"
        f"✅ برداشت تأییدشده: {approved_withdraws:,}\n"
        f"⏳ برداشت در انتظار: {pending_withdraws:,}",
        reply_markup=admin_keyboard(),
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update, context):
    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text

    if not is_owner(user.id) and not await mandatory_check(update, context):
        return

    if text == "👤 پروفایل":
        await show_profile(update, context)

    elif text == "👥 زیر مجموعه":
        await show_referrals(update, context)

    elif text == "💳 واریزی":
        await show_deposit(update, context)

    elif text == "💰 برداشت":
        await show_withdraw(update, context)

    elif text == "🎧 پشتیبانی":
        await show_support(update, context)

    elif text == "🔙 برگشت":
        await go_home(update, context)

    elif text == "⚙️ پنل مدیریت":
        await show_admin_panel(update, context)

    elif text == "🤖 روشن/خاموش ربات":
        if not is_owner(user.id):
            return

        data["settings"]["bot"] = not bot_is_on()
        save_data()

        status = "🟢 روشن" if bot_is_on() else "🔴 خاموش"

        await update.message.reply_text(
            f"🤖 وضعیت ربات تغییر کرد.\n\n"
            f"وضعیت فعلی: {status}",
            reply_markup=admin_keyboard(),
        )

    elif text == "📊 آمار":
        await admin_stats(update, context)

    elif text == "📢 کانال اجباری":
        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_channel"

        current = data["settings"].get("mandatory_channel") or "تنظیم نشده"

        await update.message.reply_text(
            "📢 تنظیم کانال اجباری\n\n"
            f"وضعیت فعلی: {current}\n\n"
            "یوزرنیم کانال را ارسال کنید.\n"
            "مثال:\n@MyChannel\n\n"
            "برای حذف، بنویسید:\nلغو",
            reply_markup=back_keyboard(),
        )

    elif text == "👥 گپ اجباری":
        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_group"

        current = data["settings"].get("mandatory_group") or "تنظیم نشده"

        await update.message.reply_text(
            "👥 تنظیم گپ اجباری\n\n"
            f"وضعیت فعلی: {current}\n\n"
            "یوزرنیم گپ را ارسال کنید.\n"
            "مثال:\n@MyGroup\n\n"
            "برای حذف، بنویسید:\nلغو",
            reply_markup=back_keyboard(),
        )

    elif text == "🔄 انتقال مالکیت":
        if not is_owner(user.id):
            return

        context.user_data.clear()
        context.user_data["state"] = "admin_transfer"

        await update.message.reply_text(
            "🔄 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید.\n\n"
            "مثال:\n123456789\n\n"
            "⚠️ بعد از انتقال، دسترسی پنل مدیریت برای مالک فعلی حذف می‌شود.",
            reply_markup=back_keyboard(),
        )


# =========================
# ADMIN INPUT STATES
# =========================

async def handle_admin_state(update, context):
    user = update.effective_user

    if not is_owner(user.id):
        return False

    text = (update.message.text or "").strip()
    state = context.user_data.get("state")

    if state == "admin_channel":
        if text.lower() == "لغو":
            data["settings"]["mandatory_channel"] = ""
        else:
            data["settings"]["mandatory_channel"] = text

        save_data()
        context.user_data.clear()

        await update.message.reply_text(
            "✅ کانال اجباری ذخیره شد.\n\n"
            f"📢 مقدار: {data['settings']['mandatory_channel'] or 'حذف شد'}",
            reply_markup=admin_keyboard(),
        )
        return True

    if state == "admin_group":
        if text.lower() == "لغو":
            data["settings"]["mandatory_group"] = ""
        else:
            data["settings"]["mandatory_group"] = text

        save_data()
        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد.\n\n"
            f"👥 مقدار: {data['settings']['mandatory_group'] or 'حذف شد'}",
            reply_markup=admin_keyboard(),
        )
        return True

    if state == "admin_transfer":
        if text.lower() == "لغو":
            context.user_data.clear()
            await update.message.reply_text(
                "❌ انتقال مالکیت لغو شد.",
                reply_markup=admin_keyboard(),
            )
            return True

        try:
            new_owner = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد.\nمثال: 123456789"
            )
            return True

        if new_owner <= 0:
            await update.message.reply_text("❌ آیدی نامعتبر است.")
            return True

        if not get_user(new_owner):
            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را استارت نکرده است.\n"
                "ابتدا با آن حساب /start را بزنید."
            )
            return True

        old_owner = data["owner"]
        data["owner"] = new_owner
        save_data()
        context.user_data.clear()

        await update.message.reply_text(
            "✅ مالکیت منتقل شد.\n\n"
            f"👤 مالک جدید: {user_display(new_owner)}",
            reply_markup=main_keyboard(user.id),
        )

        try:
            await context.bot.send_message(
                chat_id=new_owner,
                text="👑 شما به عنوان مالک جدید ربات تعیین شدید."
            )
        except Exception as e:
            print(f"❌ پیام مالک جدید: {e}")

        return True

    return False


# =========================
# MESSAGE ROUTER
# =========================

async def message_handler(update, context):
    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    if update.message.text == "🔙 برگشت":
        await go_home(update, context)
        return

    user = update.effective_user

    # ورودی‌های پنل مالک باید قبل از بررسی عادی پردازش شوند.
    if is_owner(user.id):
        if await handle_admin_state(update, context):
            return

    if not is_owner(user.id):
        if not await mandatory_check(update, context):
            return

    state = context.user_data.get("state")

    if state == "deposit_receipt":
        await handle_deposit_receipt(update, context)
        return

    if state == "deposit_amount":
        await handle_deposit_amount(update, context)
        return

    if state == "withdraw_address":
        await handle_withdraw_address(update, context)
        return

    if state == "withdraw_amount":
        await handle_withdraw_amount(update, context)
        return

    await button_handler(update, context)


# =========================
# CALLBACK ROUTER
# =========================

async def membership_callback(update, context):
    query = update.callback_query
    user = query.from_user

    await query.answer()

    if not is_owner(user.id) and not bot_is_on():
        await query.answer(
            "⛔ ربات خاموش است.",
            show_alert=True
        )
        return

    # پیام را دوباره با /start بازسازی می‌کنیم.
    try:
        await query.message.delete()
    except Exception:
        pass

    fake_context = context
    if not await mandatory_check(
        type(
            "Obj",
            (),
            {
                "effective_user": user,
                "effective_chat": query.message.chat,
                "message": query.message,
            }
        )(),
        fake_context,
    ):
        return

    create_user(user)

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=(
            "🤖 به ربات خوش آمدید.\n\n"
            f"💰 موجودی شما:\n{balance(user.id):,} DOGS\n\n"
            "عضویت تأیید شد."
        ),
        reply_markup=main_keyboard(user.id),
    )


# =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد")
        return

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game|check_membership)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deposit_method_callback,
            pattern=r"^deposit_(ultra|exchange)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(ok_wd_|no_wd_)"
        )
    )

    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
            message_handler
        )
    )

    print("=================================")
    print("✅ BOT STARTED")
    print("🤖 Telegram bot is running...")
    print("=================================")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
