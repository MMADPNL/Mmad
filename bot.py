import os
import json
import time
import random
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

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "data.json"



# =========================
# DATA
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {}

}



def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

    except:

        pass


    return DEFAULT_DATA.copy()



data = load_data()



def save_data():

    try:

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

            "date": datetime.now().isoformat()

        }

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

    if user:

        user["balance"] += int(amount)

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

    return int(uid) == int(OWNER_ID)



# =========================
# KEYBOARD
# =========================

def main_keyboard(uid):

    buttons = [

        [
            "💳 واریزی",
            "💰 برداشت"
        ],

        [
            "👤 پروفایل",
            "🎧 پشتیبانی"
        ]

    ]


    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )



# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی: {balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )

    )



# =========================
# ERROR
# =========================

async def error_handler(update, context):

    print("ERROR")

    traceback.print_exc()

# =========================
# DEPOSIT
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
                    callback_data="dep_ultra"
                ),

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="dep_exchange"
                )

            ]

        ])

    )



async def deposit_button(update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "dep_ultra":

        context.user_data["method"] = "ultra"


    elif query.data == "dep_exchange":

        context.user_data["method"] = "exchange"


    else:

        return



    context.user_data["state"] = "deposit_amount"



    await query.message.reply_text(

        "💰 مقدار DOGS را وارد کنید\n\n"

        f"حداقل: {MIN_DEPOSIT:,} DOGS"

    )




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

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."

        )

        return True



    context.user_data["amount"] = amount

    context.user_data["state"] = "deposit_receipt"



    if context.user_data["method"] == "ultra":


        await update.message.reply_text(

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"

            f"{ULTRA_ADDRESS}\n\n"

            "مثال:\n"

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



    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    elif update.message.text:

        receipt = update.message.text

        rtype = "text"


    else:

        return True




    req = (

        f"DEP_{user.id}_"
        f"{int(time.time())}"

    )



    data["deposits"][req] = {

        "user": user.id,

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
        "⏳ منتظر تایید مالک باشید."

    )



    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_dep_{req}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_dep_{req}"
            )

        ]

    ])



    text = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method}\n\n"

        f"🆔 {req}"

    )



    if rtype == "photo":

        await context.bot.send_photo(

            chat_id=OWNER_ID,

            photo=receipt,

            caption=text,

            reply_markup=keyboard

        )

    else:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=text+"\n\n📎 رسید:\n"+receipt,

            reply_markup=keyboard

        )


    return True

# =========================
# WITHDRAW
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()


    context.user_data["state"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مقدار برداشت را وارد کنید:\n\n"

        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

    )




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

        "📍 آیدی یا ولت دریافت DOGS را ارسال کنید."

    )


    return True




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

        return True



    req = (

        f"WD_{user.id}_"
        f"{int(time.time())}"

    )


    data["withdraws"][req] = {

        "user": user.id,

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



    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_wd_{req}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_wd_{req}"
            )

        ]

    ])



    await context.bot.send_message(

        chat_id=OWNER_ID,

        text=(

            "💰 برداشت جدید\n\n"

            f"👤 آیدی کاربر: {user.id}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"📍 آدرس:\n{address}"

        ),

        reply_markup=keyboard

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



    action, kind, req = query.data.split("_",2)



    if kind == "dep":


        item = data["deposits"].get(req)


        if not item:
            return


        if item["status"] != "pending":

            await query.answer(
                "قبلا بررسی شده",
                show_alert=True
            )

            return



        if action == "approve":

            add_balance(
                item["user"],
                item["amount"]
            )

            item["status"] = "approved"


            await context.bot.send_message(

                item["user"],

                "✅ واریز شما تایید شد."

            )


            await query.edit_message_text(
                "✅ واریز تایید شد"
            )



        else:

            item["status"] = "rejected"


            await context.bot.send_message(

                item["user"],

                "❌ واریز رد شد."

            )


            await query.edit_message_text(
                "❌ واریز رد شد"
            )



    elif kind == "wd":


        item = data["withdraws"].get(req)


        if not item:
            return



        if action == "approve":


            item["status"] = "approved"


            await context.bot.send_message(

                item["user"],

                "✅ برداشت شما تایید شد."

            )


            await query.edit_message_text(
                "✅ برداشت تایید شد"
            )



        else:


            item["status"] = "rejected"


            add_balance(
                item["user"],
                item["amount"]
            )


            await context.bot.send_message(

                item["user"],

                "❌ برداشت رد شد.\n💰 مبلغ برگشت داده شد."

            )


            await query.edit_message_text(

                "❌ برداشت رد شد\n"

                "💰 مبلغ برگشت داده شد"

            )



    save_data()




# =========================
# SUPPORT
# =========================

async def support(update, context):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیامت رو ارسال کن."

    )


    context.user_data["state"] = "support"




async def support_message(update, context):

    if context.user_data.get("state") != "support":

        return False


    user = update.effective_user


    await context.bot.send_message(

        OWNER_ID,

        "🎧 پیام پشتیبانی\n\n"

        f"👤 {user.id}\n\n"

        f"{update.message.text}"

    )


    context.user_data.clear()


    await update.message.reply_text(

        "✅ پیام ارسال شد."

    )


    return True

