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


# ارز
CURRENCY = "DOGS"


# واریز
ULTRA_ADDRESS = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"


# محدودیت ها
MIN_DEPOSIT = 5000

MIN_WITHDRAW = 10000


# زیرمجموعه
REF_REWARD = 50


# بازی
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

    "enabled": True

}



# =========================
# LOAD / SAVE
# =========================

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

        temp = DATA_FILE + ".tmp"

        with open(temp, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp, DATA_FILE)


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

            "ref_money": 0,

            "referrer": None,

            "date": datetime.now().isoformat()

        }


        save_data()



def get_balance(uid):

    user = data["users"].get(str(uid))


    if not user:

        return 0


    try:

        return int(user.get("balance", 0))

    except:

        return 0



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

    amount = int(amount)


    if get_balance(uid) < amount:

        return False


    data["users"][uid]["balance"] -= amount


    save_data()

    return True



def is_owner(uid):

    return int(uid) == int(data.get("owner", OWNER_ID))


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
            "بعد از عضویت روی دکمه بررسی بزنید.",

            reply_markup=join_keyboard()

        )

        return





    if not data["users"][str(user.id)].get("phone"):


        context.user_data["need_phone"] = True


        await update.message.reply_text(

            "📱 برای ورود به ربات شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط شماره ایران (+98) قبول است.",

            reply_markup=phone_keyboard()

        )

        return





    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)

    )






# =========================
# CHECK JOIN BUTTON
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




    create_user(q.from_user)


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



    contact = update.message.contact


    if not contact:

        return



    phone = contact.phone_number



    if not phone.startswith("+"):

        phone = "+" + phone




    if not phone.startswith("+98"):


        await update.message.reply_text(

            "❌ فقط شماره ایران (+98) قبول است."

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
# MAIN KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [

        [
            "💳 واریزی",
            "💰 برداشت"
        ],

        [
            "👤 پروفایل",
            "🎧 پشتیبانی"
        ],

        [
            "👥 انتقال",
            "👥 زیرمجموعه گیری"
        ]

    ]


    if is_owner(uid):

        rows.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )


    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )





# =========================
# PROFILE
# =========================

async def profile(update, context):

    user = update.effective_user

    create_user(user)


    u = data["users"][str(user.id)]


    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: {u.get('refs',0)} نفر\n"

        f"🎁 درآمد زیرمجموعه: {u.get('ref_money',0):,} DOGS"

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


    await update.message.reply_text(

        "👥 زیرمجموعه گیری\n\n"

        "لینک دعوت شما:\n"

        f"{link}\n\n"

        f"🎁 هر زیرمجموعه موفق: {REF_REWARD} DOGS\n\n"

        "با دعوت دوستان موجودی بگیرید."

    )






# =========================
# REGISTER REFERRAL
# =========================

def check_referral(new_user_id, ref_id):

    new_user_id = str(new_user_id)

    ref_id = str(ref_id)


    if new_user_id == ref_id:

        return


    if new_user_id not in data["users"]:

        return


    if data["users"][new_user_id].get("referrer"):

        return


    if ref_id not in data["users"]:

        return



    data["users"][new_user_id]["referrer"] = int(ref_id)



    data["users"][ref_id]["refs"] += 1


    data["users"][ref_id]["ref_money"] += REF_REWARD


    add_balance(
        int(ref_id),
        REF_REWARD
    )


    save_data()


# =========================
# DEPOSIT
# =========================

async def deposit_menu(update, context):

    context.user_data.clear()


    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"
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





async def deposit_select(update, context):

    q = update.callback_query

    await q.answer()


    if q.data == "deposit_ultra":

        method = "ultra"

    else:

        method = "exchange"



    context.user_data["deposit_method"] = method

    context.user_data["deposit_state"] = "amount"



    await q.message.reply_text(

        f"💰 مقدار DOGS را وارد کنید.\n\n"
        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS"

    )







async def deposit_amount(update, context):

    if context.user_data.get("deposit_state") != "amount":

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

    context.user_data["deposit_state"] = "receipt"



    method = context.user_data["deposit_method"]



    if method == "ultra":

        text = (

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "فرصت مثال واریز:\n\n"

            f"ULTRA {amount} DOGS {ULTRA_ADDRESS}\n\n"

            "واریز کنید و شات یا پیام واریز را ارسال کنید.\n\n"

            "📸 شات قبول می‌شود."

        )


    else:

        text = (

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "به این ولت واریز کنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            "بعد از واریز شات یا لینک هش تراکنش را ارسال کنید."

        )



    await update.message.reply_text(text)


    return True







