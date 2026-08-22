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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

OWNER_ID = 8552447077

FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_B_ET"

ULTRA_ID = "@CyyFr"
ULTRA_WALLET = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

# GAME
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
# DATA
# =========================================================

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            if not isinstance(loaded, dict):
                return json.loads(
                    json.dumps(DEFAULT_DATA)
                )

            for key, value in DEFAULT_DATA.items():
                if key not in loaded:
                    loaded[key] = json.loads(
                        json.dumps(value)
                    )

            if not isinstance(
                loaded.get("users"),
                dict
            ):
                loaded["users"] = {}

            if not isinstance(
                loaded.get("deposits"),
                dict
            ):
                loaded["deposits"] = {}

            if not isinstance(
                loaded.get("withdraws"),
                dict
            ):
                loaded["withdraws"] = {}

            return loaded

    except Exception:
        traceback.print_exc()

    return json.loads(
        json.dumps(DEFAULT_DATA)
    )


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
    user_id,
    seconds=1.5
):
    now = time.time()

    key = str(user_id)

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
    if not user:
        return

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

    user_data = data["users"][uid]

    user_data["id"] = user.id

    user_data["name"] = (
        user.first_name
        or user_data.get(
            "name",
            ""
        )
    )

    user_data["username"] = (
        user.username
        or user_data.get(
            "username",
            ""
        )
    )

    user_data.setdefault(
        "phone",
        ""
    )

    user_data.setdefault(
        "balance",
        0
    )

    user_data.setdefault(
        "refs",
        0
    )

    user_data.setdefault(
        "ref_by",
        None
    )

    save_data()


def get_balance(user_id):
    try:
        return int(
            data["users"]
            [str(user_id)]
            .get("balance", 0)
        )
    except Exception:
        return 0


def add_balance(
    user_id,
    amount
):
    try:
        uid = str(user_id)

        amount = int(amount)

        if uid not in data["users"]:
            return False

        current = get_balance(
            user_id
        )

        new_balance = current + amount

        if new_balance < 0:
            return False

        data["users"][uid][
            "balance"
        ] = new_balance

        save_data()

        return True

    except Exception:
        return False


def remove_balance(
    user_id,
    amount
):
    try:
        amount = int(amount)

        if amount < 0:
            return False

        if get_balance(
            user_id
        ) < amount:
            return False

        return add_balance(
            user_id,
            -amount
        )

    except Exception:
        return False


def is_owner(user_id):
    try:
        return int(user_id) == int(
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

def main_keyboard(user_id):
    buttons = [
        [
            "💳 واریزی",
            "💰 برداشت"
        ],
        [
            "👥 زیرمجموعه",
            "🎧 پشتیبانی"
        ],
        [
            "👤 پروفایل",
            "👥 انتقال"
        ],
        [
            "🎮 بازی ۵۰۰"
        ],
    ]

    if is_owner(user_id):
        buttons.append([
            "⚙️ پنل مدیریت"
        ])

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
        ],
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


# =========================================================
# FORCE JOIN
# =========================================================

async def check_join(
    user_id,
    context
):
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
        print(
            "JOIN ERROR:",
            e
        )

        return False


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

    if not user:
        return

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
# START
# =========================================================

async def start(
    update,
    context
):
    user = update.effective_user

    if not user:
        return

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
            "❌ ابتدا عضو کانال و گپ شوید.",
            reply_markup=join_keyboard()
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\n"
            "فقط شماره ایران +98 قبول است.",
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

    if not update.message:
        return

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
# REFERRAL MENU
# =========================================================

