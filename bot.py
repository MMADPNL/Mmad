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

# فعلاً کارمزد بازی صفر است
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
        "bot": True
    }
}


def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

        for key, value in DEFAULT_DATA.items():

            if key not in loaded:
                loaded[key] = value

        return loaded

    except Exception:

        return DEFAULT_DATA.copy()


data = load_data()


def save_data():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


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

            "date": datetime.now().isoformat()

        }

    else:

        data["users"][uid]["name"] = (
            user.first_name or ""
        )

        data["users"][uid]["username"] = (
            user.username or ""
        )

    save_data()

    return data["users"][uid]


def get_user(uid):

    return data["users"].get(
        str(uid)
    )


def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    return int(
        user.get(
            "balance",
            0
        )
    )


def add_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    user["balance"] = (
        int(user.get("balance", 0))
        + int(amount)
    )

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

    return int(uid) == int(
        data.get(
            "owner",
            OWNER_ID
        )
    )


def user_display(uid):

    user = get_user(uid)

    if not user:
        return str(uid)

    username = user.get(
        "username",
        ""
    )

    if username:
        return f"@{username}"

    name = user.get(
        "name",
        ""
    )

    if name:
        return name

    return str(uid)


# =========================
# PRIVATE KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [

        [
            "💳 واریزی",
            "👥 زیر مجموعه"
        ],

        [
            "👤 پروفایل",
            "💰 برداشت"
        ]

    ]

    if is_owner(uid):

        rows.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )

    rows.append(
        [
            "🎧 پشتیبانی"
        ]
    )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                "🔙 برگشت"
            ]
        ],
        resize_keyboard=True
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data.clear()

    chat_type = update.effective_chat.type

    # =========================
    # PRIVATE
    # =========================

    if chat_type == "private":

        await update.message.reply_text(

            "🤖 به ربات خوش آمدید.\n\n"

            f"👤 {user.first_name}\n\n"

            f"💰 موجودی شما:\n"
            f"{balance(user.id):,} DOGS\n\n"

            "یکی از گزینه‌های زیر را انتخاب کنید:",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return

    # =========================
    # GROUP
    # =========================

    await update.message.reply_text(

        "🤖 ربات فعال است.\n\n"

        "🎮 برای شروع بازی در گروه بنویسید:\n"
        "بازی 500\n\n"

        f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر بازی: {MAX_GAME:,} DOGS",

        reply_markup=ReplyKeyboardRemove()

    )


# =========================
# PROFILE
# =========================

async def show_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    profile = get_user(user.id)

    username = profile.get(
        "username",
        ""
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

    referrals = int(
        profile.get(
            "referrals",
            0
        )
    )

    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: "
        f"{profile.get('name', '')}\n"

        f"🔹 یوزرنیم: "
        f"{username_text}\n\n"

        f"💰 موجودی: "
        f"{balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه‌ها: "
        f"{referrals}",

        reply_markup=back_keyboard()

    )


# =========================
# REFERRALS
# =========================

async def show_referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    bot_username = context.bot.username

    referral_link = (
        f"https://t.me/{bot_username}?start=ref_{user.id}"
    )

    referrals = int(
        get_user(user.id).get(
            "referrals",
            0
        )
    )

    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"

        f"👥 تعداد زیرمجموعه‌ها: "
        f"{referrals}\n\n"

        "📢 لینک بالا را برای دوستان خود ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================
# DEPOSIT
# =========================

async def show_deposit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    context.user_data["state"] = (
        "deposit_receipt"
    )

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"

        "💎 آدرس کیف پول:\n\n"

        f"{DOGS_WALLET}\n\n"

        f"🔻 حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "1️⃣ ابتدا DOGS را به آدرس بالا واریز کنید.\n\n"

        "2️⃣ سپس عکس رسید یا لینک تراکنش را ارسال کنید.\n\n"

        "3️⃣ بعد مقدار DOGS را ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================
# DEPOSIT RECEIPT
# =========================

async def handle_deposit_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.message.photo:

        photo = update.message.photo[-1]

        context.user_data["receipt"] = (
            f"📸 رسید تصویری\n"
            f"File ID: {photo.file_id}"
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

    context.user_data["state"] = (
        "deposit_amount"
    )

    await update.message.reply_text(

        "✅ رسید دریافت شد.\n\n"

        "💰 حالا مقدار DOGS واریزی را ارسال کنید.\n\n"

        f"🔻 حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()

    )


# =========================
# DEPOSIT AMOUNT
# =========================

async def handle_deposit_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار DOGS را به صورت عدد ارسال کنید."
        )

        return

    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید.\n\n"
            "مثال:\n"
            "5000"
        )

        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است.\n\n"

            f"💰 مبلغ واردشده: "
            f"{amount:,} DOGS"

        )

        return

    receipt = context.user_data.get(
        "receipt",
        "بدون رسید"
    )

    request_id = (
        f"{user.id}_{int(datetime.now().timestamp())}"
    )

    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "receipt": receipt,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "⏳ درخواست برای مالک ارسال شد.\n"
        "پس از تأیید، موجودی شما افزایش پیدا می‌کند.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: "
        f"{user.first_name or 'بدون نام'}\n"

        f"🆔 آیدی: "
        f"{user.id}\n"

        f"🔹 یوزرنیم: "
        f"{username}\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"📝 رسید:\n"
        f"{receipt}\n\n"

        f"🆔 شناسه:\n"
        f"{request_id}"

    )

    keyboard = InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"ok_dep_{request_id}"
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"no_dep_{request_id}"
                )

            ]

        ]

    )

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=owner_text,

            reply_markup=keyboard

        )

    except Exception as e:

        print(
            f"❌ خطا در ارسال واریزی: {e}"
        )


