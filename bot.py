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

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

OWNER_GAME_FEE = 100
GAME_WIN_PRIZE = 900

# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "ref_reward": 50,
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}

# =========================================================
# DATA FUNCTIONS
# =========================================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                result = json.load(f)

            if not isinstance(result, dict):
                return json.loads(json.dumps(DEFAULT_DATA))

            for key, value in DEFAULT_DATA.items():
                if key not in result:
                    result[key] = json.loads(json.dumps(value))

            return result

    except Exception:
        traceback.print_exc()

    return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


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
# STATES
# =========================================================

CLICK_TIMES = {}

DEPOSIT_STATE = {}
WITHDRAW_STATE = {}
TRANSFER_STATE = {}
OWNER_STATE = {}

# =========================================================
# ANTI SPAM
# =========================================================

def anti_spam(user_id, seconds=1.5):

    now = time.time()
    key = str(user_id)

    last = CLICK_TIMES.get(key, 0)

    if now - last < seconds:
        return False

    CLICK_TIMES[key] = now

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
            "created": datetime.now().isoformat(),
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


def get_balance(user_id):

    try:
        return int(
            data["users"][str(user_id)]["balance"]
        )

    except Exception:
        return 0


def set_balance(user_id, amount):

    uid = str(user_id)

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


def add_balance(user_id, amount):

    try:
        amount = int(amount)
    except Exception:
        return False

    return set_balance(
        user_id,
        get_balance(user_id) + amount
    )


def remove_balance(user_id, amount):

    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        return False

    if get_balance(user_id) < amount:
        return False

    return set_balance(
        user_id,
        get_balance(user_id) - amount
    )


def is_owner(user_id):

    try:
        return int(user_id) == int(
            data.get("owner", OWNER_ID)
        )
    except Exception:
        return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id):

    buttons = [
        ["💳 واریزی", "💰 برداشت"],
        ["👥 زیرمجموعه", "👤 پروفایل"],
        ["👥 انتقال", "🎧 پشتیبانی"],
    ]

    if is_owner(user_id):
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
            ]
        ]
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

        print("JOIN ERROR:", e)

        return False


# =========================================================
# PHONE
# =========================================================

def clean_phone(phone):

    if not phone:
        return None

    phone = str(phone)

    phone = phone.replace(
        " ",
        ""
    ).replace(
        "-",
        ""
    ).replace(
        "(",
        ""
    ).replace(
        ")",
        ""
    )

    if phone.startswith("0098"):
        phone = "+" + phone[2:]

    elif phone.startswith("98"):
        phone = "+" + phone

    if phone.startswith("+98"):
        return phone

    return None


async def phone_receive(update, context):

    if not update.message:
        return

    if not update.message.contact:
        return

    user = update.effective_user
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

    data["users"][str(user.id)]["phone"] = phone

    save_data()

    await update.message.reply_text(
        "✅ شماره با موفقیت تایید شد.",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# START
# =========================================================

async def start(update, context):

    user = update.effective_user

    create_user(user)

    if not await check_join(
        user.id,
        context
    ):

        await update.message.reply_text(
            "❌ برای استفاده از ربات ابتدا عضو کانال و گپ شوید.",
            reply_markup=join_keyboard()
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(
            "📱 برای ادامه شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط شماره ایران با +98 قبول است.",
            reply_markup=phone_keyboard()
        )

        return

    await update.message.reply_text(
        "🏠 منوی اصلی\n\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(
            user.id
        )
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

    user = q.from_user

    if not await check_join(
        user.id,
        context
    ):

        await q.answer(
            "❌ هنوز عضو کانال و گپ نشده‌اید.",
            show_alert=True
        )

        return

    create_user(user)

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await context.bot.send_message(
            user.id,
            "📱 شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط شماره ایران با +98 قبول است.",
            reply_markup=phone_keyboard()
        )

    else:

        await q.message.reply_text(
            "✅ عضویت شما تایید شد.",
            reply_markup=main_keyboard(
                user.id
            )
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

    data["users"][uid]["ref_by"] = ref_id

    data["users"][
        str(ref_id)
    ]["refs"] = int(
        data["users"][
            str(ref_id)
        ].get("refs", 0)
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


# =========================================================
# REFERRAL MENU
# =========================================================

async def referral_menu(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    bot = await context.bot.get_me()

    username = bot.username or ""

    link = (
        f"https://t.me/"
        f"{username}"
        f"?start={user.id}"
    )

    refs = data["users"][
        str(user.id)
    ].get(
        "refs",
        0
    )

    reward = int(
        data.get(
            "ref_reward",
            50
        )
    )

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        f"🔗 لینک دعوت:\n{link}\n\n"
        f"👥 تعداد: {refs}\n"
        f"💰 جایزه هر نفر: "
        f"{reward:,} DOGS",
        reply_markup=main_keyboard(
            user.id
        )
            )
    # =========================================================
# DEPOSIT - ULTRA ONLY
# =========================================================

async def deposit_start(update, context):
    user = update.effective_user
    create_user(user)

    if not anti_spam(user.id):
        return

    DEPOSIT_STATE[user.id] = {
        "step": "amount"
    }

    await update.message.reply_text(
        "🐶 واریز ULTRA\n\n"
        "مقدار DOGS را وارد کنید.\n\n"
        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS",
        reply_markup=back_keyboard()
    )


async def deposit_amount(update, context):
    uid = update.effective_user.id

    state = DEPOSIT_STATE.get(uid)

    if not state:
        return

    if state.get("step") != "amount":
        return

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except Exception:
        await update.message.reply_text(
            "❌ مقدار باید عدد باشد."
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."
        )
        return

    state["amount"] = amount
    state["step"] = "receipt"

    await update.message.reply_text(
        "💳 فرصت واریز:\n\n"
        f"ULTRA {amount:,} DOGS {ULTRA_ID}\n\n"
        f"حداقل واریز {MIN_DEPOSIT:,} DOGS\n\n"
        "📸 شات خود یا رسید پیام را ارسال کنید.",
        reply_markup=back_keyboard()
    )


def deposit_buttons(request_id):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تایید",
                    callback_data=f"dep_ok:{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"dep_no:{request_id}"
                )
            ]
        ]
    )


