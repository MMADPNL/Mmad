import os
import json
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# =====================
# SETTINGS
# =====================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

DOGS_WALLET = "YOUR_WALLET"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "bot_data.json"


# =====================
# DATABASE
# =====================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "owner": OWNER_ID
}


def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except:
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


# =====================
# USER SYSTEM
# =====================

def create_user(user):

    uid = str(user.id)

    if uid not in data["users"]:

        data["users"][uid] = {

            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "date": datetime.now().isoformat()

        }

        save_data()

    return data["users"][uid]



def get_user(uid):

    return data["users"].get(str(uid))



def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    return int(user.get("balance",0))



def add_balance(uid,amount):

    user = get_user(uid)

    if not user:
        return

    user["balance"] = (
        balance(uid)+int(amount)
    )

    save_data()



def remove_balance(uid,amount):

    if balance(uid) < amount:
        return False

    user = get_user(uid)

    user["balance"] -= int(amount)

    save_data()

    return True



def is_owner(uid):

    return int(uid)==int(OWNER_ID)


# =====================
# KEYBOARD
# =====================

def main_keyboard(uid):

    buttons = [

        [
            "💳 واریزی",
            "💰 برداشت"
        ],

        [
            "👤 پروفایل",
            "👥 زیرمجموعه"
        ],

        [
            "🎮 بازی"
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


# =====================
# START
# =====================

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "از منوی زیر انتخاب کنید:",

        reply_markup=main_keyboard(user.id)

                            )

# =====================
# PROFILE
# =====================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    create_user(user)

    u = get_user(user.id)

    username = (
        f"@{u.get('username')}"
        if u.get("username")
        else "ندارد"
    )

    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {user.id}\n"
        f"👤 نام: {u.get('name')}\n"
        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 موجودی: {balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)
    )


# =====================
# REFERRAL
# =====================

async def referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    bot = context.bot.username

    link = (
        f"https://t.me/{bot}?start=ref_{user.id}"
    )


    await update.message.reply_text(

        "👥 زیرمجموعه گیری\n\n"

        "🔗 لینک شما:\n"
        f"{link}\n\n"

        "هر کاربر جدید با لینک شما ثبت شود در سیستم ذخیره می‌شود.",

        reply_markup=main_keyboard(user.id)

    )


# =====================
# SUPPORT
# =====================

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        f"ارتباط با پشتیبانی:\n{SUPPORT_USERNAME}",

        reply_markup=main_keyboard(
            update.effective_user.id
        )

    )


# =====================
# BACK
# =====================

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    await update.message.reply_text(

        "🏠 منوی اصلی",

        reply_markup=main_keyboard(user.id)

    )

# =====================
# DEPOSIT
# =====================

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    context.user_data["state"] = "deposit_amount"


    await update.message.reply_text(

        "💳 واریز DOGS\n\n"

        f"📌 آدرس کیف پول:\n"
        f"{DOGS_WALLET}\n\n"

        "بعد از واریز:\n"
        "1️⃣ مقدار DOGS را ارسال کنید.\n"
        "2️⃣ رسید یا لینک تراکنش را ارسال کنید.\n\n"

        "🔻 حداقل واریز: 5,000 DOGS",

        reply_markup=main_keyboard(
            update.effective_user.id
        )

    )


# =====================
# WITHDRAW
# =====================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    create_user(user)


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: {balance(user.id):,} DOGS\n"

            "🔻 حداقل برداشت: 10,000 DOGS",

            reply_markup=main_keyboard(user.id)

        )

        return


    context.user_data.clear()

    context.user_data["state"] = "withdraw"


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "آدرس کیف پول خود را ارسال کنید.\n\n"

        "🔻 حداقل برداشت: 10,000 DOGS",

        reply_markup=main_keyboard(user.id)

    )


