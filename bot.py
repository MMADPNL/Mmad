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

# آیدی برای واریز DOGS
DEPOSIT_USERNAME = "@CyyFr"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

# رفرال
REFERRAL_REWARD = 50

# کارمزد بازی
GAME_FEE = 0

DATA_FILE = "bot_data.json"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "referrals": {},
    "owner": OWNER_ID,

    "settings": {
        "bot": True,
        "force_channel": False,
        "force_channel_username": "",
        "force_group": False,
        "force_group_username": ""
    }
}


# =========================================================
# DATABASE
# =========================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

        if not isinstance(loaded, dict):
            loaded = {}

        for key, value in DEFAULT_DATA.items():

            if key not in loaded:
                loaded[key] = json.loads(
                    json.dumps(value)
                )

        if "settings" not in loaded:
            loaded["settings"] = {}

        for key, value in DEFAULT_DATA["settings"].items():

            if key not in loaded["settings"]:
                loaded["settings"][key] = value

        return loaded

    except Exception:

        return json.loads(json.dumps(DEFAULT_DATA))


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


# =========================================================
# USER
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

    return data["users"].get(str(uid))


def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    return int(
        user.get("balance", 0)
    )


def add_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    user["balance"] = (
        balance(uid) + int(amount)
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
        data.get("owner", OWNER_ID)
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

async def check_force_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return True

    settings = data.get(
        "settings",
        {}
    )

    # کانال اجباری
    if settings.get("force_channel"):

        channel = settings.get(
            "force_channel_username",
            ""
        ).strip()

        if channel:

            if not channel.startswith("@"):
                channel = "@" + channel

            try:

                member = await context.bot.get_chat_member(
                    channel,
                    user.id
                )

                if member.status in (
                    "left",
                    "kicked"
                ):

                    keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "📢 عضویت در کانال",
                                    url=f"https://t.me/{channel[1:]}"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "✅ بررسی عضویت",
                                    callback_data="check_join"
                                )
                            ]
                        ]
                    )

                    if update.callback_query:

                        await update.callback_query.answer(
                            "❌ ابتدا در کانال عضو شوید.",
                            show_alert=True
                        )

                    elif update.message:

                        await update.message.reply_text(
                            "❌ برای استفاده از ربات ابتدا در کانال اجباری عضو شوید.",
                            reply_markup=keyboard
                        )

                    return False

            except Exception as e:

                print(
                    f"Force channel error: {e}"
                )

    # گپ اجباری
    if settings.get("force_group"):

        group = settings.get(
            "force_group_username",
            ""
        ).strip()

        if group:

            if not group.startswith("@"):
                group = "@" + group

            try:

                member = await context.bot.get_chat_member(
                    group,
                    user.id
                )

                if member.status in (
                    "left",
                    "kicked"
                ):

                    keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "👥 ورود به گپ",
                                    url=f"https://t.me/{group[1:]}"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "✅ بررسی عضویت",
                                    callback_data="check_join"
                                )
                            ]
                        ]
                    )

                    if update.callback_query:

                        await update.callback_query.answer(
                            "❌ ابتدا وارد گپ شوید.",
                            show_alert=True
                        )

                    elif update.message:

                        await update.message.reply_text(
                            "❌ برای استفاده از ربات ابتدا وارد گپ اجباری شوید.",
                            reply_markup=keyboard
                        )

                    return False

            except Exception as e:

                print(
                    f"Force group error: {e}"
                )

    return True


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


