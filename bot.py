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
            return json.loads(json.dumps(DEFAULT_DATA))

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            loaded = json.load(f)

        # جلوگیری از خراب شدن ساختار در صورت قدیمی بودن فایل
        if "owner" not in loaded:
            loaded["owner"] = OWNER_ID

        if "users" not in loaded:
            loaded["users"] = {}

        if "deposits" not in loaded:
            loaded["deposits"] = {}

        if "withdraws" not in loaded:
            loaded["withdraws"] = {}

        if "settings" not in loaded:
            loaded["settings"] = {}

        if "bot" not in loaded["settings"]:
            loaded["settings"]["bot"] = True

        if "channel" not in loaded["settings"]:
            loaded["settings"]["channel"] = "@TAK_BE_T"

        if "group" not in loaded["settings"]:
            loaded["settings"]["group"] = "@TAK_B_ET"

        return loaded

    except Exception as e:

        print("LOAD ERROR:", e)

        return json.loads(json.dumps(DEFAULT_DATA))


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

    return data["users"].get(str(uid))


def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    try:
        return int(user.get("balance", 0))
    except:
        return 0


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
            data.get("owner", OWNER_ID)
        )
    except:
        return False


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
        resize_keyboard=True,
    )


def admin_keyboard():

    status = (
        "روشن ✅"
        if bot_is_on()
        else "خاموش ❌"
    )

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                f"🤖 ربات: {status}",
                callback_data="admin_toggle_bot",
            )
        ],

        [
            InlineKeyboardButton(
                "📢 چنل اجباری",
                callback_data="admin_channel",
            ),

            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="admin_group",
            ),
        ],

        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="admin_stats",
            )
        ],

        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_transfer",
            )
        ],

    ])


def deposit_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🟣 اولترا",
                callback_data="deposit_ultra",
            ),

            InlineKeyboardButton(
                "🏦 صرافی",
                callback_data="deposit_exchange",
            ),
        ]

    ])


def request_keyboard(request_id):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve_{request_id}",
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{request_id}",
            ),
        ]

    ])


# =========================================================
# SAFE BOT CHECK
# =========================================================

async def check_bot_status(update):

    user = update.effective_user

    if not user:
        return True

    if is_owner(user.id):
        return True

    if not bot_is_on():

        if update.message:

            await update.message.reply_text(
                "🔴 ربات موقتاً خاموش است."
            )

        return False

    return True


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await check_bot_status(update):
        return

    user = update.effective_user

    create_user(user)

    # پاک کردن وضعیت‌های قبلی
    context.user_data.clear()

    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n\n"

        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:",

        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(update, context):

    if not await check_bot_status(update):
        return

    user = update.effective_user

    create_user(user)

    u = get_user(user.id)

    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: {u.get('name', '')}\n"

        f"💰 موجودی: {balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{u.get('referrals', 0)}",

        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# REFERRAL
# =========================================================

async def referrals(update, context):

    if not await check_bot_status(update):
        return

    user = update.effective_user

    create_user(user)

    bot_username = context.bot.username

    link = (
        f"https://t.me/{bot_username}"
        f"?start=ref_{user.id}"
    )

    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"👥 تعداد: "
        f"{get_user(user.id).get('referrals', 0)}",

        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(update, context):

    if not await check_bot_status(update):
        return

    context.user_data.clear()

    context.user_data["flow"] = "support"

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیامت رو ارسال کن."

    )


async def support_message(update, context):

    if context.user_data.get("flow") != "support":
        return False

    user = update.effective_user

    text = update.message.text or ""

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "🎧 پیام پشتیبانی جدید\n\n"

            f"👤 نام: {user.first_name}\n"

            f"🆔 آیدی: {user.id}\n"

            f"🔹 یوزرنیم: {username}\n\n"

            f"💬 پیام:\n{text}"

        )

    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ پیام شما برای پشتیبانی ارسال شد."
    )

    return True


# =========================================================
# DEPOSIT MENU
# =========================================================

async def deposit_menu(update, context):

    if not await check_bot_status(update):
        return

    context.user_data.clear()

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"

        "روش واریز را انتخاب کنید:",

        reply_markup=deposit_keyboard(),

    )


# =========================================================
# DEPOSIT METHOD
# =========================================================