# =========================
# WITHDRAW
# =========================

async def show_withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    current = balance(user.id)

    if current < MIN_WITHDRAW:

        await update.message.reply_text(

            "💰 برداشت DOGS\n\n"

            f"💳 موجودی شما: "
            f"{current:,} DOGS\n\n"

            f"❌ حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS",

            reply_markup=back_keyboard()

        )

        return

    context.user_data.clear()

    context.user_data["state"] = (
        "withdraw_address"
    )

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        f"💳 موجودی شما: "
        f"{current:,} DOGS\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "1️⃣ آدرس کیف پول DOGS خود را ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================
# WITHDRAW ADDRESS
# =========================

async def handle_withdraw_address(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    context.user_data["state"] = (
        "withdraw_amount"
    )

    await update.message.reply_text(

        "✅ آدرس دریافت شد.\n\n"

        f"💳 آدرس:\n{address}\n\n"

        "2️⃣ مقدار DOGS برای برداشت را ارسال کنید.\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "مثال:\n"
        "10000",

        reply_markup=back_keyboard()

    )


# =========================
# WITHDRAW AMOUNT
# =========================

async def handle_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار برداشت را به صورت عدد ارسال کنید."
        )

        return

    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )

        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."

        )

        return

    if balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💳 موجودی: "
            f"{balance(user.id):,} DOGS\n"

            f"💰 برداشت: "
            f"{amount:,} DOGS"

        )

        return

    address = context.user_data.get(
        "withdraw_address"
    )

    if not address:

        context.user_data["state"] = (
            "withdraw_address"
        )

        await update.message.reply_text(
            "❌ آدرس پیدا نشد.\n"
            "دوباره آدرس کیف پول را ارسال کنید."
        )

        return

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return

    request_id = (
        f"{user.id}_{int(datetime.now().timestamp())}"
    )

    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "address": address,

        "amount": amount,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    new_balance = balance(
        user.id
    )

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس:\n"
        f"{address}\n\n"

        f"💰 موجودی جدید: "
        f"{new_balance:,} DOGS\n\n"

        "⏳ درخواست برای مالک ارسال شد.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (

        "💰 درخواست برداشت جدید\n\n"

        f"👤 نام: "
        f"{user.first_name or 'بدون نام'}\n"

        f"🆔 آیدی: "
        f"{user.id}\n"

        f"🔹 یوزرنیم: "
        f"{username}\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس:\n"
        f"{address}\n\n"

        f"💰 موجودی فعلی: "
        f"{new_balance:,} DOGS\n\n"

        f"🆔 شناسه:\n"
        f"{request_id}"

    )

    keyboard = InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"ok_wd_{request_id}"
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"no_wd_{request_id}"
                )

            ]

        ]

    )

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=owner_text,

            reply_markup=keyboard

        )

    except Exception as e:

        print(
            f"❌ خطا در ارسال برداشت: {e}"
        )

        add_balance(
            user.id,
            amount
        )

        if request_id in data["withdraws"]:

            data["withdraws"][request_id]["status"] = (
                "failed"
            )

            save_data()


# =========================
# SUPPORT
# =========================

async def show_support(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "برای ارتباط با پشتیبانی:\n\n"

        f"👤 {SUPPORT_USERNAME}",

        reply_markup=back_keyboard()

    )


# =========================
# HOME
# =========================

