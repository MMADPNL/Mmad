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
    ReplyKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

ULTRA = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

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
    "enabled": True,
    "channel": "",
    "group": "",
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

    except Exception:

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

        print(e)



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
            "balance": 0

        }

        save_data()



def get_balance(uid):

    user = data["users"].get(
        str(uid)
    )

    if not user:
        return 0

    return int(
        user.get("balance",0)
    )



def add_balance(uid, amount):

    if str(uid) in data["users"]:

        data["users"][str(uid)]["balance"] += int(amount)

        save_data()



def remove_balance(uid, amount):

    if get_balance(uid) < amount:

        return False


    data["users"][str(uid)]["balance"] -= int(amount)

    save_data()

    return True



def is_owner(uid):

    return int(uid) == OWNER_ID



# =========================
# KEYBOARD
# =========================

def menu():

    return ReplyKeyboardMarkup(
        [
            ["💳 واریزی","💰 برداشت"],
            ["👤 پروفایل","🎧 پشتیبانی"],
            ["⚙️ پنل مدیریت"]
        ],
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

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=menu()

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
        "💳 واریز DOGS\n\nروش را انتخاب کنید:",
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


async def deposit_select(update, context):

    q = update.callback_query
    await q.answer()

    if q.data == "ultra":
        context.user_data["method"] = "ultra"

    elif q.data == "exchange":
        context.user_data["method"] = "exchange"

    context.user_data["state"] = "dep_amount"

    await q.message.reply_text(
        f"💰 مقدار DOGS را وارد کنید\nحداقل {MIN_DEPOSIT:,}"
    )



async def deposit_amount(update, context):

    if context.user_data.get("state") != "dep_amount":
        return False

    try:
        amount = int(update.message.text)
    except:
        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید"
        )
        return True


    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل {MIN_DEPOSIT:,} DOGS"
        )
        return True


    context.user_data["amount"] = amount
    context.user_data["state"] = "dep_receipt"


    if context.user_data["method"] == "ultra":

        text = (
            "🟣 واریز اولترا\n\n"
            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"
            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"
            f"{ULTRA}\n\n"
            "مثال:\n"
            f"ULTRA {amount} DOGS\n"
            f"{ULTRA}\n\n"
            "پس از ارسال، رسید را در همین چت ارسال کنید.\n\n"
            "📸 شات یا پیام تراکنش را بفرستید.\n\n"
            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"
        )

    else:

        text = (
            "🏦 واریز صرافی\n\n"
            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"
            "ولت:\n\n"
            f"{EXCHANGE_WALLET}\n\n"
            f"مبلغ: {amount:,} DOGS\n\n"
            "پس از ارسال، شات یا لینک هش تراکنش را بفرستید.\n\n"
            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"
        )


    await update.message.reply_text(text)

    return True



