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

ULTRA_ID = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "bot_data.json"



# =========================
# DATABASE
# =========================

DEFAULT_DATA = {

    "users": {},

    "deposits": {},

    "withdraws": {},

    "owner": OWNER_ID

}



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


    return int(
        user.get("balance", 0)
    )



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

    return int(uid) == int(OWNER_ID)



# =========================
# KEYBOARD
# =========================

def main_keyboard(uid):

    buttons = [

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

        buttons.append(

            [
                InlineKeyboardButton(
                    "⚙️ پنل مالک",
                    callback_data="admin"
                )
            ]

        )


    return InlineKeyboardMarkup(buttons)

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
        f"💰 موجودی: {balance(uid):,} DOGS",

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
# DEPOSIT MENU
# =========================

async def deposit_menu(query):

    await query.edit_message_text(

        "💳 روش واریز را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(
                        "💎 اولترا",
                        callback_data="ultra"
                    )

                ],

                [

                    InlineKeyboardButton(
                        "💎 صرافی",
                        callback_data="exchange"
                    )

                ]

            ]

        )

    )



# =========================
# ULTRA DEPOSIT
# =========================

async def ultra(query, context):

    context.user_data["state"] = "deposit"


    await query.edit_message_text(

        "💎 اولترا\n\n"
        "DOGS را به این آیدی ارسال کنید:\n\n"
        f"{ULTRA_ID}\n\n"
        "بعد از ارسال، شات یا پیام رسید خود را بفرستید.\n\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"حداقل واریز: {MIN_DEPOSIT} DOGS"

    )



# =========================
# EXCHANGE DEPOSIT
# =========================

async def exchange(query, context):

    context.user_data["state"] = "deposit"


    await query.edit_message_text(

        "💎 صرافی\n\n"
        "DOGS را به این ولت ارسال کنید:\n\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از ارسال، شات یا لینک تراکنش خود را بفرستید.\n\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"حداقل واریز: {MIN_DEPOSIT} DOGS"

    )

# =========================
# WITHDRAW
# =========================

async def withdraw_menu(query, context):

    context.user_data["state"] = "withdraw"


    await query.edit_message_text(

        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "مقدار برداشت را به صورت عدد ارسال کنید."

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



    elif action == "ultra":

        await ultra(
            query,
            context
        )



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

# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    user = update.effective_user

    create_user(user)


    text = update.message.text.strip()

    state = context.user_data.get("state")



    # =====================
    # WITHDRAW
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

                "💰 برداشت جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"💰 مقدار: {amount:,} DOGS"

            )

        )


        return



    # =====================
    # DEPOSIT
    # =====================

    if state == "deposit":


        data["deposits"][str(user.id)] = {

            "receipt": text,
            "status": "pending"

        }


        save_data()


        context.user_data.clear()


        await update.message.reply_text(
            "✅ رسید ارسال شد\nمنتظر تایید مالک باشید."
        )


        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n\n"
                f"📝 رسید:\n{text}"

            ),

            reply_markup=InlineKeyboardMarkup(

                [

                    [

                        InlineKeyboardButton(
                            "✅ تایید",
                            callback_data=f"ok_dep_{user.id}"
                        ),

                        InlineKeyboardButton(
                            "❌ رد",
                            callback_data=f"no_dep_{user.id}"
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
            "✅ ارسال شد"
        )

        return

# =========================
# ADMIN CALLBACK
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user


    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید",
            show_alert=True
        )

        return



    action = query.data



    # =====================
    # ACCEPT DEPOSIT
    # =====================

    if action.startswith("ok_dep_"):

        uid = int(
            action.split("_")[2]
        )


        if str(uid) in data["deposits"]:


            data["deposits"][str(uid)]["status"] = "accepted"

            save_data()



            # اضافه شدن موجودی

            add_balance(
                uid,
                MIN_DEPOSIT
            )


            await query.edit_message_text(

                "✅ واریز تایید شد\n\n"
                f"👤 کاربر: {uid}\n"
                f"💰 اضافه شد: {MIN_DEPOSIT:,} DOGS"

            )


        return



    # =====================
    # REJECT DEPOSIT
    # =====================

    if action.startswith("no_dep_"):

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



        if not get_user(uid):

            await update.message.reply_text(
                "❌ کاربر پیدا نشد"
            )

            return



        add_balance(
            uid,
            amount
        )


        await update.message.reply_text(

            "✅ شارژ انجام شد\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مقدار: {amount:,} DOGS"

        )

# =========================
# GAME SYSTEM
# =========================

MIN_GAME = 500
MAX_GAME = 20000
GAME_FEE = 100

ACTIVE_GAMES = {}



async def game_command(update, context):

    try:

        amount = int(
            update.message.text.split()[1]
        )

    except:

        await update.message.reply_text(
            "❌ مثال:\nبازی 500"
        )

        return



    if amount < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل بازی {MIN_GAME} DOGS است"
        )

        return



    if amount > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر بازی {MAX_GAME} DOGS است"
        )

        return



    user = update.effective_user

    chat_id = update.effective_chat.id



    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )

        return



    if chat_id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ یک بازی در حال انتظار است"
        )

        return



    remove_balance(
        user.id,
        amount
    )


    ACTIVE_GAMES[chat_id] = {

        "creator": user.id,
        "amount": amount

    }



    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"
        f"👤 سازنده: {user.first_name}\n"
        f"💰 شرط: {amount:,} DOGS\n\n"
        "یک نفر برای ورود دکمه زیر را بزند.",

        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(

                        "🎮 ورود به بازی",

                        callback_data="join_game"

                    )

                ]

            ]

        )

    )



async def game_callback(update, context):

    query = update.callback_query

    await query.answer()


    chat_id = query.message.chat.id

    user = query.from_user



    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ بازی پیدا نشد",
            show_alert=True
        )

        return



    game = ACTIVE_GAMES[chat_id]


    if user.id == game["creator"]:

        await query.answer(
            "❌ خودت نمی‌توانی وارد شوی",
            show_alert=True
        )

        return



    if balance(user.id) < game["amount"]:

        await query.answer(
            "❌ موجودی کافی نیست",
            show_alert=True
        )

        return



    remove_balance(
        user.id,
        game["amount"]
    )


    total = game["amount"] * 2

    prize = total - GAME_FEE



    winner = user.id


    add_balance(
        winner,
        prize
    )


    add_balance(
        OWNER_ID,
        GAME_FEE
    )


    await query.edit_message_text(

        "🎮 نتیجه بازی\n\n"
        f"🏆 برنده: {winner}\n"
        f"💰 جایزه: {prize:,} DOGS\n\n"
        f"👑 کارمزد مالک: {GAME_FEE} DOGS"

    )


    del ACTIVE_GAMES[chat_id]

# =========================
# MAIN
# =========================

def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()



    # start

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # بازی

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern="^join_game$"
        )
    )


    # تایید و رد واریز مالک

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="^(ok_dep_|no_dep_)"
        )
    )


    # دکمه های ربات

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # دستور شارژ مالک

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.User(user_id=OWNER_ID),
            owner_commands
        )
    )


    # پیام های کاربر

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
