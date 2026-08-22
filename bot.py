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
    KeyboardButton
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


# عضویت اجباری
FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_BE_T"


# آدرس ها
ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"


# محدودیت ها
MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000


# بازی
MIN_GAME = 500
MAX_GAME = 20000


DATA_FILE = "data.json"



# =========================
# DEFAULT DATA
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "ref_reward": 50,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {},

}




# =========================
# LOAD / SAVE
# =========================


def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

                for k,v in DEFAULT_DATA.items():

                    if k not in data:

                        data[k] = v

                return data

    except:

        traceback.print_exc()


    return DEFAULT_DATA.copy()



data = load_data()




def save_data():

    try:

        tmp = DATA_FILE + ".tmp"

        with open(
            tmp,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )


        os.replace(tmp, DATA_FILE)


    except:

        traceback.print_exc()



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

            "phone": "",

            "refs": 0,

            "ref_by": None,

            "date": datetime.now().isoformat()

        }


    else:

        data["users"][uid]["name"] = user.first_name or ""

        data["users"][uid]["username"] = user.username or ""


    save_data()





def get_balance(uid):

    try:

        return int(
            data["users"]
            [str(uid)]
            .get("balance",0)
        )

    except:

        return 0




def add_balance(uid, amount):

    uid = str(uid)

    if uid not in data["users"]:

        return False


    balance = get_balance(uid) + int(amount)


    if balance < 0:

        balance = 0


    data["users"][uid]["balance"] = balance

    save_data()

    return True




def remove_balance(uid, amount):

    uid = str(uid)

    amount = int(amount)


    if get_balance(uid) < amount:

        return False


    data["users"][uid]["balance"] -= amount

    save_data()

    return True




def is_owner(uid):

    return int(uid) == int(
        data.get("owner",OWNER_ID)
)


# =========================
# KEYBOARDS
# =========================


def main_keyboard(uid):

    rows = [

        ["💳 واریزی", "💰 برداشت"],

        ["👤 پروفایل", "🎧 پشتیبانی"],

        ["👥 انتقال", "👥 زیرمجموعه"],

    ]


    if is_owner(uid):

        rows.append(
            ["⚙️ پنل مدیریت"]
        )


    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )





def join_keyboard():

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "📢 کانال",
                url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}"
            )

        ],

        [

            InlineKeyboardButton(
                "👥 گپ",
                url=f"https://t.me/{FORCE_GROUP.replace('@','')}"
            )

        ],

        [

            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="check_join"
            )

        ]

    ])





def phone_keyboard():

    return ReplyKeyboardMarkup(

        [

            [

                KeyboardButton(
                    "📱 تایید شماره",
                    request_contact=True
                )

            ]

        ],

        resize_keyboard=True,

        one_time_keyboard=True

    )





# =========================
# FORCE JOIN
# =========================


async def check_join(user_id, context):

    try:

        for chat in [
            FORCE_CHANNEL,
            FORCE_GROUP
        ]:

            member = await context.bot.get_chat_member(
                chat_id=chat,
                user_id=user_id
            )


            if member.status in [
                "left",
                "kicked"
            ]:

                return False


        return True


    except:

        return False





# =========================
# START
# =========================


async def start(update, context):

    user = update.effective_user


    create_user(user)



    ok = await check_join(
        user.id,
        context
    )


    if not ok:


        await update.message.reply_text(

            "❌ برای ورود به ربات اول عضو شوید:\n\n"

            "بعد از عضویت روی بررسی بزنید.",

            reply_markup=join_keyboard()

        )

        return




    if not data["users"][str(user.id)].get("phone"):


        await update.message.reply_text(

            "📱 برای ورود شماره تلگرام خود را تایید کنید.\n\n"

            "فقط شماره +98 قبول می‌شود.",

            reply_markup=phone_keyboard()

        )

        return




    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)

    )







# =========================
# CHECK JOIN BUTTON
# =========================


async def check_join_callback(update, context):

    q = update.callback_query

    await q.answer()


    ok = await check_join(
        q.from_user.id,
        context
    )


    if not ok:


        await q.answer(

            "❌ هنوز عضو نشده‌اید.",

            show_alert=True

        )

        return




    await q.message.reply_text(

        "✅ عضویت تایید شد.\n\n"

        "حالا شماره خود را ارسال کنید.",

        reply_markup=phone_keyboard()

    )






