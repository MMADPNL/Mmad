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

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

GROUP_LINK = "https://t.me/TAK_B_ET"

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

    return int(
        user.get("balance",0)
    )



def add_balance(uid,amount):

    user = get_user(uid)

    if user:

        user["balance"] += int(amount)

        save_data()



def remove_balance(uid,amount):

    user = get_user(uid)

    if user and user["balance"] >= amount:

        user["balance"] -= int(amount)

        save_data()

        return True

    return False



def is_owner(uid):

    return int(uid) == int(
        data.get("owner",OWNER_ID)
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

async def start(update,context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"
        f"💰 موجودی:\n"
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

async def referral(query,context):

    uid = query.from_user.id

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start={uid}"
    )


    await query.edit_message_text(

        "👥 زیرمجموعه گیری\n\n"
        f"لینک شما:\n{link}\n\n"
        f"🎁 هر دعوت: {REF_REWARD} DOGS"

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
                        "🟢 اولترا",
                        callback_data="ultra"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏦 صرافی",
                        callback_data="exchange"
                    )
                ]
            ]
        )
    )



# =========================
# DEPOSIT METHODS
# =========================

async def ultra(query,context):

    context.user_data["state"]="deposit"


    await query.edit_message_text(

        "🟢 اولترا\n\n"
        "به آیدی زیر DOGS ارسال کنید:\n\n"
        "@CyyFr\n\n"
        "بعد از ارسال، شات یا پیام تراکنش را بفرستید.\n"
        "توسط مالک بررسی می‌شود."
    )



async def exchange(query,context):

    context.user_data["state"]="deposit"


    await query.edit_message_text(

        "🏦 صرافی\n\n"
        "DOGS را به این ولت ارسال کنید:\n\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از ارسال، شات یا لینک تراکنش را بفرستید.\n"
        "توسط مالک بررسی می‌شود."
        )
    # =========================
# WITHDRAW
# =========================

async def withdraw_menu(query,context):

    context.user_data["state"]="withdraw"


    await query.edit_message_text(

        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "تعداد را وارد کنید."

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
# CALLBACK
# =========================

async def callback_handler(update,context):

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



    elif action == "ref":

        await referral(
            query,
            context
        )



    elif action == "admin":

        if is_owner(user.id):

            await query.edit_message_text(

                "⚙️ پنل مالک\n\n"
                "قسمت مدیریت",

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 آمار",
                                callback_data="stats"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔴 روشن خاموش",
                                callback_data="toggle"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "💬 گپ اجباری",
                                callback_data="setgroup"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📢 چنل اجباری",
                                callback_data="setchannel"
                            )
                        ]
                    ]
                )

            )

        else:

            await query.answer(
                "دسترسی ندارید",
                show_alert=True
            )



    elif action == "stats":

        if is_owner(user.id):

            await query.edit_message_text(

                "📊 آمار\n\n"
                f"👤 کاربران: {len(data['users'])}\n"
                f"🎮 بازی ها: {len(data['games'])}"

            )



    elif action == "toggle":

        if is_owner(user.id):

            data["settings"]["bot"] = not data["settings"]["bot"]

            save_data()

            await query.edit_message_text(     
     "✅ وضعیت ربات تغییر کرد"
)
    # =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update,context):

    user = update.effective_user

    create_user(user)


    text = update.message.text.strip()

    state = context.user_data.get("state")



    # =====================
    # TRANSFER BY REPLY
    # =====================

    if update.message.reply_to_message:

        if text.startswith("انتقال"):

            try:

                amount = int(
                    text.replace(
                        "انتقال",
                        ""
                    ).strip()
                )

            except:

                await update.message.reply_text(
                    "❌ مقدار اشتباه است"
                )
                return



            target = update.message.reply_to_message.from_user

            create_user(target)



            if balance(user.id) < amount:

                await update.message.reply_text(
                    "❌ موجودی کافی نیست"
                )
                return



            if target.id == user.id:

                await update.message.reply_text(
                    "❌ به خودت انتقال نده"
                )
                return



            remove_balance(
                user.id,
                amount
            )


            add_balance(
                target.id,
                amount
            )


            await update.message.reply_text(

                "✅ انتقال انجام شد\n\n"
                f"👤 گیرنده: {target.first_name}\n"
                f"💰 مقدار: {amount:,} DOGS"

            )

            return



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
                f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS"
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
            "✅ درخواست برداشت ارسال شد."
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
                f"👤 کاربر: {user.id}\n\n"
                f"{text}"

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
                f"👤 {user.id}\n\n"
                f"{text}"

            )

        )


        context.user_data.clear()


        await update.message.reply_text(
            "✅ ارسال شد"
        )

        return
