import os
import json
import time
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT = "@CyyFr"

ULTRA_ID = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "data.json"


# =========================
# DATA
# =========================

DEFAULT = {
    "owner": OWNER_ID,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "settings": {
        "bot": True,
        "channel": "",
        "group": ""
    }
}


def load():

    if not os.path.exists(DATA_FILE):
        return DEFAULT

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return DEFAULT



data = load()



def save():

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )



# =========================
# USER
# =========================

def create_user(user):

    uid = str(user.id)

    if uid not in data["users"]:

        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name,
            "username": user.username or "",
            "balance": 0,
            "ref": 0,
            "date": str(datetime.now())
        }

        save()



def get_user(uid):

    return data["users"].get(str(uid))



def get_balance(uid):

    u = get_user(uid)

    if not u:
        return 0

    return int(u["balance"])



def add_balance(uid, amount):

    u = get_user(uid)

    if u:

        u["balance"] += int(amount)

        save()



def remove_balance(uid, amount):

    u = get_user(uid)

    if not u:
        return False

    if u["balance"] < amount:
        return False

    u["balance"] -= int(amount)

    save()

    return True



def owner(uid):

    return int(uid) == int(data["owner"])



# =========================
# KEYBOARD
# =========================

def menu(uid):

    k = [

        ["💳 واریزی", "💰 برداشت"],

        ["👤 پروفایل", "👥 زیرمجموعه"],

        ["🎧 پشتیبانی"]

    ]

    if owner(uid):

        k.append(
            ["⚙️ پنل مدیریت"]
        )


    return ReplyKeyboardMarkup(
        k,
        resize_keyboard=True
    )



# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=menu(user.id)

            )

    # =========================
# ADMIN PANEL
# =========================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🤖 روشن/خاموش ربات",
                callback_data="toggle_bot"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 چنل اجباری",
                callback_data="channel"
            ),

            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="group"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="stats"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="owner"
            )
        ]

    ])



async def admin_panel(update, context):

    uid = update.effective_user.id

    if not owner(uid):
        return


    status = (
        "روشن ✅"
        if data["settings"]["bot"]
        else "خاموش ❌"
    )


    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت: {status}\n"

        f"📢 چنل: "
        f"{data['settings']['channel'] or 'ندارد'}\n"

        f"👥 گپ: "
        f"{data['settings']['group'] or 'ندارد'}",

        reply_markup=admin_keyboard()

    )



async def admin_callback(update, context):

    query = update.callback_query

    await query.answer()


    uid = query.from_user.id


    if not owner(uid):
        return



    if query.data == "toggle_bot":

        data["settings"]["bot"] = not data["settings"]["bot"]

        save()


        await query.edit_message_text(

            "🤖 وضعیت ربات تغییر کرد\n\n"

            +
            (
                "روشن ✅"
                if data["settings"]["bot"]
                else "خاموش ❌"
            ),

            reply_markup=admin_keyboard()

        )



    elif query.data == "stats":

        users = len(data["users"])

        total = sum(
            x["balance"]
            for x in data["users"].values()
        )


        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n"

            f"💰 کل موجودی:\n"
            f"{total:,} DOGS\n\n"

            f"💳 واریزی‌ها: "
            f"{len(data['deposits'])}\n"

            f"💰 برداشت‌ها: "
            f"{len(data['withdraws'])}",

            reply_markup=admin_keyboard()

        )



    elif query.data == "channel":

        context.user_data["admin_state"] = "channel"

        await query.message.reply_text(
            "📢 آیدی چنل را بفرست:"
        )



    elif query.data == "group":

        context.user_data["admin_state"] = "group"

        await query.message.reply_text(
            "👥 آیدی گپ را بفرست:"
        )



    elif query.data == "owner":

        context.user_data["admin_state"] = "owner"

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را بفرست:"
)

# =========================
# DEPOSIT MENU
# =========================

async def deposit_menu(update, context):

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"
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
                )
            ]

        ])

    )


# =========================
# DEPOSIT METHOD
# =========================

async def deposit_method(update, context):

    query = update.callback_query

    await query.answer()

    if query.data == "deposit_ultra":

        context.user_data["deposit_method"] = "اولترا"

    elif query.data == "deposit_exchange":

        context.user_data["deposit_method"] = "صرافی"

    else:
        return


    context.user_data["state"] = "deposit_amount"


    await query.message.reply_text(

        "💰 مبلغ واریز را وارد کنید.\n\n"

        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000"

    )


# =========================
# DEPOSIT AMOUNT
# =========================

