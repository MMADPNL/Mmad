import os
import json
import time
import random
import re
import traceback

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

# گپ اجباری و گپ بازی
FORCE_GROUP = "@TAK_B_ET"
GAME_GROUP = "@TAK_B_ET"

# اگر کانال جدا داری اینجا آیدی کانال واقعی را بگذار
# فعلاً طبق اطلاعاتی که دادی همان آیدی قرار گرفته
FORCE_CHANNEL = "@TAK_B_ET"

ULTRA_ID = "@CyyFr"

EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

GAME_MIN = 500
GAME_MAX = 20000

DATA_FILE = "data.json"


# =========================================================
# DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_status": True,
    "ref_reward": 50,
    "users": {},
    "deposits": {},
    "withdraws": {},
}


def load_data():

    try:

        if os.path.exists(DATA_FILE):

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                result = json.load(f)

                if not isinstance(result, dict):
                    return DEFAULT_DATA.copy()

                result.setdefault(
                    "owner",
                    OWNER_ID
                )

                result.setdefault(
                    "bot_status",
                    True
                )

                result.setdefault(
                    "ref_reward",
                    50
                )

                result.setdefault(
                    "users",
                    {}
                )

                result.setdefault(
                    "deposits",
                    {}
                )

                result.setdefault(
                    "withdraws",
                    {}
                )

                return result

    except Exception as e:

        print(
            "LOAD ERROR:",
            e
        )

    return DEFAULT_DATA.copy()


data = load_data()


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

    except Exception as e:

        print(
            "SAVE ERROR:",
            e
        )


# =========================================================
# ANTI BUG / ANTI SPAM
# =========================================================

CLICK = {}


def anti_spam(
    uid,
    seconds=2
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

            "name": (
                user.first_name
                or ""
            ),

            "username": (
                user.username
                or ""
            ),

            "phone": "",

            "balance": 0,

            "refs": 0,

            "ref_by": None,
        }

        save_data()

    else:

        data["users"][uid]["name"] = (
            user.first_name
            or ""
        )

        data["users"][uid]["username"] = (
            user.username
            or ""
        )


def get_balance(uid):

    try:

        return int(
            data["users"][
                str(uid)
            ]["balance"]
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

    new_balance = (
        get_balance(uid)
        +
        amount
    )

    if new_balance < 0:
        new_balance = 0

    data["users"][uid]["balance"] = (
        new_balance
    )

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

        return int(uid) == int(
            data.get(
                "owner",
                OWNER_ID
            )
        )

    except Exception:

        return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):

    buttons = [

        [
            "💳 واریزی",
            "💰 برداشت",
        ],

        [
            "👥 زیرمجموعه",
            "🎧 پشتیبانی",
        ],

        [
            "👤 پروفایل",
            "👥 انتقال",
        ],

        [
            "🎮 بازی ۵۰۰",
        ],
    ]

    if is_owner(uid):

        buttons.append(
            [
                "⚙️ پنل مدیریت"
            ]
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

    return InlineKeyboardMarkup(
        [

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

        ]
    )


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


# =========================================================
# FORCE JOIN
# =========================================================

async def check_join(
    user_id,
    context
):

    try:

        chats = []

        if FORCE_CHANNEL:
            chats.append(
                FORCE_CHANNEL
            )

        if FORCE_GROUP:
            chats.append(
                FORCE_GROUP
            )

        # جلوگیری از بررسی دوباره یک چت
        chats = list(
            dict.fromkeys(chats)
        )

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

        print(
            "JOIN ERROR:",
            e
        )

        return False


# =========================================================
# START
# =========================================================

async def start(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    # ---------------------------------
    # REFERRAL
    # ---------------------------------

    if context.args:

        try:

            ref_id = int(
                context.args[0]
            )

            uid = str(
                user.id
            )

            if (
                ref_id != user.id
                and
                not data["users"][uid].get(
                    "ref_by"
                )
                and
                str(ref_id) in data["users"]
            ):

                data["users"][uid][
                    "ref_by"
                ] = ref_id

                data["users"][
                    str(ref_id)
                ]["refs"] = int(
                    data["users"][
                        str(ref_id)
                    ].get(
                        "refs",
                        0
                    )
                ) + 1

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

        except Exception:

            pass

    # ---------------------------------
    # BOT STATUS
    # ---------------------------------

    if (
        not data.get(
            "bot_status",
            True
        )
        and
        not is_owner(user.id)
    ):

        await update.message.reply_text(
            "⛔ ربات موقتاً خاموش است."
        )

        return

    # ---------------------------------
    # FORCE JOIN
    # ---------------------------------

    if not await check_join(
        user.id,
        context
    ):

        await update.message.reply_text(
            "❌ ابتدا عضو کانال و گپ شوید.",
            reply_markup=join_keyboard()
        )

        return

    # ---------------------------------
    # PHONE
    # ---------------------------------

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\n"
            "فقط شماره ایران +98 قبول است.",
            reply_markup=phone_keyboard()
        )

        return

    # ---------------------------------
    # MAIN
    # ---------------------------------

    await update.message.reply_text(

        "✅ ورود موفق شد.\n\n"

        f"💰 موجودی شما: "
        f"{get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# PHONE
# =========================================================

def clean_phone(phone):

    if not phone:
        return None

    phone = (
        str(phone)
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

        # فقط فرمت +98
        digits = phone[1:]

        if not digits.isdigit():
            return None

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
            "❌ فقط شماره ایران +98 قبول است."
        )

        return

    create_user(user)

    data["users"][
        str(user.id)
    ]["phone"] = phone

    save_data()

    await update.message.reply_text(
        "✅ شماره تایید شد.",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# REFERRAL
# =========================================================

async def referral(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/"
        f"{bot.username}"
        f"?start={user.id}"
    )

    refs = data["users"][
        str(user.id)
    ].get(
        "refs",
        0
    )

    reward = data.get(
        "ref_reward",
        50
    )

    await update.message.reply_text(

        "👥 سیستم زیرمجموعه\n\n"

        f"🔗 لینک دعوت شما:\n"
        f"{link}\n\n"

        f"👥 تعداد زیرمجموعه: "
        f"{refs}\n\n"

        f"💰 جایزه هر نفر: "
        f"{reward:,} DOGS"
    )


# =========================================================
# DEPOSIT
# =========================================================

DEPOSIT_SESSIONS = {}


def deposit_method_keyboard():

    return InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "⚡ اولترا",
                    callback_data="dep_method_ultra"
                )

            ],

            [

                InlineKeyboardButton(
                    "🏦 صرافی",
                    callback_data="dep_method_exchange"
                )

            ],

            [

                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="dep_back"
                )

            ],

        ]
    )