async def deposit_method(update, context):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user.id) and not bot_is_on():

        await query.answer(
            "🔴 ربات خاموش است.",
            show_alert=True,
        )

        return

    if query.data == "deposit_ultra":

        context.user_data.clear()

        context.user_data["deposit_method"] = "ultra"

        context.user_data["flow"] = "deposit_amount"

    elif query.data == "deposit_exchange":

        context.user_data.clear()

        context.user_data["deposit_method"] = "exchange"

        context.user_data["flow"] = "deposit_amount"

    else:
        return

    await query.message.reply_text(

        "💰 مقدار DOGS را وارد کنید.\n\n"

        f"حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000"

    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount_handler(update, context):

    if context.user_data.get("flow") != "deposit_amount":
        return False

    user = update.effective_user

    try:

        amount = int(
            update.message.text.strip()
        )

    except:

        await update.message.reply_text(
            "❌ فقط مقدار عددی وارد کنید."
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

    context.user_data["deposit_amount"] = amount

    context.user_data["flow"] = "deposit_receipt"

    # =====================================================
    # ULTRA
    # =====================================================

    if method == "ultra":

        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"

            f"{ULTRA_ADDRESS}\n\n"

            "فرصت مثال:\n\n"

            '"ULTRA 5000 DOGS"\n'
            '"@CyyFr"\n\n'

            "پس از ارسال، رسید را در همین چت ارسال کنید.\n\n"

            "📸 شات یا پیام تراکنش را بفرستید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"

        )

    # =====================================================
    # EXCHANGE
    # =====================================================

    elif method == "exchange":

        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را از طریق صرافی "
            "به این ولت بزنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            f"مبلغ: {amount:,} DOGS\n\n"

            "پس از ارسال، شات یا لینک هش تراکنش "
            "را در همین چت ارسال کنید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"

        )

    return True


# =========================================================
# CREATE DEPOSIT
# =========================================================

async def create_deposit_request(
    update,
    context,
    receipt,
    receipt_type,
):

    user = update.effective_user

    amount = context.user_data.get(
        "deposit_amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )

    if not amount or not method:

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده است."
        )

        context.user_data.clear()

        return True

    # ID بسیار یکتا
    request_id = (
        f"DEP_"
        f"{user.id}_"
        f"{int(time.time())}_"
        f"{os.urandom(3).hex()}"
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

        "✅ رسید شما ثبت شد.\n\n"

        "⏳ درخواست شما برای مالک ارسال شد.\n"

        "پس از تأیید، مبلغ به موجودی شما اضافه می‌شود."

    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    method_name = (
        "🟣 اولترا"
        if method == "ultra"
        else "🏦 صرافی"
    )

    caption = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name or ''}\n"

        f"🆔 آیدی: {user.id}\n"

        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method_name}\n\n"

        f"🆔 درخواست:\n"
        f"{request_id}\n\n"

        "⏳ وضعیت: در انتظار بررسی"

    )

    buttons = request_keyboard(
        request_id
    )

    try:

        # اگر عکس باشد
        if receipt_type == "photo":

            await context.bot.send_photo(

                chat_id=data["owner"],

                photo=receipt,

                caption=caption,

                reply_markup=buttons,

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

                reply_markup=buttons,

            )

    except Exception as e:

        print(
            "SEND DEPOSIT TO OWNER ERROR:",
            e
        )

    return True


# =========================================================
# DEPOSIT RECEIPT TEXT
# =========================================================

async def deposit_receipt_text(
    update,
    context,
):

    if context.user_data.get("flow") != "deposit_receipt":
        return False

    text = (
        update.message.text or ""
    ).strip()

    if not text:

        await update.message.reply_text(
            "❌ رسید معتبر ارسال کنید."
        )

        return True

    return await create_deposit_request(
        update,
        context,
        text,
        "text",
    )


# =========================================================
# DEPOSIT RECEIPT PHOTO
# =========================================================

async def deposit_receipt_photo(
    update,
    context,
):

    if context.user_data.get("flow") != "deposit_receipt":
        return False

    photo = update.message.photo

    if not photo:
        return False

    file_id = photo[-1].file_id

    return await create_deposit_request(
        update,
        context,
        file_id,
        "photo",
    )


# =========================================================
# WITHDRAW MENU
# =========================================================