# =========================
# GAME SYSTEM
# =========================

GAME_FEE = 100

ACTIVE_GAMES = {}



async def create_game(update, context):

    if not update.message:
        return

    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ انجام می‌شود."
        )
        return


    try:

        amount = int(
            update.message.text.split()[1]
        )

    except:

        await update.message.reply_text(
            "❌ مثال:\nبازی 500"
        )
        return



    if amount <= 0:

        return



    user = update.effective_user


    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )
        return



    if chat_id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ یک بازی در حال انتظار است."
        )
        return



    remove_balance(
        user.id,
        amount
    )


    ACTIVE_GAMES[chat_id] = {

        "creator": user.id,
        "amount": amount,
        "player": None,
        "message": None

    }



    msg = await update.message.reply_text(

        "🎮 بازی آماده شد\n\n"
        f"👤 سازنده: {user.first_name}\n"
        f"💰 مبلغ: {amount} DOGS\n\n"
        "یک نفر برای بازی وارد شود 👇",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎮 بازی با دوستان",
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


    ACTIVE_GAMES[chat_id]["message"] = msg.message_id




async def game_buttons(update,context):

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



    # ورود بازیکن دوم

    if query.data == "join_game":


        if game["creator"] == user.id:

            await query.answer(
                "❌ خودت نمی‌توانی وارد شوی",
                show_alert=True
            )
            return



        if game["player"]:

            await query.answer(
                "❌ بازی پر شده",
                show_alert=True
            )
            return



        game["player"] = user.id



        await query.edit_message_text(

            "🎮 بازی شروع شد\n\n"
            f"👤 نفر اول: {game['creator']}\n"
            f"👤 نفر دوم: {user.id}\n\n"
            "در حال تعیین برنده..."

        )



        # انتخاب برنده ضد باگ

        import random

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


        amount = game["amount"]


        add_balance(
            winner,
            amount + (amount - GAME_FEE)
        )


        add_balance(
            OWNER_ID,
            GAME_FEE
        )


        await context.bot.send_message(

            chat_id=chat_id,

            text=(

                "🏆 نتیجه بازی\n\n"
                f"🥇 برنده: {winner}\n"
                f"💰 جایزه: {amount + amount - GAME_FEE} DOGS\n\n"
                f"👑 کارمزد مالک: {GAME_FEE} DOGS"

            )

        )


        del ACTIVE_GAMES[chat_id]




    # لغو بازی

    elif query.data == "cancel_game":


        if game["creator"] != user.id:

            await query.answer(
                "❌ فقط سازنده می‌تواند لغو کند",
                show_alert=True
            )
            return



        add_balance(
            user.id,
            game["amount"]
        )


        del ACTIVE_GAMES[chat_id]



        await query.edit_message_text(
            "❌ بازی لغو شد\n"
            "💰 مبلغ برگشت داده شد."
        )
        # =========================
# COMMANDS
# =========================

async def game_command(update,context):

    await create_game(
        update,
        context
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
        MessageHandler(
            filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_buttons,
            pattern="^(join_game|cancel_game)$"
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


    app.run_polling(
        drop_pending_updates=True
    )



if __name__ == "__main__":

    main()
