import os
import json
import time
import traceback
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
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
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

ULTRA_ADDRESS = "@CyyFr"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "data.json"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "settings": {
        "bot": True,
        "channel": "@TAK_BE_T",
        "group": "@TAK_B_ET",
    },
}


# =========================================================
# LOAD / SAVE
# =========================================================

def load_data():

    try:

        if not os.path.exists(DATA_FILE):
            return json.loads(
                json.dumps(DEFAULT_DATA)
            )

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        if not isinstance(data, dict):
            raise ValueError("Invalid data")


        data.setdefault("owner", OWNER_ID)
        data.setdefault("users", {})
        data.setdefault("deposits", {})
        data.setdefault("withdraws", {})
        data.setdefault("settings", {})

        data["settings"].setdefault(
            "bot",
            True
        )

        data["settings"].setdefault(
            "channel",
            "@TAK_BE_T"
        )

        data["settings"].setdefault(
            "group",
            "@TAK_B_ET"
        )

        return data


    except Exception as e:

        print(
            "LOAD ERROR:",
            e
        )

        return json.loads(
            json.dumps(DEFAULT_DATA)
        )


data = load_data()


def save_data():

    try:

        tmp_file = DATA_FILE + ".tmp"

        with open(
            tmp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            tmp_file,
            DATA_FILE
        )

    except Exception as e:

        print(
            "SAVE ERROR:",
            e
        )


# =========================================================
# USERS
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


def get_user(uid):

    return data["users"].get(
        str(uid)
    )


def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    try:

        return int(
            user.get(
                "balance",
                0
            )
        )

    except:

        return 0


def add_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    try:
        amount = int(amount)
    except:
        return False

    user["balance"] = (
        balance(uid) + amount
    )

    save_data()

    return True


def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    try:
        amount = int(amount)
    except:
        return False

    if amount <= 0:
        return False

    if balance(uid) < amount:
        return False

    user["balance"] = (
        balance(uid) - amount
    )

    save_data()

    return True


def is_owner(uid):

    try:

        return int(uid) == int(
            data.get(
                "owner",
                OWNER_ID
            )
        )

    except:

        return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):

    buttons = [

        [
            "💳 واریزی",
            "💰 برداشت",
        ],

        [
            "👤 پروفایل",
            "👥 زیر مجموعه",
        ],

        [
            "🎧 پشتیبانی",
        ],

    ]

    if is_owner(uid):

        buttons.append(
            [
                "⚙️ پنل مدیریت",
            ]
        )

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )


def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🤖 روشن/خاموش ربات",
                callback_data="admin_toggle"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 چنل اجباری",
                callback_data="admin_channel"
            ),

            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="admin_group"
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

    ])


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

    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

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

async def profile(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    u = get_user(user.id)

    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: {u.get('name', '')}\n"

        f"💰 موجودی: "
        f"{balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{u.get('referrals', 0)}",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(
    update,
    context
):

    user = update.effective_user

    if not is_owner(user.id):
        return

    status = (
        "روشن ✅"
        if data["settings"].get("bot", True)
        else "خاموش ❌"
    )

    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت ربات: {status}\n\n"

        f"📢 چنل اجباری: "
        f"{data['settings'].get('channel', 'ندارد')}\n\n"

        f"👥 گپ اجباری: "
        f"{data['settings'].get('group', 'ندارد')}",

        reply_markup=admin_keyboard()

    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user.id):
        return


    if query.data == "admin_toggle":

        current = data["settings"].get(
            "bot",
            True
        )

        data["settings"]["bot"] = not current

        save_data()

        status = (
            "روشن ✅"
            if data["settings"]["bot"]
            else "خاموش ❌"
        )

        await query.edit_message_text(

            "⚙️ پنل مدیریت مالک\n\n"

            f"🤖 وضعیت ربات: {status}\n\n"

            f"📢 چنل اجباری: "
            f"{data['settings'].get('channel')}\n\n"

            f"👥 گپ اجباری: "
            f"{data['settings'].get('group')}",

            reply_markup=admin_keyboard()

        )

        return


    if query.data == "admin_channel":

        context.user_data.clear()

        context.user_data["admin_flow"] = "channel"

        await query.message.reply_text(

            "📢 آیدی چنل اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@channel"

        )

        return


    if query.data == "admin_group":

        context.user_data.clear()

        context.user_data["admin_flow"] = "group"

        await query.message.reply_text(

            "👥 آیدی گپ اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@group"

        )

        return


    if query.data == "admin_owner":

        context.user_data.clear()

        context.user_data["admin_flow"] = "owner"

        await query.message.reply_text(

            "👑 آیدی عددی مالک جدید را ارسال کنید."

        )

        return


    if query.data == "admin_stats":

        users_count = len(
            data["users"]
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

        deposits_count = len(
            data["deposits"]
        )

        withdraws_count = len(
            data["withdraws"]
        )

        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: "
            f"{users_count}\n\n"

            f"💰 مجموع موجودی:\n"
            f"{total_balance:,} DOGS\n\n"

            f"💳 درخواست واریز: "
            f"{deposits_count}\n"

            f"💰 درخواست برداشت: "
            f"{withdraws_count}",

            reply_markup=admin_keyboard()

        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(
    update,
    context
):

    user = update.effective_user

    if not is_owner(user.id):
        return False

    state = context.user_data.get(
        "admin_flow"
    )

    if not state:
        return False

    text = update.message.text.strip()


    if state == "channel":

        if not text.startswith("@"):

            await update.message.reply_text(
                "❌ آیدی چنل باید با @ باشد."
            )

            return True

        data["settings"]["channel"] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ چنل اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                user.id
            )
        )

        return True


    if state == "group":

        if not text.startswith("@"):

            await update.message.reply_text(
                "❌ آیدی گپ باید با @ باشد."
            )

            return True

        data["settings"]["group"] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                user.id
            )
        )

        return True


    if state == "owner":

        try:

            new_owner = int(text)

        except:

            await update.message.reply_text(
                "❌ فقط آیدی عددی ارسال کنید."
            )

            return True

        data["owner"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ مالکیت منتقل شد."
        )

        return True


    return False


