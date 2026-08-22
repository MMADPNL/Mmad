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

        "channel": "@TAK_BE_T",

        "group": "@TAK_B_ET"

    }

}



# =========================
# SAFE DATA
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
# USER
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



def get_balance(uid):

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
        get_balance(uid)
        +
        int(amount)
    )

    save_data()

    return True



def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return False


    if get_balance(uid) < int(amount):

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
# ERROR HANDLER
# =========================

async def error_handler(update, context):

    print(
        "ERROR:",
        context.error
    )

    traceback.print_exc()

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"
        f"👤 {user.first_name}\n"
        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )

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
        f"💰 موجودی: {get_balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه: {u['referrals']}",

        reply_markup=main_keyboard(
            user.id
        )

    )



# =========================
# ADMIN
# =========================

async def admin_panel(update, context):

    if not is_owner(update.effective_user.id):

        return


    await update.message.reply_text(

        "⚙️ پنل مدیریت مالک\n\n"

        f"🤖 وضعیت: "
        f"{'روشن ✅' if data['settings']['bot'] else 'خاموش ❌'}\n\n"

        f"📢 چنل: {data['settings']['channel']}\n"

        f"👥 گپ: {data['settings']['group']}",

        reply_markup=admin_keyboard()

    )



async def admin_callback(update, context):

    q = update.callback_query

    await q.answer()


    if not is_owner(q.from_user.id):

        return


    if q.data == "toggle_bot":

        data["settings"]["bot"] = not data["settings"]["bot"]

        save_data()


        await q.edit_message_text(

            "✅ وضعیت ربات تغییر کرد",

            reply_markup=admin_keyboard()

        )



    elif q.data == "stats":

        total = sum(

            int(x.get("balance",0))

            for x in data["users"].values()

        )


        await q.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {len(data['users'])}\n"

            f"💰 کل موجودی: {total:,}\n"

            f"💳 واریزی: {len(data['deposits'])}\n"

            f"💰 برداشت: {len(data['withdraws'])}",

            reply_markup=admin_keyboard()

        )



    elif q.data == "set_channel":

        context.user_data["admin_state"] = "channel"

        await q.message.reply_text(
            "📢 آیدی چنل را بفرستید"
        )



    elif q.data == "set_group":

        context.user_data["admin_state"] = "group"

        await q.message.reply_text(
            "👥 آیدی گپ را بفرستید"
        )



    elif q.data == "transfer_owner":

        context.user_data["admin_state"] = "owner"

        await q.message.reply_text(
            "👑 آیدی عددی مالک جدید را ارسال کنید"
        )



# =========================
# DEPOSIT MENU
# =========================

async def deposit_menu(update, context):

    await update.message.reply_text(

        "💳 واریزی\n\n"
        "روش را انتخاب کنید:",

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
# DEPOSIT SELECT
# =========================

async def deposit_select(update, context):

    q = update.callback_query

    await q.answer()


    context.user_data["deposit_method"] = q.data

    context.user_data["state"] = "deposit_amount"


    await q.message.reply_text(

        "💰 مقدار واریز را ارسال کنید\n\n"
        f"حداقل: {MIN_DEPOSIT:,} DOGS"

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
            "❌ فقط عدد ارسال کنید"
        )

        return



    if amount < MIN_DEPOSIT:

        await update.message.reply_text(
            f"❌ حداقل {MIN_DEPOSIT:,} DOGS"
        )

        return



    context.user_data["amount"] = amount

    context.user_data["state"] = "deposit_receipt"


    method = context.user_data.get(
        "deposit_method"
    )


    if method == "ultra":

        text = (
            f"ULTRA {amount} DOGS\n"
            "@CyyFr"
        )


        await update.message.reply_text(

            "🟣 اولترا\n\n"

            f"📋 متن واریز:\n{text}\n\n"

            "بعد از پرداخت رسید را ارسال کنید"

        )


    else:

        await update.message.reply_text(

            "🏦 صرافی\n\n"

            f"📍 ولت:\n{EXCHANGE_WALLET}\n\n"

            "بعد از پرداخت رسید را ارسال کنید"

)

# =========================
# SUPPORT
# =========================

async def support(update, context):

    context.user_data["state"] = "support"

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"
        "پیامت رو ارسال کن."

    )



