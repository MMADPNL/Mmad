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


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

ULTRA_ADDRESS = "@CyyFr"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "data.json"



# =========================
# DEFAULT
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "settings": {

        "bot": True,

        "channel": "@TAK_BE_T",

        "group": "@TAK_B_ET"

    }

}



# =========================
# SAFE SAVE / LOAD
# =========================

def load_data():

    try:

        if not os.path.exists(DATA_FILE):

            return DEFAULT_DATA.copy()


        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)


    except Exception:

        return DEFAULT_DATA.copy()



data = load_data()



def save_data():

    try:

        tmp = DATA_FILE + ".tmp"


        with open(
            tmp,
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
            tmp,
            DATA_FILE
        )


    except Exception as e:

        print(
            "SAVE ERROR:",
            e
        )



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
        balance(uid)
        +
        int(amount)
    )


    save_data()

    return True



def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return False


    if balance(uid) < amount:

        return False


    user["balance"] -= int(amount)

    save_data()

    return True



def is_owner(uid):

    return int(uid) == int(
        data.get(
            "owner",
            OWNER_ID
        )
    )



# =========================
# ANTI ERROR
# =========================

async def error_handler(update, context):

    print("BOT ERROR:")
    traceback.print_exc()



# =========================
# KEYBOARDS
# =========================

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
        ]

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



def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🤖 روشن/خاموش",
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
                callback_data="transfer_owner"
            )
        ]

    ])

# =========================
# DEPOSIT SYSTEM
# =========================

async def deposit_menu(update, context):

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
                )
            ]
        ])
    )


async def deposit_method(update, context):

    query = update.callback_query
    await query.answer()

    if query.data == "deposit_ultra":
        context.user_data["deposit_method"] = "ultra"

    elif query.data == "deposit_exchange":
        context.user_data["deposit_method"] = "exchange"

    else:
        return

    context.user_data["flow"] = "deposit_amount"

    await query.message.reply_text(
        "💰 مبلغ واریز را ارسال کنید\n\n"
        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS"
    )



async def deposit_amount_handler(update, context):

    if context.user_data.get("flow") != "deposit_amount":
        return False


    try:
        amount = int(update.message.text)

    except:
        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )
        return True


    if amount < MIN_DEPOSIT:

        await update.message.reply_text(
            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."
        )
        return True


    context.user_data["deposit_amount"] = amount
    context.user_data["flow"] = "deposit_receipt"


    method = context.user_data.get(
        "deposit_method"
    )


    if method == "ultra":

        text = (
            f"ULTRA {amount} DOGS\n"
            f"{SUPPORT_USERNAME}"
        )


        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📋 متن واریز:\n"
            f"{text}\n\n"

            "بعد از پرداخت رسید را ارسال کنید.",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📋 کپی متن واریز",
                        copy_text=text
                    )
                ]
            ])
        )


    else:


        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            "📍 ولت:\n"
            f"{EXCHANGE_WALLET}\n\n"

            f"💰 مبلغ:\n{amount:,} DOGS\n\n"

            "بعد از پرداخت رسید را ارسال کنید.",

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

# =========================
# DEPOSIT RECEIPT
# =========================

async def deposit_receipt_handler(update, context):

    if context.user_data.get("flow") != "deposit_receipt":
        return False


    user = update.effective_user

    amount = context.user_data.get(
        "deposit_amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )


    if not amount or not method:

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده."
        )

        context.user_data.clear()
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
            "❌ فقط عکس یا متن رسید ارسال کنید."
        )

        return True



    request_id = (
        f"DEP_{user.id}_{int(datetime.now().timestamp())}"
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

        "status": "pending"

    }


    save_data()


    context.user_data.clear()



    await update.message.reply_text(

        "✅ رسید ثبت شد.\n\n"
        "⏳ منتظر تایید مالک باشید."

    )



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

        f"🆔 کد درخواست:\n{request_id}"

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
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

                text=caption
                +
                "\n\n📎 رسید:\n"
                +
                receipt,

                reply_markup=buttons

            )


    except Exception as e:

        print(
            "SEND OWNER ERROR:",
            e
        )


    return True

