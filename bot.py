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
    OWNER_ID = int(
        os.getenv("OWNER_ID", "0").strip() or "0"
    )
except Exception:
    OWNER_ID = 0

REQUIRED_CHANNEL = "@TAK_BE_T"
REQUIRED_GROUP = "@TAK_B_ET"

DATA_FILE = "data.json"

# فقط یک ارز
CURRENCY = "DOGS"

# واریزی
DEPOSIT_NETWORK = "ULTRA"
DEPOSIT_USERNAME = "@CyyFr"
MIN_DEPOSIT = 5000

# برداشت
MIN_WITHDRAW = 10000

# بازی
MIN_GAME = 500
WIN_PRIZE_RATE = 1.8
OWNER_GAME_FEE_RATE = 0.2

# رفرال
DEFAULT_REF_REWARD = 50


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "ref_reward": DEFAULT_REF_REWARD,
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}


# =========================================================
# DATA
# =========================================================

def fresh_default_data():
    return json.loads(
        json.dumps(DEFAULT_DATA)
    )


def load_data():
    if not os.path.exists(DATA_FILE):
        return fresh_default_data()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            return fresh_default_data()

        defaults = fresh_default_data()

        for key, value in defaults.items():
            if key not in loaded:
                loaded[key] = value

        if not isinstance(
            loaded.get("users"),
            dict,
        ):
            loaded["users"] = {}

        if not isinstance(
            loaded.get("deposits"),
            dict,
        ):
            loaded["deposits"] = {}

        if not isinstance(
            loaded.get("withdraws"),
            dict,
        ):
            loaded["withdraws"] = {}

        if not isinstance(
            loaded.get("games"),
            dict,
        ):
            loaded["games"] = {}

        return loaded

    except Exception as error:
        print(
            "LOAD DATA ERROR:",
            repr(error),
        )
        return fresh_default_data()


data = load_data()


def save_data():
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            temp_file,
            DATA_FILE,
        )

    except Exception as error:
        print(
            "SAVE DATA ERROR:",
            repr(error),
        )


# =========================================================
# OWNER
# =========================================================

def get_owner_id():
    try:
        return int(
            data.get(
                "owner",
                OWNER_ID,
            )
        )
    except Exception:
        return OWNER_ID


def is_owner(user_id):
    try:
        return int(user_id) == get_owner_id()
    except Exception:
        return False


# =========================================================
# USERS
# =========================================================

def create_user(tg_user):
    if not tg_user:
        return

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
        user = data["users"][uid]

        user["id"] = tg_user.id

        if tg_user.first_name:
            user["name"] = tg_user.first_name

        if tg_user.username:
            user["username"] = tg_user.username

        user.setdefault(
            "phone",
            "",
        )

        user.setdefault(
            "balance",
            0,
        )

        user.setdefault(
            "refs",
            0,
        )

        user.setdefault(
            "ref_by",
            None,
        )

    save_data()


def get_user(user_id):
    return data["users"].get(
        str(user_id)
    )


