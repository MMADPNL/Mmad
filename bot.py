import json
import os
import random
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


# GAME

MIN_GAME = 500
MAX_GAME = 20000
GAME_FEE = 100


DATA_FILE = "bot_data.json"



# =========================
# DATABASE
# =========================

DEFAULT_DATA = {

    "users": {},

    "deposits": {},

    "withdraws": {},

    "owner": OWNER_ID,

    "settings": {

        "bot": True,

        "channel": "",

        "group": ""

    }

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

            data = json.load(f)


        for key in DEFAULT_DATA:

            if key not in data:

                data[key] = DEFAULT_DATA[key]


        return data


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

    return data["users"].get(
        str(uid)
    )



def balance(uid):

    user = get_user(uid)

    if not user:

        return 0


    return int(
        user.get("balance", 0)
    )



def add_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return False


    user["balance"] = (
        int(user.get("balance", 0))
        +
        int(amount)
    )


    save_data()

    return True



def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return False


    if balance(uid) < int(amount):

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

def back_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]
        ]
    )



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
                "🎮 بازی",
                callback_data="game_info"
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



def admin_keyboard():

    return InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    "🟢 روشن / 🔴 خاموش",
                    callback_data="admin_toggle"
                )

            ],

            [

                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats"
                )

            ],

            [

                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )

            ]

        ]

    )

# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user

    if not user:

        return


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


    if not user:

        create_user(
            query.from_user
        )

        user = get_user(uid)



    name = user.get(
        "name",
        ""
    )


    username = user.get(
        "username",
        ""
    )


    await query.edit_message_text(

        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {name}\n"
        f"🔹 یوزرنیم: @{username if username else 'ندارد'}\n\n"
        f"💰 موجودی: {balance(uid):,} DOGS",

        reply_markup=back_button()

    )



# =========================
# GAME INFO
# =========================

async def game_info(query):

    await query.edit_message_text(

        "🎮 بازی دو نفره\n\n"
        "برای ساخت بازی داخل گپ بنویسید:\n\n"
        "بازی 500\n\n"
        f"💰 حداقل: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر: {MAX_GAME:,} DOGS\n"
        f"👑 کارمزد مالک: {GAME_FEE} DOGS",

        reply_markup=back_button()

    )

# =========================
# DEPOSIT SYSTEM
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
                ],
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ]
        )

    )



async def ultra(query, context):

    context.user_data["state"] = "deposit_receipt"


    await query.edit_message_text(

        "💎 اولترا\n\n"
        f"به این آیدی DOGS بزنید:\n"
        f"{ULTRA_ID}\n\n"

        "بعد از واریز:\n"
        "1️⃣ عکس رسید یا لینک تراکنش را ارسال کنید\n"
        "2️⃣ بعد مقدار DOGS را بفرستید\n\n"

        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()

    )



async def exchange(query, context):

    context.user_data["state"] = "deposit_receipt"


    await query.edit_message_text(

        "💎 صرافی\n\n"
        f"ولت DOGS:\n{DOGS_WALLET}\n\n"

        "بعد از واریز:\n"
        "1️⃣ رسید را ارسال کنید\n"
        "2️⃣ مقدار DOGS را وارد کنید\n\n"

        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()

    )

    # =========================
# DEPOSIT RECEIPT HANDLER
# =========================

async def handle_deposit(update, context):

    user = update.effective_user

    state = context.user_data.get(
        "state"
    )


    if state == "deposit_receipt":

        if update.message.photo:

            context.user_data["receipt"] = (
                "📸 عکس رسید ارسال شد"
            )

        elif update.message.text:

            context.user_data["receipt"] = (
                update.message.text
            )

        else:

            await update.message.reply_text(
                "❌ لطفاً عکس یا متن رسید ارسال کنید."
            )

            return


        context.user_data["state"] = "deposit_amount"


        await update.message.reply_text(

            "✅ رسید دریافت شد.\n\n"
            "💰 حالا مقدار DOGS واریزی را ارسال کنید.\n\n"
            f"حداقل: {MIN_DEPOSIT:,} DOGS"

        )


        return



    if state == "deposit_amount":

        try:

            amount = int(
                update.message.text
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



        receipt = context.user_data.get(
            "receipt",
            "بدون رسید"
        )


        data["deposits"][str(user.id)] = {

            "user_id": user.id,

            "amount": amount,

            "receipt": receipt,

            "status": "pending",

            "date": datetime.now().isoformat()

        }


        save_data()



        context.user_data.clear()



        await update.message.reply_text(

            "✅ درخواست واریز ثبت شد.\n\n"
            "⏳ منتظر تایید مالک باشید."

        )



        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"👤 نام: {user.first_name}\n\n"
                f"💰 مقدار: {amount:,} DOGS\n\n"
                f"📝 رسید:\n{receipt}"

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

# =========================
# ADMIN DEPOSIT CHECK
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass


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


        deposit = data["deposits"].get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ واریز پیدا نشد."
            )

            return



        if deposit.get("status") == "accepted":

            await query.edit_message_text(
                "⚠️ قبلاً تایید شده."
            )

            return



        amount = int(
            deposit.get(
                "amount",
                0
            )
        )


        add_balance(
            uid,
            amount
        )


        deposit["status"] = "accepted"


        save_data()



        await query.edit_message_text(

            "✅ واریز تایید شد\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مبلغ: {amount:,} DOGS"

        )



        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز شما تایید شد.\n\n"
                    f"➕ {amount:,} DOGS اضافه شد.\n"
                    f"💰 موجودی جدید:\n"
                    f"{balance(uid):,} DOGS"

                )

            )

        except:

            pass



        return




    # =====================
    # REJECT DEPOSIT
    # =====================

    if action.startswith("no_dep_"):


        uid = int(
            action.split("_")[2]
        )


        deposit = data["deposits"].get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ واریز پیدا نشد."
            )

            return



        deposit["status"] = "rejected"


        save_data()



        await query.edit_message_text(

            "❌ واریز رد شد\n\n"
            f"👤 کاربر: {uid}"

        )



        try:

            await context.bot.send_message(

                chat_id=uid,

                text="❌ واریز شما رد شد."

            )

        except:

            pass



        return