async def deposit_menu(
    update,
    context
):

    uid = update.effective_user.id

    if not anti_spam(uid):
        return

    await update.message.reply_text(
        "💳 روش واریزی را انتخاب کنید:",
        reply_markup=deposit_method_keyboard()
    )


async def deposit_method(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if not anti_spam(uid):
        return

    method = q.data.replace(
        "dep_method_",
        ""
    )

    DEPOSIT_SESSIONS[uid] = {
        "method": method,
        "step": "amount",
    }

    await q.message.reply_text(

        "💰 مقدار DOGS مورد نظر "
        "برای واریز را وارد کنید.\n\n"

        f"حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS"
    )


async def deposit_amount(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in DEPOSIT_SESSIONS:
        return

    session = DEPOSIT_SESSIONS[uid]

    if session.get("step") != "amount":
        return

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ مقدار باید فقط عدد باشد."
        )

        return

    amount = int(text)

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."
        )

        return

    session["amount"] = amount

    session["step"] = "receipt"

    # ---------------------------------
    # ULTRA
    # ---------------------------------

    if session["method"] == "ultra":

        await update.message.reply_text(

            f"⚡ فرصت واریز\n\n"

            f"ULTRA {amount} DOGS {ULTRA_ID}\n\n"

            f"حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS\n\n"

            "📸 شات خود یا پیام رسید "
            "ارسال کنید."
        )

    # ---------------------------------
    # EXCHANGE
    # ---------------------------------

    else:

        await update.message.reply_text(

            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ وارد شده: "
            f"{amount:,} DOGS\n\n"

            "💳 ولت:\n"

            f"{EXCHANGE_WALLET}\n\n"

            "📤 به این ولت بزنید.\n\n"

            "📸 شات خود یا\n"
            "🔗 لینک هش تراکنش "
            "ارسال کنید."
        )


async def deposit_receipt(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in DEPOSIT_SESSIONS:
        return

    session = DEPOSIT_SESSIONS[uid]

    if session.get("step") != "receipt":
        return

    amount = int(
        session["amount"]
    )

    method = session["method"]

    method_name = (
        "ULTRA"
        if method == "ultra"
        else "صرافی"
    )

    deposit_id = (
        f"{uid}_"
        f"{int(time.time() * 1000)}"
    )

    # ---------------------------------
    # PHOTO
    # ---------------------------------

    if update.message.photo:

        file_id = (
            update.message
            .photo[-1]
            .file_id
        )

        data["deposits"][
            deposit_id
        ] = {

            "user_id": uid,

            "amount": amount,

            "method": method,

            "type": "photo",

            "file_id": file_id,

            "status": "pending",

            "created": int(time.time()),
        }

        keyboard = InlineKeyboardMarkup(
            [

                [

                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=(
                            f"dep_ok_{deposit_id}"
                        )
                    ),

                    InlineKeyboardButton(
                        "❌ رد",
                        callback_data=(
                            f"dep_no_{deposit_id}"
                        )
                    ),

                ],

            ]
        )

        await context.bot.send_photo(

            chat_id=OWNER_ID,

            photo=file_id,

            caption=(

                "💳 رسید پیام\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n"

                f"⚡ روش: {method_name}"
            ),

            reply_markup=keyboard
        )

    # ---------------------------------
    # TEXT / HASH
    # ---------------------------------

    elif update.message.text:

        receipt_text = (
            update.message.text.strip()
        )

        if not receipt_text:

            await update.message.reply_text(
                "❌ لینک هش تراکنش را ارسال کنید."
            )

            return

        data["deposits"][
            deposit_id
        ] = {

            "user_id": uid,

            "amount": amount,

            "method": method,

            "type": "text",

            "text": receipt_text,

            "status": "pending",

            "created": int(time.time()),
        }

        keyboard = InlineKeyboardMarkup(
            [

                [

                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=(
                            f"dep_ok_{deposit_id}"
                        )
                    ),

                    InlineKeyboardButton(
                        "❌ رد",
                        callback_data=(
                            f"dep_no_{deposit_id}"
                        )
                    ),

                ],

            ]
        )

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(

                "💳 رسید پیام\n\n"

                f"👤 کاربر: {uid}\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n"

                f"⚡ روش: {method_name}\n\n"

                "🔗 لینک هش تراکنش:\n"

                f"{receipt_text}"
            ),

            reply_markup=keyboard
        )

    else:

        await update.message.reply_text(
            "❌ فقط شات یا لینک هش تراکنش ارسال کنید."
        )

        return

    save_data()

    del DEPOSIT_SESSIONS[uid]

    await update.message.reply_text(
        "✅ رسید پیام شما ارسال شد.\n\n"
        "⏳ منتظر تایید مالک باشید."
    )


