# ==========================================
# DOGS BOT - bot.py
# PART 1
# DATABASE + SETTINGS
# ==========================================

import os
import json
import random
import re
import asyncio
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



# ==========================================
# SETTINGS
# ==========================================

BOT_TOKEN = "PUT_YOUR_BOT_TOKEN"

OWNER_ID = 123456789


DATA_FILE = "dogs_database.json"


MIN_GAME = 500


DEFAULT_REF_REWARD = 100



# ==========================================
# DEFAULT DATABASE
# ==========================================

DEFAULT_DATA = {

    "users": {},

    "games": {},

    "deposits": {},

    "withdraws": {},

    "transfers": {},

    "settings": {

        "bot_active": True,

        "ref_reward": DEFAULT_REF_REWARD,

        "owner_id": OWNER_ID

    }

}



# ==========================================
# LOAD / SAVE DATABASE
# ==========================================

def save_data():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            DATA,
            f,
            ensure_ascii=False,
            indent=4
        )



def load_data():

    if not os.path.exists(DATA_FILE):

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                DEFAULT_DATA,
                f,
                ensure_ascii=False,
                indent=4
            )

        return DEFAULT_DATA


    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        return data


    except:

        return DEFAULT_DATA



DATA = load_data()



# ==========================================
# USER SYSTEM
# ==========================================

def create_user(user):

    uid = str(user.id)


    if uid not in DATA["users"]:


        DATA["users"][uid] = {

            "id": user.id,

            "username": user.username or "",

            "name": user.first_name or "",

            "balance": 0,

            "referrer": None,

            "referrals": [],

            "phone": None,

            "created": datetime.now().isoformat()

        }


        save_data()



    return DATA["users"][uid]




# ==========================================
# BALANCE DOGS
# ==========================================

def get_balance(user_id):

    uid = str(user_id)


    if uid not in DATA["users"]:

        return 0


    return int(
        DATA["users"][uid].get(
            "balance",
            0
        )
    )




def add_balance(user_id, amount):

    uid = str(user_id)


    if uid not in DATA["users"]:

        return


    DATA["users"][uid]["balance"] += int(amount)


    save_data()




def remove_balance(user_id, amount):

    uid = str(user_id)


    if uid not in DATA["users"]:

        return False



    if DATA["users"][uid]["balance"] < int(amount):

        return False



    DATA["users"][uid]["balance"] -= int(amount)


    save_data()


    return True




def format_dogs(amount):

    return f"{int(amount):,} DOGS"

# ==========================================
# DOGS BOT - bot.py
# PART 2
# START + MENU + BALANCE
# ==========================================



# ==========================================
# MAIN KEYBOARD
# ==========================================

def main_keyboard(user_id):

    buttons = [

        [
            "💰 موجودی",
            "👤 پروفایل"
        ],

        [
            "🎮 بازی",
            "👥 زیرمجموعه"
        ],

        [
            "💳 واریزی",
            "💸 برداشت"
        ],

        [
            "🔄 انتقال"
        ]

    ]


    if int(user_id) == int(OWNER_ID):

        buttons.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )


    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )



# ==========================================
# START
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    create_user(user)


    await update.message.reply_text(

        "🐶 به ربات DOGS خوش آمدید\n\n"
        "از منوی زیر انتخاب کنید:",

        reply_markup=main_keyboard(user.id)

    )



# ==========================================
# BALANCE
# ==========================================

async def balance_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    create_user(user)


    balance = get_balance(
        user.id
    )


    await update.message.reply_text(

        "💰 موجودی شما:\n\n"
        f"{format_dogs(balance)}"

    )



# ==========================================
# PROFILE
# ==========================================

async def profile_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    info = create_user(user)



    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {user.id}\n"

        f"👤 نام: {user.first_name}\n"

        f"💰 موجودی: {format_dogs(info['balance'])}\n"

        f"👥 زیرمجموعه: {len(info['referrals'])}"

    )



# ==========================================
# TEXT ROUTER
# ==========================================

async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return


    text = update.message.text.strip()


    user = update.effective_user


    create_user(user)



    # موجودی در گروه و پیوی

    if text in [

        "موجودی",

        "موجودی من",

        "💰 موجودی"

    ]:

        await balance_message(
            update,
            context
        )

        return



    # پروفایل

    if text in [

        "پروفایل",

        "👤 پروفایل"

    ]:

        await profile_message(
            update,
            context
        )

        return



    # بازی

    if text == "🎮 بازی":

        await update.message.reply_text(

            "🎮 بازی DOGS\n\n"
            "برای شروع بنویس:\n\n"
            "بازی 500"

        )

        return

    # ==========================================
# DOGS BOT - bot.py
# PART 3
# GAME 500 DOGS
# ==========================================


WAITING_GAMES = {}



# تبدیل عدد فارسی به انگلیسی

def convert_number(text):

    nums = {
        "۰":"0",
        "۱":"1",
        "۲":"2",
        "۳":"3",
        "۴":"4",
        "۵":"5",
        "۶":"6",
        "۷":"7",
        "۸":"8",
        "۹":"9"
    }


    for fa,en in nums.items():

        text = text.replace(
            fa,
            en
        )


    return text




# گرفتن مبلغ بازی

def parse_game(text):

    text = convert_number(text)

    text = text.replace(
        ",",
        ""
    )


    result = re.match(
        r"^بازی\s+(\d+)$",
        text
    )


    if not result:

        return None


    amount = int(
        result.group(1)
    )


    if amount < MIN_GAME:

        return None


    return amount




# شروع بازی

async def game_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    amount = parse_game(
        update.message.text
    )


    if amount is None:

        return



    create_user(user)



    if get_balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست\n\n"
            f"مبلغ بازی: {format_dogs(amount)}"

        )

        return



    remove_balance(
        user.id,
        amount
    )



    game_id = str(
        random.randint(
            100000,
            999999
        )
    )



    WAITING_GAMES[game_id] = {

        "owner": user.id,

        "amount": amount

    }



    keyboard = InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(

                    "🎮 بازی با دوستان",

                    callback_data=f"join_game:{game_id}"

                )

            ],

            [

                InlineKeyboardButton(

                    "❌ لغو",

                    callback_data=f"cancel_game:{game_id}"

                )

            ]

        ]

    )



    await update.message.reply_text(

        "🎮 بازی DOGS ساخته شد\n\n"

        f"💰 مبلغ: {format_dogs(amount)}\n\n"

        "منتظر بازیکن دوم باشید.",

        reply_markup=keyboard

    )





# دکمه‌های بازی

async def game_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    user = query.from_user


    data = query.data



    # لغو بازی

    if data.startswith(
        "cancel_game:"
    ):

        game_id = data.split(":")[1]


        game = WAITING_GAMES.get(
            game_id
        )


        if not game:

            return



        if game["owner"] != user.id:

            await query.answer(
                "این بازی برای شما نیست",
                show_alert=True
            )

            return



        add_balance(

            user.id,

            game["amount"]

        )


        del WAITING_GAMES[game_id]


        await query.edit_message_text(

            "❌ بازی لغو شد\n\n"
            "💰 مبلغ برگشت داده شد."

        )

        return




    # ورود دوست

    if data.startswith(
        "join_game:"
    ):


        game_id = data.split(":")[1]


        game = WAITING_GAMES.get(
            game_id
        )


        if not game:

            return



        if game["owner"] == user.id:

            await query.answer(

                "نمی‌توانی با خودت بازی کنی",

                show_alert=True

            )

            return



        if get_balance(user.id) < game["amount"]:

            await query.answer(

                "موجودی کافی نیست",

                show_alert=True

            )

            return



        remove_balance(

            user.id,

            game["amount"]

        )



        player1 = game["owner"]

        player2 = user.id



        winner = random.choice(

            [
                player1,
                player2
            ]

        )



        prize = game["amount"] * 2



        add_balance(

            winner,

            prize

        )



        del WAITING_GAMES[game_id]



        await query.edit_message_text(

            "🎮 بازی تمام شد\n\n"

            f"🏆 برنده: {winner}\n"

            f"🎁 جایزه: {format_dogs(prize)}"

        )

# ==========================================
# DOGS BOT - bot.py
# PART 4
# TRANSFER DOGS
# ==========================================



def save_transfer(
    sender,
    receiver,
    amount
):

    DATA["transfers"][str(datetime.now().timestamp())] = {

        "from": sender,

        "to": receiver,

        "amount": amount,

        "time": datetime.now().isoformat()

    }


    save_data()




# ==========================================
# TRANSFER COMMAND
# ==========================================

async def transfer_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    create_user(user)


    target_id = None

    amount = None



    # انتقال با ریپلای

    if update.message.reply_to_message:


        target_id = update.message.reply_to_message.from_user.id


        if context.args:

            try:

                amount = int(
                    convert_number(
                        context.args[0]
                    )
                )

            except:

                pass



    # انتقال با آیدی

    elif len(context.args) >= 2:


        try:

            target_id = int(
                context.args[0]
            )


            amount = int(
                convert_number(
                    context.args[1]
                )
            )


        except:

            pass




    if target_id is None or amount is None:


        await update.message.reply_text(

            "❌ روش استفاده:\n\n"

            "روی پیام کاربر ریپلای کن:\n"

            "انتقال 500\n\n"

            "یا:\n"

            "انتقال آیدی مبلغ"

        )

        return




    if target_id == user.id:


        await update.message.reply_text(

            "❌ نمی‌توانید به خودتان انتقال دهید."

        )

        return




    if amount <= 0:


        await update.message.reply_text(

            "❌ مبلغ اشتباه است."

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




    create_user(

        type(
            "User",
            (),
            {
                "id": target_id,
                "username": "",
                "first_name": ""
            }
        )()

    )



    add_balance(

        target_id,

        amount

    )



    save_transfer(

        user.id,

        target_id,

        amount

    )




    await update.message.reply_text(

        "✅ انتقال انجام شد\n\n"

        f"👤 گیرنده: {target_id}\n"

        f"💰 مبلغ: {format_dogs(amount)}\n\n"

        f"موجودی جدید: {format_dogs(get_balance(user.id))}"

    )

# ==========================================
# DOGS BOT - bot.py
# PART 5
# REFERRAL SYSTEM
# ==========================================



# ==========================================
# GET REF REWARD
# ==========================================

def get_ref_reward():

    return int(
        DATA["settings"].get(
            "ref_reward",
            DEFAULT_REF_REWARD
        )
    )



def set_ref_reward(amount):

    DATA["settings"]["ref_reward"] = int(amount)

    save_data()



# ==========================================
# ADD REFERRAL
# ==========================================

def add_referral(
    new_user_id,
    referrer_id
):

    new_id = str(new_user_id)

    ref_id = str(referrer_id)



    if new_id == ref_id:

        return False



    if new_id not in DATA["users"]:

        return False



    user = DATA["users"][new_id]



    # قبلاً معرف داشته

    if user.get("referrer"):

        return False




    if ref_id not in DATA["users"]:

        return False



    user["referrer"] = int(ref_id)



    if new_id not in [
        str(x)
        for x in DATA["users"][ref_id]["referrals"]
    ]:

        DATA["users"][ref_id]["referrals"].append(
            int(new_id)
        )



    reward = get_ref_reward()



    add_balance(

        int(ref_id),

        reward

    )



    save_data()


    return True




# ==========================================
# REFERRAL COMMAND
# ==========================================

async def referral_command(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    user = update.effective_user


    create_user(user)



    bot = await context.bot.get_me()



    link = (

        f"https://t.me/"
        f"{bot.username}"
        f"?start={user.id}"

    )



    refs = len(

        DATA["users"][str(user.id)]["referrals"]

    )



    await update.message.reply_text(

        "👥 زیرمجموعه DOGS\n\n"

        f"🔗 لینک دعوت شما:\n{link}\n\n"

        f"👥 تعداد دعوت‌ها: {refs}\n"

        f"🎁 جایزه هر نفر: {format_dogs(get_ref_reward())}"

    )

# ==========================================
# DOGS BOT - bot.py
# PART 6
# DEPOSIT + WITHDRAW
# ==========================================



# ==========================================
# DEPOSIT START
# ==========================================

async def deposit_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)


    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"
        "مبلغ واریزی خود را ارسال کنید.\n\n"
        "مثال:\n"
        "1000"

    )


    context.user_data["deposit"] = True



