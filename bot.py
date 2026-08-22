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

# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_B_ET"

ULTRA_ID = "@CyyFr"

DATA_FILE = "data.json"

# -------------------------
# DEPOSIT
# -------------------------

MIN_DEPOSIT = 5000

# -------------------------
# WITHDRAW
# -------------------------

MIN_WITHDRAW = 10000

# -------------------------
# GAME
# -------------------------

MIN_GAME = 500
MAX_GAME = 20000

# از شرط 500:
# برنده 900 می‌گیرد
# مالک 100 می‌گیرد
#
# یعنی:
# 500 + 500 = 1000
# 900 -> winner
# 100 -> owner

WINNER_PRIZE_RATIO = 900
OWNER_GAME_RATIO = 100

# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_status": True,

    "ref_reward": 50,

    "users": {},

    "deposits": {},

    "withdraws": {},

    "games": {},

    "game_stats": {
        "total_games": 0,
        "finished_games": 0,
        "cancelled_games": 0,
    },
}

# =========================================================
# LOAD DATA
# =========================================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            if not isinstance(loaded, dict):
                return json.loads(json.dumps(DEFAULT_DATA))

            for key, value in DEFAULT_DATA.items():
                if key not in loaded:
                    loaded[key] = json.loads(json.dumps(value))

            return loaded

    except Exception:
        traceback.print_exc()

    return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


# =========================================================
# SAVE DATA
# =========================================================

def save_data():
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_file, DATA_FILE)

    except Exception:
        traceback.print_exc()


# =========================================================
# MEMORY STATES
# =========================================================

CLICK = {}

DEPOSIT_DATA = {}

WITHDRAW_DATA = {}

TRANSFER_DATA = {}

OWNER_STATE = {}

GAMES = {}


# =========================================================
# ANTI SPAM
# =========================================================

def anti_spam(uid, seconds=1.5):

    now = time.time()

    key = str(uid)

    previous = CLICK.get(key, 0)

    if now - previous < seconds:
        return False

    CLICK[key] = now

    return True


# =========================================================
# USER SYSTEM
# =========================================================

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
            "ref_by": None,
            "games": 0,
            "wins": 0,
            "losses": 0,
        }

        save_data()

        return

    u = data["users"][uid]

    u["id"] = user.id

    if user.first_name:
        u["name"] = user.first_name

    if user.username:
        u["username"] = user.username

    u.setdefault("phone", "")
    u.setdefault("balance", 0)
    u.setdefault("refs", 0)
    u.setdefault("ref_by", None)
    u.setdefault("games", 0)
    u.setdefault("wins", 0)
    u.setdefault("losses", 0)


# =========================================================
# BALANCE
# =========================================================

def get_balance(uid):

    try:
        return int(
            data["users"][str(uid)].get("balance", 0)
        )

    except Exception:
        return 0


def set_balance(uid, amount):

    uid = str(uid)

    if uid not in data["users"]:
        return False

    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        amount = 0

    data["users"][uid]["balance"] = amount

    save_data()

    return True


def add_balance(uid, amount):

    uid = str(uid)

    if uid not in data["users"]:
        return False

    try:
        amount = int(amount)
    except Exception:
        return False

    current = get_balance(uid)

    new_balance = current + amount

    if new_balance < 0:
        new_balance = 0

    data["users"][uid]["balance"] = new_balance

    save_data()

    return True


def remove_balance(uid, amount):

    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        return False

    if get_balance(uid) < amount:
        return False

    return add_balance(uid, -amount)


# =========================================================
# OWNER
# =========================================================

def is_owner(uid):

    try:
        return int(uid) == int(
            data.get("owner", OWNER_ID)
        )

    except Exception:
        return False


# =========================================================
# MAIN KEYBOARD
# =========================================================

def main_keyboard(uid):

    buttons = [

        ["💳 واریزی", "💰 برداشت"],

        ["👥 زیرمجموعه", "🎧 پشتیبانی"],

        ["👤 پروفایل", "👥 انتقال"],

    ]

    if is_owner(uid):
        buttons.append(
            ["⚙️ پنل مدیریت"]
        )

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )


# =========================================================
# BACK KEYBOARD
# =========================================================

def back_keyboard():

    return ReplyKeyboardMarkup(
        [["🔙 برگشت"]],
        resize_keyboard=True
    )


# =========================================================
# JOIN KEYBOARD
# =========================================================

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
        ],

    ])


# =========================================================
# PHONE KEYBOARD
# =========================================================

def phone_keyboard():

    return ReplyKeyboardMarkup(

        [[
            KeyboardButton(
                "📱 ارسال شماره",
                request_contact=True
            )
        ]],

        resize_keyboard=True,

        one_time_keyboard=True
    )


# =========================================================
# FORCE JOIN
# =========================================================

async def check_join(user_id, context):

    try:

        chats = [
            FORCE_CHANNEL,
            FORCE_GROUP
        ]

        for chat in chats:

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

        print("JOIN ERROR:", e)

        return False


# =========================================================
# REFERRAL
# =========================================================

async def process_referral(update, context):

    if not context.args:
        return

    try:
        ref_id = int(
            context.args[0]
        )
    except Exception:
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

    data["users"][
        str(ref_id)
    ]["refs"] = int(
        data["users"][
            str(ref_id)
        ].get("refs", 0)
    ) + 1

    reward = int(
        data.get("ref_reward", 50)
    )

    add_balance(
        ref_id,
        reward
    )

    save_data()


# =========================================================
# CLEAN PHONE
# =========================================================

def clean_phone(phone):

    if not phone:
        return None

    phone = phone.replace(
        " ",
        ""
    ).replace(
        "-",
        ""
    )

    if phone.startswith("0098"):

        phone = "+" + phone[2:]

    elif phone.startswith("98"):

        phone = "+" + phone

    if phone.startswith("+98"):

        return phone

    return None


# =========================================================
# START
# =========================================================

