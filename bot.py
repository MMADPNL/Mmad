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


# GAME SETTINGS

MIN_GAME = 500
MAX_GAME = 20000


DATA_FILE = "data.json"



# =========================
# DEFAULT DATA
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {},

    "settings": {

        "bot": True

    }

}



# =========================
# LOAD DATA
# =========================

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



# =========================
# SAVE DATA
# =========================

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
        user.get(
            "balance",
            0
        )
    )



def add_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return


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

    return int(uid) == int(
        data.get(
            "owner",
            OWNER_ID
        )
    )



# =========================
# ERROR HANDLER
# =========================

async def error_handler(update, context):

    print("ERROR")

    traceback.print_exc()

# =========================
# DEPOSIT MENU
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
                    callback_data="deposit_ultra"
                ),

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="deposit_exchange"
                )

            ]

        ])

    )



# =========================
# SELECT METHOD
# =========================

async def deposit_method(update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "deposit_ultra":

        context.user_data["deposit_method"] = "اولترا"


    elif query.data == "deposit_exchange":

        context.user_data["deposit_method"] = "صرافی"


    else:

        return


    context.user_data["state"] = "deposit_amount"


    await query.message.reply_text(

        "💰 مقدار DOGS را وارد کنید\n\n"

        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS"

    )



# =========================
# DEPOSIT AMOUNT
# =========================

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

            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."

        )

        return True



    context.user_data["amount"] = amount

    context.user_data["state"] = "deposit_receipt"



    method = context.user_data.get(
        "deposit_method"
    )



    if method == "اولترا":


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



# =========================
# RECEIVE RECEIPT
# =========================

async def deposit_receipt(update, context):

    if context.user_data.get("state") != "deposit_receipt":

        return False


    user = update.effective_user


    amount = context.user_data.get(
        "amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )


    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    else:

        receipt = update.message.text

        rtype = "text"



    req_id = (

        f"DEP_{user.id}_"
        f"{int(time.time())}"

    )



    data["deposits"][req_id] = {

        "id": req_id,

        "user_id": user.id,

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



    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=f"approve_dep_{req_id}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=f"reject_dep_{req_id}"

            )

        ]

    ])



    text = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"💳 روش: {method}\n\n"

        f"کد:\n{req_id}"

    )



    if rtype == "photo":

        await context.bot.send_photo(

            chat_id=data["owner"],

            photo=receipt,

            caption=text,

            reply_markup=buttons

        )

    else:

        await context.bot.send_message(

            chat_id=data["owner"],

            text=text + "\n\n📎 رسید:\n" + receipt,

            reply_markup=buttons

        )


    return True

# =========================
# WITHDRAW
# =========================

async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)

    context.user_data.clear()


    if balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: {balance(user.id):,} DOGS\n"

            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data["state"] = "withdraw_amount"


    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        "مقدار برداشت را وارد کنید:\n\n"

        f"حداقل: {MIN_WITHDRAW:,} DOGS"

    )




async def withdraw_amount(update, context):

    if context.user_data.get("state") != "withdraw_amount":

        return False


    user = update.effective_user


    try:

        amount = int(
            update.message.text.strip()
        )

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



    req_id = (

        f"WD_{user.id}_"
        f"{int(time.time())}"

    )


    data["withdraws"][req_id] = {

        "id": req_id,

        "user_id": user.id,

        "amount": amount,

        "address": address,

        "status": "pending"

    }


    save_data()

    context.user_data.clear()



    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        "⏳ منتظر تایید مالک باشید."

    )



    buttons = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_wd_{req_id}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_wd_{req_id}"
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

            f"📍 آدرس:\n{address}"

        ),

        reply_markup=buttons

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



    action, kind, req_id = query.data.split("_",2)



    # -------- DEPOSIT --------


    if kind == "dep":


        req = data["deposits"].get(req_id)


        if not req:

            return



        if req["status"] != "pending":

            await query.answer(
                "قبلا بررسی شده",
                show_alert=True
            )

            return



        uid = req["user_id"]



        if action == "approve":


            add_balance(
                uid,
                req["amount"]
            )


            req["status"] = "approved"


            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز تایید شد\n\n"

                    f"💰 +{req['amount']:,} DOGS"

                )

            )


            await query.edit_message_text(
                "✅ واریز تایید شد"
            )



        else:


            req["status"] = "rejected"


            await query.edit_message_text(
                "❌ واریز رد شد"
            )




    # -------- WITHDRAW --------


    elif kind == "wd":


        req = data["withdraws"].get(req_id)


        if not req:

            return



        uid = req["user_id"]



        if action == "approve":


            req["status"] = "approved"


            await context.bot.send_message(

                chat_id=uid,

                text="✅ برداشت شما تایید شد."

            )


            await query.edit_message_text(
                "✅ برداشت تایید شد"
            )



        else:


            req["status"] = "rejected"


            add_balance(
                uid,
                req["amount"]
            )


            await context.bot.send_message(

                chat_id=uid,

                text="❌ برداشت رد شد.\n💰 مبلغ برگشت داده شد."

            )


            await query.edit_message_text(

                "❌ برداشت رد شد\n"

                "💰 مبلغ برگشت داده شد"

            )



    save_data()