# ==========================================
# DEPOSIT AMOUNT
# ==========================================

async def deposit_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get("deposit"):

        return


    try:

        amount = int(
            convert_number(
                update.message.text
            )
        )

    except:

        await update.message.reply_text(
            "❌ مبلغ صحیح نیست."
        )

        return



    if amount <= 0:

        await update.message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )

        return



    user = update.effective_user



    deposit_id = str(
        random.randint(
            100000,
            999999
        )
    )



    DATA["deposits"][deposit_id] = {

        "user": user.id,

        "amount": amount,

        "status": "pending",

        "time": datetime.now().isoformat()

    }



    save_data()



    context.user_data["deposit"] = False



    await update.message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💰 مبلغ: {format_dogs(amount)}\n"

        "⏳ منتظر بررسی مدیریت باشید."

    )





# ==========================================
# WITHDRAW START
# ==========================================

async def withdraw_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    create_user(user)



    await update.message.reply_text(

        "💸 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید."

    )



    context.user_data["withdraw"] = True





# ==========================================
# WITHDRAW AMOUNT
# ==========================================

async def withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get("withdraw"):

        return



    try:

        amount = int(
            convert_number(
                update.message.text
            )
        )

    except:

        await update.message.reply_text(
            "❌ مبلغ اشتباه است."
        )

        return



    user = update.effective_user



    if get_balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست."

        )

        return




    withdraw_id = str(
        random.randint(
            100000,
            999999
        )
    )



    DATA["withdraws"][withdraw_id] = {

        "user": user.id,

        "amount": amount,

        "status": "pending",

        "time": datetime.now().isoformat()

    }



    save_data()



    context.user_data["withdraw"] = False



    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: {format_dogs(amount)}\n"

        "⏳ منتظر تأیید مدیریت باشید."

    )
    # ==========================================
# DOGS BOT - bot.py
# PART 7
# ADMIN PANEL
# ==========================================



# ==========================================
# CHECK OWNER
# ==========================================

def is_owner(user_id):

    return int(user_id) == int(
        DATA["settings"]["owner_id"]
    )



# ==========================================
# ADMIN KEYBOARD
# ==========================================

def admin_keyboard():

    active = DATA["settings"].get(
        "bot_active",
        True
    )


    status = (
        "🔴 خاموش کردن ربات"
        if active
        else
        "🟢 روشن کردن ربات"
    )


    return InlineKeyboardMarkup(

        [

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
                    "🎁 تغییر جایزه زیرمجموعه",
                    callback_data="admin_reward"
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
                    status,
                    callback_data="admin_toggle"
                )

            ],

            [

                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_owner"
                )

            ]

        ]

    )





# ==========================================
# ADMIN COMMAND
# ==========================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    if not is_owner(user.id):

        await update.message.reply_text(
            "❌ فقط مالک دسترسی دارد."
        )

        return



    await update.message.reply_text(

        "⚙️ پنل مدیریت DOGS\n\n"
        "یک گزینه را انتخاب کنید:",

        reply_markup=admin_keyboard()

    )





# ==========================================
# ADMIN CALLBACK
# ==========================================

async def admin_callback(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):

    query = update.callback_query

    user = query.from_user



    if not is_owner(user.id):

        await query.answer(
            "دسترسی ندارید",
            show_alert=True
        )

        return



    data = query.data



    # روشن خاموش

    if data == "admin_toggle":


        current = DATA["settings"].get(
            "bot_active",
            True
        )


        DATA["settings"]["bot_active"] = not current


        save_data()


        await query.answer(
            "وضعیت تغییر کرد"
        )


        await query.edit_message_reply_markup(
            reply_markup=admin_keyboard()
        )


        return




    # آمار

    if data == "admin_stats":


        users = len(
            DATA["users"]
        )


        total = 0


        for u in DATA["users"].values():

            total += int(
                u.get(
                    "balance",
                    0
                )
            )


        await query.message.reply_text(

            "📊 آمار DOGS\n\n"

            f"👥 کاربران: {users}\n"

            f"💰 کل موجودی: {format_dogs(total)}"

        )


        return




    # تغییر جایزه

    if data == "admin_reward":


        context.user_data["admin_state"] = "reward"


        await query.message.reply_text(

            "🎁 مقدار جایزه جدید را ارسال کنید:\n\n"
            "مثال:\n"
            "500"

        )


        return
        # ==========================================
# DOGS BOT - bot.py
# PART 9
# OWNER TRANSFER
# ==========================================


# ==========================================
# START OWNER TRANSFER
# ==========================================

async def owner_transfer_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    if not is_owner(user.id):

        await update.message.reply_text(
            "❌ فقط مالک دسترسی دارد."
        )

        return



    context.user_data["admin_state"] = "owner_transfer"



    await update.message.reply_text(

        "👑 انتقال مالکیت\n\n"
        "آیدی عددی مالک جدید را ارسال کنید.\n\n"
        "مثال:\n"
        "123456789"

    )





# ==========================================
# OWNER TRANSFER PROCESS
# ==========================================

async def owner_transfer_process(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    state = context.user_data.get(
        "admin_state"
    )


    if state != "owner_transfer":

        return False



    try:

        new_owner = int(
            convert_number(
                update.message.text
            )
        )

    except:


        await update.message.reply_text(

            "❌ آیدی صحیح نیست."

        )

        return True




    DATA["settings"]["owner_id"] = new_owner

    save_data()



    context.user_data.pop(
        "admin_state",
        None
    )



    await update.message.reply_text(

        "✅ انتقال مالکیت انجام شد.\n\n"

        f"👑 مالک جدید:\n"
        f"{new_owner}"

    )


    return True

    # ==========================================
# DOGS BOT - bot.py
# PART 10
# ADMIN STATES
# ==========================================


async def admin_state_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return False

    # فقط مالک
    if not is_owner(user.id):
        return False

    state = context.user_data.get("admin_state")

    if not state:
        return False


    # ==========================================
    # CHANGE REFERRAL REWARD
    # ==========================================

    if state == "reward":

        try:
            amount = int(
                convert_number(
                    update.message.text.strip()
                ).replace(",", "")
            )

        except ValueError:

            await update.message.reply_text(
                "❌ مبلغ وارد شده صحیح نیست.\n\n"
                "مثال:\n"
                "500"
            )

            return True


        if amount < 0:

            await update.message.reply_text(
                "❌ مبلغ نمی‌تواند منفی باشد."
            )

            return True


        set_ref_reward(amount)

        context.user_data.pop(
            "admin_state",
            None
        )


        await update.message.reply_text(

            "✅ جایزه زیرمجموعه تغییر کرد.\n\n"
            f"🎁 جایزه جدید: {format_dogs(amount)}",

            reply_markup=main_keyboard(user.id)

        )

        return True


    # ==========================================
    # OWNER TRANSFER
    # ==========================================

    if state == "owner_transfer":

        try:

            new_owner = int(
                convert_number(
                    update.message.text.strip()
                )
            )

        except ValueError:

            await update.message.reply_text(
                "❌ آیدی عددی صحیح نیست."
            )

            return True


        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )

            return True


        # انتقال مستقیم مالکیت
        DATA["settings"]["owner_id"] = new_owner

        save_data()


        context.user_data.pop(
            "admin_state",
            None
        )


        await update.message.reply_text(

            "✅ انتقال مالکیت انجام شد.\n\n"
            f"👑 مالک جدید: `{new_owner}`\n\n"
            "⚠️ مالک قبلی دیگر دسترسی مدیریت ندارد.",

            parse_mode="Markdown"

        )

        return True


    return False

    # ==========================================
# DOGS BOT - bot.py
# PART 11
# CORE HELPERS
# ==========================================

import re
import time
import traceback


# ==========================================
# NUMBER CONVERTER
# ==========================================

def convert_number(value):

    if value is None:
        return ""

    value = str(value)

    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )

    return value.translate(table).replace(",", "").replace("٬", "").strip()


# ==========================================
# DOGS FORMAT
# ==========================================

def format_dogs(amount):

    try:
        amount = int(amount)
    except Exception:
        amount = 0

    return f"{amount:,} DOGS"


# ==========================================
# REFERRAL REWARD
# ==========================================

def get_ref_reward():

    try:
        return int(
            DATA["settings"].get(
                "referral_reward",
                DEFAULT_REFERRAL_REWARD
            )
        )

    except Exception:
        return DEFAULT_REFERRAL_REWARD


def set_ref_reward(amount):

    amount = max(
        0,
        int(amount)
    )

    DATA["settings"]["referral_reward"] = amount

    save_data()


# ==========================================
# BOT ACTIVE
# ==========================================

def bot_active():

    return bool(
        DATA["settings"].get(
            "bot_enabled",
            True
        )
    )


def set_bot_active(value):

    DATA["settings"]["bot_enabled"] = bool(value)

    save_data()


# ==========================================
# OWNER ID
# ==========================================

def get_owner_id():

    try:

        return int(
            DATA["settings"].get(
                "owner_id",
                OWNER_ID
            )
        )

    except Exception:

        return int(OWNER_ID)


# ==========================================
# UPDATE OWNER CHECK
# ==========================================

def is_owner(user_id):

    try:

        return int(user_id) == get_owner_id()

    except Exception:

        return False


# ==========================================
# USER CREATOR
# ==========================================