def admin_keyboard():

    return InlineKeyboardMarkup(
        [

            [
                InlineKeyboardButton(
                    "🤖 روشن/خاموش ربات",
                    callback_data="admin_bot_toggle"
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
                    callback_data="admin_transfer"
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
                    "🔄 بروزرسانی پنل",
                    callback_data="admin_panel"
                )
            ]

        ]
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

    # رفرال
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

                    current = get_user(
                        user.id
                    )

                    if not current.get(
                        "referred_by"
                    ):

                        current["referred_by"] = ref_id

                        ref_user = get_user(
                            ref_id
                        )

                        if ref_user:

                            ref_user["referrals"] = (
                                int(
                                    ref_user.get(
                                        "referrals",
                                        0
                                    )
                                ) + 1
                            )

                            add_balance(
                                ref_id,
                                REFERRAL_REWARD
                            )

                            data["referrals"][
                                str(user.id)
                            ] = ref_id

                            save_data()

            except Exception as e:

                print(
                    f"Referral error: {e}"
                )

    context.user_data.clear()

    if not await check_force_join(
        update,
        context
    ):
        return

    chat_type = update.effective_chat.type

    # گروه
    if chat_type != "private":

        await update.message.reply_text(

            "🤖 ربات فعال است.\n\n"

            "🎮 برای شروع بازی:\n"
            "بازی 500\n\n"

            f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"💰 حداکثر بازی: {MAX_GAME:,} DOGS",

            reply_markup=ReplyKeyboardRemove()

        )

        return

    # خاموش بودن ربات
    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است.\n\n"
            "لطفاً بعداً دوباره تلاش کنید."
        )

        return

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


# =========================================================
# PROFILE
# =========================================================

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
        f"👤 نام: {profile.get('name', '')}\n"
        f"🔹 یوزرنیم: {username_text}\n\n"

        f"💰 موجودی: {balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه‌ها: {referrals}",

        reply_markup=back_keyboard()

    )


# =========================================================
# REFERRALS
# =========================================================

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

        "🎁 پاداش هر رفرال: "
        f"{REFERRAL_REWARD} DOGS\n\n"

        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"

        f"👥 تعداد زیرمجموعه‌ها: {referrals}\n\n"

        "📢 لینک بالا را برای دوستان خود ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT
# =========================================================

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

        f"📥 ابتدا DOGS را به این آیدی بفرستید:\n"
        f"{DEPOSIT_USERNAME}\n\n"

        "📸 سپس شات/عکس رسید خود را ارسال کنید.\n\n"

        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"

        "بعد از ارسال رسید، مقدار واریزی را وارد کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

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
                "❌ لطفاً شات رسید یا لینک تراکنش را ارسال کنید."
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

        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

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

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📝 رسید:\n{receipt}\n\n"

        f"🆔 شناسه:\n{request_id}"

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
            chat_id=data.get("owner", OWNER_ID),
            text=owner_text,
            reply_markup=keyboard
        )

    except Exception as e:

        print(
            f"❌ خطا در ارسال واریزی: {e}"
        )


# =========================================================
# WITHDRAW
# =========================================================

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

            f"💳 موجودی شما: {current:,} DOGS\n\n"

            f"❌ حداقل برداشت: {MIN_WITHDRAW:,} DOGS",

            reply_markup=back_keyboard()

        )

        return

    context.user_data.clear()

    context.user_data["state"] = (
        "withdraw_address"
    )

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        f"💳 موجودی شما: {current:,} DOGS\n\n"

        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"

        "1️⃣ آدرس کیف پول DOGS خود را ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

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

        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"

        "مثال:\n"
        "10000",

        reply_markup=back_keyboard()

    )


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

async def handle_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار برداشت را ارسال کنید."
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
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )

        return

    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
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
            "❌ آدرس پیدا نشد.\nدوباره آدرس را ارسال کنید."
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

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"💳 آدرس:\n{address}\n\n"

        f"💰 موجودی جدید: {new_balance:,} DOGS\n\n"

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

        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"💳 آدرس:\n{address}\n\n"

        f"💰 موجودی فعلی: {new_balance:,} DOGS\n\n"

        f"🆔 شناسه:\n{request_id}"

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
            chat_id=data.get("owner", OWNER_ID),
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

        data["withdraws"][request_id]["status"] = "failed"

        save_data()


# =========================================================
# SUPPORT
# =========================================================

