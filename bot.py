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

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "data.json"


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
}


# =========================================================
# LOAD DATA
# =========================================================

def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                loaded = json.load(f)

            if isinstance(loaded, dict):

                for key, value in DEFAULT_DATA.items():

                    if key not in loaded:

                        loaded[key] = json.loads(
                            json.dumps(value)
                        )

                return loaded

    except Exception as e:

        print(
            "LOAD ERROR:",
            e
        )

    return json.loads(
        json.dumps(DEFAULT_DATA)
    )


data = load_data()


# =========================================================
# SAVE DATA
# =========================================================

def save_data():

    try:

        temp_file = DATA_FILE + ".tmp"

        with open(
            temp_file,
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
            temp_file,
            DATA_FILE
        )

    except Exception:

        traceback.print_exc()


# =========================================================
# STATES
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

def anti_spam(
    uid,
    seconds=1.5
):

    now = time.time()

    key = str(uid)

    old = CLICK.get(
        key,
        0
    )

    if now - old < seconds:

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
        }

        save_data()
        return

    u = data["users"][uid]

    u["id"] = user.id

    u["name"] = (
        user.first_name
        or u.get("name", "")
    )

    u["username"] = (
        user.username
        or u.get("username", "")
    )

    u.setdefault(
        "phone",
        ""
    )

    u.setdefault(
        "balance",
        0
    )

    u.setdefault(
        "refs",
        0
    )

    u.setdefault(
        "ref_by",
        None
    )


def get_balance(uid):

    try:

        return int(
            data["users"]
            [str(uid)]
            ["balance"]
        )

    except Exception:

        return 0


def add_balance(
    uid,
    amount
):

    uid = str(uid)

    if uid not in data["users"]:
        return False

    try:

        amount = int(amount)

    except Exception:

        return False

    data["users"][uid]["balance"] = (
        get_balance(uid)
        + amount
    )

    if data["users"][uid]["balance"] < 0:

        data["users"][uid]["balance"] = 0

    save_data()

    return True


def remove_balance(
    uid,
    amount
):

    try:

        amount = int(amount)

    except Exception:

        return False

    if amount < 0:
        return False

    if get_balance(uid) < amount:
        return False

    return add_balance(
        uid,
        -amount
    )


def is_owner(uid):

    try:

        return (
            int(uid)
            == int(
                data.get(
                    "owner",
                    OWNER_ID
                )
            )
        )

    except Exception:

        return False


# =========================================================
# KEYBOARDS
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


def back_keyboard():

    return ReplyKeyboardMarkup(
        [["🔙 برگشت"]],
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


# =========================================================
# PHONE
# =========================================================

def clean_phone(phone):

    if not phone:
        return None

    phone = (
        phone
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if phone.startswith("0098"):

        phone = "+" + phone[2:]

    elif phone.startswith("98"):

        phone = "+" + phone

    if phone.startswith("+98"):

        return phone

    return None


async def phone_receive(
    update,
    context
):

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
            "❌ فقط شماره ایران با +98 قبول است."
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

        reply_markup=
        main_keyboard(user.id)
    )


# =========================================================
# REFERRAL
# =========================================================

async def process_referral(
    update,
    context
):

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

    if data["users"][uid].get(
        "ref_by"
    ):

        return

    if str(ref_id) not in data["users"]:

        return

    data["users"][uid][
        "ref_by"
    ] = ref_id

    data["users"][
        str(ref_id)
    ]["refs"] = (

        int(
            data["users"][
                str(ref_id)
            ].get(
                "refs",
                0
            )
        ) + 1
    )

    reward = int(
        data.get(
            "ref_reward",
            50
        )
    )

    add_balance(
        ref_id,
        reward
    )

    save_data()


# =========================================================
# START
# =========================================================

async def start(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    await process_referral(
        update,
        context
    )

    joined = await check_join(
        user.id,
        context
    )

    if not joined:

        await update.message.reply_text(

            "❌ برای استفاده از ربات ابتدا "
            "در کانال و گپ عضو شوید.\n\n"
            "بعد از عضویت روی "
            "«✅ بررسی عضویت» بزنید.",

            reply_markup=
            join_keyboard()
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(

            "📱 شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط شماره ایران با +98 قبول است.",

            reply_markup=
            phone_keyboard()
        )

        return

    await update.message.reply_text(

        "✅ ورود موفق بود.\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",

        reply_markup=
        main_keyboard(user.id)
    )


# =========================================================
# JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if await check_join(
        uid,
        context
    ):

        create_user(
            q.from_user
        )

        if not data["users"][
            str(uid)
        ].get("phone"):

            try:

                await q.message.delete()

            except Exception:

                pass

            await context.bot.send_message(

                uid,

                "📱 شماره خود را ارسال کنید.\n\n"
                "⚠️ فقط شماره ایران با +98 قبول است.",

                reply_markup=
                phone_keyboard()
            )

        else:

            await q.message.reply_text(

                "✅ عضویت شما تایید شد.",

                reply_markup=
                main_keyboard(uid)
            )

    else:

        await q.answer(

            "❌ هنوز عضو کانال و گپ نشده‌اید.",

            show_alert=True
        )

# =========================================================
# DEPOSIT - ULTRA ONLY
# =========================================================

async def deposit_start(update, context):

    user = update.effective_user
    create_user(user)

    if not anti_spam(user.id):
        return

    await update.message.reply_text(

        "🐶 واریز ULTRA\n\n"

        "مقدار DOGS را وارد کنید.\n\n"

        "مثال:\n"
        "5000\n\n"

        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_keyboard()
    )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def deposit_amount(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in DEPOSIT_DATA:
        return

    if DEPOSIT_DATA[uid].get(
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
            "❌ مقدار باید فقط عدد باشد.\n\n"
            "مثال:\n"
            "5000"
        )

        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."
        )

        return

    DEPOSIT_DATA[uid][
        "amount"
    ] = amount

    DEPOSIT_DATA[uid][
        "step"
    ] = "receipt"

    await update.message.reply_text(

        "💳 فرصت واریز:\n\n"

        f"ULTRA {amount:,} DOGS {ULTRA_ID}\n\n"

        f"حداقل واریز {MIN_DEPOSIT:,}\n\n"

        "📸 شات خود یا رسید پیام را ارسال کنید."
    )


# =========================================================
# DEPOSIT REQUEST ID
# =========================================================

def make_deposit_id(uid):

    return (
        f"D"
        f"{int(time.time() * 1000)}"
        f"_{uid}"
    )


# =========================================================
# OWNER BUTTONS
# =========================================================

def deposit_buttons(req_id):

    return InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید",
                callback_data=
                f"dep_ok:{req_id}"
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=
                f"dep_no:{req_id}"
            )

        ]

    ])