# =========================
# GAME SYSTEM
# =========================

async def game_command(update, context):

    if update.effective_chat.type == "private":
        return


    user = update.effective_user

    create_user(user)


    try:

        amount = int(
            update.message.text.split()[1]
        )

    except:

        return



    if amount < MIN_GAME or amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ مبلغ بازی باید بین "
            f"{MIN_GAME:,} تا {MAX_GAME:,} DOGS باشد."

        )

        return



    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return



    game_id = str(
        int(time.time())
    )


    data["games"][game_id] = {

        "owner": user.id,

        "amount": amount,

        "chat": update.effective_chat.id,

        "status": "waiting"

    }


    save_data()



    keyboard = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "👥 بازی با دوستان",

                callback_data=f"join_game_{game_id}"

            )

        ],

        [

            InlineKeyboardButton(

                "❌ لغو",

                callback_data=f"cancel_game_{game_id}"

            )

        ]

    ])



    await update.message.reply_text(

        "🎮 بازی جدید\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "یک نفر برای بازی وارد شود.",

        reply_markup=keyboard

    )





# =========================
# GAME BUTTONS
# =========================

async def game_callback(update, context):

    query = update.callback_query

    await query.answer()


    user = query.from_user



    if query.data.startswith("join_game_"):


        game_id = query.data.replace(
            "join_game_",
            ""
        )


        game = data["games"].get(game_id)


        if not game:

            return



        if game["status"] != "waiting":

            return



        if user.id == game["owner"]:

            await query.answer(

                "خودت نمی‌توانی وارد شوی",

                show_alert=True

            )

            return



        amount = game["amount"]



        if balance(user.id) < amount:

            await query.answer(

                "موجودی کافی نیست",

                show_alert=True

            )

            return



        # کم کردن شرط دو نفر

        remove_balance(

            game["owner"],

            amount

        )


        remove_balance(

            user.id,

            amount

        )



        # انتخاب برنده

        winner = random.choice([

            game["owner"],

            user.id

        ])


        loser = (

            user.id

            if winner == game["owner"]

            else game["owner"]

        )



        # 90 درصد جایزه

        prize = int(

            amount * 1.8

        )


        owner_profit = (

            amount * 2

            -

            prize

        )



        add_balance(

            winner,

            prize

        )


        add_balance(

            OWNER_ID,

            owner_profit

        )



        game["status"] = "done"

        game["winner"] = winner

        game["loser"] = loser


        save_data()



        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"👤 بازیکن اول: {game['owner']}\n"

            f"👤 بازیکن دوم: {user.id}\n\n"

            f"🏆 برنده:\n{winner}\n\n"

            f"❌ بازنده:\n{loser}\n\n"

            f"💰 جایزه برنده: {prize:,} DOGS\n"

            f"👑 سهم مالک: {owner_profit:,} DOGS"

        )




    elif query.data.startswith("cancel_game_"):


        game_id = query.data.replace(

            "cancel_game_",

            ""

        )


        game = data["games"].get(game_id)



        if game and game["owner"] == user.id:


            game["status"] = "cancel"

            save_data()



            await query.edit_message_text(

                "❌ بازی لغو شد."

                               )

# =========================
# PROFILE
# =========================

async def profile(update, context):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"💰 موجودی: {balance(user.id):,} DOGS"

    )



# =========================
# TEXT ROUTER
# =========================

async def text_router(update, context):

    if not update.message:

        return


    text = update.message.text.strip()



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



    # پشتیبانی

    if await support_message(update, context):

        return



    # واریزی

    if await deposit_amount(update, context):

        return



    if await deposit_receipt(update, context):

        return



    # برداشت

    if await withdraw_amount(update, context):

        return



    if await withdraw_address(update, context):

        return



    # بازی گروه

    if text.startswith("بازی "):

        await game_command(update, context)

        return





# =========================
# PHOTO
# =========================

async def photo_router(update, context):

    await deposit_receipt(
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



    # start

    app.add_handler(

        CommandHandler(
            "start",
            start
        )

    )



    # deposit buttons

    app.add_handler(

        CallbackQueryHandler(

            deposit_button,

            pattern="^dep_"

        )

    )



    # approve reject

    app.add_handler(

        CallbackQueryHandler(

            approve_reject,

            pattern="^(approve|reject)_(dep|wd)_"

        )

    )



    # game buttons

    app.add_handler(

        CallbackQueryHandler(

            game_callback,

            pattern="^(join_game|cancel_game)_"

        )

    )



    # text

    app.add_handler(

        MessageHandler(

            filters.TEXT & ~filters.COMMAND,

            text_router

        )

    )



    # photo

    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_router

        )

    )



    app.add_error_handler(
        error_handler
    )



    print(
        "BOT STARTED"
    )



    app.run_polling()




if __name__ == "__main__":

    main()
