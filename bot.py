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
    KeyboardButton,
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

BOT_USERNAME = "tak_BETTbot"


# عضویت اجباری
FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_BE_T"


# کیف پول
CURRENCY = "DOGS"


# واریز
ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"


# محدودیت ها
MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

REF_REWARD = 50


# بازی
MIN_GAME = 500
MAX_GAME = 20000


DATA_FILE = "data.json"


# =========================
# DATA
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "enabled": True,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {}

}



def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(DATA_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

    except:

        traceback.print_exc()


    return DEFAULT_DATA.copy()



data = load_data()



def save_data():

    try:

        with open(DATA_FILE, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

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

            "phone": False,

            "refs": 0,

            "ref_money": 0,

            "referrer": None,

            "date": datetime.now().isoformat()

        }

        save_data()



def get_balance(uid):

    user = data["users"].get(str(uid))

    if not user:

        return 0


    return int(user.get("balance", 0))



def add_balance(uid, amount):

    uid = str(uid)


    if uid not in data["users"]:

        return False


    data["users"][uid]["balance"] = (

        get_balance(uid) + int(amount)

    )


    save_data()

    return True



def remove_balance(uid, amount):

    uid = str(uid)


    if get_balance(uid) < amount:

        return False


    data["users"][uid]["balance"] -= int(amount)


    save_data()

    return True



def is_owner(uid):

    return int(uid) == int(data.get("owner", OWNER_ID))



# =========================
# KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [

        ["💳 واریزی", "💰 برداشت"],

        ["👤 پروفایل", "🎧 پشتیبانی"],

        ["👥 انتقال", "👥 زیرمجموعه گیری"]

    ]


    if is_owner(uid):

        rows.append(
            ["⚙️ پنل مدیریت"]
        )


    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
)


# =========================
# FORCE JOIN
# =========================

async def check_join(bot, user_id):

    try:

        for chat in [FORCE_CHANNEL, FORCE_GROUP]:

            member = await bot.get_chat_member(
                chat_id=chat,
                user_id=user_id
            )

            if member.status in ["left", "kicked"]:

                return False


        return True


    except Exception:

        return False



def join_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📢 کانال",
                url="https://t.me/TAK_B_ET"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 گپ",
                url="https://t.me/TAK_BE_T"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="check_join"
            )
        ]

    ])



# =========================
# PHONE BUTTON
# =========================

def phone_keyboard():

    return ReplyKeyboardMarkup(

        [

            [

                KeyboardButton(
                    "📱 ارسال شماره",
                    request_contact=True
                )

            ]

        ],

        resize_keyboard=True,

        one_time_keyboard=True

    )





# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user


    create_user(user)



    if not await check_join(
        context.bot,
        user.id
    ):


        await update.message.reply_text(

            "❌ ابتدا عضو کانال و گپ شوید.\n\n"
            "بعد از عضویت روی بررسی بزنید.",

            reply_markup=join_keyboard()

        )

        return




    if not data["users"][str(user.id)].get("phone"):


        context.user_data["need_phone"] = True


        await update.message.reply_text(

            "📱 برای ورود به ربات شماره خود را ارسال کنید.\n\n"
            "فقط شماره ایران (+98) قبول است.",

            reply_markup=phone_keyboard()

        )

        return




    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)

    )





# =========================
# CHECK JOIN CALLBACK
# =========================

async def check_join_callback(update, context):

    q = update.callback_query

    await q.answer()



    if not await check_join(
        context.bot,
        q.from_user.id
    ):


        await q.answer(

            "❌ هنوز عضو نشده‌اید.",

            show_alert=True

        )

        return




    create_user(
        q.from_user
    )


    context.user_data["need_phone"] = True



    await q.message.reply_text(

        "✅ عضویت تایید شد.\n\n"
        "📱 روی دکمه ارسال شماره بزنید.",

        reply_markup=phone_keyboard()

    )





# =========================
# PHONE VERIFY
# =========================

async def phone_contact(update, context):

    if not context.user_data.get("need_phone"):

        return



    if not update.message.contact:

        return



    phone = update.message.contact.phone_number



    if not phone.startswith("+"):

        phone = "+" + phone




    if not phone.startswith("+98"):


        await update.message.reply_text(

            "❌ فقط شماره ایران قبول است."

        )

        return




    uid = str(update.effective_user.id)



    data["users"][uid]["phone"] = phone



    save_data()



    context.user_data.clear()



    await update.message.reply_text(

        "✅ شماره تایید شد.\n\n"
        "خوش آمدید 🤖",

        reply_markup=main_keyboard(
            update.effective_user.id
        )

            )