async def deposit_receipt(
    update,
    context
):

    uid = update.effective_user.id

    state = DEPOSIT_STATE.get(uid)

    if not state:
        return

    if state.get("step") != "receipt":
        return

    amount = int(
        state["amount"]
    )

    request_id = (
        f"D"
        f"{int(time.time() * 1000)}"
        f"_{uid}"
    )

    if update.message.photo:

        content_type = "photo"

        content = (
            update.message.photo[-1].file_id
        )

    elif update.message.text:

        content_type = "text"

        content = update.message.text.strip()

        if not content:
            await update.message.reply_text(
                "❌ رسید معتبر ارسال کنید."
            )
            return

    else:

        await update.message.reply_text(
            "❌ لطفاً عکس رسید یا متن/لینک رسید را ارسال کنید."
        )

        return

    request = {
        "request_id": request_id,
        "user_id": uid,
        "amount": amount,
        "type": "ULTRA",
        "kind": content_type,
        "content": content,
        "status": "pending",
        "created": datetime.now().isoformat()
    }

    data["deposits"][
        request_id
    ] = request

    save_data()

    owner_id = data.get(
        "owner",
        OWNER_ID
    )

    caption = (
        "💳 درخواست واریزی جدید\n\n"
        f"🆔 درخواست: {request_id}\n"
        f"👤 کاربر: {uid}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        "🐶 روش: ULTRA\n\n"
        "📋 رسید برای بررسی مالک ارسال شده است."
    )

    try:

        if content_type == "photo":

            await context.bot.send_photo(
                chat_id=owner_id,
                photo=content,
                caption=caption,
                reply_markup=deposit_buttons(
                    request_id
                )
            )

        else:

            await context.bot.send_message(
                chat_id=owner_id,
                text=(
                    caption
                    + "\n\n"
                    "🧾 متن رسید:\n"
                    + content
                ),
                reply_markup=deposit_buttons(
                    request_id
                )
            )

    except Exception:

        traceback.print_exc()

        data["deposits"].pop(
            request_id,
            None
        )

        save_data()

        await update.message.reply_text(
            "❌ ارسال رسید به مالک انجام نشد."
        )

        return

    DEPOSIT_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ رسید شما برای مالک ارسال شد.\n\n"
        "⏳ منتظر تایید مالک باشید.",
        reply_markup=main_keyboard(uid)
    )


async def deposit_decision(
    update,
    context
):

    q = update.callback_query

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await q.answer()

    try:

        action, request_id = (
            q.data.split(":", 1)
        )

    except Exception:

        await q.message.reply_text(
            "❌ درخواست نامعتبر است."
        )

        return

    request = data[
        "deposits"
    ].get(request_id)

    if not request:

        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get(
        "status"
    ) != "pending":

        await q.answer(
            "⚠️ این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = request["user_id"]
    amount = int(
        request["amount"]
    )

    if action == "dep_ok":

        request["status"] = "approved"

        add_balance(
            uid,
            amount
        )

        save_data()

        try:

            await context.bot.send_message(
                uid,
                "✅ واریز شما تایید شد.\n\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"💳 موجودی جدید: "
                f"{get_balance(uid):,} DOGS"
            )

        except Exception:
            pass

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(
            f"✅ واریز کاربر {uid} تایید شد."
        )

    elif action == "dep_no":

        request["status"] = "rejected"

        save_data()

        try:

            await context.bot.send_message(
                uid,
                "❌ درخواست واریز شما رد شد."
            )

        except Exception:
            pass

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(
            f"❌ واریز کاربر {uid} رد شد."
        )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(
    update,
    context
):

    user = update.effective_user
    uid = user.id

    create_user(user)

    balance = get_balance(uid)

    if balance < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n"
            f"موجودی شما: "
            f"{balance:,} DOGS",
            reply_markup=main_keyboard(uid)
        )

        return

    WITHDRAW_STATE[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(
        "💰 مقدار برداشت را ارسال کنید.\n\n"
        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n"
        f"موجودی: "
        f"{balance:,} DOGS",
        reply_markup=back_keyboard()
    )


async def withdraw_amount(
    update,
    context
):

    uid = update.effective_user.id

    state = WITHDRAW_STATE.get(uid)

    if not state:
        return

    if state.get("step") != "amount":
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

    WITHDRAW_STATE[uid] = {
        "step": "wallet",
        "amount": amount
    }

    await update.message.reply_text(
        "📥 آدرس ولت مقصد را ارسال کنید.",
        reply_markup=back_keyboard()
    )


async def withdraw_wallet(
    update,
    context
):

    uid = update.effective_user.id

    state = WITHDRAW_STATE.get(uid)

    if not state:
        return

    if state.get("step") != "wallet":
        return

    wallet = update.message.text.strip()

    if len(wallet) < 5:

        await update.message.reply_text(
            "❌ آدرس ولت نامعتبر است."
        )

        return

    amount = int(
        state["amount"]
    )

    if get_balance(uid) < amount:

        WITHDRAW_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ برداشت انجام نشد."
        )

        return

    request_id = (
        f"W"
        f"{int(time.time() * 1000)}"
        f"_{uid}"
    )

    request = {
        "request_id": request_id,
        "user_id": uid,
        "amount": amount,
        "wallet": wallet,
        "status": "pending",
        "created": datetime.now().isoformat()
    }

    data["withdraws"][
        request_id
    ] = request

    save_data()

    markup = InlineKeyboardMarkup(
        [
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
        ]
    )

    owner_id = data.get(
        "owner",
        OWNER_ID
    )

    try:

        await context.bot.send_message(
            owner_id,
            "💰 درخواست برداشت جدید\n\n"
            f"🆔 درخواست: {request_id}\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مبلغ: {amount:,} DOGS\n\n"
            f"📥 ولت مقصد:\n{wallet}",
            reply_markup=markup
        )

    except Exception:

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
            "❌ ارسال درخواست به مالک انجام نشد و مبلغ برگشت داده شد."
        )

        return

    WITHDRAW_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ درخواست برداشت ارسال شد.\n\n"
        "⏳ مبلغ تا تعیین تکلیف مالک رزرو شده.",
        reply_markup=main_keyboard(uid)
    )