def create_user(user):

    if not user:
        return None

    user_id = str(user.id)

    if user_id not in DATA["users"]:

        DATA["users"][user_id] = {

            "id": user.id,

            "name": (
                user.first_name
                or ""
            ),

            "username": (
                user.username
                or ""
            ),

            "phone": None,

            "phone_verified": False,

            "balance": 0,

            "referrer": None,

            "refs": 0,

            "referrals": [],

            "referral_rewarded": False,

            "created_at":
                datetime.now().isoformat()

        }

        save_data()

        return DATA["users"][user_id]


    # اطلاعات کاربر موجود را به‌روز کن

    DATA["users"][user_id]["name"] = (
        user.first_name
        or DATA["users"][user_id].get(
            "name",
            ""
        )
    )

    DATA["users"][user_id]["username"] = (
        user.username
        or DATA["users"][user_id].get(
            "username",
            ""
        )
    )

    return DATA["users"][user_id]


# ==========================================
# SAVE DATA SAFE
# ==========================================

def save_data():

    temp = DATA_FILE + ".tmp"

    try:

        with open(
            temp,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                DATA,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp,
            DATA_FILE
        )

    except Exception as error:

        print(
            "SAVE DATA ERROR:",
            repr(error)
        )

        try:

            if os.path.exists(temp):
                os.remove(temp)

        except Exception:
            pass


# ==========================================
# BALANCE
# ==========================================

def get_balance(user_id):

    user_id = str(user_id)

    if user_id not in DATA["users"]:

        return 0

    try:

        return int(
            DATA["users"][user_id].get(
                "balance",
                0
            )
        )

    except Exception:

        return 0


def set_balance(user_id, amount):

    user_id = str(user_id)

    if user_id not in DATA["users"]:

        DATA["users"][user_id] = {

            "id": int(user_id),

            "balance": 0,

            "refs": 0,

            "referrer": None,

            "phone_verified": False

        }


    DATA["users"][user_id]["balance"] = max(
        0,
        int(amount)
    )

    save_data()


def add_balance(user_id, amount):

    amount = int(amount)

    if amount <= 0:
        return

    set_balance(
        user_id,
        get_balance(user_id) + amount
    )


def remove_balance(user_id, amount):

    amount = int(amount)

    current = get_balance(user_id)

    if amount <= 0:
        return False

    if current < amount:
        return False

    set_balance(
        user_id,
        current - amount
    )

    return True


# ==========================================
# ANTI SPAM
# ==========================================

ANTI_SPAM = {}


def anti_spam(user_id):

    now = time.time()

    old = ANTI_SPAM.get(
        user_id,
        0
    )

    if now - old < 0.7:

        return False

    ANTI_SPAM[user_id] = now

    return True


# ==========================================
# USER STATE
# ==========================================

STATE = {}


def clear_state(user_id):

    STATE.pop(
        int(user_id),
        None
    )

    return True


# ==========================================
# WAITING GAMES
# ==========================================

WAITING_GAMES = {}


# ==========================================
# REQUIRE ACCESS
# ==========================================

async def require_access(
    update,
    context
):

    user = update.effective_user

    if not user:
        return False


    if is_owner(user.id):
        return True


    if not bot_active():

        if update.effective_message:

            await update.effective_message.reply_text(
                "🔴 ربات در حال حاضر خاموش است."
            )

        return False


    return True

    # ==========================================
# DOGS BOT - bot.py
# PART 12
# GAME 500 - FRIENDS
# ==========================================

GAME_MIN_AMOUNT = 500

WAITING_GAMES = {}


# ==========================================
# CREATE GAME
# ==========================================

async def game_command(update, context):

    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    create_user(user)

    text = message.text or ""

    parts = text.strip().split()

    if len(parts) != 2:
        return

    if parts[0] != "بازی":
        return

    try:
        amount = int(
            convert_number(parts[1])
        )
    except Exception:
        await message.reply_text(
            "❌ مبلغ بازی صحیح نیست."
        )
        return

    if amount < GAME_MIN_AMOUNT:
        await message.reply_text(
            "❌ حداقل مبلغ بازی "
            f"{GAME_MIN_AMOUNT:,} DOGS است."
        )
        return

    # جلوگیری از ساخت چند بازی همزمان
    for game in WAITING_GAMES.values():

        if int(game["creator_id"]) == user.id:

            await message.reply_text(
                "❌ شما یک بازی در انتظار دارید."
            )

            return

    balance = get_balance(user.id)

    if balance < amount:

        await message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: "
            f"{format_dogs(balance)}\n"

            f"🎯 مبلغ بازی: "
            f"{format_dogs(amount)}"

        )

        return

    # کسر مبلغ

    if not remove_balance(
        user.id,
        amount
    ):

        await message.reply_text(
            "❌ خطا در کسر مبلغ."
        )

        return

    game_id = str(
        random.randint(
            100000,
            999999
        )
    )

    WAITING_GAMES[game_id] = {

        "creator_id": user.id,

        "creator_name": (
            user.first_name
            or "کاربر"
        ),

        "amount": amount,

        "message_id": message.message_id,

        "chat_id": message.chat_id,

        "created_at": time.time()

    }

    await message.reply_text(

        "🎮 بازی ۵۰۰\n\n"

        f"👤 سازنده: "
        f"{user.first_name or 'کاربر'}\n"

        f"💰 مبلغ بازی: "
        f"{format_dogs(amount)}\n\n"

        "یک نفر می‌تواند وارد بازی شود.",

        reply_markup=waiting_game_keyboard(
            game_id
        )

    )


# ==========================================
# GAME JOIN
# ==========================================

async def game_join_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    create_user(user)

    game_id = query.data.split(
        ":",
        1
    )[1]

    game = WAITING_GAMES.get(
        game_id
    )

    if not game:

        await query.message.reply_text(
            "❌ این بازی دیگر فعال نیست."
        )

        return

    creator_id = int(
        game["creator_id"]
    )

    amount = int(
        game["amount"]
    )

    # سازنده نمی‌تواند خودش وارد شود

    if user.id == creator_id:

        await query.answer(
            "❌ نمی‌توانی وارد بازی خودت شوی.",
            show_alert=True
        )

        return

    # موجودی نفر دوم

    if get_balance(user.id) < amount:

        await query.answer(
            "❌ موجودی کافی نیست.",
            show_alert=True
        )

        return

    # کسر مبلغ نفر دوم

    if not remove_balance(
        user.id,
        amount
    ):

        await query.answer(
            "❌ خطا در ثبت مبلغ.",
            show_alert=True
        )

        return

    # حذف بازی انتظار

    WAITING_GAMES.pop(
        game_id,
        None
    )

    # ==========================================
    # RANDOM RESULT
    # ==========================================

    creator_score = random.randint(
        1,
        100
    )

    joiner_score = random.randint(
        1,
        100
    )

    # مساوی

    if creator_score == joiner_score:

        # مبلغ هر دو نفر برگردد

        add_balance(
            creator_id,
            amount
        )

        add_balance(
            user.id,
            amount
        )

        result_text = (

            "🤝 بازی مساوی شد.\n\n"

            f"👤 امتیاز سازنده: "
            f"{creator_score}\n"

            f"👤 امتیاز شما: "
            f"{joiner_score}\n\n"

            "💰 مبلغ هر دو نفر برگشت داده شد."

        )

        creator_text = (

            "🤝 بازی شما مساوی شد.\n\n"

            f"👤 امتیاز شما: "
            f"{creator_score}\n"

            f"👤 امتیاز حریف: "
            f"{joiner_score}\n\n"

            "💰 مبلغ بازی به شما برگشت."

        )

    else:

        total = amount * 2

        if creator_score > joiner_score:

            winner_id = creator_id

            winner_score = creator_score

            loser_score = joiner_score

        else:

            winner_id = user.id

            winner_score = joiner_score

            loser_score = creator_score

        # جایزه به برنده

        add_balance(
            winner_id,
            total
        )

        if winner_id == user.id:

            result_text = (

                "🎉 شما برنده شدید!\n\n"

                f"👤 امتیاز شما: "
                f"{winner_score}\n"

                f"👤 امتیاز حریف: "
                f"{loser_score}\n\n"

                f"🏆 جایزه: "
                f"{format_dogs(total)}"

            )

            creator_text = (

                "😔 شما باختید.\n\n"

                f"👤 امتیاز شما: "
                f"{loser_score}\n"

                f"👤 امتیاز حریف: "
                f"{winner_score}\n\n"

                f"❌ مبلغ بازی: "
                f"{format_dogs(amount)}"

            )

        else:

            result_text = (

                "😔 شما باختید.\n\n"

                f"👤 امتیاز شما: "
                f"{loser_score}\n"

                f"👤 امتیاز حریف: "
                f"{winner_score}\n\n"

                f"❌ مبلغ بازی: "
                f"{format_dogs(amount)}"

            )

            creator_text = (

                "🎉 شما برنده شدید!\n\n"

                f"👤 امتیاز شما: "
                f"{winner_score}\n"

                f"👤 امتیاز حریف: "
                f"{loser_score}\n\n"

                f"🏆 جایزه: "
                f"{format_dogs(total)}"

            )

    # ==========================================
    # RESULT TO JOINER
    # ==========================================

    try:

        await context.bot.send_message(

            chat_id=user.id,

            text=(
                "🎮 نتیجه بازی ۵۰۰\n\n"
                + result_text
            )

        )

    except Exception as error:

        print(
            "JOINER RESULT ERROR:",
            repr(error)
        )

    # ==========================================
    # RESULT TO CREATOR
    # ==========================================

    try:

        await context.bot.send_message(

            chat_id=creator_id,

            text=(
                "🎮 نتیجه بازی ۵۰۰\n\n"
                + creator_text
            )

        )

    except Exception as error:

        print(
            "CREATOR RESULT ERROR:",
            repr(error)
        )

    # پیام گپ

    try:

        await query.message.edit_text(

            "🎮 بازی ۵۰۰ تمام شد.\n\n"
            "📩 نتیجه برای هر دو بازیکن "
            "در پیوی ارسال شد."

        )

    except Exception:

        pass


# ==========================================
# CANCEL GAME
# ==========================================

async def game_cancel_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    game_id = query.data.split(
        ":",
        1
    )[1]

    game = WAITING_GAMES.get(
        game_id
    )

    if not game:

        await query.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    creator_id = int(
        game["creator_id"]
    )

    if user.id != creator_id:

        await query.answer(
            "❌ فقط سازنده بازی می‌تواند آن را لغو کند.",
            show_alert=True
        )

        return

    amount = int(
        game["amount"]
    )

    # حذف بازی

    WAITING_GAMES.pop(
        game_id,
        None
    )

    # برگشت مبلغ

    add_balance(
        creator_id,
        amount
    )

    try:

        await query.message.edit_text(

            "❌ بازی لغو شد.\n\n"

            f"↩️ مبلغ "
            f"{format_dogs(amount)} "
            "به سازنده برگشت داده شد."

        )

    except Exception:

        await query.message.reply_text(

            "❌ بازی لغو شد.\n\n"

            f"↩️ مبلغ "
            f"{format_dogs(amount)} "
            "برگشت داده شد."

        )

        # ==========================================
# DOGS BOT - bot.py
# PART 13
# TRANSFER DOGS
# ==========================================


