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

ULTRA_USERNAME = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

FORCE_CHANNEL = "@TAK_BE_T"
FORCE_GROUP = "https://t.me/TAK_B_ET"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

REFERRAL_REWARD = 50

MIN_GAME = 500
MAX_GAME = 20000

GAME_FEE = 0

DATA_FILE = "bot_data.json"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "force_channel": FORCE_CHANNEL,
        "force_group": FORCE_GROUP,
    },
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

        return json.loads(
            json.dumps(DEFAULT_DATA)
        )


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

        print(
            f"❌ خطا در ذخیره اطلاعات: {e}"
        )


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

            "ref_reward_received": False,

            "date": datetime.now().isoformat(),

        }

        save_data()

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

    if is_owner(user.id):
        return True

    bot_enabled = data.get(
        "settings",
        {}
    ).get(
        "bot",
        True
    )

    if not bot_enabled:
        return True

    channel = data.get(
        "settings",
        {}
    ).get(
        "force_channel",
        FORCE_CHANNEL
    )

    group = data.get(
        "settings",
        {}
    ).get(
        "force_group",
        FORCE_GROUP
    )

    missing = []

    # کانال
    try:

        member = await context.bot.get_chat_member(
            chat_id=channel,
            user_id=user.id
        )

        if member.status in (
            "left",
            "kicked"
        ):
            missing.append("channel")

    except Exception as e:

        print(
            f"❌ بررسی کانال: {e}"
        )

    # گپ
    try:

        group_username = group

        if group.startswith(
            "https://t.me/"
        ):

            group_username = (
                "@"
                + group.split(
                    "https://t.me/"
                )[1]
            )

        member = await context.bot.get_chat_member(
            chat_id=group_username,
            user_id=user.id
        )

        if member.status in (
            "left",
            "kicked"
        ):
            missing.append("group")

    except Exception as e:

        print(
            f"❌ بررسی گپ: {e}"
        )

    if missing:

        buttons = []

        if "channel" in missing:

            buttons.append(
                [
                    InlineKeyboardButton(
                        "📢 عضویت در کانال",
                        url=f"https://t.me/{channel.lstrip('@')}"
                    )
                ]
            )

        if "group" in missing:

            buttons.append(
                [
                    InlineKeyboardButton(
                        "👥 ورود به گپ",
                        url=group
                    )
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    "✅ بررسی عضویت",
                    callback_data="check_join"
                )
            ]
        )

        text = (
            "🔒 برای استفاده از ربات باید ابتدا "
            "در موارد زیر عضو شوید:\n\n"
        )

        if "channel" in missing:
            text += "📢 کانال اجباری\n"

        if "group" in missing:
            text += "👥 گپ اجباری\n"

        if update.message:

            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    buttons
                )
            )

        return False

    return True


# =========================================================
# KEYBOARDS
# =========================================================

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
                    "🔄 روشن / خاموش ربات",
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
                    "🔙 بستن پنل",
                    callback_data="admin_close"
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

    context.user_data.clear()

    if not await check_force_join(
        update,
        context
    ):
        return

    if not data["settings"].get(
        "bot",
        True
    ) and not is_owner(user.id):

        await update.message.reply_text(
            "⛔ ربات موقتاً خاموش است."
        )

        return

    # referral
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

                        current[
                            "referred_by"
                        ] = ref_id

                        data["users"][
                            str(ref_id)
                        ]["referrals"] = (
                            int(
                                data["users"][
                                    str(ref_id)
                                ].get(
                                    "referrals",
                                    0
                                )
                            ) + 1
                        )

                        add_balance(
                            ref_id,
                            REFERRAL_REWARD
                        )

                        save_data()

            except Exception as e:

                print(
                    f"Referral error: {e}"
                )

    chat_type = (
        update.effective_chat.type
    )

    if chat_type != "private":

        await update.message.reply_text(

            "🤖 ربات فعال است.\n\n"

            "🎮 برای شروع بازی بنویسید:\n"
            "بازی 500\n\n"

            f"💰 حداقل بازی: "
            f"{MIN_GAME:,} DOGS\n"

            f"💰 حداکثر بازی: "
            f"{MAX_GAME:,} DOGS",

            reply_markup=ReplyKeyboardRemove()

        )

        return

    await update.message.reply_text(

        "🤖 به ربات خوش آمدید.\n\n"

        f"👤 {user.first_name}\n\n"

        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:",

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

    profile = get_user(
        user.id
    )

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

        f"👥 زیرمجموعه: "
        f"{referrals}",

        reply_markup=back_keyboard()

    )