# =========================================================
# SEND DEPOSIT TO OWNER
# =========================================================

async def send_deposit_to_owner(
    context,
    req
):

    owner_id = data.get(
        "owner",
        OWNER_ID
    )

    caption = (

        "💳 درخواست واریزی جدید\n\n"

        f"🆔 درخواست: "
        f"{req['request_id']}\n"

        f"👤 کاربر: "
        f"{req['user_id']}\n"

        f"💰 مبلغ: "
        f"{req['amount']:,} DOGS\n"

        f"🐶 روش: ULTRA\n\n"

        "لطفاً بررسی کنید."
    )

    markup = deposit_buttons(
        req["request_id"]
    )

    if req["kind"] == "photo":

        await context.bot.send_photo(

            chat_id=owner_id,

            photo=req["content"],

            caption=caption,

            reply_markup=markup
        )

    else:

        await context.bot.send_message(

            chat_id=owner_id,

            text=(
                caption
                + "\n\n"
                + "🧾 رسید:\n"
                + req["content"]
            ),

            reply_markup=markup
        )


# =========================================================
# RECEIVE DEPOSIT RECEIPT
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

    info = DEPOSIT_DATA[uid]

    amount = int(
        info["amount"]
    )

    req_id = make_deposit_id(
        uid
    )

    # =====================================================
    # PHOTO
    # =====================================================

    if update.message.photo:

        content = (
            update.message
            .photo[-1]
            .file_id
        )

        req = {

            "request_id":
                req_id,

            "user_id":
                uid,

            "amount":
                amount,

            "type":
                "ULTRA",

            "kind":
                "photo",

            "content":
                content,

            "status":
                "pending",

            "created":
                datetime.now()
                .isoformat()
        }

    # =====================================================
    # TEXT RECEIPT
    # =====================================================

    elif update.message.text:

        content = (
            update.message.text
            .strip()
        )

        if not content:

            await update.message.reply_text(
                "❌ رسید معتبر ارسال کنید."
            )

            return

        req = {

            "request_id":
                req_id,

            "user_id":
                uid,

            "amount":
                amount,

            "type":
                "ULTRA",

            "kind":
                "text",

            "content":
                content,

            "status":
                "pending",

            "created":
                datetime.now()
                .isoformat()
        }

    else:

        await update.message.reply_text(

            "❌ لطفاً شات یا رسید پیام "
            "ارسال کنید."
        )

        return

    # =====================================================
    # SAVE
    # =====================================================

    data["deposits"][
        req_id
    ] = req

    save_data()

    # =====================================================
    # SEND TO OWNER
    # =====================================================

    try:

        await send_deposit_to_owner(
            context,
            req
        )

    except Exception as e:

        print(
            "DEPOSIT OWNER ERROR:",
            e
        )

        data["deposits"][
            req_id
        ]["status"] = "error"

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

        "✅ رسید شما ارسال شد.\n\n"

        "⏳ درخواست برای مالک ارسال شد.\n"

        "بعد از بررسی، نتیجه به شما اعلام می‌شود.",

        reply_markup=
        main_keyboard(uid)
    )


# =========================================================
# OWNER DEPOSIT DECISION
# =========================================================

async def deposit_decision(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ فقط مالک اجازه دارد.",
            show_alert=True
        )

        return

    try:

        action, req_id = (
            q.data.split(
                ":",
                1
            )
        )

    except Exception:

        await q.message.reply_text(
            "❌ درخواست نامعتبر است."
        )

        return

    req = data[
        "deposits"
    ].get(req_id)

    if not req:

        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if req.get(
        "status"
    ) != "pending":

        await q.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده است."
        )

        return

    uid = req["user_id"]

    # =====================================================
    # APPROVE
    # =====================================================

    if action == "dep_ok":

        req["status"] = "approved"

        add_balance(
            uid,
            req["amount"]
        )

        save_data()

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(

            "✅ واریز تایید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{req['amount']:,} DOGS"
        )

        try:

            await context.bot.send_message(

                uid,

                "✅ واریز شما تایید شد.\n\n"

                f"➕ مبلغ: "
                f"{req['amount']:,} DOGS\n"

                f"💳 موجودی جدید: "
                f"{get_balance(uid):,} DOGS"
            )

        except Exception:

            pass

        return

    # =====================================================
    # REJECT
    # =====================================================

    req["status"] = "rejected"

    save_data()

    await q.message.edit_reply_markup(
        reply_markup=None
    )

    await q.message.reply_text(

        "❌ واریز رد شد.\n\n"

        f"👤 کاربر: {uid}\n"

        f"💰 مبلغ: "
        f"{req['amount']:,} DOGS"
    )

    try:

        await context.bot.send_message(

            uid,

            "❌ درخواست واریز شما رد شد."
        )

    except Exception:

        pass

# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update, context):

    uid = update.effective_user.id
    create_user(update.effective_user)

    balance = get_balance(uid)

    if balance < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است.\n\n"

            f"💰 موجودی شما: "
            f"{balance:,} DOGS",

            reply_markup=
            main_keyboard(uid)
        )

        return

    WITHDRAW_DATA[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(

        "💰 مقدار برداشت را وارد کنید.\n\n"

        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n"

        f"موجودی شما: "
        f"{balance:,} DOGS",

        reply_markup=
        back_keyboard()
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

        "📥 آدرس ولت مقصد را ارسال کنید."
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
        WITHDRAW_DATA[uid][
            "amount"
        ]
    )

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        WITHDRAW_DATA.pop(
            uid,
            None
        )

        return

    # رزرو مبلغ
    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ انجام برداشت ممکن نیست."
        )

        return

    req_id = (
        f"W"
        f"{int(time.time() * 1000)}"
        f"_{uid}"
    )

    req = {

        "request_id":
            req_id,

        "user_id":
            uid,

        "amount":
            amount,

        "wallet":
            wallet,

        "status":
            "pending",

        "created":
            datetime.now()
            .isoformat()
    }

    data["withdraws"][
        req_id
    ] = req

    save_data()

    # =====================================================
    # OWNER BUTTONS
    # =====================================================

    markup = InlineKeyboardMarkup([

        [

            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data=
                f"with_ok:{req_id}"
            ),

            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=
                f"with_no:{req_id}"
            )

        ]

    ])

    await context.bot.send_message(

        data.get(
            "owner",
            OWNER_ID
        ),

        "💰 درخواست برداشت جدید\n\n"

        f"🆔 درخواست: {req_id}\n"

        f"👤 کاربر: {uid}\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        "📥 ولت مقصد:\n"

        f"{wallet}",

        reply_markup=markup
    )

    WITHDRAW_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "✅ درخواست برداشت ارسال شد.\n\n"

        "⏳ منتظر تایید مالک باشید.\n"

        "💰 مبلغ تا تعیین تکلیف درخواست "
        "رزرو شده.",

        reply_markup=
        main_keyboard(uid)
    )


# =========================================================
# OWNER WITHDRAW DECISION
# =========================================================

async def withdraw_decision(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ فقط مالک اجازه دارد.",
            show_alert=True
        )

        return

    try:

        action, req_id = (
            q.data.split(
                ":",
                1
            )
        )

    except Exception:

        await q.message.reply_text(
            "❌ درخواست نامعتبر است."
        )

        return

    req = data[
        "withdraws"
    ].get(req_id)

    if not req:

        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if req.get(
        "status"
    ) != "pending":

        await q.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده است."
        )

        return

    uid = req["user_id"]
    amount = req["amount"]

    # =====================================================
    # APPROVE
    # =====================================================

    if action == "with_ok":

        req["status"] = "approved"

        save_data()

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(

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
                f"{amount:,} DOGS\n"

                "پرداخت طبق ولت ثبت‌شده انجام می‌شود."
            )

        except Exception:

            pass

        return

    # =====================================================
    # REJECT
    # =====================================================

    req["status"] = "rejected"

    # برگشت مبلغ به کاربر
    add_balance(
        uid,
        amount
    )

    save_data()

    await q.message.edit_reply_markup(
        reply_markup=None
    )

    await q.message.reply_text(

        "❌ برداشت رد شد.\n\n"

        f"👤 کاربر: {uid}\n"

        f"💰 مبلغ برگشتی: "
        f"{amount:,} DOGS"
    )

    try:

        await context.bot.send_message(

            uid,

            "❌ درخواست برداشت شما رد شد.\n\n"

            f"💰 مبلغ "
            f"{amount:,} DOGS "
            "به موجودی شما برگشت."
        )

    except Exception:

        pass


# =========================================================
# TRANSFER - انتقال 500
# =========================================================

async def transfer_command(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    uid = user.id

    # -----------------------------------------------------
    # مثال:
    # انتقال 500
    # -----------------------------------------------------

    if not context.args:

        await update.message.reply_text(

            "👥 انتقال DOGS\n\n"

            "برای انتقال باید روی پیام "
            "کاربر موردنظر ریپلای کنید.\n\n"

            "مثال:\n"
            "انتقال 500\n\n"

            "یعنی 500 DOGS برای همان کاربر ارسال می‌شود."
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

            "❌ مقدار نامعتبر است.\n\n"

            "مثال صحیح:\n"
            "انتقال 500"
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ مقدار باید بیشتر از صفر باشد."
        )

        return

    # -----------------------------------------------------
    # فقط با ریپلای
    # -----------------------------------------------------

    if not update.message.reply_to_message:

        await update.message.reply_text(

            "❌ ابتدا روی پیام کاربر ریپلای کنید.\n\n"

            "مثال:\n"
            "انتقال 500"
        )

        return

    target = (
        update.message
        .reply_to_message
        .from_user
    )

    if not target:

        await update.message.reply_text(
            "❌ گیرنده پیدا نشد."
        )

        return

    if target.id == uid:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return

    create_user(target)

    # -----------------------------------------------------
    # بررسی موجودی
    # -----------------------------------------------------

    if get_balance(uid) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS"
        )

        return

    # -----------------------------------------------------
    # انتقال اتمیک
    # -----------------------------------------------------

    if not remove_balance(
        uid,
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

    # -----------------------------------------------------
    # پیام فرستنده
    # -----------------------------------------------------

    await update.message.reply_text(

        "✅ انتقال با موفقیت انجام شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n"

        f"👤 گیرنده: "
        f"{target.first_name}\n"

        f"💳 موجودی شما: "
        f"{get_balance(uid):,} DOGS"
    )

    # -----------------------------------------------------
    # پیام گیرنده
    # -----------------------------------------------------

    try:

        await context.bot.send_message(

            target.id,

            "💰 یک انتقال برای شما انجام شد.\n\n"

            f"➕ مبلغ: "
            f"{amount:,} DOGS\n"

            f"👤 از طرف: "
            f"{user.first_name}\n"

            f"💳 موجودی جدید: "
            f"{get_balance(target.id):,} DOGS"
        )

    except Exception:

        pass

# =========================================================
# GAME SYSTEM - بازی با دوستان
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=f"game_join:{game_id}"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ لغو بازی",
                callback_data=f"game_cancel:{game_id}"
            )
        ]

    ])


# =========================================================
# CREATE GAME
# =========================================================