def get_balance(user_id):
    try:
        user = get_user(user_id)

        if not user:
            return 0

        return int(
            user.get(
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

    if amount < 0:
        return False

    return set_balance(
        user_id,
        get_balance(user_id) + amount,
    )


def remove_balance(user_id, amount):
    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        return False

    current = get_balance(user_id)

    if current < amount:
        return False

    return set_balance(
        user_id,
        current - amount,
    )


# =========================================================
# STATE / ANTI SPAM
# =========================================================

STATE = {}
LAST_ACTION = {}


def clear_state(user_id):
    STATE.pop(
        user_id,
        None,
    )


def anti_spam(
    user_id,
    seconds=0.7,
):
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

async def check_join(
    user_id,
    context,
):
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
                repr(error),
            )
            return False

    return True


async def require_access(
    update,
    context,
):
    user = update.effective_user

    if not user:
        return False

    create_user(user)

    if not await check_join(
        user.id,
        context,
    ):
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔒 ابتدا در کانال و گپ عضو شوید.",
                reply_markup=join_keyboard(),
            )

        return False

    user_data = data["users"].get(
        str(user.id),
        {},
    )

    if not user_data.get("phone"):
        if update.effective_message:
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

    if not user:
        return

    if ref_id == user.id:
        return

    uid = str(user.id)

    if uid not in data["users"]:
        create_user(user)

    if data["users"][uid].get("ref_by"):
        return

    if str(ref_id) not in data["users"]:
        return

    data["users"][uid]["ref_by"] = ref_id

    data["users"][str(ref_id)]["refs"] = (
        int(
            data["users"][str(ref_id)].get(
                "refs",
                0,
            )
        ) + 1
    )

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
            f"🎁 جایزه: {reward:,} {CURRENCY}\n"
            f"💰 موجودی: "
            f"{get_balance(ref_id):,} {CURRENCY}",
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

    if not user:
        return

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
            "⚠️ فقط شماره‌های +98 قبول می‌شود.",
            reply_markup=phone_keyboard(),
        )
        return

    await update.message.reply_text(
        "👋 خوش آمدید.\n\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} {CURRENCY}",
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

    if not query:
        return

    user = query.from_user

    try:
        await query.answer()
    except Exception:
        pass

    create_user(user)

    if not await check_join(
        user.id,
        context,
    ):
        try:
            await query.answer(
                "❌ هنوز عضو کانال و گپ نشده‌اید.",
                show_alert=True,
            )
        except Exception:
            pass

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

    phone = str(phone).strip()

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

    if not phone.startswith("+98"):
        return None

    digits = phone[1:]

    if not digits.isdigit():
        return None

    if not digits.startswith("98"):
        return None

    return "+" + digits


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

    if not await check_join(
        user.id,
        context,
    ):
        await update.message.reply_text(
            "❌ ابتدا در کانال و گپ عضو شوید.",
            reply_markup=join_keyboard(),
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
# فقط یک تابع برای نمایش موجودی
# =========================================================

async def balance_message(
    update,
    context,
):
    user = update.effective_user

    if not user:
        return

    create_user(user)

    await update.message.reply_text(
        "💰 موجودی شما:\n\n"
        f"{get_balance(user.id):,} {CURRENCY}"
    )


async def command_balance(
    update,
    context,
):
    try:
        await balance_message(
            update,
            context,
        )
    except Exception as error:
        print(
            "BALANCE ERROR:",
            repr(error),
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

    username = info.get(
        "username",
        "",
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

    await update.message.reply_text(
        "👤 پروفایل شما\n\n"
        f"🆔 شناسه: {user.id}\n"
        f"👤 نام: {info.get('name', '')}\n"
        f"🔹 یوزرنیم: {username_text}\n"
        f"📱 شماره: "
        f"{info.get('phone') or 'ثبت نشده'}\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} {CURRENCY}\n"
        f"👥 زیرمجموعه: {refs}\n"
        f"🎁 جایزه هر رفرال: "
        f"{reward:,} {CURRENCY}",
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
        f"{reward:,} {CURRENCY}\n\n"
        "با دعوت هر کاربر جدید، "
        "جایزه به موجودی شما اضافه می‌شود.",
        reply_markup=main_keyboard(
            user.id
        ),
    )


# =========================================================
# GAME
# =========================================================

async def game_start(
    update,
    context,
):
    uid = update.effective_user.id

    STATE[uid] = {
        "step": "game_amount"
    }

    await update.message.reply_text(
        "🎮 بازی\n\n"
        f"💰 حداقل بازی: "
        f"{MIN_GAME:,} {CURRENCY}\n"
        "♾️ حداکثر بازی: ندارد\n\n"
        "مبلغ بازی را وارد کنید.\n\n"
        "مثال:\n"
        "500",
        reply_markup=back_keyboard(),
    )


async def game_amount(
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

    if amount < MIN_GAME:
        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی "
            f"{MIN_GAME:,} {CURRENCY} است."
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

    win = random.choice(
        [True, False]
    )

    if win:
        prize = int(
            amount * WIN_PRIZE_RATE
        )

        owner_fee = int(
            amount * OWNER_GAME_FEE_RATE
        )

        add_balance(
            uid,
            prize,
        )

        if (
            get_owner_id() != uid
            and owner_fee > 0
        ):
            add_balance(
                get_owner_id(),
                owner_fee,
            )

        result = (
            "🎉 برنده شدید!\n\n"
            f"🎮 مبلغ بازی: "
            f"{amount:,} {CURRENCY}\n"
            f"🏆 جایزه: "
            f"{prize:,} {CURRENCY}\n"
            f"👑 سهم مالک: "
            f"{owner_fee:,} {CURRENCY}\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(uid):,} {CURRENCY}"
        )

    else:
        owner_fee = amount

        if get_owner_id() != uid:
            add_balance(
                get_owner_id(),
                owner_fee,
            )

        result = (
            "❌ باختید.\n\n"
            f"🎮 مبلغ بازی: "
            f"{amount:,} {CURRENCY}\n"
            f"👑 سهم مالک: "
            f"{owner_fee:,} {CURRENCY}\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(uid):,} {CURRENCY}"
        )

    game_id = (
        f"G{time.time_ns()}"
    )

    data["games"][game_id] = {
        "user_id": uid,
        "amount": amount,
        "win": win,
        "created_at": int(
            time.time()
        ),
    }

    save_data()

    clear_state(uid)

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
        f"💰 حداقل واریز: "
        f"{MIN_DEPOSIT:,} {CURRENCY}\n"
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
            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} {CURRENCY} است."
        )
        return

    deposit_id = (
        f"D{time.time_ns()}"
    )

    data["deposits"][
        deposit_id
    ] = {
        "user_id": uid,
        "amount": amount,
        "status": "waiting_receipt",
        "created_at": int(
            time.time()
        ),
    }

    save_data()

    STATE[uid] = {
        "step": "deposit_receipt",
        "id": deposit_id,
    }

    # فرمت دقیق واریزی
    await update.message.reply_text(
        "💳 واریزی\n\n"
        f"{DEPOSIT_NETWORK} "
        f"{amount:,} {CURRENCY} "
        f"{DEPOSIT_USERNAME}\n\n"
        "📌 روی متن بالا بزنید تا کپی شود.\n\n"
        "📸 بعد از پرداخت، رسید را "
        "به صورت عکس یا فایل ارسال کنید.",
        reply_markup=back_keyboard(),
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
        clear_state(uid)

        await update.message.reply_text(
            "❌ درخواست واریز پیدا نشد."
        )
        return

    if deposit.get("status") != "waiting_receipt":
        await update.message.reply_text(
            "⚠️ این رسید قبلاً ارسال شده است."
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
        f"{deposit['amount']:,} {CURRENCY}\n"
        f"📋 فرمت: "
        f"{DEPOSIT_NETWORK} "
        f"{deposit['amount']:,} "
        f"{CURRENCY} "
        f"{DEPOSIT_USERNAME}\n"
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
            repr(error),
        )

        deposit["status"] = (
            "waiting_receipt"
        )

        save_data()

        await update.message.reply_text(
            "❌ ارسال رسید برای مالک انجام نشد."
        )

        return

    clear_state(uid)

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

    if not query:
        return

    if not is_owner(
        query.from_user.id
    ):
        try:
            await query.answer(
                "❌ دسترسی ندارید.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    try:
        action, deposit_id = (
            query.data.split(
                ":",
                1,
            )
        )
    except Exception:
        return

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

        deposit["status"] = "approved"

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            "✅ واریز تأیید شد.\n\n"
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}"
        )

        user_text = (
            "✅ واریز شما تأیید شد.\n\n"
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"💳 موجودی: "
            f"{get_balance(uid):,} "
            f"{CURRENCY}"
        )

    else:

        deposit["status"] = "rejected"

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
        f"💰 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} {CURRENCY}\n"
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
            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} {CURRENCY} است."
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
        f"{amount:,} {CURRENCY}\n\n"
        "👤 حالا آیدی خودتان را وارد کنید.\n\n"
        "مثال:\n"
        "@username\n\n"
        "⚠️ آیدی عددی وارد نکنید."
    )


async def withdraw_target(
    update,
    context,
):
    uid = update.effective_user.id

    target_id = (
        update.message.text.strip()
    )

    if not target_id:
        await update.message.reply_text(
            "❌ آیدی معتبر وارد کنید."
        )
        return

    if target_id.isdigit():
        await update.message.reply_text(
            "❌ آیدی عددی قابل قبول نیست.\n"
            "آیدی خودتان را مثل @username وارد کنید."
        )
        return

    if len(target_id) > 100:
        await update.message.reply_text(
            "❌ آیدی بیش از حد طولانی است."
        )
        return

    state = STATE.get(
        uid,
        {},
    )

    amount = int(
        state.get(
            "amount",
            0,
        )
    )

    if amount < MIN_WITHDRAW:
        clear_state(uid)
        return

    if not remove_balance(
        uid,
        amount,
    ):
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        clear_state(uid)
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
        "created_at": int(
            time.time()
        ),
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
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"👤 آیدی کاربر: {target_id}\n"
            f"📋 درخواست: {withdraw_id}",
            reply_markup=keyboard,
        )

    except Exception as error:

        print(
            "WITHDRAW SEND ERROR:",
            repr(error),
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

        clear_state(uid)

        await update.message.reply_text(
            "❌ ارسال درخواست برای مالک انجام نشد.\n"
            "💰 مبلغ به موجودی شما برگشت."
        )

        return

    clear_state(uid)

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

    if not query:
        return

    if not is_owner(
        query.from_user.id
    ):
        try:
            await query.answer(
                "❌ دسترسی ندارید.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    try:
        action, withdraw_id = (
            query.data.split(
                ":",
                1,
            )
        )
    except Exception:
        return

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

    target_id = str(
        request["target_id"]
    )

    if action == "with_ok":

        request["status"] = "approved"

        admin_text = (
            "✅ برداشت تأیید شد.\n\n"
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"👤 آیدی: {target_id}"
        )

        user_text = (
            "✅ برداشت شما تأیید شد.\n\n"
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"👤 آیدی: {target_id}"
        )

    else:

        request["status"] = "rejected"

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            "❌ برداشت رد شد و مبلغ برگشت خورد.\n\n"
            f"💰 مبلغ: "
            f"{amount:,} {CURRENCY}"
        )

        user_text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ {amount:,} "
            f"{CURRENCY} به موجودی شما برگشت."
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

async def transfer_start(
    update,
    context,
):
    await update.message.reply_text(
        "🔄 انتقال موجودی\n\n"
        "روی پیام کاربر ریپلای کنید و سپس بنویسید:\n\n"
        "انتقال 500\n\n"
        "مثال:\n"
        "انتقال 500",
        reply_markup=back_keyboard(),
    )


async def transfer_text(
    update,
    context,
):
    message = update.message
    uid = update.effective_user.id

    if not message.reply_to_message:
        await message.reply_text(
            "❌ برای انتقال باید روی پیام کاربر ریپلای کنید.\n\n"
            "مثال:\n"
            "انتقال 500"
        )
        return

    parts = (
        message.text
        .strip()
        .split()
    )

    if len(parts) != 2:
        await message.reply_text(
            "❌ فرمت صحیح:\n"
            "انتقال 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(
                ",",
                "",
            )
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

    if not receiver:
        await message.reply_text(
            "❌ گیرنده پیدا نشد."
        )
        return

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
        f"💰 مبلغ: "
        f"{amount:,} {CURRENCY}\n"
        f"👤 گیرنده: {receiver.first_name}\n\n"
        f"💳 موجودی شما: "
        f"{get_balance(uid):,} {CURRENCY}"
    )

    try:
        await context.bot.send_message(
            receiver.id,
            "💰 یک انتقال دریافت کردید.\n\n"
            f"➕ مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"💳 موجودی شما: "
            f"{get_balance(receiver.id):,} "
            f"{CURRENCY}",
        )
    except Exception:
        pass