async def withdraw_decision(
    update,
    context
):

    q = update.callback_query

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await q.answer()

    try:

        action, request_id = (
            q.data.split(":", 1)
        )

    except Exception:

        await q.message.reply_text(
            "❌ درخواست نامعتبر است."
        )

        return

    request = data[
        "withdraws"
    ].get(request_id)

    if not request:

        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get(
        "status"
    ) != "pending":

        await q.answer(
            "⚠️ این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = request["user_id"]
    amount = int(
        request["amount"]
    )

    if action == "with_ok":

        request["status"] = "approved"

        text = (
            "✅ برداشت شما تایید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"📥 ولت:\n{request['wallet']}"
        )

        owner_text = (
            f"✅ برداشت {request_id} تایید شد."
        )

    else:

        request["status"] = "rejected"

        add_balance(
            uid,
            amount
        )

        text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ {amount:,} DOGS "
            "به موجودی شما برگشت."
        )

        owner_text = (
            f"❌ برداشت {request_id} رد شد "
            "و مبلغ برگشت داده شد."
        )

    save_data()

    try:

        await context.bot.send_message(
            uid,
            text
        )

    except Exception:
        pass

    await q.message.edit_reply_markup(
        reply_markup=None
    )

    await q.message.reply_text(
        owner_text
)

# =========================================================
# TRANSFER + GAME SYSTEM
# =========================================================

TRANSFER_STATE = {}
GAMES = {}


# =========================================================
# FIND USER
# =========================================================

def find_user_by_username(username):
    username = str(username).replace("@", "").strip().lower()

    for uid, user in data["users"].items():
        saved = str(
            user.get("username", "")
        ).replace("@", "").strip().lower()

        if saved == username:
            return int(uid)

    return None


# =========================================================
# TRANSFER
# =========================================================

async def transfer_start(update, context):
    user = update.effective_user
    uid = user.id

    create_user(user)

    target_id = None
    target_name = ""

    # -----------------------------------------
    # انتقال با ریپلای
    # مثال:
    # روی پیام شخص بزن:
    # انتقال 500
    # -----------------------------------------

    if update.message.reply_to_message:

        target = update.message.reply_to_message.from_user

        if not target:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return

        target_id = target.id
        target_name = target.first_name or "کاربر"

        if target_id == uid:
            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )
            return

        create_user(target)

    # -----------------------------------------
    # انتقال با آیدی یا یوزرنیم
    # -----------------------------------------

    elif context.args:

        raw = context.args[0].strip()

        # اگر مبلغ مستقیماً آمده:
        # انتقال 500
        #
        # در این حالت باید ریپلای وجود داشته باشد.
        if raw.isdigit():
            await update.message.reply_text(
                "❌ برای انتقال با مبلغ، "
                "روی پیام گیرنده ریپلای کنید.\n\n"
                "مثال:\n"
                "انتقال 500"
            )
            return

        try:
            target_id = int(raw)
        except Exception:
            target_id = find_user_by_username(raw)

        if not target_id:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return

        if target_id == uid:
            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )
            return

        if str(target_id) not in data["users"]:
            await update.message.reply_text(
                "❌ این کاربر هنوز داخل ربات ثبت نشده است."
            )
            return

        target_name = data["users"][
            str(target_id)
        ].get("name", "کاربر")

    else:

        await update.message.reply_text(
            "👥 انتقال DOGS\n\n"
            "برای انتقال روی پیام شخص ریپلای کنید:\n\n"
            "انتقال 500\n\n"
            "یا:\n"
            "انتقال @username"
        )

        return

    # -----------------------------------------
    # اگر مبلغ در همان پیام آمده باشد
    # -----------------------------------------

    if context.args:

        try:
            amount = int(
                context.args[0]
                .replace(",", "")
            )

            if amount > 0:

                await execute_transfer(
                    update,
                    context,
                    uid,
                    target_id,
                    amount
                )

                return

        except Exception:
            pass

    # -----------------------------------------
    # اگر مبلغ هنوز وارد نشده
    # -----------------------------------------

    TRANSFER_STATE[uid] = {
        "step": "amount",
        "target": target_id,
        "target_name": target_name
    }

    await update.message.reply_text(
        f"👤 گیرنده: {target_name}\n\n"
        "💰 مقدار DOGS را ارسال کنید.\n\n"
        "مثال:\n"
        "500"
    )


# =========================================================
# EXECUTE TRANSFER
# =========================================================