# =========================================================
# DEPOSIT MENU
# =========================================================

async def deposit_menu(
    update,
    context
):

    context.user_data.clear()

    await update.message.reply_text(

        "💳 واریز DOGS\n\n"

        "روش واریز را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(
                    "🟣 اولترا",
                    callback_data="deposit_ultra"
                ),

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="deposit_exchange"
                ),

            ]

        ])

    )


# =========================================================
# DEPOSIT METHOD
# =========================================================

async def deposit_method(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if query.data == "deposit_ultra":

        method = "ultra"

    elif query.data == "deposit_exchange":

        method = "exchange"

    else:

        return


    context.user_data.clear()

    context.user_data["flow"] = "deposit_amount"

    context.user_data["deposit_method"] = method


    await query.message.reply_text(

        "💰 مبلغ واریز را ارسال کنید.\n\n"

        f"حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000"

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount_handler(
    update,
    context
):

    if context.user_data.get(
        "flow"
    ) != "deposit_amount":

        return False


    try:

        amount = int(
            update.message.text.strip()
        )

    except:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )

        return True


    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."

        )

        return True


    method = context.user_data.get(
        "deposit_method"
    )

    if method not in (
        "ultra",
        "exchange"
    ):

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده."
        )

        return True


    context.user_data["deposit_amount"] = amount

    context.user_data["flow"] = "deposit_receipt"


    if method == "ultra":

        copy_text = (
            f"ULTRA {amount} DOGS "
            f"{ULTRA_ADDRESS}"
        )

        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📋 متن واریز:\n"

            f"{copy_text}\n\n"

            "روی دکمه زیر بزنید تا متن کپی شود.\n\n"

            "بعد از پرداخت، رسید را ارسال کنید.",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "📋 کپی متن واریز",

                        copy_text=copy_text

                    )

                ]

            ])

        )

    else:

        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📍 ولت:\n"

            f"{EXCHANGE_WALLET}\n\n"

            "روی دکمه زیر بزنید تا ولت کپی شود.\n\n"

            "بعد از پرداخت، رسید را ارسال کنید.",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "📋 کپی ولت",

                        copy_text=EXCHANGE_WALLET

                    )

                ]

            ])

        )


    return True


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