# =========================
# PROFILE
# =========================

async def profile(update, context):

    user = update.effective_user

    create_user(user)

    u = data["users"][str(user.id)]

    link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start={user.id}"
    )


    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS\n\n"

        f"👥 زیرمجموعه: {u['refs']} نفر\n"

        f"🎁 درآمد دعوت: {u['ref_money']:,} DOGS\n\n"

        f"🔗 لینک دعوت:\n{link}"

    )



# =========================
# REFERRAL
# =========================

async def referral(update, context):

    user = update.effective_user

    create_user(user)


    link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start={user.id}"
    )


    u = data["users"][str(user.id)]


    await update.message.reply_text(

        "👥 زیرمجموعه گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"👤 تعداد دعوت: {u['refs']}\n"

        f"💰 درآمد: {u['ref_money']:,} DOGS\n\n"

        f"🎁 هر نفر: +{REF_REWARD} DOGS"

    )





# =========================
# TRANSFER
# =========================

async def transfer(update, context):

    user = update.effective_user


    if not update.message.reply_to_message:

        await update.message.reply_text(

            "❌ روی پیام کاربر ریپلای کن.\n\n"
            "مثال:\n"
            "انتقال 500"

        )

        return



    parts = update.message.text.split()


    if len(parts) != 2:

        await update.message.reply_text(

            "❌ فرمت اشتباه."

        )

        return



    try:

        amount = int(parts[1])

    except:

        await update.message.reply_text(

            "❌ مبلغ باید عدد باشد."

        )

        return




    if amount <= 0:

        return



    target = update.message.reply_to_message.from_user



    if target.id == user.id:

        await update.message.reply_text(

            "❌ انتقال به خودت امکان ندارد."

        )

        return



    create_user(target)



    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return




    add_balance(
        target.id,
        amount
    )




    await update.message.reply_text(

        "✅ انتقال انجام شد.\n\n"

        f"👤 گیرنده: {target.first_name}\n"

        f"💰 مبلغ: {amount:,} DOGS"

    )



    try:

        await context.bot.send_message(

            target.id,

            "📥 موجودی دریافت شد.\n\n"

            f"💰 +{amount:,} DOGS"

        )

    except:

        pass



# =========================
# DEPOSIT
# =========================

async def deposit_menu(update, context):

    await update.message.reply_text(

        "💳 روش واریزی را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "🟣 اولترا",
                    callback_data="dep_ultra"
                )
            ],

            [
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

        f"💰 مقدار DOGS را وارد کنید.\n\n"
        f"حداقل: {MIN_DEPOSIT:,}"

    )





async def deposit_amount(update, context):

    if context.user_data.get("dep_state") != "amount":

        return False



    try:

        amount = int(update.message.text)

    except:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )

        return True




    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل {MIN_DEPOSIT:,} DOGS"

        )

        return True




    context.user_data["dep_amount"] = amount

    context.user_data["dep_state"] = "receipt"



    method = context.user_data["dep_method"]




    if method == "ultra":


        text = (

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"آیدی:\n{ULTRA_ADDRESS}\n\n"

            "بعد از ارسال، رسید را بفرستید."

        )


    else:


        text = (

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"ولت:\n{EXCHANGE_WALLET}\n\n"

            "بعد از ارسال، رسید را بفرستید."

        )




    await update.message.reply_text(text)


    return True






async def deposit_receipt(update, context):

    if context.user_data.get("dep_state") != "receipt":

        return False



    user = update.effective_user

    amount = context.user_data.get("dep_amount")



    if update.message.photo:

        receipt = update.message.photo[-1].file_id


    else:

        receipt = update.message.text




    req = f"DEP_{user.id}_{time.time_ns()}"



    data["deposits"][req] = {

        "user": user.id,

        "amount": amount,

        "receipt": receipt,

        "status": "pending"

    }



    save_data()



    context.user_data.clear()




    await update.message.reply_text(

        "✅ رسید ثبت شد.\n"
        "⏳ منتظر تایید مالک باشید."

    )




    await context.bot.send_message(

        OWNER_ID,

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"🆔 {req}",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(
                    "✅ تایید",
                    callback_data=f"dep_ok_{req}"
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"dep_no_{req}"
                )

            ]

        ])

    )



    return True






