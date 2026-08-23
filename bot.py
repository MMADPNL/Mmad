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

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0").strip() or "0")
except ValueError:
    OWNER_ID = 0

REQUIRED_CHANNEL = "@TAK_BE_T"
REQUIRED_GROUP = "@TAK_B_ET"

DATA_FILE = "data.json"

# بازی
MIN_GAME = 500
WIN_PRIZE = 900
OWNER_GAME_FEE = 100

# واریز / برداشت
MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

# رفرال
DEFAULT_REF_REWARD = 50


# =========================================================
# DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "ref_reward": DEFAULT_REF_REWARD,
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_DATA))

        for key, value in DEFAULT_DATA.items():
            if key not in data:
                data[key] = json.loads(json.dumps(value))

        return data

    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


def save_data():
    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temp_file, DATA_FILE)


def get_owner_id():
    try:
        return int(data.get("owner", OWNER_ID))
    except Exception:
        return OWNER_ID


def is_owner(user_id):
    return int(user_id) == get_owner_id()


# =========================================================
# USER
# =========================================================

def create_user(tg_user):
    uid = str(tg_user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": tg_user.id,
            "name": tg_user.first_name or "",
            "username": tg_user.username or "",
            "phone": "",
            "balance": 0,
            "refs": 0,
            "ref_by": None,
        }

    else:
        u = data["users"][uid]

        u["name"] = (
            tg_user.first_name
            or u.get("name", "")
        )

        u["username"] = (
            tg_user.username
            or u.get("username", "")
        )

        u.setdefault("phone", "")
        u.setdefault("balance", 0)
        u.setdefault("refs", 0)
        u.setdefault("ref_by", None)

    save_data()


def get_balance(user_id):
    try:
        return int(
            data["users"][str(user_id)].get(
                "balance",
                0,
            )
        )
    except Exception:
        return 0


def set_balance(user_id, amount):
    uid = str(user_id)

    if uid not in data["users"]:
        return False

    data["users"][uid]["balance"] = max(
        0,
        int(amount),
    )

    save_data()
    return True


def add_balance(user_id, amount):
    return set_balance(
        user_id,
        get_balance(user_id) + int(amount),
    )


def remove_balance(user_id, amount):
    amount = int(amount)

    if amount < 0:
        return False

    if get_balance(user_id) < amount:
        return False

    return set_balance(
        user_id,
        get_balance(user_id) - amount,
    )


# =========================================================
# STATE
# =========================================================

STATE = {}

LAST_ACTION = {}


def anti_spam(user_id, seconds=1.0):
    now = time.time()

    old = LAST_ACTION.get(
        user_id,
        0,
    )

    if now - old < seconds:
        return False

    LAST_ACTION[user_id] = now

    return True


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(user_id):

    rows = [
        ["🎮 بازی", "💰 موجودی"],
        ["💳 واریزی", "💸 برداشت"],
        ["👥 زیرمجموعه", "👤 پروفایل"],
        ["🔄 انتقال", "🎧 پشتیبانی"],
    ]

    if is_owner(user_id):
        rows.append(
            ["⚙️ پنل مدیریت"]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def back_keyboard():

    return ReplyKeyboardMarkup(
        [["🔙 برگشت"]],
        resize_keyboard=True,
    )


def phone_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 ارسال شماره",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def join_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 کانال",
                    url="https://t.me/TAK_BE_T",
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 گپ",
                    url="https://t.me/TAK_B_ET",
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ بررسی عضویت",
                    callback_data="check_join",
                )
            ],
        ]
    )


# =========================================================
# REQUIRED JOIN
# =========================================================

async def check_join(user_id, context):

    for chat in (
        REQUIRED_CHANNEL,
        REQUIRED_GROUP,
    ):

        try:
            member = await context.bot.get_chat_member(
                chat,
                user_id,
            )

            if member.status in (
                "left",
                "kicked",
            ):
                return False

        except Exception as error:
            print(
                "JOIN CHECK ERROR:",
                error,
            )
            return False

    return True


async def require_access(
    update,
    context,
):

    user = update.effective_user
    uid = user.id

    create_user(user)

    if not await check_join(
        uid,
        context,
    ):

        await update.effective_message.reply_text(
            "🔒 ابتدا در کانال و گپ عضو شوید.",
            reply_markup=join_keyboard(),
        )

        return False

    if not data["users"][
        str(uid)
    ].get("phone"):

        await update.effective_message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.\n\n"
            "⚠️ فقط شماره‌های +98 پذیرفته می‌شوند.",
            reply_markup=phone_keyboard(),
        )

        return False

    return True