async def deposit_receipt_handler(
    update,
    context
):

    if context.user_data.get(
        "flow"
    ) != "deposit_receipt":

        return False


    user = update.effective_user

    amount = context.user_data.get(
        "deposit_amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )


    if not amount or method not in (
        "ultra",
        "exchange"
    ):

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده."
        )

        return True


    receipt = None

    receipt_type = None


    if update.message.photo:

        receipt_type = "photo"

        receipt = (
            update.message.photo[-1].file_id
        )


    elif update.message.text:

        receipt_type = "text"

        receipt = (
            update.message.text.strip()
        )


    else:

        await update.message.reply_text(

            "❌ عکس یا متن رسید ارسال کنید."

        )

        return True


    request_id = (

        f"DEP_{user.id}_"
        f"{int(time.time())}_"
        f"{len(data['deposits']) + 1}"

    )


    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "method": method,

        "receipt": receipt,

        "receipt_type": receipt_type,

        "status": "pending",

        "created": datetime.now().isoformat(),

    }


    save_data()


    context.user_data.clear()


    await update.message.reply_text(

        "✅ رسید شما ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "⏳ منتظر تأیید مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )


    username = (

        f"@{user.username}"

        if user.username

        else "ندارد"

    )


    method_text = (
        "🟣 اولترا"
        if method == "ultra"
        else "🏦 صرافی"
    )


    caption = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n"

        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method_text}\n\n"

        f"🆔 درخواست:\n"
        f"{request_id}"

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تأیید واریز",

                callback_data=
                f"approve_dep_{request_id}"

            ),

            InlineKeyboardButton(

                "❌ رد واریز",

                callback_data=
                f"reject_dep_{request_id}"

            )

        ]

    ])


    try:

        if receipt_type == "photo":

            await context.bot.send_photo(

                chat_id=data["owner"],

                photo=receipt,

                caption=caption,

                reply_markup=buttons

            )

        else:

            await context.bot.send_message(

                chat_id=data["owner"],

                text=(
                    caption
                    +
                    "\n\n📎 رسید:\n"
                    +
                    receipt
                ),

                reply_markup=buttons

            )

    except Exception as e:

        print(
            "DEPOSIT OWNER SEND ERROR:",
            e
        )


    return True


# =========================================================
# WITHDRAW MENU
# =========================================================

async def withdraw_menu(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما:\n"
            f"{balance(user.id):,} DOGS\n\n"

            f"حداقل برداشت:\n"
            f"{MIN_WITHDRAW:,} DOGS"

        )

        return


    context.user_data["flow"] = (
        "withdraw_amount"
    )


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید.\n\n"

        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "مثال:\n"
        "10000"

    )


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

async def withdraw_amount_handler(
    update,
    context
):

    if context.user_data.get(
        "flow"
    ) != "withdraw_amount":

        return False


    user = update.effective_user


    try:

        amount = int(
            update.message.text.strip()
        )

    except:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )

        return True


    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."

        )

        return True


    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return True


    context.user_data["withdraw_amount"] = amount

    context.user_data["flow"] = (
        "withdraw_address"
    )


    await update.message.reply_text(

        "📍 آدرس یا آیدی دریافت DOGS را ارسال کنید."

    )


    return True


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

async def withdraw_address_handler(
    update,
    context
):

    if context.user_data.get(
        "flow"
    ) != "withdraw_address":

        return False


    user = update.effective_user


    if not update.message.text:

        return True


    address = update.message.text.strip()

    amount = context.user_data.get(
        "withdraw_amount"
    )


    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست برداشت منقضی شده."
        )

        return True


    if not address:

        await update.message.reply_text(
            "❌ آدرس را ارسال کنید."
        )

        return True


    # کسر موجودی فقط یک بار
    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست یا خطا در کسر موجودی."
        )

        context.user_data.clear()

        return True


    request_id = (

        f"WD_{user.id}_"
        f"{int(time.time())}_"
        f"{len(data['withdraws']) + 1}"

    )


    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "address": address,

        "status": "pending",

        "created": datetime.now().isoformat(),

    }


    save_data()


    context.user_data.clear()


    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"📍 آدرس:\n{address}\n\n"

        "⏳ منتظر تأیید مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تأیید برداشت",

                callback_data=
                f"approve_wd_{request_id}"

            ),

            InlineKeyboardButton(

                "❌ رد برداشت",

                callback_data=
                f"reject_wd_{request_id}"

            )

        ]

    ])


    try:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=(

                "💰 برداشت جدید\n\n"

                f"👤 نام: {user.first_name}\n"

                f"🆔 آیدی: {user.id}\n"

                f"🔹 یوزرنیم: "
                f"@{user.username}"
                if user.username
                else
                "🔹 یوزرنیم: ندارد"

            )
            +
            (

                f"\n\n💰 مبلغ: "
                f"{amount:,} DOGS\n\n"

                f"📍 آدرس:\n"
                f"{address}\n\n"

                f"🆔 درخواست:\n"
                f"{request_id}"

            ),

            reply_markup=buttons

        )

    except Exception as e:

        print(
            "WITHDRAW OWNER SEND ERROR:",
            e
        )


    return True