# =========================================================
# REFERRAL
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

        f"🎁 پاداش هر رفرال: "
        f"{REFERRAL_REWARD:,} DOGS\n\n"

        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"

        f"👥 تعداد زیرمجموعه‌ها: "
        f"{referrals}\n\n"

        f"💰 پاداش هر نفر: "
        f"{REFERRAL_REWARD:,} DOGS",

        reply_markup=back_keyboard()

    )


# =========================================================
# DEPOSIT MENU
# =========================================================

async def show_deposit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    keyboard = InlineKeyboardMarkup(

        [

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
            ]

        ]

    )

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"

        f"🔻 حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "روش واریز را انتخاب کنید:",

        reply_markup=keyboard

    )


# =========================================================
# DEPOSIT CALLBACK
# =========================================================

async def deposit_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if query.data == "deposit_ultra":

        context.user_data.clear()

        context.user_data["state"] = (
            "deposit_ultra_receipt"
        )

        await query.message.reply_text(

            "⚡ اولترا\n\n"

            f"{ULTRA_USERNAME}\n\n"

            "به این آیدی DOGS را بزنید.\n\n"

            "📸 شات پرداخت خود را ارسال کنید.\n"
            "بعد مقدار DOGS را ارسال کنید.\n\n"

            f"🔻 حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS\n\n"

            "⚠️ اگر مقدار واردشده درست نباشد، "
            "درخواست توسط مالک رد می‌شود.",

            reply_markup=back_keyboard()

        )

        return

    if query.data == "deposit_exchange":

        context.user_data.clear()

        context.user_data["state"] = (
            "deposit_exchange_receipt"
        )

        await query.message.reply_text(

            "🏦 صرافی\n\n"

            f"💳 کیف پول DOGS:\n"
            f"{EXCHANGE_WALLET}\n\n"

            "از طریق صرافی DOGS را به این ولت بزنید.\n\n"

            "📸 شات یا لینک هش تراکنش را ارسال کنید.\n"
            "بعد مقدار DOGS را ارسال کنید.\n\n"

            f"🔻 حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS\n\n"

            "⚠️ اگر مقدار واردشده درست نباشد، "
            "درخواست توسط مالک رد می‌شود.",

            reply_markup=back_keyboard()

        )

        return


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

async def handle_deposit_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    method="exchange"
):

    if update.message.photo:

        photo = update.message.photo[-1]

        context.user_data[
            "receipt"
        ] = (
            f"📸 عکس رسید\n"
            f"File ID: {photo.file_id}"
        )

    elif update.message.text:

        text = update.message.text.strip()

        if not text:

            await update.message.reply_text(
                "❌ رسید یا لینک تراکنش را ارسال کنید."
            )

            return

        context.user_data[
            "receipt"
        ] = text

    else:

        await update.message.reply_text(
            "❌ عکس، شات یا لینک تراکنش را ارسال کنید."
        )

        return

    context.user_data[
        "deposit_method"
    ] = method

    context.user_data[
        "state"
    ] = "deposit_amount"

    await update.message.reply_text(

        "✅ رسید دریافت شد.\n\n"

        "💰 حالا مقدار DOGS را ارسال کنید.\n\n"

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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    try:

        amount = int(
            update.message.text.strip()
        )

    except Exception:

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
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
        "exchange"
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

        "amount": amount,

        "method": method,

        "receipt": receipt,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        "⏳ منتظر بررسی مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    method_text = (
        "⚡ اولترا"
        if method == "ultra"
        else "🏦 صرافی"
    )

    owner_text = (

        "💳 واریزی جدید\n\n"

        f"🔹 روش: {method_text}\n"

        f"👤 کاربر: "
        f"{user.first_name or 'بدون نام'}\n"

        f"🆔 آیدی: "
        f"{user.id}\n\n"

        f"💰 مبلغ اعلامی: "
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

            chat_id=data["owner"],

            text=owner_text,

            reply_markup=keyboard

        )

    except Exception as e:

        print(
            f"❌ ارسال واریزی مالک: {e}"
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

    current = balance(
        user.id
    )

    if current < MIN_WITHDRAW:

        await update.message.reply_text(

            "💰 برداشت DOGS\n\n"

            f"💳 موجودی: "
            f"{current:,} DOGS\n\n"

            f"❌ حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n\n"

            "برای برداشت باید حداقل "
            f"{MIN_WITHDRAW:,} DOGS "
            "موجودی داشته باشید.",

            reply_markup=back_keyboard()

        )

        return

    context.user_data.clear()

    context.user_data[
        "state"
    ] = "withdraw_address"

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        f"💳 موجودی: "
        f"{current:,} DOGS\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "آدرس کیف پول DOGS خود را ارسال کنید.",

        reply_markup=back_keyboard()

    )


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

