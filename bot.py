import json
import os
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

DATA_FILE = "bot_data.json"

# =========================
# اجباری
# =========================

FORCE_CHANNEL = "@TAK_BE_T"
FORCE_CHANNEL_LINK = "https://t.me/TAK_BE_T"

FORCE_GROUP = "@TAK_B_ET"
FORCE_GROUP_LINK = "https://t.me/TAK_B_ET"

# =========================
# DATA
# =========================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "force_channel": True,
        "force_group": True,
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
                loaded[key] = value

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
# USERS
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


def get_user(uid):
    return data["users"].get(str(uid))


def balance(uid):
    user = get_user(uid)
    if not user:
        return 0
    return int(user.get("balance", 0))


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

    return user.get("name", "") or str(uid)


# =========================
# FORCE JOIN
# =========================

async def check_force_join(bot, user_id):
    settings = data.get("settings", {})

    missing_channel = False
    missing_group = False

    if settings.get("force_channel", True):
        try:
            member = await bot.get_chat_member(
                FORCE_CHANNEL,
                user_id
            )

            if member.status in ("left", "kicked"):
                missing_channel = True

        except Exception as e:
            print("CHANNEL CHECK ERROR:", e)
            missing_channel = True

    if settings.get("force_group", True):
        try:
            member = await bot.get_chat_member(
                FORCE_GROUP,
                user_id
            )

            if member.status in ("left", "kicked"):
                missing_group = True

        except Exception as e:
            print("GROUP CHECK ERROR:", e)
            missing_group = True

    return missing_channel, missing_group


