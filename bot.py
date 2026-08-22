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


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

# اولترا
ULTRA_USERNAME = "@CyyFr"

# صرافی
EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

# حداقل واریز
MIN_DEPOSIT = 5000

# حداقل برداشت
MIN_WITHDRAW = 10000

# بازی
MIN_GAME = 500
MAX_GAME = 20000

# رفرال
REFERRAL_REWARD = 50

# فایل اطلاعات
DATA_FILE = "bot_data.json"

# =========================================================
# اجباری
# =========================================================
# اگر نمی‌خواهی اجباری باشد خالی بگذار:
#
# مثال کانال:
# FORCE_CHANNEL = "@YourChannel"
#
# مثال گپ:
# FORCE_GROUP = "@YourGroup"

FORCE_CHANNEL = ""
FORCE_GROUP = ""


# =========================================================
# DATABASE
# =========================================================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "settings": {
        "bot": True,
        "force_channel": FORCE_CHANNEL,
        "force_group": FORCE_GROUP,
    },
    "owner": OWNER_ID,
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

        if "settings" not in loaded:
            loaded["settings"] = {}

        if "bot" not in loaded["settings"]:
            loaded["settings"]["bot"] = True

        if "force_channel" not in loaded["settings"]:
            loaded["settings"]["force_channel"] = FORCE_CHANNEL

        if "force_group" not in loaded["settings"]:
            loaded["settings"]["force_group"] = FORCE_GROUP

        return loaded

    except Exception as e:

        print("❌ خطا در خواندن دیتابیس:", e)

        return DEFAULT_DATA.copy()


data = load_data()


def save_data():

    try:

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

    except Exception as e:

        print("❌ خطا در ذخیره دیتابیس:", e)


# =========================================================
# USER SYSTEM
# =========================================================

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

            "referral_reward_received": False,

            "date": datetime.now().isoformat(),

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

    return data["users"].get(str(uid))


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


# =========================================================
# BOT STATUS
# =========================================================

def bot_is_on():

    return bool(
        data.get(
            "settings",
            {}
        ).get(
            "bot",
            True
        )
    )


# =========================================================
# FORCE JOIN
# =========================================================