async def start(update, context):

    user = update.effective_user

    create_user(user)

    await process_referral(
        update,
        context
    )

    if not await check_join(
        user.id,
        context
    ):

        await update.message.reply_text(

            "❌ ابتدا عضو کانال و گپ شوید.\n\n"
            "بعد از عضویت روی دکمه بررسی بزنید.",

            reply_markup=join_keyboard()
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(

            "📱 شماره خود را ارسال کنید.\n\n"
            "فقط شماره ایران با +98 قبول است.",

            reply_markup=phone_keyboard()
        )

        return

    await update.message.reply_text(

        "✅ ورود موفق شد.\n\n"

        f"💰 موجودی شما: "
        f"{get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# PHONE RECEIVE
# =========================================================

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

    data["users"][
        str(user.id)
    ]["phone"] = phone

    save_data()

    await update.message.reply_text(

        "✅ شماره با موفقیت تایید شد.\n\n"

        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
)

# =========================================================
# REFERRAL MENU
# =========================================================

async def referral_menu(update, context):

    user = update.effective_user

    create_user(user)

    try:
        bot = await context.bot.get_me()
        username = bot.username or "YOUR_BOT"
    except Exception:
        username = "YOUR_BOT"

    link = f"https://t.me/{username}?start={user.id}"

    refs = int(
        data["users"][str(user.id)].get(
            "refs",
            0
        )
    )

    reward = int(
        data.get("ref_reward", 50)
    )

    await update.message.reply_text(

        "👥 زیرمجموعه\n\n"

        f"🔗 لینک دعوت شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه: {refs}\n"

        f"💰 پاداش هر زیرمجموعه: "
        f"{reward:,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# ULTRA DEPOSIT
# =========================================================

async def deposit_start(update, context):

    user = update.effective_user

    create_user(user)

    if not anti_spam(user.id):
        return

    DEPOSIT_DATA[user.id] = {
        "step": "amount"
    }

    await update.message.reply_text(

        "🐶 واریز ULTRA\n\n"

        "مقدار DOGS را وارد کنید.\n\n"

        f"حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS",

        reply_markup=back_keyboard()
    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount(update, context):

    uid = update.effective_user.id

    if uid not in DEPOSIT_DATA:
        return

    if DEPOSIT_DATA[uid].get(
        "step"
    ) != "amount":
        return

    text = update.message.text.strip()

    try:

        amount = int(
            text.replace(",", "")
        )

    except Exception:

        await update.message.reply_text(
            "❌ مقدار فقط باید عدد باشد."
        )

        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."
        )

        return

    DEPOSIT_DATA[uid] = {
        "step": "receipt",
        "amount": amount
    }

    await update.message.reply_text(

        "💳 فرصت واریز:\n\n"

        f"ULTRA {amount:,} DOGS {ULTRA_ID}\n\n"

        f"حداقل واریز {MIN_DEPOSIT:,} DOGS\n\n"

        "📸 شات خود یا رسید پیام ارسال کنید.\n\n"

        "⏳ بعد از ارسال رسید، درخواست "
        "سریع برای مالک ارسال می‌شود.",

        reply_markup=back_keyboard()
    )


# =========================================================
# DEPOSIT OWNER BUTTONS
# =========================================================

def deposit_buttons(request_id):

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید واریز",
                callback_data=f"dep_ok:{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد واریز",
                callback_data=f"dep_no:{request_id}"
            ),

        ]

    ])


# =========================================================
# SEND DEPOSIT TO OWNER
# =========================================================

async def send_deposit_to_owner(
    context,
    request
):

    owner = data.get(
        "owner",
        OWNER_ID
    )

    request_id = request["request_id"]

    caption = (

        "💳 واریز جدید\n\n"

        f"🆔 درخواست: {request_id}\n"

        f"👤 کاربر: "
        f"{request['user_id']}\n"

        f"💰 مبلغ: "
        f"{request['amount']:,} DOGS\n"

        f"🐶 روش: ULTRA\n\n"

        "📋 رسید کاربر را بررسی کنید."

    )

    markup = deposit_buttons(
        request_id
    )

    if request["kind"] == "photo":

        await context.bot.send_photo(

            chat_id=owner,

            photo=request["content"],

            caption=caption,

            reply_markup=markup

        )

    else:

        await context.bot.send_message(

            chat_id=owner,

            text=(
                caption
                + "\n\n"
                + "🧾 رسید:\n"
                + str(request["content"])
            ),

            reply_markup=markup
        )


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

async def deposit_receipt(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in DEPOSIT_DATA:
        return

    if DEPOSIT_DATA[uid].get(
        "step"
    ) != "receipt":

        return

    amount = int(
        DEPOSIT_DATA[uid]["amount"]
    )

    request_id = (
        f"D{int(time.time() * 1000)}"
        f"_{uid}"
    )

    # -------------------------
    # PHOTO RECEIPT
    # -------------------------

    if update.message.photo:

        request = {

            "request_id": request_id,

            "user_id": uid,

            "type": "ULTRA",

            "amount": amount,

            "kind": "photo",

            "content":
                update.message.photo[-1].file_id,

            "status": "pending",

            "created":
                datetime.now().isoformat()

        }

    # -------------------------
    # TEXT RECEIPT
    # -------------------------

    elif update.message.text:

        receipt_text = (
            update.message.text.strip()
        )

        if not receipt_text:

            await update.message.reply_text(
                "❌ رسید معتبر ارسال کنید."
            )

            return

        request = {

            "request_id": request_id,

            "user_id": uid,

            "type": "ULTRA",

            "amount": amount,

            "kind": "text",

            "content": receipt_text,

            "status": "pending",

            "created":
                datetime.now().isoformat()

        }

    else:

        await update.message.reply_text(

            "❌ لطفاً شات یا متن رسید "
            "تراکنش را ارسال کنید."
        )

        return

    data["deposits"][
        request_id
    ] = request

    save_data()

    try:

        await send_deposit_to_owner(
            context,
            request
        )

    except Exception as e:

        print(
            "DEPOSIT OWNER ERROR:",
            e
        )

        data["deposits"].pop(
            request_id,
            None
        )

        save_data()

        await update.message.reply_text(

            "❌ ارسال رسید به مالک انجام نشد.\n"
            "لطفاً دوباره تلاش کنید."
        )

        return

    DEPOSIT_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "✅ رسید شما برای مالک ارسال شد.\n\n"

        "⏳ منتظر تایید مالک باشید.",

        reply_markup=main_keyboard(uid)
    )