async def game_command(
    update,
    context
):

    # بازی فقط داخل گپ
    if update.effective_chat.type not in [
        "group",
        "supergroup"
    ]:

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ قابل انجام است."
        )

        return

    user = update.effective_user

    create_user(user)

    # -----------------------------------------------------
    # بررسی عضو بودن
    # -----------------------------------------------------

    if not await check_join(
        user.id,
        context
    ):

        await update.message.reply_text(
            "❌ ابتدا عضو کانال و گپ شوید."
        )

        return

    # -----------------------------------------------------
    # مبلغ وارد نشده
    # -----------------------------------------------------

    if not context.args:

        await update.message.reply_text(

            "🎮 ساخت بازی\n\n"

            "مثال:\n"
            "بازی 500\n\n"

            f"💰 حداقل بازی: "
            f"{MIN_GAME:,} DOGS\n"

            f"💰 حداکثر بازی: "
            f"{MAX_GAME:,} DOGS"
        )

        return

    # -----------------------------------------------------
    # دریافت مبلغ
    # -----------------------------------------------------

    try:

        bet = int(
            context.args[0]
            .replace(",", "")
            .strip()
        )

    except Exception:

        await update.message.reply_text(

            "❌ مبلغ بازی باید عدد باشد.\n\n"

            "مثال:\n"
            "بازی 500"
        )

        return

    # -----------------------------------------------------
    # حداقل و حداکثر
    # -----------------------------------------------------

    if bet < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل مبلغ بازی "
            f"{MIN_GAME:,} DOGS است."
        )

        return

    if bet > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر مبلغ بازی "
            f"{MAX_GAME:,} DOGS است."
        )

        return

    # -----------------------------------------------------
    # موجودی سازنده
    # -----------------------------------------------------

    if get_balance(user.id) < bet:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی شما: "
            f"{get_balance(user.id):,} DOGS"
        )

        return

    # -----------------------------------------------------
    # رزرو مبلغ سازنده
    # -----------------------------------------------------

    if not remove_balance(
        user.id,
        bet
    ):

        await update.message.reply_text(
            "❌ رزرو مبلغ بازی انجام نشد."
        )

        return

    # -----------------------------------------------------
    # ساخت شناسه بازی
    # -----------------------------------------------------

    game_id = (

        f"{update.effective_chat.id}_"
        f"{int(time.time() * 1000)}_"
        f"{user.id}"
    )

    GAMES[game_id] = {

        "game_id":
            game_id,

        "chat_id":
            update.effective_chat.id,

        "message_id":
            None,

        "creator":
            user.id,

        "creator_name":
            user.first_name or "کاربر",

        "bet":
            bet,

        "joiner":
            None,

        "joiner_name":
            None,

        "status":
            "waiting",

        "winner":
            None,

        "loser":
            None,

        "owner_fee":
            0,

        "winner_reward":
            0
    }

    # -----------------------------------------------------
    # پیام بازی
    # -----------------------------------------------------

    msg = await update.message.reply_text(

        "🎮 بازی جدید ساخته شد!\n\n"

        f"👤 سازنده: "
        f"{user.first_name}\n"

        f"💰 مبلغ بازی: "
        f"{bet:,} DOGS\n\n"

        "👥 یک نفر می‌تواند وارد بازی شود.\n\n"

        "برای شرکت روی دکمه زیر بزنید.",

        reply_markup=
        game_keyboard(game_id)
    )

    GAMES[game_id][
        "message_id"
    ] = msg.message_id


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    try:

        action, game_id = (
            q.data.split(
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

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    uid = q.from_user.id

    # =====================================================
    # CANCEL GAME
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:

            await q.answer(
                "❌ فقط سازنده بازی می‌تواند لغو کند.",
                show_alert=True
            )

            return

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True
            )

            return

        # برگشت پول سازنده
        add_balance(
            game["creator"],
            game["bet"]
        )

        game["status"] = "cancelled"

        await q.message.edit_text(

            "❌ بازی لغو شد.\n\n"

            f"💰 مبلغ "
            f"{game['bet']:,} DOGS "
            "به موجودی سازنده برگشت."
        )

        save_data()

        return

    # =====================================================
    # JOIN GAME
    # =====================================================

    if action == "game_join":

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی قبلاً شروع شده است.",
                show_alert=True
            )

            return

        # سازنده نمی‌تواند خودش وارد شود
        if uid == game["creator"]:

            await q.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )

            return

        create_user(
            q.from_user
        )

        # بررسی موجودی
        if get_balance(uid) < game["bet"]:

            await q.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return

        # رزرو مبلغ نفر دوم
        if not remove_balance(
            uid,
            game["bet"]
        ):

            await q.answer(
                "❌ برداشت مبلغ بازی انجام نشد.",
                show_alert=True
            )

            return

        # -------------------------------------------------
        # ثبت بازیکن دوم
        # -------------------------------------------------

        game["joiner"] = uid

        game["joiner_name"] = (
            q.from_user.first_name
            or "کاربر"
        )

        game["status"] = "playing"

        await q.message.edit_text(

            "🎮 بازی شروع شد!\n\n"

            f"👤 بازیکن ۱: "
            f"{game['creator_name']}\n"

            f"👤 بازیکن ۲: "
            f"{game['joiner_name']}\n\n"

            f"💰 شرط هر نفر: "
            f"{game['bet']:,} DOGS\n\n"

            "🎲 در حال تعیین برنده..."
        )

        # =================================================
        # تعیین برنده
        # =================================================

        players = [
            game["creator"],
            game["joiner"]
        ]

        winner = random.choice(
            players
        )

        loser = (
            game["joiner"]
            if winner == game["creator"]
            else game["creator"]
        )

        # =================================================
        # محاسبه جایزه
        # =================================================

        total_pot = (
            game["bet"] * 2
        )

        # 10 درصد سهم مالک
        owner_fee = (
            total_pot * 10 // 100
        )

        winner_reward = (
            total_pot - owner_fee
        )

        # =================================================
        # پرداخت
        # =================================================

        add_balance(
            winner,
            winner_reward
        )

        add_balance(
            data.get(
                "owner",
                OWNER_ID
            ),
            owner_fee
        )

        game["winner"] = winner

        game["loser"] = loser

        game["owner_fee"] = owner_fee

        game["winner_reward"] = winner_reward

        game["status"] = "finished"

        save_data()

        # =================================================
        # نام بازیکنان
        # =================================================

        if winner == game["creator"]:

            winner_name = (
                game["creator_name"]
            )

            loser_name = (
                game["joiner_name"]
            )

        else:

            winner_name = (
                game["joiner_name"]
            )

            loser_name = (
                game["creator_name"]
            )

        # =================================================
        # نتیجه
        # =================================================

        result = (

            "🏆 نتیجه بازی\n\n"

            f"🥇 برنده: "
            f"{winner_name}\n"

            f"💔 بازنده: "
            f"{loser_name}\n\n"

            f"💰 مبلغ هر نفر: "
            f"{game['bet']:,} DOGS\n"

            f"🏆 جایزه برنده: "
            f"{winner_reward:,} DOGS\n"

            f"👑 سهم مالک: "
            f"{owner_fee:,} DOGS"
        )

        await q.message.edit_text(
            result
        )

        # =================================================
        # پیام به برنده
        # =================================================

        try:

            await context.bot.send_message(

                winner,

                "🎉 تبریک!\n\n"

                "🏆 شما برنده بازی شدید.\n\n"

                f"💰 جایزه: "
                f"{winner_reward:,} DOGS\n"

                f"💳 موجودی جدید: "
                f"{get_balance(winner):,} DOGS"
            )

        except Exception:

            pass

        # =================================================
        # پیام به بازنده
        # =================================================

        try:

            await context.bot.send_message(

                loser,

                "❌ بازی را باختید.\n\n"

                f"💰 مبلغ بازی: "
                f"{game['bet']:,} DOGS"
            )

        except Exception:

            pass

        return