# =========================
# PHONE VERIFY
# =========================


async def phone_contact(update, context):

    user = update.effective_user


    if not update.message.contact:

        return



    contact = update.message.contact


    if contact.user_id != user.id:

        await update.message.reply_text(

            "❌ فقط شماره خودتان را ارسال کنید."

        )

        return




    phone = contact.phone_number



    if not phone.startswith("+98"):


        await update.message.reply_text(

            "❌ فقط شماره +98 قبول است."

        )

        return





    create_user(user)



    data["users"][str(user.id)]["phone"] = phone


    save_data()




    await update.message.reply_text(

        "✅ شماره تایید شد.\n\n"

        "خوش آمدید.",

        reply_markup=main_keyboard(user.id)

        )


# =========================
# DEPOSIT
# =========================


async def deposit_menu(update, context):

    context.user_data.clear()


    await update.message.reply_text(

        "💳 روش واریز را انتخاب کنید:",

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





async def deposit_select(update, context):

    q = update.callback_query

    await q.answer()


    if q.data == "dep_ultra":

        context.user_data["dep_method"] = "ultra"


    elif q.data == "dep_exchange":

        context.user_data["dep_method"] = "exchange"


    else:

        return



    context.user_data["dep_state"] = "amount"



    await q.message.reply_text(

        "💰 مقدار DOGS را وارد کنید.\n\n"

        f"حداقل: {MIN_DEPOSIT:,} DOGS"

    )






async def deposit_amount(update, context):

    if context.user_data.get("dep_state") != "amount":

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




    method = context.user_data.get(
        "dep_method"
    )



    context.user_data["dep_amount"] = amount

    context.user_data["dep_state"] = "receipt"



    if method == "ultra":


        text = (

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "فرصت مثال واریز:\n\n"

            f"ULTRA {amount} DOGS {ULTRA_ADDRESS}\n\n"

            f"به این آیدی ارسال کنید:\n{ULTRA_ADDRESS}\n\n"

            "بعد از واریز شات یا پیام تراکنش را ارسال کنید."

        )


    else:


        text = (

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "به این ولت ارسال کنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            "بعد از واریز شات یا لینک هش ارسال کنید."

        )



    await update.message.reply_text(text)


    return True







async def deposit_receipt(update, context):

    if context.user_data.get("dep_state") != "receipt":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "dep_amount"
    )



    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    else:

        receipt = update.message.text

        rtype = "text"





    req = f"DEP_{user.id}_{time.time_ns()}"



    data["deposits"][req] = {


        "id": req,

        "user": user.id,

        "amount": amount,

        "receipt": receipt,

        "type": rtype,

        "status": "pending"


    }



    save_data()



    context.user_data.clear()



    await update.message.reply_text(

        "✅ رسید ثبت شد.\n\n"

        "⏳ منتظر تایید مالک باشید."

    )




    kb = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=f"dep_ok:{req}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=f"dep_no:{req}"

            )

        ]

    ])




    msg = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"🆔 {req}"

    )



    if rtype == "photo":


        await context.bot.send_photo(

            OWNER_ID,

            receipt,

            caption=msg,

            reply_markup=kb

        )


    else:


        await context.bot.send_message(

            OWNER_ID,

            msg + "\n\n" + receipt,

            reply_markup=kb

        )



    return True







# =========================
# DEPOSIT ADMIN
# =========================


async def deposit_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        await q.answer(

            "⛔ فقط مالک",

            show_alert=True

        )

        return




    action, req = q.data.split(":",1)



    dep = data["deposits"].get(req)



    if not dep:

        return




    if dep["status"] != "pending":


        await q.answer(

            "این درخواست قبلا بررسی شده.",

            show_alert=True

        )

        return





    uid = dep["user"]




    if action == "dep_ok":


        add_balance(

            uid,

            dep["amount"]

        )


        dep["status"] = "approved"

        save_data()



        await q.edit_message_text(

            "✅ واریز تایید شد."

        )



        await context.bot.send_message(

            uid,

            f"✅ واریز تایید شد\n\n"

            f"💰 +{dep['amount']:,} DOGS"

        )




    else:


        dep["status"] = "rejected"

        save_data()



        await q.edit_message_text(

            "❌ واریز رد شد."

        )



        await context.bot.send_message(

            uid,

            "❌ واریز شما رد شد."

    )# =========================