# =========================================================
# APPROVE / REJECT
# =========================================================

async def approve_reject(
    update,
    context
):

    query = update.callback_query

    await query.answer()


    if not is_owner(
        query.from_user.id
    ):

        return


    parts = query.data.split("_")


    if len(parts) < 3:

        return


    action = parts[0]

    kind = parts[1]

    request_id = "_".join(
        parts[2:]
    )


    # =====================================================
    # DEPOSIT
    # =====================================================

    if kind == "dep":

        req = data["deposits"].get(
            request_id
        )


        if not req:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return


        if req.get("status") != "pending":

            await query.edit_message_text(

                "⚠️ این درخواست قبلاً بررسی شده."

            )

            return


        uid = req["user_id"]


        if action == "approve":

            if not add_balance(
                uid,
                req["amount"]
            ):

                await query.edit_message_text(
                    "❌ خطا در اضافه کردن موجودی."
                )

                return


            req["status"] = "approved"

            req["approved_at"] = (
                datetime.now().isoformat()
            )

            save_data()


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ واریز شما تأیید شد.\n\n"

                        f"💰 مبلغ:\n"
                        f"+{req['amount']:,} DOGS\n\n"

                        f"💳 موجودی:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "USER DEPOSIT MESSAGE ERROR:",
                    e
                )


            await query.edit_message_text(

                "✅ واریز تأیید شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS"

            )


        elif action == "reject":

            req["status"] = "rejected"

            req["rejected_at"] = (
                datetime.now().isoformat()
            )

            save_data()


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "❌ واریز شما رد شد.\n\n"

                        f"💰 مبلغ: "
                        f"{req['amount']:,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "USER DEPOSIT REJECT ERROR:",
                    e
                )


            await query.edit_message_text(

                "❌ واریز رد شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS"

            )

        return


    # =====================================================
    # WITHDRAW
    # =====================================================

    if kind == "wd":

        req = data["withdraws"].get(
            request_id
        )


        if not req:

            await query.edit_message_text(
                "❌ درخواست برداشت پیدا نشد."
            )

            return


        if req.get("status") != "pending":

            await query.edit_message_text(

                "⚠️ این درخواست قبلاً بررسی شده."

            )

            return


        uid = req["user_id"]


        if action == "approve":

            req["status"] = "approved"

            req["approved_at"] = (
                datetime.now().isoformat()
            )

            save_data()


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ برداشت شما تأیید شد.\n\n"

                        f"💰 مبلغ:\n"
                        f"{req['amount']:,} DOGS\n\n"

                        f"📍 آدرس:\n"
                        f"{req['address']}"

                    )

                )

            except Exception as e:

                print(
                    "USER WITHDRAW MESSAGE ERROR:",
                    e
                )


            await query.edit_message_text(

                "✅ برداشت تأیید شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS\n\n"

                f"📍 آدرس:\n"
                f"{req['address']}"

            )


        elif action == "reject":

            # فقط در صورت رد، پول برگردد
            if not add_balance(
                uid,
                req["amount"]
            ):

                await query.edit_message_text(
                    "❌ خطا در برگشت موجودی."
                )

                return


            req["status"] = "rejected"

            req["rejected_at"] = (
                datetime.now().isoformat()
            )

            save_data()


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "❌ برداشت شما رد شد.\n\n"

                        f"💰 مبلغ "
                        f"{req['amount']:,} DOGS "
                        "به موجودی شما برگشت داده شد.\n\n"

                        f"💳 موجودی:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "USER WITHDRAW REJECT ERROR:",
                    e
                )


            await query.edit_message_text(

                "❌ برداشت رد شد.\n\n"

                f"💰 مبلغ "
                f"{req['amount']:,} DOGS "
                "برگشت داده شد."

            )

        return


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update,
    context
):

    context.user_data.clear()

    context.user_data["flow"] = "support"


    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیامت رو ارسال کن."

    )