async def handle_withdraw_address(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    address = update.message.text.strip()

    if len(address) < 10:

        await update.message.reply_text(
            "❌ آدرس کیف پول معتبر نیست."
        )

        return

    context.user_data[
        "withdraw_address"
    ] = address

    context.user_data[
        "state"
    ] = "withdraw_amount"

    await update.message.reply_text(

        "✅ آدرس دریافت شد.\n\n"

        f"💳 {address}\n\n"

        "حالا مقدار DOGS برداشت را ارسال کنید.\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS",

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

    try:

        amount = int(
            update.message.text.strip()
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

    if balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: "
            f"{balance(user.id):,} DOGS"

        )

        return

    address = context.user_data.get(
        "withdraw_address"
    )

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

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس:\n"
        f"{address}\n\n"

        "⏳ منتظر تأیید مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    owner_text = (

        "💰 برداشت جدید\n\n"

        f"👤 کاربر: "
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

            chat_id=data["owner"],

            text=owner_text,

            reply_markup=keyboard

        )

    except Exception as e:

        print(
            f"❌ ارسال برداشت مالک: {e}"
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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        f"{SUPPORT_USERNAME}",

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

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(

        "🏠 منوی اصلی\n\n"

        f"💰 موجودی: "
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
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گروه است."
        )

        return

    user = update.effective_user

    create_user(user)

    if not data["settings"].get(
        "bot",
        True
    ) and not is_owner(user.id):

        await update.message.reply_text(
            "⛔ ربات خاموش است."
        )

        return

    try:

        parts = update.message.text.strip().split()

        if len(parts) != 2:
            raise ValueError

        amount = int(
            parts[1]
        )

    except Exception:

        await update.message.reply_text(

            "❌ فرمت اشتباه.\n\n"
            "مثال:\n"
            "بازی 500"

        )

        return

    if amount < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل بازی "
            f"{MIN_GAME:,} DOGS است."

        )

        return

    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر بازی "
            f"{MAX_GAME:,} DOGS است."

        )

        return

    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ در این گپ بازی فعال است."
        )

        return

    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    remove_balance(
        user.id,
        amount
    )

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

        "👥 نفر دوم وارد شود.",

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
            "❌ بازی لغو شد و مبلغ برگشت خورد."
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

        remove_balance(
            user.id,
            amount
        )

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
# ADMIN CALLBACK
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

    # -----------------------------------------------------
    # DEPOSIT
    # -----------------------------------------------------

    if query.data.startswith(
        "ok_dep_"
    ):

        request_id = query.data[
            len("ok_dep_"):
        ]

        request = data[
            "deposits"
        ].get(request_id)

        if not request:
            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )
            return

        if request["status"] != "pending":

            await query.answer(
                "قبلاً بررسی شده.",
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

            f"👤 {user_display(uid)}\n"

            f"💰 {request['amount']:,} DOGS"

        )

        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{request['amount']:,} DOGS\n\n"

                    f"💳 موجودی: "
                    f"{balance(uid):,} DOGS"

                )

            )

        except Exception:
            pass

        return

    if query.data.startswith(
        "no_dep_"
    ):

        request_id = query.data[
            len("no_dep_"):
        ]

        request = data[
            "deposits"
        ].get(request_id)

        if not request:
            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )
            return

        if request["status"] != "pending":

            await query.answer(
                "قبلاً بررسی شده.",
                show_alert=True
            )

            return

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.edit_message_text(
            "❌ واریز رد شد."
        )

        try:

            await context.bot.send_message(

                chat_id=request["user_id"],

                text=(
                    "❌ درخواست واریز شما رد شد."
                )

            )

        except Exception:
            pass

        return

    # -----------------------------------------------------
    # WITHDRAW
    # -----------------------------------------------------

    if query.data.startswith(
        "ok_wd_"
    ):

        request_id = query.data[
            len("ok_wd_"):
        ]

        request = data[
            "withdraws"
        ].get(request_id)

        if not request:
            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )
            return

        if request["status"] != "pending":

            await query.answer(
                "قبلاً بررسی شده.",
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

            f"👤 {user_display(request['user_id'])}\n\n"

            f"💰 {request['amount']:,} DOGS\n\n"

            f"💳 {request['address']}"

        )

        try:

            await context.bot.send_message(

                chat_id=request["user_id"],

                text=(

                    "✅ برداشت شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{request['amount']:,} DOGS"

                )

            )

        except Exception:
            pass

        return

    if query.data.startswith(
        "no_wd_"
    ):

        request_id = query.data[
            len("no_wd_"):
        ]

        request = data[
            "withdraws"
        ].get(request_id)

        if not request:
            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )
            return

        if request["status"] != "pending":

            await query.answer(
                "قبلاً بررسی شده.",
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

            f"💰 مبلغ "
            f"{request['amount']:,} DOGS "
            "به کاربر برگشت داده شد."

        )

        try:

            await context.bot.send_message(

                chat_id=request["user_id"],

                text=(

                    "❌ برداشت شما رد شد.\n\n"

                    f"💰 مبلغ "
                    f"{request['amount']:,} DOGS "
                    "به موجودی شما برگشت داده شد."

                )

            )

        except Exception:
            pass

        return

    # -----------------------------------------------------
    # BOT TOGGLE
    # -----------------------------------------------------

    if query.data == "admin_bot_toggle":

        current = data["settings"].get(
            "bot",
            True
        )

        data["settings"]["bot"] = not current

        save_data()

        status = (
            "🟢 روشن"
            if data["settings"]["bot"]
            else "🔴 خاموش"
        )

        await query.edit_message_text(

            f"🤖 وضعیت ربات: {status}",

            reply_markup=admin_keyboard()

        )

        return

    # -----------------------------------------------------
    # CHANNEL
    # -----------------------------------------------------

    if query.data == "admin_channel":

        current = data["settings"].get(
            "force_channel",
            FORCE_CHANNEL
        )

        await query.edit_message_text(

            "📢 کانال اجباری\n\n"

            f"کانال فعلی:\n"
            f"{current}\n\n"

            "برای تغییر، فعلاً مقدار داخل تنظیمات "
            "کد را تغییر دهید.",

            reply_markup=admin_keyboard()

        )

        return

    # -----------------------------------------------------
    # GROUP
    # -----------------------------------------------------

    if query.data == "admin_group":

        current = data["settings"].get(
            "force_group",
            FORCE_GROUP
        )

        await query.edit_message_text(

            "👥 گپ اجباری\n\n"

            f"گپ فعلی:\n"
            f"{current}\n\n"

            "برای تغییر، مقدار داخل تنظیمات "
            "کد را تغییر دهید.",

            reply_markup=admin_keyboard()

        )

        return

    # -----------------------------------------------------
    # TRANSFER OWNER
    # -----------------------------------------------------

    if query.data == "admin_transfer":

        context.user_data[
            "state"
        ] = "transfer_owner"

        await query.message.reply_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789\n\n"

            "⚠️ با انتقال مالکیت، دسترسی مدیریتی "
            "به آیدی جدید منتقل می‌شود.",

            reply_markup=back_keyboard()

        )

        return

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    if query.data == "admin_stats":

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
            balance(uid)
            for uid in data["users"]
        )

        active_games = len(
            ACTIVE_GAMES
        )

        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n\n"

            f"💳 درخواست‌های واریز: "
            f"{deposits}\n\n"

            f"💰 درخواست‌های برداشت: "
            f"{withdraws}\n\n"

            f"💵 مجموع موجودی کاربران: "
            f"{total_balance:,} DOGS\n\n"

            f"🎮 بازی‌های فعال: "
            f"{active_games}\n\n"

            f"🤖 وضعیت ربات: "
            f"{'🟢 روشن' if data['settings'].get('bot', True) else '🔴 خاموش'}",

            reply_markup=admin_keyboard()

        )

        return

    # -----------------------------------------------------
    # CLOSE
    # -----------------------------------------------------

    if query.data == "admin_close":

        await query.edit_message_text(
            "✅ پنل مدیریت بسته شد."
        )

        return