# =========================================================
# ADMIN KEYBOARD
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
            [
                InlineKeyboardButton(
                    "🔙 بستن پنل",
                    callback_data="adm_close",
                ),
            ],
        ]
    )


# =========================================================
# ADMIN PANEL
# =========================================================

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
        f"{reward:,} {CURRENCY}\n\n"
        "از دکمه‌های زیر استفاده کنید.",
        reply_markup=admin_keyboard(),
    )


async def admin_callback(
    update,
    context,
):
    query = update.callback_query

    if not query:
        return

    uid = query.from_user.id

    if not is_owner(uid):
        try:
            await query.answer(
                "❌ فقط مالک دسترسی دارد.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = query.data

    if action == "adm_close":

        clear_state(uid)

        try:
            await query.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await query.message.reply_text(
            "🏠 پنل بسته شد.",
            reply_markup=main_keyboard(uid),
        )
        return

    if action == "adm_users":

        await query.message.reply_text(
            "👥 اطلاعات کاربران\n\n"
            f"تعداد کاربران ثبت‌شده: "
            f"{len(data['users']):,}"
        )
        return

    if action == "adm_add":

        STATE[uid] = {
            "step": "admin_add"
        }

        await query.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000",
            reply_markup=back_keyboard(),
        )
        return

    if action == "adm_remove":

        STATE[uid] = {
            "step": "admin_remove"
        }

        await query.message.reply_text(
            "➖ کسر موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000",
            reply_markup=back_keyboard(),
        )
        return

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
            f"{current_reward:,} {CURRENCY}\n\n"
            "مبلغ جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "50",
            reply_markup=back_keyboard(),
        )
        return

    if action == "adm_owner":

        STATE[uid] = {
            "step": "admin_owner"
        }

        await query.message.reply_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "123456789",
            reply_markup=back_keyboard(),
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

    admin_steps = (
        "admin_add",
        "admin_remove",
        "admin_reward",
        "admin_owner",
    )

    if step not in admin_steps:
        return False

    if not is_owner(uid):
        return True

    text = (
        update.message.text
        .strip()
    )

    if step == "admin_reward":

        try:
            reward = int(
                text.replace(
                    ",",
                    "",
                )
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

        clear_state(uid)

        await update.message.reply_text(
            "✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 جایزه جدید هر رفرال: "
            f"{reward:,} {CURRENCY}",
            reply_markup=main_keyboard(uid),
        )

        return True

    if step == "admin_owner":

        try:
            new_owner = int(text)
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

        clear_state(uid)

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
        target_id = int(parts[0])

        amount = int(
            parts[1].replace(
                ",",
                "",
            )
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی و مبلغ باید عدد باشند."
        )

        return True

    if (
        target_id <= 0
        or amount <= 0
    ):
        await update.message.reply_text(
            "❌ اطلاعات واردشده نامعتبر است."
        )
        return True

    if str(target_id) not in data["users"]:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )
        return True

    if step == "admin_add":

        add_balance(
            target_id,
            amount,
        )

        result = (
            "✅ موجودی شارژ شد.\n\n"
            f"👤 کاربر: {target_id}\n"
            f"➕ مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} "
            f"{CURRENCY}"
        )

    else:

        if not remove_balance(
            target_id,
            amount,
        ):
            await update.message.reply_text(
                "❌ موجودی کاربر برای کسر این مبلغ کافی نیست."
            )
            return True

        result = (
            "✅ موجودی کسر شد.\n\n"
            f"👤 کاربر: {target_id}\n"
            f"➖ مبلغ: "
            f"{amount:,} {CURRENCY}\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} "
            f"{CURRENCY}"
        )

    clear_state(uid)

    await update.message.reply_text(
        result,
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
        "پیام خود را ارسال کنید.\n\n"
        "پشتیبانی به‌زودی بررسی می‌کند.",
        reply_markup=back_keyboard(),
    )