# =========================================================
# REFERRAL
# =========================================================

async def process_referral(
    update,
    context,
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
        ].get(
            "refs",
            0,
        )
    ) + 1

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    add_balance(
        ref_id,
        reward,
    )

    save_data()

    try:

        await context.bot.send_message(
            ref_id,
            "🎉 زیرمجموعه جدید!\n\n"
            f"🎁 جایزه: {reward:,} DOGS\n"
            f"💰 موجودی: {get_balance(ref_id):,} DOGS",
        )

    except Exception:
        pass


# =========================================================
# START
# =========================================================

async def start(
    update,
    context,
):

    user = update.effective_user

    create_user(user)

    await process_referral(
        update,
        context,
    )

    if not await check_join(
        user.id,
        context,
    ):

        await update.message.reply_text(
            "🔒 برای استفاده از ربات ابتدا "
            "در کانال و گپ عضو شوید.",
            reply_markup=join_keyboard(),
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط +98 قبول می‌شود.",
            reply_markup=phone_keyboard(),
        )

        return

    await update.message.reply_text(
        "👋 خوش آمدید.\n\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(
            user.id
        ),
    )


# =========================================================
# JOIN CALLBACK
# =========================================================

async def check_join_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    create_user(user)

    if not await check_join(
        user.id,
        context,
    ):

        await query.answer(
            "❌ هنوز عضو کانال و گپ نشده‌اید.",
            show_alert=True,
        )

        return

    if not data["users"][
        str(user.id)
    ].get("phone"):

        await query.message.reply_text(
            "✅ عضویت تأیید شد.\n\n"
            "📱 حالا شماره خود را ارسال کنید.",
            reply_markup=phone_keyboard(),
        )

        return

    await query.message.reply_text(
        "✅ آماده استفاده هستید.",
        reply_markup=main_keyboard(
            user.id
        ),
    )


# =========================================================
# PHONE
# =========================================================

def normalize_phone(phone):

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

    if not phone.startswith("+98"):
        return None

    return phone