async def referral_menu(
    update,
    context
):
    user = update.effective_user

    create_user(user)

    bot = await context.bot.get_me()

    username = bot.username or "bot"

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
        "👥 سیستم زیرمجموعه\n\n"
        f"🔗 لینک دعوت شما:\n{link}\n\n"
        f"👥 تعداد زیرمجموعه: {refs}\n"
        f"💰 جایزه هر نفر: "
        f"{reward:,} DOGS",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(
    update,
    context
):
    user = update.effective_user

    create_user(user)

    if not anti_spam(user.id):
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "🐶 ULTRA / DOGS",
                callback_data="dep_ultra"
            )
        ],
        [
            InlineKeyboardButton(
                "💱 صرافی",
                callback_data="dep_exchange"
            )
        ],
    ]

    await update.message.reply_text(
        "💳 روش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


async def deposit_type(
    update,
    context
):
    query = update.callback_query

    await query.answer()

    uid = query.from_user.id

    if query.data == "dep_ultra":

        DEPOSIT_DATA[uid] = {
            "type": "ULTRA",
            "step": "amount"
        }

        text = (
            "🐶 واریز ULTRA\n\n"
            "مقدار DOGS را وارد کنید.\n"
            f"حداقل واریز: "
            f"{MIN_DEPOSIT:,} DOGS"
        )

    else:

        DEPOSIT_DATA[uid] = {
            "type": "EXCHANGE",
            "step": "amount"
        }

        text = (
            "💱 واریز صرافی\n\n"
            "مبلغ را وارد کنید.\n"
            "بعد از آن ولت نمایش داده می‌شود."
        )

    await query.message.edit_text(
        text
    )


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
            "❌ مقدار فقط عدد باشد."
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ مقدار نامعتبر است."
        )

        return

    typ = DEPOSIT_DATA[uid][
        "type"
    ]

    if (
        typ == "ULTRA"
        and amount < MIN_DEPOSIT
    ):

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

    if typ == "ULTRA":

        text = (
            "🐶 واریز ULTRA\n\n"
            f"مقدار: {amount:,} DOGS\n\n"
            f"ULTRA ID:\n"
            f"{ULTRA_ID}\n\n"
            "بعد از پرداخت، "
            "عکس رسید را ارسال کنید."
        )

    else:

        text = (
            "💱 واریز صرافی\n\n"
            f"مبلغ: {amount:,}\n\n"
            "ولت:\n"
            f"`{EXCHANGE_WALLET}`\n\n"
            "بعد از پرداخت عکس رسید "
            "یا لینک تراکنش را ارسال کنید."
        )

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


def deposit_buttons(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"dep_ok:{req_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"dep_no:{req_id}"
            ),
        ]
    ])


async def send_deposit_to_owner(
    context,
    req
):
    owner = data.get(
        "owner",
        OWNER_ID
    )

    req_id = req["request_id"]

    caption = (
        "💳 درخواست واریزی جدید\n\n"
        f"🆔 درخواست: {req_id}\n"
        f"👤 کاربر: {req['user_id']}\n"
        f"💰 نوع: {req['type']}\n"
        f"📊 مبلغ: {req['amount']:,} DOGS\n\n"
        "بررسی کنید."
    )

    markup = deposit_buttons(
        req_id
    )

    if req["kind"] == "photo":

        await context.bot.send_photo(
            chat_id=owner,
            photo=req["content"],
            caption=caption,
            reply_markup=markup
        )

    else:

        await context.bot.send_message(
            chat_id=owner,
            text=(
                caption
                + "\n\n🧾 رسید:\n"
                + req["content"]
            ),
            reply_markup=markup
        )


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

    req_id = (
        f"D{int(time.time()*1000)}"
        f"_{uid}"
    )

    info = DEPOSIT_DATA[uid]

    if update.message.photo:

        req = {
            "request_id": req_id,
            "user_id": uid,
            "type": info["type"],
            "amount": info["amount"],
            "kind": "photo",
            "content": update.message.photo[-1].file_id,
            "status": "pending",
            "created": datetime.now().isoformat()
        }

    elif (
        update.message.text
        and info["type"] == "EXCHANGE"
    ):

        req = {
            "request_id": req_id,
            "user_id": uid,
            "type": info["type"],
            "amount": info["amount"],
            "kind": "text",
            "content": update.message.text.strip(),
            "status": "pending",
            "created": datetime.now().isoformat()
        }

    else:

        await update.message.reply_text(
            "❌ برای این درخواست "
            "عکس رسید یا متن تراکنش ارسال کنید."
        )

        return

    data["deposits"][
        req_id
    ] = req

    save_data()

    try:

        await send_deposit_to_owner(
            context,
            req
        )

    except Exception:

        traceback.print_exc()

        await update.message.reply_text(
            "❌ ارسال درخواست به مالک انجام نشد."
        )

        return

    DEPOSIT_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ رسید ارسال شد.\n"
        "⏳ منتظر تایید مالک باشید.",
        reply_markup=main_keyboard(
            uid
        )
    )


