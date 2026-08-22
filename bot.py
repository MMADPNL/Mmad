import os
import json
import time
import traceback
import random

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

FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_B_ET"


DATA_FILE = "data.json"


MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000


MIN_GAME = 500
MAX_GAME = 20000


DEFAULT_REF_REWARD = 50



# =========================
# DATA
# =========================

DEFAULT_DATA = {

    "owner": OWNER_ID,

    "ref_reward": DEFAULT_REF_REWARD,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {}

}



# =========================
# ANTI BUG
# =========================

LAST_CLICK = {}



def anti_spam(uid):

    now = time.time()

    last = LAST_CLICK.get(
        str(uid),
        0
    )

    if now - last < 2:

        return False


    LAST_CLICK[str(uid)] = now

    return True





def safe_int(value):

    try:
        return int(value)

    except:
        return 0






# =========================
# DATA LOAD / SAVE
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


            for k, v in DEFAULT_DATA.items():

                if k not in data:

                    data[k] = v


            return data


    except Exception as e:

        print(
            "LOAD ERROR:",
            e
        )


        try:

            if os.path.exists(
                "data_backup.json"
            ):

                with open(
                    "data_backup.json",
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


        with open(
            "data_backup.json",
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
# USER SYSTEM
# =========================


def create_user(user):

    uid = str(user.id)


    if uid not in data["users"]:

        data["users"][uid] = {

            "id": user.id,

            "name": user.first_name or "",

            "username": user.username or "",

            "phone": "",

            "balance": 0,

            "refs": 0,

            "ref_by": None

        }

        save_data()



def get_balance(uid):

    try:

        return safe_int(
            data["users"][str(uid)]["balance"]
        )

    except:

        return 0





def add_balance(uid, amount):

    uid = str(uid)


    if uid not in data["users"]:

        return False


    new_balance = (
        get_balance(uid)
        +
        safe_int(amount)
    )


    if new_balance < 0:

        new_balance = 0



    data["users"][uid]["balance"] = new_balance

    save_data()

    return True





def remove_balance(uid, amount):

    amount = safe_int(amount)


    if get_balance(uid) < amount:

        return False


    return add_balance(
        uid,
        -amount
    )






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


def main_keyboard(uid):

    buttons = [

        ["💳 واریزی", "💰 برداشت"],

        ["👤 پروفایل", "🎧 پشتیبانی"],

        ["👥 انتقال", "👥 زیرمجموعه"]

    ]


    if is_owner(uid):

        buttons.append(
            ["⚙️ پنل مدیریت"]
        )


    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )






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
                url="https://t.me/TAK_B_ET"
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

        resize_keyboard=True

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
                chat,
                user_id
            )


            if member.status in [
                "left",
                "kicked"
            ]:

                return False



        return True



    except Exception as e:

        print(
            "JOIN ERROR:",
            e
        )

        return False







# =========================
# START
# =========================


async def start(update, context):

    user = update.effective_user


    create_user(user)



    if not await check_join(
        user.id,
        context
    ):


        await update.message.reply_text(

            "❌ ابتدا عضو کانال و گپ شوید.",

            reply_markup=join_keyboard()

        )

        return






    if not data["users"][str(user.id)].get(
        "phone"
    ):


        await update.message.reply_text(

            "📱 برای ورود شماره خود را ارسال کنید.\n\n"

            "فقط شماره ایران +98 قبول است.",

            reply_markup=phone_keyboard()

        )

        return





    await update.message.reply_text(

        "✅ خوش آمدید\n\n"

        f"💰 موجودی: {get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(user.id)

                )



# =========================
# PHONE VERIFY
# =========================


def clean_phone(phone):

    if not phone:

        return None


    phone = (
        phone
        .replace(" ","")
        .replace("-","")
    )


    if phone.startswith("0098"):

        phone = "+" + phone[2:]


    elif phone.startswith("98"):

        phone = "+" + phone



    if phone.startswith("+98"):

        return phone



    return None






async def phone_receive(update, context):

    user = update.effective_user


    if not update.message.contact:

        return



    contact = update.message.contact



    if contact.user_id != user.id:


        await update.message.reply_text(

            "❌ فقط شماره خودتان را ارسال کنید."

        )

        return




    phone = clean_phone(
        contact.phone_number
    )



    if not phone:


        await update.message.reply_text(

            "❌ فقط شماره ایران (+98) قبول است."

        )

        return




    create_user(user)



    data["users"][str(user.id)]["phone"] = phone

    save_data()



    await update.message.reply_text(

        "✅ شماره تایید شد.",

        reply_markup=main_keyboard(user.id)

    )







# =========================
# DEPOSIT
# =========================