async def force_join_message(update, context):
    buttons = []

    missing_channel, missing_group = await check_force_join(
        context.bot,
        update.effective_user.id
    )

    if missing_channel:
        buttons.append([
            InlineKeyboardButton(
                "📢 عضویت در کانال",
                url=FORCE_CHANNEL_LINK
            )
        ])

    if missing_group:
        buttons.append([
            InlineKeyboardButton(
                "👥 ورود به گپ",
                url=FORCE_GROUP_LINK
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_join"
        )
    ])

    await update.message.reply_text(
        "🔒 برای استفاده از ربات ابتدا باید در موارد زیر عضو شوید:\n\n"
        + (
            "📢 کانال اجباری\n"
            if missing_channel else ""
        )
        + (
            "👥 گپ اجباری\n"
            if missing_group else ""
        )
        + "\nبعد از عضویت روی «بررسی عضویت» بزنید.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# =========================
# KEYBOARD
# =========================

def main_keyboard(uid):
    rows = [
        [
            "💳 واریزی",
            "👥 زیر مجموعه",
        ],
        [
            "👤 پروفایل",
            "💰 برداشت",
        ],
    ]

    if is_owner(uid):
        rows.append([
            "⚙️ پنل مدیریت"
        ])

    rows.append([
        "🎧 پشتیبانی"
    ])

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [["🔙 برگشت"]],
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

    if update.effective_chat.type == "private":

        missing_channel, missing_group = await check_force_join(
            context.bot,
            user.id
        )

        if missing_channel or missing_group:
            await force_join_message(update, context)
            return

        await update.message.reply_text(
            "🤖 به ربات خوش آمدید.\n\n"
            f"👤 {user.first_name}\n\n"
            f"💰 موجودی: {balance(user.id):,} DOGS\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=main_keyboard(user.id)
        )

        return

    await update.message.reply_text(
        "🤖 ربات فعال است.\n\n"
        "🎮 برای بازی بنویسید:\n"
        "بازی 500\n\n"
        f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر بازی: {MAX_GAME:,} DOGS",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================
# JOIN CALLBACK
# =========================

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data != "check_join":
        return

    missing_channel, missing_group = await check_force_join(
        context.bot,
        query.from_user.id
    )

    if missing_channel or missing_group:

        buttons = []

        if missing_channel:
            buttons.append([
                InlineKeyboardButton(
                    "📢 عضویت در کانال",
                    url=FORCE_CHANNEL_LINK
                )
            ])

        if missing_group:
            buttons.append([
                InlineKeyboardButton(
                    "👥 ورود به گپ",
                    url=FORCE_GROUP_LINK
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "✅ بررسی مجدد",
                callback_data="check_join"
            )
        ])

        await query.edit_message_text(
            "❌ هنوز عضویت شما کامل نشده است.\n\n"
            "ابتدا عضو کانال و گپ شوید، سپس بررسی مجدد را بزنید.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return

    await query.edit_message_text(
        "✅ عضویت شما تأیید شد.\n\n"
        "حالا می‌توانید از ربات استفاده کنید."
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
        f"👥 زیرمجموعه‌ها: {profile.get('referrals', 0)}",
        reply_markup=back_keyboard()
    )


# =========================
# REFERRALS
# =========================

async def show_referrals(update, context):

    user = update.effective_user

    bot_info = await context.bot.get_me()

    referral_link = (
        f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    )

    referrals = get_user(user.id).get("referrals", 0)

    await update.message.reply_text(
        "👥 زیرمجموعه‌گیری\n\n"
        "💰 پاداش هر رفرال: 50 DOGS\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"
        f"👥 تعداد زیرمجموعه: {referrals}",
        reply_markup=back_keyboard()
    )


# =========================
# DEPOSIT
# =========================

async def show_deposit(update, context):

    buttons = [
        [
            InlineKeyboardButton(
                "🏦 صرافی",
                callback_data="deposit_exchange"
            )
        ],
        [
            InlineKeyboardButton(
                "⚡ اولترا",
                callback_data="deposit_ultra"
            )
        ],
    ]

    await update.message.reply_text(
        "💳 روش واریز DOGS را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def deposit_method_callback(update, context):

    query = update.callback_query
    await query.answer()

    if query.data == "deposit_ultra":

        await query.edit_message_text(
            "⚡ واریز از اولترا\n\n"
            f"👤 به این آیدی DOGS را بزنید:\n"
            f"{SUPPORT_USERNAME}\n\n"
            "📸 بعد از واریز شات خود را ارسال کنید.\n"
            "💰 سپس مقدار DOGS را ارسال کنید.\n\n"
            f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
            "⚠️ اگر مقدار واردشده درست نباشد، درخواست توسط مالک رد می‌شود."
        )

    elif query.data == "deposit_exchange":

        await query.edit_message_text(
            "🏦 واریز از صرافی\n\n"
            "💎 آدرس DOGS:\n"
            f"{DOGS_WALLET}\n\n"
            "📸 شات یا لینک هش تراکنش را ارسال کنید.\n"
            "💰 سپس مقدار DOGS را ارسال کنید.\n\n"
            f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
            "⚠️ اگر مقدار واردشده درست نباشد، درخواست توسط مالک رد می‌شود."
        )


# =========================
# SUPPORT
# =========================

async def show_support(update, context):

    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        f"{SUPPORT_USERNAME}",
        reply_markup=back_keyboard()
    )


# =========================
# WITHDRAW
# =========================

async def show_withdraw(update, context):

    user = update.effective_user
    current = balance(user.id)

    await update.message.reply_text(
        "💰 برداشت DOGS\n\n"
        f"💳 موجودی شما: {current:,} DOGS\n"
        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "برای ثبت برداشت با پشتیبانی تماس بگیرید.",
        reply_markup=back_keyboard()
    )


# =========================
# HOME
# =========================

async def go_home(update, context):

    user = update.effective_user

    await update.message.reply_text(
        "🏠 منوی اصلی\n\n"
        f"💰 موجودی: {balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id)
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update, context):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    text = update.message.text
    user = update.effective_user

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

        if is_owner(user.id):

            bot_status = data["settings"].get("bot", True)
            channel_status = data["settings"].get("force_channel", True)
            group_status = data["settings"].get("force_group", True)

            await update.message.reply_text(
                "⚙️ پنل مدیریت\n\n"
                f"🤖 ربات: {'🟢 روشن' if bot_status else '🔴 خاموش'}\n"
                f"📢 کانال اجباری: {'🟢 فعال' if channel_status else '🔴 خاموش'}\n"
                f"👥 گپ اجباری: {'🟢 فعال' if group_status else '🔴 خاموش'}\n\n"
                f"👤 کاربران: {len(data['users'])}\n"
                f"💳 واریزی‌ها: {len(data['deposits'])}\n"
                f"💰 برداشت‌ها: {len(data['withdraws'])}",
                reply_markup=back_keyboard()
            )


# =========================
# GAME
# =========================

ACTIVE_GAMES = {}


async def game_command(update, context):

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "❌ بازی فقط داخل گروه قابل انجام است."
        )
        return

    user = update.effective_user
    create_user(user)

    try:
        amount = int(update.message.text.split()[1])
    except Exception:
        await update.message.reply_text(
            "❌ مثال صحیح:\nبازی 500"
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

    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_GAMES:
        await update.message.reply_text(
            "❌ در این گپ یک بازی فعال است."
        )
        return

    if balance(user.id) < amount:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست.\n"
            f"💰 موجودی: {balance(user.id):,} DOGS"
        )
        return

    remove_balance(user.id, amount)

    ACTIVE_GAMES[chat_id] = {
        "creator": user.id,
        "amount": amount,
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 ورود به بازی",
                callback_data="join_game"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو بازی",
                callback_data="cancel_game"
            )
        ],
    ])

    await update.message.reply_text(
        "🎮 بازی ساخته شد\n\n"
        f"👤 سازنده: {user_display(user.id)}\n"
        f"💰 شرط: {amount:,} DOGS\n\n"
        "👥 نفر دوم وارد شود.",
        reply_markup=keyboard
    )