async def show_support(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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


# =========================================================
# GAME
# =========================================================

ACTIVE_GAMES = {}


async def game_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گروه قابل انجام است."
        )

        return

    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
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
            f"❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی شما: {balance(user.id):,} DOGS"
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

        f"👤 سازنده: {user_display(user.id)}\n\n"

        f"💰 شرط: {amount:,} DOGS\n\n"

        "👥 نفر دوم روی «ورود به بازی» بزند.",

        reply_markup=keyboard

    )


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user = query.from_user

    chat_id = query.message.chat.id

    if query.data == "check_join":

        await query.answer(
            "این دکمه برای عضویت اجباری است.",
            show_alert=True
        )

        return

    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True
        )

        return

    game = ACTIVE_GAMES[chat_id]

    # لغو
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

        await query.answer()

        await query.edit_message_text(

            "❌ بازی لغو شد.\n\n"

            f"💰 مبلغ {game['amount']:,} DOGS "
            "به سازنده برگشت داده شد."

        )

        return

    # ورود
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

        loser = (
            user.id
            if winner == game["creator"]
            else game["creator"]
        )

        total_pot = amount * 2

        prize = total_pot - GAME_FEE

        add_balance(
            winner,
            prize
        )

        if GAME_FEE > 0:

            if not get_user(
                data.get("owner", OWNER_ID)
            ):

                data["users"][
                    str(data.get("owner", OWNER_ID))
                ] = {

                    "id": data.get("owner", OWNER_ID),
                    "name": "OWNER",
                    "username": "",
                    "balance": 0,
                    "referrals": 0,
                    "referred_by": None,
                    "date": datetime.now().isoformat()

                }

                save_data()

            add_balance(
                data.get("owner", OWNER_ID),
                GAME_FEE
            )

        del ACTIVE_GAMES[chat_id]

        await query.answer()

        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"🏆 برنده: {user_display(winner)}\n\n"

            f"💰 جایزه: {prize:,} DOGS\n\n"

            f"😢 بازنده: {user_display(loser)}"

        )


# =========================================================
# ADMIN PANEL
# =========================================================