async def execute_transfer(
    update,
    context,
    sender,
    receiver,
    amount
):

    try:
        amount = int(amount)
    except Exception:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )

        return False

    if amount <= 0:

        await update.message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )

        return False

    if sender == receiver:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return False

    if str(receiver) not in data["users"]:

        await update.message.reply_text(
            "❌ گیرنده پیدا نشد."
        )

        return False

    if get_balance(sender) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return False

    # کم کردن از فرستنده
    if not remove_balance(
        sender,
        amount
    ):

        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )

        return False

    # اضافه کردن به گیرنده
    if not add_balance(
        receiver,
        amount
    ):

        # برگشت پول در صورت خطا
        add_balance(
            sender,
            amount
        )

        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )

        return False

    save_data()

    await update.message.reply_text(
        "✅ انتقال با موفقیت انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {receiver}\n"
        f"💳 موجودی شما: "
        f"{get_balance(sender):,} DOGS",
        reply_markup=main_keyboard(sender)
    )

    # اطلاع گیرنده
    try:

        await context.bot.send_message(
            receiver,
            "💰 دریافت DOGS\n\n"
            f"مبلغ {amount:,} DOGS "
            "به حساب شما انتقال داده شد.\n\n"
            f"💳 موجودی شما: "
            f"{get_balance(receiver):,} DOGS"
        )

    except Exception:
        pass

    return True


# =========================================================
# TRANSFER AMOUNT
# =========================================================

async def transfer_amount(
    update,
    context
):

    uid = update.effective_user.id

    state = TRANSFER_STATE.get(uid)

    if not state:
        return

    if state.get("step") != "amount":
        return

    try:

        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )

    except Exception:

        await update.message.reply_text(
            "❌ فقط عدد وارد کنید.\n\n"
            "مثال: 500"
        )

        return

    target = state["target"]

    success = await execute_transfer(
        update,
        context,
        uid,
        target,
        amount
    )

    if success:

        TRANSFER_STATE.pop(
            uid,
            None
        )


# =========================================================
# GAME KEYBOARD
# =========================================================

def game_keyboard(game_id):

    return InlineKeyboardMarkup(
        [
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
        ]
    )


# =========================================================
# CREATE GAME
# =========================================================

async def game_create(update, context):

    chat = update.effective_chat

    if chat.type not in [
        "group",
        "supergroup"
    ]:

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ انجام می‌شود."
        )

        return

    user = update.effective_user

    create_user(user)

    # -----------------------------------------
    # بدون مبلغ
    # -----------------------------------------

    if not context.args:

        await update.message.reply_text(
            "🎮 ساخت بازی\n\n"
            "مثال:\n"
            "/game 500\n\n"
            f"حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"حداکثر بازی: {MAX_GAME:,} DOGS\n\n"
            "💡 مبلغ بازی می‌تواند هر عددی "
            "بین حداقل و حداکثر باشد."
        )

        return

    # -----------------------------------------
    # دریافت مبلغ
    # -----------------------------------------

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
            "/game 500"
        )

        return

    # -----------------------------------------
    # حداقل
    # -----------------------------------------

    if bet < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی "
            f"{MIN_GAME:,} DOGS است."
        )

        return

    # -----------------------------------------
    # حداکثر
    # -----------------------------------------

    if bet > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر مبلغ بازی "
            f"{MAX_GAME:,} DOGS است."
        )

        return

    # -----------------------------------------
    # موجودی
    # -----------------------------------------

    if get_balance(user.id) < bet:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💳 موجودی: "
            f"{get_balance(user.id):,} DOGS"
        )

        return

    # -----------------------------------------
    # رزرو مبلغ بازیکن اول
    # -----------------------------------------

    if not remove_balance(
        user.id,
        bet
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    # -----------------------------------------
    # ساخت شناسه بازی
    # -----------------------------------------

    game_id = (
        f"{chat.id}_"
        f"{int(time.time() * 1000)}_"
        f"{user.id}"
    )

    GAMES[game_id] = {
        "id": game_id,
        "chat_id": chat.id,
        "creator": user.id,
        "creator_name": (
            user.first_name or "کاربر"
        ),
        "bet": bet,
        "joiner": None,
        "joiner_name": "",
        "status": "waiting",
        "message_id": None
    }

    # -----------------------------------------
    # پیام بازی
    # -----------------------------------------

    msg = await update.message.reply_text(
        "🎮 بازی جدید ساخته شد!\n\n"
        f"👤 سازنده: "
        f"{user.first_name or 'کاربر'}\n"
        f"💰 مبلغ بازی: "
        f"{bet:,} DOGS\n\n"
        f"📌 حداقل بازی: "
        f"{MIN_GAME:,}\n"
        f"📌 حداکثر بازی: "
        f"{MAX_GAME:,}\n\n"
        "👥 یک نفر برای ورود روی "
        "«🎮 بازی با دوستان» بزند.",
        reply_markup=game_keyboard(game_id)
    )

    GAMES[game_id]["message_id"] = (
        msg.message_id
    )


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(
    update,
    context
):

    q = update.callback_query

    try:
        await q.answer()
    except Exception:
        pass

    try:

        action, game_id = (
            q.data.split(":", 1)
        )

    except Exception:
        return

    game = GAMES.get(game_id)

    if not game:

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )

        return

    uid = q.from_user.id

    # =====================================================
    # CANCEL
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:

            await q.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True
            )

            return

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True
            )

            return

        game["status"] = "cancelled"

        # برگشت مبلغ سازنده
        add_balance(
            game["creator"],
            game["bet"]
        )

        save_data()

        await q.message.edit_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ "
            f"{game['bet']:,} DOGS "
            "به موجودی سازنده برگشت."
        )

        return

    # =====================================================
    # JOIN
    # =====================================================

    if action == "game_join":

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی قبلاً شروع شده است.",
                show_alert=True
            )

            return

        if uid == game["creator"]:

            await q.answer(
                "❌ سازنده نمی‌تواند وارد بازی خودش شود.",
                show_alert=True
            )

            return

        create_user(
            q.from_user
        )

        # بررسی موجودی بازیکن دوم
        if get_balance(uid) < game["bet"]:

            await q.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return

        # رزرو مبلغ بازیکن دوم
        if not remove_balance(
            uid,
            game["bet"]
        ):

            await q.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )

            return

        game["joiner"] = uid

        game["joiner_name"] = (
            q.from_user.first_name
            or "کاربر"
        )

        game["status"] = "playing"

        await q.message.edit_text(
            "🎮 بازی شروع شد!\n\n"
            f"👤 بازیکن اول: "
            f"{game['creator_name']}\n"
            f"👤 بازیکن دوم: "
            f"{game['joiner_name']}\n\n"
            f"💰 مبلغ هر بازیکن: "
            f"{game['bet']:,} DOGS\n\n"
            "🎲 در حال مشخص کردن نتیجه..."
        )

        # =================================================
        # تعیین برنده
        # =================================================

        winner = random.choice(
            [
                game["creator"],
                game["joiner"]
            ]
        )

        loser = (
            game["joiner"]
            if winner == game["creator"]
            else game["creator"]
        )

        winner_name = (
            game["creator_name"]
            if winner == game["creator"]
            else game["joiner_name"]
        )

        loser_name = (
            game["joiner_name"]
            if winner == game["creator"]
            else game["creator_name"]
        )

        # =================================================
        # محاسبه جایزه
        #
        # بازی 500:
        # کل پول = 1000
        # سهم مالک = 100
        # جایزه برنده = 900
        #
        # بازی 1000:
        # کل پول = 2000
        # سهم مالک = 200
        # جایزه برنده = 1800
        #
        # بازی 20000:
        # کل پول = 40000
        # سهم مالک = 4000
        # جایزه برنده = 36000
        # =================================================

        total_pot = game["bet"] * 2

        owner_fee = int(
            total_pot * 10 / 100
        )

        winner_prize = (
            total_pot - owner_fee
        )

        owner_id = data.get(
            "owner",
            OWNER_ID
        )

        # جایزه برنده
        add_balance(
            winner,
            winner_prize
        )

        # سهم مالک
        if owner_id != winner:

            add_balance(
                owner_id,
                owner_fee
            )

        # ثبت نتیجه
        game["winner"] = winner
        game["loser"] = loser
        game["winner_prize"] = winner_prize
        game["owner_fee"] = owner_fee
        game["total_pot"] = total_pot
        game["status"] = "finished"

        save_data()

        # =================================================
        # نتیجه
        # =================================================

        result = (
            "🏆 نتیجه بازی\n\n"
            f"🥇 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"
            f"💰 مبلغ هر نفر: "
            f"{game['bet']:,} DOGS\n"
            f"💰 کل بازی: "
            f"{total_pot:,} DOGS\n\n"
            f"🏆 جایزه برنده: "
            f"{winner_prize:,} DOGS\n"
            f"👑 سهم مالک: "
            f"{owner_fee:,} DOGS"
        )

        await q.message.edit_text(
            result
        )

        # =================================================
        # پیام برنده
        # =================================================

        try:

            await context.bot.send_message(
                winner,
                "🎉 تبریک!\n\n"
                "شما برنده بازی شدید.\n\n"
                f"🏆 جایزه: "
                f"{winner_prize:,} DOGS\n\n"
                f"💳 موجودی شما: "
                f"{get_balance(winner):,} DOGS"
            )

        except Exception:
            pass

        # =================================================
        # پیام بازنده
        # =================================================

        try:

            await context.bot.send_message(
                loser,
                "❌ شما بازی را باختید.\n\n"
                f"💰 مبلغ بازی: "
                f"{game['bet']:,} DOGS"
            )

        except Exception:
            pass

        return

