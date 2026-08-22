import os
import json
import time
import random
import traceback


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


ULTRA_ID = "@CyyFr"


ULTRA_WALLET = "ولت_اولترا"


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

    "bot_status": True,

    "ref_reward": 50,

    "users": {},

    "deposits": {},

    "withdraws": {}

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

    except Exception as e:

        print("LOAD ERROR:", e)



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

        print("SAVE ERROR:", e)





# =========================
# ANTI BUG
# =========================


CLICK = {}



def anti_spam(uid):

    now = time.time()


    old = CLICK.get(str(uid), 0)


    if now - old < 2:

        return False



    CLICK[str(uid)] = now


    return True


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

        return int(
            data["users"][str(uid)]["balance"]
        )

    except:

        return 0






def add_balance(uid, amount):

    uid = str(uid)


    if uid not in data["users"]:

        return False



    try:

        amount = int(amount)

    except:

        return False





    data["users"][uid]["balance"] = (

        get_balance(uid)

        +

        amount

    )




    if data["users"][uid]["balance"] < 0:

        data["users"][uid]["balance"] = 0




    save_data()


    return True







def remove_balance(uid, amount):


    try:

        amount = int(amount)

    except:

        return False




    if get_balance(uid) < amount:

        return False




    return add_balance(

        uid,

        -amount

    )







def is_owner(uid):


    try:

        return int(uid) == int(

            data.get(

                "owner",

                OWNER_ID

            )

        )

    except:

        return False


# =========================
# KEYBOARDS
# =========================


def main_keyboard(uid):

    buttons = [

        ["💳 واریزی", "💰 برداشت"],

        ["👥 زیرمجموعه", "🎧 پشتیبانی"],

        ["👤 پروفایل", "👥 انتقال"]

    ]


    if is_owner(uid):

        buttons.append(

            ["⚙️ پنل مدیریت"]

        )


    return ReplyKeyboardMarkup(

        buttons,

        resize_keyboard=True

    )







def back_keyboard():

    return ReplyKeyboardMarkup(

        [

            [

                "🔙 برگشت"

            ]

        ],

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





    if not data.get(

        "bot_status",

        True

    ) and not is_owner(user.id):


        await update.message.reply_text(

            "🔴 ربات خاموش است."

        )

        return






    if not await check_join(

        user.id,

        context

    ):


        await update.message.reply_text(

            "❌ اول عضو کانال و گپ شوید.",

            reply_markup=join_keyboard()

        )

        return






    if not data["users"][str(user.id)].get(

        "phone"

    ):


        await update.message.reply_text(

            "📱 شماره خود را ارسال کنید.\n\n"

            "فقط +98 قبول است.",

            reply_markup=phone_keyboard()

        )

        return






    await update.message.reply_text(

        "✅ ورود موفق\n\n"

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

        .replace(" ", "")

        .replace("-", "")

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

            "❌ فقط شماره ایران +98 قبول است."

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

        50

    )






    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        f"🔗 لینک شما:\n{link}\n\n"

        f"👥 تعداد زیرمجموعه: {refs}\n"

        f"💰 جایزه هر نفر: {reward:,} DOGS"

    )









async def check_ref(update, context):


    if not context.args:

        return



    try:

        ref_id = int(

            context.args[0]

        )

    except:

        return





    user = update.effective_user



    if ref_id == user.id:

        return






    create_user(user)




    uid = str(user.id)





    if data["users"][uid].get("ref_by"):

        return






    if str(ref_id) not in data["users"]:

        return






    data["users"][uid]["ref_by"] = ref_id



    data["users"][str(ref_id)]["refs"] += 1






    reward = data.get(

        "ref_reward",

        50

    )





    add_balance(

        ref_id,

        reward

    )



    save_data()


# =========================
# DEPOSIT SYSTEM
# =========================


async def deposit_menu(update, context):

    await update.message.reply_text(

        "💳 نوع واریزی را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup([

            [

                InlineKeyboardButton(
                    "🟣 اولترا",
                    callback_data="ultra"
                )

            ],

            [

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="exchange"
                )

            ]

        ])

    )








async def deposit_type(update, context):

    q = update.callback_query

    await q.answer()



    context.user_data["deposit_type"] = q.data

    context.user_data["deposit_step"] = "amount"



    await q.message.reply_text(

        f"💰 تعداد DOGS را وارد کنید.\n\n"

        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_keyboard()

    )