# =========================
# GAME SYSTEM
# =========================

ACTIVE_GAMES = {}



def user_display(uid):

    user = get_user(uid)

    if not user:

        return str(uid)


    if user.get("username"):

        return (
            "@"
            +
            user["username"]
        )


    return user.get(
        "name",
        str(uid)
    )



# =========================
# CREATE GAME
# =========================

async def game_command(update, context):

    user = update.effective_user

    create_user(user)


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
            f"❌ حداقل بازی {MIN_GAME:,} DOGS است."
        )

        return



    if amount > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر بازی {MAX_GAME:,} DOGS است."
        )

        return



    chat_id = update.effective_chat.id


    if chat_id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ یک بازی فعال است."
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


    ACTIVE_GAMES[chat_id] = {

        "creator": user.id,

        "amount": amount

    }



    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"
        f"👤 سازنده: {user_display(user.id)}\n"
        f"💰 شرط: {amount:,} DOGS\n\n"
        "برای ورود دکمه را بزنید.",


        reply_markup=InlineKeyboardMarkup(

            [

                [

                    InlineKeyboardButton(
                        "🎮 ورود به بازی",
                        callback_data="join_game"
                    )

                ],

                [

                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="cancel_game"
                    )

                ]

            ]

        )

        )

id="x7q2lm"
# =========================
# GAME CALLBACK
# =========================

async def game_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass


    user = query.from_user

    chat_id = query.message.chat.id


    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ بازی تمام شده.",
            show_alert=True
        )

        return



    game = ACTIVE_GAMES[chat_id]



    # =====================
    # CANCEL GAME
    # =====================

    if query.data == "cancel_game":


        if user.id != game["creator"]:

            await query.answer(
                "❌ فقط سازنده می‌تواند لغو کند.",
                show_alert=True
            )

            return



        add_balance(
            user.id,
            game["amount"]
        )


        del ACTIVE_GAMES[chat_id]


        await query.edit_message_text(

            "❌ بازی لغو شد.\n\n"
            "💰 مبلغ به سازنده برگشت داده شد."

        )

        return



    # =====================
    # JOIN GAME
    # =====================

    if query.data == "join_game":


        if user.id == game["creator"]:

            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )

            return



        create_user(user)


        amount = game["amount"]


        if balance(user.id) < amount:

            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return



        remove_balance(
            user.id,
            amount
        )



        # انتخاب برنده

        winner = random.choice(

            [

                game["creator"],

                user.id

            ]

        )



        loser = (

            user.id

            if winner == game["creator"]

            else game["creator"]

        )



        prize = (

            amount * 2

        ) - GAME_FEE



        add_balance(
            winner,
            prize
        )


        add_balance(
            OWNER_ID,
            GAME_FEE
        )



        del ACTIVE_GAMES[chat_id]



        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"🏆 برنده: {user_display(winner)}\n"

            f"💰 جایزه: {prize:,} DOGS\n\n"

            f"😢 بازنده: {user_display(loser)}\n\n"

            f"👑 کارمزد مالک: {GAME_FEE:,} DOGS"

        )

        return

# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN پیدا نشد"
        )

        return



    app = Application.builder().token(
        BOT_TOKEN
    ).build()



    # START

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )



    # GAME CREATE

    app.add_handler(
        MessageHandler(

            filters.TEXT
            &
            filters.Regex(
                r"^بازی\s+\d+$"
            ),

            game_command

        )
    )



    # GAME BUTTONS

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )



    # DEPOSIT ACCEPT / REJECT

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )



    # ALL BUTTONS





    # DEPOSIT PHOTO + TEXT + STATES

    app.add_handler(
        MessageHandler(
            (
                filters.TEXT
                |
                filters.PHOTO
            )
            &
            ~filters.COMMAND,

            lambda update, context:
            handle_deposit(update, context)
            if context.user_data.get("state")
            in [
                "deposit_receipt",
                "deposit_amount"
            ]
            else message_handler(update, context)

        )
    )



    # OWNER COMMANDS

    



    print(
        "✅ BOT STARTED"
    )



    app.run_polling(
        drop_pending_updates=True
    )



# =========================
# RUN
# =========================

if __name__ == "__main__":

    main()
