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

ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "data.json"



# =========================
# DEFAULT DATA
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
# LOAD / SAVE
# =========================

def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)


    except Exception:

        pass


    return DEFAULT_DATA.copy()



data = load_data()



def save_data():

    try:

        temp = DATA_FILE + ".tmp"

        with open(
            temp,
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
            temp,
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

        return


    user["balance"] = (
        balance(uid)
        +
        int(amount)
    )

    save_data()



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
# KEYBOARDS
# =========================

def main_keyboard(uid):

    keys = [

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

        keys.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )


    return ReplyKeyboardMarkup(
        keys,
        resize_keyboard=True
    )



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
                callback_data="set_channel"
            ),

            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="set_group"
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
# START
# =========================

async def start(update, context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )

    )

# =========================
# DEPOSIT MENU
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



# =========================
# DEPOSIT METHOD
# =========================

async def deposit_method(update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "deposit_ultra":

        context.user_data["method"] = "ultra"


    elif query.data == "deposit_exchange":

        context.user_data["method"] = "exchange"


    else:

        return



    context.user_data["state"] = "deposit_amount"


    await query.message.reply_text(

        "💰 مقدار DOGS را وارد کنید\n\n"

        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS"

    )



# =========================
# DEPOSIT AMOUNT
# =========================

async def deposit_amount(update, context):

    if context.user_data.get("state") != "deposit_amount":

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

            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."

        )

        return True



    context.user_data["amount"] = amount

    context.user_data["state"] = "deposit_receipt"



    method = context.user_data.get(
        "method"
    )


    if method == "ultra":


        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"

            f"{ULTRA_ADDRESS}\n\n"

            "فرصت مثال:\n\n"

            f"ULTRA {amount} DOGS\n"

            f"{ULTRA_ADDRESS}\n\n"

            "پس از ارسال، رسید را در همین چت ارسال کنید.\n\n"

            "📸 شات یا پیام تراکنش را بفرستید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"

        )


    else:


        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را از طریق صرافی به این ولت بزنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            f"مبلغ: {amount:,} DOGS\n\n"

            "پس از ارسال، شات یا لینک هش تراکنش را در همین چت ارسال کنید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"

        )


    return True



# =========================
# DEPOSIT RECEIPT
# =========================

async def deposit_receipt(update, context):

    if context.user_data.get("state") != "deposit_receipt":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "amount"
    )


    method = context.user_data.get(
        "method"
    )


    if not amount:

        context.user_data.clear()

        return True



    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    else:

        receipt = update.message.text

        rtype = "text"



    request_id = (
        f"DEP_{user.id}_{int(time.time())}"
    )



    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "amount": amount,

        "method": method,

        "receipt": receipt,

        "type": rtype,

        "status": "pending"

    }


    save_data()


    context.user_data.clear()



    await update.message.reply_text(

        "✅ رسید ارسال شد.\n\n"

        "⏳ منتظر تأیید مالک باشید."

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



    text = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method}\n\n"

        f"🆔 درخواست:\n{request_id}"

    )


    if rtype == "photo":

        await context.bot.send_photo(

            chat_id=data["owner"],

            photo=receipt,

            caption=text,

            reply_markup=buttons

        )


    else:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=text + "\n\n📎 رسید:\n" + receipt,

            reply_markup=buttons

        )


    return True



# =========================
# WITHDRAW MENU
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return



    context.user_data.clear()

    context.user_data["state"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 مقدار برداشت را وارد کنید\n\n"

        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

    )

# =========================
# WITHDRAW AMOUNT
# =========================

async def withdraw_amount(update, context):

    if context.user_data.get("state") != "withdraw_amount":
        return False

    user = update.effective_user

    try:
        amount = int(update.message.text.strip())

    except:
        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )
        return True


    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return True


    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return True


    context.user_data["withdraw_amount"] = amount
    context.user_data["state"] = "withdraw_address"


    await update.message.reply_text(
        "📍 آیدی یا آدرس دریافت DOGS را ارسال کنید."
    )

    return True



# =========================
# WITHDRAW ADDRESS
# =========================

async def withdraw_address(update, context):

    if context.user_data.get("state") != "withdraw_address":
        return False


    user = update.effective_user

    amount = context.user_data.get(
        "withdraw_amount"
    )

    address = update.message.text.strip()


    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در موجودی."
        )
        return True


    request_id = (
        f"WD_{user.id}_{int(time.time())}"
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
        "✅ درخواست برداشت ارسال شد.\n\n"
        "⏳ منتظر تایید مالک باشید."
    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_wd_{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_wd_{request_id}"
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

            f"📍 آدرس:\n{address}"

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


    action, kind, request_id = query.data.split("_",2)


    if kind == "dep":

        req = data["deposits"].get(request_id)


        if not req:
            return


        if req["status"] != "pending":

            await query.answer(
                "قبلا بررسی شده",
                show_alert=True
            )
            return



        uid = req["user_id"]


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

                    f"+{req['amount']:,} DOGS"

                )

            )


            await query.edit_message_text(
                "✅ واریز تایید شد"
            )


        else:

            req["status"] = "rejected"


            await context.bot.send_message(
                chat_id=uid,
                text="❌ واریز رد شد."
            )


            await query.edit_message_text(
                "❌ واریز رد شد"
            )




    elif kind == "wd":

        req = data["withdraws"].get(request_id)


        if not req:
            return


        if req["status"] != "pending":

            await query.answer(
                "قبلا بررسی شده",
                show_alert=True
            )
            return



        uid = req["user_id"]


        if action == "approve":

            req["status"] = "approved"


            await context.bot.send_message(
                chat_id=uid,
                text="✅ برداشت تایید شد."
            )


            await query.edit_message_text(
                "✅ برداشت تایید شد"
            )


        else:

            req["status"] = "rejected"


            add_balance(
                uid,
                req["amount"]
            )


            await context.bot.send_message(
                chat_id=uid,
                text="❌ برداشت رد شد.\n💰 مبلغ برگشت داده شد."
            )


            await query.edit_message_text(
                "❌ برداشت رد شد\n💰 مبلغ برگشت داده شد."
            )


    save_data()



# =========================
# PROFILE
# =========================

async def profile(update, context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 {user.id}\n"

        f"💰 موجودی: {balance(user.id):,} DOGS"

    )



# =========================
# TEXT ROUTER
# =========================

async def text_router(update, context):

    text = update.message.text


    if text == "💳 واریزی":
        await deposit_menu(update, context)
        return


    if text == "💰 برداشت":
        await withdraw_menu(update, context)
        return


    if text == "👤 پروفایل":
        await profile(update, context)
        return


    if await deposit_amount(update, context):
        return


    if await deposit_receipt(update, context):
        return


    if await withdraw_amount(update, context):
        return


    if await withdraw_address(update, context):
        return



async def photo_router(update, context):

    await deposit_receipt(update, context)



# =========================
# MAIN
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
            pattern=r"^(approve|reject)_(dep|wd)_"
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


    app.add_error_handler(
        lambda update, context:
        traceback.print_exc()
    )


    print("BOT STARTED")

    app.run_polling()



if __name__ == "__main__":
    main()