async def deposit_receipt(update, context):

    if context.user_data.get("state") != "dep_receipt":
        return False


    user = update.effective_user

    amount = context.user_data.get("amount")


    if update.message.photo:

        receipt = update.message.photo[-1].file_id
        rtype = "photo"

    else:

        receipt = update.message.text
        rtype = "text"



    req = f"DEP_{user.id}_{int(time.time())}"


    data["deposits"][req] = {

        "user": user.id,
        "amount": amount,
        "receipt": receipt,
        "type": rtype,
        "status": "pending"

    }


    save_data()

    context.user_data.clear()


    await update.message.reply_text(
        "✅ رسید ارسال شد\n⏳ منتظر تایید مالک باشید"
    )


    kb = InlineKeyboardMarkup([
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


    await context.bot.send_message(
        OWNER_ID,
        f"💳 واریزی جدید\n\n"
        f"👤 آیدی: {user.id}\n"
        f"💰 مبلغ: {amount:,} DOGS",
        reply_markup=kb
    )


    return True



# =========================
# WITHDRAW
# =========================

async def withdraw_menu(update, context):

    context.user_data.clear()

    context.user_data["state"] = "wd_amount"


    await update.message.reply_text(
        f"💰 مقدار برداشت را وارد کنید\nحداقل {MIN_WITHDRAW:,}"
    )



async def withdraw_amount(update, context):

    if context.user_data.get("state") != "wd_amount":
        return False


    try:
        amount = int(update.message.text)

    except:

        return True



    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ مقدار کم است"
        )
        return True



    if get_balance(update.effective_user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )

        return True



    context.user_data["amount"] = amount

    context.user_data["state"] = "wd_address"


    await update.message.reply_text(
        "📍 آیدی یا ولت دریافت را ارسال کنید"
    )


    return True


# =========================
# WITHDRAW ADDRESS
# =========================

async def withdraw_address(update, context):

    if context.user_data.get("state") != "wd_address":
        return False


    user = update.effective_user

    amount = context.user_data.get("amount")

    address = update.message.text.strip()


    if not remove_balance(user.id, amount):

        return True


    req = f"WD_{user.id}_{int(time.time())}"


    data["withdraws"][req] = {

        "user": user.id,
        "amount": amount,
        "address": address,
        "status": "pending"

    }


    save_data()

    context.user_data.clear()


    await update.message.reply_text(
        "✅ درخواست برداشت ارسال شد\n⏳ منتظر تایید مالک باشید"
    )


    kb = InlineKeyboardMarkup([
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
        OWNER_ID,
        f"💰 برداشت جدید\n\n"
        f"👤 {user.id}\n"
        f"💰 {amount:,} DOGS\n\n"
        f"📍 {address}",
        reply_markup=kb
    )

    return True



# =========================
# APPROVE REJECT
# =========================

async def approve_reject(update, context):

    q = update.callback_query

    await q.answer()


    if not is_owner(q.from_user.id):
        return


    action, kind, req = q.data.split("_",2)



    if kind == "dep":

        item = data["deposits"].get(req)

        if not item:
            return


        if action == "approve":

            add_balance(
                item["user"],
                item["amount"]
            )

            item["status"]="approved"


            await context.bot.send_message(
                item["user"],
                "✅ واریز تایید شد"
            )

            await q.edit_message_text(
                "✅ واریز تایید شد"
            )


        else:

            item["status"]="rejected"

            await context.bot.send_message(
                item["user"],
                "❌ واریز رد شد"
            )

            await q.edit_message_text(
                "❌ واریز رد شد"
            )



    if kind == "wd":

        item=data["withdraws"].get(req)

        if not item:
            return


        if action=="approve":

            item["status"]="approved"

            await context.bot.send_message(
                item["user"],
                "✅ برداشت تایید شد"
            )

            await q.edit_message_text(
                "✅ برداشت تایید شد"
            )


        else:

            item["status"]="rejected"

            add_balance(
                item["user"],
                item["amount"]
            )

            await context.bot.send_message(
                item["user"],
                "❌ برداشت رد شد\n💰 مبلغ برگشت داده شد"
            )

            await q.edit_message_text(
                "❌ برداشت رد شد"
            )


    save_data()



# =========================
# PROFILE / SUPPORT
# =========================

async def profile(update, context):

    user=update.effective_user

    create_user(user)


    await update.message.reply_text(
        f"👤 آیدی: {user.id}\n"
        f"💰 موجودی: {get_balance(user.id):,}"
    )



async def support(update, context):

    context.user_data["state"]="support"

    await update.message.reply_text(
        "🎧 پیامت رو ارسال کن"
    )



async def support_msg(update, context):

    if context.user_data.get("state")!="support":
        return False


    await context.bot.send_message(
        OWNER_ID,
        f"🎧 پشتیبانی\n\n"
        f"{update.effective_user.id}\n\n"
        f"{update.message.text}"
    )


    context.user_data.clear()

    await update.message.reply_text(
        "✅ ارسال شد"
    )

    return True



# =========================
# GAME
# =========================

async def game_command(update,context):

    try:
        amount=int(update.message.text.split()[1])
    except:
        return


    if amount<MIN_GAME or amount>MAX_GAME:
        return


    user=update.effective_user

    create_user(user)


    if get_balance(user.id)<amount:
        return


    gid=str(int(time.time()))


    data["games"][gid]={
        "owner":user.id,
        "amount":amount,
        "status":"wait"
    }


    save_data()


    await update.message.reply_text(
        f"🎮 بازی {amount:,} DOGS\n\n"
        "یک نفر وارد شود",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "👥 ورود",
                    callback_data=f"join_{gid}"
                )
            ]
        ])
    )



# =========================
# TEXT ROUTER
# =========================

async def text_router(update,context):

    t=update.message.text


    if t=="💳 واریزی":
        return await deposit_menu(update,context)

    if t=="💰 برداشت":
        return await withdraw_menu(update,context)

    if t=="👤 پروفایل":
        return await profile(update,context)

    if t=="🎧 پشتیبانی":
        return await support(update,context)


    if await support_msg(update,context):
        return

    if await deposit_amount(update,context):
        return

    if await deposit_receipt(update,context):
        return

    if await withdraw_amount(update,context):
        return

    if await withdraw_address(update,context):
        return

    if t.startswith("بازی "):
        return await game_command(update,context)



# =========================
# MAIN
# =========================

def main():

    app=Application.builder().token(
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
            deposit_select,
            pattern="^(ultra|exchange)$"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern="^(approve|reject)_(dep|wd)_"
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )


    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            deposit_receipt
        )
    )


    app.add_error_handler(
        error_handler
    )


    print("BOT STARTED")

    app.run_polling()



if __name__=="__main__":
    main()