async def deposit_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return




    parts = q.data.split("_",2)


    action = parts[1]

    req = parts[2]



    dep = data["deposits"].get(req)



    if not dep:

        return



    if dep["status"] != "pending":

        return



    if action == "ok":


        add_balance(
            dep["user"],
            dep["amount"]
        )


        dep["status"]="approved"



        await q.edit_message_text(

            "✅ واریز تایید شد."

        )



        await context.bot.send_message(

            dep["user"],

            f"✅ واریز تایید شد.\n"
            f"💰 +{dep['amount']:,} DOGS"

        )



    else:


        dep["status"]="rejected"



        await q.edit_message_text(

            "❌ واریز رد شد."

        )



    save_data()


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

            f"حداقل برداشت: {MIN_WITHDRAW:,}"

        )

        return



    context.user_data["wd_state"] = "amount"



    await update.message.reply_text(

        "💰 مبلغ برداشت را ارسال کنید.\n\n"

        f"حداقل: {MIN_WITHDRAW:,} DOGS"

    )





async def withdraw_amount(update, context):

    if context.user_data.get("wd_state") != "amount":

        return False



    try:

        amount = int(update.message.text)

    except:

        await update.message.reply_text(
            "❌ عدد ارسال کنید."
        )

        return True



    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت {MIN_WITHDRAW:,}"

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

        "📍 آدرس یا آیدی دریافت را ارسال کنید."

    )

    return True






async def withdraw_address(update, context):

    if context.user_data.get("wd_state") != "address":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "wd_amount"
    )


    address = update.message.text



    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(

            "❌ خطا در کسر موجودی."

        )

        return True




    req = f"WD_{user.id}_{time.time_ns()}"



    data["withdraws"][req] = {

        "user": user.id,

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





    await context.bot.send_message(

        OWNER_ID,

        "💰 برداشت جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📍 آدرس:\n{address}\n\n"

        f"🆔 {req}",


        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "✅ تایید",

                    callback_data=f"wd_ok_{req}"

                ),

                InlineKeyboardButton(

                    "❌ رد",

                    callback_data=f"wd_no_{req}"

                )

            ]

        ])

    )



    return True







async def withdraw_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return



    parts = q.data.split("_",2)



    action = parts[1]

    req = parts[2]



    wd = data["withdraws"].get(req)



    if not wd:

        return



    if wd["status"] != "pending":

        return



    uid = wd["user"]



    if action == "ok":


        wd["status"]="approved"



        await q.edit_message_text(

            "✅ برداشت تایید شد."

        )



        await context.bot.send_message(

            uid,

            f"✅ برداشت تایید شد.\n\n"

            f"💰 مبلغ: {wd['amount']:,} DOGS"

        )



    else:


        wd["status"]="rejected"



        add_balance(

            uid,

            wd["amount"]

        )



        await q.edit_message_text(

            "❌ برداشت رد شد.\n"
            "💰 موجودی برگشت داده شد."

        )



        await context.bot.send_message(

            uid,

            "❌ برداشت رد شد.\n\n"

            f"💰 +{wd['amount']:,} DOGS برگشت داده شد."

        )



    save_data()


# =========================
# GAME IN GROUP
# =========================

async def game_command(update, context):

    if update.effective_chat.type == "private":
        return


    user = update.effective_user

    create_user(user)


    parts = update.message.text.split()


    if len(parts) != 2:

        await update.message.reply_text(
            "❌ مثال:\nبازی 500"
        )

        return



    try:

        amount = int(parts[1])

    except:

        await update.message.reply_text(
            "❌ مبلغ اشتباه است."
        )

        return



    if amount < MIN_GAME or amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ شرط بین {MIN_GAME:,} تا {MAX_GAME:,} DOGS"

        )

        return



    if get_balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return



    gid = f"G_{user.id}_{time.time_ns()}"


    data["games"][gid] = {

        "owner": user.id,

        "amount": amount,

        "status": "waiting"

    }


    save_data()



    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"

        f"👤 سازنده: {user.first_name}\n"

        f"💰 شرط: {amount:,} DOGS\n\n"

        "یک نفر وارد شود.",


        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "🎮 ورود",

                    callback_data=f"game_join_{gid}"

                )

            ]

        ])

    )