async def show_admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_owner(user.id):
        return

    status = (
        "🟢 روشن"
        if bot_is_on()
        else "🔴 خاموش"
    )

    settings = data.get(
        "settings",
        {}
    )

    channel = settings.get(
        "force_channel_username",
        ""
    )

    group = settings.get(
        "force_group_username",
        ""
    )

    text = (

        "⚙️ پنل مدیریت\n\n"

        f"🤖 وضعیت ربات: {status}\n\n"

        f"📢 کانال اجباری: "
        f"{channel if settings.get('force_channel') else 'خاموش'}\n\n"

        f"👥 گپ اجباری: "
        f"{group if settings.get('force_group') else 'خاموش'}\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:"

    )

    await update.message.reply_text(
        text,
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_panel_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not is_owner(query.from_user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    await query.answer()

    action = query.data

    # -------------------------
    # PANEL
    # -------------------------

    if action == "admin_panel":

        status = (
            "🟢 روشن"
            if bot_is_on()
            else "🔴 خاموش"
        )

        settings = data["settings"]

        text = (

            "⚙️ پنل مدیریت\n\n"

            f"🤖 وضعیت ربات: {status}\n"

            f"📢 کانال اجباری: "
            f"{'🟢 روشن' if settings.get('force_channel') else '🔴 خاموش'}\n"

            f"👥 گپ اجباری: "
            f"{'🟢 روشن' if settings.get('force_group') else '🔴 خاموش'}"

        )

        await query.edit_message_text(
            text,
            reply_markup=admin_keyboard()
        )

        return

    # -------------------------
    # BOT TOGGLE
    # -------------------------

    if action == "admin_bot_toggle":

        data["settings"]["bot"] = not bot_is_on()

        save_data()

        status = (
            "🟢 روشن"
            if bot_is_on()
            else "🔴 خاموش"
        )

        await query.edit_message_text(

            "🤖 وضعیت ربات تغییر کرد.\n\n"
            f"وضعیت فعلی: {status}",

            reply_markup=admin_keyboard()

        )

        return

    # -------------------------
    # CHANNEL
    # -------------------------

    if action == "admin_channel":

        current = data["settings"].get(
            "force_channel",
            False
        )

        if current:

            data["settings"]["force_channel"] = False

            save_data()

            await query.edit_message_text(
                "📢 کانال اجباری خاموش شد.",
                reply_markup=admin_keyboard()
            )

        else:

            context.user_data["state"] = (
                "admin_channel_input"
            )

            await query.edit_message_text(

                "📢 کانال اجباری\n\n"

                "یوزرنیم کانال را ارسال کنید.\n\n"

                "مثال:\n"
                "@mychannel\n\n"

                "بعد از ارسال، کانال فعال می‌شود."

            )

        return

    # -------------------------
    # GROUP
    # -------------------------

    if action == "admin_group":

        current = data["settings"].get(
            "force_group",
            False
        )

        if current:

            data["settings"]["force_group"] = False

            save_data()

            await query.edit_message_text(
                "👥 گپ اجباری خاموش شد.",
                reply_markup=admin_keyboard()
            )

        else:

            context.user_data["state"] = (
                "admin_group_input"
            )

            await query.edit_message_text(

                "👥 گپ اجباری\n\n"

                "یوزرنیم گپ را ارسال کنید.\n\n"

                "مثال:\n"
                "@mygroup\n\n"

                "بعد از ارسال، گپ فعال می‌شود."

            )

        return

    # -------------------------
    # TRANSFER
    # -------------------------

    if action == "admin_transfer":

        context.user_data["state"] = (
            "admin_transfer_input"
        )

        await query.edit_message_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789\n\n"

            "⚠️ پس از انتقال، مالک فعلی دیگر دسترسی مالک را ندارد."

        )

        return

    # -------------------------
    # STATS
    # -------------------------

    if action == "admin_stats":

        users = len(
            data["users"]
        )

        deposits = len(
            data["deposits"]
        )

        withdraws = len(
            data["withdraws"]
        )

        total_balance = sum(
            int(
                u.get(
                    "balance",
                    0
                )
            )
            for u in data["users"].values()
        )

        approved_deposits = sum(
            1
            for x in data["deposits"].values()
            if x.get("status") == "approved"
        )

        pending_deposits = sum(
            1
            for x in data["deposits"].values()
            if x.get("status") == "pending"
        )

        approved_withdraws = sum(
            1
            for x in data["withdraws"].values()
            if x.get("status") == "approved"
        )

        pending_withdraws = sum(
            1
            for x in data["withdraws"].values()
            if x.get("status") == "pending"
        )

        text = (

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n\n"

            f"💰 مجموع موجودی کاربران: "
            f"{total_balance:,} DOGS\n\n"

            f"💳 کل درخواست‌های واریز: {deposits}\n"
            f"✅ واریز تأییدشده: {approved_deposits}\n"
            f"⏳ واریز در انتظار: {pending_deposits}\n\n"

            f"💰 کل درخواست‌های برداشت: {withdraws}\n"
            f"✅ برداشت تأییدشده: {approved_withdraws}\n"
            f"⏳ برداشت در انتظار: {pending_withdraws}\n\n"

            f"🎁 پاداش هر رفرال: "
            f"{REFERRAL_REWARD} DOGS"

        )

        await query.edit_message_text(
            text,
            reply_markup=admin_keyboard()
        )

        return


# =========================================================
# ADMIN TEXT STATES
# =========================================================

async def handle_admin_state(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_owner(user.id):
        return False

    state = context.user_data.get(
        "state"
    )

    if state == "admin_channel_input":

        value = update.message.text.strip()

        if not value.startswith("@"):
            value = "@" + value

        data["settings"][
            "force_channel_username"
        ] = value

        data["settings"][
            "force_channel"
        ] = True

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ کانال اجباری فعال شد.\n\n"
            f"📢 {value}",
            reply_markup=main_keyboard(user.id)
        )

        return True

    if state == "admin_group_input":

        value = update.message.text.strip()

        if not value.startswith("@"):
            value = "@" + value

        data["settings"][
            "force_group_username"
        ] = value

        data["settings"][
            "force_group"
        ] = True

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ گپ اجباری فعال شد.\n\n"
            f"👥 {value}",
            reply_markup=main_keyboard(user.id)
        )

        return True

    if state == "admin_transfer_input":

        text = update.message.text.strip()

        try:

            new_owner = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return True

        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی معتبر نیست."
            )

            return True

        data["owner"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ مالکیت منتقل شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return True

    return False


# =========================================================
# ADMIN DEPOSIT CALLBACK
# =========================================================

async def admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

    if query.data.startswith(
        "ok_dep_"
    ):

        request_id = query.data[
            len("ok_dep_"):
        ]

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
            f"💰 مبلغ: {request['amount']:,} DOGS"

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
                f"❌ ارسال تأیید واریز: {e}"
            )

        return

    if query.data.startswith(
        "no_dep_"
    ):

        request_id = query.data[
            len("no_dep_"):
        ]

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
                    "در صورت اشتباه با پشتیبانی تماس بگیرید."
                )

            )

        except Exception as e:

            print(
                f"❌ ارسال رد واریز: {e}"
            )