# ==========================================
# TRANSFER BY TEXT
# ==========================================

async def transfer_text(
    update,
    context
):

    message = update.effective_message
    sender = update.effective_user

    if not message or not sender:
        return


    create_user(sender)


    target_id = None
    amount = None


    # ==========================================
    # TRANSFER BY REPLY
    # ==========================================

    if message.reply_to_message:

        target_user = (
            message.reply_to_message
            .from_user
        )

        if not target_user:
            return

        target_id = target_user.id

        parts = message.text.strip().split()

        if len(parts) < 2:

            await message.reply_text(

                "❌ مبلغ را وارد کنید.\n\n"
                "مثال:\n"
                "انتقال 500"

            )

            return

        try:

            amount = int(
                convert_number(
                    parts[1]
                )
            )

        except Exception:

            await message.reply_text(
                "❌ مبلغ صحیح نیست."
            )

            return


    # ==========================================
    # TRANSFER BY ID
    # ==========================================

    else:

        parts = message.text.strip().split()

        if len(parts) < 3:

            await message.reply_text(

                "❌ فرمت صحیح:\n\n"
                "انتقال آیدی مبلغ\n\n"
                "مثال:\n"
                "انتقال 123456789 500"

            )

            return


        try:

            target_id = int(
                convert_number(
                    parts[1]
                )
            )

            amount = int(
                convert_number(
                    parts[2]
                )
            )

        except Exception:

            await message.reply_text(
                "❌ آیدی یا مبلغ صحیح نیست."
            )

            return


    # ==========================================
    # VALIDATION
    # ==========================================

    if target_id == sender.id:

        await message.reply_text(
            "❌ نمی‌توانی به خودت DOGS انتقال بدهی."
        )

        return


    if amount <= 0:

        await message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )

        return


    sender_balance = get_balance(
        sender.id
    )


    if sender_balance < amount:

        await message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{format_dogs(sender_balance)}\n"

            f"💸 مبلغ انتقال: "
            f"{format_dogs(amount)}"

        )

        return


    # ==========================================
    # CREATE TARGET USER
    # ==========================================

    if str(target_id) not in DATA["users"]:

        DATA["users"][str(target_id)] = {

            "id": target_id,

            "name": "کاربر",

            "username": "",

            "phone": None,

            "phone_verified": False,

            "balance": 0,

            "referrer": None,

            "refs": 0,

            "referrals": [],

            "referral_rewarded": False,

            "created_at":
                datetime.now().isoformat()

        }

        save_data()


    # ==========================================
    # TRANSFER
    # ==========================================

    if not remove_balance(
        sender.id,
        amount
    ):

        await message.reply_text(
            "❌ انتقال انجام نشد."
        )

        return


    add_balance(
        target_id,
        amount
    )


    # ==========================================
    # SENDER MESSAGE
    # ==========================================

    await message.reply_text(

        "✅ انتقال با موفقیت انجام شد.\n\n"

        f"👤 گیرنده: `{target_id}`\n"

        f"💸 مبلغ: "
        f"{format_dogs(amount)}\n"

        f"💰 موجودی جدید شما: "
        f"{format_dogs(get_balance(sender.id))}",

        parse_mode="Markdown"

    )


    # ==========================================
    # NOTIFY RECEIVER
    # ==========================================

    try:

        await context.bot.send_message(

            chat_id=target_id,

            text=(

                "💰 انتقال DOGS\n\n"

                "🎉 یک انتقال برای شما ثبت شد.\n\n"

                f"💸 مبلغ دریافتی: "
                f"{format_dogs(amount)}\n"

                f"💰 موجودی جدید: "
                f"{format_dogs(get_balance(target_id))}"

            )

        )

    except Exception as error:

        print(
            "TRANSFER NOTIFY ERROR:",
            repr(error)
        )


# ==========================================
# TRANSFER START
# ==========================================

async def transfer_start(
    update,
    context
):

    await update.effective_message.reply_text(

        "🔄 انتقال DOGS\n\n"

        "می‌توانی به دو روش انتقال بدهی:\n\n"

        "1️⃣ با ریپلای:\n"
        "روی پیام کاربر ریپلای کن و بنویس:\n"
        "انتقال 500\n\n"

        "2️⃣ با آیدی:\n"
        "انتقال 123456789 500",

        reply_markup=back_keyboard()

    )

    # ==========================================
# DOGS BOT - bot.py
# PART 14
# DEPOSIT / WITHDRAW ADMIN CALLBACK
# ==========================================


# ==========================================
# ADMIN REQUEST KEYBOARD
# ==========================================

def request_keyboard(request_type, request_id):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"{request_type}_ok:{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"{request_type}_no:{request_id}"
                )
            ]
        ]
    )


# ==========================================
# SEND DEPOSIT REQUEST TO OWNER
# ==========================================

async def send_deposit_to_owner(
    context,
    request_id
):

    request = DATA["deposits"].get(
        request_id
    )

    if not request:
        return

    user_id = int(
        request["user"]
    )

    amount = int(
        request["amount"]
    )

    await context.bot.send_message(

        chat_id=get_owner_id(),

        text=(
            "💳 درخواست واریز DOGS\n\n"

            f"🆔 کاربر: `{user_id}`\n"

            f"💰 مبلغ: "
            f"{format_dogs(amount)}\n\n"

            "وضعیت: ⏳ در انتظار بررسی"
        ),

        parse_mode="Markdown",

        reply_markup=request_keyboard(
            "dep",
            request_id
        )

    )


# ==========================================
# SEND WITHDRAW REQUEST TO OWNER
# ==========================================

async def send_withdraw_to_owner(
    context,
    request_id
):

    request = DATA["withdraws"].get(
        request_id
    )

    if not request:
        return

    user_id = int(
        request["user"]
    )

    amount = int(
        request["amount"]
    )

    await context.bot.send_message(

        chat_id=get_owner_id(),

        text=(
            "💸 درخواست برداشت DOGS\n\n"

            f"🆔 کاربر: `{user_id}`\n"

            f"💰 مبلغ: "
            f"{format_dogs(amount)}\n\n"

            "وضعیت: ⏳ در انتظار بررسی"
        ),

        reply_markup=request_keyboard(
            "with",
            request_id
        )

    )


# ==========================================
# DEPOSIT / WITHDRAW CALLBACK
# ==========================================

async def deposit_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    value = query.data

    # ==========================================
    # DEPOSIT APPROVE
    # ==========================================

    if value.startswith("dep_ok:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = DATA["deposits"].get(
            request_id
        )

        if not request:

            await query.message.reply_text(
                "❌ درخواست پیدا نشد."
            )

            return

        if request.get("status") != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        target_id = int(
            request["user"]
        )

        amount = int(
            request["amount"]
        )

        add_balance(
            target_id,
            amount
        )

        request["status"] = "approved"

        request["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "✅ واریز تأیید شد."
        )

        try:

            await context.bot.send_message(

                chat_id=target_id,

                text=(
                    "✅ واریز شما تأیید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{format_dogs(amount)}\n"

                    f"💳 موجودی جدید: "
                    f"{format_dogs(get_balance(target_id))}"
                )

            )

        except Exception as error:

            print(
                "DEPOSIT USER NOTIFY ERROR:",
                repr(error)
            )

        return


    # ==========================================
    # DEPOSIT REJECT
    # ==========================================

    if value.startswith("dep_no:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = DATA["deposits"].get(
            request_id
        )

        if not request:
            return

        if request.get("status") != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        target_id = int(
            request["user"]
        )

        amount = int(
            request["amount"]
        )

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "❌ درخواست واریز رد شد."
        )

        try:

            await context.bot.send_message(

                chat_id=target_id,

                text=(
                    "❌ درخواست واریز شما رد شد.\n\n"

                    f"💰 مبلغ درخواست: "
                    f"{format_dogs(amount)}"
                )

            )

        except Exception as error:

            print(
                "DEPOSIT REJECT NOTIFY ERROR:",
                repr(error)
            )

        return


# ==========================================
# WITHDRAW CALLBACK
# ==========================================

async def withdraw_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    value = query.data


    # ==========================================
    # WITHDRAW APPROVE
    # ==========================================

    if value.startswith("with_ok:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = DATA["withdraws"].get(
            request_id
        )

        if not request:
            return

        if request.get("status") != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        target_id = int(
            request["user"]
        )

        amount = int(
            request["amount"]
        )

        # مبلغ هنگام ثبت درخواست
        # از موجودی کسر نشده؛ اینجا کسر می‌شود

        if get_balance(target_id) < amount:

            request["status"] = "rejected"

            request["reason"] = (
                "موجودی هنگام تأیید کافی نبود."
            )

            save_data()

            await query.message.reply_text(
                "❌ موجودی کاربر برای برداشت کافی نیست."
            )

            return

        remove_balance(
            target_id,
            amount
        )

        request["status"] = "approved"

        request["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "✅ برداشت تأیید شد."
        )

        try:

            await context.bot.send_message(

                chat_id=target_id,

                text=(
                    "✅ درخواست برداشت شما تأیید شد.\n\n"

                    f"💸 مبلغ: "
                    f"{format_dogs(amount)}\n"

                    f"💰 موجودی جدید: "
                    f"{format_dogs(get_balance(target_id))}"
                )

            )

        except Exception as error:

            print(
                "WITHDRAW USER NOTIFY ERROR:",
                repr(error)
            )

        return


    # ==========================================
    # WITHDRAW REJECT
    # ==========================================

    if value.startswith("with_no:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = DATA["withdraws"].get(
            request_id
        )

        if not request:
            return

        if request.get("status") != "pending":

            await query.answer(
                "این درخواست قبلاً بررسی شده.",
                show_alert=True
            )

            return

        target_id = int(
            request["user"]
        )

        amount = int(
            request["amount"]
        )

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(
            "❌ درخواست برداشت رد شد."
        )

        try:

            await context.bot.send_message(

                chat_id=target_id,

                text=(
                    "❌ درخواست برداشت شما رد شد.\n\n"

                    f"💸 مبلغ درخواست: "
                    f"{format_dogs(amount)}"
                )

            )

        except Exception as error:

            print(
                "WITHDRAW REJECT NOTIFY ERROR:",
                repr(error)
            )

        return

        # ==========================================
# DOGS BOT - bot.py
# PART 15
# DEPOSIT / WITHDRAW FLOW
# ==========================================


# ==========================================
# DEPOSIT START
# ==========================================

async def deposit_start(update, context):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data["state"] = "deposit_amount"

    await update.effective_message.reply_text(

        "💳 واریزی DOGS\n\n"

        "مبلغ واریزی را به صورت عدد ارسال کنید.\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()

    )


# ==========================================
# DEPOSIT AMOUNT
# ==========================================