async def deposit_receipt(update, context):

    if context.user_data.get("deposit_state") != "receipt":

        return False



    user = update.effective_user


    amount = context.user_data.get("amount")


    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        rtype = "photo"


    elif update.message.text:

        receipt = update.message.text

        rtype = "text"


    else:

        await update.message.reply_text(
            "❌ فقط عکس یا متن ارسال کنید."
        )

        return True




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
                callback_data=f"deposit_ok:{req}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"deposit_no:{req}"
            )

        ]

    ])



    msg = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"🆔 درخواست:\n{req}"

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

            msg + "\n\n📎 رسید:\n" + receipt,

            reply_markup=kb

        )







async def deposit_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        await q.answer(
            "⛔ فقط مالک",
            show_alert=True
        )

        return



    action, req = q.data.split(":")



    dep = data["deposits"].get(req)



    if not dep:

        return



    if dep["status"] != "pending":

        await q.answer(
            "قبلا بررسی شده",
            show_alert=True
        )

        return




    uid = dep["user"]



    if action == "deposit_ok":


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

    context.user_data.clear()


    if get_balance(user.id) < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: {get_balance(user.id):,} DOGS\n"

            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

        )

        return



    context.user_data["withdraw_state"] = "amount"



    await update.message.reply_text(

        f"💰 مبلغ برداشت را وارد کنید.\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"

    )






async def withdraw_amount(update, context):

    if context.user_data.get("withdraw_state") != "amount":

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



    context.user_data["withdraw_amount"] = amount

    context.user_data["withdraw_state"] = "address"



    await update.message.reply_text(

        "📍 آدرس ولت یا آیدی دریافت را ارسال کنید."

    )


    return True







async def withdraw_address(update, context):

    if context.user_data.get("withdraw_state") != "address":

        return False



    user = update.effective_user


    amount = context.user_data.get(
        "withdraw_amount"
    )


    address = update.message.text.strip()



    if not address or not amount:

        return True




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

                callback_data=f"withdraw_ok:{req}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_data=f"withdraw_no:{req}"

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







async def withdraw_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        await q.answer(
            "⛔ فقط مالک",
            show_alert=True
        )

        return



    action, req = q.data.split(":")



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



    if action == "withdraw_ok":


        wd["status"] = "approved"

        save_data()



        await q.edit_message_text(

            "✅ برداشت تایید شد."

        )



        await context.bot.send_message(

            uid,

            f"✅ برداشت تایید شد\n\n"
            f"💰 مبلغ: {wd['amount']:,} DOGS"

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

    create_user(user)


    parts = update.message.text.split()


    if len(parts) != 2:

        await update.message.reply_text(

            "❌ فرمت صحیح:\n\n"
            "روی پیام کاربر ریپلای کن و بنویس:\n"
            "انتقال 500"

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

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return




    if not update.message.reply_to_message:

        await update.message.reply_text(

            "❌ باید روی پیام گیرنده ریپلای کنید."

        )

        return




    target = update.message.reply_to_message.from_user



    if target.is_bot:

        await update.message.reply_text(
            "❌ انتقال به ربات امکان ندارد."
        )

        return




    if target.id == user.id:

        await update.message.reply_text(

            "❌ انتقال به خودت امکان ندارد."

        )

        return




    create_user(target)




    if get_balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return




    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(

            "❌ انتقال انجام نشد."

        )

        return




    add_balance(
        target.id,
        amount
    )





    await update.message.reply_text(

        "✅ انتقال انجام شد.\n\n"

        f"👤 گیرنده: {target.first_name}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"💳 موجودی شما: {get_balance(user.id):,} DOGS"

    )




    try:

        await context.bot.send_message(

            target.id,

            "📥 موجودی دریافت شد.\n\n"

            f"💰 +{amount:,} DOGS\n"

            f"👤 فرستنده: {user.first_name}"

        )


    except:

        pass


# =========================
# GROUP GAME
# =========================

async def game_command(update, context):

    if update.effective_chat.type == "private":
        return


    user = update.effective_user

    create_user(user)


    parts = update.message.text.split()


    if len(parts) != 2:

        await update.message.reply_text(

            "❌ فرمت:\n"
            "بازی 500\n\n"
            f"حداقل: {MIN_GAME:,}\n"
            f"حداکثر: {MAX_GAME:,}"

        )

        return



    try:

        amount = int(parts[1])

    except:

        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )

        return




    if amount < MIN_GAME or amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ مبلغ بازی بین {MIN_GAME:,} تا {MAX_GAME:,} DOGS باشد."

        )

        return




    if get_balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return




    gid = f"GAME_{user.id}_{time.time_ns()}"



    data["games"][gid] = {

        "id": gid,

        "owner": user.id,

        "amount": amount,

        "chat": update.effective_chat.id,

        "status": "waiting"

    }



    save_data()




    await update.message.reply_text(

        "🎮 بازی جدید ساخته شد\n\n"

        f"👤 سازنده: {user.first_name}\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "یک نفر وارد شود:",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "🎮 ورود به بازی",

                    callback_data=f"join_game:{gid}"

                )

            ]

        ])

    )