async def deposit_approve(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    deposit_id = q.data.replace(
        "dep_ok_",
        ""
    )

    item = data["deposits"].get(
        deposit_id
    )

    if not item:

        await q.answer(
            "❌ درخواست پیدا نشد.",
            show_alert=True
        )

        return

    if item.get("status") != "pending":

        await q.answer(
            "⚠️ این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = int(
        item["user_id"]
    )

    amount = int(
        item["amount"]
    )

    item["status"] = "approved"

    item["approved_by"] = (
        q.from_user.id
    )

    item["approved_at"] = int(
        time.time()
    )

    add_balance(
        uid,
        amount
    )

    save_data()

    try:

        await context.bot.send_message(

            chat_id=uid,

            text=(

                "✅ واریزی شما تایید شد.\n\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n\n"

                "💳 مبلغ به موجودی شما اضافه شد."
            )
        )

    except Exception:
        pass

    try:

        if q.message.photo:

            await q.message.edit_caption(

                caption=(

                    "✅ واریزی تایید شد.\n\n"

                    f"💰 مبلغ: "
                    f"{amount:,} DOGS"
                ),

                reply_markup=None
            )

        else:

            await q.message.edit_text(

                (
                    "✅ واریزی تایید شد.\n\n"
                    f"💰 مبلغ: "
                    f"{amount:,} DOGS"
                ),

                reply_markup=None
            )

    except Exception:
        pass


async def deposit_reject(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    deposit_id = q.data.replace(
        "dep_no_",
        ""
    )

    item = data["deposits"].get(
        deposit_id
    )

    if not item:

        await q.answer(
            "❌ درخواست پیدا نشد.",
            show_alert=True
        )

        return

    if item.get("status") != "pending":

        await q.answer(
            "⚠️ این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = int(
        item["user_id"]
    )

    amount = int(
        item["amount"]
    )

    item["status"] = "rejected"

    item["rejected_by"] = (
        q.from_user.id
    )

    item["rejected_at"] = int(
        time.time()
    )

    save_data()

    try:

        await context.bot.send_message(

            chat_id=uid,

            text=(

                "❌ واریزی شما رد شد.\n\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n\n"

                "در صورت مشکل با پشتیبانی تماس بگیرید."
            )
        )

    except Exception:
        pass

    try:

        if q.message.photo:

            await q.message.edit_caption(
                caption="❌ واریزی رد شد.",
                reply_markup=None
            )

        else:

            await q.message.edit_text(
                "❌ واریزی رد شد.",
                reply_markup=None
            )

    except Exception:
        pass


# =========================================================
# WITHDRAW
# =========================================================

WITHDRAW_SESSIONS = {}


async def withdraw_start(
    update,
    context
):

    uid = update.effective_user.id

    if not anti_spam(uid):
        return

    if get_balance(uid) < MIN_WITHDRAW:

        await update.message.reply_text(

            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است.\n\n"

            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS"
        )

        return

    WITHDRAW_SESSIONS[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(

        "💰 مقدار برداشت را وارد کنید.\n\n"

        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS",

        reply_markup=back_keyboard()
    )


async def withdraw_amount(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in WITHDRAW_SESSIONS:
        return

    if WITHDRAW_SESSIONS[uid].get(
        "step"
    ) != "amount":

        return

    text = update.message.text.strip()

    if not text.isdigit():

        await update.message.reply_text(
            "❌ مقدار باید فقط عدد باشد."
        )

        return

    amount = int(text)

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

    WITHDRAW_SESSIONS[uid]["amount"] = (
        amount
    )

    WITHDRAW_SESSIONS[uid]["step"] = (
        "wallet"
    )

    await update.message.reply_text(
        "💳 آدرس کیف پول DOGS خود را ارسال کنید."
    )


async def withdraw_wallet(
    update,
    context
):

    uid = update.effective_user.id

    if uid not in WITHDRAW_SESSIONS:
        return

    if WITHDRAW_SESSIONS[uid].get(
        "step"
    ) != "wallet":

        return

    wallet = update.message.text.strip()

    if len(wallet) < 5:

        await update.message.reply_text(
            "❌ آدرس کیف پول معتبر نیست."
        )

        return

    amount = int(
        WITHDRAW_SESSIONS[uid]["amount"]
    )

    withdraw_id = (
        f"{uid}_"
        f"{int(time.time() * 1000)}"
    )

    data["withdraws"][
        withdraw_id
    ] = {

        "user_id": uid,

        "amount": amount,

        "wallet": wallet,

        "status": "pending",

        "created": int(time.time()),
    }

    save_data()

    keyboard = InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "✅ تایید برداشت",
                    callback_data=(
                        f"wd_ok_{withdraw_id}"
                    )
                ),

                InlineKeyboardButton(
                    "❌ رد برداشت",
                    callback_data=(
                        f"wd_no_{withdraw_id}"
                    )
                ),

            ]

        ]
    )

    await context.bot.send_message(

        chat_id=OWNER_ID,

        text=(

            "📤 درخواست برداشت جدید\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS\n\n"

            f"💳 ولت:\n"
            f"{wallet}"
        ),

        reply_markup=keyboard
    )

    del WITHDRAW_SESSIONS[uid]

    await update.message.reply_text(

        "✅ درخواست برداشت ارسال شد.\n"
        "⏳ منتظر تایید مالک باشید.",

        reply_markup=main_keyboard(uid)
    )