# =========================================================
# DEPOSIT APPROVE / REJECT
# =========================================================

async def deposit_decision(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ فقط مالک اجازه دارد.",
            show_alert=True
        )

        return

    await query.answer()

    try:

        action, request_id = (
            query.data.split(
                ":",
                1
            )
        )

    except Exception:

        await query.message.reply_text(
            "❌ درخواست نامعتبر است."
        )

        return

    request = data["deposits"].get(
        request_id
    )

    if not request:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get(
        "status"
    ) != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    uid = int(
        request["user_id"]
    )

    amount = int(
        request["amount"]
    )

    # -------------------------
    # APPROVE
    # -------------------------

    if action == "dep_ok":

        request["status"] = "approved"

        add_balance(
            uid,
            amount
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(

            "✅ واریز تایید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS"
        )

        try:

            await context.bot.send_message(

                uid,

                "✅ واریز شما تایید شد.\n\n"

                f"💰 مبلغ اضافه شده: "
                f"{amount:,} DOGS\n"

                f"💳 موجودی جدید: "
                f"{get_balance(uid):,} DOGS"

            )

        except Exception:
            pass

    # -------------------------
    # REJECT
    # -------------------------

    elif action == "dep_no":

        request["status"] = "rejected"

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(

            "❌ واریز رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS"
        )

        try:

            await context.bot.send_message(

                uid,

                "❌ درخواست واریز شما توسط مالک رد شد."
            )

        except Exception:
            pass


# =========================================================
# FIND USER
# =========================================================

def find_user_by_username(
    username
):

    username = (
        username
        .replace("@", "")
        .strip()
        .lower()
    )

    for uid, user in data["users"].items():

        saved_username = str(
            user.get(
                "username",
                ""
            )
        ).lower()

        if saved_username == username:

            return int(uid)

    return None


# =========================================================
# TRANSFER START
# =========================================================

async def transfer_start(
    update,
    context
):

    user = update.effective_user

    uid = user.id

    create_user(user)

    # -------------------------------------------------
    # حالت: انتقال 500
    # -------------------------------------------------

    if context.args:

        try:

            amount = int(
                context.args[0]
                .replace(",", "")
                .strip()
            )

        except Exception:

            await update.message.reply_text(
                "❌ مقدار انتقال باید عدد باشد.\n\n"
                "مثال:\n"
                "انتقال 500"
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "❌ مقدار انتقال نامعتبر است."
            )

            return

        TRANSFER_DATA[uid] = {

            "step": "target",

            "amount": amount

        }

        await update.message.reply_text(

            f"💰 مبلغ انتقال: "
            f"{amount:,} DOGS\n\n"

            "👤 حالا آیدی عددی یا @username "
            "گیرنده را ارسال کنید.\n\n"

            "یا روی پیام کاربر ریپلای کنید."

        )

        return

    # -------------------------------------------------
    # حالت: ریپلای
    # -------------------------------------------------

    if update.message.reply_to_message:

        target_user = (
            update.message
            .reply_to_message
            .from_user
        )

        if target_user.id == uid:

            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )

            return

        create_user(
            target_user
        )

        TRANSFER_DATA[uid] = {

            "step": "amount",

            "target":
                target_user.id

        }

        await update.message.reply_text(

            f"👤 گیرنده: "
            f"{target_user.first_name}\n\n"

            "💰 مقدار DOGS را ارسال کنید.\n\n"

            "مثال:\n"
            "500"

        )

        return

    # -------------------------------------------------
    # راهنما
    # -------------------------------------------------

    await update.message.reply_text(

        "👥 انتقال DOGS\n\n"

        "مثال:\n"
        "انتقال 500\n\n"

        "سپس آیدی یا @username گیرنده "
        "را ارسال کنید.\n\n"

        "یا روی پیام کاربر ریپلای کنید "
        "و بنویسید:\n"
        "انتقال"

    )


# =========================================================
# TRANSFER TARGET
# =========================================================

async def transfer_target(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in TRANSFER_DATA:
        return

    state = TRANSFER_DATA[uid]

    if state.get(
        "step"
    ) != "target":

        return

    text = update.message.text.strip()

    target_id = None

    # اگر روی پیام ریپلای شده باشد
    if update.message.reply_to_message:

        target_user = (
            update.message
            .reply_to_message
            .from_user
        )

        target_id = target_user.id

        create_user(
            target_user
        )

    else:

        # آیدی عددی
        try:

            target_id = int(
                text.replace("@", "")
            )

        except Exception:

            # username
            target_id = find_user_by_username(
                text
            )

    if not target_id:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )

        return

    if target_id == uid:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    if str(target_id) not in data["users"]:

        await update.message.reply_text(
            "❌ این کاربر هنوز داخل ربات ثبت نشده است."
        )

        return

    amount = int(
        state["amount"]
    )

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    # انتقال اتمیک ساده
    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    add_balance(
        target_id,
        amount
    )

    TRANSFER_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "✅ انتقال با موفقیت انجام شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n"

        f"👤 گیرنده: "
        f"{target_id}\n\n"

        f"💳 موجودی شما: "
        f"{get_balance(uid):,} DOGS",

        reply_markup=main_keyboard(uid)
    )

    try:

        await context.bot.send_message(

            target_id,

            "💰 انتقال جدید\n\n"

            f"مبلغ "
            f"{amount:,} DOGS "
            "به موجودی شما اضافه شد."

        )

    except Exception:
        pass

# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update, context):

    user = update.effective_user
    uid = user.id

    create_user(user)

    balance = get_balance(uid)

    if balance < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ امکان برداشت ندارید.\n\n"

            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n"

            f"موجودی شما: "
            f"{balance:,} DOGS",

            reply_markup=main_keyboard(uid)
        )

        return

    WITHDRAW_DATA[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n"

        f"موجودی شما: "
        f"{balance:,} DOGS\n\n"

        "مقدار برداشت را ارسال کنید.",

        reply_markup=back_keyboard()
    )


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