async def game_join(update, context):

    q = update.callback_query

    await q.answer()



    user = q.from_user

    create_user(user)



    gid = q.data.split(":")[1]



    game = data["games"].get(gid)



    if not game:

        return




    if game["status"] != "waiting":

        await q.answer(

            "این بازی تمام شده.",

            show_alert=True

        )

        return




    if game["owner"] == user.id:

        await q.answer(

            "خودت نمی‌توانی وارد شوی.",

            show_alert=True

        )

        return




    amount = game["amount"]



    if get_balance(user.id) < amount:

        await q.answer(

            "موجودی کافی نیست.",

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




    players = [

        game["owner"],

        user.id

    ]



    winner = random.choice(players)


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



    game["status"] = "done"

    game["winner"] = winner

    game["loser"] = loser



    save_data()





    await q.edit_message_text(

        "🎮 نتیجه بازی\n\n"

        f"🏆 برنده: {winner}\n"

        f"❌ بازنده: {loser}\n\n"

        f"💰 جایزه: {prize:,} DOGS"

    )




    try:

        await context.bot.send_message(

            winner,

            f"🏆 تبریک! برنده شدی 🎉\n\n"
            f"💰 +{prize:,} DOGS"

        )


    except:

        pass




    try:

        await context.bot.send_message(

            loser,

            f"❌ بازی را باختی.\n\n"
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

        context.user_data["admin_action"] = "add"

        await q.message.reply_text(

            "💰 آیدی کاربر و مقدار را بفرست:\n\n"
            "مثال:\n"
            "123456 5000"

        )


    elif q.data == "admin_remove":

        context.user_data["admin_action"] = "remove"

        await q.message.reply_text(

            "➖ آیدی کاربر و مقدار را بفرست:\n\n"
            "مثال:\n"
            "123456 5000"

        )


    elif q.data == "admin_owner":

        context.user_data["admin_action"] = "owner"

        await q.message.reply_text(

            "👑 آیدی مالک جدید را ارسال کن."

        )







async def admin_text(update, context):

    action = context.user_data.get(
        "admin_action"
    )


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



        create_user(
            update.effective_user
        )


        if action == "add":

            add_balance(
                uid,
                amount
            )

        else:

            remove_balance(
                uid,
                amount
            )



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
# ROUTER
# =========================

async def router(update, context):

    if not update.message:

        return



    text = update.message.text



    if await admin_text(update, context):

        return



    if text in ["💳 واریزی","واریزی","واریز"]:

        await deposit_menu(update, context)


    elif text in ["💰 برداشت","برداشت","برداشتی"]:

        await withdraw_menu(update, context)


    elif text in ["👤 پروفایل","پروفایل"]:

        await profile(update, context)


    elif text in ["👥 زیرمجموعه گیری","زیرمجموعه"]:

        await referral(update, context)


    elif text == "⚙️ پنل مدیریت":

        await admin_panel(update, context)


    elif text.startswith("انتقال "):

        await transfer(update, context)


    elif text.startswith("بازی "):

        await game_command(update, context)


    elif text == "🎧 پشتیبانی":

        await support(update, context)


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
            pattern="deposit_"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            deposit_admin,
            pattern="deposit_(ok|no):"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            withdraw_admin,
            pattern="withdraw_(ok|no):"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_join,
            pattern="join_game:"
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


    app.add_error_handler(
        lambda u,c: traceback.print_exc()
    )


    print("BOT STARTED")


    app.run_polling()



if __name__ == "__main__":

    main()