async def deposit_amount(update, context):

    user = update.effective_user

    if not user:
        return

    try:

        amount = int(
            convert_number(
                update.effective_message.text
            )
        )

    except Exception:

        await update.effective_message.reply_text(
            "❌ مبلغ صحیح نیست."
        )

        return


    if amount <= 0:

        await update.effective_message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )

        return


    request_id = str(
        random.randint(
            100000,
            999999
        )
    )


    while request_id in DATA["deposits"]:

        request_id = str(
            random.randint(
                100000,
                999999
            )
        )


    DATA["deposits"][request_id] = {

        "id": request_id,

        "user": user.id,

        "amount": amount,

        "status": "pending",

        "created_at":
            datetime.now().isoformat()

    }


    save_data()


    context.user_data.pop(
        "state",
        None
    )


    await update.effective_message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💰 مبلغ: {format_dogs(amount)}\n"

        f"🧾 کد درخواست: `{request_id}`\n\n"

        "⏳ درخواست شما برای مدیریت ارسال شد.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(user.id)

    )


    # ارسال به مالک

    try:

        await send_deposit_to_owner(

            context,

            request_id

        )

    except Exception as error:

        print(
            "SEND DEPOSIT OWNER ERROR:",
            repr(error)
        )


# ==========================================
# WITHDRAW START
# ==========================================

async def withdraw_start(update, context):

    user = update.effective_user

    if not user:
        return

    create_user(user)


    balance = get_balance(
        user.id
    )


    if balance <= 0:

        await update.effective_message.reply_text(

            "❌ موجودی شما برای برداشت کافی نیست.\n\n"

            f"💰 موجودی: "
            f"{format_dogs(balance)}"

        )

        return


    context.user_data["state"] = (
        "withdraw_amount"
    )


    await update.effective_message.reply_text(

        "💸 برداشت DOGS\n\n"

        "مبلغ برداشت را ارسال کنید.\n\n"

        f"💰 موجودی شما: "
        f"{format_dogs(balance)}",

        reply_markup=back_keyboard()

    )


# ==========================================
# WITHDRAW AMOUNT
# ==========================================

async def withdraw_amount(update, context):

    user = update.effective_user

    if not user:
        return


    try:

        amount = int(
            convert_number(
                update.effective_message.text
            )
        )

    except Exception:

        await update.effective_message.reply_text(
            "❌ مبلغ صحیح نیست."
        )

        return


    if amount <= 0:

        await update.effective_message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )

        return


    if get_balance(user.id) < amount:

        await update.effective_message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: "
            f"{format_dogs(get_balance(user.id))}\n"

            f"💸 درخواست: "
            f"{format_dogs(amount)}"

        )

        return


    context.user_data["withdraw_amount"] = amount

    context.user_data["state"] = (
        "withdraw_target"
    )


    await update.effective_message.reply_text(

        "💳 مقصد برداشت را ارسال کنید.\n\n"

        "می‌توانید آیدی عددی یا اطلاعات مقصد "
        "خود را ارسال کنید.\n\n"

        "مثال:\n"
        "123456789",

        reply_markup=back_keyboard()

    )


# ==========================================
# WITHDRAW TARGET
# ==========================================

async def withdraw_target(update, context):

    user = update.effective_user

    if not user:
        return


    amount = context.user_data.get(
        "withdraw_amount"
    )


    if not amount:

        context.user_data.pop(
            "state",
            None
        )

        return


    target = (
        update.effective_message.text
        or ""
    ).strip()


    if not target:

        await update.effective_message.reply_text(
            "❌ مقصد برداشت را وارد کنید."
        )

        return


    request_id = str(
        random.randint(
            100000,
            999999
        )
    )


    while request_id in DATA["withdraws"]:

        request_id = str(
            random.randint(
                100000,
                999999
            )
        )


    DATA["withdraws"][request_id] = {

        "id": request_id,

        "user": user.id,

        "amount": int(amount),

        "target": target,

        "status": "pending",

        "created_at":
            datetime.now().isoformat()

    }


    save_data()


    context.user_data.pop(
        "state",
        None
    )

    context.user_data.pop(
        "withdraw_amount",
        None
    )


    await update.effective_message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💸 مبلغ: "
        f"{format_dogs(amount)}\n"

        f"📍 مقصد: {target}\n"

        f"🧾 کد درخواست: `{request_id}`\n\n"

        "⏳ منتظر بررسی مدیریت باشید.",

        parse_mode="Markdown",

        reply_markup=main_keyboard(user.id)

    )


    # ارسال درخواست برای مالک

    try:

        await send_withdraw_to_owner(

            context,

            request_id

        )

    except Exception as error:

        print(
            "SEND WITHDRAW OWNER ERROR:",
            repr(error)
        )

        # ==========================================
# DOGS BOT - bot.py
# PART 16
# REFERRAL SYSTEM
# ==========================================


# ==========================================
# REFERRAL REWARD
# ==========================================

def get_referral_reward():

    try:

        return int(
            DATA.get(
                "settings",
                {}
            ).get(
                "referral_reward",
                DEFAULT_REFERRAL_REWARD
            )
        )

    except Exception:

        return DEFAULT_REFERRAL_REWARD


def set_referral_reward(amount):

    amount = max(
        0,
        int(amount)
    )

    if "settings" not in DATA:
        DATA["settings"] = {}

    DATA["settings"][
        "referral_reward"
    ] = amount

    save_data()


# ==========================================
# REFERRAL COUNT
# ==========================================

def referral_count(user_id):

    user = ensure_user(
        user_id
    )

    referrals = user.get(
        "referrals",
        []
    )

    if isinstance(
        referrals,
        list
    ):

        return len(referrals)

    return int(
        referrals or 0
    )


# ==========================================
# ADD REFERRAL
# ==========================================

def register_referral(
    referrer_id,
    new_user_id
):

    referrer_id = int(
        referrer_id
    )

    new_user_id = int(
        new_user_id
    )


    if referrer_id == new_user_id:
        return False


    referrer = ensure_user(
        referrer_id
    )

    new_user = ensure_user(
        new_user_id
    )


    # کاربر قبلاً زیرمجموعه داشته
    if new_user.get(
        "referrer"
    ):

        return False


    # ثبت معرف
    new_user[
        "referrer"
    ] = referrer_id


    if not isinstance(
        referrer.get(
            "referrals"
        ),
        list
    ):

        referrer[
            "referrals"
        ] = []


    if new_user_id not in [
        int(x)
        for x in referrer[
            "referrals"
        ]
    ]:

        referrer[
            "referrals"
        ].append(
            new_user_id
        )


    # ==========================================
    # REWARD
    # ==========================================

    if not new_user.get(
        "referral_rewarded",
        False
    ):

        reward = get_referral_reward()


        if reward > 0:

            add_balance(
                referrer_id,
                reward
            )


        new_user[
            "referral_rewarded"
        ] = True


    save_data()

    return True


# ==========================================
# REFERRAL LINK
# ==========================================

async def get_referral_link(
    user_id,
    context
):

    try:

        bot = await context.bot.get_me()

        username = bot.username

        if not username:
            return None

        return (
            f"https://t.me/"
            f"{username}"
            f"?start={user_id}"
        )

    except Exception as error:

        print(
            "REFERRAL LINK ERROR:",
            repr(error)
        )

        return None


# ==========================================
# REFERRAL MENU
# ==========================================

async def referral_menu(
    update,
    context
):

    user = update.effective_user

    if not user:
        return


    ensure_user(
        user.id
    )


    link = await get_referral_link(
        user.id,
        context
    )


    if not link:

        link = "❌ لینک قابل ساخت نیست."


    count = referral_count(
        user.id
    )


    reward = get_referral_reward()


    text = (

        "👥 سیستم زیرمجموعه DOGS\n\n"

        f"🔗 لینک دعوت شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه: "
        f"{count}\n\n"

        f"🎁 جایزه هر زیرمجموعه: "
        f"{format_dogs(reward)}\n\n"

        "📌 لینک خود را برای دوستانتان "
        "ارسال کنید."
    )


    await update.effective_message.reply_text(

        text,

        reply_markup=main_keyboard(
            user.id
        )

    )


# ==========================================
# START REFERRAL PARSER
# ==========================================

def parse_referral_argument(
    context
):

    if not context.args:
        return None


    value = str(
        context.args[0]
    ).strip()


    # فرمت:
    # /start 123456789
    if value.isdigit():

        return int(value)


    # فرمت:
    # /start ref_123456789
    if value.startswith(
        "ref_"
    ):

        value = value[4:]

        if value.isdigit():

            return int(value)


    return None


# ==========================================
# HANDLE REFERRAL ON START
# ==========================================

async def process_start_referral(
    update,
    context
):

    user = update.effective_user

    if not user:
        return


    referrer_id = parse_referral_argument(
        context
    )


    if referrer_id is None:
        return


    if referrer_id == user.id:
        return


    try:

        registered = register_referral(
            referrer_id,
            user.id
        )


        if not registered:
            return


        reward = get_referral_reward()


        # پیام به معرف
        try:

            await context.bot.send_message(

                chat_id=referrer_id,

                text=(

                    "🎉 زیرمجموعه جدید!\n\n"

                    f"👤 کاربر جدید وارد ربات شد.\n"

                    f"🎁 جایزه شما: "
                    f"{format_dogs(reward)}\n\n"

                    f"💰 موجودی جدید: "
                    f"{format_dogs(get_balance(referrer_id))}"

                )

            )

        except Exception as error:

            print(
                "REFERRER NOTIFY ERROR:",
                repr(error)
            )


    except Exception as error:

        print(
            "PROCESS REFERRAL ERROR:",
            repr(error)
        )


# ==========================================
# REFERRAL ADMIN SET REWARD
# ==========================================

async def admin_set_referral_reward(
    update,
    context
):

    user = update.effective_user

    if not user:
        return


    if not is_owner(
        user.id
    ):

        return


    text = (
        update.effective_message.text
        or ""
    ).strip()


    parts = text.split()


    if len(parts) < 2:

        await update.effective_message.reply_text(

            "❌ مبلغ جایزه را وارد کنید.\n\n"

            "مثال:\n"
            "جایزه رفرال 5000"

        )

        return


    try:

        amount = int(
            convert_number(
                parts[-1]
            )
        )

    except Exception:

        await update.effective_message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return


    if amount < 0:

        await update.effective_message.reply_text(
            "❌ مبلغ نمی‌تواند منفی باشد."
        )

        return


    set_referral_reward(
        amount
    )


    await update.effective_message.reply_text(

        "✅ جایزه زیرمجموعه تغییر کرد.\n\n"

        f"🎁 جایزه جدید: "
        f"{format_dogs(amount)}"

    )


# ==========================================
# REFERRAL TEXT COMMAND
# ==========================================

async def referral_text_command(
    update,
    context
):

    user = update.effective_user

    if not user:
        return


    if not await require_access(
        update,
        context
    ):

        return


    await referral_menu(
        update,
        context
    )


# ==========================================
# ADMIN REFERRAL BUTTON
# ==========================================

