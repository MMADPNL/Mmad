import json
import os
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_WITHDRAW = 10000
REF_REWARD = 50

DATA_FILE = "bot_data.json"


# =========================
# DATABASE
# =========================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "group": "",
        "channel": ""
    }
}


def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return DEFAULT_DATA



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
# USER SYSTEM
# =========================

def create_user(user):

    uid = str(user.id)

    if uid not in data["users"]:

        data["users"][uid] = {

            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "refs": [],
            "ref_by": None,
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

    return int(user.get("balance", 0))



def add_balance(uid, amount):

    user = get_user(uid)

    if user:

        user["balance"] += int(amount)

        save_data()



def remove_balance(uid, amount):

    user = get_user(uid)

    if user and user["balance"] >= amount:

        user["balance"] -= int(amount)

        save_data()

        return True

    return False



def is_owner(uid):

    return int(uid) == int(
        data.get("owner", OWNER_ID)
        )
    # =========================
# KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [

        [
            InlineKeyboardButton(
                "💳 واریز",
                callback_data="deposit"
            ),
            InlineKeyboardButton(
                "💰 برداشت",
                callback_data="withdraw"
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

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"
        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )

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
        f"👤 نام: {user['name']}\n"
        f"💰 موجودی: {balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه: {len(user['refs'])}",

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
# REFERRAL
# =========================

async def referral(query, context):

    uid = query.from_user.id

    bot = await context.bot.get_me()


    link = (
        f"https://t.me/{bot.username}"
        f"?start={uid}"
    )


    await query.edit_message_text(

        "👥 زیرمجموعه گیری\n\n"
        f"🔗 لینک شما:\n{link}\n\n"
        f"🎁 پاداش هر دعوت: {REF_REWARD} DOGS"

    )



# =========================
# DEPOSIT MENU
# =========================

async def deposit_menu(query):

    await query.edit_message_text(

        "💳 روش واریز را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💎 انتقال DOGS",
                        callback_data="exchange"
                    )
                ]
            ]
        )

    )



# =========================
# DEPOSIT ADDRESS
# =========================

async def exchange(query, context):

    context.user_data["state"] = "deposit"


    await query.edit_message_text(

        "💎 واریز DOGS\n\n"
        "DOGS را به آدرس زیر ارسال کنید:\n\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از انتقال، رسید یا هش تراکنش را ارسال کنید.\n"
        "مالک بررسی می‌کند."

            )
# =========================
# WITHDRAW
# =========================

async def withdraw_menu(query, context):

    context.user_data["state"] = "withdraw"


    await query.edit_message_text(

        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "تعداد DOGS را ارسال کنید."

    )



# =========================
# SUPPORT
# =========================

async def support(query, context):

    context.user_data["state"] = "support"


    await query.edit_message_text(

        "🎧 پشتیبانی\n\n"
        f"{SUPPORT_USERNAME}\n\n"
        "پیام خود را ارسال کنید."

    )



# =========================
# CALLBACK HANDLER
# =========================

