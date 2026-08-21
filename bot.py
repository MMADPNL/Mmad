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
        user.get("balance",0)
    )



def add_balance(uid, amount):

    user = get_user(uid)

    if user:

        user["balance"] = (
            int(user.get("balance",0))
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
        data.get("owner", OWNER_ID)
    )



# =========================
# BUTTONS
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

        buttons.append(

            [

                InlineKeyboardButton(
                    "⚙️ پنل مالک",
                    callback_data="admin"
                )

            ]

        )


    return InlineKeyboardMarkup(buttons)



def admin_keyboard():

    return InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    "🟢 روشن/خاموش ربات",
                    callback_data="admin_toggle"
                )

            ],

            [

                InlineKeyboardButton(
                    "📢 چنل اجباری",
                    callback_data="admin_channel"
                ),

                InlineKeyboardButton(
                    "👥 گپ اجباری",
                    callback_data="admin_group"
                )

            ],

            [

                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_transfer"
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

        create_user(query.from_user)

        user = get_user(uid)



    await query.edit_message_text(

        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {user.get('name','')}\n"
        f"💰 موجودی: {balance(uid):,} DOGS",

        reply_markup=back_button()

    )



# =========================
# GAME INFO
# =========================

async def game_info(query):

    await query.edit_message_text(

        "🎮 بازی دو نفره\n\n"
        "برای ساخت بازی در گپ بنویسید:\n\n"
        "بازی 500\n\n"
        f"💰 حداقل: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر: {MAX_GAME:,} DOGS\n"
        f"👑 کارمزد مالک: {GAME_FEE} DOGS",

        reply_markup=back_button()

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



# =========================
# ULTRA
# =========================

async def ultra(query, context):

    context.user_data["state"] = "deposit"


    await query.edit_message_text(

        "💎 اولترا\n\n"
        "به این آیدی DOGS بزنید:\n\n"
        f"{ULTRA_ID}\n\n"
        "بعد از واریز، شات یا پیام رسید خود را ارسال کنید.\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()

    )



# =========================
# EXCHANGE
# =========================

async def exchange(query, context):

    context.user_data["state"] = "deposit"


    await query.edit_message_text(

        "💎 صرافی\n\n"
        "به این ولت DOGS بزنید:\n\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از واریز، شات یا لینک تراکنش خود را ارسال کنید.\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()

    )



# =========================
# WITHDRAW
# =========================

async def withdraw_menu(query, context):

    context.user_data["state"] = "withdraw"


    await query.edit_message_text(

        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "مقدار برداشت را ارسال کنید.",

        reply_markup=back_button()

    )



# =========================
# SUPPORT
# =========================

async def support(query, context):

    context.user_data["state"] = "support"


    await query.edit_message_text(

        "🎧 پشتیبانی\n\n"
        f"{SUPPORT_USERNAME}\n\n"
        "پیام خود را ارسال کنید.",

        reply_markup=back_button()

    )

# =========================
# CALLBACK HANDLER
# =========================

async def callback_handler(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass


    user = query.from_user

    create_user(user)


    action = query.data



    # خانه

    if action == "home":

        await query.edit_message_text(

            "🤖 منوی اصلی\n\n"
            f"💰 موجودی: {balance(user.id):,} DOGS",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return



    # پروفایل

    if action == "profile":

        await profile(query)

        return



    # واریز

    if action == "deposit":

        await deposit_menu(query)

        return



    # اولترا

    if action == "ultra":

        await ultra(
            query,
            context
        )

        return



    # صرافی

    if action == "exchange":

        await exchange(
            query,
            context
        )

        return



    # برداشت

    if action == "withdraw":

        await withdraw_menu(
            query,
            context
        )

        return



    # پشتیبانی

    if action == "support":

        await support(
            query,
            context
        )

        return



    # اطلاعات بازی

    if action == "game_info":

        await game_info(query)

        return



    # پنل مالک

    if action == "admin":


        if not is_owner(user.id):

            await query.answer(
                "❌ دسترسی ندارید",
                show_alert=True
            )

            return


        settings = data.get(
            "settings",
            {}
        )


        status = (
            "🟢 روشن"
            if settings.get("bot", True)
            else
            "🔴 خاموش"
        )


        await query.edit_message_text(

            "⚙️ پنل مالک\n\n"
            f"🤖 وضعیت: {status}\n\n"
            "یکی را انتخاب کنید:",

            reply_markup=admin_keyboard()

        )

        return

# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    if not update.message:
        return


    user = update.effective_user

    if not user:
        return


    create_user(user)


    text = (
        update.message.text or ""
    ).strip()


    state = context.user_data.get(
        "state"
    )



    # =====================
    # برداشت
    # =====================

    if state == "withdraw":

        try:

            amount = int(text)

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



        if not remove_balance(
            user.id,
            amount
        ):

            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )

            return



        data["withdraws"][str(user.id)] = {

            "user_id": user.id,

            "amount": amount,

            "status": "pending",

            "date": datetime.now().isoformat()

        }


        save_data()


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(

            "✅ درخواست برداشت ثبت شد.\n\n"
            f"💰 مقدار: {amount:,} DOGS\n"
            "⏳ منتظر تایید مالک باشید."

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
    # واریز (متن یا عکس)
    # =====================

    if state == "deposit":


        if update.message.photo:

            receipt = "📸 عکس رسید ارسال شد"

        elif text:

            receipt = text

        else:

            await update.message.reply_text(

                "❌ لطفاً عکس رسید یا لینک تراکنش ارسال کنید."

            )

            return



        data["deposits"][str(user.id)] = {

            "user_id": user.id,

            "receipt": receipt,

            "status": "pending",

            "amount": MIN_DEPOSIT,

            "date": datetime.now().isoformat()

        }


        save_data()


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(

            "✅ رسید دریافت شد.\n\n"
            "⏳ توسط مالک بررسی و تایید می‌شود."

        )



        # ارسال برای مالک

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"👤 نام: {user.first_name}\n\n"
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



        # ارسال خود عکس

        if update.message.photo:

            await context.bot.send_photo(

                chat_id=OWNER_ID,

                photo=update.message.photo[-1].file_id,

                caption=(

                    f"📸 عکس رسید\n"
                    f"👤 کاربر: {user.id}"

                )

            )


        return



    # =====================
    # پشتیبانی
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


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(

            "✅ پیام ارسال شد."

        )


        return

# =========================
# ADMIN DEPOSIT CALLBACK
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
    # تایید واریز
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



        deposit["status"] = "accepted"


        amount = deposit.get(
            "amount",
            MIN_DEPOSIT
        )


        add_balance(
            uid,
            amount
        )


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
                    f"💰 موجودی: {balance(uid):,} DOGS"

                )

            )

        except:

            pass



        return



    # =====================
    # رد واریز
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
# OWNER CHARGE
# =========================

async def owner_commands(update, context):

    user = update.effective_user


    if not is_owner(user.id):

        return



    text = update.message.text.strip()



    if text.startswith("شارژ"):


        parts = text.split()



        if len(parts) != 3:

            await update.message.reply_text(

                "❌ مثال:\n"
                "شارژ آیدی مقدار"

            )

            return



        try:

            uid = int(parts[1])

            amount = int(parts[2])


        except:


            await update.message.reply_text(

                "❌ عدد صحیح وارد کنید."

            )

            return




        if not get_user(uid):

            await update.message.reply_text(

                "❌ کاربر وجود ندارد."

            )

            return




        add_balance(

            uid,

            amount

        )



        await update.message.reply_text(

            "✅ شارژ شد\n\n"
            f"👤 {uid}\n"
            f"💰 {amount:,} DOGS"

        )



        return

# =========================
# GAME SYSTEM
# =========================

ACTIVE_GAMES = {}



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
        f"👤 سازنده: {user.first_name}\n"
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





# =========================
# GAME CALLBACK
# =========================

async def game_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user

    chat_id = query.message.chat.id



    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ بازی تمام شده.",
            show_alert=True
        )

        return



    game = ACTIVE_GAMES[chat_id]



    # لغو بازی

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
            "💰 مبلغ برگشت داده شد."

        )


        return




    # ورود بازی

    if query.data == "join_game":


        if user.id == game["creator"]:

            await query.answer(
                "❌ خودت نمی‌توانی وارد شوی.",
                show_alert=True
            )

            return



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
            f"🏆 برنده: {winner}\n"
            f"💰 جایزه: {prize:,} DOGS\n\n"
            f"👑 کارمزد مالک: {GAME_FEE} DOGS"

        )


        return

# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد")
        return


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
            filters.TEXT & filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )


    # تایید و رد واریز مالک
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )


    # پنل مالک
    app.add_handler(
        CallbackQueryHandler(
            admin_settings_callback,
            pattern=r"^admin_"
        )
    )


    # دکمه های اصلی
    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # دستورهای مالک
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.User(
                user_id=OWNER_ID
            ),
            owner_commands
        )
    )


    # پیام و عکس کاربران
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
            message_handler
        )
    )


    print("✅ BOT STARTED")


    app.run_polling(
        drop_pending_updates=True
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