async def withdraw_menu(update, context):

    if not await check_bot_status(update):
        return

    user = update.effective_user

    create_user(user)

    context.user_data.clear()

    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS\n\n"

            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS",

            reply_markup=main_keyboard(user.id),

        )

        return

    context.user_data["flow"] = (
        "withdraw_amount"
    )

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مقدار برداشت را وارد کنید.\n\n"

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
    context,
):

    if context.user_data.get("flow") != "withdraw_amount":
        return False

    user = update.effective_user

    try:

        amount = int(
            update.message.text.strip()
        )

    except:

        await update.message.reply_text(
            "❌ فقط مقدار عددی وارد کنید."
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

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS"

        )

        return True

    context.user_data["withdraw_amount"] = amount

    context.user_data["flow"] = (
        "withdraw_address"
    )

    await update.message.reply_text(

        "📍 حالا آیدی یا آدرس دریافت را ارسال کنید."

    )

    return True


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

async def withdraw_address_handler(
    update,
    context,
):

    if context.user_data.get("flow") != "withdraw_address":
        return False

    user = update.effective_user

    address = (
        update.message.text or ""
    ).strip()

    if not address:

        await update.message.reply_text(
            "❌ آیدی یا آدرس معتبر ارسال کنید."
        )

        return True

    amount = context.user_data.get(
        "withdraw_amount"
    )

    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست برداشت منقضی شده."
        )

        return True

    # اول موجودی کسر می‌شود
    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست یا خطایی رخ داد."
        )

        context.user_data.clear()

        return True

    request_id = (
        f"WD_"
        f"{user.id}_"
        f"{int(time.time())}_"
        f"{os.urandom(3).hex()}"
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

        f"📍 آدرس/آیدی:\n{address}\n\n"

        "⏳ درخواست برای مالک ارسال شد."

    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (

        "💰 برداشت جدید\n\n"

        f"👤 نام: {user.first_name or ''}\n"

        f"🆔 آیدی کاربر: {user.id}\n"

        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📍 آیدی/آدرس دریافت:\n"
        f"{address}\n\n"

        f"🆔 درخواست:\n"
        f"{request_id}\n\n"

        "⏳ وضعیت: در انتظار بررسی"

    )

    try:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=owner_text,

            reply_markup=request_keyboard(
                request_id
            ),

        )

    except Exception as e:

        print(
            "SEND WITHDRAW TO OWNER ERROR:",
            e
        )

    return True


# =========================================================
# APPROVE / REJECT
# =========================================================

async def approve_reject(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    owner = query.from_user

    if not is_owner(owner.id):

        await query.answer(
            "❌ فقط مالک دسترسی دارد.",
            show_alert=True,
        )

        return

    callback = query.data

    # -----------------------------------------------------
    # callback:
    # approve_DEP_xxx
    # reject_DEP_xxx
    # approve_WD_xxx
    # reject_WD_xxx
    # -----------------------------------------------------

    if callback.startswith("approve_"):

        action = "approve"

        request_id = callback[
            len("approve_"):
        ]

    elif callback.startswith("reject_"):

        action = "reject"

        request_id = callback[
            len("reject_"):
        ]

    else:

        return

    # =====================================================
    # DEPOSIT
    # =====================================================

    if request_id.startswith("DEP_"):

        req = data["deposits"].get(
            request_id
        )

        if not req:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return

        if req.get("status") != "pending":

            await query.answer(
                "⚠️ این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

        # -------------------------------------------------
        # APPROVE DEPOSIT
        # -------------------------------------------------

        if action == "approve":

            # ضد دوباره واریز شدن
            if req.get("status") != "pending":
                return

            add_balance(
                uid,
                amount
            )

            req["status"] = "approved"

            req["processed_at"] = (
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
                    "SEND DEPOSIT APPROVED ERROR:",
                    e
                )

            await query.edit_message_text(

                "✅ واریز تأیید شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: {amount:,} DOGS\n\n"

                f"🆔 درخواست:\n{request_id}"

            )

        # -------------------------------------------------
        # REJECT DEPOSIT
        # -------------------------------------------------

        else:

            req["status"] = "rejected"

            req["processed_at"] = (
                datetime.now().isoformat()
            )

            save_data()

            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "❌ واریز شما رد شد.\n\n"

                        f"💰 مبلغ: "
                        f"{amount:,} DOGS\n\n"

                        "در صورت اشتباه، "
                        "با پشتیبانی تماس بگیرید."

                    )

                )

            except Exception as e:

                print(
                    "SEND DEPOSIT REJECT ERROR:",
                    e
                )

            await query.edit_message_text(

                "❌ واریز رد شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: {amount:,} DOGS\n\n"

                f"🆔 درخواست:\n{request_id}"

            )

        return

    # =====================================================
    # WITHDRAW
    # =====================================================

    if request_id.startswith("WD_"):

        req = data["withdraws"].get(
            request_id
        )

        if not req:

            await query.edit_message_text(
                "❌ درخواست برداشت پیدا نشد."
            )

            return

        if req.get("status") != "pending":

            await query.answer(
                "⚠️ این درخواست قبلاً بررسی شده.",
                show_alert=True,
            )

            return

        uid = int(
            req["user_id"]
        )

        amount = int(
            req["amount"]
        )

        # -------------------------------------------------
        # APPROVE WITHDRAW
        # -------------------------------------------------

        if action == "approve":

            req["status"] = "approved"

            req["processed_at"] = (
                datetime.now().isoformat()
            )

            save_data()

            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ برداشت شما تأیید شد.\n\n"

                        f"💰 مبلغ: "
                        f"{amount:,} DOGS\n\n"

                        f"📍 آدرس/آیدی:\n"
                        f"{req['address']}"

                    )

                )

            except Exception as e:

                print(
                    "SEND WITHDRAW APPROVED ERROR:",
                    e
                )

            await query.edit_message_text(

                "✅ برداشت تأیید شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: {amount:,} DOGS\n\n"

                f"📍 آدرس:\n"
                f"{req['address']}\n\n"

                f"🆔 درخواست:\n{request_id}"

            )

        # -------------------------------------------------
        # REJECT WITHDRAW
        # -------------------------------------------------

        else:

            req["status"] = "rejected"

            req["processed_at"] = (
                datetime.now().isoformat()
            )

            # برگشت مبلغ به کاربر
            add_balance(
                uid,
                amount
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

                        f"💳 موجودی جدید:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "SEND WITHDRAW REJECT ERROR:",
                    e
                )

            await query.edit_message_text(

                "❌ برداشت رد شد.\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: {amount:,} DOGS\n\n"

                "💰 مبلغ به کاربر برگشت داده شد.\n\n"

                f"🆔 درخواست:\n{request_id}"

            )

        return


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update, context):

    user = update.effective_user

    if not is_owner(user.id):
        return

    status = (
        "روشن ✅"
        if bot_is_on()
        else "خاموش ❌"
    )

    channel = data["settings"].get(
        "channel",
        "@TAK_BE_T"
    )

    group = data["settings"].get(
        "group",
        "@TAK_B_ET"
    )

    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت ربات: {status}\n\n"

        f"📢 چنل اجباری: {channel}\n"

        f"👥 گپ اجباری: {group}",

        reply_markup=admin_keyboard(),

    )