async def check_membership(
    update,
    context
):

    user = update.effective_user

    if not user:
        return True

    if is_owner(user.id):
        return True

    settings = data.get(
        "settings",
        {}
    )

    channel = settings.get(
        "force_channel",
        ""
    )

    group = settings.get(
        "force_group",
        ""
    )

    missing = []

    for chat in [channel, group]:

        if not chat:
            continue

        try:

            member = await context.bot.get_chat_member(
                chat_id=chat,
                user_id=user.id
            )

            if member.status in [
                "left",
                "kicked"
            ]:

                missing.append(chat)

        except Exception:

            # اگر اجباری تنظیم شده ولی ربات دسترسی ندارد
            # فعلاً کاربر را رد می‌کنیم
            missing.append(chat)

    if not missing:
        return True

    buttons = []

    for item in missing:

        clean = str(item).replace("@", "")

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📢 عضویت در {item}",
                    url=f"https://t.me/{clean}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔄 بررسی عضویت",
                callback_data="check_join"
            )
        ]
    )

    text = (
        "🚫 برای استفاده از ربات ابتدا باید "
        "در موارد زیر عضو شوید:\n\n"
        "بعد از عضویت روی «بررسی عضویت» بزنید."
    )

    if update.message:

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):

    rows = [

        [
            "💳 واریزی",
            "👥 زیر مجموعه"
        ],

        [
            "👤 پروفایل",
            "💰 برداشت"
        ],

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


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    # -----------------------------------------
    # REFERRAL
    # -----------------------------------------

    if context.args:

        arg = context.args[0]

        if arg.startswith("ref_"):

            try:

                ref_id = int(
                    arg.replace(
                        "ref_",
                        ""
                    )
                )

                if (
                    ref_id != user.id
                    and get_user(ref_id)
                ):

                    current_user = get_user(
                        user.id
                    )

                    if (
                        current_user.get(
                            "referred_by"
                        ) is None
                    ):

                        current_user[
                            "referred_by"
                        ] = ref_id

                        ref_user = get_user(
                            ref_id
                        )

                        ref_user[
                            "referrals"
                        ] = int(
                            ref_user.get(
                                "referrals",
                                0
                            )
                        ) + 1

                        add_balance(
                            ref_id,
                            REFERRAL_REWARD
                        )

                        save_data()

                        try:

                            await context.bot.send_message(

                                chat_id=ref_id,

                                text=(

                                    "🎉 زیرمجموعه جدید!\n\n"

                                    f"👤 کاربر: "
                                    f"{user_display(user.id)}\n\n"

                                    f"💰 پاداش رفرال: "
                                    f"{REFERRAL_REWARD:,} DOGS\n\n"

                                    f"💳 موجودی جدید: "
                                    f"{balance(ref_id):,} DOGS"

                                )

                            )

                        except Exception:
                            pass

            except Exception:
                pass

    context.user_data.clear()

    # -----------------------------------------
    # BOT OFF
    # -----------------------------------------

    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )

        return

    # -----------------------------------------
    # FORCE JOIN
    # -----------------------------------------

    if not await check_membership(
        update,
        context
    ):

        return

    # -----------------------------------------
    # PRIVATE
    # -----------------------------------------

    if update.effective_chat.type == "private":

        await update.message.reply_text(

            "🤖 به ربات خوش آمدید.\n\n"

            f"👤 {user.first_name}\n\n"

            f"💰 موجودی:\n"
            f"{balance(user.id):,} DOGS\n\n"

            "یکی از گزینه‌های زیر را انتخاب کنید:",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return

    # -----------------------------------------
    # GROUP
    # -----------------------------------------

    await update.message.reply_text(

        "🤖 ربات فعال است.\n\n"

        "🎮 برای ساخت بازی بنویسید:\n"
        "بازی 500\n\n"

        f"💰 حداقل بازی: "
        f"{MIN_GAME:,} DOGS\n"

        f"💰 حداکثر بازی: "
        f"{MAX_GAME:,} DOGS",

        reply_markup=ReplyKeyboardRemove()

    )


# =========================================================
# PROFILE
# =========================================================

async def show_profile(
    update,
    context
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

    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: "
        f"{profile.get('name', '')}\n"

        f"🔹 یوزرنیم: "
        f"{username_text}\n\n"

        f"💰 موجودی: "
        f"{balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{profile.get('referrals', 0)}\n\n"

        f"🎁 پاداش هر رفرال: "
        f"{REFERRAL_REWARD:,} DOGS",

        reply_markup=back_keyboard()

    )


# =========================================================
# REFERRALS
# =========================================================

async def show_referrals(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    bot_username = context.bot.username

    referral_link = (
        f"https://t.me/{bot_username}"
        f"?start=ref_{user.id}"
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

        f"👥 تعداد رفرال‌ها: "
        f"{referrals}\n\n"

        f"🎁 پاداش هر رفرال: "
        f"{REFERRAL_REWARD:,} DOGS\n\n"

        "📢 لینک بالا را برای دوستان خود ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT MENU
# =========================================================

async def show_deposit(
    update,
    context
):

    context.user_data.clear()

    keyboard = InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    "🔵 اولترا",
                    callback_data="deposit_ultra"
                ),

                InlineKeyboardButton(
                    "🟢 صرافی",
                    callback_data="deposit_exchange"
                )

            ]

        ]

    )

    await update.message.reply_text(

        "💳 روش واریز را انتخاب کنید:",

        reply_markup=keyboard

    )


# =========================================================
# DEPOSIT METHOD CALLBACK
# =========================================================

async def deposit_method_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if query.data == "deposit_ultra":

        context.user_data.clear()

        context.user_data["state"] = (
            "deposit_receipt"
        )

        context.user_data[
            "deposit_method"
        ] = "اولترا"

        await query.edit_message_text(

            "🔵 واریز اولترا\n\n"

            "👤 آیدی اولترا:\n"
            f"{ULTRA_USERNAME}\n\n"

            "💎 به این آیدی DOGS را بزنید.\n\n"

            "📸 بعد از واریز شات خود را ارسال کنید.\n"

            "💰 بعد مقدار DOGS را ارسال کنید.\n\n"

            f"🔻 حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS\n\n"

            "⚠️ اگر مقدار اعلام‌شده درست نباشد، "
            "درخواست توسط مالک رد می‌شود."

        )

        return

    if query.data == "deposit_exchange":

        context.user_data.clear()

        context.user_data["state"] = (
            "deposit_receipt"
        )

        context.user_data[
            "deposit_method"
        ] = "صرافی"

        await query.edit_message_text(

            "🟢 واریز صرافی\n\n"

            "💎 آدرس کیف پول:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            "💰 DOGS را به این ولت واریز کنید.\n\n"

            "📸 بعد از واریز یکی از موارد زیر را ارسال کنید:\n"

            "• شات تراکنش\n"
            "• لینک هش تراکنش\n\n"

            "💰 سپس مقدار DOGS را ارسال کنید.\n\n"

            f"🔻 حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS\n\n"

            "⚠️ اگر مقدار اعلام‌شده با تراکنش واقعی "
            "مطابقت نداشته باشد، درخواست رد می‌شود."

        )

        return


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