# =========================================================
# OWNER PANEL
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
            )
        ],
        [
            InlineKeyboardButton(
                "📋 واریزی‌ها",
                callback_data="adm_deposits"
            ),
            InlineKeyboardButton(
                "💸 برداشت‌ها",
                callback_data="adm_withdraws"
            )
        ],
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="adm_stats"
            )
        ]
    ])


async def owner_panel(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ شما دسترسی مالک را ندارید."
        )

        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        "یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=owner_panel_keyboard()
    )


# =========================================================
# OWNER STATES
# =========================================================

OWNER_STATE = {}


async def owner_panel_callback(
    update,
    context
):

    q = update.callback_query

    if not is_owner(
        q.from_user.id
    ):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    await q.answer()

    uid = q.from_user.id

    action = q.data

    # =====================================================
    # ADD BALANCE
    # =====================================================

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

    # =====================================================
    # REMOVE BALANCE
    # =====================================================

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

    # =====================================================
    # REFERRAL REWARD
    # =====================================================

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

    # =====================================================
    # DEPOSITS
    # =====================================================

    if action == "adm_deposits":

        pending = [
            item
            for item in data["deposits"].values()
            if item.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "📋 واریزی در انتظار وجود ندارد."
            )

            return

        text = (
            "📋 واریزی‌های در انتظار\n\n"
        )

        for item in pending[-20:]:

            text += (
                f"🆔 {item['request_id']}\n"
                f"👤 کاربر: {item['user_id']}\n"
                f"💰 مبلغ: "
                f"{int(item['amount']):,} DOGS\n"
                f"🐶 روش: {item.get('type', 'ULTRA')}\n\n"
            )

        await q.message.reply_text(
            text
        )

        return

    # =====================================================
    # WITHDRAWS
    # =====================================================

    if action == "adm_withdraws":

        pending = [
            item
            for item in data["withdraws"].values()
            if item.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "💸 برداشت در انتظار وجود ندارد."
            )

            return

        text = (
            "💸 برداشت‌های در انتظار\n\n"
        )

        for item in pending[-20:]:

            text += (
                f"🆔 {item['request_id']}\n"
                f"👤 کاربر: {item['user_id']}\n"
                f"💰 مبلغ: "
                f"{int(item['amount']):,} DOGS\n"
                f"📥 ولت:\n"
                f"{item['wallet']}\n\n"
            )

        await q.message.reply_text(
            text
        )

        return

    # =====================================================
    # STATS
    # =====================================================

    if action == "adm_stats":

        users_count = len(
            data["users"]
        )

        total_balance = 0

        for uid_key in data["users"]:

            total_balance += get_balance(
                uid_key
            )

        pending_deposits = sum(
            1
            for x in data["deposits"].values()
            if x.get("status") == "pending"
        )

        pending_withdraws = sum(
            1
            for x in data["withdraws"].values()
            if x.get("status") == "pending"
        )

        active_games = sum(
            1
            for x in GAMES.values()
            if x.get("status") in [
                "waiting",
                "playing"
            ]
        )

        finished_games = sum(
            1
            for x in GAMES.values()
            if x.get("status") == "finished"
        )

        await q.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 تعداد کاربران: "
            f"{users_count:,}\n"
            f"💰 مجموع موجودی کاربران: "
            f"{total_balance:,} DOGS\n\n"
            f"🎮 بازی‌های فعال: "
            f"{active_games:,}\n"
            f"🏆 بازی‌های تمام‌شده: "
            f"{finished_games:,}\n\n"
            f"💳 واریزی در انتظار: "
            f"{pending_deposits:,}\n"
            f"💸 برداشت در انتظار: "
            f"{pending_withdraws:,}\n\n"
            f"👑 آیدی مالک: "
            f"{data.get('owner', OWNER_ID)}"
        )

        return


