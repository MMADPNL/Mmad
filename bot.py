import json
import os
import random
import asyncio
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_WITHDRAW = 10000
MIN_DEPOSIT = 5000

REF_REWARD = 50

DATA_FILE = "bot_data.json"


# =========================
# DATA
# =========================

DEFAULT_DATA = {
    "users": {},
    "pending_deposits": {},
    "pending_withdrawals": {},
    "games": {},
    "settings": {
        "bot_enabled": True,
        "force_channel": "",
        "force_group": ""
    },
    "owner_id": OWNER_ID
}


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


def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except:
        return DEFAULT_DATA


data = load_data()


# =========================
# USER SYSTEM
# =========================

def ensure_user(user):

    uid = str(user.id)

    if uid not in data["users"]:

        data["users"][uid] = {
            "id": user.id,
            "username": user.username or "",
            "name": user.first_name or "",
            "balance": 0,
            "referrals": [],
            "referred_by": None,
            "created": datetime.now().isoformat()
        }

        save_data()

    else:

        u = data["users"][uid]

        u["username"] = user.username or ""
        u["name"] = user.first_name or ""

        save_data()


    return data["users"][uid]



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



def set_balance(uid, amount):

    uid = str(uid)

    if uid not in data["users"]:
        return False

    data["users"][uid]["balance"] = max(
        0,
        int(amount)
    )

    save_data()

    return True



def add_balance(uid, amount):

    return set_balance(
        uid,
        get_balance(uid)+int(amount)
    )



def remove_balance(uid, amount):

    if get_balance(uid) < amount:
        return False

    return set_balance(
        uid,
        get_balance(uid)-amount
    )



# =========================
# OWNER
# =========================

def get_owner():

    return int(
        data.get(
            "owner_id",
            OWNER_ID
        )
    )


def is_owner(uid):

    return int(uid) == get_owner()
    # =========================
# KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [
        [
            InlineKeyboardButton(
                "💰 برداشت",
                callback_data="withdraw"
            ),
            InlineKeyboardButton(
                "💳 واریز",
                callback_data="deposit"
            )
        ],
        [
            InlineKeyboardButton(
                "👤 پروفایل",
                callback_data="profile"
            ),
            InlineKeyboardButton(
                "👥 زیرمجموعه",
                callback_data="ref"
            )
        ],
        [
            InlineKeyboardButton(
                "🎧 پشتیبانی",
                callback_data="support"
            )
        ]
    ]

    if is_owner(uid):

        rows.append(
            [
                InlineKeyboardButton(
                    "⚙️ پنل مالک",
                    callback_data="admin"
                )
            ]
        )

    return InlineKeyboardMarkup(rows)



# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user

    ensure_user(user)

    await update.message.reply_text(
        "🤖 خوش آمدید\n\n"
        f"💰 موجودی شما:\n"
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id)
    )



# =========================
# PROFILE
# =========================

async def profile(query):

    uid = query.from_user.id

    user = get_user(uid)

    await query.edit_message_text(

        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {user.get('name')}\n"
        f"💰 موجودی: {get_balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه: "
        f"{len(user.get('referrals',[]))}",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ]
        )
    )



# =========================
# DEPOSIT
# =========================

async def deposit(query,context):

    context.user_data["state"]="deposit"

    await query.edit_message_text(

        "💳 واریز DOGS\n\n"
        f"آدرس کیف پول:\n\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از واریز رسید را ارسال کنید."

    )



# =========================
# WITHDRAW
# =========================

async def withdraw(query,context):

    context.user_data["state"]="withdraw"

    await query.edit_message_text(

        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "مقدار را ارسال کنید."
    )



# =========================
# SUPPORT
# =========================

async def support(query,context):

    context.user_data["state"]="support"

    await query.edit_message_text(

        "🎧 پشتیبانی\n\n"
        f"{SUPPORT_USERNAME}\n\n"
        "پیام خود را ارسال کنید."
    )



# =========================
# REFERRAL
# =========================

async def referral(query,context):

    uid=query.from_user.id

    bot=await context.bot.get_me()

    link=f"https://t.me/{bot.username}?start={uid}"


    await query.edit_message_text(

        "👥 زیرمجموعه گیری\n\n"
        "لینک شما:\n"
        f"{link}\n\n"
        f"🎁 پاداش: {REF_REWARD} DOGS"

    )



# =========================
# CALLBACK
# =========================

async def callback_handler(update,context):

    query=update.callback_query

    await query.answer()

    uid=query.from_user.id

    ensure_user(
        query.from_user
    )

    action=query.data


    if action=="home":

        await query.edit_message_text(
            "منوی اصلی",
            reply_markup=main_keyboard(uid)
        )


    elif action=="profile":

        await profile(query)


    elif action=="deposit":

        await deposit(
            query,
            context
        )


    elif action=="withdraw":

        await withdraw(
            query,
            context
        )


    elif action=="support":

        await support(
            query,
            context
        )


    elif action=="ref":

        await referral(
            query,
            context
        )


    elif action=="admin":

        if is_owner(uid):

            await query.edit_message_text(
                "⚙️ پنل مالک\n\n"
                "قسمت مدیریت در بخش بعدی اضافه می‌شود."
            )
        else:

            await query.answer(
                "دسترسی ندارید",
                show_alert=True
                    )
            return


# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    user = update.effective_user
    ensure_user(user)

    state = context.user_data.get("state")


    # برداشت
    if state == "withdraw":

        try:
            amount = int(update.message.text)
        except:
            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید."
            )
            return


        if amount < MIN_WITHDRAW:
            await update.message.reply_text(
                f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
            )
            return


        if get_balance(user.id) < amount:
            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )
            return


        remove_balance(
            user.id,
            amount
        )

        wid = str(
            random.randint(
                10000000,
                99999999
            )
        )


        data["pending_withdrawals"][wid] = {
            "user_id": user.id,
            "amount": amount,
            "status": "pending"
        }

        save_data()


        context.user_data.clear()


        await update.message.reply_text(
            "✅ درخواست برداشت ثبت شد."
        )


        await context.bot.send_message(
            chat_id=get_owner(),
            text=(
                "💰 برداشت جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"💰 مقدار: {amount:,} DOGS"
            )
        )

        return



    # پشتیبانی
    if state == "support":

        await context.bot.send_message(
            chat_id=get_owner(),
            text=(
                "🎧 پیام پشتیبانی\n\n"
                f"👤 {user.id}\n\n"
                f"{update.message.text}"
            )
        )


        context.user_data.clear()


        await update.message.reply_text(
            "✅ پیام ارسال شد."
        )

        return



    # رسید واریز
    if state == "deposit":


        did = str(
            random.randint(
                10000000,
                99999999
            )
        )


        data["pending_deposits"][did] = {
            "user_id": user.id,
            "content": update.message.text,
            "status": "pending"
        }


        save_data()


        context.user_data.clear()


        await update.message.reply_text(
            "✅ رسید ارسال شد.\nمنتظر تایید باشید."
        )


        await context.bot.send_message(
            chat_id=get_owner(),
            text=(
                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"📎 رسید:\n"
                f"{update.message.text}"
            )
        )

        return



    await update.message.reply_text(
        "از منو استفاده کنید.",
        reply_markup=main_keyboard(user.id)
    )



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
            callback_handler
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT,
            message_handler
        )
    )


    print(
        "BOT STARTED"
    )


    app.run_polling()



if __name__ == "__main__":
    main()            