async def withdraw_approve(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):
        return

    withdraw_id = q.data.replace(
        "wd_ok_",
        ""
    )

    item = data["withdraws"].get(
        withdraw_id
    )

    if not item:

        await q.answer(
            "❌ درخواست پیدا نشد.",
            show_alert=True
        )

        return

    if item.get("status") != "pending":

        await q.answer(
            "⚠️ قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = int(
        item["user_id"]
    )

    amount = int(
        item["amount"]
    )

    if get_balance(uid) < amount:

        item["status"] = "rejected"

        item["reason"] = (
            "insufficient_balance"
        )

        save_data()

        await context.bot.send_message(
            chat_id=uid,
            text="❌ برداشت به دلیل کافی نبودن موجودی رد شد."
        )

        return

    remove_balance(
        uid,
        amount
    )

    item["status"] = "approved"

    item["approved_at"] = int(
        time.time()
    )

    save_data()

    await context.bot.send_message(

        chat_id=uid,

        text=(

            "✅ برداشت شما تایید شد.\n\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS\n\n"

            f"💳 ولت:\n"
            f"{item['wallet']}"
        )
    )

    try:

        await q.message.edit_text(

            (
                "✅ برداشت تایید شد.\n\n"
                f"💰 مبلغ: "
                f"{amount:,} DOGS"
            ),

            reply_markup=None
        )

    except Exception:
        pass


async def withdraw_reject(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    if not is_owner(
        q.from_user.id
    ):
        return

    withdraw_id = q.data.replace(
        "wd_no_",
        ""
    )

    item = data["withdraws"].get(
        withdraw_id
    )

    if not item:

        await q.answer(
            "❌ درخواست پیدا نشد.",
            show_alert=True
        )

        return

    if item.get("status") != "pending":

        await q.answer(
            "⚠️ قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = int(
        item["user_id"]
    )

    amount = int(
        item["amount"]
    )

    item["status"] = "rejected"

    item["rejected_at"] = int(
        time.time()
    )

    save_data()

    await context.bot.send_message(

        chat_id=uid,

        text=(

            "❌ برداشت شما رد شد.\n\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS"
        )
    )

    try:

        await q.message.edit_text(
            "❌ برداشت رد شد.",
            reply_markup=None
        )

    except Exception:
        pass


# =========================================================
# TRANSFER
# =========================================================

async def transfer_help(
    update,
    context
):

    await update.message.reply_text(

        "👥 انتقال DOGS\n\n"

        "روی پیام کاربر موردنظر Reply بزنید "
        "و بنویسید:\n\n"

        "انتقال 500\n\n"

        "مثال:\n"
        "انتقال 5000"
    )


async def transfer_handler(
    update,
    context
):

    if not update.message.reply_to_message:
        return

    text = update.message.text.strip()

    match = re.fullmatch(
        r"انتقال\s+([0-9]+)",
        text
    )

    if not match:
        return

    uid = update.effective_user.id

    amount = int(
        match.group(1)
    )

    if amount <= 0:

        await update.message.reply_text(
            "❌ مقدار انتقال صحیح نیست."
        )

        return

    target = (
        update.message
        .reply_to_message
        .from_user
    )

    if target.id == uid:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return

    create_user(target)

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    remove_balance(
        uid,
        amount
    )

    add_balance(
        target.id,
        amount
    )

    await update.message.reply_text(

        "✅ انتقال انجام شد.\n\n"

        f"👤 دریافت‌کننده: "
        f"{target.first_name}\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS"
    )

    try:

        await context.bot.send_message(

            chat_id=target.id,

            text=(

                "💰 یک انتقال دریافت کردید.\n\n"

                f"👤 فرستنده: "
                f"{update.effective_user.first_name}\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS"
            )
        )

    except Exception:
        pass


# =========================================================
# GAME SYSTEM
# =========================================================

GAMES = {}


def game_keyboard(
    game_id
):

    return InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "🎮 بازی با دوستان",
                    callback_data=(
                        f"game_join_{game_id}"
                    )
                )

            ],

            [

                InlineKeyboardButton(
                    "❌ لغو",
                    callback_data=(
                        f"game_cancel_{game_id}"
                    )
                )

            ],

        ]
    )