async def support_message(update, context):

    if context.user_data.get("state") != "support":

        return False


    user = update.effective_user


    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "🎧 پیام پشتیبانی جدید\n\n"

            f"👤 نام: {user.first_name}\n"

            f"🆔 آیدی: {user.id}\n\n"

            f"💬 پیام:\n{update.message.text}"

        )

    )


    context.user_data.clear()


    await update.message.reply_text(

        "✅ پیام شما برای پشتیبانی ارسال شد."

    )

    return True



# =========================
# WITHDRAW
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    if get_balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست\n\n"

            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data["state"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 مبلغ برداشت را ارسال کنید."

    )



async def withdraw_amount(update, context):

    try:

        amount = int(update.message.text)

    except:

        await update.message.reply_text(
            "❌ عدد ارسال کنید"
        )

        return



    user = update.effective_user


    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ کمتر از حداقل برداشت است"
        )

        return


    if get_balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )

        return



    context.user_data["withdraw_amount"] = amount

    context.user_data["state"] = "withdraw_address"


    await update.message.reply_text(

        "📍 آدرس دریافت را ارسال کنید."

    )



async def withdraw_address(update, context):

    user = update.effective_user

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
            "❌ خطا"
        )

        return



    address = update.message.text


    rid = (
        f"wd_{user.id}_{int(time.time())}"
    )


    data["withdraws"][rid] = {

        "id": rid,

        "user_id": user.id,

        "amount": amount,

        "address": address,

        "status": "pending"

    }


    save_data()

    context.user_data.clear()


    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد\n\n"

        f"💰 مبلغ: {amount:,} DOGS"

    )


    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "💰 برداشت جدید\n\n"

            f"👤 کاربر: {user.id}\n"

            f"💰 مبلغ: {amount:,} DOGS\n"

            f"📍 آدرس:\n{address}"

        )

    )



# =========================
# DEPOSIT RECEIPT
# =========================

async def deposit_receipt(update, context):

    user = update.effective_user


    amount = context.user_data.get(
        "amount"
    )


    if not amount:

        context.user_data.clear()

        return



    rid = (
        f"dep_{user.id}_{int(time.time())}"
    )


    data["deposits"][rid] = {

        "user_id": user.id,

        "amount": amount,

        "status": "pending"

    }


    save_data()

    context.user_data.clear()


    await update.message.reply_text(

        "✅ رسید ارسال شد\n"

        "⏳ منتظر تایید مالک باشید"

    )


    await context.bot.send_message(

        chat_id=data["owner"],

        text=(

            "💳 واریزی جدید\n\n"

            f"👤 آیدی: {user.id}\n"

            f"💰 مبلغ: {amount:,} DOGS"

        )

    )



# =========================
# TEXT ROUTER
# =========================

async def router(update, context):

    if not update.message:

        return


    text = update.message.text


    # پشتیبانی

    if await support_message(update, context):

        return



    state = context.user_data.get(
        "state"
    )


    if text == "💳 واریزی":

        await deposit_menu(update, context)
        return


    if text == "💰 برداشت":

        await withdraw_menu(update, context)
        return


    if text == "👤 پروفایل":

        await profile(update, context)
        return


    if text == "🎧 پشتیبانی":

        await support(update, context)
        return


    if text == "⚙️ پنل مدیریت":

        await admin_panel(update, context)
        return



    if state == "deposit_amount":

        await deposit_amount(update, context)
        return


    if state == "deposit_receipt":

        await deposit_receipt(update, context)
        return


    if state == "withdraw_amount":

        await withdraw_amount(update, context)
        return


    if state == "withdraw_address":

        await withdraw_address(update, context)
        return



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
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            router
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            deposit_select,
            pattern="^(ultra|exchange)$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            admin_callback
        )
    )


    app.add_error_handler(
        error_handler
    )


    print("BOT STARTED")

    app.run_polling()



if __name__ == "__main__":

    main()