async def deposit_decision(
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
        action, req_id = (
            query.data.split(
                ":",
                1
            )
        )
    except Exception:
        return

    req = data["deposits"].get(
        req_id
    )

    if not req:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if req.get(
        "status"
    ) != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    uid = req["user_id"]

    if action == "dep_ok":

        req["status"] = "approved"

        add_balance(
            uid,
            req["amount"]
        )

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "✅ واریز شما تایید شد.\n\n"
                f"💰 مبلغ: "
                f"{req['amount']:,} DOGS\n"
                f"💰 موجودی جدید: "
                f"{get_balance(uid):,} DOGS"
            )
        except Exception:
            pass

        try:
            await query.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await query.message.reply_text(
            f"✅ واریز کاربر {uid} تایید شد."
        )

    else:

        req["status"] = "rejected"

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "❌ درخواست واریز شما رد شد."
            )
        except Exception:
            pass

        try:
            await query.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await query.message.reply_text(
            f"❌ واریز کاربر {uid} رد شد."
        )


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(
    update,
    context
):
    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    if get_balance(uid) < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است.\n\n"
            f"💰 موجودی: "
            f"{get_balance(uid):,} DOGS"
        )

        return

    WITHDRAW_DATA[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(
        f"💰 مقدار برداشت را وارد کنید.\n\n"
        f"حداقل: {MIN_WITHDRAW:,} DOGS\n"
        f"موجودی: {get_balance(uid):,} DOGS",
        reply_markup=back_keyboard()
    )


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

    wallet = update.message.text.strip()

    if len(wallet) < 5:

        await update.message.reply_text(
            "❌ آدرس ولت نامعتبر است."
        )

        return

    amount = WITHDRAW_DATA[uid][
        "amount"
    ]

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        WITHDRAW_DATA.pop(
            uid,
            None
        )

        return

    req_id = (
        f"W{int(time.time()*1000)}"
        f"_{uid}"
    )

    req = {
        "request_id": req_id,
        "user_id": uid,
        "amount": amount,
        "wallet": wallet,
        "status": "pending",
        "created": datetime.now().isoformat()
    }

    data["withdraws"][
        req_id
    ] = req

    save_data()

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data=f"with_ok:{req_id}"
            ),
            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"with_no:{req_id}"
            ),
        ]
    ])

    try:

        await context.bot.send_message(
            data.get(
                "owner",
                OWNER_ID
            ),
            "💰 درخواست برداشت جدید\n\n"
            f"🆔 {req_id}\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مبلغ: {amount:,} DOGS\n\n"
            f"📥 ولت:\n{wallet}",
            reply_markup=markup
        )

    except Exception:

        add_balance(
            uid,
            amount
        )

        data["withdraws"][
            req_id
        ]["status"] = "failed"

        save_data()

        await update.message.reply_text(
            "❌ ارسال درخواست به مالک انجام نشد؛ "
            "مبلغ به موجودی شما برگشت."
        )

        WITHDRAW_DATA.pop(
            uid,
            None
        )

        return

    WITHDRAW_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ درخواست برداشت ارسال شد.\n"
        "⏳ مبلغ تا تعیین تکلیف رزرو است.",
        reply_markup=main_keyboard(
            uid
        )
    )


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
        action, req_id = (
            query.data.split(
                ":",
                1
            )
        )
    except Exception:
        return

    req = data["withdraws"].get(
        req_id
    )

    if not req:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if req.get(
        "status"
    ) != "pending":

        await query.message.reply_text(
            "⚠️ قبلاً بررسی شده."
        )

        return

    uid = req["user_id"]

    if action == "with_ok":

        req["status"] = "approved"

        text = (
            "✅ برداشت شما تایید شد.\n\n"
            f"💰 مبلغ: "
            f"{req['amount']:,} DOGS"
        )

        owner_text = (
            "✅ برداشت تایید شد."
        )

    else:

        req["status"] = "rejected"

        add_balance(
            uid,
            req["amount"]
        )

        text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ "
            f"{req['amount']:,} DOGS "
            "به موجودی برگشت."
        )

        owner_text = (
            "❌ برداشت رد شد."
        )

    save_data()

    try:
        await context.bot.send_message(
            uid,
            text
        )
    except Exception:
        pass

    try:
        await query.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await query.message.reply_text(
        owner_text
    )


# =========================================================
# TRANSFER
# =========================================================

def find_user_by_username(
    username
):
    username = (
        username
        .lstrip("@")
        .lower()
    )

    for uid, user in data[
        "users"
    ].items():

        if str(
            user.get(
                "username",
                ""
            )
        ).lower() == username:

            return int(uid)

    return None