async def withdraw_amount(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in WITHDRAW_DATA:
        return

    if WITHDRAW_DATA[uid].get(
        "step"
    ) != "amount":

        return

    try:

        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )

    except Exception:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید."
        )

        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."
        )

        return

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    WITHDRAW_DATA[uid] = {

        "step": "wallet",

        "amount": amount

    }

    await update.message.reply_text(

        f"💰 مبلغ برداشت: "
        f"{amount:,} DOGS\n\n"

        "📥 آدرس ولت مقصد را ارسال کنید.",

        reply_markup=back_keyboard()
    )


# =========================================================
# WITHDRAW WALLET
# =========================================================

async def withdraw_wallet(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in WITHDRAW_DATA:
        return

    if WITHDRAW_DATA[uid].get(
        "step"
    ) != "wallet":

        return

    wallet = (
        update.message.text
        .strip()
    )

    if len(wallet) < 5:

        await update.message.reply_text(
            "❌ آدرس ولت نامعتبر است."
        )

        return

    amount = int(
        WITHDRAW_DATA[uid]["amount"]
    )

    if get_balance(uid) < amount:

        WITHDRAW_DATA.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    # رزرو مبلغ
    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ برداشت انجام نشد."
        )

        return

    request_id = (
        f"W{int(time.time() * 1000)}"
        f"_{uid}"
    )

    request = {

        "request_id": request_id,

        "user_id": uid,

        "amount": amount,

        "wallet": wallet,

        "status": "pending",

        "created":
            datetime.now().isoformat()

    }

    data["withdraws"][
        request_id
    ] = request

    save_data()

    owner = data.get(
        "owner",
        OWNER_ID
    )

    markup = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data=f"with_ok:{request_id}"
            ),

            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"with_no:{request_id}"
            )

        ]

    ])

    try:

        await context.bot.send_message(

            owner,

            "💰 درخواست برداشت جدید\n\n"

            f"🆔 درخواست: "
            f"{request_id}\n"

            f"👤 کاربر: "
            f"{uid}\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS\n\n"

            f"📥 ولت مقصد:\n"
            f"{wallet}",

            reply_markup=markup
        )

    except Exception:

        # اگر ارسال به مالک نشد،
        # مبلغ به کاربر برگردد.

        add_balance(
            uid,
            amount
        )

        data["withdraws"].pop(
            request_id,
            None
        )

        save_data()

        await update.message.reply_text(

            "❌ ارسال درخواست به مالک انجام نشد.\n"
            "مبلغ به موجودی شما برگشت."
        )

        return

    WITHDRAW_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "✅ درخواست برداشت ارسال شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        "⏳ مبلغ تا تایید یا رد مالک "
        "رزرو شده است.",

        reply_markup=main_keyboard(uid)
    )


# =========================================================
# WITHDRAW DECISION
# =========================================================

async def withdraw_decision(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await query.answer()

    try:

        action, request_id = (
            query.data.split(
                ":",
                1
            )
        )

    except Exception:

        return

    request = data["withdraws"].get(
        request_id
    )

    if not request:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get(
        "status"
    ) != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    uid = int(
        request["user_id"]
    )

    amount = int(
        request["amount"]
    )

    if action == "with_ok":

        request["status"] = "approved"

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(

            "✅ برداشت تایید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS"

        )

        try:

            await context.bot.send_message(

                uid,

                "✅ برداشت شما تایید شد.\n\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n\n"

                "پرداخت را طبق اطلاعات ثبت‌شده "
                "انجام دهید."

            )

        except Exception:
            pass

    else:

        request["status"] = "rejected"

        # برگشت مبلغ
        add_balance(
            uid,
            amount
        )

        save_data()

        await query.message.edit_reply_markup(
            reply_markup=None
        )

        await query.message.reply_text(

            "❌ برداشت رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ برگشتی: "
            f"{amount:,} DOGS"

        )

        try:

            await context.bot.send_message(

                uid,

                "❌ برداشت شما رد شد.\n\n"

                f"💰 مبلغ "
                f"{amount:,} DOGS "
                "به موجودی شما برگشت."

            )

        except Exception:
            pass


# =========================================================
# PROFILE
# =========================================================

async def profile(
    update,
    context
):

    user = update.effective_user

    uid = user.id

    create_user(user)

    u = data["users"][
        str(uid)
    ]

    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 ID: {uid}\n"

        f"👤 نام: "
        f"{u.get('name', '')}\n"

        f"📱 شماره: "
        f"{u.get('phone') or 'ثبت نشده'}\n\n"

        f"💰 موجودی: "
        f"{get_balance(uid):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{int(u.get('refs', 0))}\n\n"

        f"🎮 تعداد بازی: "
        f"{int(u.get('games', 0))}\n"

        f"🏆 برد: "
        f"{int(u.get('wins', 0))}\n"

        f"❌ باخت: "
        f"{int(u.get('losses', 0))}",

        reply_markup=main_keyboard(uid)
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update,
    context
):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "پیام خود را همینجا ارسال کنید.\n"
        "در اولین فرصت بررسی می‌شود.",

        reply_markup=main_keyboard(
            update.effective_user.id
        )
    )


# =========================================================
# OWNER PANEL KEYBOARD
# =========================================================

def owner_panel_keyboard():

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "💰 شارژ موجودی",
                callback_data="adm_add"
            ),

            InlineKeyboardButton(
                "➖ کسر موجودی",
                callback_data="adm_remove"
            )

        ],

        [

            InlineKeyboardButton(
                "👥 جایزه زیرمجموعه",
                callback_data="adm_reward"
            ),

            InlineKeyboardButton(
                "📋 واریزی‌ها",
                callback_data="adm_deposits"
            )

        ],

        [

            InlineKeyboardButton(
                "💸 برداشت‌ها",
                callback_data="adm_withdraws"
            ),

            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="adm_owner"
            )

        ],

        [

            InlineKeyboardButton(
                "🎮 آمار بازی",
                callback_data="adm_games"
            )

        ],

        [

            InlineKeyboardButton(
                "📊 آمار کلی",
                callback_data="adm_stats"
            )

        ]

    ])


# =========================================================
# OWNER PANEL
# =========================================================