async def create_game(
    update,
    context
):

    if not update.message:
        return

    chat = update.effective_chat

    # =====================================================
    # بازی فقط در گپ
    # =====================================================

    if chat.type not in [
        "group",
        "supergroup"
    ]:

        await update.message.reply_text(

            "❌ بازی فقط داخل گپ انجام می‌شود.\n\n"

            f"👥 گپ بازی:\n"
            f"{GAME_GROUP}\n\n"

            "داخل گپ بنویسید:\n"
            "بازی 500"
        )

        return

    # =====================================================
    # بررسی گپ اصلی
    # =====================================================

    if chat.username:

        if (
            chat.username.lower()
            !=
            GAME_GROUP.lstrip("@").lower()
        ):

            await update.message.reply_text(
                "❌ بازی فقط داخل گپ اصلی انجام می‌شود."
            )

            return

    else:

        # اگر گپ username نداشت، با get_chat بررسی می‌کنیم
        try:

            game_chat = await context.bot.get_chat(
                GAME_GROUP
            )

            if game_chat.id != chat.id:

                await update.message.reply_text(
                    "❌ بازی فقط داخل گپ اصلی انجام می‌شود."
                )

                return

        except Exception:

            await update.message.reply_text(
                "❌ گپ بازی قابل شناسایی نیست."
            )

            return

    # =====================================================
    # بررسی عضویت
    # =====================================================

    uid = update.effective_user.id

    try:

        member = await context.bot.get_chat_member(
            GAME_GROUP,
            uid
        )

        if member.status in [
            "left",
            "kicked"
        ]:

            await update.message.reply_text(
                "❌ ابتدا باید عضو گپ شوید."
            )

            return

    except Exception as e:

        print(
            "GAME JOIN CHECK ERROR:",
            e
        )

    # =====================================================
    # مقدار بازی
    # =====================================================

    text = update.message.text.strip()

    match = re.fullmatch(
        r"بازی\s+([0-9]+)",
        text
    )

    if not match:
        return

    amount = int(
        match.group(1)
    )

    if amount < GAME_MIN:

        await update.message.reply_text(

            f"❌ حداقل مبلغ بازی "
            f"{GAME_MIN:,} DOGS است."
        )

        return

    if amount > GAME_MAX:

        await update.message.reply_text(

            f"❌ حداکثر مبلغ بازی "
            f"{GAME_MAX:,} DOGS است."
        )

        return

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    # =====================================================
    # جلوگیری از چند بازی همزمان
    # =====================================================

    for game in GAMES.values():

        if (
            game["status"] == "waiting"
            and
            game["creator_id"] == uid
        ):

            await update.message.reply_text(
                "⚠️ شما از قبل یک بازی در انتظار دارید."
            )

            return

    # =====================================================
    # ساخت بازی
    # =====================================================

    game_id = (
        str(int(time.time() * 1000))
        +
        str(random.randint(100, 999))
    )

    GAMES[game_id] = {

        "creator_id": uid,

        "creator_name": (
            update.effective_user.first_name
            or "کاربر"
        ),

        "amount": amount,

        "status": "waiting",

        "chat_id": chat.id,

        "created": int(time.time()),
    }

    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"

        f"👤 سازنده: "
        f"{update.effective_user.first_name}\n\n"

        f"💰 مبلغ بازی: "
        f"{amount:,} DOGS\n\n"

        "👥 فقط یک نفر می‌تواند وارد شود.\n"

        "⚡ بعد از ورود نفر دوم، "
        "بازی خودکار انجام می‌شود.",

        reply_markup=game_keyboard(
            game_id
        )
    )