async def transfer_start(
    update,
    context
):
    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    # Reply transfer
    if update.message.reply_to_message:

        target = (
            update.message
            .reply_to_message
            .from_user
        )

        if not target:
            return

        if target.id == uid:

            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )

            return

        if target.is_bot:

            await update.message.reply_text(
                "❌ نمی‌توانید به ربات انتقال دهید."
            )

            return

        create_user(target)

        TRANSFER_DATA[uid] = {
            "step": "amount",
            "target": target.id
        }

        await update.message.reply_text(
            f"👤 گیرنده: "
            f"{target.first_name}\n\n"
            "💰 مقدار DOGS را ارسال کنید."
        )

        return

    # Username / ID
    if context.args:

        raw = context.args[0]

        target_id = None

        try:
            target_id = int(raw)

        except Exception:
            target_id = (
                find_user_by_username(
                    raw
                )
            )

        if (
            not target_id
            or str(target_id)
            not in data["users"]
        ):

            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )

            return

        if target_id == uid:

            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )

            return

        TRANSFER_DATA[uid] = {
            "step": "amount",
            "target": target_id
        }

        await update.message.reply_text(
            "💰 مقدار DOGS را ارسال کنید."
        )

        return

    await update.message.reply_text(
        "👥 انتقال DOGS\n\n"
        "روی پیام کاربر ریپلای کن و /transfer بزن.\n\n"
        "یا:\n"
        "/transfer @username\n\n"
        "یا:\n"
        "/transfer USER_ID"
    )


async def transfer_amount(
    update,
    context
):
    uid = update.effective_user.id

    if uid not in TRANSFER_DATA:
        return

    if TRANSFER_DATA[uid].get(
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
            "❌ مقدار فقط عدد باشد."
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ مقدار نامعتبر است."
        )

        return

    target = TRANSFER_DATA[
        uid
    ]["target"]

    if target == uid:

        await update.message.reply_text(
            "❌ انتقال به خودتان ممکن نیست."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    if str(target) not in data[
        "users"
    ]:

        await update.message.reply_text(
            "❌ گیرنده پیدا نشد."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

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
        target,
        amount
    )

    TRANSFER_DATA.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: "
        f"{amount:,} DOGS\n"
        f"👤 گیرنده: {target}\n"
        f"💵 موجودی شما: "
        f"{get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(
            uid
        )
    )

    try:

        await context.bot.send_message(
            target,
            "💰 انتقال جدید\n\n"
            f"مبلغ: {amount:,} DOGS"
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
    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    user_data = data[
        "users"
    ][str(uid)]

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"🆔 ID: {uid}\n"
        f"👤 نام: "
        f"{user_data.get('name','')}\n"
        f"📱 شماره: "
        f"{user_data.get('phone') or 'ثبت نشده'}\n"
        f"👥 زیرمجموعه: "
        f"{user_data.get('refs',0)}\n"
        f"💰 موجودی: "
        f"{get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(
            uid
        )
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
        "مشکل خود را همینجا ارسال کنید."
    )


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
                "📊 آمار",
                callback_data="adm_stats"
            )
        ]
    ])


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
        "⚙️ پنل مدیریت",
        reply_markup=owner_panel_keyboard()
    )


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

    if action == "adm_add":

        OWNER_STATE[
            query.from_user.id
        ] = {
            "action": "add",
            "step": "user"
        }

        await query.message.reply_text(
            "🆔 آیدی کاربر را ارسال کنید."
        )

    elif action == "adm_remove":

        OWNER_STATE[
            query.from_user.id
        ] = {
            "action": "remove",
            "step": "user"
        }

        await query.message.reply_text(
            "🆔 آیدی کاربر را ارسال کنید."
        )

    elif action == "adm_reward":

        OWNER_STATE[
            query.from_user.id
        ] = {
            "action": "reward",
            "step": "amount"
        }

        await query.message.reply_text(
            f"💰 جایزه فعلی: "
            f"{int(data.get('ref_reward',50)):,} DOGS\n\n"
            "مقدار جدید را ارسال کنید."
        )

    elif action == "adm_owner":

        OWNER_STATE[
            query.from_user.id
        ] = {
            "action": "owner",
            "step": "user"
        }

        await query.message.reply_text(
            "👑 آیدی مالک جدید را ارسال کنید."
        )

    elif action == "adm_deposits":

        pending = [
            item
            for item in data[
                "deposits"
            ].values()
            if item.get(
                "status"
            ) == "pending"
        ]

        if not pending:

            await query.message.reply_text(
                "📋 واریزی معلقی وجود ندارد."
            )

        else:

            text = (
                "📋 واریزی‌های در انتظار:\n\n"
            )

            for item in pending[-20:]:

                text += (
                    f"🆔 {item['request_id']}\n"
                    f"👤 {item['user_id']}\n"
                    f"💰 {item['amount']:,} DOGS\n"
                    f"نوع: {item['type']}\n\n"
                )

            await query.message.reply_text(
                text
            )

    elif action == "adm_withdraws":

        pending = [
            item
            for item in data[
                "withdraws"
            ].values()
            if item.get(
                "status"
            ) == "pending"
        ]

        if not pending:

            await query.message.reply_text(
                "💸 برداشت معلقی وجود ندارد."
            )

        else:

            text = (
                "💸 برداشت‌های در انتظار:\n\n"
            )

            for item in pending[-20:]:

                text += (
                    f"🆔 {item['request_id']}\n"
                    f"👤 {item['user_id']}\n"
                    f"💰 {item['amount']:,} DOGS\n"
                    f"ولت:\n{item['wallet']}\n\n"
                )

            await query.message.reply_text(
                text
            )

    elif action == "adm_stats":

        users_count = len(
            data["users"]
        )

        total_balance = sum(
            get_balance(uid)
            for uid in data["users"]
        )

        await query.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {users_count}\n"
            f"💰 مجموع موجودی: "
            f"{total_balance:,} DOGS"
        )