async def phone_receive(
    update,
    context,
):

    user = update.effective_user
    contact = update.message.contact

    if not contact:
        return

    if contact.user_id != user.id:

        await update.message.reply_text(
            "❌ فقط شماره خود حساب را ارسال کنید.",
            reply_markup=phone_keyboard(),
        )

        return

    phone = normalize_phone(
        contact.phone_number
    )

    if not phone:

        await update.message.reply_text(
            "❌ فقط شماره‌های +98 پذیرفته می‌شوند.",
            reply_markup=phone_keyboard(),
        )

        return

    create_user(user)

    data["users"][
        str(user.id)
    ]["phone"] = phone

    save_data()

    await update.message.reply_text(
        "✅ شماره با موفقیت تأیید شد.",
        reply_markup=main_keyboard(
            user.id
        ),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance_message(
    update,
    context,
):

    user = update.effective_user

    create_user(user)

    await update.message.reply_text(
        f"💰 موجودی شما:\n\n"
        f"{get_balance(user.id):,} DOGS"
    )


async def balance_command(
    update,
    context,
):

    await balance_message(
        update,
        context,
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(
    update,
    context,
):

    user = update.effective_user

    create_user(user)

    info = data["users"][
        str(user.id)
    ]

    refs = int(
        info.get(
            "refs",
            0,
        )
    )

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    await update.message.reply_text(
        "👤 پروفایل شما\n\n"
        f"🆔 آیدی: {user.id}\n"
        f"👤 نام: {info.get('name', '')}\n"
        f"📱 شماره: "
        f"{info.get('phone') or 'ثبت نشده'}\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه: {refs}\n"
        f"🎁 جایزه هر رفرال: "
        f"{reward:,} DOGS",
        reply_markup=main_keyboard(
            user.id
        ),
    )


# =========================================================
# REFERRAL MENU
# =========================================================

async def referral_menu(
    update,
    context,
):

    user = update.effective_user

    create_user(user)

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/"
        f"{bot.username}"
        f"?start={user.id}"
    )

    refs = int(
        data["users"][
            str(user.id)
        ].get(
            "refs",
            0,
        )
    )

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    await update.message.reply_text(
        "👥 سیستم زیرمجموعه\n\n"
        f"🔗 لینک اختصاصی شما:\n"
        f"{link}\n\n"
        f"👥 تعداد زیرمجموعه: {refs}\n"
        f"🎁 جایزه هر رفرال: "
        f"{reward:,} DOGS\n\n"
        "با دعوت هر کاربر جدید، "
        "جایزه به موجودی شما اضافه می‌شود.",
        reply_markup=main_keyboard(
            user.id
        ),
        )

# =========================================================
# GAME
# =========================================================

async def game_start(update, context):
    uid = update.effective_user.id

    STATE[uid] = {
        "step": "game_amount"
    }

    await update.message.reply_text(
        "🎮 بازی\n\n"
        "💰 حداقل بازی: 500 DOGS\n"
        "♾️ حداکثر بازی: ندارد\n\n"
        "مبلغ بازی را وارد کنید.\n\n"
        "مثال:\n"
        "500",
        reply_markup=back_keyboard(),
    )


async def game_amount(update, context):
    uid = update.effective_user.id

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount < MIN_GAME:
        await update.message.reply_text(
            "❌ حداقل مبلغ بازی 500 DOGS است."
        )
        return

    if not remove_balance(
        uid,
        amount,
    ):
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # -----------------------------------------------------
    # نتیجه بازی
    # -----------------------------------------------------

    win = random.choice(
        [True, False]
    )

    if win:

        # نمونه:
        # بازی 500
        # برنده 900
        # 100 سهم مالک

        prize = int(
            amount * 1.8
        )

        owner_fee = int(
            amount * 0.2
        )

        add_balance(
            uid,
            prize,
        )

        if (
            owner_id() != uid
            and owner_fee > 0
        ):
            add_balance(
                owner_id(),
                owner_fee,
            )

        result = (
            "🎉 برنده شدید!\n\n"
            f"🎮 مبلغ بازی: "
            f"{amount:,} DOGS\n"
            f"🏆 جایزه: "
            f"{prize:,} DOGS\n"
            f"👑 سهم مالک: "
            f"{owner_fee:,} DOGS\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS"
        )

    else:

        owner_fee = amount

        if owner_id() != uid:
            add_balance(
                owner_id(),
                owner_fee,
            )

        result = (
            "❌ باختید.\n\n"
            f"🎮 مبلغ بازی: "
            f"{amount:,} DOGS\n"
            f"👑 سهم مالک: "
            f"{owner_fee:,} DOGS\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS"
        )

    game_id = f"G{time.time_ns()}"

    data["games"][game_id] = {
        "user_id": uid,
        "amount": amount,
        "win": win,
        "created_at": int(time.time()),
    }

    save_data()

    STATE.pop(
        uid,
        None,
    )

    await update.message.reply_text(
        result,
        reply_markup=main_keyboard(uid),
    )


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(
    update,
    context,
):

    uid = update.effective_user.id

    STATE[uid] = {
        "step": "deposit_amount"
    }

    await update.message.reply_text(
        "💳 واریزی\n\n"
        "💰 حداقل واریز: 5,000 DOGS\n"
        "♾️ حداکثر: ندارد\n\n"
        "مبلغ واریزی را وارد کنید.",
        reply_markup=back_keyboard(),
    )


async def deposit_amount(
    update,
    context,
):

    uid = update.effective_user.id

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            "❌ حداقل واریز 5,000 DOGS است."
        )
        return

    deposit_id = (
        f"D{time.time_ns()}"
    )

    data["deposits"][deposit_id] = {
        "user_id": uid,
        "amount": amount,
        "status": "waiting_receipt",
        "created_at": int(time.time()),
    }

    save_data()

    STATE[uid] = {
        "step": "deposit_receipt",
        "id": deposit_id,
    }

    await update.message.reply_text(
        f"💳 مبلغ واریزی:\n"
        f"{amount:,} DOGS\n\n"
        "📥 آدرس واریز را از پیام واریزی ربات استفاده کنید.\n\n"
        "📸 بعد از پرداخت، رسید را ارسال کنید."
    )