async def owner_panel(
    update,
    context
):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ دسترسی ندارید."
        )

        return

    await update.message.reply_text(

        "⚙️ پنل مدیریت\n\n"
        "یکی از گزینه‌ها را انتخاب کنید.",

        reply_markup=owner_panel_keyboard()
    )


# =========================================================
# OWNER CALLBACK
# =========================================================

async def owner_panel_callback(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await query.answer()

    action = query.data

    uid = query.from_user.id

    # -------------------------
    # ADD BALANCE
    # -------------------------

    if action == "adm_add":

        OWNER_STATE[uid] = {

            "action": "add",

            "step": "user"

        }

        await query.message.reply_text(
            "🆔 آیدی کاربر را ارسال کنید."
        )

    # -------------------------
    # REMOVE BALANCE
    # -------------------------

    elif action == "adm_remove":

        OWNER_STATE[uid] = {

            "action": "remove",

            "step": "user"

        }

        await query.message.reply_text(
            "🆔 آیدی کاربر را ارسال کنید."
        )

    # -------------------------
    # REF REWARD
    # -------------------------

    elif action == "adm_reward":

        OWNER_STATE[uid] = {

            "action": "reward",

            "step": "amount"

        }

        await query.message.reply_text(

            f"💰 پاداش فعلی: "
            f"{int(data.get('ref_reward', 50)):,} DOGS\n\n"

            "مقدار جدید را ارسال کنید."
        )

    # -------------------------
    # OWNER TRANSFER
    # -------------------------

    elif action == "adm_owner":

        OWNER_STATE[uid] = {

            "action": "owner",

            "step": "user"

        }

        await query.message.reply_text(
            "👑 آیدی مالک جدید را ارسال کنید."
        )

    # -------------------------
    # DEPOSITS
    # -------------------------

    elif action == "adm_deposits":

        pending = [

            item

            for item in data["deposits"].values()

            if item.get(
                "status"
            ) == "pending"

        ]

        if not pending:

            await query.message.reply_text(
                "📋 واریزی معلقی وجود ندارد."
            )

            return

        text = (
            "📋 واریزی‌های در انتظار\n\n"
        )

        for item in pending[-20:]:

            text += (

                f"🆔 {item['request_id']}\n"

                f"👤 {item['user_id']}\n"

                f"💰 {item['amount']:,} DOGS\n"

                "🐶 ULTRA\n\n"

            )

        await query.message.reply_text(
            text
        )

    # -------------------------
    # WITHDRAWS
    # -------------------------

    elif action == "adm_withdraws":

        pending = [

            item

            for item in data["withdraws"].values()

            if item.get(
                "status"
            ) == "pending"

        ]

        if not pending:

            await query.message.reply_text(
                "💸 برداشت معلقی وجود ندارد."
            )

            return

        text = (
            "💸 برداشت‌های در انتظار\n\n"
        )

        for item in pending[-20:]:

            text += (

                f"🆔 {item['request_id']}\n"

                f"👤 {item['user_id']}\n"

                f"💰 {item['amount']:,} DOGS\n"

                f"📥 {item['wallet']}\n\n"

            )

        await query.message.reply_text(
            text
        )

    # -------------------------
    # GAME STATS
    # -------------------------

    elif action == "adm_games":

        stats = data.get(
            "game_stats",
            {}
        )

        await query.message.reply_text(

            "🎮 آمار بازی\n\n"

            f"🎮 کل بازی‌ها: "
            f"{int(stats.get('total_games', 0))}\n"

            f"🏁 بازی‌های تمام‌شده: "
            f"{int(stats.get('finished_games', 0))}\n"

            f"❌ بازی‌های لغوشده: "
            f"{int(stats.get('cancelled_games', 0))}"

        )

    # -------------------------
    # GENERAL STATS
    # -------------------------

    elif action == "adm_stats":

        users = len(
            data["users"]
        )

        total_balance = sum(

            get_balance(uid)

            for uid in data["users"]

        )

        await query.message.reply_text(

            "📊 آمار کلی\n\n"

            f"👥 کاربران: "
            f"{users}\n\n"

            f"💰 مجموع موجودی: "
            f"{total_balance:,} DOGS\n\n"

            f"🎮 کل بازی‌ها: "
            f"{int(data.get('game_stats', {}).get('total_games', 0))}"

        )

# =========================================================
# OWNER STATE
# =========================================================

async def owner_state_receive(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):
        return

    if uid not in OWNER_STATE:
        return

    state = OWNER_STATE[uid]

    text = update.message.text.strip()

    # =====================================================
    # ADD / REMOVE BALANCE
    # =====================================================

    if state["action"] in ["add", "remove"]:

        if state["step"] == "user":

            try:
                target = int(
                    text.replace("@", "").strip()
                )
            except Exception:
                await update.message.reply_text(
                    "❌ آیدی باید عدد باشد."
                )
                return

            if str(target) not in data["users"]:

                await update.message.reply_text(
                    "❌ این کاربر داخل ربات ثبت نشده است."
                )
                return

            state["target"] = target
            state["step"] = "amount"

            await update.message.reply_text(
                "💰 مقدار DOGS را ارسال کنید."
            )

            return

        if state["step"] == "amount":

            try:
                amount = int(
                    text.replace(",", "").strip()
                )
            except Exception:

                await update.message.reply_text(
                    "❌ مقدار باید عدد باشد."
                )
                return

            if amount <= 0:

                await update.message.reply_text(
                    "❌ مقدار نامعتبر است."
                )
                return

            target = state["target"]

            if state["action"] == "add":

                add_balance(
                    target,
                    amount
                )

                result = (
                    "✅ شارژ انجام شد.\n\n"
                    f"👤 کاربر: {target}\n"
                    f"💰 مبلغ: {amount:,} DOGS\n"
                    f"💳 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

            else:

                if get_balance(target) < amount:

                    await update.message.reply_text(
                        "❌ موجودی کاربر برای کسر "
                        "این مقدار کافی نیست."
                    )
                    return

                remove_balance(
                    target,
                    amount
                )

                result = (
                    "✅ کسر موجودی انجام شد.\n\n"
                    f"👤 کاربر: {target}\n"
                    f"💰 مبلغ کسر شده: "
                    f"{amount:,} DOGS\n"
                    f"💳 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

            OWNER_STATE.pop(
                uid,
                None
            )

            await update.message.reply_text(
                result,
                reply_markup=main_keyboard(uid)
            )

            return

    # =====================================================
    # REFERRAL REWARD
    # =====================================================

    if state["action"] == "reward":

        try:
            amount = int(
                text.replace(",", "").strip()
            )
        except Exception:

            await update.message.reply_text(
                "❌ مقدار باید عدد باشد."
            )
            return

        if amount < 0:

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )
            return

        data["ref_reward"] = amount

        save_data()

        OWNER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(

            "✅ جایزه زیرمجموعه تغییر کرد.\n\n"

            f"💰 جایزه جدید: "
            f"{amount:,} DOGS",

            reply_markup=main_keyboard(uid)
        )

        return

    # =====================================================
    # OWNER TRANSFER
    # =====================================================

    if state["action"] == "owner":

        if state["step"] != "user":
            return

        try:
            new_owner = int(
                text.replace("@", "").strip()
            )
        except Exception:

            await update.message.reply_text(
                "❌ آیدی باید عدد باشد."
            )
            return

        if str(new_owner) not in data["users"]:

            await update.message.reply_text(
                "❌ این کاربر هنوز داخل ربات ثبت نشده است."
            )
            return

        OWNER_STATE[uid] = {
            "action": "owner_confirm",
            "target": new_owner
        }

        await update.message.reply_text(

            "⚠️ انتقال مالکیت\n\n"

            f"👤 آیدی مالک جدید:\n"
            f"{new_owner}\n\n"

            "آیا مطمئن هستید؟",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=
                        f"owner_yes:{new_owner}"
                    ),

                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data=
                        "owner_no"
                    )

                ]

            ])

        )

        return