# DEPOSIT
# =========================


async def deposit_menu(update, context):

    context.user_data.clear()


    await update.message.reply_text(

        "💳 روش واریز را انتخاب کنید:",

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





async def deposit_select(update, context):

    q = update.callback_query

    await q.answer()


    if q.data == "dep_ultra":

        context.user_data["dep_method"] = "ultra"


    elif q.data == "dep_exchange":

        context.user_data["dep_method"] = "exchange"


    else:

        return



    context.user_data["dep_state"] = "amount"



    await q.message.reply_text(

        "💰 مقدار DOGS را وارد کنید.\n\n"

        f"حداقل: {MIN_DEPOSIT:,} DOGS"

    )






async def deposit_amount(update, context):

    if context.user_data.get("dep_state") != "amount":

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




    method = context.user_data.get(
        "dep_method"
    )



    context.user_data["dep_amount"] = amount

    context.user_data["dep_state"] = "receipt"



    if method == "ultra":


        text = (

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "فرصت مثال واریز:\n\n"

            f"ULTRA {amount} DOGS {ULTRA_ADDRESS}\n\n"

            f"به این آیدی ارسال کنید:\n{ULTRA_ADDRESS}\n\n"

            "بعد از واریز شات یا پیام تراکنش را ارسال کنید."

        )


    else:


        text = (

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "به این ولت ارسال کنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            "بعد از واریز شات یا لینک هش ارسال کنید."

        )



    await update.message.reply_text(text)


    return True







async def deposit_receipt(update, context):

    if context.user_data.get("dep_state") != "receipt":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "dep_amount"
    )



    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    else:

        receipt = update.message.text

        rtype = "text"





    req = f"DEP_{user.id}_{time.time_ns()}"



    data["deposits"][req] = {


        "id": req,

        "user": user.id,

        "amount": amount,

        "receipt": receipt,

        "type": rtype,

        "status": "pending"


    }



    save_data()



    context.user_data.clear()



    await update.message.reply_text(

        "✅ رسید ثبت شد.\n\n"

        "⏳ منتظر تایید مالک باشید."

    )




    kb = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=f"dep_ok:{req}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=f"dep_no:{req}"

            )

        ]

    ])




    msg = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"🆔 {req}"

    )



    if rtype == "photo":


        await context.bot.send_photo(

            OWNER_ID,

            receipt,

            caption=msg,

            reply_markup=kb

        )


    else:


        await context.bot.send_message(

            OWNER_ID,

            msg + "\n\n" + receipt,

            reply_markup=kb

        )



    return True







# =========================
# DEPOSIT ADMIN
# =========================


async def deposit_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        await q.answer(

            "⛔ فقط مالک",

            show_alert=True

        )

        return




    action, req = q.data.split(":",1)



    dep = data["deposits"].get(req)



    if not dep:

        return




    if dep["status"] != "pending":


        await q.answer(

            "این درخواست قبلا بررسی شده.",

            show_alert=True

        )

        return





    uid = dep["user"]




    if action == "dep_ok":


        add_balance(

            uid,

            dep["amount"]

        )


        dep["status"] = "approved"

        save_data()



        await q.edit_message_text(

            "✅ واریز تایید شد."

        )



        await context.bot.send_message(

            uid,

            f"✅ واریز تایید شد\n\n"

            f"💰 +{dep['amount']:,} DOGS"

        )




    else:


        dep["status"] = "rejected"

        save_data()



        await q.edit_message_text(

            "❌ واریز رد شد."

        )



        await context.bot.send_message(

            uid,

            "❌ واریز شما رد شد."

        )


# =========================
# WITHDRAW
# =========================


async def withdraw_menu(update, context):

    user = update.effective_user

    create_user(user)


    if get_balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: {get_balance(user.id):,} DOGS\n"

            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data.clear()

    context.user_data["wd_state"] = "amount"



    await update.message.reply_text(

        f"💰 مبلغ برداشت را وارد کنید.\n\n"

        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

    )