# =========================================================
# CHECK JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    channel = data["settings"].get(
        "force_channel",
        FORCE_CHANNEL
    )

    group = data["settings"].get(
        "force_group",
        FORCE_GROUP
    )

    missing = []

    try:

        member = await context.bot.get_chat_member(
            channel,
            user.id
        )

        if member.status in (
            "left",
            "kicked"
        ):
            missing.append("channel")

    except Exception:
        pass

    try:

        group_username = group

        if group.startswith(
            "https://t.me/"
        ):

            group_username = (
                "@"
                + group.split(
                    "https://t.me/"
                )[1]
            )

        member = await context.bot.get_chat_member(
            group_username,
            user.id
        )

        if member.status in (
            "left",
            "kicked"
        ):
            missing.append("group")

    except Exception:
        pass

    if missing:

        await query.answer(
            "❌ هنوز در موارد اجباری عضو نیستید.",
            show_alert=True
        )

        return

    await query.edit_message_text(
        "✅ عضویت شما تأیید شد.\n\n"
        "حالا /start را بزنید."
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

        if not is_owner(
            update.effective_user.id
        ):
            return

        status = (
            "🟢 روشن"
            if data["settings"].get(
                "bot",
                True
            )
            else "🔴 خاموش"
        )

        await update.message.reply_text(

            "⚙️ پنل مدیریت\n\n"

            f"🤖 وضعیت ربات: {status}\n"

            f"📢 کانال: "
            f"{data['settings'].get('force_channel', FORCE_CHANNEL)}\n"

            f"👥 گپ: "
            f"{data['settings'].get('force_group', FORCE_GROUP)}",

            reply_markup=admin_keyboard()

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

    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    create_user(user)

    text = (
        update.message.text
        if update.message.text
        else ""
    )

    # خاموش بودن ربات
    if (
        not data["settings"].get(
            "bot",
            True
        )
        and not is_owner(user.id)
    ):

        return

    # برگشت
    if text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

        return

    state = context.user_data.get(
        "state"
    )

    # انتقال مالکیت
    if state == "transfer_owner":

        if not is_owner(user.id):
            return

        try:

            new_owner = int(
                text.strip()
            )

        except Exception:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return

        if new_owner == user.id:

            await update.message.reply_text(
                "❌ این آیدی مالک فعلی است."
            )

            return

        data["owner"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ مالکیت منتقل شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}"

        )

        return

    # واریز اولترا
    if state == "deposit_ultra_receipt":

        await handle_deposit_receipt(
            update,
            context,
            "ultra"
        )

        return

    # واریز صرافی
    if state == "deposit_exchange_receipt":

        await handle_deposit_receipt(
            update,
            context,
            "exchange"
        )

        return

    # مبلغ واریز
    if state == "deposit_amount":

        await handle_deposit_amount(
            update,
            context
        )

        return

    # برداشت آدرس
    if state == "withdraw_address":

        await handle_withdraw_address(
            update,
            context
        )

        return

    # برداشت مبلغ
    if state == "withdraw_amount":

        await handle_withdraw_amount(
            update,
            context
        )

        return

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
            "❌ BOT_TOKEN پیدا نشد."
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

    # DEPOSIT MENU
    app.add_handler(
        CallbackQueryHandler(
            deposit_callback,
            pattern=r"^deposit_(exchange|ultra)$"
        )
    )

    # GAME CALLBACK
    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )

    # FORCE JOIN
    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
        )
    )

    # ADMIN DEPOSIT
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )

    # ADMIN WITHDRAW
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_wd_|no_wd_)"
        )
    )

    # ADMIN PANEL
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # PRIVATE TEXT / PHOTO
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
        f"👑 OWNER: {data['owner']}"
    )

    print(
        f"🎮 GAME: {MIN_GAME} - {MAX_GAME}"
    )

    print(
        f"💰 WITHDRAW MIN: {MIN_WITHDRAW}"
    )

    print(
        "================================="
    )

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