# =========================
# WITHDRAW SYSTEM
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: {balance(user.id):,} DOGS\n"

            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data["flow"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید:\n\n"

        "مثال:\n"
        "10000"

    )



async def withdraw_amount_handler(update, context):

    if context.user_data.get("flow") != "withdraw_amount":

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

    context.user_data["flow"] = "withdraw_address"



    await update.message.reply_text(

        "📍 آدرس دریافت را ارسال کنید."

    )


    return True





async def withdraw_address_handler(update, context):

    if context.user_data.get("flow") != "withdraw_address":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "withdraw_amount"
    )


    address = update.message.text.strip()



    if not amount:

        context.user_data.clear()

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

        f"WD_{user.id}_"
        f"{int(datetime.now().timestamp())}"

    )



    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "amount": amount,

        "address": address,

        "status": "pending"

    }


    save_data()


    context.user_data.clear()



    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"📍 آدرس:\n{address}\n\n"

        "⏳ منتظر تایید مالک باشید."

    )



    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=
                f"approve_wd_{request_id}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=
                f"reject_wd_{request_id}"

            )

        ]

    ])



    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "💰 برداشت جدید\n\n"

            f"👤 کاربر: {user.first_name}\n"

            f"🆔 آیدی: {user.id}\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"📍 آدرس:\n{address}\n\n"

            f"🆔 درخواست:\n{request_id}"

        ),

        reply_markup=buttons

    )


    return True

# =========================
# APPROVE / REJECT
# =========================

async def approve_reject(update, context):

    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return


    parts = query.data.split("_")

    action = parts[0]
    kind = parts[1]

    request_id = "_".join(parts[2:])


    # =====================
    # DEPOSIT
    # =====================

    if kind == "dep":

        req = data["deposits"].get(request_id)

        if not req:
            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )
            return


        uid = req["user_id"]


        if req["status"] != "pending":

            await query.edit_message_text(
                "⚠️ قبلا بررسی شده."
            )
            return



        if action == "approve":

            add_balance(
                uid,
                req["amount"]
            )

            req["status"] = "approved"


            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز تایید شد\n\n"

                    f"💰 +{req['amount']:,} DOGS\n"

                    f"💳 موجودی:\n"
                    f"{balance(uid):,} DOGS"

                )

            )


            await query.edit_message_text(

                "✅ واریز تایید شد\n\n"

                f"💰 مبلغ: {req['amount']:,} DOGS"

            )



        else:

            req["status"] = "rejected"


            await context.bot.send_message(

                chat_id=uid,

                text="❌ واریز شما رد شد."

            )


            await query.edit_message_text(
                "❌ واریز رد شد."
            )



    # =====================
    # WITHDRAW
    # =====================

    elif kind == "wd":


        req = data["withdraws"].get(request_id)


        if not req:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return



        uid = req["user_id"]



        if req["status"] != "pending":

            await query.edit_message_text(
                "⚠️ قبلا بررسی شده."
            )

            return



        if action == "approve":


            req["status"] = "approved"



            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ برداشت تایید شد\n\n"

                    f"💰 مبلغ: "
                    f"{req['amount']:,} DOGS"

                )

            )


            await query.edit_message_text(

                "✅ برداشت تایید شد."

            )



        else:


            req["status"] = "rejected"


            add_balance(
                uid,
                req["amount"]
            )



            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "❌ برداشت رد شد\n\n"

                    "💰 مبلغ برگشت داده شد."

                )

            )


            await query.edit_message_text(

                "❌ برداشت رد شد\n\n"
                "💰 مبلغ برگشت داده شد."

            )


    save_data()



# =========================
# SUPPORT
# =========================

async def support(update, context):

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


    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "🎧 پیام پشتیبانی جدید\n\n"

            f"👤 {user.first_name}\n"

            f"🆔 {user.id}\n\n"

            f"{update.message.text}"

        )

    )


    context.user_data.clear()


    await update.message.reply_text(
        "✅ پیام شما ارسال شد."
    )

    return True



# =========================
# HANDLERS
# =========================

def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            deposit_method,
            pattern="^deposit_"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern="^(approve|reject)_(dep|wd)_"
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )


    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )


    print("BOT STARTED")

    app.run_polling()



if __name__ == "__main__":

    main()