async def game_join(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    # =====================================================
    # فقط گپ
    # =====================================================

    if q.message.chat.type not in [
        "group",
        "supergroup"
    ]:

        await q.answer(
            "❌ بازی فقط داخل گپ انجام می‌شود.",
            show_alert=True
        )

        return

    # =====================================================
    # فقط همان گپ
    # =====================================================

    game_id = q.data.replace(
        "game_join_",
        ""
    )

    game = GAMES.get(
        game_id
    )

    if not game:

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    if q.message.chat.id != game.get(
        "chat_id"
    ):

        await q.answer(
            "❌ این بازی مربوط به این گپ نیست.",
            show_alert=True
        )

        return

    if game["status"] != "waiting":

        await q.answer(
            "⚠️ این بازی دیگر قابل ورود نیست.",
            show_alert=True
        )

        return

    if game["creator_id"] == uid:

        await q.answer(
            "❌ خودتان نمی‌توانید وارد بازی خودتان شوید.",
            show_alert=True
        )

        return

    # =====================================================
    # بررسی موجودی
    # =====================================================

    amount = int(
        game["amount"]
    )

    creator_id = int(
        game["creator_id"]
    )

    if get_balance(uid) < amount:

        await q.answer(
            "❌ موجودی کافی ندارید.",
            show_alert=True
        )

        return

    if get_balance(creator_id) < amount:

        game["status"] = "cancelled"

        try:

            await q.message.edit_text(
                "❌ بازی به دلیل کافی نبودن موجودی سازنده لغو شد."
            )

        except Exception:
            pass

        return

    # =====================================================
    # برداشت مبلغ از هر دو
    # =====================================================

    if not remove_balance(
        creator_id,
        amount
    ):

        await q.answer(
            "❌ موجودی سازنده کافی نیست.",
            show_alert=True
        )

        return

    if not remove_balance(
        uid,
        amount
    ):

        # برگرداندن پول سازنده
        add_balance(
            creator_id,
            amount
        )

        await q.answer(
            "❌ موجودی شما کافی نیست.",
            show_alert=True
        )

        return

    # =====================================================
    # بازیکن دوم
    # =====================================================

    game["player2_id"] = uid

    game["player2_name"] = (
        q.from_user.first_name
        or "کاربر"
    )

    game["status"] = "playing"

    # =====================================================
    # اعلام شروع
    # =====================================================

    try:

        await q.message.edit_text(

            "🎮 بازی شروع شد!\n\n"

            f"👤 بازیکن اول: "
            f"{game['creator_name']}\n"

            f"👤 بازیکن دوم: "
            f"{game['player2_name']}\n\n"

            f"💰 مبلغ: "
            f"{amount:,} DOGS\n\n"

            "⏳ در حال تعیین نتیجه..."
        )

    except Exception:
        pass

    # کمی مکث برای طبیعی شدن
    await __import__(
        "asyncio"
    ).sleep(1)

    # =====================================================
    # تعیین برنده
    # =====================================================

    winner_id = random.choice(
        [
            creator_id,
            uid
        ]
    )

    loser_id = (
        uid
        if winner_id == creator_id
        else creator_id
    )

    winner_name = (
        game["creator_name"]
        if winner_id == creator_id
        else game["player2_name"]
    )

    loser_name = (
        game["player2_name"]
        if loser_id == uid
        else game["creator_name"]
    )

    prize = amount * 2

    # =====================================================
    # پرداخت جایزه
    # =====================================================

    add_balance(
        winner_id,
        prize
    )

    game["status"] = "finished"

    game["winner_id"] = (
        winner_id
    )

    game["loser_id"] = (
        loser_id
    )

    game["finished"] = int(
        time.time()
    )

    # =====================================================
    # نتیجه
    # =====================================================

    result_text = (

        "🏆 نتیجه بازی\n\n"

        f"🎮 مبلغ بازی: "
        f"{amount:,} DOGS\n\n"

        f"👑 برنده:\n"
        f"{winner_name}\n\n"

        f"❌ بازنده:\n"
        f"{loser_name}\n\n"

        f"💰 جایزه برنده: "
        f"{prize:,} DOGS"
    )

    # =====================================================
    # نتیجه داخل گپ
    # =====================================================

    try:

        await q.message.edit_text(
            result_text,
            reply_markup=None
        )

    except Exception:

        try:

            await q.message.reply_text(
                result_text
            )

        except Exception:
            pass

    # =====================================================
    # نتیجه پیوی هر دو
    # =====================================================

    for player_id in [
        creator_id,
        uid
    ]:

        try:

            personal_text = (
                result_text
                +
                "\n\n"
                f"💰 موجودی فعلی شما: "
                f"{get_balance(player_id):,} DOGS"
            )

            await context.bot.send_message(
                chat_id=player_id,
                text=personal_text
            )

        except Exception as e:

            print(
                "GAME PV ERROR:",
                e
            )

    save_data()


async def game_cancel(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    game_id = q.data.replace(
        "game_cancel_",
        ""
    )

    game = GAMES.get(
        game_id
    )

    if not game:

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    if game["status"] != "waiting":

        await q.answer(
            "⚠️ این بازی دیگر قابل لغو نیست.",
            show_alert=True
        )

        return

    if game["creator_id"] != uid:

        await q.answer(
            "❌ فقط سازنده می‌تواند بازی را لغو کند.",
            show_alert=True
        )

        return

    game["status"] = "cancelled"

    try:

        await q.message.edit_text(
            "❌ بازی توسط سازنده لغو شد.",
            reply_markup=None
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

    create_user(user)

    await update.message.reply_text(

        "👤 پروفایل\n\n"

        f"🆔 ID: {user.id}\n"

        f"👤 نام: "
        f"{user.first_name or '-'}\n"

        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS\n"

        f"👥 زیرمجموعه: "
        f"{data['users'][str(user.id)].get('refs', 0)} نفر"
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

        "پیام خود را ارسال کنید.\n"
        "پشتیبانی آن را بررسی می‌کند."
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        [

            [

                InlineKeyboardButton(
                    "💰 شارژ موجودی",
                    callback_data="admin_charge"
                ),

                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="admin_remove"
                ),

            ],

            [

                InlineKeyboardButton(
                    "🐶 جایزه زیرمجموعه",
                    callback_data="admin_ref_reward"
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
                    "📢 پیام همگانی",
                    callback_data="admin_broadcast"
                )

            ],

        ]
    )


ADMIN_SESSIONS = {}


async def admin_panel(
    update,
    context
):

    uid = update.effective_user.id

    if not is_owner(uid):
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=admin_keyboard()
    )


async def admin_callback(
    update,
    context
):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if not is_owner(uid):

        await q.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    action = q.data.replace(
        "admin_",
        ""
    )

    if action == "charge":

        ADMIN_SESSIONS[uid] = {
            "step": "charge"
        }

        await q.message.reply_text(

            "💰 شارژ موجودی\n\n"

            "فرمت:\n"

            "شارژ ID مبلغ\n\n"

            "مثال:\n"

            "شارژ 123456789 5000"
        )

    elif action == "remove":

        ADMIN_SESSIONS[uid] = {
            "step": "remove"
        }

        await q.message.reply_text(

            "➖ کسر موجودی\n\n"

            "فرمت:\n"

            "کسر ID مبلغ\n\n"

            "مثال:\n"

            "کسر 123456789 5000"
        )

    elif action == "ref_reward":

        ADMIN_SESSIONS[uid] = {
            "step": "ref_reward"
        }

        await q.message.reply_text(

            "🐶 جایزه زیرمجموعه\n\n"

            "مقدار جایزه هر نفر را وارد کنید.\n\n"

            "مثال:\n"
            "100"
        )

    elif action == "stats":

        users = len(
            data["users"]
        )

        pending_dep = sum(
            1
            for x in data["deposits"].values()
            if x.get("status") == "pending"
        )

        pending_wd = sum(
            1
            for x in data["withdraws"].values()
            if x.get("status") == "pending"
        )

        total_balance = sum(
            get_balance(x)
            for x in data["users"].keys()
        )

        await q.message.reply_text(

            "📊 آمار ربات\n\n"

            f"👥 کاربران: {users}\n"

            f"💰 مجموع موجودی‌ها: "
            f"{total_balance:,} DOGS\n"

            f"💳 واریزی در انتظار: "
            f"{pending_dep}\n"

            f"📤 برداشت در انتظار: "
            f"{pending_wd}\n"

            f"🐶 جایزه زیرمجموعه: "
            f"{data.get('ref_reward', 50):,} DOGS"
        )

    elif action == "broadcast":

        ADMIN_SESSIONS[uid] = {
            "step": "broadcast"
        }

        await q.message.reply_text(
            "📢 پیام همگانی را ارسال کنید."
        )


async def admin_text_handler(
    update,
    context
):

    uid = update.effective_user.id

    if not is_owner(uid):
        return

    if uid not in ADMIN_SESSIONS:
        return

    session = ADMIN_SESSIONS[uid]

    text = update.message.text.strip()

    # ---------------------------------
    # REF REWARD
    # ---------------------------------

    if session["step"] == "ref_reward":

        if not text.isdigit():

            await update.message.reply_text(
                "❌ فقط عدد وارد کنید."
            )

            return

        reward = int(text)

        if reward < 0:

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )

            return

        data["ref_reward"] = reward

        save_data()

        del ADMIN_SESSIONS[uid]

        await update.message.reply_text(

            f"✅ جایزه هر زیرمجموعه شد "
            f"{reward:,} DOGS."
        )

        return

    # ---------------------------------
    # CHARGE / REMOVE
    # ---------------------------------

    if session["step"] in [
        "charge",
        "remove"
    ]:

        parts = text.split()

        if len(parts) != 3:

            await update.message.reply_text(

                "❌ فرمت اشتباه است.\n\n"

                "مثال:\n"
                "شارژ 123456789 5000"
            )

            return

        try:

            target_id = int(
                parts[1]
            )

            amount = int(
                parts[2]
            )

        except Exception:

            await update.message.reply_text(
                "❌ ID و مبلغ باید عدد باشند."
            )

            return

        if str(target_id) not in data["users"]:

            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )

            return

        if amount <= 0:

            await update.message.reply_text(
                "❌ مبلغ باید بیشتر از صفر باشد."
            )

            return

        if session["step"] == "charge":

            add_balance(
                target_id,
                amount
            )

            msg = (

                "✅ موجودی شارژ شد.\n\n"

                f"👤 ID: {target_id}\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS"
            )

        else:

            if get_balance(
                target_id
            ) < amount:

                await update.message.reply_text(
                    "❌ موجودی کاربر کافی نیست."
                )

                return

            remove_balance(
                target_id,
                amount
            )

            msg = (

                "✅ موجودی کسر شد.\n\n"

                f"👤 ID: {target_id}\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS"
            )

        del ADMIN_SESSIONS[uid]

        await update.message.reply_text(
            msg
        )

        return

    # ---------------------------------
    # BROADCAST
    # ---------------------------------

    if session["step"] == "broadcast":

        sent = 0
        failed = 0

        for user_id in list(
            data["users"].keys()
        ):

            try:

                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=text
                )

                sent += 1

            except Exception:

                failed += 1

        del ADMIN_SESSIONS[uid]

        await update.message.reply_text(

            "📢 پیام همگانی انجام شد.\n\n"

            f"✅ موفق: {sent}\n"

            f"❌ ناموفق: {failed}"
        )