async def go_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(

        "🏠 منوی اصلی\n\n"

        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌های زیر را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================
# GAME SYSTEM
# =========================

ACTIVE_GAMES = {}


async def game_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    # فقط گروه
    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گروه قابل انجام است."
        )

        return

    create_user(user)

    try:

        parts = update.message.text.strip().split()

        if len(parts) != 2:
            raise ValueError

        amount = int(parts[1])

    except (ValueError, IndexError):

        await update.message.reply_text(

            "❌ فرمت اشتباه است.\n\n"

            "مثال:\n"
            "بازی 500"

        )

        return

    if amount < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل شرط بازی "
            f"{MIN_GAME:,} DOGS است."

        )

        return

    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر شرط بازی "
            f"{MAX_GAME:,} DOGS است."

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

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS"

        )

        return

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return

    ACTIVE_GAMES[chat_id] = {

        "creator": user.id,

        "amount": amount,

        "created_at": datetime.now().isoformat()

    }

    keyboard = InlineKeyboardMarkup(

        [

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

            ]

        ]

    )

    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"

        f"👤 سازنده: "
        f"{user_display(user.id)}\n\n"

        f"💰 شرط: "
        f"{amount:,} DOGS\n\n"

        "👥 فقط یک نفر می‌تواند وارد بازی شود.",

        reply_markup=keyboard

    )


# =========================
# GAME CALLBACK
# =========================

async def game_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    chat_id = query.message.chat.id

    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True
        )

        return

    game = ACTIVE_GAMES[chat_id]

    # =========================
    # CANCEL
    # =========================

    if query.data == "cancel_game":

        if user.id != game["creator"]:

            await query.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
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

            f"💰 مبلغ "
            f"{game['amount']:,} DOGS "
            "به سازنده برگشت داده شد."

        )

        return

    # =========================
    # JOIN
    # =========================

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

        if not remove_balance(
            user.id,
            amount
        ):

            await query.answer(
                "❌ خطا در کسر موجودی.",
                show_alert=True
            )

            return

        winner = random.choice(
            [
                game["creator"],
                user.id
            ]
        )

        if winner == game["creator"]:

            loser = user.id

        else:

            loser = game["creator"]

        total_pot = amount * 2

        prize = total_pot - GAME_FEE

        add_balance(
            winner,
            prize
        )

        if GAME_FEE > 0:

            if not get_user(OWNER_ID):

                data["users"][str(OWNER_ID)] = {

                    "id": OWNER_ID,

                    "name": "OWNER",

                    "username": "",

                    "balance": 0,

                    "referrals": 0,

                    "referred_by": None,

                    "date": datetime.now().isoformat()

                }

                save_data()

            add_balance(
                OWNER_ID,
                GAME_FEE
            )

        del ACTIVE_GAMES[chat_id]

        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"🏆 برنده: "
            f"{user_display(winner)}\n\n"

            f"💰 جایزه: "
            f"{prize:,} DOGS\n\n"

            f"😢 بازنده: "
            f"{user_display(loser)}"

        )

        return