async def withdraw_amount(update, context):

    if context.user_data.get("wd_state") != "amount":

        return False



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




    if get_balance(update.effective_user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return True




    context.user_data["wd_amount"] = amount

    context.user_data["wd_state"] = "address"



    await update.message.reply_text(

        "📍 آدرس ولت یا آیدی دریافت را ارسال کنید."

    )

    return True







async def withdraw_address(update, context):

    if context.user_data.get("wd_state") != "address":

        return False



    user = update.effective_user

    amount = context.user_data.get("wd_amount")

    address = update.message.text.strip()



    if not address or not amount:

        return True




    # رزرو موجودی

    if not remove_balance(user.id, amount):

        await update.message.reply_text(

            "❌ خطا در موجودی."

        )

        return True





    req = f"WD_{user.id}_{time.time_ns()}"



    data["withdraws"][req] = {

        "id": req,

        "user": user.id,

        "amount": amount,

        "address": address,

        "status": "pending"

    }


    save_data()



    context.user_data.clear()



    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        "⏳ منتظر تایید مالک باشید."

    )




    kb = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=f"wd_ok:{req}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=f"wd_no:{req}"

            )

        ]

    ])




    await context.bot.send_message(

        OWNER_ID,

        "💰 برداشت جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📍 آدرس:\n{address}\n\n"

        f"🆔 {req}",

        reply_markup=kb

    )



    return True







# =========================
# WITHDRAW ADMIN
# =========================


async def withdraw_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return




    action, req = q.data.split(":",1)



    wd = data["withdraws"].get(req)



    if not wd:

        return



    if wd["status"] != "pending":

        await q.answer(

            "قبلا بررسی شده",

            show_alert=True

        )

        return




    uid = wd["user"]




    if action == "wd_ok":


        wd["status"] = "approved"

        save_data()



        await q.edit_message_text(

            "✅ برداشت تایید شد."

        )



        await context.bot.send_message(

            uid,

            "✅ برداشت شما تایید شد."

        )




    else:


        wd["status"] = "rejected"


        add_balance(

            uid,

            wd["amount"]

        )


        save_data()



        await q.edit_message_text(

            "❌ برداشت رد شد و موجودی برگشت."

        )



        await context.bot.send_message(

            uid,

            f"❌ برداشت رد شد\n\n"

            f"💰 +{wd['amount']:,} DOGS برگشت داده شد."

        )







# =========================
# TRANSFER
# =========================


async def transfer(update, context):

    user = update.effective_user


    parts = update.message.text.split()



    if len(parts) != 2:


        await update.message.reply_text(

            "❌ روی پیام کاربر ریپلای کن و بنویس:\n"

            "انتقال 500"

        )

        return




    try:

        amount = int(parts[1])

    except:


        await update.message.reply_text(

            "❌ مبلغ اشتباه است."

        )

        return





    if not update.message.reply_to_message:


        await update.message.reply_text(

            "❌ باید روی پیام گیرنده ریپلای شود."

        )

        return




    target = update.message.reply_to_message.from_user




    if target.is_bot or target.id == user.id:

        await update.message.reply_text(

            "❌ انتقال امکان ندارد."

        )

        return





    create_user(target)



    if get_balance(user.id) < amount:


        await update.message.reply_text(

            "❌ موجودی کافی نیست."

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

        "✅ انتقال انجام شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS"

    )


# =========================
# SUPPORT
# =========================


async def support(update, context):

    context.user_data.clear()

    context.user_data["support"] = True


    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیام خود را ارسال کنید."

    )






async def support_message(update, context):

    if not context.user_data.get("support"):

        return False



    user = update.effective_user


    await context.bot.send_message(

        OWNER_ID,

        "🎧 پیام پشتیبانی جدید\n\n"

        f"👤 نام: {user.first_name}\n"

        f"🆔 آیدی: {user.id}\n"

        f"💬 پیام:\n{update.message.text}"

    )



    context.user_data.clear()



    await update.message.reply_text(

        "✅ پیام شما برای مالک ارسال شد."

    )


    return True







# =========================
# REFERRAL
# =========================


async def referral(update, context):

    user = update.effective_user


    create_user(user)



    bot = await context.bot.get_me()



    link = (

        f"https://t.me/{bot.username}"

        f"?start={user.id}"

    )



    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"💰 پاداش هر زیرمجموعه: "

        f"{data.get('ref_reward',50)} DOGS\n\n"

        f"👥 تعداد زیرمجموعه‌ها: "

        f"{data['users'][str(user.id)]['refs']}"

    )