async def handle_deposit_receipt(
    update,
    context
):

    if update.message.photo:

        photo = update.message.photo[-1]

        context.user_data["receipt"] = (
            f"📸 شات تصویری\n"
            f"File ID: {photo.file_id}"
        )

    elif update.message.text:

        text = update.message.text.strip()

        if not text:

            await update.message.reply_text(
                "❌ شات یا لینک هش تراکنش را ارسال کنید."
            )

            return

        context.user_data["receipt"] = text

    else:

        await update.message.reply_text(
            "❌ شات یا لینک هش تراکنش را ارسال کنید."
        )

        return

    context.user_data["state"] = (
        "deposit_amount"
    )

    await update.message.reply_text(

        "✅ رسید دریافت شد.\n\n"

        "💰 حالا مقدار DOGS واریزی را ارسال کنید.\n\n"

        f"🔻 حداقل: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def handle_deposit_amount(
    update,
    context
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار را به صورت عدد ارسال کنید."
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

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."

        )

        return

    receipt = context.user_data.get(
        "receipt",
        "بدون رسید"
    )

    method = context.user_data.get(
        "deposit_method",
        "نامشخص"
    )

    request_id = (
        f"dep_{user.id}_"
        f"{int(datetime.now().timestamp())}"
    )

    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "method": method,

        "amount": amount,

        "receipt": receipt,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💳 روش: {method}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "⏳ برای مالک ارسال شد.\n"
        "بعد از تأیید، موجودی افزایش پیدا می‌کند.",

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

        f"💳 روش: {method}\n"

        f"💰 مبلغ اعلام‌شده: "
        f"{amount:,} DOGS\n\n"

        f"📝 رسید / هش:\n"
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
            "❌ خطا در ارسال واریزی:",
            e
        )


# =========================================================
# WITHDRAW
# =========================================================

async def show_withdraw(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    current = balance(user.id)

    if current < MIN_WITHDRAW:

        await update.message.reply_text(

            "💰 برداشت DOGS\n\n"

            f"💳 موجودی: "
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

        f"💳 موجودی: "
        f"{current:,} DOGS\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "آدرس کیف پول DOGS را ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

async def handle_withdraw_address(
    update,
    context
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

    context.user_data[
        "withdraw_address"
    ] = address

    context.user_data["state"] = (
        "withdraw_amount"
    )

    await update.message.reply_text(

        "✅ آدرس دریافت شد.\n\n"

        "💰 مقدار DOGS برداشت را ارسال کنید.\n\n"

        f"🔻 حداقل: "
        f"{MIN_WITHDRAW:,} DOGS",

        reply_markup=back_keyboard()

    )


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

async def handle_withdraw_amount(
    update,
    context
):

    user = update.effective_user

    try:

        amount = int(
            update.message.text.strip()
        )

    except Exception:

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
            f"{balance(user.id):,} DOGS"

        )

        return

    address = context.user_data.get(
        "withdraw_address"
    )

    if not address:
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
        f"wd_{user.id}_"
        f"{int(datetime.now().timestamp())}"
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

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "⏳ برای مالک ارسال شد.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    owner_text = (

        "💰 برداشت جدید\n\n"

        f"👤 نام: "
        f"{user.first_name or 'بدون نام'}\n"

        f"🆔 آیدی: "
        f"{user.id}\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس:\n"
        f"{address}\n\n"

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
            "❌ خطا در ارسال برداشت:",
            e
        )

        add_balance(
            user.id,
            amount
        )

        data["withdraws"][
            request_id
        ]["status"] = "failed"

        save_data()


# =========================================================
# SUPPORT
# =========================================================

async def show_support(
    update,
    context
):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        f"👤 {SUPPORT_USERNAME}",

        reply_markup=back_keyboard()

    )


# =========================================================
# HOME
# =========================================================