async def deposit_receipt(
    update,
    context,
):

    uid = update.effective_user.id

    state = STATE.get(
        uid,
        {},
    )

    deposit_id = state.get(
        "id"
    )

    deposit = data["deposits"].get(
        deposit_id
    )

    if not deposit:

        STATE.pop(
            uid,
            None,
        )

        await update.message.reply_text(
            "❌ درخواست واریز پیدا نشد."
        )

        return

    deposit["status"] = "pending"

    save_data()

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=(
                        f"dep_ok:{deposit_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=(
                        f"dep_no:{deposit_id}"
                    ),
                ),
            ]
        ]
    )

    caption = (
        "💳 واریز جدید\n\n"
        f"👤 کاربر: {uid}\n"
        f"💰 مبلغ: "
        f"{deposit['amount']:,} DOGS\n"
        f"🆔 درخواست: {deposit_id}"
    )

    try:

        if update.message.photo:

            await context.bot.send_photo(
                get_owner_id(),
                update.message.photo[-1].file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        elif update.message.document:

            await context.bot.send_document(
                get_owner_id(),
                update.message.document.file_id,
                caption=caption,
                reply_markup=keyboard,
            )

        else:

            await context.bot.send_message(
                get_owner_id(),
                caption
                + "\n\n"
                + (
                    update.message.text
                    or ""
                ),
                reply_markup=keyboard,
            )

    except Exception as error:

        print(
            "DEPOSIT SEND ERROR:",
            error,
        )

        await update.message.reply_text(
            "❌ ارسال رسید برای مالک انجام نشد."
        )

        return

    STATE.pop(
        uid,
        None,
    )

    await update.message.reply_text(
        "✅ رسید شما برای مالک ارسال شد.\n\n"
        "⏳ منتظر بررسی باشید.",
        reply_markup=main_keyboard(uid),
    )


async def deposit_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True,
        )

        return

    action, deposit_id = (
        query.data.split(
            ":",
            1,
        )
    )

    deposit = data["deposits"].get(
        deposit_id
    )

    if (
        not deposit
        or deposit.get("status")
        != "pending"
    ):

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده است."
        )

        return

    uid = int(
        deposit["user_id"]
    )

    amount = int(
        deposit["amount"]
    )

    if action == "dep_ok":

        deposit["status"] = (
            "approved"
        )

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            f"✅ واریز {amount:,} DOGS تأیید شد."
        )

        user_text = (
            "✅ واریز شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی: "
            f"{get_balance(uid):,} DOGS"
        )

    else:

        deposit["status"] = (
            "rejected"
        )

        admin_text = (
            "❌ واریز رد شد."
        )

        user_text = (
            "❌ واریز شما رد شد."
        )

    save_data()

    await query.message.reply_text(
        admin_text
    )

    try:

        await context.bot.send_message(
            uid,
            user_text,
        )

    except Exception:
        pass

    try:

        await query.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(
    update,
    context,
):

    uid = update.effective_user.id

    STATE[uid] = {
        "step": "withdraw_amount"
    }

    await update.message.reply_text(
        "💸 برداشت\n\n"
        "💰 حداقل برداشت: 10,000 DOGS\n"
        "♾️ حداکثر برداشت: ندارد\n\n"
        "مبلغ برداشت را وارد کنید.",
        reply_markup=back_keyboard(),
    )


async def withdraw_amount(
    update,
    context,
):

    uid = update.effective_user.id

    try:

        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )

        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            "❌ حداقل برداشت 10,000 DOGS است."
        )

        return

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    STATE[uid] = {
        "step": "withdraw_target",
        "amount": amount,
    }

    await update.message.reply_text(
        f"💰 مبلغ برداشت: "
        f"{amount:,} DOGS\n\n"
        "🆔 حالا آیدی عددی دریافت‌کننده را وارد کنید.\n\n"
        "مثال:\n"
        "123456789"
    )


async def withdraw_target(
    update,
    context,
):

    uid = update.effective_user.id

    try:

        target_id = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی باید عددی باشد."
        )

        return

    amount = int(
        STATE.get(
            uid,
            {},
        ).get(
            "amount",
            0,
        )
    )

    if amount < MIN_WITHDRAW:

        STATE.pop(
            uid,
            None,
        )

        return

    if not remove_balance(
        uid,
        amount,
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        STATE.pop(
            uid,
            None,
        )

        return

    withdraw_id = (
        f"W{time.time_ns()}"
    )

    data["withdraws"][
        withdraw_id
    ] = {
        "user_id": uid,
        "target_id": target_id,
        "amount": amount,
        "status": "pending",
        "created_at": int(time.time()),
    }

    save_data()

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید برداشت",
                    callback_data=(
                        f"with_ok:{withdraw_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "❌ رد برداشت",
                    callback_data=(
                        f"with_no:{withdraw_id}"
                    ),
                ),
            ]
        ]
    )

    try:

        await context.bot.send_message(
            get_owner_id(),
            "💸 درخواست برداشت جدید\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"🆔 دریافت‌کننده: {target_id}\n"
            f"📋 درخواست: {withdraw_id}",
            reply_markup=keyboard,
        )

    except Exception as error:

        print(
            "WITHDRAW SEND ERROR:",
            error,
        )

        add_balance(
            uid,
            amount,
        )

        data["withdraws"].pop(
            withdraw_id,
            None,
        )

        save_data()

        STATE.pop(
            uid,
            None,
        )

        await update.message.reply_text(
            "❌ ارسال درخواست برای مالک انجام نشد.\n"
            "💰 مبلغ به موجودی شما برگشت."
        )

        return

    STATE.pop(
        uid,
        None,
    )

    # عمداً پیام «برداشت شد» در گپ ارسال نمی‌شود.
    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        "⏳ منتظر تأیید مالک باشید.",
        reply_markup=main_keyboard(uid),
    )