# =========================================================
# OWNER STATE RECEIVER
# =========================================================

async def owner_state_receive(
    update,
    context
):

    uid = update.effective_user.id

    if not is_owner(uid):
        return

    state = OWNER_STATE.get(uid)

    if not state:
        return

    text = update.message.text.strip()

    action = state.get("action")
    step = state.get("step")

    # =====================================================
    # ADD / REMOVE
    # =====================================================

    if action in [
        "add",
        "remove"
    ]:

        if step == "user":

            try:
                target = int(text)
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

        if step == "amount":

            try:
                amount = int(
                    text.replace(",", "")
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

            # -------------------------
            # ADD
            # -------------------------

            if action == "add":

                add_balance(
                    target,
                    amount
                )

                await update.message.reply_text(
                    "✅ موجودی شارژ شد.\n\n"
                    f"👤 کاربر: {target}\n"
                    f"💰 مبلغ: {amount:,} DOGS\n"
                    f"💳 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

                try:

                    await context.bot.send_message(
                        target,
                        "💰 موجودی شما توسط مالک شارژ شد.\n\n"
                        f"➕ مبلغ: {amount:,} DOGS\n"
                        f"💳 موجودی جدید: "
                        f"{get_balance(target):,} DOGS"
                    )

                except Exception:
                    pass

            # -------------------------
            # REMOVE
            # -------------------------

            else:

                if get_balance(target) < amount:

                    await update.message.reply_text(
                        "❌ موجودی کاربر کافی نیست."
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
                    f"💳 موجودی جدید: "
                    f"{get_balance(target):,} DOGS"
                )

                try:

                    await context.bot.send_message(
                        target,
                        "⚠️ موجودی شما توسط مالک تغییر کرد.\n\n"
                        f"➖ مبلغ: {amount:,} DOGS\n"
                        f"💳 موجودی جدید: "
                        f"{get_balance(target):,} DOGS"
                    )

                except Exception:
                    pass

            OWNER_STATE.pop(
                uid,
                None
            )

            save_data()

            return

    # =====================================================
    # REFERRAL REWARD
    # =====================================================

    if action == "reward":

        try:
            amount = int(
                text.replace(",", "")
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
            f"{amount:,} DOGS"
        )

        return


# =========================================================
# ADMIN COMMAND
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
# TRANSFER COMMAND
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
# GAME COMMAND
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
# GAME + TRANSFER SYSTEM
# =========================================================

MIN_GAME = 500
MAX_GAME = 20000

GAMES = {}
TRANSFER_STATE = {}


# =========================================================
# GAME KEYBOARD
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

async def game_create(update, context):

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

    text = update.message.text.strip()

    parts = text.split()

    if len(parts) < 2:

        await update.message.reply_text(
            "🎮 بازی دوستان\n\n"
            "مثال:\n"
            "بازی 500\n\n"
            f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"💰 حداکثر بازی: {MAX_GAME:,} DOGS"
        )
        return

    try:
        bet = int(
            parts[1].replace(",", "")
        )
    except Exception:

        await update.message.reply_text(
            "❌ مبلغ بازی باید عدد باشد.\n\n"
            "مثال:\n"
            "بازی 500"
        )
        return

    # =====================================================
    # MINIMUM
    # =====================================================

    if bet < MIN_GAME:

        await update.message.reply_text(
            "❌ مبلغ بازی کمتر از حد مجاز است.\n\n"
            f"💰 حداقل بازی: {MIN_GAME:,} DOGS"
        )
        return

    # =====================================================
    # MAXIMUM
    # =====================================================

    if bet > MAX_GAME:

        await update.message.reply_text(
            "❌ مبلغ بازی بیشتر از حد مجاز است.\n\n"
            f"💰 حداکثر بازی: {MAX_GAME:,} DOGS"
        )
        return

    # =====================================================
    # BALANCE
    # =====================================================

    balance = get_balance(user.id)

    if balance < bet:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 مبلغ بازی: {bet:,} DOGS\n"
            f"💳 موجودی شما: {balance:,} DOGS"
        )
        return

    # =====================================================
    # RESERVE MONEY
    # =====================================================

    if not remove_balance(
        user.id,
        bet
    ):

        await update.message.reply_text(
            "❌ مبلغ بازی رزرو نشد."
        )
        return

    # =====================================================
    # GAME ID
    # =====================================================

    game_id = (
        f"{update.effective_chat.id}_"
        f"{user.id}_"
        f"{int(time.time() * 1000)}"
    )

    GAMES[game_id] = {

        "game_id": game_id,

        "chat_id":
            update.effective_chat.id,

        "creator":
            user.id,

        "creator_name":
            user.first_name or "کاربر",

        "creator_username":
            user.username or "",

        "bet":
            bet,

        "status":
            "waiting",

        "joiner":
            None,

        "joiner_name":
            "",

        "winner":
            None,

        "loser":
            None,

        "created":
            datetime.now().isoformat()
    }

    # =====================================================
    # GAME MESSAGE
    # =====================================================

    msg = await update.message.reply_text(

        "🎮 بازی جدید ساخته شد!\n\n"

        f"💰 مبلغ بازی: {bet:,} DOGS\n\n"

        f"👤 سازنده: "
        f"{user.first_name or 'کاربر'}\n\n"

        "👥 یک نفر دیگر وارد بازی شود.\n\n"

        "👇 برای شرکت روی دکمه زیر بزنید.",

        reply_markup=
            game_keyboard(game_id)
    )

    GAMES[game_id]["message_id"] = (
        msg.message_id
    )

    save_data()


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

        action, game_id = q.data.split(
            ":",
            1
        )

    except Exception:
        return

    game = GAMES.get(game_id)

    if not game:

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )
        return

    uid = q.from_user.id

    # =====================================================
    # CANCEL
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:

            await q.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
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
            "به موجودی سازنده برگشت."
        )

        return

    # =====================================================
    # JOIN
    # =====================================================

    if action == "game_join":

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی قبلاً شروع شده است.",
                show_alert=True
            )
            return

        if uid == game["creator"]:

            await q.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )
            return

        create_user(
            q.from_user
        )

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
                "❌ مبلغ بازی رزرو نشد.",
                show_alert=True
            )
            return

        # =================================================
        # PLAYER 2
        # =================================================

        game["joiner"] = uid

        game["joiner_name"] = (
            q.from_user.first_name
            or "کاربر"
        )

        game["joiner_username"] = (
            q.from_user.username
            or ""
        )

        game["status"] = "playing"

        save_data()

        await q.message.edit_text(

            "🎮 بازی شروع شد!\n\n"

            f"👤 بازیکن اول: "
            f"{game['creator_name']}\n"

            f"👤 بازیکن دوم: "
            f"{game['joiner_name']}\n\n"

            f"💰 شرط هر نفر: "
            f"{game['bet']:,} DOGS\n\n"

            "🎲 در حال تعیین برنده..."
        )

        # =================================================
        # RANDOM WINNER
        # =================================================

        players = [
            game["creator"],
            game["joiner"]
        ]

        winner = random.choice(
            players
        )

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
        # MONEY
        # =================================================

        total_pot = (
            game["bet"] * 2
        )

        # 20 درصد برای مالک
        owner_fee = (
            total_pot // 10
        )

        # 80 درصد برای برنده
        winner_prize = (
            total_pot - owner_fee
        )

        owner_id = data.get(
            "owner",
            OWNER_ID
        )

        # =================================================
        # OWNER FEE
        # =================================================

        if str(owner_id) in data["users"]:

            add_balance(
                owner_id,
                owner_fee
            )

        # =================================================
        # WINNER
        # =================================================

        add_balance(
            winner,
            winner_prize
        )

        # =================================================
        # SAVE GAME
        # =================================================

        game["winner"] = winner
        game["loser"] = loser

        game["total_pot"] = (
            total_pot
        )

        game["owner_fee"] = (
            owner_fee
        )

        game["winner_prize"] = (
            winner_prize
        )

        game["status"] = (
            "finished"
        )

        game["finished"] = (
            datetime.now().isoformat()
        )

        save_data()

        # =================================================
        # RESULT
        # =================================================

        result = (

            "🏆 نتیجه بازی\n\n"

            f"🥇 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"

            f"💰 شرط هر نفر: "
            f"{game['bet']:,} DOGS\n"

            f"🏦 سهم مالک: "
            f"{owner_fee:,} DOGS\n"

            f"🏆 جایزه برنده: "
            f"{winner_prize:,} DOGS\n\n"

            "🎉 تبریک به برنده!"
        )

        await q.message.edit_text(
            result
        )

        # =================================================
        # WINNER MESSAGE
        # =================================================

        try:

            await context.bot.send_message(

                winner,

                "🏆 تبریک!\n\n"
                "شما برنده بازی شدید.\n\n"

                f"🏆 جایزه: "
                f"{winner_prize:,} DOGS\n"

                f"💳 موجودی: "
                f"{get_balance(winner):,} DOGS"
            )

        except Exception:
            pass

        # =================================================
        # LOSER MESSAGE
        # =================================================

        try:

            await context.bot.send_message(

                loser,

                "❌ بازی را باختید.\n\n"

                f"💰 مبلغ بازی: "
                f"{game['bet']:,} DOGS\n"

                f"💳 موجودی: "
                f"{get_balance(loser):,} DOGS"
            )

        except Exception:
            pass