async def deposit_amount(update, context):

    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

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


    method = context.user_data.get(
        "deposit_method"
    )

    if not method:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده."
        )

        return


    context.user_data["deposit_amount"] = amount

    context.user_data["state"] = "deposit_receipt"


    # =====================
    # ULTRA
    # =====================

    if method == "اولترا":

        ultra_text = (
            f"ULTRA {amount} DOGS"
        )


        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📋 متن واریز:\n"
            f"{ultra_text}\n\n"

            f"👤 آیدی:\n"
            f"{ULTRA_ADDRESS}\n\n"

            "بعد از پرداخت، رسید را ارسال کنید.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "📋 کپی متن واریز",
                        copy_text=ultra_text
                    )
                ],

                [
                    InlineKeyboardButton(
                        "👤 کپی آیدی",
                        copy_text=ULTRA_ADDRESS
                    )
                ]

            ])

        )


    # =====================
    # EXCHANGE
    # =====================

    elif method == "صرافی":

        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📍 ولت صرافی:\n"
            f"{EXCHANGE_WALLET}\n\n"

            "بعد از واریز، رسید را ارسال کنید.",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "📋 کپی ولت",
                        copy_text=EXCHANGE_WALLET
                    )
                ]

            ])

        )

# =========================
# DEPOSIT RECEIPT
# =========================

async def deposit_receipt(update, context):

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
            "❌ درخواست واریز منقضی شده."
        )

        return


    receipt = None
    receipt_type = None


    # =====================
    # PHOTO RECEIPT
    # =====================

    if update.message.photo:

        receipt_type = "photo"

        receipt = (
            update.message.photo[-1].file_id
        )


    # =====================
    # TEXT RECEIPT
    # =====================

    elif update.message.text:

        receipt_type = "text"

        receipt = update.message.text.strip()


    else:

        await update.message.reply_text(
            "❌ لطفاً عکس رسید یا لینک تراکنش را ارسال کنید."
        )

        return


    # =====================
    # REQUEST ID
    # =====================

    request_id = (
        f"dep_{user.id}_{len(data['deposits']) + 1}"
    )


    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "method": method,

        "receipt_type": receipt_type,

        "receipt": receipt,

        "status": "pending"

    }


    save()


    # پاک کردن وضعیت کاربر

    context.user_data.clear()


    # =====================
    # USER MESSAGE
    # =====================

    await update.message.reply_text(

        "✅ رسید شما ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"
        f"💳 روش: {method}\n\n"

        "⏳ منتظر تأیید مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )


    # =====================
    # OWNER MESSAGE
    # =====================

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )


    caption = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n"

        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method}\n\n"

        f"🆔 درخواست:\n"
        f"{request_id}"

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve_dep_{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_dep_{request_id}"
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
                    "\n\n🔗 رسید:\n"
                    +
                    receipt
                ),

                reply_markup=buttons

            )

    except Exception as e:

        print(
            "OWNER SEND ERROR:",
            e
        )

# =========================
# WITHDRAW MENU
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS\n\n"

            f"📌 حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS"

        )

        return


    context.user_data["state"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید.\n\n"

        f"📌 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "مثال:\n"
        "10000"

    )


# =========================
# WITHDRAW AMOUNT
# =========================

async def withdraw_amount(update, context):

    user = update.effective_user


    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

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

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS"

        )

        return


    context.user_data["withdraw_amount"] = amount

    context.user_data["state"] = "withdraw_address"


    await update.message.reply_text(

        "📍 آدرس یا آیدی دریافت DOGS را ارسال کنید.\n\n"

        "مثال:\n"
        "UQxxxxxxxxxxxxxxxx"

    )


# =========================
# WITHDRAW ADDRESS
# =========================

async def withdraw_address(update, context):

    user = update.effective_user

    address = update.message.text.strip()

    amount = context.user_data.get(
        "withdraw_amount"
    )


    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ درخواست برداشت منقضی شده."
        )

        return


    if not address:

        await update.message.reply_text(
            "❌ آدرس نمی‌تواند خالی باشد."
        )

        return


    # =====================
    # کسر موجودی
    # =====================

    if not remove_balance(
        user.id,
        amount
    ):

        context.user_data.clear()

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return


    # =====================
    # REQUEST ID
    # =====================

    request_id = (
        f"wd_{user.id}_{len(data['withdraws']) + 1}"
    )


    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "address": address,

        "status": "pending"

    }


    save()


    context.user_data.clear()


    # =====================
    # USER
    # =====================

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📍 آدرس:\n"
        f"{address}\n\n"

        "⏳ منتظر تأیید مالک باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )


    # =====================
    # OWNER
    # =====================

    username = (

        f"@{user.username}"
        if user.username
        else "ندارد"

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"approve_wd_{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_wd_{request_id}"
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

                f"🔹 یوزرنیم: {username}\n\n"

                f"💰 مبلغ: {amount:,} DOGS\n\n"

                f"📍 آدرس دریافت:\n"
                f"{address}\n\n"

                f"🆔 درخواست:\n"
                f"{request_id}"

            ),

            reply_markup=buttons

        )

    except Exception as e:

        print(
            "OWNER WITHDRAW ERROR:",
            e
        )