# =========================================================
# OWNER TRANSFER CALLBACK
# =========================================================

async def owner_transfer_decision(
    update,
    context
):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await query.answer()

    if query.data == "owner_no":

        OWNER_STATE.pop(
            query.from_user.id,
            None
        )

        await query.message.reply_text(
            "❌ انتقال مالکیت لغو شد."
        )

        return

    try:

        new_owner = int(
            query.data.split(
                ":",
                1
            )[1]
        )

    except Exception:

        await query.message.reply_text(
            "❌ خطا در انتقال مالکیت."
        )

        return

    if str(new_owner) not in data["users"]:

        await query.message.reply_text(
            "❌ کاربر پیدا نشد."
        )

        return

    old_owner = data.get(
        "owner",
        OWNER_ID
    )

    data["owner"] = new_owner

    save_data()

    OWNER_STATE.pop(
        query.from_user.id,
        None
    )

    await query.message.reply_text(

        "✅ انتقال مالکیت انجام شد.\n\n"

        f"👑 مالک قبلی: {old_owner}\n"

        f"👑 مالک جدید: {new_owner}"

    )

    try:

        await context.bot.send_message(

            new_owner,

            "👑 تبریک!\n\n"
            "شما مالک جدید ربات شدید."

        )

    except Exception:
        pass


# =========================================================
# GAME SYSTEM
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=
                f"game_join:{game_id}"
            )

        ],

        [

            InlineKeyboardButton(
                "❌ لغو بازی",
                callback_data=
                f"game_cancel:{game_id}"
            )

        ]

    ])


# =========================================================
# CREATE GAME
# =========================================================