# =========================================================
# TRANSFER
# =========================================================

async def transfer_farsi(
    update,
    context
):

    user = update.effective_user

    create_user(user)

    text = update.message.text.strip()

    parts = text.split()

    # =====================================================
    # AMOUNT
    # =====================================================

    if len(parts) != 2:

        await update.message.reply_text(

            "👥 انتقال DOGS\n\n"

            "مثال:\n"
            "انتقال 500\n\n"

            "اگر روی پیام کاربر ریپلای کنید، "
            "مبلغ مستقیماً برای همان کاربر ارسال می‌شود."
        )

        return

    try:

        amount = int(
            parts[1].replace(",", "")
        )

    except Exception:

        await update.message.reply_text(
            "❌ مبلغ انتقال باید عدد باشد."
        )
        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    # =====================================================
    # TARGET BY REPLY
    # =====================================================

    target = None

    if update.message.reply_to_message:

        target = (
            update.message.reply_to_message
            .from_user
        )

        if target:

            create_user(
                target
            )

            target_id = target.id

        else:

            target_id = None

    else:

        await update.message.reply_text(

            "❌ برای انتقال باید روی پیام "
            "کاربر ریپلای کنید.\n\n"

            "مثال:\n"
            "انتقال 500"
        )

        return

    # =====================================================
    # SELF
    # =====================================================

    if target_id == user.id:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    # =====================================================
    # BALANCE
    # =====================================================

    if get_balance(user.id) < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💰 مبلغ انتقال: "
            f"{amount:,} DOGS\n"

            f"💳 موجودی شما: "
            f"{get_balance(user.id):,} DOGS"
        )

        return

    # =====================================================
    # TRANSFER
    # =====================================================

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )
        return

    add_balance(
        target_id,
        amount
    )

    save_data()

    # =====================================================
    # SENDER
    # =====================================================

    await update.message.reply_text(

        "✅ انتقال با موفقیت انجام شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n"

        f"👤 گیرنده: "
        f"{target.first_name or target_id}\n\n"

        f"💳 موجودی شما: "
        f"{get_balance(user.id):,} DOGS"
    )

    # =====================================================
    # RECEIVER
    # =====================================================

    try:

        await context.bot.send_message(

            target_id,

            "💰 واریز جدید دریافت کردید.\n\n"

            f"➕ مبلغ: "
            f"{amount:,} DOGS\n"

            f"👤 فرستنده: "
            f"{user.first_name or 'کاربر'}\n\n"

            f"💳 موجودی شما: "
            f"{get_balance(target_id):,} DOGS"
        )

    except Exception:
        pass