async def admin_referral_reward_button(
    update,
    context
):

    query = update.callback_query

    if not query:
        return


    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return


    await query.answer()


    await query.message.reply_text(

        "🎁 تغییر جایزه زیرمجموعه\n\n"

        f"جایزه فعلی: "
        f"{format_dogs(get_referral_reward())}\n\n"

        "برای تغییر، این دستور را ارسال کنید:\n\n"

        "جایزه رفرال 5000\n\n"

        "مثال بالا جایزه هر زیرمجموعه را "
        "روی 5000 DOGS قرار می‌دهد."

    )

    # ==========================================
# DOGS BOT - PART 17
# انتقال مستقیم DOGS
# ==========================================


async def transfer_text(update, context):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    sender_id = user.id

    target_id = None
    amount = None

    # ==========================================
    # حالت اول:
    # ریپلای به پیام کاربر
    #
    # انتقال 500
    # ==========================================

    if message.reply_to_message:

        target_user = (
            message.reply_to_message.from_user
        )

        if not target_user:
            await message.reply_text(
                "❌ کاربر گیرنده پیدا نشد."
            )
            return

        target_id = target_user.id

        if not context.args:

            await message.reply_text(
                "❌ مبلغ را وارد کنید.\n\n"
                "مثال:\n"
                "انتقال 500"
            )
            return

        try:

            amount = int(
                convert_number(
                    context.args[0]
                )
            )

        except Exception:

            await message.reply_text(
                "❌ مبلغ نامعتبر است."
            )
            return

    # ==========================================
    # حالت دوم:
    # انتقال با آیدی عددی
    #
    # انتقال 123456789 500
    # ==========================================

    else:

        if len(context.args) < 2:

            await message.reply_text(
                "❌ روش استفاده:\n\n"
                "روی پیام کاربر ریپلای کنید:\n"
                "انتقال 500\n\n"
                "یا:\n"
                "انتقال 123456789 500"
            )
            return

        try:

            target_id = int(
                convert_number(
                    context.args[0]
                )
            )

            amount = int(
                convert_number(
                    context.args[1]
                )
            )

        except Exception:

            await message.reply_text(
                "❌ آیدی یا مبلغ نامعتبر است."
            )
            return

    # ==========================================
    # بررسی مبلغ
    # ==========================================

    if amount <= 0:

        await message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )
        return

    # ==========================================
    # انتقال به خودش ممنوع
    # ==========================================

    if int(target_id) == int(sender_id):

        await message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    # ==========================================
    # ساخت کاربر گیرنده
    # ==========================================

    ensure_user(sender_id)
    ensure_user(target_id)

    # ==========================================
    # بررسی موجودی
    # ==========================================

    sender_balance = get_balance(
        sender_id
    )

    if sender_balance < amount:

        await message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{format_dogs(sender_balance)}\n"

            f"💸 مبلغ انتقال: "
            f"{format_dogs(amount)}"

        )
        return

    # ==========================================
    # کسر از فرستنده
    # ==========================================

    success = remove_balance(
        sender_id,
        amount
    )

    if not success:

        await message.reply_text(
            "❌ انتقال انجام نشد.\n"
            "موجودی شما کافی نیست."
        )
        return

    # ==========================================
    # اضافه به گیرنده
    # ==========================================

    add_balance(
        target_id,
        amount
    )

    # ==========================================
    # ثبت انتقال در دیتابیس
    # ==========================================

    transfer_id = str(
        random.randint(
            100000,
            999999
        )
    )

    while transfer_id in DATA["transfers"]:

        transfer_id = str(
            random.randint(
                100000,
                999999
            )
        )

    DATA["transfers"][transfer_id] = {

        "id": transfer_id,

        "sender": sender_id,

        "receiver": target_id,

        "amount": amount,

        "status": "completed",

        "created_at":
            datetime.now().isoformat()

    }

    save_data()

    # ==========================================
    # پیام موفقیت برای فرستنده
    # ==========================================

    await message.reply_text(

        "✅ انتقال با موفقیت انجام شد.\n\n"

        f"👤 گیرنده: `{target_id}`\n"

        f"💸 مبلغ: "
        f"{format_dogs(amount)}\n"

        f"💰 موجودی جدید: "
        f"{format_dogs(get_balance(sender_id))}",

        parse_mode="Markdown"

    )

    # ==========================================
    # اطلاع به گیرنده
    # ==========================================

    try:

        await context.bot.send_message(

            chat_id=target_id,

            text=(

                "💰 دریافت DOGS\n\n"

                f"👤 فرستنده: `{sender_id}`\n"

                f"💵 مبلغ دریافتی: "
                f"{format_dogs(amount)}\n\n"

                f"💰 موجودی جدید: "
                f"{format_dogs(get_balance(target_id))}"

            ),

            parse_mode="Markdown"

        )

    except Exception as error:

        print(
            "TRANSFER NOTIFY ERROR:",
            repr(error)
        )

        # =========================================================
# PART 18 — انتقال مالکیت DOGS
# =========================================================

OWNER_TRANSFER_REQUESTS = {}


# =========================================================
# OWNER ID
# =========================================================

def get_owner_id():
    try:
        # اگر مالک داخل دیتابیس ذخیره شده باشد
        saved_owner = DATA.get("settings", {}).get("owner_id")

        if saved_owner:
            return int(saved_owner)

        return int(OWNER_ID)

    except Exception:
        return int(OWNER_ID)


def is_owner(user_id):
    try:
        return int(user_id) == get_owner_id()
    except Exception:
        return False


# =========================================================
# OWNER TRANSFER KEYBOARD
# =========================================================

def owner_transfer_keyboard(request_id):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👑 قبول مالکیت",
                    callback_data=f"owner_accept:{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"owner_reject:{request_id}"
                )
            ]
        ]
    )


# =========================================================
# START OWNER TRANSFER
# =========================================================

async def owner_transfer(update, context):

    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # فقط مالک فعلی
    if not is_owner(user.id):

        await message.reply_text(
            "❌ فقط مالک فعلی می‌تواند مالکیت را منتقل کند."
        )

        return

    target_id = None

    # -----------------------------------------
    # انتقال با ریپلای
    # -----------------------------------------

    if message.reply_to_message:

        target_user = message.reply_to_message.from_user

        if target_user:
            target_id = target_user.id

    # -----------------------------------------
    # انتقال با آیدی عددی
    # -----------------------------------------

    elif context.args:

        try:

            target_id = int(
                convert_number(
                    context.args[0]
                )
            )

        except Exception:

            target_id = None

    # -----------------------------------------
    # گیرنده مشخص نیست
    # -----------------------------------------

    if target_id is None:

        await message.reply_text(
            "❌ مالک جدید مشخص نیست.\n\n"
            "روی پیام کاربر ریپلای کنید:\n"
            "انتقال مالکیت\n\n"
            "یا:\n"
            "انتقال مالکیت 123456789"
        )

        return

    # -----------------------------------------
    # انتقال به خودش
    # -----------------------------------------

    if int(target_id) == int(user.id):

        await message.reply_text(
            "❌ شما همین الان مالک ربات هستید."
        )

        return

    # -----------------------------------------
    # ساخت درخواست
    # -----------------------------------------

    request_id = str(
        random.randint(
            100000,
            999999
        )
    )

    while request_id in OWNER_TRANSFER_REQUESTS:

        request_id = str(
            random.randint(
                100000,
                999999
            )
        )

    OWNER_TRANSFER_REQUESTS[request_id] = {

        "id": request_id,

        "old_owner": int(user.id),

        "new_owner": int(target_id),

        "status": "pending",

        "created_at": datetime.now().isoformat()
    }

    # -----------------------------------------
    # ارسال درخواست به مالک جدید
    # -----------------------------------------

    try:

        await context.bot.send_message(

            chat_id=target_id,

            text=(
                "👑 درخواست انتقال مالکیت DOGS\n\n"

                f"👤 مالک فعلی: `{user.id}`\n\n"

                "مالک فعلی می‌خواهد مالکیت ربات "
                "را به شما منتقل کند.\n\n"

                "اگر قبول کنید، پنل مدیریت برای شما فعال می‌شود."
            ),

            parse_mode="Markdown",

            reply_markup=owner_transfer_keyboard(
                request_id
            )
        )

    except Exception as error:

        OWNER_TRANSFER_REQUESTS.pop(
            request_id,
            None
        )

        print(
            "OWNER TRANSFER SEND ERROR:",
            repr(error)
        )

        await message.reply_text(
            "❌ ارسال درخواست انجام نشد.\n\n"
            "ممکن است کاربر هنوز ربات را Start نکرده باشد."
        )

        return

    await message.reply_text(

        "✅ درخواست انتقال مالکیت ارسال شد.\n\n"

        f"👑 مالک جدید: `{target_id}`\n\n"

        "⏳ تا قبول مالک جدید، مالک فعلی تغییر نمی‌کند.",

        parse_mode="Markdown"
    )


# =========================================================
# OWNER TRANSFER CALLBACK
# =========================================================