# =========================
# APPROVE / REJECT
# =========================

async def approve_reject(update, context):

    query = update.callback_query

    await query.answer()


    if not owner(query.from_user.id):
        return


    parts = query.data.split("_")

    action = parts[0]
    kind = parts[1]

    request_id = "_".join(parts[2:])


    # =========================
    # DEPOSIT
    # =========================

    if kind == "dep":

        req = data["deposits"].get(request_id)

        if not req:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return


        if req["status"] != "pending":

            await query.edit_message_text(

                "⚠️ این درخواست قبلاً بررسی شده.\n\n"

                f"وضعیت: {req['status']}"

            )

            return


        uid = req["user_id"]


        # =====================
        # APPROVE DEPOSIT
        # =====================

        if action == "approve":

            add_balance(
                uid,
                req["amount"]
            )

            req["status"] = "approved"

            save()


            await query.edit_message_text(

                "✅ واریز تأیید شد.\n\n"

                f"👤 آیدی کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS"

            )


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ واریز شما تأیید شد.\n\n"

                        f"💰 مبلغ: "
                        f"+{req['amount']:,} DOGS\n\n"

                        f"💳 موجودی جدید:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "USER DEPOSIT MESSAGE ERROR:",
                    e
                )


        # =====================
        # REJECT DEPOSIT
        # =====================

        elif action == "reject":

            req["status"] = "rejected"

            save()


            await query.edit_message_text(

                "❌ واریز رد شد.\n\n"

                f"👤 آیدی کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS"

            )


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
                    "USER DEPOSIT REJECT MESSAGE ERROR:",
                    e
                )


    # =========================
    # WITHDRAW
    # =========================

    elif kind == "wd":

        req = data["withdraws"].get(request_id)

        if not req:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return


        if req["status"] != "pending":

            await query.edit_message_text(

                "⚠️ این درخواست قبلاً بررسی شده.\n\n"

                f"وضعیت: {req['status']}"

            )

            return


        uid = req["user_id"]


        # =====================
        # APPROVE WITHDRAW
        # =====================

        if action == "approve":

            req["status"] = "approved"

            save()


            await query.edit_message_text(

                "✅ برداشت تأیید شد.\n\n"

                f"👤 آیدی کاربر: {uid}\n"

                f"💰 مبلغ:\n"
                f"{req['amount']:,} DOGS\n\n"

                f"📍 آدرس:\n"
                f"{req['address']}"

            )


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ برداشت شما تأیید شد.\n\n"

                        f"💰 مبلغ: "
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


        # =====================
        # REJECT WITHDRAW
        # =====================

        elif action == "reject":

            req["status"] = "rejected"


            # برگرداندن مبلغ به کاربر

            add_balance(
                uid,
                req["amount"]
            )


            save()


            await query.edit_message_text(

                "❌ برداشت رد شد.\n\n"

                f"👤 آیدی کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS\n\n"

                "💵 مبلغ به موجودی کاربر برگشت داده شد."

            )


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "❌ درخواست برداشت شما رد شد.\n\n"

                        f"💰 مبلغ: "
                        f"{req['amount']:,} DOGS\n\n"

                        "💵 مبلغ به موجودی شما برگشت داده شد.\n\n"

                        f"💳 موجودی جدید:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except Exception as e:

                print(
                    "USER WITHDRAW REJECT MESSAGE ERROR:",
                    e
            )

# =========================
# PROFILE
# =========================

async def profile(update, context):

    user = update.effective_user

    create_user(user)

    u = get_user(user.id)

    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: {u['name']}\n"

        f"💰 موجودی: "
        f"{balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{u.get('referrals', 0)}",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================
# REFERRAL
# =========================

async def referrals(update, context):

    user = update.effective_user

    create_user(user)

    bot_username = context.bot.username

    link = (
        f"https://t.me/{bot_username}"
        f"?start=ref_{user.id}"
    )

    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک دعوت شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه:\n"
        f"{data['users'][str(user.id)].get('referrals', 0)}",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================
# SUPPORT
# =========================

async def support(update, context):

    context.user_data["support"] = True

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیامت رو ارسال کن ✍️"

    )