async def withdraw_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True,
        )

        return

    action, withdraw_id = (
        query.data.split(
            ":",
            1,
        )
    )

    request = data["withdraws"].get(
        withdraw_id
    )

    if (
        not request
        or request.get("status")
        != "pending"
    ):

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده است."
        )

        return

    uid = int(
        request["user_id"]
    )

    amount = int(
        request["amount"]
    )

    target_id = int(
        request["target_id"]
    )

    if action == "with_ok":

        request["status"] = (
            "approved"
        )

        admin_text = (
            "✅ برداشت تأیید شد."
        )

        user_text = (
            "✅ برداشت شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"🆔 دریافت‌کننده: {target_id}"
        )

    else:

        request["status"] = (
            "rejected"
        )

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            "❌ برداشت رد شد و مبلغ برگشت خورد."
        )

        user_text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ {amount:,} DOGS "
            "به موجودی شما برگشت."
        )

    save_data()

    await query.message.reply_text(
        admin_text
    )

    try:

        await context.bot.send_message(
            uid,
            user_text,
        )

    except Exception:
        pass

    try:

        await query.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass

# =========================================================
# TRANSFER
# =========================================================

async def transfer_start(update, context):
    uid = update.effective_user.id

    await update.message.reply_text(
        "🔄 انتقال موجودی\n\n"
        "روی پیام کاربر ریپلای کنید و سپس بنویسید:\n\n"
        "انتقال 500\n\n"
        "مثال:\n"
        "انتقال 500"
    )


async def transfer_text(update, context):
    message = update.message
    uid = update.effective_user.id

    if not message.reply_to_message:
        await message.reply_text(
            "❌ برای انتقال باید روی پیام کاربر ریپلای کنید.\n\n"
            "مثال:\n"
            "انتقال 500"
        )
        return

    parts = message.text.strip().split()

    if len(parts) != 2:
        await message.reply_text(
            "❌ فرمت صحیح:\n"
            "انتقال 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except ValueError:
        await message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ مبلغ انتقال باید بیشتر از صفر باشد."
        )
        return

    receiver = (
        message.reply_to_message.from_user
    )

    if receiver.id == uid:
        await message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    create_user(receiver)

    if not remove_balance(
        uid,
        amount,
    ):
        await message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    add_balance(
        receiver.id,
        amount,
    )

    await message.reply_text(
        "✅ انتقال با موفقیت انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {receiver.first_name}\n\n"
        f"💳 موجودی شما: "
        f"{get_balance(uid):,} DOGS"
    )

    try:
        await context.bot.send_message(
            receiver.id,
            "💰 یک انتقال دریافت کردید.\n\n"
            f"➕ مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی شما: "
            f"{get_balance(receiver.id):,} DOGS",
        )
    except Exception:
        pass


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 شارژ موجودی",
                    callback_data="adm_add",
                ),
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="adm_remove",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎁 جایزه رفرال",
                    callback_data="adm_reward",
                ),
                InlineKeyboardButton(
                    "👥 کاربران",
                    callback_data="adm_users",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="adm_owner",
                ),
            ],
        ]
    )


async def admin_panel(
    update,
    context,
):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ فقط مالک ربات به این بخش دسترسی دارد."
        )

        return

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"👑 مالک فعلی: {get_owner_id()}\n"
        f"👥 تعداد کاربران: "
        f"{len(data['users']):,}\n"
        f"🎁 جایزه هر رفرال: "
        f"{reward:,} DOGS\n\n"
        "از دکمه‌های زیر استفاده کنید.",
        reply_markup=admin_keyboard(),
    )


