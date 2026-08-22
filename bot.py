import os
import json
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

SUPPORT_USERNAME = "@CyyFr"

ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

FORCED_CHANNEL = "@TAK_BE_T"
FORCED_GROUP = "@TAK_B_ET"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "bot_data.json"


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
        "channel": FORCED_CHANNEL,
        "group": FORCED_GROUP
    }
}


# =========================
# DATA
# =========================

def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        return data

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

        save_data()


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
        user.get("balance",0)
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

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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
# PROFILE
# =========================

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

        f"👤 نام: {u['name']}\n"

        f"💰 موجودی: {balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: {u['referrals']}",

        reply_markup=main_keyboard(
            user.id
        )

)


# =========================
# ADMIN PANEL
# =========================

async def admin_panel(update, context):

    user = update.effective_user

    if not is_owner(user.id):
        return


    status = (
        "روشن ✅"
        if data["settings"]["bot"]
        else "خاموش ❌"
    )


    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت ربات: {status}\n"

        f"📢 چنل اجباری: "
        f"{data['settings'].get('channel')}\n"

        f"👥 گپ اجباری: "
        f"{data['settings'].get('group')}",

        reply_markup=admin_keyboard()

    )



# =========================
# ADMIN CALLBACK
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    user = query.from_user

    await query.answer()


    if not is_owner(user.id):
        return



    if query.data == "toggle_bot":

        data["settings"]["bot"] = (
            not data["settings"]["bot"]
        )

        save_data()


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


        users = len(
            data["users"]
        )


        total = sum(

            int(x.get("balance",0))

            for x in data["users"].values()

        )


        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n\n"

            f"💰 مجموع موجودی:\n"
            f"{total:,} DOGS\n\n"

            f"💳 واریزی‌ها: "
            f"{len(data['deposits'])}\n"

            f"💰 برداشت‌ها: "
            f"{len(data['withdraws'])}",

            reply_markup=admin_keyboard()

        )


    elif query.data == "set_channel":

        context.user_data["admin"] = "channel"

        await query.message.reply_text(

            "📢 آیدی چنل را ارسال کنید\n\n"

            "مثال:\n"
            "@channel"

        )


    elif query.data == "set_group":

        context.user_data["admin"] = "group"

        await query.message.reply_text(

            "👥 آیدی گپ را ارسال کنید\n\n"

            "مثال:\n"
            "@group"

        )


    elif query.data == "transfer_owner":

        context.user_data["admin"] = "owner"

        await query.message.reply_text(

            "👑 آیدی عددی مالک جدید را ارسال کنید."

        )



# =========================
# ADMIN TEXT
# =========================

async def admin_text(update, context):

    if not is_owner(
        update.effective_user.id
    ):
        return False


    state = context.user_data.get(
        "admin"
    )


    if not state:
        return False


    text = update.message.text.strip()



    if state == "channel":

        data["settings"]["channel"] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ چنل اجباری ذخیره شد."
        )


    elif state == "group":

        data["settings"]["group"] = text

        save_data()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد."
        )


    elif state == "owner":

        try:

            new_owner = int(text)

        except:

            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید."
            )

            return True



        data["owner"] = new_owner

        save_data()

        context.user_data.clear()


        await update.message.reply_text(

            "✅ انتقال مالکیت انجام شد."

        )


    return True

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
                    callback_data="ultra"
                ),

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="exchange"
                )

            ]

        ])

    )



# =========================
# DEPOSIT METHOD
# =========================

async def deposit_callback(update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "ultra":

        context.user_data["deposit_method"] = "اولترا"


    else:

        context.user_data["deposit_method"] = "صرافی"



    context.user_data["state"] = "deposit_amount"


    await query.message.reply_text(

        "💰 مبلغ واریز را ارسال کنید\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS\n\n"
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

    except:

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



    method = context.user_data.get(
        "deposit_method"
    )


    context.user_data["amount"] = amount

    context.user_data["state"] = (
        "deposit_receipt"
    )



    if method == "اولترا":


        copy_text = (
            f"ULTRA {amount} DOGS {ULTRA_ADDRESS}"
        )


        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ:\n"
            f"{amount:,} DOGS\n\n"

            "📌 متن واریز:\n"

            f"ULTRA {amount} DOGS\n\n"

            "👤 آیدی:\n"

            f"{ULTRA_ADDRESS}\n\n"

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

# =========================
# DEPOSIT RECEIPT
# =========================

async def deposit_receipt(update, context):

    user = update.effective_user

    amount = context.user_data.get(
        "amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )


    if not amount or not method:

        await update.message.reply_text(
            "❌ درخواست واریز منقضی شده."
        )

        context.user_data.clear()

        return



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
            "❌ عکس یا لینک تراکنش ارسال کنید."
        )

        return



    request_id = (
        f"dep_{user.id}_{int(time.time())}"
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


    save_data()


    context.user_data.clear()



    await update.message.reply_text(

        "✅ رسید ارسال شد.\n\n"

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


    caption = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n"

        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method}\n\n"

        f"🆔 درخواست:\n{request_id}"

    )


    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تأیید",

                callback_data=
                f"approve_dep_{request_id}"

            ),

            InlineKeyboardButton(

                "❌ رد",

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

                text=caption
                +
                "\n\n🔗 رسید:\n"
                +
                receipt,

                reply_markup=buttons

            )


    except Exception as e:

        print(
            "OWNER SEND ERROR:",
            e
        )

# =========================
# WITHDRAW
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS\n\n"

            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data["state"] = (
        "withdraw_amount"
    )


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید.\n\n"

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

    except:

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

            "❌ موجودی کافی نیست."

        )

        return



    context.user_data["withdraw_amount"] = amount

    context.user_data["state"] = (
        "withdraw_address"
    )


    await update.message.reply_text(

        "📍 آدرس یا آیدی دریافت DOGS را ارسال کنید."

    )