async def go_home(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(

        "🏠 منوی اصلی\n\n"

        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# GAME
# =========================================================

ACTIVE_GAMES = {}


async def game_command(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گروه است."
        )

        return

    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )

        return

    if not await check_membership(
        update,
        context
    ):

        return

    create_user(user)

    try:

        parts = update.message.text.split()

        if len(parts) != 2:
            raise ValueError

        amount = int(parts[1])

    except Exception:

        await update.message.reply_text(

            "❌ فرمت اشتباه.\n\n"
            "مثال:\n"
            "بازی 500"

        )

        return

    if amount < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل شرط "
            f"{MIN_GAME:,} DOGS است."

        )

        return

    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر شرط "
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

            f"💰 موجودی: "
            f"{balance(user.id):,} DOGS"

        )

        return

    if not remove_balance(
        user.id,
        amount
    ):

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

        "👥 نفر دوم روی ورود به بازی بزند.",

        reply_markup=keyboard

    )


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    chat_id = query.message.chat.id

    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ بازی دیگر فعال نیست.",
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

            f"💰 مبلغ "
            f"{game['amount']:,} DOGS "
            "برگشت داده شد."

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

        prize = amount * 2

        add_balance(
            winner,
            prize
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


# =========================================================
# ADMIN DEPOSIT CALLBACK
# =========================================================

async def admin_deposit_callback(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    await query.answer()

    request_id = query.data.split(
        "_",
        2
    )[-1]

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

    if query.data.startswith("ok_dep_"):

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

            f"👤 کاربر: "
            f"{user_display(uid)}\n"

            f"💰 مبلغ: "
            f"{request['amount']:,} DOGS"

        )

        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{request['amount']:,} DOGS\n\n"

                    f"💳 موجودی جدید: "
                    f"{balance(uid):,} DOGS"

                )

            )

        except Exception:
            pass

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
                "مقدار تراکنش مورد تأیید مالک نبوده است."
            )

        )

    except Exception:
        pass


# =========================================================
# ADMIN WITHDRAW CALLBACK
# =========================================================

async def admin_withdraw_callback(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    await query.answer()

    request_id = query.data.split(
        "_",
        2
    )[-1]

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

    uid = request["user_id"]

    if query.data.startswith("ok_wd_"):

        request["status"] = "approved"

        request["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(

            "✅ برداشت تأیید شد.\n\n"

            f"👤 کاربر: "
            f"{user_display(uid)}\n\n"

            f"💰 مبلغ: "
            f"{request['amount']:,} DOGS\n\n"

            f"💳 آدرس:\n"
            f"{request['address']}"

        )

        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ درخواست برداشت شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{request['amount']:,} DOGS\n\n"

                    "پرداخت توسط مالک تأیید شد."

                )

            )

        except Exception:
            pass

        return

    add_balance(
        uid,
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
        f"{user_display(uid)}\n\n"

        f"💰 مبلغ برگشت داده شد: "
        f"{request['amount']:,} DOGS"

    )

    try:

        await context.bot.send_message(

            chat_id=uid,

            text=(

                "❌ درخواست برداشت رد شد.\n\n"

                f"💰 مبلغ "
                f"{request['amount']:,} DOGS "
                "به موجودی برگشت داده شد.\n\n"

                f"💳 موجودی جدید: "
                f"{balance(uid):,} DOGS"

            )

        )

    except Exception:
        pass


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    status = (
        "🟢 روشن"
        if bot_is_on()
        else "🔴 خاموش"
    )

    return InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    status,
                    callback_data="admin_toggle_bot"
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

            ]

        ]

    )