# =========================================================
# BACK
# =========================================================

async def go_back(
    update,
    context,
):
    uid = update.effective_user.id

    clear_state(uid)

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

    if not user:
        return

    uid = user.id

    text = (
        update.message.text
        .strip()
    )

    create_user(user)

    # ضد اسپم
    if not anti_spam(uid):
        return

    # -----------------------------------------------------
    # BACK
    # -----------------------------------------------------

    if text == "🔙 برگشت":

        await go_back(
            update,
            context,
        )
        return

    # -----------------------------------------------------
    # فقط یک مسیر برای موجودی
    # -----------------------------------------------------

    if (
        text == "💰 موجودی"
        or text.lower() == "موجودی"
    ):

        await balance_message(
            update,
            context,
        )
        return

    # -----------------------------------------------------
    # انتقال
    # -----------------------------------------------------

    if text.startswith("انتقال "):

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
    # ADMIN STATE
    # -----------------------------------------------------

    if await admin_state(
        update,
        context,
    ):
        return

    # -----------------------------------------------------
    # CURRENT STATE
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
# COMMANDS
# =========================================================

async def command_start(
    update,
    context,
):
    try:
        await start(
            update,
            context,
        )
    except Exception as error:
        print(
            "START ERROR:",
            repr(error),
        )