async def game_create(
    update,
    context
):

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in [
        "group",
        "supergroup"
    ]:

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ قابل انجام است."
        )

        return

    create_user(user)

    if not context.args:

        await update.message.reply_text(

            "🎮 بازی DOGS\n\n"

            "مثال:\n"
            "/game 500\n\n"

            f"حداقل بازی: "
            f"{MIN_GAME:,} DOGS\n"

            f"حداکثر بازی: "
            f"{MAX_GAME:,} DOGS\n\n"

            "👥 بعد از ساخت بازی، "
            "دوست شما می‌تواند وارد شود."

        )

        return

    try:

        amount = int(
            context.args[0]
            .replace(",", "")
            .strip()
        )

    except Exception:

        await update.message.reply_text(
            "❌ مبلغ بازی باید عدد باشد."
        )

        return

    # =====================================================
    # GAME LIMIT
    # =====================================================

    if amount < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل بازی "
            f"{MIN_GAME:,} DOGS است."

        )

        return

    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر بازی "
            f"{MAX_GAME:,} DOGS است."

        )

        return

    # =====================================================
    # BALANCE
    # =====================================================

    if get_balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{get_balance(user.id):,} DOGS"

        )

        return

    # =====================================================
    # RESERVE CREATOR MONEY
    # =====================================================

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    # =====================================================
    # CREATE GAME ID
    # =====================================================

    game_id = (
        f"{chat.id}_"
        f"{user.id}_"
        f"{int(time.time() * 1000)}"
    )

    GAMES[game_id] = {

        "game_id": game_id,

        "chat_id": chat.id,

        "creator": user.id,

        "creator_name":
            user.first_name or "کاربر",

        "bet": amount,

        "joiner": None,

        "joiner_name": "",

        "status": "waiting",

        "message_id": None,

        "created":
            datetime.now().isoformat()

    }

    message = await update.message.reply_text(

        "🎮 بازی جدید ساخته شد!\n\n"

        f"💰 مبلغ بازی: "
        f"{amount:,} DOGS\n\n"

        f"👤 سازنده: "
        f"{user.first_name}\n\n"

        "👥 یک دوست می‌تواند وارد بازی شود.\n\n"

        "👇 برای ورود روی دکمه زیر بزنید.",

        reply_markup=
        game_keyboard(game_id)

    )

    GAMES[game_id][
        "message_id"
    ] = message.message_id


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    try:

        action, game_id = (
            query.data.split(
                ":",
                1
            )
        )

    except Exception:
        return

    game = GAMES.get(
        game_id
    )

    if not game:

        await query.message.reply_text(
            "❌ بازی پیدا نشد."
        )

        return

    uid = query.from_user.id

    # =====================================================
    # CANCEL GAME
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:

            await query.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True
            )

            return

        if game["status"] != "waiting":

            await query.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True
            )

            return

        amount = game["bet"]

        add_balance(
            game["creator"],
            amount
        )

        game["status"] = "cancelled"

        stats = data.setdefault(
            "game_stats",
            {
                "total_games": 0,
                "finished_games": 0,
                "cancelled_games": 0
            }
        )

        stats["cancelled_games"] = (
            int(stats.get(
                "cancelled_games",
                0
            )) + 1
        )

        save_data()

        await query.message.edit_text(

            "❌ بازی لغو شد.\n\n"

            f"💰 مبلغ "
            f"{amount:,} DOGS "
            "به موجودی سازنده برگشت."

        )

        return

    # =====================================================
    # JOIN GAME
    # =====================================================

    if action == "game_join":

        if game["status"] != "waiting":

            await query.answer(
                "❌ این بازی قبلاً شروع شده.",
                show_alert=True
            )

            return

        if uid == game["creator"]:

            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )

            return

        create_user(
            query.from_user
        )

        amount = game["bet"]

        if get_balance(uid) < amount:

            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return

        if not remove_balance(
            uid,
            amount
        ):

            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return

        game["joiner"] = uid

        game["joiner_name"] = (
            query.from_user.first_name
            or "کاربر"
        )

        game["status"] = "playing"

        # =================================================
        # UPDATE GAME MESSAGE
        # =================================================

        await query.message.edit_text(

            "🎮 بازی شروع شد!\n\n"

            f"👤 بازیکن اول:\n"
            f"{game['creator_name']}\n\n"

            f"👤 بازیکن دوم:\n"
            f"{game['joiner_name']}\n\n"

            f"💰 مبلغ هر نفر:\n"
            f"{amount:,} DOGS\n\n"

            "🎲 در حال تعیین برنده..."

        )

        # =================================================
        # FAIR RANDOM RESULT
        # =================================================

        winner = random.choice([

            game["creator"],

            game["joiner"]

        ])

        if winner == game["creator"]:

            loser = game["joiner"]

            winner_name = (
                game["creator_name"]
            )

            loser_name = (
                game["joiner_name"]
            )

        else:

            loser = game["creator"]

            winner_name = (
                game["joiner_name"]
            )

            loser_name = (
                game["creator_name"]
            )

        # =================================================
        # PRIZE
        # =================================================

        # مجموع شرط دو نفر
        total_pot = amount * 2

        # طبق قانون بازی:
        # برنده 90 درصد
        # مالک 10 درصد

        owner_fee = (
            total_pot // 10
        )

        winner_reward = (
            total_pot - owner_fee
        )

        add_balance(
            winner,
            winner_reward
        )

        owner = data.get(
            "owner",
            OWNER_ID
        )

        # 10 درصد برای مالک
        add_balance(
            owner,
            owner_fee
        )

        # =================================================
        # STATS
        # =================================================

        creator_data = data["users"].get(
            str(game["creator"])
        )

        joiner_data = data["users"].get(
            str(game["joiner"])
        )

        if creator_data:

            creator_data["games"] = (
                int(
                    creator_data.get(
                        "games",
                        0
                    )
                ) + 1
            )

        if joiner_data:

            joiner_data["games"] = (
                int(
                    joiner_data.get(
                        "games",
                        0
                    )
                ) + 1
            )

        if winner == game["creator"]:

            creator_data["wins"] = (
                int(
                    creator_data.get(
                        "wins",
                        0
                    )
                ) + 1
            )

            joiner_data["losses"] = (
                int(
                    joiner_data.get(
                        "losses",
                        0
                    )
                ) + 1
            )

        else:

            joiner_data["wins"] = (
                int(
                    joiner_data.get(
                        "wins",
                        0
                    )
                ) + 1
            )

            creator_data["losses"] = (
                int(
                    creator_data.get(
                        "losses",
                        0
                    )
                ) + 1
            )

        stats = data.setdefault(
            "game_stats",
            {
                "total_games": 0,
                "finished_games": 0,
                "cancelled_games": 0
            }
        )

        stats["finished_games"] = (
            int(
                stats.get(
                    "finished_games",
                    0
                )
            ) + 1
        )

        stats["total_games"] = (
            int(
                stats.get(
                    "total_games",
                    0
                )
            ) + 1
        )

        game["winner"] = winner

        game["loser"] = loser

        game["owner_fee"] = owner_fee

        game["winner_reward"] = (
            winner_reward
        )

        game["status"] = "finished"

        save_data()

        # =================================================
        # RESULT
        # =================================================

        result = (

            "🏆 نتیجه بازی\n\n"

            f"🥇 برنده:\n"
            f"{winner_name}\n\n"

            f"💔 بازنده:\n"
            f"{loser_name}\n\n"

            f"💰 مبلغ هر نفر:\n"
            f"{amount:,} DOGS\n\n"

            f"🏆 جایزه برنده:\n"
            f"{winner_reward:,} DOGS\n\n"

            f"👑 سهم مالک:\n"
            f"{owner_fee:,} DOGS"

        )

        await query.message.edit_text(
            result
        )

        # =================================================
        # MESSAGE WINNER
        # =================================================

        try:

            await context.bot.send_message(

                winner,

                "🎉 تبریک!\n\n"

                "شما برنده بازی شدید.\n\n"

                f"🏆 جایزه:\n"
                f"{winner_reward:,} DOGS\n\n"

                f"💰 موجودی جدید:\n"
                f"{get_balance(winner):,} DOGS"

            )

        except Exception:
            pass

        # =================================================
        # MESSAGE LOSER
        # =================================================

        try:

            await context.bot.send_message(

                loser,

                "❌ بازی را باختید.\n\n"

                f"💰 مبلغ بازی:\n"
                f"{amount:,} DOGS"

            )

        except Exception:
            pass

        return

# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    text = text.strip()

    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    # =====================================================
    # ACTIVE STATES
    # =====================================================

    if uid in OWNER_STATE:

        await owner_state_receive(
            update,
            context
        )

        return

    if uid in TRANSFER_DATA:

        await transfer_amount(
            update,
            context
        )

        return

    if uid in DEPOSIT_DATA:

        step = DEPOSIT_DATA[
            uid
        ].get("step")

        if step == "amount":

            await deposit_amount(
                update,
                context
            )

            return

        if step == "receipt":

            await deposit_receipt(
                update,
                context
            )

            return

    if uid in WITHDRAW_DATA:

        step = WITHDRAW_DATA[
            uid
        ].get("step")

        if step == "amount":

            await withdraw_amount(
                update,
                context
            )

            return

        if step == "wallet":

            await withdraw_wallet(
                update,
                context
            )

            return

    # =====================================================
    # MAIN MENU
    # =====================================================

    if text == "💳 واریزی":

        await deposit_start(
            update,
            context
        )

        return

    if text == "💰 برداشت":

        await withdraw_start(
            update,
            context
        )

        return

    if text == "👥 زیرمجموعه":

        await referral_menu(
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

    if text == "👤 پروفایل":

        await profile(
            update,
            context
        )

        return

    if text == "👥 انتقال":

        await transfer_start(
            update,
            context
        )

        return

    if text == "⚙️ پنل مدیریت":

        await owner_panel(
            update,
            context
        )

        return

    if text == "🔙 برگشت":

        await update.message.reply_text(

            "🏠 منوی اصلی",

            reply_markup=
            main_keyboard(uid)

        )

        return


# =========================================================
# PHOTO ROUTER
# =========================================================

async def photo_router(
    update,
    context
):

    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    if uid in DEPOSIT_DATA:

        if DEPOSIT_DATA[uid].get(
            "step"
        ) == "receipt":

            await deposit_receipt(
                update,
                context
            )

            return


# =========================================================
# CONTACT ROUTER
# =========================================================

async def contact_router(
    update,
    context
):

    await phone_receive(
        update,
        context
    )


# =========================================================
# COMMAND: TRANSFER
# =========================================================

async def transfer_command(
    update,
    context
):

    await transfer_start(
        update,
        context
    )


# =========================================================
# COMMAND: GAME
# =========================================================

async def game_command(
    update,
    context
):

    await game_create(
        update,
        context
    )


# =========================================================
# COMMAND: ADMIN
# =========================================================

async def admin_command(
    update,
    context
):

    await owner_panel(
        update,
        context
    )


# =========================================================
# COMMAND: START
# =========================================================

async def start_command(
    update,
    context
):

    await start(
        update,
        context
    )


# =========================================================
# FORCE JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    uid = query.from_user.id

    ok = await check_join(
        uid,
        context
    )

    if not ok:

        await query.answer(

            "❌ ابتدا عضو کانال و گپ شوید.",

            show_alert=True

        )

        return

    create_user(
        query.from_user
    )

    user_data = data[
        "users"
    ][
        str(uid)
    ]

    if not user_data.get(
        "phone"
    ):

        try:

            await query.message.delete()

        except Exception:
            pass

        await context.bot.send_message(

            uid,

            "📱 شماره خود را ارسال کنید.\n\n"

            "فقط شماره ایران +98 قبول است.",

            reply_markup=
            phone_keyboard()

        )

        return

    try:

        await query.message.edit_text(
            "✅ عضویت شما تایید شد."
        )

    except Exception:
        pass

    await context.bot.send_message(

        uid,

        "🏠 منوی اصلی\n\n"

        f"💰 موجودی: "
        f"{get_balance(uid):,} DOGS",

        reply_markup=
        main_keyboard(uid)

    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    error = context.error

    print(
        "================================"
    )

    print(
        "BOT ERROR:"
    )

    print(
        repr(error)
    )

    traceback.print_exception(

        type(error),

        error,

        error.__traceback__

    )

    print(
        "================================"
    )


# =========================================================
# APPLICATION
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(

            "BOT_TOKEN environment variable "
            "is missing."

        )

    application = (

        Application

        .builder()

        .token(BOT_TOKEN)

        .build()

    )

    # =====================================================
    # COMMANDS
    # =====================================================

    application.add_handler(

        CommandHandler(
            "start",
            start_command
        )

    )

    application.add_handler(

        CommandHandler(
            "transfer",
            transfer_command
        )

    )

    application.add_handler(

        CommandHandler(
            "game",
            game_command
        )

    )

    application.add_handler(

        CommandHandler(
            "admin",
            admin_command
        )

    )

    application.add_handler(

        CommandHandler(
            "transferowner",
            transfer_owner_command
        )

    )

    # =====================================================
    # JOIN
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(

            check_join_callback,

            pattern=r"^check_join$"

        )

    )

    # =====================================================
    # DEPOSIT
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(

            deposit_type,

            pattern=r"^dep_(ultra|exchange)$"

        )

    )

    application.add_handler(

        CallbackQueryHandler(

            deposit_decision,

            pattern=r"^dep_(ok|no):"

        )

    )

    # =====================================================
    # WITHDRAW
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(

            withdraw_decision,

            pattern=r"^with_(ok|no):"

        )

    )

    # =====================================================
    # OWNER
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(

            owner_transfer_decision,

            pattern=r"^owner_(yes|no):?"

        )

    )

    application.add_handler(

        CallbackQueryHandler(

            owner_panel_callback,

            pattern=r"^adm_"

        )

    )

    # =====================================================
    # GAME
    # =====================================================

    application.add_handler(

        CallbackQueryHandler(

            game_callback,

            pattern=r"^game_(join|cancel):"

        )

    )

    # =====================================================
    # CONTACT
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.CONTACT,

            contact_router

        )

    )

    # =====================================================
    # PHOTO
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_router

        )

    )

    # =====================================================
    # TEXT
    # =====================================================

    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_router

        )

    )

    # =====================================================
    # ERRORS
    # =====================================================

    application.add_error_handler(
        error_handler
    )

    print(
        "================================"
    )

    print(
        "BOT STARTED"
    )

    print(
        "MIN GAME:",
        MIN_GAME
    )

    print(
        "MAX GAME:",
        MAX_GAME
    )

    print(
        "MIN DEPOSIT:",
        MIN_DEPOSIT
    )

    print(
        "MIN WITHDRAW:",
        MIN_WITHDRAW
    )

    print(
        "================================"
    )

    application.run_polling(

        drop_pending_updates=True,

        allowed_updates=
        Update.ALL_TYPES

    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()