async def admin_callback(
    update,
    context,
):

    query = update.callback_query

    await query.answer()

    uid = query.from_user.id

    if not is_owner(uid):

        await query.answer(
            "❌ فقط مالک دسترسی دارد.",
            show_alert=True,
        )

        return

    action = query.data

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    if action == "adm_users":

        await query.message.reply_text(
            "👥 اطلاعات کاربران\n\n"
            f"تعداد کاربران ثبت‌شده: "
            f"{len(data['users']):,}"
        )

        return

    # -----------------------------------------------------
    # ADD BALANCE
    # -----------------------------------------------------

    if action == "adm_add":

        STATE[uid] = {
            "step": "admin_add"
        }

        await query.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return

    # -----------------------------------------------------
    # REMOVE BALANCE
    # -----------------------------------------------------

    if action == "adm_remove":

        STATE[uid] = {
            "step": "admin_remove"
        }

        await query.message.reply_text(
            "➖ کسر موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return

    # -----------------------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------------------

    if action == "adm_reward":

        STATE[uid] = {
            "step": "admin_reward"
        }

        current_reward = int(
            data.get(
                "ref_reward",
                DEFAULT_REF_REWARD,
            )
        )

        await query.message.reply_text(
            "🎁 تنظیم جایزه رفرال\n\n"
            f"جایزه فعلی: "
            f"{current_reward:,} DOGS\n\n"
            "مبلغ جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "50"
        )

        return

    # -----------------------------------------------------
    # TRANSFER OWNERSHIP
    # -----------------------------------------------------

    if action == "adm_owner":

        STATE[uid] = {
            "step": "admin_owner"
        }

        await query.message.reply_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "123456789"
        )

        return


# =========================================================
# ADMIN STATE
# =========================================================

async def admin_state(
    update,
    context,
):

    uid = update.effective_user.id

    state = STATE.get(
        uid,
        {},
    )

    step = state.get(
        "step"
    )

    if step not in (
        "admin_add",
        "admin_remove",
        "admin_reward",
        "admin_owner",
    ):
        return False

    if not is_owner(uid):
        return True

    text = (
        update.message.text
        .strip()
    )

    # -----------------------------------------------------
    # REFERRAL REWARD
    # -----------------------------------------------------

    if step == "admin_reward":

        try:
            reward = int(
                text.replace(",", "")
            )
        except ValueError:

            await update.message.reply_text(
                "❌ مبلغ نامعتبر است."
            )

            return True

        if reward < 0:

            await update.message.reply_text(
                "❌ جایزه نمی‌تواند منفی باشد."
            )

            return True

        data["ref_reward"] = reward

        save_data()

        STATE.pop(
            uid,
            None,
        )

        await update.message.reply_text(
            "✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 جایزه جدید هر رفرال: "
            f"{reward:,} DOGS",
            reply_markup=main_keyboard(uid),
        )

        return True

    # -----------------------------------------------------
    # CHANGE OWNER
    # -----------------------------------------------------

    if step == "admin_owner":

        try:
            new_owner = int(
                text
            )
        except ValueError:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return True

        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )

            return True

        if str(new_owner) not in data["users"]:

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را استارت نکرده است."
            )

            return True

        old_owner = get_owner_id()

        data["owner"] = new_owner

        save_data()

        STATE.pop(
            uid,
            None,
        )

        await update.message.reply_text(
            "✅ انتقال مالکیت انجام شد.\n\n"
            f"👑 مالک قبلی: {old_owner}\n"
            f"👑 مالک جدید: {new_owner}",
            reply_markup=main_keyboard(uid),
        )

        try:

            await context.bot.send_message(
                new_owner,
                "👑 شما مالک جدید ربات شدید.\n\n"
                "⚙️ پنل مدیریت برای شما فعال شد.",
            )

        except Exception:
            pass

        return True

    # -----------------------------------------------------
    # ADD / REMOVE BALANCE
    # -----------------------------------------------------

    parts = text.split()

    if len(parts) != 2:

        await update.message.reply_text(
            "❌ فرمت صحیح:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return True

    try:

        target_id = int(
            parts[0]
        )

        amount = int(
            parts[1].replace(",", "")
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی و مبلغ باید عدد باشند."
        )

        return True

    if target_id <= 0 or amount <= 0:

        await update.message.reply_text(
            "❌ اطلاعات واردشده نامعتبر است."
        )

        return True

    if str(target_id) not in data["users"]:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )

        return True

    # -----------------------------------------------------
    # ADD
    # -----------------------------------------------------

    if step == "admin_add":

        add_balance(
            target_id,
            amount,
        )

        text_result = (
            "✅ موجودی شارژ شد.\n\n"
            f"👤 کاربر: {target_id}\n"
            f"➕ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} DOGS"
        )

    # -----------------------------------------------------
    # REMOVE
    # -----------------------------------------------------

    else:

        if not remove_balance(
            target_id,
            amount,
        ):

            await update.message.reply_text(
                "❌ موجودی کاربر برای کسر این مبلغ کافی نیست."
            )

            return True

        text_result = (
            "✅ موجودی کسر شد.\n\n"
            f"👤 کاربر: {target_id}\n"
            f"➖ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} DOGS"
        )

    STATE.pop(
        uid,
        None,
    )

    await update.message.reply_text(
        text_result,
        reply_markup=main_keyboard(uid),
    )

    return True