async def command_referral(
    update,
    context,
):
    try:

        user = update.effective_user

        if user:
            create_user(user)

        await referral_menu(
            update,
            context,
        )

    except Exception as error:

        print(
            "REFERRAL ERROR:",
            repr(error),
        )


async def command_profile(
    update,
    context,
):
    try:
        await profile(
            update,
            context,
        )
    except Exception as error:
        print(
            "PROFILE ERROR:",
            repr(error),
        )


async def command_admin(
    update,
    context,
):
    try:
        await admin_panel(
            update,
            context,
        )
    except Exception as error:
        print(
            "ADMIN ERROR:",
            repr(error),
        )


# =========================================================
# CONTACT
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
            repr(error),
        )

        try:
            await update.message.reply_text(
                "❌ هنگام تأیید شماره خطایی رخ داد."
            )
        except Exception:
            pass


# =========================================================
# PHOTO
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
            repr(error),
        )


# =========================================================
# DOCUMENT
# =========================================================

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
            repr(error),
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

        data_value = (
            query.data or ""
        )

        if data_value == "check_join":

            await check_join_callback(
                update,
                context,
            )
            return

        if (
            data_value.startswith(
                "dep_ok:"
            )
            or data_value.startswith(
                "dep_no:"
            )
        ):

            await deposit_callback(
                update,
                context,
            )
            return

        if (
            data_value.startswith(
                "with_ok:"
            )
            or data_value.startswith(
                "with_no:"
            )
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

        try:
            await query.answer()
        except Exception:
            pass

    except Exception as error:

        print(
            "CALLBACK ERROR:",
            repr(error),
        )

        try:
            await query.answer(
                "❌ خطایی رخ داد.",
                show_alert=True,
            )
        except Exception:
            pass


# =========================================================
# ERROR HANDLER
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
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__,
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

    # فقط یک balance handler
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
            filters.TEXT & ~filters.COMMAND,
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