async def game_callback(update, context):

    q = update.callback_query

    await q.answer()



    if not q.data.startswith("game_join_"):

        return



    gid = q.data.replace(
        "game_join_",
        ""
    )


    game = data["games"].get(gid)



    if not game:

        return



    user = q.from_user



    if user.id == game["owner"]:

        await q.answer(

            "❌ خودت نمی‌توانی",

            show_alert=True

        )

        return



    amount = game["amount"]



    if get_balance(user.id) < amount:

        await q.answer(

            "❌ موجودی کافی نیست",

            show_alert=True

        )

        return



    remove_balance(
        game["owner"],
        amount
    )


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


    prize = amount * 2



    add_balance(
        winner,
        prize
    )



    game["status"]="done"

    game["winner"]=winner

    save_data()



    await q.edit_message_text(

        "🎮 نتیجه بازی\n\n"

        f"🏆 برنده: {winner}\n"

        f"💰 جایزه: {prize:,} DOGS"

    )



    try:

        await context.bot.send_message(

            winner,

            "🏆 تبریک! برنده شدی\n\n"

            f"💰 +{prize:,} DOGS"

        )

    except:

        pass



    try:

        await context.bot.send_message(

            loser,

            "❌ باختی\n\n"

            f"💸 -{amount:,} DOGS"

        )

    except:

        pass


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
                    "💰 شارژ موجودی",
                    callback_data="admin_add"
                ),
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="admin_remove"
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_owner"
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

        await q.message.reply_text(

            "📊 آمار\n\n"

            f"👤 کاربران: {len(data['users'])}\n"

            f"💳 واریزی: {len(data['deposits'])}\n"

            f"💰 برداشت: {len(data['withdraws'])}\n"

            f"🎮 بازی: {len(data['games'])}"

        )


    elif q.data == "admin_add":

        context.user_data["admin"] = "add"

        await q.message.reply_text(

            "💰 آیدی و مقدار را بفرست:\n\n"
            "مثال:\n"
            "123456 5000"

        )


    elif q.data == "admin_remove":

        context.user_data["admin"] = "remove"

        await q.message.reply_text(

            "➖ آیدی و مقدار را بفرست:\n\n"
            "مثال:\n"
            "123456 5000"

        )


    elif q.data == "admin_owner":

        context.user_data["admin"] = "owner"

        await q.message.reply_text(
            "👑 آیدی مالک جدید را بفرست."
        )





async def admin_text(update, context):

    action = context.user_data.get("admin")


    if not action:
        return False


    if not is_owner(update.effective_user.id):
        return False



    if action in ["add","remove"]:

        try:

            uid, amount = update.message.text.split()

            uid = int(uid)

            amount = int(amount)


        except:

            await update.message.reply_text(
                "❌ فرمت اشتباه."
            )

            return True



        create_user(update.effective_user)


        if action == "add":

            add_balance(uid, amount)

        else:

            remove_balance(uid, amount)



        await update.message.reply_text(
            "✅ انجام شد."
        )



    elif action == "owner":

        new_owner = int(
            update.message.text
        )


        data["owner"] = new_owner

        save_data()


        await update.message.reply_text(
            "👑 مالک تغییر کرد."
        )



    context.user_data.clear()

    return True





# =========================
# TEXT ROUTER
# =========================

async def router(update, context):

    if not update.message:
        return


    text = update.message.text


    if await admin_text(update, context):
        return



    if text == "💳 واریزی":
        await deposit_menu(update, context)


    elif text == "💰 برداشت":
        await withdraw_menu(update, context)


    elif text == "👤 پروفایل":
        await profile(update, context)


    elif text == "👥 زیرمجموعه گیری":
        await referral(update, context)


    elif text == "👥 انتقال":
        await update.message.reply_text(
            "روی پیام کاربر ریپلای کن و بنویس:\nانتقال 500"
        )


    elif text.startswith("انتقال "):
        await transfer(update, context)


    elif text == "⚙️ پنل مدیریت":
        await admin_panel(update, context)


    elif text.startswith("بازی "):
        await game_command(update, context)


    elif await deposit_amount(update, context):
        return


    elif await deposit_receipt(update, context):
        return


    elif await withdraw_amount(update, context):
        return


    elif await withdraw_address(update, context):
        return





# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise Exception(
            "BOT_TOKEN missing"
        )


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
            pattern="dep_(ok|no)_"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            withdraw_admin,
            pattern="wd_(ok|no)_"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern="game_join_"
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
            filters.TEXT & ~filters.COMMAND,
            router
        )
    )


    print("BOT STARTED")

    app.run_polling()



if __name__ == "__main__":
    main()