async def deposit_amount(update, context):


    if context.user_data.get(

        "deposit_step"

    ) != "amount":

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

            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."

        )

        return True





    context.user_data["amount"] = amount





    if context.user_data.get(

        "deposit_type"

    ) == "ultra":



        text = (

            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"📌 آدرس اولترا:\n{ULTRA_ID}\n\n"

            f"💳 ولت:\n{ULTRA_WALLET}\n\n"

            "📸 بعد از واریز عکس رسید را ارسال کنید."

        )



    else:



        text = (

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "💳 ولت صرافی:\n"

            f"{EXCHANGE_WALLET}\n\n"

            "📸 بعد از واریز عکس یا متن رسید را ارسال کنید."

        )






    context.user_data["deposit_step"] = "receipt"





    await update.message.reply_text(

        text,

        reply_markup=back_keyboard()

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



    elif update.message.text:


        receipt = update.message.text

        kind = "text"



    else:

        return True






    req = (

        f"DEP_{user.id}_"

        f"{time.time_ns()}"

    )





    data["deposits"][req] = {

        "user": user.id,

        "amount": amount,

        "receipt": receipt,

        "kind": kind,

        "status": "pending"

    }




    save_data()



    context.user_data.clear()






    kb = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(

                "✅ تایید",

                callback_data=f"dep_ok:{req}"

            ),

            InlineKeyboardButton(

                "❌ رد",

                callback_callback=f"dep_no:{req}"

            )

        ]

    ])






    admin_text = (

        "💳 واریزی جدید\n\n"

        f"👤 کاربر: {user.id}\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"🆔 {req}"

    )






    if kind == "photo":


        await context.bot.send_photo(

            OWNER_ID,

            receipt,

            caption=admin_text,

            reply_markup=kb

        )



    else:


        await context.bot.send_message(

            OWNER_ID,

            admin_text +

            "\n\n📄 رسید:\n" +

            receipt,

            reply_markup=kb

        )






    await update.message.reply_text(

        "✅ رسید دریافت شد.\n\n"

        "⏳ منتظر تایید مالک باشید.",

        reply_markup=main_keyboard(user.id)

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





    action, req = q.data.split(":", 1)



    dep = data["deposits"].get(req)



    if not dep:

        return





    if dep["status"] != "pending":

        await q.answer(

            "قبلا بررسی شده",

            show_alert=True

        )

        return






    if action == "dep_ok":



        add_balance(

            dep["user"],

            dep["amount"]

        )



        dep["status"] = "approved"



        save_data()





        if q.message.photo:

            await q.edit_message_caption(

                caption="✅ واریزی تایید شد."

            )

        else:

            await q.edit_message_text(

                "✅ واریزی تایید شد."

            )





        await context.bot.send_message(

            dep["user"],

            "✅ واریز شما تایید شد.\n\n"

            f"💰 +{dep['amount']:,} DOGS"

        )







    else:



        dep["status"] = "rejected"


        save_data()



        if q.message.photo:

            await q.edit_message_caption(

                caption="❌ واریزی رد شد."

            )

        else:

            await q.edit_message_text(

                "❌ واریزی رد شد."

            )





        await context.bot.send_message(

            dep["user"],

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

        "💰 مقدار برداشت را وارد کنید.",

        reply_markup=back_keyboard()

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

            "❌ کمتر از حداقل برداشت است."

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

        "📍 آدرس ولت را ارسال کنید.",

        reply_markup=back_keyboard()

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



    address = update.message.text





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






    await context.bot.send_message(

        OWNER_ID,

        "💰 برداشت جدید\n\n"

        f"👤 {user.id}\n"

        f"💰 {amount:,} DOGS\n"

        f"📍 {address}"

    )






    await update.message.reply_text(

        "✅ درخواست برداشت ارسال شد.",

        reply_markup=main_keyboard(user.id)

    )



    return True







# =========================
# TRANSFER
# =========================


async def transfer(update, context):


    if not update.message.reply_to_message:


        await update.message.reply_text(

            "❌ روی پیام کاربر ریپلای کن.\n\n"

            "مثال:\nانتقال 500"

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

        "🎧 پیام خود را ارسال کنید.",

        reply_markup=back_keyboard()

    )







async def support_receive(update, context):


    if not context.user_data.get("support"):

        return False




    user = update.effective_user



    await context.bot.send_message(

        data["owner"],

        "🎧 پیام پشتیبانی\n\n"

        f"👤 آیدی: {user.id}\n"

        f"متن:\n{update.message.text}"

    )




    context.user_data.clear()



    await update.message.reply_text(

        "✅ پیام ارسال شد.",

        reply_markup=main_keyboard(user.id)

    )


    return True







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

                    "📊 آمار کاربران",

                    callback_data="stats"

                )

            ],

            [

                InlineKeyboardButton(

                    "👥 اضافه کردن زیرمجموعه",

                    callback_data="add_ref"

                )

            ],

            [

                InlineKeyboardButton(

                    "🔴 روشن / خاموش",

                    callback_data="toggle_bot"

                )

            ],

            [

                InlineKeyboardButton(

                    "👑 انتقال مالکیت",

                    callback_data="owner_change"

                )

            ]

        ])

    )