# =========================================================
# ADMIN CALLBACK
# =========================================================

async def admin_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user.id):

        await query.answer(
            "❌ فقط مالک دسترسی دارد.",
            show_alert=True,
        )

        return

    action = query.data

    # =====================================================
    # TOGGLE
    # =====================================================

    if action == "admin_toggle_bot":

        data["settings"]["bot"] = not bot_is_on()

        save_data()

        status = (
            "روشن ✅"
            if bot_is_on()
            else "خاموش ❌"
        )

        await query.edit_message_text(

            "🤖 وضعیت ربات تغییر کرد.\n\n"

            f"وضعیت فعلی: {status}",

            reply_markup=admin_keyboard(),

        )

        return

    # =====================================================
    # CHANNEL
    # =====================================================

    if action == "admin_channel":

        context.user_data.clear()

        context.user_data["admin_flow"] = "channel"

        await query.message.reply_text(

            "📢 آیدی چنل اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@TAK_BE_T"

        )

        return

    # =====================================================
    # GROUP
    # =====================================================

    if action == "admin_group":

        context.user_data.clear()

        context.user_data["admin_flow"] = "group"

        await query.message.reply_text(

            "👥 آیدی گپ اجباری را ارسال کنید.\n\n"

            "مثال:\n"
            "@TAK_B_ET"

        )

        return

    # =====================================================
    # STATS
    # =====================================================

    if action == "admin_stats":

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

        deposits_pending = sum(

            1

            for x in data["deposits"].values()

            if x.get("status") == "pending"

        )

        withdraws_pending = sum(

            1

            for x in data["withdraws"].values()

            if x.get("status") == "pending"

        )

        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users_count}\n\n"

            f"💰 مجموع موجودی کاربران:\n"
            f"{total_balance:,} DOGS\n\n"

            f"💳 کل واریزی‌ها: "
            f"{len(data['deposits'])}\n"

            f"⏳ واریزی در انتظار: "
            f"{deposits_pending}\n\n"

            f"💰 کل برداشت‌ها: "
            f"{len(data['withdraws'])}\n"

            f"⏳ برداشت در انتظار: "
            f"{withdraws_pending}",

            reply_markup=admin_keyboard(),

        )

        return

    # =====================================================
    # TRANSFER OWNER
    # =====================================================

    if action == "admin_transfer":

        context.user_data.clear()

        context.user_data["admin_flow"] = (
            "transfer_owner"
        )

        await query.message.reply_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789"

        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(
    update,
    context,
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

    # =====================================================
    # CHANNEL
    # =====================================================

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

            "✅ چنل اجباری ذخیره شد.\n\n"

            f"📢 {text}",

            reply_markup=main_keyboard(
                user.id
            ),

        )

        return True

    # =====================================================
    # GROUP
    # =====================================================

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

            "✅ گپ اجباری ذخیره شد.\n\n"

            f"👥 {text}",

            reply_markup=main_keyboard(
                user.id
            ),

        )

        return True

    # =====================================================
    # OWNER
    # =====================================================

    if state == "transfer_owner":

        try:

            new_owner = int(text)

        except:

            await update.message.reply_text(
                "❌ فقط آیدی عددی ارسال کنید."
            )

            return True

        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی معتبر نیست."
            )

            return True

        old_owner = data["owner"]

        data["owner"] = new_owner

        save_data()

        context.user_data.clear()

        await update.message.reply_text(

            "✅ انتقال مالکیت انجام شد.\n\n"

            f"👑 مالک قبلی:\n{old_owner}\n\n"

            f"👑 مالک جدید:\n{new_owner}"

        )

        return True

    return False


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context,
):

    if not update.message:
        return

    user = update.effective_user

    text = (
        update.message.text or ""
    ).strip()

    # =====================================================
    # ADMIN INPUT
    # =====================================================

    if await admin_text(
        update,
        context
    ):

        return

    # =====================================================
    # SUPPORT
    # =====================================================

    if context.user_data.get("flow") == "support":

        if await support_message(
            update,
            context
        ):

            return

    # =====================================================
    # DEPOSIT RECEIPT
    # =====================================================

    if context.user_data.get(
        "flow"
    ) == "deposit_receipt":

        if await deposit_receipt_text(
            update,
            context
        ):

            return

    # =====================================================
    # DEPOSIT AMOUNT
    # =====================================================

    if context.user_data.get(
        "flow"
    ) == "deposit_amount":

        if await deposit_amount_handler(
            update,
            context
        ):

            return

    # =====================================================
    # WITHDRAW AMOUNT
    # =====================================================

    if context.user_data.get(
        "flow"
    ) == "withdraw_amount":

        if await withdraw_amount_handler(
            update,
            context
        ):

            return

    # =====================================================
    # WITHDRAW ADDRESS
    # =====================================================

    if context.user_data.get(
        "flow"
    ) == "withdraw_address":

        if await withdraw_address_handler(
            update,
            context
        ):

            return

    # =====================================================
    # MAIN BUTTONS
    # =====================================================

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
    context,
):

    if not update.message:
        return

    # فقط زمانی عکس را رسید حساب کن
    if context.user_data.get(
        "flow"
    ) == "deposit_receipt":

        await deposit_receipt_photo(
            update,
            context
        )

        return

    # اگر پشتیبانی روی عکس بود
    if context.user_data.get(
        "flow"
    ) == "support":

        user = update.effective_user

        username = (
            f"@{user.username}"
            if user.username
            else "ندارد"
        )

        photo_id = (
            update.message.photo[-1].file_id
        )

        try:

            await context.bot.send_photo(

                chat_id=data["owner"],

                photo=photo_id,

                caption=(

                    "🎧 پیام تصویری پشتیبانی\n\n"

                    f"👤 نام: {user.first_name}\n"

                    f"🆔 آیدی: {user.id}\n"

                    f"🔹 یوزرنیم: {username}"

                )

            )

        except Exception as e:

            print(
                "SUPPORT PHOTO ERROR:",
                e
            )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد."
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context,
):

    print("\n========== BOT ERROR ==========")

    try:
        print(
            "UPDATE:",
            update
        )
    except:
        pass

    try:
        print(
            "ERROR:",
            context.error
        )

        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )

    except:
        pass

    print(
        "===============================\n"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN environment variable is missing."
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
    # APPROVE / REJECT
    # مهم: قبل از callbackهای عمومی قرار گرفته
    # -----------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern=r"^(approve|reject)_(DEP|WD)_"
        )
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
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
    # TEXT
    # -----------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
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
        "BOT STARTED SUCCESSFULLY"
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