# =========================
# WITHDRAW ADDRESS
# =========================

async def withdraw_address(update, context):

    user = update.effective_user


    address = (
        update.message.text.strip()
    )


    amount = context.user_data.get(
        "withdraw_amount"
    )


    if not amount:

        context.user_data.clear()

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
        f"wd_{user.id}_{int(time.time())}"
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

        "⏳ منتظر تأیید مالک باشید."

    )



    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تأیید",

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

# =========================
# ADMIN APPROVE / REJECT
# =========================

async def approve_reject(update, context):

    query = update.callback_query

    await query.answer()


    if not is_owner(
        query.from_user.id
    ):
        return



    parts = query.data.split("_")

    action = parts[0]

    kind = parts[1]

    request_id = "_".join(
        parts[2:]
    )



    # =====================
    # DEPOSIT
    # =====================

    if kind == "dep":

        req = data["deposits"].get(
            request_id
        )


        if not req:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return



        uid = req["user_id"]



        if action == "approve":


            add_balance(
                uid,
                req["amount"]
            )


            req["status"] = "approved"


            await query.edit_message_text(

                "✅ واریز تأیید شد\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS"

            )


            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "✅ واریز شما تأیید شد.\n\n"

                        f"💰 +{req['amount']:,} DOGS\n\n"

                        f"💳 موجودی:\n"
                        f"{balance(uid):,} DOGS"

                    )

                )

            except:

                pass



        else:


            req["status"] = "rejected"


            await query.edit_message_text(

                "❌ واریز رد شد\n\n"

                f"👤 کاربر: {uid}"

            )



        save_data()




    # =====================
    # WITHDRAW
    # =====================


    elif kind == "wd":


        req = data["withdraws"].get(
            request_id
        )


        if not req:

            await query.edit_message_text(
                "❌ درخواست پیدا نشد."
            )

            return



        uid = req["user_id"]



        if action == "approve":


            req["status"] = "approved"



            await query.edit_message_text(

                "✅ برداشت تأیید شد\n\n"

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
                        f"{req['amount']:,} DOGS"

                    )

                )

            except:

                pass



        else:


            req["status"] = "rejected"


            add_balance(
                uid,
                req["amount"]
            )


            await query.edit_message_text(

                "❌ برداشت رد شد\n\n"

                "💰 مبلغ به حساب کاربر برگشت."

            )



            try:

                await context.bot.send_message(

                    chat_id=uid,

                    text=(

                        "❌ برداشت شما رد شد.\n\n"

                        f"💰 مبلغ "
                        f"{req['amount']:,} DOGS "
                        "برگشت داده شد."

                    )

                )

            except:

                pass



        save_data()

# =========================
# SUPPORT
# =========================

async def support(update, context):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        f"{SUPPORT_USERNAME}"

    )



# =========================
# REFERRAL
# =========================

async def referrals(update, context):

    user = update.effective_user

    bot_username = context.bot.username


    link = (
        f"https://t.me/{bot_username}"
        f"?start=ref_{user.id}"
    )


    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"👥 تعداد: "
        f"{get_user(user.id).get('referrals',0)}"

    )



# =========================
# TEXT ROUTER
# =========================

async def text_router(update, context):

    if not update.message:
        return


    text = update.message.text

    state = context.user_data.get(
        "state"
    )


    # admin inputs

    if await admin_text(
        update,
        context
    ):
        return



    if text == "⚙️ پنل مدیریت":

        await admin_panel(
            update,
            context
        )

        return



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

    state = context.user_data.get(
        "state"
    )


    if state == "deposit_receipt":

        await deposit_receipt(
            update,
            context
        )



# =========================
# MAIN
# =========================

def main():

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )



    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )



    app.add_handler(
        CallbackQueryHandler(
            deposit_callback,
            pattern="^(ultra|exchange)$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(toggle_bot|set_channel|set_group|stats|transfer_owner)$"
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



    print(
        "BOT STARTED"
    )


    app.run_polling()



if __name__ == "__main__":

    main()