async def callback_handler(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user

    create_user(user)


    action = query.data



    if action == "home":

        await query.edit_message_text(

            "منوی اصلی",

            reply_markup=main_keyboard(
                user.id
            )

        )



    elif action == "profile":

        await profile(query)



    elif action == "deposit":

        await deposit_menu(query)



    elif action == "exchange":

        await exchange(
            query,
            context
        )



    elif action == "withdraw":

        await withdraw_menu(
            query,
            context
        )



    elif action == "support":

        await support(
            query,
            context
        )



    elif action == "ref":

        await referral(
            query,
            context
        )



    elif action == "admin":

        if not is_owner(user.id):

            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )

            return


        await query.edit_message_text(

            "⚙️ پنل مالک\n\n"
            "مدیریت ربات",

            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📊 آمار",
                            callback_data="stats"
                        )
                    ]
                ]
            )

        )



    elif action == "stats":

        if is_owner(user.id):

            await query.edit_message_text(

                "📊 آمار\n\n"
                f"👤 کاربران: {len(data['users'])}"

)
            # =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    user = update.effective_user

    create_user(user)


    text = update.message.text.strip()

    state = context.user_data.get("state")



    # =====================
    # WITHDRAW REQUEST
    # =====================

    if state == "withdraw":

        try:

            amount = int(text)

        except:

            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید"
            )

            return



        if amount < MIN_WITHDRAW:

            await update.message.reply_text(
                f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است"
            )

            return



        if balance(user.id) < amount:

            await update.message.reply_text(
                "❌ موجودی کافی نیست"
            )

            return



        remove_balance(
            user.id,
            amount
        )


        data["withdraws"][str(user.id)] = {

            "amount": amount,
            "status": "pending"

        }

        save_data()


        context.user_data.clear()


        await update.message.reply_text(
            "✅ درخواست برداشت ارسال شد"
        )


        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💰 درخواست برداشت\n\n"
                f"👤 کاربر: {user.id}\n"
                f"💰 مقدار: {amount:,} DOGS"

            )

        )


        return



    # =====================
    # DEPOSIT RECEIPT
    # =====================

    if state == "deposit":


        data["deposits"][str(user.id)] = {

            "text": text,
            "status": "pending"

        }


        save_data()


        context.user_data.clear()


        await update.message.reply_text(
            "✅ رسید ارسال شد، منتظر تایید مالک باشید."
        )


        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"📝 رسید:\n{text}"

            ),

            reply_markup=InlineKeyboardMarkup(

                [
                    [
                        InlineKeyboardButton(
                            "✅ تایید",
                            callback_data=f"ok_d_{user.id}"
                        ),

                        InlineKeyboardButton(
                            "❌ رد",
                            callback_data=f"no_d_{user.id}"
                        )
                    ]
                ]

            )

        )


        return



    # =====================
    # SUPPORT
    # =====================

    if state == "support":


        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "🎧 پیام پشتیبانی\n\n"
                f"👤 کاربر: {user.id}\n\n"
                f"{text}"

            )

        )


        context.user_data.clear()


        await update.message.reply_text(
            "✅ پیام ارسال شد"
        )


        return
        # =========================
# ADMIN CALLBACKS
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user


    if not is_owner(user.id):

        await query.answer(
            "دسترسی ندارید",
            show_alert=True
        )

        return



    action = query.data



    # تایید واریز

    if action.startswith("ok_d_"):

        uid = int(
            action.split("_")[2]
        )


        if str(uid) in data["deposits"]:

            data["deposits"][str(uid)]["status"] = "accepted"

            save_data()



        await query.edit_message_text(
            "✅ واریز تایید شد\n\n"
            f"👤 کاربر: {uid}\n\n"
            "برای اضافه کردن موجودی از دستور شارژ استفاده کنید."
        )


        return



    # رد واریز

    if action.startswith("no_d_"):

        uid = int(
            action.split("_")[2]
        )


        if str(uid) in data["deposits"]:

            data["deposits"][str(uid)]["status"] = "rejected"

            save_data()



        await query.edit_message_text(
            "❌ واریز رد شد\n\n"
            f"👤 کاربر: {uid}"
        )


        return



# =========================
# OWNER CHARGE
# =========================

async def owner_commands(update, context):

    user = update.effective_user


    if not is_owner(user.id):

        return



    text = update.message.text



    # مثال:
    # شارژ 123456 5000

    if text.startswith("شارژ"):

        try:

            parts = text.split()

            uid = int(parts[1])

            amount = int(parts[2])


        except:

            await update.message.reply_text(
                "❌ مثال:\nشارژ آیدی مقدار"
            )

            return



        create_user(
            type(
                "User",
                (),
                {
                    "id":uid,
                    "first_name":"",
                    "username":""
                }
            )
        )


        add_balance(
            uid,
            amount
        )


        await update.message.reply_text(

            "✅ موجودی اضافه شد\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مقدار: {amount:,} DOGS"

        )


        return

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


    # تایید و رد واریز مالک

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(ok_d_|no_d_)"
        )
    )


    # منوی دکمه ها

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # دستورات مالک مثل شارژ

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.User(user_id=OWNER_ID),
            owner_commands
        )
    )


    # پیام های عادی

    app.add_handler(
        MessageHandler(
            filters.TEXT,
            message_handler
        )
    )


    print(
        "BOT STARTED"
    )


    app.run_polling(
        drop_pending_updates=True
    )



if __name__ == "__main__":

    main()