async def check_referral(user):

    uid = str(user.id)


    if uid not in data["users"]:

        return



    ref = data["users"][uid].get(
        "ref_by"
    )



    if ref:

        return




    # اینجا فقط برای start با کد دعوت استفاده می‌شود


# =========================
# ADMIN PANEL
# =========================

async def admin_panel(update, context):

    if not is_owner(update.effective_user.id):
        return


    await update.message.reply_text(

        "⚙️ پنل مدیریت",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    "💰 تغییر جایزه زیرمجموعه",
                    callback_data="admin_ref"
                )
            ]

        ])

    )





async def admin_callback(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return



    if q.data == "admin_stats":

        total_balance = 0


        for u in data["users"].values():

            total_balance += int(
                u.get("balance",0)
            )



        await q.message.reply_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {len(data['users'])}\n"

            f"💰 مجموع موجودی: {total_balance:,} DOGS\n"

            f"💳 واریزی‌ها: {len(data['deposits'])}\n"

            f"💸 برداشت‌ها: {len(data['withdraws'])}\n"

            f"🎮 بازی‌ها: {len(data['games'])}"

        )



    elif q.data == "admin_ref":

        context.user_data["admin_ref"] = True


        await q.message.reply_text(

            "💰 مقدار جدید جایزه زیرمجموعه را ارسال کنید.\n\n"

            "مثال:\n50"

        )








async def admin_text(update, context):

    if not is_owner(update.effective_user.id):

        return False



    if context.user_data.get("admin_ref"):


        try:

            amount = int(
                update.message.text
            )


        except:


            await update.message.reply_text(

                "❌ فقط عدد ارسال کنید."

            )

            return True




        data["ref_reward"] = amount

        save_data()



        context.user_data.clear()



        await update.message.reply_text(

            f"✅ جایزه زیرمجموعه تغییر کرد.\n\n"

            f"💰 مقدار جدید: {amount} DOGS"

        )


        return True



    return False







# =========================
# GAME
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


        await update.message.reply_text(

            "❌ مثال:\nبازی 500"

        )

        return




    if amount < MIN_GAME or amount > MAX_GAME:

        await update.message.reply_text(

            "❌ مبلغ بازی اشتباه است."

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



    enemy = random.randint(
        1,
        100
    )

    player = random.randint(
        1,
        100
    )



    if player > enemy:


        add_balance(
            user.id,
            900
        )


        add_balance(
            OWNER_ID,
            100
        )


        result = "🏆 بردی"



        try:

            await context.bot.send_message(

                user.id,

                "🏆 تبریک!\n\n"

                "🎮 بازی را بردی\n"

                "💰 +900 DOGS"

            )


        except:

            pass



    else:


        result = "❌ باختی"



        try:

            await context.bot.send_message(

                user.id,

                f"❌ بازی را باختی\n\n"

                f"💸 -{amount:,} DOGS"

            )


        except:

            pass




    await update.message.reply_text(

        "🎮 نتیجه بازی\n\n"

        f"{result}\n\n"

        f"🎲 مبلغ: {amount:,} DOGS"

    )








# =========================
# ROUTER
# =========================

async def router(update, context):

    if await admin_text(update, context):

        return


    if await support_message(update, context):

        return



    text = update.message.text



    if text == "💳 واریزی":

        await deposit_menu(update, context)


    elif text == "💰 برداشت":

        await withdraw_menu(update, context)


    elif text == "🎧 پشتیبانی":

        await support(update, context)


    elif text == "👥 زیرمجموعه":

        await referral(update, context)


    elif text == "👥 انتقال":

        await update.message.reply_text(

            "روی پیام کاربر ریپلای کن و بنویس:\nانتقال 500"

        )


    elif text.startswith("انتقال "):

        await transfer(update, context)


    elif text.startswith("بازی "):

        await game_command(update, context)


    elif text == "⚙️ پنل مدیریت":

        await admin_panel(update, context)







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
            check_join_callback,
            pattern="check_join"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            deposit_select,
            pattern="dep_"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            deposit_admin,
            pattern="dep_(ok|no):"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            withdraw_admin,
            pattern="wd_(ok|no):"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern="admin_"
        )
    )


    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_contact
        )
    )


    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            deposit_receipt
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            router
        )
    )


    print("BOT STARTED")


    app.run_polling()



if __name__ == "__main__":

    main()