# =========================================================
# ADMIN WITHDRAW CALLBACK
# =========================================================

async def admin_withdraw_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
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

    if query.data.startswith(
        "ok_wd_"
    ):

        request_id = query.data[
            len("ok_wd_"):
        ]

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

                    "پرداخت توسط مالک تأیید شد."

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال تأیید برداشت: {e}"
            )

        return

    if query.data.startswith(
        "no_wd_"
    ):

        request_id = query.data[
            len("no_wd_"):
        ]

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
                f"❌ ارسال رد برداشت: {e}"
            )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    text = update.message.text

    user = update.effective_user

    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    # بازی را از این هندلر رد نکن
    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    if not user:
        return

    create_user(user)

    # مدیریت state ها
    if await handle_admin_state(
        update,
        context
    ):
        return

    state = context.user_data.get(
        "state"
    )

    # برگشت
    if update.message.text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

        return

    # ربات خاموش
    if not bot_is_on() and not is_owner(user.id):

        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )

        return

    # واریزی
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

    # برداشت
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

    # دکمه‌های اصلی
    await button_handler(
        update,
        context
    )


# =========================================================
# MAIN
# =========================================================

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

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # GAME
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(
                r"^بازی\s+\d+$"
            ),
            game_command
        )
    )

    # GAME CALLBACK
    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )

    # CHECK JOIN
    app.add_handler(
        CallbackQueryHandler(
            force_join_callback,
            pattern=r"^check_join$"
        )
    )

    # ADMIN PANEL
    app.add_handler(
        CallbackQueryHandler(
            admin_panel_callback,
            pattern=r"^admin_"
        )
    )

    # DEPOSIT
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )

    # WITHDRAW
    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(ok_wd_|no_wd_)"
        )
    )

    # PRIVATE TEXT + PHOTO
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
        f"🎮 GAME: {MIN_GAME} - {MAX_GAME}"
    )

    print(
        f"🎁 REFERRAL: {REFERRAL_REWARD} DOGS"
    )

    print(
        "================================="
    )

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# FORCE JOIN CALLBACK
# =========================================================

async def force_join_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    fake_update = update

    ok = await check_force_join(
        fake_update,
        context
    )

    if ok:

        await query.message.reply_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "حالا می‌توانید از ربات استفاده کنید.",
            reply_markup=main_keyboard(
                user.id
            )
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