# =========================================================
# OWNER STATE
# =========================================================

async def owner_state_receive(
    update,
    context
):
    uid = update.effective_user.id

    if not is_owner(uid):
        return

    if uid not in OWNER_STATE:
        return

    state = OWNER_STATE[uid]

    try:

        value = int(
            update.message.text
            .replace(",", "")
            .strip()
        )

    except Exception:

        value = None

    # -----------------------------------------------------
    # ADD / REMOVE
    # -----------------------------------------------------

    if state["action"] in [
        "add",
        "remove"
    ]:

        if state["step"] == "user":

            if (
                value is None
                or str(value)
                not in data["users"]
            ):

                await update.message.reply_text(
                    "❌ آیدی کاربر معتبر نیست."
                )

                return

            state["target"] = value

            state["step"] = "amount"

            await update.message.reply_text(
                "💰 مقدار DOGS را ارسال کنید."
            )

            return

        if state["step"] == "amount":

            if (
                value is None
                or value <= 0
            ):

                await update.message.reply_text(
                    "❌ مقدار نامعتبر است."
                )

                return

            target = state["target"]

            if state["action"] == "add":

                add_balance(
                    target,
                    value
                )

                message = (
                    f"✅ {value:,} DOGS "
                    "به موجودی اضافه شد."
                )

            else:

                if get_balance(
                    target
                ) < value:

                    await update.message.reply_text(
                        "❌ موجودی کاربر کافی نیست."
                    )

                    return

                remove_balance(
                    target,
                    value
                )

                message = (
                    f"✅ {value:,} DOGS "
                    "از موجودی کسر شد."
                )

            OWNER_STATE.pop(
                uid,
                None
            )

            await update.message.reply_text(
                message
            )

            return

    # -----------------------------------------------------
    # REWARD
    # -----------------------------------------------------

    if state["action"] == "reward":

        if (
            value is None
            or value < 0
        ):

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )

            return

        data["ref_reward"] = value

        save_data()

        OWNER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            f"✅ جایزه زیرمجموعه روی "
            f"{value:,} DOGS تنظیم شد."
        )

        return

    # -----------------------------------------------------
    # OWNER
    # -----------------------------------------------------

    if state["action"] == "owner":

        if (
            value is None
            or str(value)
            not in data["users"]
        ):

            await update.message.reply_text(
                "❌ کاربر باید قبلاً ثبت شده باشد."
            )

            return

        OWNER_STATE[uid] = {
            "action": "owner_confirm",
            "target": value
        }

        await update.message.reply_text(
            f"⚠️ انتقال مالکیت\n\n"
            f"👑 مالک جدید: {value}\n\n"
            "تایید می‌کنید؟",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=f"owner_yes:{value}"
                    ),
                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="owner_no"
                    )
                ]
            ])
        )

        return


# =========================================================
# OWNER TRANSFER DECISION
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
            "❌ خطا."
        )

        return

    if str(new_owner) not in data[
        "users"
    ]:

        await query.message.reply_text(
            "❌ کاربر پیدا نشد."
        )

        return

    data["owner"] = new_owner

    save_data()

    OWNER_STATE.pop(
        query.from_user.id,
        None
    )

    await query.message.reply_text(
        "✅ انتقال مالکیت انجام شد.\n\n"
        f"👑 مالک جدید: {new_owner}"
    )

    try:

        await context.bot.send_message(
            new_owner,
            "👑 شما مالک جدید ربات شدید."
        )

    except Exception:
        pass