async def support_message(
    update,
    context
):

    if context.user_data.get(
        "flow"
    ) != "support":

        return False


    user = update.effective_user


    if not update.message.text:

        await update.message.reply_text(
            "❌ لطفاً پیام متنی ارسال کنید."
        )

        return True


    try:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=(

                "🎧 پیام پشتیبانی جدید\n\n"

                f"👤 نام: {user.first_name}\n"

                f"🆔 آیدی: {user.id}\n"

                f"🔹 یوزرنیم: "
                f"@{user.username}"
                if user.username
                else
                "🔹 یوزرنیم: ندارد"

            )
            +
            (

                "\n\n💬 پیام:\n"
                +
                update.message.text

            )

        )

    except Exception as e:

        print(
            "SUPPORT ERROR:",
            e
        )


        await update.message.reply_text(
            "❌ ارسال پیام ناموفق بود."
        )

        return True


    context.user_data.clear()


    await update.message.reply_text(

        "✅ پیام شما برای پشتیبانی ارسال شد.",

        reply_markup=main_keyboard(
            user.id
        )

    )


    return True


# =========================================================
# REFERRAL
# =========================================================

async def referrals(
    update,
    context
):

    user = update.effective_user

    create_user(user)


    try:

        bot_info = await context.bot.get_me()

        bot_username = bot_info.username

    except:

        bot_username = ""


    link = (

        f"https://t.me/{bot_username}"
        f"?start=ref_{user.id}"

    )


    u = get_user(user.id)


    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه:\n"
        f"{u.get('referrals', 0)}"

    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context
):

    if not update.message:
        return

    if not update.message.text:
        return


    text = update.message.text.strip()


    # -----------------------------------------------------
    # ADMIN INPUT
    # -----------------------------------------------------

    if await admin_text(
        update,
        context
    ):

        return


    # -----------------------------------------------------
    # SUPPORT MESSAGE
    # -----------------------------------------------------

    if await support_message(
        update,
        context
    ):

        return


    # -----------------------------------------------------
    # ACTIVE FLOWS
    # -----------------------------------------------------

    if await deposit_amount_handler(
        update,
        context
    ):

        return


    if await deposit_receipt_handler(
        update,
        context
    ):

        return


    if await withdraw_amount_handler(
        update,
        context
    ):

        return


    if await withdraw_address_handler(
        update,
        context
    ):

        return


    # -----------------------------------------------------
    # MAIN BUTTONS
    # -----------------------------------------------------

    if text == "💳 واریزی":

        await deposit_menu(
            update,
            context
        )

        return


    if text == "💰 برداشت":

        await withdraw_menu(
            update,
            context
        )

        return


    if text == "👤 پروفایل":

        await profile(
            update,
            context
        )

        return


    if text == "👥 زیر مجموعه":

        await referrals(
            update,
            context
        )

        return


    if text == "🎧 پشتیبانی":

        await support(
            update,
            context
        )

        return


    if text == "⚙️ پنل مدیریت":

        await admin_panel(
            update,
            context
        )

        return


# =========================================================
# PHOTO ROUTER
# =========================================================

async def photo_router(
    update,
    context
):

    if not update.message:
        return


    if context.user_data.get(
        "flow"
    ) == "deposit_receipt":

        await deposit_receipt_handler(
            update,
            context
        )

        return


    await update.message.reply_text(
        "❌ در حال حاضر منتظر عکس رسید واریز نیستم."
    )


# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "========== BOT ERROR =========="
    )

    print(
        "ERROR:",
        context.error
    )

    traceback.print_exc()

    print(
        "==============================="
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN is not set."
        )

        return


    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # -----------------------------------------------------
    # DEPOSIT BUTTONS
    # -----------------------------------------------------

    app.add_handler(

        CallbackQueryHandler(

            deposit_method,

            pattern=r"^deposit_(ultra|exchange)$"

        )

    )


    # -----------------------------------------------------
    # ADMIN BUTTONS
    # -----------------------------------------------------

    app.add_handler(

        CallbackQueryHandler(

            admin_callback,

            pattern=r"^admin_(toggle|channel|group|stats|owner)$"

        )

    )


    # -----------------------------------------------------
    # APPROVE / REJECT
    # کاملاً جدا از واریز و برداشت
    # -----------------------------------------------------

    app.add_handler(

        CallbackQueryHandler(

            approve_reject,

            pattern=r"^(approve|reject)_(dep|wd)_"

        )

    )


    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_router

        )

    )


    # -----------------------------------------------------
    # PHOTO
    # -----------------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_router

        )

    )


    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    app.add_error_handler(
        error_handler
    )


    print(
        "================================"
    )

    print(
        "BOT STARTED"
    )

    print(
        "================================"
    )


    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
