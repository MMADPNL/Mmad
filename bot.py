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

ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

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
# DATA
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

            loaded = json.load(f)

        if not isinstance(loaded, dict):
            return json.loads(
                json.dumps(DEFAULT_DATA)
            )

        for key in DEFAULT_DATA:

            if key not in loaded:
                loaded[key] = json.loads(
                    json.dumps(DEFAULT_DATA[key])
                )

        return loaded

    except Exception as e:

        print("LOAD ERROR:", e)

        return json.loads(
            json.dumps(DEFAULT_DATA)
        )


data = load_data()


def save_data():

    try:

        temp_file = DATA_FILE + ".tmp"

        with open(
            temp_file,
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
            temp_file,
            DATA_FILE
        )

    except Exception as e:

        print("SAVE ERROR:", e)


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

    try:

        return int(uid) == int(
            data.get(
                "owner",
                OWNER_ID
            )
        )

    except Exception:

        return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):

    buttons = [

        [
            "💳 واریزی",
            "💰 برداشت"
        ],

        [
            "👤 پروفایل",
            "👥 زیر مجموعه"
        ],

        [
            "🎧 پشتیبانی"
        ],
    ]

    if is_owner(uid):

        buttons.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )


def deposit_keyboard():

    return InlineKeyboardMarkup([

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
            ),

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


def request_keyboard(request_id, kind):

    if kind == "deposit":

        return InlineKeyboardMarkup([

            [

                InlineKeyboardButton(
                    "✅ تأیید واریز",
                    callback_data=f"approve_dep_{request_id}"
                ),

                InlineKeyboardButton(
                    "❌ رد واریز",
                    callback_data=f"reject_dep_{request_id}"
                ),

            ]

        ])

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تأیید برداشت",
                callback_data=f"approve_wd_{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"reject_wd_{request_id}"
            ),

        ]

    ])


# =========================================================
# START
# =========================================================

async def start(update, context):

    user = update.effective_user

    create_user(user)

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

async def profile(update, context):

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
# DEPOSIT MENU
# =========================================================

async def deposit_menu(update, context):

    context.user_data.clear()

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"

        "روش واریز را انتخاب کنید:",

        reply_markup=deposit_keyboard()
    )


# =========================================================
# DEPOSIT METHOD
# =========================================================

async def deposit_method(update, context):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    create_user(user)

    if query.data == "deposit_ultra":

        context.user_data["deposit_method"] = "ultra"

    elif query.data == "deposit_exchange":

        context.user_data["deposit_method"] = "exchange"

    else:

        return

    context.user_data["flow"] = (
        "deposit_amount"
    )

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

    text = (
        update.message.text or ""
    ).strip()

    try:

        amount = int(text)

    except Exception:

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

    context.user_data[
        "deposit_amount"
    ] = amount

    context.user_data[
        "flow"
    ] = "deposit_receipt"

    method = context.user_data.get(
        "deposit_method"
    )

    # -----------------------------------------------------
    # ULTRA
    # -----------------------------------------------------

    if method == "ultra":

        copy_text = (
            f"ULTRA {amount} DOGS\n"
            f"{ULTRA_ADDRESS}"
        )

        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را به "
            "این آیدی بزنید:\n\n"

            f"{ULTRA_ADDRESS}\n\n"

            "فرصت مثال:\n\n"

            f"\"ULTRA {amount} DOGS\"\n"

            f"\"{ULTRA_ADDRESS}\"\n\n"

            "پس از ارسال، رسید را در همین "
            "چت ارسال کنید.\n\n"

            "📸 شات یا لینک هش تراکنش را "
            "بفرستید.\n\n"

            "پس از تأیید ادمین، مبلغ شما "
            "واریز خواهد شد ✅",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "📋 کپی اطلاعات واریز",
                        copy_text=copy_text
                    )

                ]

            ])
        )

        return True

    # -----------------------------------------------------
    # EXCHANGE
    # -----------------------------------------------------

    if method == "exchange":

        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را از "
            "طریق صرافی به این ولت بزنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            f"مبلغ: {amount:,} DOGS\n\n"

            "پس از ارسال، شات یا لینک هش "
            "تراکنش را در همین چت ارسال کنید.\n\n"

            "پس از تأیید ادمین، مبلغ شما "
            "واریز خواهد شد ✅",

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

    if not amount or not method:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده است."
        )

        return True

    receipt = None
    receipt_type = None

    # عکس
    if update.message.photo:

        receipt_type = "photo"

        receipt = (
            update.message.photo[-1].file_id
        )

    # متن / لینک هش
    elif update.message.text:

        receipt_type = "text"

        receipt = (
            update.message.text.strip()
        )

    else:

        await update.message.reply_text(

            "❌ لطفاً شات یا لینک هش "
            "تراکنش را ارسال کنید."
        )

        return True

    request_id = (
        f"DEP_{user.id}_{int(time.time())}"
    )

    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": int(amount),

        "method": method,

        "receipt": receipt,

        "receipt_type": receipt_type,

        "status": "pending",

        "created_at": datetime.now().isoformat(),

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ رسید ثبت شد.\n\n"

        "⏳ منتظر تأیید ادمین باشید.\n\n"

        f"💰 مبلغ: {amount:,} DOGS"

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

        f"🆔 کد درخواست:\n"
        f"{request_id}"

    )

    buttons = request_keyboard(
        request_id,
        "deposit"
    )

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
                    "\n\n📎 رسید / هش:\n"
                    +
                    receipt
                ),

                reply_markup=buttons
            )

    except Exception as e:

        print(
            "SEND DEPOSIT OWNER ERROR:",
            e
        )

    return True