# =========================================================
# BACK
# =========================================================

async def back_handler(
    update,
    context
):

    uid = update.effective_user.id

    DEPOSIT_SESSIONS.pop(
        uid,
        None
    )

    WITHDRAW_SESSIONS.pop(
        uid,
        None
    )

    ADMIN_SESSIONS.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "🔙 برگشت",

        reply_markup=main_keyboard(
            uid
        )
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context
):

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    uid = update.effective_user.id

    # ---------------------------------
    # ADMIN SESSION
    # ---------------------------------

    if (
        is_owner(uid)
        and
        uid in ADMIN_SESSIONS
    ):

        await admin_text_handler(
            update,
            context
        )

        return

    # ---------------------------------
    # DEPOSIT AMOUNT
    # ---------------------------------

    if uid in DEPOSIT_SESSIONS:

        if (
            DEPOSIT_SESSIONS[uid].get(
                "step"
            )
            ==
            "amount"
        ):

            await deposit_amount(
                update,
                context
            )

            return

    # ---------------------------------
    # WITHDRAW
    # ---------------------------------

    if uid in WITHDRAW_SESSIONS:

        step = WITHDRAW_SESSIONS[
            uid
        ].get(
            "step"
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

    # ---------------------------------
    # TRANSFER
    # ---------------------------------

    if re.fullmatch(
        r"انتقال\s+[0-9]+",
        text.strip()
    ):

        await transfer_handler(
            update,
            context
        )

        return

    # ---------------------------------
    # GAME
    # ---------------------------------

    if re.fullmatch(
        r"بازی\s+[0-9]+",
        text.strip()
    ):

        await create_game(
            update,
            context
        )

        return

    # ---------------------------------
    # MAIN BUTTONS
    # ---------------------------------

    if text == "💳 واریزی":

        await deposit_menu(
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

        await referral(
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

    if text == "👥 انتقال":

        await transfer_help(
            update,
            context
        )

        return

    if text == "🎮 بازی ۵۰۰":

        await update.message.reply_text(

            "🎮 بازی DOGS\n\n"

            "بازی فقط داخل گپ انجام می‌شود.\n\n"

            f"👥 گپ:\n"
            f"{GAME_GROUP}\n\n"

            "مثال:\n"
            "بازی 500\n\n"

            f"حداقل: "
            f"{GAME_MIN:,} DOGS\n"

            f"حداکثر: "
            f"{GAME_MAX:,} DOGS"
        )

        return

    if text == "⚙️ پنل مدیریت":

        if is_owner(uid):

            await admin_panel(
                update,
                context
            )

        return

    if text == "🔙 برگشت":

        await back_handler(
            update,
            context
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

    if uid in DEPOSIT_SESSIONS:

        if (
            DEPOSIT_SESSIONS[uid].get(
                "step"
            )
            ==
            "receipt"
        ):

            await deposit_receipt(
                update,
                context
            )

            return


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(
    update,
    context
):

    q = update.callback_query

    value = q.data

    # ---------------------------------
    # JOIN CHECK
    # ---------------------------------

    if value == "check_join":

        if await check_join(
            q.from_user.id,
            context
        ):

            await q.answer(
                "✅ عضویت تایید شد.",
                show_alert=True
            )

            try:

                await q.message.reply_text(
                    "✅ عضویت تایید شد.\n"
                    "حالا /start را بزنید."
                )

            except Exception:
                pass

        else:

            await q.answer(
                "❌ هنوز عضو نشده‌اید.",
                show_alert=True
            )

        return

    # ---------------------------------
    # DEPOSIT BACK
    # ---------------------------------

    if value == "dep_back":

        await q.answer()

        DEPOSIT_SESSIONS.pop(
            q.from_user.id,
            None
        )

        await q.message.reply_text(

            "🔙 برگشت",

            reply_markup=main_keyboard(
                q.from_user.id
            )
        )

        return

    # ---------------------------------
    # DEPOSIT METHOD
    # ---------------------------------

    if value.startswith(
        "dep_method_"
    ):

        await deposit_method(
            update,
            context
        )

        return

    # ---------------------------------
    # DEPOSIT APPROVE
    # ---------------------------------

    if value.startswith(
        "dep_ok_"
    ):

        await deposit_approve(
            update,
            context
        )

        return

    # ---------------------------------
    # DEPOSIT REJECT
    # ---------------------------------

    if value.startswith(
        "dep_no_"
    ):

        await deposit_reject(
            update,
            context
        )

        return

    # ---------------------------------
    # WITHDRAW APPROVE
    # ---------------------------------

    if value.startswith(
        "wd_ok_"
    ):

        await withdraw_approve(
            update,
            context
        )

        return

    # ---------------------------------
    # WITHDRAW REJECT
    # ---------------------------------

    if value.startswith(
        "wd_no_"
    ):

        await withdraw_reject(
            update,
            context
        )

        return

    # ---------------------------------
    # GAME JOIN
    # ---------------------------------

    if value.startswith(
        "game_join_"
    ):

        await game_join(
            update,
            context
        )

        return

    # ---------------------------------
    # GAME CANCEL
    # ---------------------------------

    if value.startswith(
        "game_cancel_"
    ):

        await game_cancel(
            update,
            context
        )

        return

    # ---------------------------------
    # ADMIN
    # ---------------------------------

    if value.startswith(
        "admin_"
    ):

        await admin_callback(
            update,
            context
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "BOT ERROR:"
    )

    traceback.print_exception(
        type(
            context.error
        ),
        context.error,
        context.error.__traceback__
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        print(
            "ERROR: BOT_TOKEN environment variable "
            "is not set."
        )

        return

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # /ref
    app.add_handler(
        CommandHandler(
            "ref",
            referral
        )
    )

    # contact
    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_receive
        )
    )

    # callbacks
    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # photos
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )

    # text
    app.add_handler(
        MessageHandler(
            filters.TEXT
            &
            ~filters.COMMAND,
            text_router
        )
    )

    # errors
    app.add_error_handler(
        error_handler
    )

    print(
        "BOT STARTED"
    )

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":

    main()