# =========================================================
# GAME 500
# =========================================================

def game_keyboard(
    game_id
):
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
            "❌ بازی ۵۰۰ فقط داخل گپ انجام می‌شود."
        )

        return

    create_user(user)

    # عضویت اجباری
    if not await check_join(
        user.id,
        context
    ):

        await update.message.reply_text(
            "❌ ابتدا عضو کانال و گپ شوید."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "🎮 بازی ۵۰۰\n\n"
            "مثال:\n"
            "/game 500\n\n"
            f"💰 حداقل: {MIN_GAME:,} DOGS\n"
            f"💰 حداکثر: {MAX_GAME:,} DOGS\n\n"
            "قانون پرداخت:\n"
            "🏆 برنده: ۹۰٪\n"
            "👑 مالک: ۱۰٪"
        )

        return

    try:

        bet = int(
            context.args[0]
            .replace(",", "")
        )

    except Exception:

        await update.message.reply_text(
            "❌ مبلغ بازی باید عدد باشد."
        )

        return

    if bet < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل بازی "
            f"{MIN_GAME:,} DOGS است."
        )

        return

    if bet > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر بازی "
            f"{MAX_GAME:,} DOGS است."
        )

        return

    if get_balance(
        user.id
    ) < bet:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    # رزرو پول سازنده
    if not remove_balance(
        user.id,
        bet
    ):

        await update.message.reply_text(
            "❌ برداشت مبلغ بازی انجام نشد."
        )

        return

    game_id = (
        f"{chat.id}_"
        f"{user.id}_"
        f"{time.time_ns()}"
    )

    GAMES[game_id] = {
        "chat_id": chat.id,
        "message_id": None,
        "creator": user.id,
        "creator_name": (
            user.first_name
            or "کاربر"
        ),
        "bet": bet,
        "status": "waiting",
        "joiner": None
    }

    try:

        message = await update.message.reply_text(
            "🎮 بازی ۵۰۰ ساخته شد!\n\n"
            f"👤 سازنده: "
            f"{user.first_name}\n"
            f"💰 مبلغ بازی: "
            f"{bet:,} DOGS\n\n"
            "👥 دوستت برای ورود "
            "روی دکمه زیر بزند.\n\n"
            "🏆 برنده: ۹۰٪ کل مبلغ\n"
            "👑 مالک: ۱۰٪ کل مبلغ",
            reply_markup=game_keyboard(
                game_id
            )
        )

        GAMES[game_id][
            "message_id"
        ] = message.message_id

    except Exception:

        # اگر ارسال پیام خطا خورد،
        # پول سازنده برگردد.
        add_balance(
            user.id,
            bet
        )

        GAMES.pop(
            game_id,
            None
        )

        raise