# =========================================================
# WITHDRAW MENU
# =========================================================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()

    current = balance(user.id)

    if current < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{current:,} DOGS\n\n"

            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS"
        )

        return

    context.user_data["flow"] = (
        "withdraw_amount"
    )

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید.\n\n"

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

    except Exception:

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

    context.user_data[
        "withdraw_amount"
    ] = amount

    context.user_data[
        "flow"
    ] = "withdraw_address"

    await update.message.reply_text(
        "📍 آدرس یا آیدی دریافت DOGS "
        "را ارسال کنید."
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

    address = (
        update.message.text or ""
    ).strip()

    amount = context.user_data.get(
        "withdraw_amount"
    )

    if not amount or not address:

        return True

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return True

    request_id = (
        f"WD_{user.id}_{int(time.time())}"
    )

    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": int(amount),

        "address": address,

        "status": "pending",

        "created_at": datetime.now().isoformat(),

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📍 آدرس:\n{address}\n\n"

        "⏳ منتظر تأیید ادمین باشید."
    )

    buttons = request_keyboard(
        request_id,
        "withdraw"
    )

    try:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=(

                "💰 برداشت جدید\n\n"

                f"👤 کاربر: "
                f"{user.first_name}\n"

                f"🆔 آیدی: {user.id}\n\n"

                f"💰 مبلغ: "
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
            "SEND WITHDRAW OWNER ERROR:",
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

    try:

        await query.answer()

    except Exception:
        pass

    admin_id = query.from_user.id

    if not is_owner(admin_id):

        try:
            await query.answer(
                "❌ فقط مالک اجازه دارد.",
                show_alert=True
            )
        except Exception:
            pass

        return

    callback = query.data

    # -----------------------------------------------------
    # APPROVE DEPOSIT
    # -----------------------------------------------------

    if callback.startswith(
        "approve_dep_"
    ):

        request_id = callback[
            len("approve_dep_"):
        ]

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

                "⚠️ این درخواست قبلاً "
                "بررسی شده است."
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

        add_balance(
            uid,
            amount
        )

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

                    f"💰 مبلغ: "
                    f"+{amount:,} DOGS\n\n"

                    f"💳 موجودی جدید:\n"
                    f"{balance(uid):,} DOGS"
                )
            )

        except Exception as e:

            print(
                "SEND USER DEPOSIT APPROVE ERROR:",
                e
            )

        await query.edit_message_text(

            "✅ واریز تأیید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"🆔 درخواست:\n{request_id}"
        )

        return

    # -----------------------------------------------------
    # REJECT DEPOSIT
    # -----------------------------------------------------

    if callback.startswith(
        "reject_dep_"
    ):

        request_id = callback[
            len("reject_dep_"):
        ]

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

                "⚠️ این درخواست قبلاً "
                "بررسی شده است."
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

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
                    f"{amount:,} DOGS"
                )
            )

        except Exception as e:

            print(
                "SEND USER DEPOSIT REJECT ERROR:",
                e
            )

        await query.edit_message_text(

            "❌ واریز رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"🆔 درخواست:\n{request_id}"
        )

        return

    # -----------------------------------------------------
    # APPROVE WITHDRAW
    # -----------------------------------------------------

    if callback.startswith(
        "approve_wd_"
    ):

        request_id = callback[
            len("approve_wd_"):
        ]

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

                "⚠️ این درخواست قبلاً "
                "بررسی شده است."
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

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

                    f"💰 مبلغ: "
                    f"{amount:,} DOGS"
                )
            )

        except Exception as e:

            print(
                "SEND USER WITHDRAW APPROVE ERROR:",
                e
            )

        await query.edit_message_text(

            "✅ برداشت تأیید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"📍 آدرس:\n"
            f"{req.get('address', '')}\n\n"

            f"🆔 درخواست:\n{request_id}"
        )

        return

    # -----------------------------------------------------
    # REJECT WITHDRAW
    # -----------------------------------------------------

    if callback.startswith(
        "reject_wd_"
    ):

        request_id = callback[
            len("reject_wd_"):
        ]

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

                "⚠️ این درخواست قبلاً "
                "بررسی شده است."
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

        # برگشت پول
        add_balance(
            uid,
            amount
        )

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
                    f"{amount:,} DOGS "
                    "به موجودی شما برگشت داده شد.\n\n"

                    f"💳 موجودی:\n"
                    f"{balance(uid):,} DOGS"
                )
            )

        except Exception as e:

            print(
                "SEND USER WITHDRAW REJECT ERROR:",
                e
            )

        await query.edit_message_text(

            "❌ برداشت رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "💳 مبلغ به موجودی کاربر "
            "برگشت داده شد."
        )

        return


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

    bot_status = (
        "روشن ✅"
        if data["settings"].get(
            "bot",
            True
        )
        else "خاموش ❌"
    )

    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت ربات: {bot_status}\n\n"

        f"📢 چنل اجباری: "
        f"{data['settings'].get('channel', 'تنظیم نشده')}\n\n"

        f"👥 گپ اجباری: "
        f"{data['settings'].get('group', 'تنظیم نشده')}",

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

    if not is_owner(
        query.from_user.id
    ):
        return

    action = query.data

    # -----------------------------------------------------
    # TOGGLE
    # -----------------------------------------------------

    if action == "admin_toggle":

        current = data["settings"].get(
            "bot",
            True
        )

        data["settings"]["bot"] = (
            not current
        )

        save_data()

        status = (
            "روشن ✅"
            if data["settings"]["bot"]
            else "خاموش ❌"
        )

        await query.edit_message_text(

            "🤖 وضعیت ربات تغییر کرد.\n\n"

            f"وضعیت فعلی: {status}",

            reply_markup=admin_keyboard()
        )

        return

    # -----------------------------------------------------
    # CHANNEL
    # -----------------------------------------------------

    if action == "admin_channel":

        context.user_data[
            "admin_flow"
        ] = "channel"

        await query.message.reply_text(

            "📢 آیدی چنل اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@TAK_BE_T\n\n"

            "برای حذف اجباری بودن:\n"
            "خاموش"
        )

        return

    # -----------------------------------------------------
    # GROUP
    # -----------------------------------------------------

    if action == "admin_group":

        context.user_data[
            "admin_flow"
        ] = "group"

        await query.message.reply_text(

            "👥 آیدی گپ اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@TAK_B_ET\n\n"

            "برای حذف اجباری بودن:\n"
            "خاموش"
        )

        return

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    if action == "admin_stats":

        users_count = len(
            data["users"]
        )

        total_balance = sum(

            int(
                user.get(
                    "balance",
                    0
                )
            )

            for user in data["users"].values()
        )

        deposits_count = len(
            data["deposits"]
        )

        withdraws_count = len(
            data["withdraws"]
        )

        pending_deposits = sum(

            1

            for x in data["deposits"].values()

            if x.get("status") == "pending"
        )

        pending_withdraws = sum(

            1

            for x in data["withdraws"].values()

            if x.get("status") == "pending"
        )

        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: "
            f"{users_count}\n\n"

            f"💰 مجموع موجودی: "
            f"{total_balance:,} DOGS\n\n"

            f"💳 کل واریزی‌ها: "
            f"{deposits_count}\n"

            f"⏳ واریزی در انتظار: "
            f"{pending_deposits}\n\n"

            f"💰 کل برداشت‌ها: "
            f"{withdraws_count}\n"

            f"⏳ برداشت در انتظار: "
            f"{pending_withdraws}",

            reply_markup=admin_keyboard()
        )

        return

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    if action == "admin_owner":

        context.user_data[
            "admin_flow"
        ] = "owner"

        await query.message.reply_text(

            "👑 آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789"
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

    text = (
        update.message.text or ""
    ).strip()

    # CHANNEL
    if state == "channel":

        if text.lower() == "خاموش":

            data["settings"]["channel"] = ""

        else:

            data["settings"]["channel"] = text

        save_data()

        context.user_data.pop(
            "admin_flow",
            None
        )

        await update.message.reply_text(
            "✅ تنظیم چنل اجباری ذخیره شد."
        )

        return True

    # GROUP
    if state == "group":

        if text.lower() == "خاموش":

            data["settings"]["group"] = ""

        else:

            data["settings"]["group"] = text

        save_data()

        context.user_data.pop(
            "admin_flow",
            None
        )

        await update.message.reply_text(
            "✅ تنظیم گپ اجباری ذخیره شد."
        )

        return True

    # OWNER
    if state == "owner":

        try:

            new_owner = int(text)

        except Exception:

            await update.message.reply_text(
                "❌ آیدی مالک باید عددی باشد."
            )

            return True

        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )

            return True

        data["owner"] = new_owner

        save_data()

        context.user_data.pop(
            "admin_flow",
            None
        )

        await update.message.reply_text(

            "✅ مالکیت منتقل شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}"
        )

        return True

    return False


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update,
    context
):

    context.user_data.clear()

    context.user_data[
        "flow"
    ] = "support"

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

    if update.message.text:

        message_text = (
            update.message.text
        )

        try:

            await context.bot.send_message(

                chat_id=data["owner"],

                text=(

                    "🎧 پیام پشتیبانی جدید\n\n"

                    f"👤 نام: "
                    f"{user.first_name}\n"

                    f"🆔 آیدی: "
                    f"{user.id}\n"

                    f"🔹 یوزرنیم: "
                    f"@{user.username}"
                    if user.username
                    else
                    "🎧 پیام پشتیبانی جدید\n\n"
                    f"👤 نام: {user.first_name}\n"
                    f"🆔 آیدی: {user.id}\n"
                    f"🔹 یوزرنیم: ندارد"
                )
                +
                f"\n\n💬 پیام:\n{message_text}"
            )

        except Exception as e:

            print(
                "SUPPORT SEND ERROR:",
                e
            )

    elif update.message.photo:

        try:

            await context.bot.send_photo(

                chat_id=data["owner"],

                photo=update.message.photo[-1].file_id,

                caption=(

                    "🎧 عکس پشتیبانی جدید\n\n"

                    f"👤 نام: "
                    f"{user.first_name}\n"

                    f"🆔 آیدی: "
                    f"{user.id}"
                )
            )

        except Exception as e:

            print(
                "SUPPORT PHOTO ERROR:",
                e
            )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما ارسال شد."
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

    username = (
        await context.bot.get_me()
    ).username

    link = (
        f"https://t.me/{username}"
        f"?start=ref_{user.id}"
    )

    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه: "
        f"{data['users'][str(user.id)].get('referrals', 0)}"
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

    user = update.effective_user

    create_user(user)

    text = (
        update.message.text or ""
    ).strip()

    # -----------------------------------------------------
    # ADMIN INPUT
    # -----------------------------------------------------

    if await admin_text(
        update,
        context
    ):

        return

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

    if context.user_data.get(
        "flow"
    ) == "support":

        await support_message(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # DEPOSIT AMOUNT
    # -----------------------------------------------------

    if context.user_data.get(
        "flow"
    ) == "deposit_amount":

        await deposit_amount_handler(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # DEPOSIT RECEIPT TEXT
    # -----------------------------------------------------

    if context.user_data.get(
        "flow"
    ) == "deposit_receipt":

        await deposit_receipt_handler(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # WITHDRAW AMOUNT
    # -----------------------------------------------------

    if context.user_data.get(
        "flow"
    ) == "withdraw_amount":

        await withdraw_amount_handler(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # WITHDRAW ADDRESS
    # -----------------------------------------------------

    if context.user_data.get(
        "flow"
    ) == "withdraw_address":

        await withdraw_address_handler(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # MENU
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

    user = update.effective_user

    create_user(user)

    # رسید واریز
    if context.user_data.get(
        "flow"
    ) == "deposit_receipt":

        await deposit_receipt_handler(
            update,
            context
        )

        return

    # پشتیبانی
    if context.user_data.get(
        "flow"
    ) == "support":

        await support_message(
            update,
            context
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "================ BOT ERROR ================"
    )

    print(
        repr(context.error)
    )

    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__
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

    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # DEPOSIT BUTTONS
    app.add_handler(
        CallbackQueryHandler(
            deposit_method,
            pattern=r"^deposit_(ultra|exchange)$"
        )
    )

    # ADMIN BUTTONS
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_(toggle|channel|group|stats|owner)$"
        )
    )

    # APPROVE / REJECT
    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern=r"^(approve|reject)_(dep|wd)_.+$"
        )
    )

    # PHOTO
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )

    # TEXT
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    # ERRORS
    app.add_error_handler(
        error_handler
    )

    print(
        "================================="
    )

    print(
        "BOT STARTED"
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