# =========================
# ADMIN DEPOSIT CALLBACK
# =========================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if not is_owner(query.from_user.id):

        return

    if query.data.startswith("ok_dep_"):

        request_id = query.data[len("ok_dep_"):]

        request = data["deposits"].get(
            request_id
        )

        if not request:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return

        if request["status"] != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        uid = request["user_id"]

        add_balance(
            uid,
            request["amount"]
        )

        request["status"] = "approved"

        request["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(

            "✅ واریز تأیید شد.\n\n"

            f"👤 کاربر: {user_display(uid)}\n"

            f"💰 مبلغ: "
            f"{request['amount']:,} DOGS"

        )

        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز شما تأیید شد.\n\n"

                    f"💰 مبلغ اضافه‌شده: "
                    f"{request['amount']:,} DOGS\n\n"

                    f"💳 موجودی جدید: "
                    f"{balance(uid):,} DOGS"

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام تأیید واریز: {e}"
            )

        return

    if query.data.startswith("no_dep_"):

        request_id = query.data[len("no_dep_"):]

        request = data["deposits"].get(
            request_id
        )

        if not request:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return

        if request["status"] != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(

            "❌ واریز رد شد.\n\n"

            f"👤 کاربر: "
            f"{user_display(request['user_id'])}\n"

            f"💰 مبلغ: "
            f"{request['amount']:,} DOGS"

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

            print(
                f"❌ ارسال پیام رد واریز: {e}"
            )


# =========================
# ADMIN WITHDRAW CALLBACK
# =========================

async def admin_withdraw_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if not is_owner(query.from_user.id):

        return

    if query.data.startswith("ok_wd_"):

        request_id = query.data[len("ok_wd_"):]

        request = data["withdraws"].get(
            request_id
        )

        if not request:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return

        if request["status"] != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        request["status"] = "approved"

        request["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(

            "✅ برداشت تأیید شد.\n\n"

            f"👤 کاربر: "
            f"{user_display(request['user_id'])}\n\n"

            f"💰 مبلغ: "
            f"{request['amount']:,} DOGS\n\n"

            f"💳 آدرس:\n"
            f"{request['address']}"

        )

        try:

            await context.bot.send_message(

                chat_id=request["user_id"],

                text=(

                    "✅ درخواست برداشت شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{request['amount']:,} DOGS\n\n"

                    "پرداخت توسط مالک بررسی و تأیید شد."

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام تأیید برداشت: {e}"
            )

        return

    if query.data.startswith("no_wd_"):

        request_id = query.data[len("no_wd_"):]

        request = data["withdraws"].get(
            request_id
        )

        if not request:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return

        if request["status"] != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        # برگشت پول به کاربر
        add_balance(
            request["user_id"],
            request["amount"]
        )

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(

            "❌ برداشت رد شد.\n\n"

            f"👤 کاربر: "
            f"{user_display(request['user_id'])}\n\n"

            f"💰 مبلغ برگشت داده شد: "
            f"{request['amount']:,} DOGS"

        )

        try:

            await context.bot.send_message(

                chat_id=request["user_id"],

                text=(

                    "❌ درخواست برداشت شما رد شد.\n\n"

                    f"💰 مبلغ "
                    f"{request['amount']:,} DOGS "
                    "به موجودی شما برگشت داده شد.\n\n"

                    f"💳 موجودی جدید: "
                    f"{balance(request['user_id']):,} DOGS"

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام رد برداشت: {e}"
            )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    text = update.message.text

    if text == "👤 پروفایل":

        await show_profile(
            update,
            context
        )

    elif text == "👥 زیر مجموعه":

        await show_referrals(
            update,
            context
        )

    elif text == "💳 واریزی":

        await show_deposit(
            update,
            context
        )

    elif text == "💰 برداشت":

        await show_withdraw(
            update,
            context
        )

    elif text == "🎧 پشتیبانی":

        await show_support(
            update,
            context
        )

    elif text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

    elif text == "⚙️ پنل مدیریت":

        if is_owner(
            update.effective_user.id
        ):

            await update.message.reply_text(

                "⚙️ پنل مدیریت\n\n"

                f"👥 تعداد کاربران: "
                f"{len(data['users'])}\n\n"

                f"💳 واریزی‌ها: "
                f"{len(data['deposits'])}\n\n"

                f"💰 برداشت‌ها: "
                f"{len(data['withdraws'])}",

                reply_markup=back_keyboard()

            )


# =========================
# MESSAGE ROUTER
# =========================

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    # =========================
    # PRIVATE ONLY
    # =========================

    if update.effective_chat.type != "private":
        return

    state = context.user_data.get(
        "state"
    )

    # =========================
    # BACK
    # =========================

    if update.message.text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

        return

    # =========================
    # DEPOSIT
    # =========================

    if state == "deposit_receipt":

        await handle_deposit_receipt(
            update,
            context
        )

        return

    if state == "deposit_amount":

        await handle_deposit_amount(
            update,
            context
        )

        return

    # =========================
    # WITHDRAW
    # =========================

    if state == "withdraw_address":

        await handle_withdraw_address(
            update,
            context
        )

        return

    if state == "withdraw_amount":

        await handle_withdraw_amount(
            update,
            context
        )

        return

    # =========================
    # NORMAL BUTTONS
    # =========================

    await button_handler(
        update,
        context
    )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN پیدا نشد"
        )

        return

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =========================
    # START
    # =========================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # =========================
    # GAME
    # فقط گروه
    # =========================

    app.add_handler(
        MessageHandler(

            filters.TEXT
            & filters.Regex(
                r"^بازی\s+\d+$"
            ),

            game_command

        )
    )

    # =========================
    # GAME BUTTONS
    # =========================

    app.add_handler(
        CallbackQueryHandler(

            game_callback,

            pattern=r"^(join_game|cancel_game)$"

        )
    )

    # =========================
    # DEPOSIT ADMIN
    # =========================

    app.add_handler(
        CallbackQueryHandler(

            admin_callback,

            pattern=r"^(ok_dep_|no_dep_)"

        )
    )

    # =========================
    # WITHDRAW ADMIN
    # =========================

    app.add_handler(
        CallbackQueryHandler(

            admin_withdraw_callback,

            pattern=r"^(ok_wd_|no_wd_)"

        )
    )

    # =========================
    # PRIVATE TEXT + PHOTO
    # =========================

    app.add_handler(
        MessageHandler(

            (
                filters.TEXT
                |
                filters.PHOTO
            )
            & ~filters.COMMAND,

            message_handler

        )
    )

    print(
        "================================="
    )

    print(
        "✅ BOT STARTED"
    )

    print(
        "🤖 Telegram bot is running..."
    )

    print(
        "================================="
    )

    app.run_polling(
        drop_pending_updates=True
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":

    main()