async def admin_callback(update, context):


    q = update.callback_query

    await q.answer()



    if not is_owner(q.from_user.id):

        return






    if q.data == "stats":



        total = 0

        refs = 0



        for uid in data["users"]:

            total += get_balance(uid)

            refs += data["users"][uid].get(

                "refs",

                0

            )





        await q.message.reply_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {len(data['users'])}\n"

            f"💰 موجودی کل: {total:,} DOGS\n"

            f"👥 زیرمجموعه‌ها: {refs}"

        )






    elif q.data == "add_ref":


        context.user_data["add_ref"] = True



        await q.message.reply_text(

            "🆔 آیدی کاربر را ارسال کنید."

        )








    elif q.data == "toggle_bot":


        data["bot_status"] = not data.get(

            "bot_status",

            True

        )


        save_data()



        await q.message.reply_text(

            "✅ وضعیت ربات تغییر کرد."

        )







    elif q.data == "owner_change":


        context.user_data["change_owner"] = True



        await q.message.reply_text(

            "🆔 آیدی مالک جدید را ارسال کنید."

        )








# =========================
# ADD REF RECEIVE
# =========================


async def add_ref_receive(update, context):


    if not context.user_data.get("add_ref"):

        return False




    if "ref_user" not in context.user_data:


        try:

            uid = int(update.message.text)

        except:

            return True




        if str(uid) not in data["users"]:


            await update.message.reply_text(

                "❌ کاربر پیدا نشد."

            )

            return True




        context.user_data["ref_user"] = uid



        await update.message.reply_text(

            "👥 تعداد زیرمجموعه را بفرست."

        )



        return True







    try:

        count = int(update.message.text)

    except:

        return True






    uid = context.user_data["ref_user"]



    data["users"][str(uid)]["refs"] += count



    save_data()



    context.user_data.clear()




    await update.message.reply_text(

        f"✅ {count} زیرمجموعه اضافه شد."

    )



    return True







# =========================
# OWNER CHANGE
# =========================


async def owner_change_receive(update, context):


    if not context.user_data.get("change_owner"):

        return False




    try:

        new_owner = int(update.message.text)

    except:

        return True




    data["owner"] = new_owner


    save_data()



    context.user_data.clear()




    await update.message.reply_text(

        "👑 مالک جدید ثبت شد."

    )



    return True


# =========================
# ROUTER
# =========================


async def router(update, context):


    if not update.message:

        return




    text = update.message.text or ""





    if text == "🔙 برگشت":


        context.user_data.clear()


        await update.message.reply_text(

            "✅ برگشتید.",

            reply_markup=main_keyboard(update.effective_user.id)

        )

        return







    if text == "💳 واریزی":


        await deposit_menu(update, context)

        return






    if text == "💰 برداشت":


        await withdraw_menu(update, context)

        return






    if text == "👥 زیرمجموعه":


        await referral(update, context)

        return






    if text == "🎧 پشتیبانی":


        await support(update, context)

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







    if await add_ref_receive(update, context):

        return






    if await owner_change_receive(update, context):

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

        MessageHandler(

            filters.CONTACT,

            phone_receive

        )

    )







    app.add_handler(

        CallbackQueryHandler(

            deposit_type,

            pattern="^(ultra|exchange)$"

        )

    )







    app.add_handler(

        CallbackQueryHandler(

            deposit_admin,

            pattern="^dep_"

        )

    )







    app.add_handler(

        CallbackQueryHandler(

            admin_callback

        )

    )







    # مهم: عکس + متن

    app.add_handler(

        MessageHandler(

            (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,

            router

        )

    )







    print(

        "BOT STARTED"

    )




    app.run_polling()








if __name__ == "__main__":

    main()