# =========================================================
# REFERRAL MENU
# =========================================================

async def referral_menu(update, context):

    user = update.effective_user

    create_user(user)

    try:
        bot = await context.bot.get_me()
        username = bot.username
    except Exception:
        username = None

    if username:
        link = f"https://t.me/{username}?start={user.id}"
    else:
        link = "لینک دعوت در دسترس نیست."

    refs = int(
        data["users"][str(user.id)].get(
            "refs",
            0
        )
    )

    reward = int(
        data.get(
            "ref_reward",
            50
        )
    )

    await update.message.reply_text(

        "👥 زیرمجموعه\n\n"

        f"🔗 لینک دعوت شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه: "
        f"{refs}\n\n"

        f"💰 پاداش هر زیرمجموعه: "
        f"{reward:,} DOGS",

        reply_markup=
        main_keyboard(user.id)
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(update, context):

    user = update.effective_user

    create_user(user)

    uid = user.id

    u = data["users"][
        str(uid)
    ]

    phone = u.get(
        "phone",
        ""
    )

    if not phone:
        phone = "ثبت نشده"

    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {uid}\n"

        f"👤 نام: "
        f"{u.get('name', '')}\n"

        f"📱 شماره: "
        f"{phone}\n"

        f"👥 زیرمجموعه: "
        f"{int(u.get('refs', 0))}\n"

        f"💰 موجودی: "
        f"{get_balance(uid):,} DOGS",

        reply_markup=
        main_keyboard(uid)
    )


# =========================================================
# SUPPORT
# =========================================================

async def support(update, context):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "📩 پیام خود را همینجا ارسال کنید.\n"
        "پشتیبانی در سریع‌ترین زمان ممکن "
        "بررسی می‌کند.",

        reply_markup=
        back_keyboard()
    )


# =========================================================
# MAIN MENU TEXT
# =========================================================

async def text_menu_router(
    update,
    context
):

    if not update.message:
        return

    if not update.message.text:
        return

    text = (
        update.message.text
        .strip()
    )

    uid = update.effective_user.id

    # -----------------------------------------------------
    # Owner state
    # -----------------------------------------------------

    if uid in OWNER_STATE:

        await owner_state_receive(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # Transfer state
    # -----------------------------------------------------

    if uid in TRANSFER_DATA:

        return

    # -----------------------------------------------------
    # Deposit state
    # -----------------------------------------------------

    if uid in DEPOSIT_DATA:

        step = (
            DEPOSIT_DATA[uid]
            .get("step")
        )

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

    # -----------------------------------------------------
    # Withdraw state
    # -----------------------------------------------------

    if uid in WITHDRAW_DATA:

        step = (
            WITHDRAW_DATA[uid]
            .get("step")
        )

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
    # MENU
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

        await update.message.reply_text(

            "👥 انتقال DOGS\n\n"

            "برای انتقال، روی پیام کاربر "
            "ریپلای کنید و بنویسید:\n\n"

            "انتقال 500\n\n"

            "مثلاً برای انتقال ۵۰۰ DOGS."
        )

        return

    if text == "⚙️ پنل مدیریت":

        if is_owner(uid):

            await owner_panel(
                update,
                context
            )

        else:

            await update.message.reply_text(
                "❌ دسترسی ندارید."
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
                "👑 انتقال مالکیت",
                callback_data="adm_owner"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 واریزی‌های معلق",
                callback_data="adm_deposits"
            ),
            InlineKeyboardButton(
                "💸 برداشت‌های معلق",
                callback_data="adm_withdraws"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار ربات",
                callback_data="adm_stats"
            )
        ]

    ])


# =========================================================
# OWNER PANEL
# =========================================================

async def owner_panel(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ دسترسی ندارید."
        )

        return

    await update.message.reply_text(

        "⚙️ پنل مدیریت\n\n"
        "گزینه مورد نظر را انتخاب کنید:",

        reply_markup=owner_panel_keyboard()
    )


# =========================================================
# OWNER PANEL CALLBACK
# =========================================================