async def owner_transfer_callback(update, context):

    query = update.callback_query

    if not query:
        return

    value = query.data or ""

    # =====================================================
    # ACCEPT
    # =====================================================

    if value.startswith("owner_accept:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = OWNER_TRANSFER_REQUESTS.get(
            request_id
        )

        if not request:

            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )

            return

        old_owner = int(
            request["old_owner"]
        )

        new_owner = int(
            request["new_owner"]
        )

        # فقط مالک جدید اجازه قبول دارد
        if query.from_user.id != new_owner:

            await query.answer(
                "❌ این درخواست برای شما نیست.",
                show_alert=True
            )

            return

        # -----------------------------------------
        # تغییر مالک
        # -----------------------------------------

        globals()["OWNER_ID"] = new_owner

        if "settings" not in DATA:
            DATA["settings"] = {}

        DATA["settings"]["owner_id"] = new_owner

        request["status"] = "accepted"

        request["accepted_at"] = (
            datetime.now().isoformat()
        )

        # ثبت انتقال در دیتابیس
        if "owner_transfers" not in DATA:
            DATA["owner_transfers"] = []

        DATA["owner_transfers"].append(
            {
                "old_owner": old_owner,
                "new_owner": new_owner,
                "request_id": request_id,
                "created_at": request.get(
                    "created_at"
                ),
                "accepted_at": request.get(
                    "accepted_at"
                )
            }
        )

        save_data()

        OWNER_TRANSFER_REQUESTS.pop(
            request_id,
            None

          OWNER_TRANSFER_REQUESTS.pop(
            request_id,
            None
        )

        await query.answer(
            "✅ مالکیت ربات به شما منتقل شد."
        )

        try:

            await query.edit_message_text(

                "👑 انتقال مالکیت انجام شد.\n\n"

                "✅ شما اکنون مالک ربات هستید.\n"

                "⚙️ پنل مدیریت برای شما فعال شد."

            )

        except Exception as error:

            print(
                "OWNER ACCEPT EDIT ERROR:",
                repr(error)
            )

        # اطلاع به مالک قبلی

        try:

            await context.bot.send_message(

                chat_id=old_owner,

                text=(

                    "👑 انتقال مالکیت انجام شد.\n\n"

                    f"👤 مالک جدید: `{new_owner}`\n\n"

                    "⚠️ دسترسی مدیریت شما حذف شد."

                ),

                parse_mode="Markdown"

            )

        except Exception as error:

            print(
                "OLD OWNER NOTIFY ERROR:",
                repr(error)
            )

        return


    # =====================================================
    # REJECT
    # =====================================================

    if value.startswith("owner_reject:"):

        request_id = value.split(
            ":",
            1
        )[1]

        request = OWNER_TRANSFER_REQUESTS.get(
            request_id
        )

        if not request:

            await query.answer(
                "❌ درخواست پیدا نشد.",
                show_alert=True
            )

            return

        old_owner = int(
            request["old_owner"]
        )

        new_owner = int(
            request["new_owner"]
        )

        # فقط مالک جدید اجازه رد دارد

        if query.from_user.id != new_owner:

            await query.answer(
                "❌ این درخواست برای شما نیست.",
                show_alert=True
            )

            return

        request["status"] = "rejected"

        request["rejected_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        OWNER_TRANSFER_REQUESTS.pop(
            request_id,
            None
        )

        await query.answer(
            "❌ درخواست انتقال رد شد."
        )

        try:

            await query.edit_message_text(

                "❌ درخواست انتقال مالکیت رد شد.\n\n"

                "مالک فعلی بدون تغییر باقی ماند."

            )

        except Exception as error:

            print(
                "OWNER REJECT EDIT ERROR:",
                repr(error)
            )

        # اطلاع به مالک فعلی

        try:

            await context.bot.send_message(

                chat_id=old_owner,

                text=(

                    "❌ انتقال مالکیت رد شد.\n\n"

                    f"👤 کاربری که درخواست برای او ارسال شده بود:\n"
                    f"`{new_owner}`\n\n"

                    "مالکیت ربات همچنان در اختیار شماست."

                ),

                parse_mode="Markdown"

            )

        except Exception as error:

            print(
                "OLD OWNER REJECT NOTIFY ERROR:",
                repr(error)
            )

        return


# =========================================================
# PART 19 — KEYBOARDS
# =========================================================


def back_keyboard():

    return ReplyKeyboardMarkup(

        [
            [
                KeyboardButton(
                    "🔙 بازگشت"
                )
            ]
        ],

        resize_keyboard=True

    )


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(

        [

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
                    "🎁 جایزه زیرمجموعه",
                    callback_data="admin_reward"
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
                    "🔴/🟢 وضعیت ربات",
                    callback_data="admin_toggle"
                )

            ],

            [

                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_owner"
                )

            ]

        ]

    )


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard(user_id):

    buttons = [

        [
            "💰 موجودی",
            "👤 پروفایل"
        ],

        [
            "🎮 بازی",
            "👥 زیرمجموعه"
        ],

        [
            "💳 واریزی",
            "💸 برداشت"
        ],

        [
            "🔄 انتقال"
        ]

    ]

    if is_owner(user_id):

        buttons.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )

    return ReplyKeyboardMarkup(

        buttons,

        resize_keyboard=True

    )


# =========================================================
# PART 20 — ENSURE USER
# =========================================================

def ensure_user(user_id):

    user_id = int(user_id)

    uid = str(user_id)

    if uid not in DATA["users"]:

        DATA["users"][uid] = {

            "id": user_id,

            "name": "کاربر",

            "username": "",

            "phone": None,

            "phone_verified": False,

            "balance": 0,

            "referrer": None,

            "refs": 0,

            "referrals": [],

            "referral_rewarded": False,

            "created_at":
                datetime.now().isoformat()

        }

        save_data()

    else:

        user = DATA["users"][uid]

        user.setdefault(
            "balance",
            0
        )

        user.setdefault(
            "referrer",
            None
        )

        user.setdefault(
            "referrals",
            []
        )

        user.setdefault(
            "phone_verified",
            False
        )

        user.setdefault(
            "refs",
            0
        )

        user.setdefault(
            "referral_rewarded",
            False
        )

        save_data()

    return DATA["users"][uid]


# =========================================================
# PART 21 — ADMIN ADD / REMOVE BALANCE
# =========================================================

async def admin_balance_callback(
    update,
    context
):

    query = update.callback_query

    if not query:
        return

    user = query.from_user

    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    data = query.data

    if data == "admin_add":

        context.user_data[
            "admin_state"
        ] = "add_balance"

        await query.answer()

        await query.message.reply_text(

            "💰 شارژ موجودی\n\n"

            "به این شکل ارسال کنید:\n\n"

            "شارژ آیدی مبلغ\n\n"

            "مثال:\n"

            "شارژ 123456789 5000"

        )

        return


    if data == "admin_remove":

        context.user_data[
            "admin_state"
        ] = "remove_balance"

        await query.answer()

        await query.message.reply_text(

            "➖ کسر موجودی\n\n"

            "به این شکل ارسال کنید:\n\n"

            "کسر آیدی مبلغ\n\n"

            "مثال:\n"

            "کسر 123456789 5000"

        )

        return


# =========================================================
# ADMIN BALANCE PROCESS
# =========================================================

async def admin_balance_process(
    update,
    context
):

    user = update.effective_user

    if not user:
        return False

    if not is_owner(user.id):
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if state not in [
        "add_balance",
        "remove_balance"
    ]:

        return False

    text = (
        update.effective_message.text
        or ""
    ).strip()

    parts = text.split()

    if len(parts) < 3:

        await update.effective_message.reply_text(

            "❌ فرمت صحیح نیست.\n\n"

            "شارژ آیدی مبلغ\n"

            "یا\n"

            "کسر آیدی مبلغ"

        )

        return True

    try:

        target_id = int(
            convert_number(
                parts[1]
            )
        )

        amount = int(
            convert_number(
                parts[2]
            )
        )

    except Exception:

        await update.effective_message.reply_text(
            "❌ آیدی یا مبلغ نامعتبر است."
        )

        return True

    if target_id <= 0 or amount <= 0:

        await update.effective_message.reply_text(
            "❌ آیدی و مبلغ باید معتبر باشند."
        )

        return True

    ensure_user(
        target_id
    )

    if state == "add_balance":

        add_balance(
            target_id,
            amount
        )

        result = "شارژ"

    else:

        if not remove_balance(
            target_id,
            amount
        ):

            await update.effective_message.reply_text(
                "❌ موجودی کاربر کافی نیست."
            )

            return True

        result = "کسر"

    context.user_data.pop(
        "admin_state",
        None
    )

    await update.effective_message.reply_text(

        f"✅ {result} موجودی انجام شد.\n\n"

        f"👤 کاربر: `{target_id}`\n"

        f"💰 مبلغ: {format_dogs(amount)}\n"

        f"💳 موجودی جدید: "
        f"{format_dogs(get_balance(target_id))}",

        parse_mode="Markdown",

        reply_markup=main_keyboard(
            user.id
        )

    )

    # اطلاع به کاربر

    try:

        await context.bot.send_message(

            chat_id=target_id,

            text=(

                f"💰 تغییر موجودی\n\n"

                f"عملیات: {result}\n"

                f"مبلغ: {format_dogs(amount)}\n\n"

                f"💳 موجودی جدید:\n"
                f"{format_dogs(get_balance(target_id))}"

            )

        )

    except Exception as error:

        print(
            "ADMIN BALANCE NOTIFY ERROR:",
            repr(error)
        )

    return True


# =========================================================
# PART 22 — PROFILE
# =========================================================