async def game_callback(update, context):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat_id = query.message.chat.id

    if chat_id not in ACTIVE_GAMES:
        await query.answer(
            "❌ بازی تمام شده.",
            show_alert=True
        )
        return

    game = ACTIVE_GAMES[chat_id]

    if query.data == "cancel_game":

        if user.id != game["creator"]:
            await query.answer(
                "❌ فقط سازنده می‌تواند لغو کند.",
                show_alert=True
            )
            return

        add_balance(
            user.id,
            game["amount"]
        )

        del ACTIVE_GAMES[chat_id]

        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"{game['amount']:,} DOGS برگشت داده شد."
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

        remove_balance(user.id, amount)

        winner = game["creator"] if __import__("random").choice([True, False]) else user.id
        loser = user.id if winner == game["creator"] else game["creator"]

        prize = amount * 2

        add_balance(winner, prize)

        del ACTIVE_GAMES[chat_id]

        await query.edit_message_text(
            "🎮 نتیجه بازی\n\n"
            f"🏆 برنده: {user_display(winner)}\n\n"
            f"💰 جایزه: {prize:,} DOGS\n\n"
            f"😢 بازنده: {user_display(loser)}"
        )


# =========================
# MESSAGE ROUTER
# =========================

async def message_router(update, context):

    if not update.message:
        return

    if update.effective_chat.type == "private":

        if not is_owner(update.effective_user.id):

            missing_channel, missing_group = await check_force_join(
                context.bot,
                update.effective_user.id
            )

            if missing_channel or missing_group:
                await force_join_message(update, context)
                return

        await button_handler(update, context)


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
            filters.TEXT
            & filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            join_callback,
            pattern=r"^check_join$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deposit_method_callback,
            pattern=r"^deposit_(exchange|ultra)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_router
        )
    )

    print("==============================")
    print("✅ BOT STARTED")
    print("==============================")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