async def support_message(update, context):

    if not context.user_data.get("support"):
        return False

    user = update.effective_user

    text = update.message.text.strip()

    if not text:

        await update.message.reply_text(
            "❌ پیام خالی است."
        )

        return True


    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )


    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "📩 پیام جدید پشتیبانی\n\n"

            f"👤 نام: {user.first_name}\n"

            f"🆔 آیدی: {user.id}\n"

            f"🔹 یوزرنیم: {username}\n\n"

            f"💬 پیام:\n{text}"

        )

    )


    context.user_data.clear()


    await update.message.reply_text(

        "✅ پیامت ارسال شد.\n\n"

        "⏳ منتظر پاسخ پشتیبانی باشید.",

        reply_markup=main_keyboard(
            user.id
        )

    )

    return True


# =========================
# ADMIN TEXT INPUT
# =========================

async def admin_text(update, context):

    uid = update.effective_user.id

    if not owner(uid):
        return False


    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False


    text = update.message.text.strip()


    # =====================
    # CHANNEL
    # =====================

    if state == "channel":

        data["settings"]["channel"] = text

        save()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ چنل اجباری ذخیره شد."
        )

        return True


    # =====================
    # GROUP
    # =====================

    if state == "group":

        data["settings"]["group"] = text

        save()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد."
        )

        return True


    # =====================
    # TRANSFER OWNER
    # =====================

    if state == "owner":

        try:

            new_owner = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ آیدی عددی صحیح وارد کنید."
            )

            return True


        data["owner"] = new_owner

        save()

        context.user_data.clear()


        await update.message.reply_text(

            "✅ مالکیت با موفقیت منتقل شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}"

        )

        return True


    return False


# =========================
# TEXT ROUTER
# =========================

async def text_router(update, context):

    if not update.message:
        return


    text = update.message.text.strip()


    # =====================
    # SUPPORT
    # =====================

    if await support_message(
        update,
        context
    ):
        return


    # =====================
    # ADMIN INPUT
    # =====================

    if await admin_text(
        update,
        context
    ):
        return


    # =====================
    # ADMIN PANEL
    # =====================

    if text == "⚙️ پنل مدیریت":

        await admin_panel(
            update,
            context
        )

        return


    # =====================
    # DEPOSIT
    # =====================

    if text == "💳 واریزی":

        await deposit_menu(
            update,
            context
        )

        return


    # =====================
    # WITHDRAW
    # =====================

    if text == "💰 برداشت":

        await withdraw_menu(
            update,
            context
        )

        return


    # =====================
    # PROFILE
    # =====================

    if text == "👤 پروفایل":

        await profile(
            update,
            context
        )

        return


    # =====================
    # REFERRAL
    # =====================

    if text == "👥 زیر مجموعه":

        await referrals(
            update,
            context
        )

        return


    # =====================
    # SUPPORT BUTTON
    # =====================

    if text == "🎧 پشتیبانی":

        await support(
            update,
            context
        )

        return


    # =====================
    # STATES
    # =====================

    state = context.user_data.get(
        "state"
    )


    if state == "deposit_amount":

        await deposit_amount(
            update,
            context
        )

        return


    if state == "deposit_receipt":

        await deposit_receipt(
            update,
            context
        )

        return


    if state == "withdraw_amount":

        await withdraw_amount(
            update,
            context
        )

        return


    if state == "withdraw_address":

        await withdraw_address(
            update,
            context
        )

        return

# =========================
# PHOTO ROUTER
# =========================

async def photo_router(update, context):

    state = context.user_data.get("state")

    if state == "deposit_receipt":

        await deposit_receipt(
            update,
            context
        )

        return


# =========================
# START COMMAND
# =========================

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


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN تنظیم نشده است."
        )

        return


    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )


    # =====================
    # START
    # =====================

    app.add_handler(

        CommandHandler(
            "start",
            start
        )

    )


    # =====================
    # DEPOSIT BUTTONS
    # =====================

    app.add_handler(

        CallbackQueryHandler(

            deposit_method,

            pattern=
            r"^deposit_(ultra|exchange)$"

        )

    )


    # =====================
    # ADMIN PANEL
    # =====================

    app.add_handler(

        CallbackQueryHandler(

            admin_callback,

            pattern=
            r"^(toggle_bot|channel|group|stats|owner)$"

        )

    )


    # =====================
    # APPROVE / REJECT
    # =====================

    app.add_handler(

        CallbackQueryHandler(

            approve_reject,

            pattern=
            r"^(approve|reject)_(dep|wd)_"

        )

    )


    # =====================
    # PHOTO
    # =====================

    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_router

        )

    )


    # =====================
    # TEXT
    # =====================

    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_router

        )

    )


    print(
        "BOT STARTED"
    )


    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":

    main()