async def show_admin_panel(
    update,
    context
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    await update.message.reply_text(

        "⚙️ پنل مدیریت\n\n"

        "از گزینه‌های زیر استفاده کنید:",

        reply_markup=admin_keyboard()

    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_panel_callback(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    await query.answer()

    # -----------------------------
    # TOGGLE BOT
    # -----------------------------

    if query.data == "admin_toggle_bot":

        data["settings"]["bot"] = not bot_is_on()

        save_data()

        status = (
            "🟢 روشن"
            if bot_is_on()
            else "🔴 خاموش"
        )

        await query.edit_message_text(

            f"🤖 وضعیت ربات: {status}\n\n"

            "برای تغییر دوباره روی دکمه بزنید.",

            reply_markup=admin_keyboard()

        )

        return

    # -----------------------------
    # CHANNEL
    # -----------------------------

    if query.data == "admin_channel":

        context.user_data.clear()

        context.user_data[
            "admin_state"
        ] = "channel"

        current = data["settings"].get(
            "force_channel",
            ""
        )

        await query.message.reply_text(

            "📢 کانال اجباری\n\n"

            f"وضعیت فعلی:\n"
            f"{current or 'خاموش'}\n\n"

            "یوزرنیم کانال را ارسال کنید.\n"
            "مثال:\n"
            "@YourChannel\n\n"

            "برای خاموش کردن بنویسید:\n"
            "خاموش"

        )

        return

    # -----------------------------
    # GROUP
    # -----------------------------

    if query.data == "admin_group":

        context.user_data.clear()

        context.user_data[
            "admin_state"
        ] = "group"

        current = data["settings"].get(
            "force_group",
            ""
        )

        await query.message.reply_text(

            "👥 گپ اجباری\n\n"

            f"وضعیت فعلی:\n"
            f"{current or 'خاموش'}\n\n"

            "یوزرنیم گپ را ارسال کنید.\n"
            "مثال:\n"
            "@YourGroup\n\n"

            "برای خاموش کردن بنویسید:\n"
            "خاموش"

        )

        return

    # -----------------------------
    # OWNER
    # -----------------------------

    if query.data == "admin_owner":

        context.user_data.clear()

        context.user_data[
            "admin_state"
        ] = "owner"

        await query.message.reply_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789\n\n"

            "⚠️ بعد از انتقال، مالک فعلی دسترسی مالکیت را از دست می‌دهد."

        )

        return

    # -----------------------------
    # STATS
    # -----------------------------

    if query.data == "admin_stats":

        users = len(
            data.get(
                "users",
                {}
            )
        )

        deposits = data.get(
            "deposits",
            {}
        )

        withdraws = data.get(
            "withdraws",
            {}
        )

        pending_dep = sum(
            1
            for x in deposits.values()
            if x.get("status") == "pending"
        )

        approved_dep = sum(
            1
            for x in deposits.values()
            if x.get("status") == "approved"
        )

        pending_wd = sum(
            1
            for x in withdraws.values()
            if x.get("status") == "pending"
        )

        approved_wd = sum(
            1
            for x in withdraws.values()
            if x.get("status") == "approved"
        )

        total_balance = sum(
            balance(uid)
            for uid in data["users"]
        )

        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n\n"

            f"💳 کل درخواست واریز: "
            f"{len(deposits)}\n"

            f"✅ واریز تأییدشده: "
            f"{approved_dep}\n"

            f"⏳ واریز در انتظار: "
            f"{pending_dep}\n\n"

            f"💰 کل درخواست برداشت: "
            f"{len(withdraws)}\n"

            f"✅ برداشت تأییدشده: "
            f"{approved_wd}\n"

            f"⏳ برداشت در انتظار: "
            f"{pending_wd}\n\n"

            f"💳 مجموع موجودی کاربران: "
            f"{total_balance:,} DOGS\n\n"

            f"🎁 پاداش هر رفرال: "
            f"{REFERRAL_REWARD:,} DOGS",

            reply_markup=admin_keyboard()

        )

        return


# =========================================================
# ADMIN TEXT SETTINGS
# =========================================================

async def handle_admin_text(
    update,
    context
):

    if not is_owner(
        update.effective_user.id
    ):
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    text = update.message.text.strip()

    if state == "channel":

        if text == "خاموش":

            data["settings"][
                "force_channel"
            ] = ""

        else:

            data["settings"][
                "force_channel"
            ] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ تنظیم کانال اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            )
        )

        return True

    if state == "group":

        if text == "خاموش":

            data["settings"][
                "force_group"
            ] = ""

        else:

            data["settings"][
                "force_group"
            ] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ تنظیم گپ اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            )
        )

        return True

    if state == "owner":

        try:

            new_owner = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return True

        old_owner = data.get(
            "owner",
            OWNER_ID
        )

        data["owner"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ مالکیت منتقل شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}\n\n"

            "دسترسی مالک قبلی حذف شد."

        )

        try:

            await context.bot.send_message(

                chat_id=new_owner,

                text=(
                    "👑 شما مالک جدید ربات شدید."
                )

            )

        except Exception:
            pass

        print(
            f"OWNER CHANGED: {old_owner} -> {new_owner}"
        )

        return True

    return False


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(
    update,
    context
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    text = update.message.text

    user = update.effective_user

    if (
        not bot_is_on()
        and not is_owner(user.id)
    ):

        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )

        return

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

        if is_owner(user.id):

            await show_admin_panel(
                update,
                context
            )


# =========================================================
# MESSAGE ROUTER
# =========================================================

async def message_handler(
    update,
    context
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    create_user(user)

    # -----------------------------
    # ADMIN INPUT
    # -----------------------------

    if