async def deposit_menu(update, context):

    if not anti_spam(update.effective_user.id):

        return



    await update.message.reply_text(

        "💳 نوع واریز را انتخاب کنید:",

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



    context.user_data["deposit_type"] = q.data

    context.user_data["deposit_step"] = "amount"



    await q.message.reply_text(

        f"💰 مبلغ DOGS را وارد کنید.\n\n"

        f"حداقل: {MIN_DEPOSIT:,}"

    )







async def deposit_amount(update, context):


    if context.user_data.get(
        "deposit_step"
    ) != "amount":

        return False




    try:

        amount = int(update.message.text)

    except:


        return True





    if amount < MIN_DEPOSIT:


        await update.message.reply_text(

            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."

        )

        return True




    context.user_data["amount"] = amount

    context.user_data["deposit_step"] = "receipt"



    await update.message.reply_text(

        "📸 شات یا لینک هش واریز را ارسال کنید."

    )

    return True







async def deposit_receipt(update, context):


    if context.user_data.get(
        "deposit_step"
    ) != "receipt":

        return False





    user = update.effective_user


    amount = context.user_data.get(
        "amount"
    )


    if update.message.photo:

        receipt = update.message.photo[-1].file_id

        kind = "photo"


    else:

        receipt = update.message.text

        kind = "text"





    req = f"DEP_{user.id}_{time.time_ns()}"




    data["deposits"][req] = {

        "user": user.id,

        "amount": amount,

        "receipt": receipt,

        "kind": kind,

        "status": "pending"

    }



    save_data()



    context.user_data.clear()




    keyboard = InlineKeyboardMarkup([

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




    await context.bot.send_message(

        OWNER_ID,

        f"💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"🆔 {req}",

        reply_markup=keyboard

    )




    await update.message.reply_text(

        "✅ رسید ارسال شد.\n"

        "⏳ منتظر تایید مالک باشید."

    )


    return True
# =========================
# DEPOSIT ADMIN
# =========================


async def deposit_admin(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return




    if not anti_spam(q.from_user.id):

        return





    action, req = q.data.split(":",1)



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

    if get_balance(update.effective_user.id) < MIN_WITHDRAW:


        await update.message.reply_text(

            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."

        )

        return



    context.user_data.clear()

    context.user_data["withdraw_step"] = "amount"



    await update.message.reply_text(

        "💰 مبلغ برداشت را ارسال کنید."

    )






async def withdraw_amount(update, context):

    if context.user_data.get(
        "withdraw_step"
    ) != "amount":

        return False



    try:

        amount = int(update.message.text)

    except:

        return True





    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت {MIN_WITHDRAW:,} است."

        )

        return True





    if get_balance(update.effective_user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return True





    context.user_data["withdraw_amount"] = amount

    context.user_data["withdraw_step"] = "address"



    await update.message.reply_text(

        "📍 آدرس ولت را ارسال کنید."

    )



    return True







async def withdraw_address(update, context):

    if context.user_data.get(
        "withdraw_step"
    ) != "address":

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





    req = f"WD_{user.id}_{time.time_ns()}"



    data["withdraws"][req] = {

        "user": user.id,

        "amount": amount,

        "address": address,

        "status": "pending"

    }



    save_data()



    context.user_data.clear()



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

        f"💰 برداشت جدید\n\n"

        f"👤 {user.id}\n"

        f"💰 {amount:,} DOGS\n\n"

        f"📍 {address}",

        reply_markup=kb

    )



    await update.message.reply_text(

        "✅ درخواست برداشت ارسال شد."

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





    if action == "wd_ok":


        wd["status"] = "approved"

        save_data()



        await q.edit_message_text(

            "✅ برداشت تایید شد."

        )



    else:


        wd["status"] = "rejected"


        add_balance(
            wd["user"],
            wd["amount"]
        )


        save_data()



        await q.edit_message_text(

            "❌ رد شد و موجودی برگشت."

        )







# =========================
# TRANSFER
# =========================


async def transfer(update, context):


    if not update.message.reply_to_message:

        await update.message.reply_text(

            "❌ روی پیام کاربر ریپلای کن.\n"

            "مثال: انتقال 500"

        )

        return





    try:

        amount = int(
            update.message.text.split()[1]
        )

    except:

        return





    sender = update.effective_user

    receiver = update.message.reply_to_message.from_user



    create_user(receiver)




    if not remove_balance(
        sender.id,
        amount
    ):

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return





    add_balance(
        receiver.id,
        amount
    )



    await update.message.reply_text(

        "✅ انتقال انجام شد."

    )


# =========================
# SUPPORT
# =========================


async def support(update, context):

    context.user_data["support"] = True


    await update.message.reply_text(

        "🎧 پیام خود را برای پشتیبانی ارسال کنید."

    )







async def support_receive(update, context):

    if not context.user_data.get(
        "support"
    ):

        return False



    user = update.effective_user


    await context.bot.send_message(

        OWNER_ID,

        "🎧 پیام پشتیبانی\n\n"

        f"👤 کاربر: {user.id}\n"

        f"📩 پیام:\n{update.message.text}"

    )


    context.user_data.clear()



    await update.message.reply_text(

        "✅ پیام شما ارسال شد."

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



    refs = data["users"][str(user.id)].get(
        "refs",
        0
    )


    reward = data.get(
        "ref_reward",
        DEFAULT_REF_REWARD
    )



    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"👥 تعداد: {refs}\n"

        f"💰 جایزه هر نفر: {reward:,} DOGS"

    )







async def check_ref(update, context):

    if not context.args:

        return



    try:

        ref = int(
            context.args[0]
        )

    except:

        return




    user = update.effective_user


    if ref == user.id:

        return



    create_user(user)



    uid = str(user.id)



    if data["users"][uid].get(
        "ref_by"
    ):

        return




    if str(ref) not in data["users"]:

        return




    data["users"][uid]["ref_by"] = ref


    data["users"][str(ref)]["refs"] += 1



    reward = data.get(
        "ref_reward",
        DEFAULT_REF_REWARD
    )


    add_balance(
        ref,
        reward
    )


    save_data()







# =========================
# ADMIN PANEL
# =========================


async def admin_panel(update, context):

    if not is_owner(
        update.effective_user.id
    ):

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
                    callback_data="change_reward"
                )

            ]

        ])

    )