# =========================================================
# TEXT COMMAND ROUTER - PART 6
# =========================================================

async def text_command_router(update, context):
    if not update.message:
        return

    text = (update.message.text or "").strip()

    if not text:
        return

    uid = update.effective_user.id

    # =====================================================
    # بازی 500
    # =====================================================

    if text.startswith("بازی"):

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "🎮 روش استفاده:\n\n"
                "بازی 500\n\n"
                f"حداقل: {MIN_GAME:,} DOGS\n"
                f"حداکثر: {MAX_GAME:,} DOGS"
            )
            return

        await game_create(
            update,
            context
        )

        return

    # =====================================================
    # انتقال 500
    # =====================================================

    if text.startswith("انتقال"):

        parts = text.split()

        if len(parts) != 2:

            await update.message.reply_text(
                "👥 روش استفاده:\n\n"
                "روی پیام کاربر ریپلای کنید و بنویسید:\n\n"
                "انتقال 500"
            )
            return

        await transfer_farsi(
            update,
            context
        )

        return

    # =====================================================
    # منوی اصلی
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
            "روی پیام شخص موردنظر ریپلای کنید و بنویسید:\n\n"
            "انتقال 500"
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

    # =====================================================
    # BACK
    # =====================================================

    if text == "🔙 برگشت":

        await update.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard(uid)
        )

        return


# =========================================================
# PHOTO ROUTER
# =========================================================

async def photo_message_router(
    update,
    context
):

    uid = update.effective_user.id

    # رسید واریز
    if uid in DEPOSIT_DATA:

        await deposit_receipt(
            update,
            context
        )

        return


# =========================================================
# CONTACT ROUTER
# =========================================================

async def contact_message_router(
    update,
    context
):

    if not update.message.contact:
        return

    await phone_receive(
        update,
        context
    )


# =========================================================
# ERROR SAFE HANDLER
# =========================================================

async def safe_error_handler(
    update,
    context
):

    try:

        print(
            "BOT ERROR:",
            context.error
        )

        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__
        )

    except Exception:
        pass

# =========================================================
# MAIN - PART 7
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
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
            start
        )
    )

    # دستورات قبلی انتقال
    app.add_handler(
        CommandHandler(
            "transfer",
            transfer_command
        )
    )

    # بازی قدیمی در صورت وجود
    app.add_handler(
        CommandHandler(
            "game",
            game_command
        )
    )

    # پنل مدیریت
    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # =====================================================
    # JOIN CALLBACK
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
        )
    )

    # =====================================================
    # DEPOSIT CALLBACK
    # =====================================================

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

    # =====================================================
    # WITHDRAW CALLBACK
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            withdraw_decision,
            pattern=r"^with_(ok|no):"
        )
    )

    # =====================================================
    # OWNER CALLBACK
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            owner_transfer_decision,
            pattern=r"^owner_(yes|no)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_panel_callback,
            pattern=r"^adm_"
        )
    )

    # =====================================================
    # GAME CALLBACK
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^game_(join|cancel):"
        )
    )

    # =====================================================
    # CONTACT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_message_router
        )
    )

    # =====================================================
    # PHOTO / RECEIPT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_message_router
        )
    )

    # =====================================================
    # فارسی
    #
    # بازی 500
    # انتقال 500
    # واریزی
    # برداشت
    # پروفایل
    # ...
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_command_router
        )
    )

    # =====================================================
    # ERROR HANDLER
    # =====================================================

    app.add_error_handler(
        safe_error_handler
    )

    print(
        "================================="
    )

    print(
        "BOT STARTED"
    )

    print(
        "GAME: بازی 500"
    )

    print(
        "TRANSFER: انتقال 500"
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
        "================================="
    )

    # =====================================================
    # START BOT
    # =====================================================

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