async def owner_panel_callback(update, context):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if not is_owner(uid):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    action = q.data

    # -----------------------------------------------------
    # ADD BALANCE
    # -----------------------------------------------------

    if action == "adm_add":

        OWNER_STATE[uid] = {
            "action": "add",
            "step": "user"
        }

        await q.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "🆔 آیدی کاربر را ارسال کنید."
        )

        return

    # -----------------------------------------------------
    # REMOVE BALANCE
    # -----------------------------------------------------

    if action == "adm_remove":

        OWNER_STATE[uid] = {
            "action": "remove",
            "step": "user"
        }

        await q.message.reply_text(
            "➖ کسر موجودی\n\n"
            "🆔 آیدی کاربر را ارسال کنید."
        )

        return

    # -----------------------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------------------

    if action == "adm_reward":

        OWNER_STATE[uid] = {
            "action": "reward",
            "step": "amount"
        }

        await q.message.reply_text(

            "👥 جایزه زیرمجموعه\n\n"

            f"💰 مقدار فعلی: "
            f"{int(data.get('ref_reward', 50)):,} DOGS\n\n"

            "مقدار جدید را ارسال کنید."
        )

        return

    # -----------------------------------------------------
    # TRANSFER OWNER
    # -----------------------------------------------------

    if action == "adm_owner":

        OWNER_STATE[uid] = {
            "action": "owner",
            "step": "user"
        }

        await q.message.reply_text(

            "👑 انتقال مالکیت\n\n"

            "🆔 آیدی مالک جدید را ارسال کنید.\n\n"

            "⚠️ کاربر باید قبلاً داخل ربات ثبت شده باشد."
        )

        return

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    if action == "adm_stats":

        users_count = len(
            data.get("users", {})
        )

        total_balance = 0

        for user_id in data.get(
            "users",
            {}
        ):

            total_balance += get_balance(
                user_id
            )

        pending_deposits = sum(
            1
            for x in data.get(
                "deposits",
                {}
            ).values()
            if x.get("status") == "pending"
        )

        pending_withdraws = sum(
            1
            for x in data.get(
                "withdraws",
                {}
            ).values()
            if x.get("status") == "pending"
        )

        await q.message.reply_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: "
            f"{users_count:,}\n"

            f"💰 مجموع موجودی: "
            f"{total_balance:,} DOGS\n"

            f"💳 واریزی معلق: "
            f"{pending_deposits:,}\n"

            f"💸 برداشت معلق: "
            f"{pending_withdraws:,}"
        )

        return

    # -----------------------------------------------------
    # DEPOSITS
    # -----------------------------------------------------

    if action == "adm_deposits":

        pending = [
            x
            for x in data.get(
                "deposits",
                {}
            ).values()
            if x.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "📋 واریزی معلقی وجود ندارد."
            )

            return

        text = "📋 واریزی‌های معلق\n\n"

        for req in pending[-20:]:

            text += (

                f"🆔 {req.get('request_id')}\n"
                f"👤 کاربر: {req.get('user_id')}\n"
                f"💰 مبلغ: "
                f"{int(req.get('amount', 0)):,} DOGS\n"
                f"🐶 نوع: {req.get('type', 'ULTRA')}\n\n"
            )

        await q.message.reply_text(text)

        return

    # -----------------------------------------------------
    # WITHDRAWS
    # -----------------------------------------------------

    if action == "adm_withdraws":

        pending = [
            x
            for x in data.get(
                "withdraws",
                {}
            ).values()
            if x.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "💸 برداشت معلقی وجود ندارد."
            )

            return

        text = "💸 برداشت‌های معلق\n\n"

        for req in pending[-20:]:

            text += (

                f"🆔 {req.get('request_id')}\n"
                f"👤 کاربر: {req.get('user_id')}\n"
                f"💰 مبلغ: "
                f"{int(req.get('amount', 0)):,} DOGS\n"
                f"📥 ولت:\n"
                f"{req.get('wallet', '')}\n\n"
            )

        await q.message.reply_text(text)

        return

# =========================================================
# OWNER STATE RECEIVE - PART 9
# =========================================================