# =========================================================
# SUPPORT
# =========================================================

async def support(
    update,
    context,
):

    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "پیام خود را ارسال کنید."
    )


# =========================================================
# BACK BUTTON
# =========================================================

async def go_back(
    update,
    context,
):

    uid = update.effective_user.id

    STATE.pop(
        uid,
        None,
    )

    await update.message.reply_text(
        "🏠 به منوی اصلی برگشتید.",
        reply_markup=main_keyboard(uid),
    )


# =========================================================
# MEDIA ROUTER
# =========================================================

async def media_router(
    update,
    context,
):

    uid = update.effective_user.id

    step = STATE.get(
        uid,
        {},
    ).get(
        "step"
    )

    if step == "deposit_receipt":

        if not await require_access(
            update,
            context,
        ):
            return

        await deposit_receipt(
            update,
            context,
        )

        return


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context,
):

    if (
        not update.message
        or not update.message.text
    ):
        return

    user = update.effective_user
    uid = user.id
    text = update.message.text.strip()

    create_user(user)

    # -----------------------------------------------------
    # موجودی در گپ و پیوی
    # -----------------------------------------------------

    if text.lower() in (
        "موجودی",
        "/balance",
        "balance",
    ):

        await balance_message(
            update,
            context,
        )

        return

    # -----------------------------------------------------
    # انتقال با ریپلای
    # -----------------------------------------------------

    if text.startswith(
        "انتقال "
    ):

        if not await require_access(
            update,
            context,
        ):
            return

        await transfer_text(
            update,
            context,
        )

        return

    # -----------------------------------------------------
    # دستورات مدیریتی در حال انجام
    # -----------------------------------------------------

    if await admin_state(
        update,
        context,
    ):
        return

    # -----------------------------------------------------
    # دستورات مرحله‌ای
    # -----------------------------------------------------

    state = STATE.get(
        uid,
        {}
    )

    step = state.get(
        "step"
    )

    if step == "game_amount":

        if not await require_access(
            update,
            context,
        ):
            return

        await game_amount(
            update,
            context,
        )

        return

    if step == "deposit_amount":

        if not await require_access(
            update,
            context,
        ):
            return

        await deposit_amount(
            update,
            context,
        )

        return

    if step == "withdraw_amount":

        if not await require_access(
            update,
            context,
        ):
            return

        await withdraw_amount(
            update,
            context,
        )

        return

    if step == "withdraw_target":

        if not await require_access(
            update,
            context,
        ):
            return

        await withdraw_target(
            update,
            context,
        )

        return

    if step == "deposit_receipt":

        await update.message.reply_text(
            "📸 لطفاً رسید را به صورت عکس یا فایل ارسال کنید."
        )

        return

    # -----------------------------------------------------
    # برگشت
    # -----------------------------------------------------

    if text == "🔙 برگشت":

        await go_back(
            update,
            context,
        )

        return

    # -----------------------------------------------------
    # MAIN BUTTONS
    # -----------------------------------------------------

    if text == "🎮 بازی":

        if not await require_access(
            update,
            context,
        ):
            return

        await game_start(
            update,
            context,
        )

        return

    if text == "💰 موجودی":

        await balance_message(
            update,
            context,
        )

        return

    if text == "💳 واریزی":

        if not await require_access(
            update,
            context,
        ):
            return

        await deposit_start(
            update,
            context,
        )

        return

    if text == "💸 برداشت":

        if not await require_access(
            update,
            context,
        ):
            return

        await withdraw_start(
            update,
            context,
        )

        return

    if text == "👥 زیرمجموعه":

        if not await require_access(
            update,
            context,
        ):
            return

        await referral_menu(
            update,
            context,
        )

        return

    if text == "👤 پروفایل":

        if not await require_access(
            update,
            context,
        ):
            return

        await profile(
            update,
            context,
        )

        return

    if text == "🔄 انتقال":

        if not await require_access(
            update,
            context,
        ):
            return

        await transfer_start(
            update,
            context,
        )

        return

    if text == "🎧 پشتیبانی":

        if not await require_access(
            update,
            context,
        ):
            return

        await support(
            update,
            context,
        )

        return

    if text == "⚙️ پنل مدیریت":

        if not is_owner(uid):

            await update.message.reply_text(
                "❌ فقط مالک دسترسی دارد."
            )

            return

        await admin_panel(
            update,
            context,
        )

        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context,
):

    print(
        "BOT ERROR:",
        context.error,
    )

    try:

        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )

    except Exception:
        pass