async def profile_text(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    info = ensure_user(
        user.id
    )

    await update.effective_message.reply_text(

        "👤 پروفایل DOGS\n\n"

        f"🆔 آیدی: `{user.id}`\n"

        f"👤 نام: "
        f"{user.first_name or 'کاربر'}\n"

        f"💰 موجودی: "
        f"{format_dogs(info.get('balance', 0))}\n"

        f"👥 زیرمجموعه: "
        f"{referral_count(user.id)}\n\n"

        f"📅 عضویت:\n"
        f"{info.get('created_at', '-')}",

        parse_mode="Markdown",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# PART 23 — BALANCE
# =========================================================

async def balance_text(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    ensure_user(
        user.id
    )

    await update.effective_message.reply_text(

        "💰 موجودی DOGS\n\n"

        f"💳 موجودی شما:\n\n"
        f"{format_dogs(get_balance(user.id))}",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# PART 24 — ADMIN PANEL
# =========================================================

async def admin_panel(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    if not is_owner(user.id):

        await update.effective_message.reply_text(
            "❌ فقط مالک دسترسی دارد."
        )

        return

    await update.effective_message.reply_text(

        "⚙️ پنل مدیریت DOGS\n\n"

        "یک گزینه را انتخاب کنید:",

        reply_markup=admin_keyboard()

    )


# =========================================================
# PART 25 — ADMIN STATS / TOGGLE / REWARD
# =========================================================

async def admin_general_callback(
    update,
    context
):

    query = update.callback_query

    if not query:
        return

    user = query.from_user

    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    data = query.data

    # -----------------------------------------
    # STATS
    # -----------------------------------------

    if data == "admin_stats":

        users_count = len(
            DATA["users"]
        )

        total_balance = 0

        for user_data in DATA["users"].values():

            try:

                total_balance += int(
                    user_data.get(
                        "balance",
                        0
                    )
                )

            except Exception:
                pass

        deposits = len(
            DATA.get(
                "deposits",
                {}
            )
        )

        withdraws = len(
            DATA.get(
                "withdraws",
                {}
            )
        )

        transfers = len(
            DATA.get(
                "transfers",
                {}
            )
        )

        await query.answer()

        await query.message.reply_text(

            "📊 آمار DOGS\n\n"

            f"👥 کاربران: {users_count}\n"

            f"💰 کل موجودی: "
            f"{format_dogs(total_balance)}\n\n"

            f"💳 درخواست‌های واریز: "
            f"{deposits}\n"

            f"💸 درخواست‌های برداشت: "
            f"{withdraws}\n"

            f"🔄 انتقال‌ها: "
            f"{transfers}"

        )

        return

    # -----------------------------------------
    # TOGGLE
    # -----------------------------------------

    if data == "admin_toggle":

        current = bot_active()

        set_bot_active(
            not current
        )

        await query.answer(
            "وضعیت ربات تغییر کرد."
        )

        try:

            await query.edit_message_reply_markup(
                reply_markup=admin_keyboard()
            )

        except Exception:

            pass

        return

    # -----------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------

    if data == "admin_reward":

        await query.answer()

        context.user_data[
            "admin_state"
        ] = "reward"

        await query.message.reply_text(

            "🎁 تغییر جایزه زیرمجموعه\n\n"

            f"جایزه فعلی:\n"
            f"{format_dogs(get_referral_reward())}\n\n"

            "مبلغ جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "5000"

        )

        return

    # -----------------------------------------
    # OWNER TRANSFER
    # -----------------------------------------

    if data == "admin_owner":

        await query.answer()

        context.user_data[
            "admin_state"
        ] = "owner_transfer"

        await query.message.reply_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789"

        )

        return


# =========================================================
# PART 26 — ADMIN STATE ROUTER
# =========================================================

async def admin_state_handler(
    update,
    context
):

    user = update.effective_user

    if not user:
        return False

    if not is_owner(user.id):
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    # -----------------------------------------
    # ADD / REMOVE BALANCE
    # -----------------------------------------

    if state in [
        "add_balance",
        "remove_balance"
    ]:

        return await admin_balance_process(
            update,
            context
        )

    # -----------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------

    if state == "reward":

        text = (
            update.effective_message.text
            or ""
        ).strip()

        try:

            amount = int(
                convert_number(
                    text
                )
            )

        except Exception:

            await update.effective_message.reply_text(
                "❌ مبلغ صحیح نیست."
            )

            return True

        if amount < 0:

            await update.effective_message.reply_text(
                "❌ مبلغ نمی‌تواند منفی باشد."
            )

            return True

        set_referral_reward(
            amount
        )

        context.user_data.pop(
            "admin_state",
            None
        )

        await update.effective_message.reply_text(

            "✅ جایزه زیرمجموعه تغییر کرد.\n\n"

            f"🎁 جایزه جدید:\n"
            f"{format_dogs(amount)}",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return True

    # -----------------------------------------
    # OWNER TRANSFER
    # -----------------------------------------

    if state == "owner_transfer":

        text = (
            update.effective_message.text
            or ""
        ).strip()

        try:

            new_owner = int(
                convert_number(
                    text
                )
            )

        except Exception:

            await update.effective_message.reply_text(
                "❌ آیدی صحیح نیست."
            )

            return True

        if new_owner <= 0:

            await update.effective_message.reply_text(
                "❌ آیدی نامعتبر است."
            )

            return True

        if new_owner == user.id:

            await update.effective_message.reply_text(
                "❌ شما همین الان مالک هستید."
            )

            return True

        context.user_data.pop(
            "admin_state",
            None
        )

        # ساخت درخواست انتقال

        request_id = str(
            random.randint(
                100000,
                999999
            )
        )

        while request_id in OWNER_TRANSFER_REQUESTS:

            request_id = str(
                random.randint(
                    100000,
                    999999
                )
            )

        OWNER_TRANSFER_REQUESTS[
            request_id
        ] = {

            "id": request_id,

            "old_owner": user.id,

            "new_owner": new_owner,

            "status": "pending",

            "created_at":
                datetime.now().isoformat()

        }

        try:

            await context.bot.send_message(

                chat_id=new_owner,

                text=(

                    "👑 درخواست انتقال مالکیت DOGS\n\n"

                    f"👤 مالک فعلی: `{user.id}`\n\n"

                    "برای قبول یا رد درخواست "
                    "از دکمه‌های زیر استفاده کنید."

                ),

                parse_mode="Markdown",

                reply_markup=owner_transfer_keyboard(
                    request_id
                )

            )

        except Exception:

            OWNER_TRANSFER_REQUESTS.pop(
                request_id,
                None
            )

            await update.effective_message.reply_text(

                "❌ ارسال درخواست انجام نشد.\n\n"

                "کاربر باید قبلاً ربات را Start کرده باشد."

            )

            return True

        await update.effective_message.reply_text(

            "✅ درخواست انتقال مالکیت ارسال شد.\n\n"

            f"👑 مالک جدید: `{new_owner}`\n\n"

            "⏳ تا تأیید او، مالک فعلی تغییر نمی‌کند.",

            parse_mode="Markdown"

        )

        return True

    return False


# =========================================================
# PART 27 — START HANDLER
# =========================================================

async def start_handler(
    update,
    context
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    # پردازش رفرال

    await process_start_referral(
        update,
        context
    )

    if not await require_access(
        update,
        context
    ):

        return

    await update.effective_message.reply_text(

        "🐶 به ربات DOGS خوش آمدید!\n\n"

        "از منوی زیر انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# PART 28 — TEXT ROUTER
# =========================================================

async def main_text_router(
    update,
    context
):

    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    text = (
        message.text
        or ""
    ).strip()

    if not text:
        return

    create_user(user)

    # ضد اسپم

    if not anti_spam(user.id):

        return

    # -----------------------------------------
    # BACK
    # -----------------------------------------

    if text in [
        "🔙 بازگشت",
        "بازگشت"
    ]:

        context.user_data.clear()

        await message.reply_text(

            "🏠 به منوی اصلی برگشتید.",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return

    # -----------------------------------------
    # ADMIN STATE
    # -----------------------------------------

    if is_owner(user.id):

        handled = await admin_state_handler(
            update,
            context
        )

        if handled:

            return

    # -----------------------------------------
    # ACCESS
    # -----------------------------------------

    if not await require_access(
        update,
        context
    ):

        return

    # -----------------------------------------
    # DEPOSIT STATE
    # -----------------------------------------

    state = context.user_data.get(
        "state"
    )

    if state == "deposit_amount":

        await deposit_amount(
            update,
            context
        )

        return

    # -----------------------------------------
    # WITHDRAW AMOUNT
    # -----------------------------------------

    if state == "withdraw_amount":

        await withdraw_amount(
            update,
            context
        )

        return

    # -----------------------------------------
    # WITHDRAW TARGET
    # -----------------------------------------

    if state == "withdraw_target":

        await withdraw_target(
            update,
            context
        )

        return

    # -----------------------------------------
    # BALANCE
    # -----------------------------------------

    if text in [
        "💰 موجودی",
        "موجودی",
        "موجودی من"
    ]:

        await balance_text(
            update,
            context
        )

        return

    # -----------------------------------------
    # PROFILE
    # -----------------------------------------

    if text in [
        "👤 پروفایل",
        "پروفایل"
    ]:

        await profile_text(
            update,
            context
        )

        return

    # -----------------------------------------
    # GAME
    # -----------------------------------------

    if text == "🎮 بازی":

        await message.reply_text(

            "🎮 بازی DOGS\n\n"

            "برای ساخت بازی بنویس:\n\n"

            "بازی 500\n\n"

            "حداقل مبلغ بازی:\n"

            f"{format_dogs(GAME_MIN_AMOUNT)}",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return

    # -----------------------------------------
    # GAME COMMAND
    # -----------------------------------------

    if text.startswith("بازی "):

        await game_command(
            update,
            context
        )

        return

    # -----------------------------------------
    # REFERRAL
    # -----------------------------------------

    if text in [
        "👥 زیرمجموعه",
        "زیرمجموعه",
        "رفرال"
    ]:

        await referral_menu(
            update,
            context
        )

        return

    # -----------------------------------------
    # DEPOSIT
    # -----------------------------------------

    if text in [
        "💳 واریزی",
        "واریزی",
        "واریز"
    ]:

        await deposit_start(
            update,
            context
        )

        return

    # -----------------------------------------
    # WITHDRAW
    # -----------------------------------------

    if text in [
        "💸 برداشت",
        "برداشت"
    ]:

        await withdraw_start(
            update,
            context
        )

        return

    # -----------------------------------------
    # TRANSFER
    # -----------------------------------------

    if text in [
        "🔄 انتقال",
        "انتقال"
    ]:

        await transfer_start(
            update,
            context
        )

        return

    # -----------------------------------------
    # TRANSFER COMMAND
    # -----------------------------------------

    if text.startswith("انتقال "):

        # context.args در MessageHandler
        # به صورت خودکار پر نمی‌شود،
        # پس دستی می‌سازیم.

        parts = text.split()

        old_args = context.args

        context.args = parts[1:]

        try:

            await transfer_text(
                update,
                context
            )

        finally:

            context.args = old_args

        return

    # -----------------------------------------
    # ADMIN PANEL
    # -----------------------------------------

    if text == "⚙️ پنل مدیریت":

        await admin_panel(
            update,
            context
        )

        return

    # -----------------------------------------
    # UNKNOWN
    # -----------------------------------------

    await message.reply_text(

        "❓ دستور شناخته نشد.\n\n"

        "از دکمه‌های منوی اصلی استفاده کنید.",

        reply_markup=main_keyboard(
            user.id
        )

    )


# =========================================================
# PART 29 — CALLBACK ROUTER
# =========================================================

async def callback_router(
    update,
    context
):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    # -----------------------------------------
    # GAME JOIN
    # -----------------------------------------

    if data.startswith(
        "game_join:"
    ):

        await game_join_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # GAME CANCEL
    # -----------------------------------------

    if data.startswith(
        "game_cancel:"
    ):

        await game_cancel_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # OLD GAME CALLBACK COMPATIBILITY
    # -----------------------------------------

    if data.startswith(
        "join_game:"
    ):

        # تبدیل به ساختار جدید

        query.data = data.replace(
            "join_game:",
            "game_join:",
            1
        )

        await game_join_callback(
            update,
            context
        )

        return

    if data.startswith(
        "cancel_game:"
    ):

        query.data = data.replace(
            "cancel_game:",
            "game_cancel:",
            1
        )

        await game_cancel_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # DEPOSIT
    # -----------------------------------------

    if data.startswith(
        "dep_ok:"
    ) or data.startswith(
        "dep_no:"
    ):

        await deposit_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # WITHDRAW
    # -----------------------------------------

    if data.startswith(
        "with_ok:"
    ) or data.startswith(
        "with_no:"
    ):

        await withdraw_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # OWNER TRANSFER
    # -----------------------------------------

    if data.startswith(
        "owner_accept:"
    ) or data.startswith(
        "owner_reject:"
    ):

        await owner_transfer_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # ADMIN BALANCE
    # -----------------------------------------

    if data in [
        "admin_add",
        "admin_remove"
    ]:

        await admin_balance_callback(
            update,
            context
        )

        return

    # -----------------------------------------
    # ADMIN GENERAL
    # -----------------------------------------

    if data in [
        "admin_stats",
        "admin_toggle",
        "admin_reward",
        "admin_owner"
    ]:

        await admin_general_callback(
            update,
            context
        )

        return

    await query.answer()


# =========================================================
# PART 30 — ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "BOT ERROR:"
    )

    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__
    )


# =========================================================
# PART 31 — APPLICATION
# =========================================================

def build_application():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------
    # START
    # -----------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start_handler
        )
    )

    # -----------------------------------------
    # CALLBACKS
    # -----------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # -----------------------------------------
    # TEXT
    # -----------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            main_text_router
        )
    )

    # -----------------------------------------
    # ERRORS
    # -----------------------------------------

    application.add_error_handler(
        error_handler
    )

    return application


# =========================================================
# PART 32 — MAIN
# =========================================================

def main():

    print(
        "🐶 DOGS BOT STARTING..."
    )

    print(
        f"👑 OWNER ID: {get_owner_id()}"
    )

    print(
        f"🎮 MIN GAME: {GAME_MIN_AMOUNT}"
    )

    print(
        "✅ BOT IS RUNNING"
    )

    application = build_application()

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()          