# =====================
# HANDLE STATES
# =====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    state = context.user_data.get("state")


    if state == "deposit_amount":

        try:
            amount = int(update.message.text)

        except:

            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید."
            )
            return


        if amount < 5000:

            await update.message.reply_text(
                "❌ حداقل واریز 5,000 DOGS است."
            )
            return


        context.user_data["deposit"] = amount
        context.user_data["state"] = "deposit_receipt"


        await update.message.reply_text(
            "✅ مقدار ثبت شد.\n\n"
            "حالا رسید یا لینک تراکنش را ارسال کنید."
        )


    elif state == "deposit_receipt":


        user = update.effective_user

        amount = context.user_data.get(
            "deposit",
            0
        )


        req = str(
            datetime.now().timestamp()
        )


        data["deposits"][req] = {

            "user": user.id,
            "amount": amount,
            "receipt": update.message.text,
            "status": "pending"

        }


        save_data()


        await update.message.reply_text(

            "✅ درخواست واریز ارسال شد.\n"
            "منتظر تایید مالک باشید.",

            reply_markup=main_keyboard(user.id)

        )


        await context.bot.send_message(

            OWNER_ID,

            "💳 واریز جدید\n\n"
            f"👤 کاربر: {user.id}\n"
            f"💰 مقدار: {amount:,} DOGS\n\n"
            f"رسید:\n{update.message.text}"

        )


        context.user_data.clear()


    elif state == "withdraw":


        address = update.message.text


        context.user_data["address"] = address
        context.user_data["state"] = "withdraw_amount"


        await update.message.reply_text(
            "مقدار برداشت را ارسال کنید."
        )


    elif state == "withdraw_amount":


        user = update.effective_user


        try:
            amount = int(update.message.text)

        except:

            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید."
            )
            return


        if amount < 10000:

            await update.message.reply_text(
                "❌ حداقل برداشت 10,000 DOGS است."
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


        await update.message.reply_text(

            "✅ درخواست برداشت ثبت شد.",

            reply_markup=main_keyboard(user.id)

        )


        await context.bot.send_message(

            OWNER_ID,

            "💰 برداشت جدید\n\n"
            f"👤 کاربر: {user.id}\n"
            f"💰 مقدار: {amount:,} DOGS\n"
            f"💳 آدرس:\n{context.user_data.get('address')}"

        )


        context.user_data.clear()

# =====================
# GAME SYSTEM (PRIVATE)
# =====================

import random


async def game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    context.user_data["state"] = "game_amount"


    await update.message.reply_text(

        "🎮 بازی DOGS\n\n"

        "مقدار شرط را ارسال کنید.\n\n"

        "مثال:\n"
        "500\n\n"

        "حداقل شرط: 500 DOGS",

        reply_markup=main_keyboard(
            update.effective_user.id
        )

    )


async def game_play(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    try:

        amount = int(
            update.message.text
        )

    except:

        await update.message.reply_text(
            "❌ مقدار شرط را عددی ارسال کنید."
        )

        return


    if amount < 500:

        await update.message.reply_text(
            "❌ حداقل شرط 500 DOGS است."
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


    user_score = random.randint(
        1,
        6
    )

    bot_score = random.randint(
        1,
        6
    )


    if user_score > bot_score:

        prize = amount * 2

        add_balance(
            user.id,
            prize
        )


        result = (
            "🏆 شما بردید!"
            f"\n💰 جایزه: {prize:,} DOGS"
        )


    elif user_score == bot_score:

        add_balance(
            user.id,
            amount
        )

        result = (
            "🤝 مساوی شد!"
            "\nشرط برگشت داده شد."
        )


    else:

        result = (
            "😢 شما باختید!"
            f"\n💸 باخت: {amount:,} DOGS"
        )


    await update.message.reply_text(

        "🎮 نتیجه بازی\n\n"

        f"👤 امتیاز شما: {user_score}\n"
        f"🤖 امتیاز ربات: {bot_score}\n\n"

        f"{result}\n\n"

        f"💰 موجودی جدید:\n"
        f"{balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)

    )


    context.user_data.clear()

# =====================
# MESSAGE ROUTER
# =====================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user = update.effective_user


    if text == "👤 پروفایل":
        await profile(update, context)

    elif text == "👥 زیرمجموعه":
        await referrals(update, context)

    elif text == "🎧 پشتیبانی":
        await support(update, context)

    elif text == "💳 واریزی":
        await deposit(update, context)

    elif text == "💰 برداشت":
        await withdraw(update, context)

    elif text == "🎮 بازی":
        await game_menu(update, context)

    elif text == "🔙 برگشت":
        await back(update, context)

    elif context.user_data.get("state"):
        await handle_text(update, context)

    elif text.isdigit() and context.user_data.get("state") == "game_amount":
        await game_play(update, context)



# =====================
# MAIN
# =====================

def main():

    if not BOT_TOKEN:

        print("BOT_TOKEN پیدا نشد")
        return


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
        MessageHandler(
            filters.PHOTO,
            handle_text
        )
    )


    print("✅ BOT STARTED")


    app.run_polling(
        drop_pending_updates=True
    )



if __name__ == "__main__":
    main()