# =========================================================
# MAIN
# =========================================================

def owner_id():
    return get_owner_id()


async def command_start(update, context):
    try:
        await start(update, context)
    except Exception as e:
        print("START ERROR:", e)


async def command_balance(update, context):
    try:
        await balance_command(update, context)
    except Exception as e:
        print("BALANCE ERROR:", e)


async def command_referral(update, context):
    try:
        user = update.effective_user
        create_user(user)

        await referral_menu(
            update,
            context,
        )
    except Exception as e:
        print("REFERRAL ERROR:", e)


async def command_profile(update, context):
    try:
        await profile(
            update,
            context,
        )
    except Exception as e:
        print("PROFILE ERROR:", e)


async def command_admin(update, context):
    try:
        await admin_panel(
            update,
            context,
        )
    except Exception as e:
        print("ADMIN ERROR:", e)


# =========================================================
# CONTACT HANDLER
# =========================================================

async def contact_handler(
    update,
    context,
):

    try:

        await phone_receive(
            update,
            context,
        )

    except Exception as error:

        print(
            "CONTACT ERROR:",
            error,
        )

        try:

            await update.message.reply_text(
                "❌ هنگام تأیید شماره خطایی رخ داد."
            )

        except Exception:
            pass


# =========================================================
# PHOTO / DOCUMENT HANDLER
# =========================================================

async def photo_handler(
    update,
    context,
):

    try:

        await media_router(
            update,
            context,
        )

    except Exception as error:

        print(
            "PHOTO ERROR:",
            error,
        )


async def document_handler(
    update,
    context,
):

    try:

        await media_router(
            update,
            context,
        )

    except Exception as error:

        print(
            "DOCUMENT ERROR:",
            error,
        )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(
    update,
    context,
):

    query = update.callback_query

    if not query:
        return

    try:

        data_value = query.data or ""

        if data_value == "check_join":

            await check_join_callback(
                update,
                context,
            )

            return

        if data_value.startswith(
            "dep_ok:"
        ) or data_value.startswith(
            "dep_no:"
        ):

            await deposit_callback(
                update,
                context,
            )

            return

        if data_value.startswith(
            "with_ok:"
        ) or data_value.startswith(
            "with_no:"
        ):

            await withdraw_callback(
                update,
                context,
            )

            return

        if data_value.startswith(
            "adm_"
        ):

            await admin_callback(
                update,
                context,
            )

            return

        await query.answer()

    except Exception as error:

        print(
            "CALLBACK ERROR:",
            error,
        )

        try:

            await query.answer(
                "❌ خطایی رخ داد.",
                show_alert=True,
            )

        except Exception:
            pass


# =========================================================
# GLOBAL ERROR PROTECTION
# =========================================================

async def safe_error_handler(
    update,
    context,
):

    error = context.error

    print(
        "\n=============================="
    )

    print(
        "BOT ERROR:",
        repr(error),
    )

    print(
        "==============================\n"
    )

    try:

        if update and update.effective_message:

            await update.effective_message.reply_text(
                "❌ خطایی رخ داد.\n"
                "لطفاً دوباره تلاش کنید."
            )

    except Exception:

        pass


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            command_start,
        )
    )

    application.add_handler(
        CommandHandler(
            "balance",
            command_balance,
        )
    )

    application.add_handler(
        CommandHandler(
            "ref",
            command_referral,
        )
    )

    application.add_handler(
        CommandHandler(
            "profile",
            command_profile,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            command_admin,
        )
    )

    # -----------------------------------------------------
    # CALLBACK
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # -----------------------------------------------------
    # CONTACT
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # -----------------------------------------------------
    # PHOTO
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler,
        )
    )

    # -----------------------------------------------------
    # DOCUMENT
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler,
        )
    )

    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router,
        )
    )

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    application.add_error_handler(
        safe_error_handler
    )

    print(
        "================================="
    )

    print(
        "BOT STARTED"
    )

    print(
        "================================="
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