async def owner_state_receive(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):
        OWNER_STATE.pop(uid, None)
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
                target = int(text)
            except ValueError:
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
                    text.replace(",", "")
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ مقدار باید عدد باشد."
                )
                return

            if amount <= 0:
                await update.message.reply_text(
                    "❌ مقدار باید بیشتر از صفر باشد."
                )
                return

            target = state["target"]

            # شارژ
            if state["action"] == "add":

                add_balance(
                    target,
                    amount
                )

                await update.message.reply_text(

                    "✅ موجودی شارژ شد.\n\n"

                    f"👤 کاربر: {target}\n"
                    f"➕ مبلغ: {amount:,} DOGS\n"
                    f"💰 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

            # کسر
            else:

                if get_balance(target) < amount:

                    await update.message.reply_text(

                        "❌ موجودی کاربر کافی نیست.\n\n"

                        f"💰 موجودی فعلی: "
                        f"{get_balance(target):,} DOGS"
                    )

                    return

                remove_balance(
                    target,
                    amount
                )

                await update.message.reply_text(

                    "✅ موجودی کسر شد.\n\n"

                    f"👤 کاربر: {target}\n"
                    f"➖ مبلغ: {amount:,} DOGS\n"
                    f"💰 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

            OWNER_STATE.pop(
                uid,
                None
            )

            return

    # =====================================================
    # REFERRAL REWARD
    # =====================================================

    if state["action"] == "reward":

        try:
            amount = int(
                text.replace(",", "")
            )
        except ValueError:

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
            f"{amount:,} DOGS"
        )

        return

    # =====================================================
    # OWNER TRANSFER
    # =====================================================

    if state["action"] == "owner":

        if state["step"] != "user":
            return

        try:
            new_owner = int(text)
        except ValueError:

            await update.message.reply_text(
                "❌ آیدی مالک جدید باید عدد باشد."
            )

            return

        # کاربر باید ثبت شده باشد
        if str(new_owner) not in data["users"]:

            await update.message.reply_text(

                "❌ این کاربر داخل ربات ثبت نشده است.\n\n"
                "ابتدا کاربر باید ربات را /start کند."
            )

            return

        if new_owner == uid:

            await update.message.reply_text(
                "❌ شما همین الان مالک هستید."
            )

            OWNER_STATE.pop(
                uid,
                None
            )

            return

        OWNER_STATE[uid] = {
            "action": "owner_confirm",
            "target": new_owner
        }

        await update.message.reply_text(

            "⚠️ انتقال مالکیت\n\n"

            f"👑 مالک فعلی: {uid}\n"
            f"👤 مالک جدید: {new_owner}\n\n"

            "آیا مطمئن هستید؟",

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "✅ تایید انتقال",
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
# OWNER TRANSFER CONFIRMATION - PART 10
# =========================================================

async def owner_transfer_decision(update, context):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    # فقط مالک فعلی اجازه دارد
    if not is_owner(uid):

        await q.answer(
            "❌ فقط مالک فعلی اجازه دارد.",
            show_alert=True
        )

        return

    action = q.data

    # =====================================================
    # CANCEL
    # =====================================================

    if action == "owner_no":

        OWNER_STATE.pop(
            uid,
            None
        )

        await q.message.edit_text(
            "❌ انتقال مالکیت لغو شد."
        )

        return

    # =====================================================
    # CONFIRM
    # =====================================================

    if action.startswith("owner_yes:"):

        try:

            new_owner = int(
                action.split(
                    ":",
                    1
                )[1]
            )

        except (ValueError, IndexError):

            await q.message.reply_text(
                "❌ آیدی مالک جدید نامعتبر است."
            )

            return

        # بررسی ثبت بودن کاربر
        if str(new_owner) not in data["users"]:

            await q.message.reply_text(

                "❌ این کاربر داخل ربات ثبت نشده است."
            )

            return

        # جلوگیری از انتقال به خود
        if new_owner == uid:

            await q.message.reply_text(
                "❌ شما همین الان مالک هستید."
            )

            return

        old_owner = data.get(
            "owner",
            OWNER_ID
        )

        # انتقال مالکیت
        data["owner"] = new_owner

        save_data()

        OWNER_STATE.pop(
            uid,
            None
        )

        # پیام برای مالک قبلی
        try:

            await context.bot.send_message(

                old_owner,

                "⚠️ مالکیت ربات منتقل شد.\n\n"
                f"👑 مالک جدید:\n"
                f"{new_owner}"
            )

        except Exception:
            pass

        # پیام برای مالک جدید
        try:

            await context.bot.send_message(

                new_owner,

                "👑 تبریک!\n\n"
                "شما مالک جدید ربات شدید."
            )

        except Exception:
            pass

        await q.message.edit_text(

            "✅ انتقال مالکیت با موفقیت انجام شد.\n\n"

            f"👑 مالک جدید:\n"
            f"{new_owner}"
        )

        return

# =========================================================
# ساخت بازی با دستور فارسی
# مثال: بازی ۵۰۰
# حداقل: ۵۰۰
# حداکثر: ۲۰۰۰۰
# =========================================================

async def game_create(update, context):

    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            "❌ بازی فقط داخل گپ قابل اجراست."
        )
        return

    user = update.effective_user
    create_user(user)

    # بررسی عضویت
    if not await check_join(user.id, context):
        await update.message.reply_text(
            "❌ ابتدا عضو کانال و گپ شوید."
        )
        return

    text = update.message.text.strip()

    # حذف کلمه «بازی»
    amount_text = text.replace("بازی", "", 1).strip()

    if not amount_text:
        await update.message.reply_text(
            "🎮 ساخت بازی\n\n"
            "مثال:\n"
            "بازی ۵۰۰\n\n"
            f"حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"حداکثر بازی: {MAX_GAME:,} DOGS"
        )
        return

    # تبدیل اعداد فارسی و عربی به انگلیسی
    translate_digits = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )

    amount_text = amount_text.translate(
        translate_digits
    )

    amount_text = amount_text.replace(",", "")
    amount_text = amount_text.replace("٬", "")
    amount_text = amount_text.strip()

    try:
        bet = int(amount_text)
    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ بازی باید عدد باشد.\n\n"
            "مثال:\n"
            "بازی ۵۰۰"
        )
        return

    # حداقل
    if bet < MIN_GAME:
        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی "
            f"{MIN_GAME:,} DOGS است."
        )
        return

    # حداکثر
    if bet > MAX_GAME:
        await update.message.reply_text(
            f"❌ حداکثر مبلغ بازی "
            f"{MAX_GAME:,} DOGS است."
        )
        return

    # بررسی موجودی
    if get_balance(user.id) < bet:
        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(user.id):,} DOGS\n"
            f"🎮 مبلغ بازی: "
            f"{bet:,} DOGS"
        )
        return

    # رزرو مبلغ سازنده
    if not remove_balance(user.id, bet):
        await update.message.reply_text(
            "❌ خطا در رزرو مبلغ بازی."
        )
        return

    game_id = (
        f"{update.effective_chat.id}_"
        f"{int(time.time() * 1000)}"
    )

    GAMES[game_id] = {
        "game_id": game_id,
        "chat_id": update.effective_chat.id,
        "message_id": None,
        "creator": user.id,
        "creator_name": user.first_name or "کاربر",
        "bet": bet,
        "joiner": None,
        "joiner_name": "",
        "status": "waiting",
        "created": datetime.now().isoformat()
    }

    msg = await update.message.reply_text(
        "🎮 فرصت بازی ایجاد شد!\n\n"
        f"💰 مبلغ بازی: {bet:,} DOGS\n\n"
        f"👤 سازنده: {user.first_name or 'کاربر'}\n\n"
        "👥 یک نفر دیگر می‌تواند وارد بازی شود.\n\n"
        "👇 برای ورود روی دکمه زیر بزنید.",
        reply_markup=game_keyboard(game_id)
    )

    GAMES[game_id]["message_id"] = msg.message_id

# =========================================================
# PART 12 - دکمه های بازی
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=f"game_join:{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو بازی",
                callback_data=f"game_cancel:{game_id}"
            )
        ]
    ])