async def admin_callback(update, context):

    q = update.callback_query

    await q.answer()



    if not is_owner(
        q.from_user.id
    ):

        return





    if q.data == "admin_stats":


        total = sum(

            get_balance(uid)

            for uid in data["users"]

        )



        await q.message.reply_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {len(data['users'])}\n"

            f"💰 کل موجودی: {total:,} DOGS"

        )





    elif q.data == "change_reward":


        context.user_data["reward_change"] = True



        await q.message.reply_text(

            "مقدار جایزه جدید را ارسال کن."

        )








async def admin_text(update, context):

    if not is_owner(
        update.effective_user.id
    ):

        return False



    if context.user_data.get(
        "reward_change"
    ):


        try:

            value = int(
                update.message.text
            )

        except:

            return True




        data["ref_reward"] = value


        save_data()


        context.user_data.clear()



        await update.message.reply_text(

            f"✅ جایزه تغییر کرد به {value:,} DOGS"

        )


        return True



    return False


# =========================
# GAME IN GROUP
# =========================


async def game(update, context):

    if update.effective_chat.type == "private":

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



    user = update.effective_user


    create_user(user)



    if amount < MIN_GAME or amount > MAX_GAME:


        await update.message.reply_text(

            "❌ شرط باید بین 500 تا 20000 باشد."

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





    bot_score = random.randint(1,100)

    user_score = random.randint(1,100)



    if user_score > bot_score:


        add_balance(
            user.id,
            900
        )


        add_balance(
            OWNER_ID,
            100
        )


        result = "🏆 برنده شدی"



        try:

            await context.bot.send_message(

                user.id,

                "🏆 تبریک!\n\n"

                "شما در بازی برنده شدید.\n"

                "💰 جایزه: +900 DOGS"

            )

        except:

            pass



    else:


        result = "❌ باختی"


        try:

            await context.bot.send_message(

                user.id,

                "❌ شما بازی را باختید."

            )

        except:

            pass






    await update.message.reply_text(

        "🎮 نتیجه بازی\n\n"

        f"{result}\n"

        f"🎲 شرط: {amount:,}"

    )








# =========================
# ROUTER
# =========================


async def router(update, context):

    if not update.message:

        return


    text = update.message.text or ""



    if text == "💳 واریزی":

        await deposit_menu(update, context)
        return



    if text == "💰 برداشت":

        await withdraw_menu(update, context)
        return



    if text == "🎧 پشتیبانی":

        await support(update, context)
        return



    if text == "👥 زیرمجموعه":

        await referral(update, context)
        return



    if text == "⚙️ پنل مدیریت":

        await admin_panel(update, context)
        return



    if text.startswith("انتقال"):

        await transfer(update, context)
        return



    if text.startswith("بازی"):

        await game(update, context)
        return



    if await admin_text(update, context):

        return



    if await support_receive(update, context):

        return



    if await deposit_amount(update, context):

        return



    if await deposit_receipt(update, context):

        return



    if await withdraw_amount(update, context):

        return



    if await withdraw_address(update, context):

        return







# =========================
# ERROR HANDLER
# =========================


async def error_handler(update, context):

    print(
        "ERROR:",
        context.error
    )

    traceback.print_exc()








# =========================
# MAIN
# =========================


def main():


    app = Application.builder().token(
        BOT_TOKEN
    ).build()



    app.add_error_handler(
        error_handler
    )



    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "start",
            check_ref
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
            pattern="admin_|change_reward"
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            lambda u,c: check_join_callback(u,c),
            pattern="check_join"
        )
    )



    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_receive
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