async def game_callback(
    update,
    context
):
    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

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

        try:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True
            )
        except Exception:
            pass

        return

    uid = query.from_user.id

    # =====================================================
    # CANCEL
    # =====================================================

    if action == "game_cancel":

        if uid != game["creator"]:

            try:
                await query.answer(
                    "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        if game.get(
            "status"
        ) != "waiting":

            try:
                await query.answer(
                    "❌ این بازی دیگر قابل لغو نیست.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        # برگشت پول سازنده
        add_balance(
            game["creator"],
            game["bet"]
        )

        game["status"] = "cancelled"

        save_data()

        try:

            await query.message.edit_text(
                "❌ بازی لغو شد.\n\n"
                f"💰 مبلغ "
                f"{game['bet']:,} DOGS "
                "به سازنده برگشت."
            )

        except Exception:
            pass

        return

    # =====================================================
    # JOIN
    # =====================================================

    if action == "game_join":

        if game.get(
            "status"
        ) != "waiting":

            try:
                await query.answer(
                    "❌ این بازی قبلاً شروع شده.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        if uid == game["creator"]:

            try:
                await query.answer(
                    "❌ سازنده نمی‌تواند وارد بازی خودش شود.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        if query.from_user.is_bot:

            try:
                await query.answer(
                    "❌ ربات نمی‌تواند بازی کند.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        create_user(
            query.from_user
        )

        bet = int(
            game["bet"]
        )

        if bet < MIN_GAME or bet > MAX_GAME:

            game["status"] = "cancelled"

            add_balance(
                game["creator"],
                bet
            )

            await query.message.reply_text(
                "❌ مبلغ این بازی نامعتبر بود؛ "
                "بازی لغو و مبلغ سازنده برگشت داده شد."
            )

            return

        # بررسی موجودی نفر دوم
        if get_balance(uid) < bet:

            try:
                await query.answer(
                    "❌ موجودی کافی نیست.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        # رزرو مبلغ نفر دوم
        if not remove_balance(
            uid,
            bet
        ):

            try:
                await query.answer(
                    "❌ کسر مبلغ انجام نشد.",
                    show_alert=True
                )
            except Exception:
                pass

            return

        # =================================================
        # GAME START
        # =================================================

        game["joiner"] = uid

        game["joiner_name"] = (
            query.from_user.first_name
            or "کاربر"
        )

        game["status"] = "playing"

        creator_id = game[
            "creator"
        ]

        joiner_id = game[
            "joiner"
        ]

        creator_name = game[
            "creator_name"
        ]

        joiner_name = game[
            "joiner_name"
        ]

        # =================================================
        # TOTAL POT
        # =================================================

        total_pot = bet * 2

        # =================================================
        # OWNER 10%
        # WINNER 90%
        # =================================================

        owner_share = (
            total_pot * 10
        ) // 100

        winner_share = (
            total_pot
            - owner_share
        )

        # =================================================
        # RANDOM WINNER
        # =================================================

        winner = random.choice([
            creator_id,
            joiner_id
        ])

        if winner == creator_id:

            loser = joiner_id

            winner_name = creator_name

            loser_name = joiner_name

        else:

            loser = creator_id

            winner_name = joiner_name

            loser_name = creator_name

        # =================================================
        # PAY WINNER 90%
        # =================================================

        if not add_balance(
            winner,
            winner_share
        ):

            # اگر پرداخت برنده شکست خورد،
            # وضعیت بازی را نگه می‌داریم
            # تا پول گم نشود.
            game["status"] = "payment_error"

            save_data()

            await query.message.reply_text(
                "⚠️ خطا در پرداخت جایزه.\n"
                "لطفاً مالک بررسی کند."
            )

            return

        # =================================================
        # PAY OWNER 10%
        # =================================================

        owner_id = int(
            data.get(
                "owner",
                OWNER_ID
            )
        )

        owner_paid = add_balance(
            owner_id,
            owner_share
        )

        # اگر مالک حساب ندارد،
        # سهم مالک را گم نمی‌کنیم.
        if not owner_paid:

            game["owner_payment_pending"] = (
                owner_share
            )

        # =================================================
        # SAVE RESULT
        # =================================================

        game["winner"] = winner

        game["loser"] = loser

        game["winner_amount"] = (
            winner_share
        )

        game["owner_amount"] = (
            owner_share
        )

        game["total_pot"] = (
            total_pot
        )

        game["status"] = "finished"

        game["finished_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        # =================================================
        # RESULT MESSAGE
        # =================================================

        result = (
            "🏆 نتیجه بازی ۵۰۰\n\n"
            f"🥇 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n\n"
            f"💰 کل مبلغ بازی: "
            f"{total_pot:,} DOGS\n\n"
            f"🏆 سهم برنده (۹۰٪): "
            f"{winner_share:,} DOGS\n"
            f"👑 سهم مالک (۱۰٪): "
            f"{owner_share:,} DOGS"
        )

        try:

            await query.message.edit_text(
                result
            )

        except Exception:

            try:

                await context.bot.send_message(
                    game["chat_id"],
                    result
                )

            except Exception:
                pass

        # =================================================
        # MESSAGE WINNER
        # =================================================

        try:

            await context.bot.send_message(
                winner,
                "🎉 تبریک!\n\n"
                "🏆 شما برنده بازی ۵۰۰ شدید.\n\n"
                f"💰 دریافتی: "
                f"{winner_share:,} DOGS\n"
                f"💰 موجودی جدید: "
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
                "❌ متأسفانه بازی را باختید.\n\n"
                f"💸 مبلغ بازی: "
                f"{bet:,} DOGS"
            )

        except Exception:
            pass

        # =================================================
        # DELETE GAME FROM MEMORY
        # =================================================

        GAMES.pop(
            game_id,
            None
        )

        return


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context
):
    if (
        not update.message
        or not update.message.text
    ):
        return

    text = update.message.text.strip()

    uid = update.effective_user.id

    # Owner state
    if uid in OWNER_STATE:

        await owner_state_receive(
            update,
            context
        )

        return

    # Transfer state
    if uid in TRANSFER_DATA:

        await transfer_amount(
            update,
            context
        )

        return

    # Deposit state
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

    # Withdraw state
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

    # Main buttons
    if text == "💳 واریزی":

        await deposit_start(
            update,
            context
        )

    elif text == "💰 برداشت":

        await withdraw_start(
            update,
            context
        )

    elif text == "👥 زیرمجموعه":

        await referral_menu(
            update,
            context
        )

    elif text == "🎧 پشتیبانی":

        await support(
            update,
            context
        )

    elif text == "👤 پروفایل":

        await profile(
            update,
            context
        )

    elif text == "👥 انتقال":

        await transfer_start(
            update,
            context
        )

    elif text == "⚙️ پنل مدیریت":

        await owner_panel(
            update,
            context
        )

    elif text == "🎮 بازی ۵۰۰":

        await update.message.reply_text(
            "🎮 بازی ۵۰۰\n\n"
            "بازی فقط داخل گپ انجام می‌شود.\n\n"
            "مثال:\n"
            "/game 500\n\n"
            f"💰 حداقل: "
            f"{MIN_GAME:,} DOGS\n"
            f"💰 حداکثر: "
            f"{MAX_GAME:,} DOGS\n\n"
            "🏆 برنده: ۹۰٪\n"
            "👑 مالک: ۱۰٪"
        )

    elif text == "🔙 برگشت":

        await update.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard(
                uid
            )
        )


# =========================================================
# PHOTO ROUTER
# =========================================================

async def photo_router(
    update,
    context
):
    uid = update.effective_user.id

    if uid in DEPOSIT_DATA:

        await deposit_receipt(
            update,
            context
        )


# =========================================================
# COMMANDS
# =========================================================

async def transfer_command(
    update,
    context
):
    await transfer_start(
        update,
        context
    )


async def game_command(
    update,
    context
):
    await game_create(
        update,
        context
    )


async def admin_command(
    update,
    context
):
    await owner_panel(
        update,
        context
    )


async def transfer_owner_command(
    update,
    context
):
    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ فقط مالک اجازه دارد."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "❌ استفاده:\n"
            "/transferowner ID"
        )

        return

    try:

        new_owner = int(
            context.args[0]
        )

    except Exception:

        await update.message.reply_text(
            "❌ آیدی نامعتبر است."
        )

        return

    if str(new_owner) not in data[
        "users"
    ]:

        await update.message.reply_text(
            "❌ کاربر باید قبلاً "
            "داخل ربات ثبت شده باشد."
        )

        return

    data["owner"] = new_owner

    save_data()

    await update.message.reply_text(
        "✅ انتقال مالکیت انجام شد.\n"
        f"👑 مالک جدید: {new_owner}"
    )


# =========================================================
# JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update,
    context
):
    query = update.callback_query

    if await check_join(
        query.from_user.id,
        context
    ):

        await query.answer()

        create_user(
            query.from_user
        )

        uid = query.from_user.id

        try:
            await query.message.delete()
        except Exception:
            pass

        if not data["users"][
            str(uid)
        ].get("phone"):

            await context.bot.send_message(
                uid,
                "📱 شماره خود را ارسال کنید.\n\n"
                "فقط شماره ایران +98 قبول است.",
                reply_markup=phone_keyboard()
            )

        else:

            await context.bot.send_message(
                uid,
                "✅ عضویت تایید شد.\n\n"
                f"💰 موجودی: "
                f"{get_balance(uid):,} DOGS",
                reply_markup=main_keyboard(uid)
            )

    else:

        await query.answer(
            "❌ هنوز عضو کانال و گپ نیستید.",
            show_alert=True
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):
    print(
        "================ ERROR ================"
    )

    print(
        "ERROR:",
        repr(context.error)
    )

    try:

        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__
        )

    except Exception:
        pass

    print(
        "========================================"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
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
            start
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
            "transferowner",
            transfer_owner_command
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

    # =====================================================
    # CALLBACKS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
        )
    )

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

    application.add_handler(
        CallbackQueryHandler(
            withdraw_decision,
            pattern=r"^with_(ok|no):"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_transfer_decision,
            pattern=r"^owner_(yes|no)"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^game_(join|cancel):"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_panel_callback,
            pattern=r"^adm_"
        )
    )

    # =====================================================
    # CONTACT
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_receive
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
    # ERROR
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
        f"MIN GAME: {MIN_GAME}"
    )

    print(
        f"MAX GAME: {MAX_GAME}"
    )

    print(
        "WINNER: 90%"
    )

    print(
        "OWNER: 10%"
    )

    print(
        "================================"
    )

    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