async def game_callback(update, context):

    q = update.callback_query
    await q.answer()

    try:
        action, game_id = q.data.split(":", 1)
    except Exception:
        return

    game = GAMES.get(game_id)

    if not game:
        await q.answer(
            "❌ این بازی دیگر وجود ندارد.",
            show_alert=True
        )
        return

    uid = q.from_user.id

    # =====================================================
    # لغو بازی
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:
            await q.answer(
                "❌ فقط سازنده بازی می‌تواند لغو کند.",
                show_alert=True
            )
            return

        if game["status"] != "waiting":
            await q.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True
            )
            return

        add_balance(
            game["creator"],
            game["bet"]
        )

        game["status"] = "cancelled"

        save_data()

        await q.message.edit_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {game['bet']:,} DOGS "
            "به سازنده برگشت داده شد."
        )

        return

    # =====================================================
    # ورود بازیکن دوم
    # =====================================================

    if action == "game_join":

        if game["status"] != "waiting":
            await q.answer(
                "❌ این بازی قبلاً شروع شده.",
                show_alert=True
            )
            return

        if uid == game["creator"]:
            await q.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )
            return

        create_user(q.from_user)

        if get_balance(uid) < game["bet"]:
            await q.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )
            return

        if not remove_balance(
            uid,
            game["bet"]
        ):
            await q.answer(
                "❌ خطا در برداشت مبلغ بازی.",
                show_alert=True
            )
            return

        game["joiner"] = uid
        game["joiner_name"] = (
            q.from_user.first_name or "کاربر"
        )
        game["status"] = "playing"

        save_data()

        await q.message.edit_text(
            "🎮 بازی شروع شد!\n\n"
            f"👤 بازیکن اول: "
            f"{game['creator_name']}\n"
            f"👤 بازیکن دوم: "
            f"{game['joiner_name']}\n\n"
            f"💰 مبلغ بازی هر نفر: "
            f"{game['bet']:,} DOGS\n\n"
            "🎲 در حال مشخص کردن برنده..."
        )

        # =================================================
        # تعیین برنده
        # =================================================

        winner = random.choice([
            game["creator"],
            game["joiner"]
        ])

        if winner == game["creator"]:
            loser = game["joiner"]
            winner_name = game["creator_name"]
            loser_name = game["joiner_name"]
        else:
            loser = game["creator"]
            winner_name = game["joiner_name"]
            loser_name = game["creator_name"]

        # =================================================
        # محاسبه جایزه
        # =================================================

        total = game["bet"] * 2

        # 90 درصد برای برنده
        winner_reward = total * 90 // 100

        # 10 درصد برای مالک
        owner_reward = total - winner_reward

        owner_id = data.get(
            "owner",
            OWNER_ID
        )

        add_balance(
            winner,
            winner_reward
        )

        add_balance(
            owner_id,
            owner_reward
        )

        game["winner"] = winner
        game["loser"] = loser
        game["winner_reward"] = winner_reward
        game["owner_reward"] = owner_reward
        game["status"] = "finished"

        save_data()

        # =================================================
        # اعلام نتیجه در گپ
        # =================================================

        result_text = (

            "🏆 نتیجه بازی\n\n"

            f"🥇 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"

            f"🎮 مبلغ بازی: "
            f"{game['bet']:,} DOGS\n\n"

            f"🏆 جایزه برنده: "
            f"{winner_reward:,} DOGS\n"

            f"👑 سهم مالک: "
            f"{owner_reward:,} DOGS"
        )

        await q.message.edit_text(
            result_text
        )

        # =================================================
        # پیام خصوصی برنده
        # =================================================

        try:

            await context.bot.send_message(
                winner,

                "🎉 تبریک!\n\n"
                "🏆 شما برنده بازی شدید.\n\n"
                f"💰 مبلغ دریافت‌شده: "
                f"{winner_reward:,} DOGS"
            )

        except Exception:
            pass

        # =================================================
        # پیام خصوصی بازنده
        # =================================================

        try:

            await context.bot.send_message(
                loser,

                "❌ متأسفانه بازی را باختید.\n\n"
                f"🎮 مبلغ بازی: "
                f"{game['bet']:,} DOGS"
            )

        except Exception:
            pass

# =========================================================
# PART 13 - دستورات اصلی
# =========================================================

async def transfer_command(update, context):
    await transfer_start(update, context)


async def admin_command(update, context):
    await owner_panel(update, context)


async def transfer_owner_command(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ فقط مالک اجازه استفاده از این دستور را دارد."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ آیدی مالک جدید را وارد کنید.\n\n"
            "مثال:\n"
            "/transferowner 123456789"
        )
        return

    try:
        new_owner = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ آیدی باید عدد باشد."
        )
        return

    if str(new_owner) not in data["users"]:
        await update.message.reply_text(
            "❌ این کاربر هنوز در ربات ثبت نشده است."
        )
        return

    data["owner"] = new_owner
    save_data()

    await update.message.reply_text(
        "✅ انتقال مالکیت انجام شد.\n\n"
        f"👑 مالک جدید:\n{new_owner}"
    )


# =========================================================
# دستور بازی فارسی
# =========================================================

async def game_command(update, context):

    await update.message.reply_text(
        "🎮 برای ساخت بازی از دستور فارسی استفاده کنید.\n\n"
        "مثال:\n"
        "بازی ۵۰۰\n\n"
        f"💰 حداقل: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر: {MAX_GAME:,} DOGS"
    )


# =========================================================
# دستور شروع
# =========================================================

async def start_command(update, context):

    await start(
        update,
        context
    )


# =========================================================
# دستور پنل مدیریت
# =========================================================

async def panel_command(update, context):

    if not is_owner(
        update.effective_user.id
    ):
        await update.message.reply_text(
            "❌ دسترسی ندارید."
        )
        return

    await owner_panel(
        update,
        context
    )

# =========================================================
# PART 14 - MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # COMMANDS
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    app.add_handler(
        CommandHandler(
            "transfer",
            transfer_command
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    app.add_handler(
        CommandHandler(
            "transferowner",
            transfer_owner_command
        )
    )

    # =====================================================
    # CALLBACKS
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deposit_type,
            pattern=r"^dep_(ultra|exchange)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deposit_decision,
            pattern=r"^dep_(ok|no):"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            withdraw_decision,
            pattern=r"^with_(ok|no):"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_transfer_decision,
            pattern=r"^owner_(yes|no)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^game_(join|cancel):"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_panel_callback,
            pattern=r"^adm_"
        )
    )

    # =====================================================
    # CONTACT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_receive
        )
    )

    # =====================================================
    # PHOTO
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )

    # =====================================================
    # TEXT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    # =====================================================
    # ERROR
    # =====================================================

    app.add_error_handler(
        error_handler
    )

    print(
        "================================"
    )

    print(
        "🤖 BOT STARTED"
    )

    print(
        "🎮 بازی فارسی فعال است"
    )

    print(
        "💳 واریز ULTRA فعال است"
    )

    print(
        "👥 انتقال موجودی فعال است"
    )

    print(
        "================================"
    )

    # =====================================================
    # RUN
    # =====================================================

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    main()