# =========================
# GAME SYSTEM
# =========================

async def game_command(update, context):

    if update.effective_chat.type == "private":

        return


    user = update.effective_user

    create_user(user)


    text = update.message.text.strip()


    try:

        amount = int(
            text.split()[1]
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

        "id": game_id,

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

        "🎮 بازی ساخته شد\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "منتظر بازیکن دوم هستیم...",

        reply_markup=keyboard

    )




# =========================
# JOIN GAME
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


        game = data["games"].get(
            game_id
        )


        if not game:

            return



        if game["status"] != "waiting":

            await query.answer(
                "این بازی تمام شده",
                show_alert=True
            )

            return



        if user.id == game["owner"]:

            await query.answer(
                "خودت نمی‌توانی وارد شوی",
                show_alert=True
            )

            return



        create_user(user)



        amount = game["amount"]



        if balance(user.id) < amount:

            await query.answer(
                "موجودی کافی نیست",
                show_alert=True
            )

            return



        if not remove_balance(
            game["owner"],
            amount
        ):

            return



        remove_balance(
            user.id,
            amount
        )



        winner = random.choice([

            game["owner"],

            user.id

        ])



        loser = (

            user.id
            if winner == game["owner"]
            else game["owner"]

        )



        prize = int(
            amount * 1.8
        )


        owner_fee = (
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
            owner_fee
        )



        game["status"] = "done"

        game["winner"] = winner

        game["loser"] = loser


        save_data()



        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"👤 بازیکن ۱: {game['owner']}\n"

            f"👤 بازیکن ۲: {user.id}\n\n"

            f"🏆 برنده:\n{winner}\n\n"

            f"❌ بازنده:\n{loser}\n\n"

            f"💰 جایزه: {prize:,} DOGS\n"

            f"👑 سهم مالک: {owner_fee:,} DOGS"

        )



    elif query.data.startswith("cancel_game_"):


        game_id = query.data.replace(
            "cancel_game_",
            ""
        )


        game = data["games"].get(
            game_id
        )


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
# SUPPORT
# =========================

async def support(update, context):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیام خود را ارسال کنید."

    )



# =========================
# TEXT ROUTER
# =========================

async def text_router(update, context):

    if not update.message:

        return


    text = update.message.text.strip()



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



    if text == "🎧 پشتیبانی":

        await support(
            update,
            context
        )

        return



    # واریزی

    if await deposit_amount(
        update,
        context
    ):

        return



    if await deposit_receipt(
        update,
        context
    ):

        return



    # برداشت

    if await withdraw_amount(
        update,
        context
    ):

        return



    if await withdraw_address(
        update,
        context
    ):

        return



    # بازی داخل گپ

    if text.lower().startswith(
        "بازی "
    ):

        await game_command(
            update,
            context
        )

        return




# =========================
# PHOTO HANDLER
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



    # START

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )



    # DEPOSIT BUTTONS

    app.add_handler(
        CallbackQueryHandler(
            deposit_method,
            pattern="^deposit_"
        )
    )



    # APPROVE / REJECT

    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern=r"^(approve|reject)_(dep|wd)_"
        )
    )



    # GAME BUTTONS

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)_"
        )
    )



    # TEXT

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )



    # PHOTO

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )



    # ERROR

    app.add_error_handler(
        error_handler
    )



    print(
        "BOT STARTED"
    )


    app.run_polling()



if __name__ == "__main__":

    main()
