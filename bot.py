import os
import json
import random
import time
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
# تنظیمات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()

try:
    OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else 0
except ValueError:
    OWNER_ID = 0


# آیدی کانال و گپ اجباری
# مثال:
# @mychannel
# @mygroup
REQUIRED_CHANNEL = os.getenv(
    "REQUIRED_CHANNEL",
    "@YOUR_CHANNEL"
).strip()

REQUIRED_GROUP = os.getenv(
    "REQUIRED_GROUP",
    "@YOUR_GROUP"
).strip()


DATA_FILE = "data.json"

# فقط حداقل بازی
MIN_GAME = 500

# حداقل واریز
MIN_DEPOSIT = 5000

# حداقل برداشت
MIN_WITHDRAW = 10000

# آدرس/نام کیف پول
ULTRA_WALLET = "@CyyFr"


# =========================================================
# داده
# =========================================================

def default_data():
    return {
        "owner_id": OWNER_ID,
        "users": {},
        "deposits": {},
        "withdraws": {},
        "games": {},
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            result = json.load(f)

        if not isinstance(result, dict):
            return default_data()

        base = default_data()
        base.update(result)

        if not isinstance(base.get("users"), dict):
            base["users"] = {}

        if not isinstance(base.get("deposits"), dict):
            base["deposits"] = {}

        if not isinstance(base.get("withdraws"), dict):
            base["withdraws"] = {}

        if not isinstance(base.get("games"), dict):
            base["games"] = {}

        if not base.get("owner_id"):
            base["owner_id"] = OWNER_ID

        return base

    except Exception:
        return default_data()


data = load_data()


def save_data():
    temp = DATA_FILE + ".tmp"

    with open(
        temp,
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
        temp,
        DATA_FILE
    )


# =========================================================
# مالک
# =========================================================

def get_owner_id():
    try:
        return int(data.get("owner_id", 0))
    except Exception:
        return 0


def is_owner(user_id):
    return int(user_id) == get_owner_id()


# =========================================================
# کاربران
# =========================================================

def create_user(user):
    uid = str(user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "کاربر",
            "username": user.username or "",
            "phone": "",
            "verified": False,
            "balance": 0,
        }

    else:
        data["users"][uid]["name"] = (
            user.first_name or
            data["users"][uid].get("name", "کاربر")
        )

        data["users"][uid]["username"] = (
            user.username or
            data["users"][uid].get("username", "")
        )

    save_data()


def ensure_user(user_id):
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": int(user_id),
            "name": "کاربر",
            "username": "",
            "phone": "",
            "verified": False,
            "balance": 0,
        }

        save_data()


def get_balance(user_id):
    ensure_user(user_id)

    return int(
        data["users"][str(user_id)].get(
            "balance",
            0
        )
    )


def set_balance(user_id, amount):
    ensure_user(user_id)

    data["users"][str(user_id)]["balance"] = max(
        0,
        int(amount)
    )

    save_data()


def add_balance(user_id, amount):
    set_balance(
        user_id,
        get_balance(user_id) + int(amount)
    )


def remove_balance(user_id, amount):
    amount = int(amount)

    if amount < 0:
        return False

    balance = get_balance(user_id)

    if balance < amount:
        return False

    set_balance(
        user_id,
        balance - amount
    )

    return True


# =========================================================
# وضعیت کاربر
# =========================================================

USER_STATE = {}


# =========================================================
# عضویت اجباری
# =========================================================

async def check_membership(bot, user_id):
    chats = [
        REQUIRED_CHANNEL,
        REQUIRED_GROUP,
    ]

    for chat in chats:

        if not chat:
            continue

        if chat.startswith("@YOUR_"):
            return False

        try:

            member = await bot.get_chat_member(
                chat_id=chat,
                user_id=user_id
            )

            if member.status in (
                "left",
                "kicked"
            ):
                return False

        except Exception as e:

            print(
                f"Membership error for {chat}: {e}"
            )

            return False

    return True


def membership_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 کانال",
                    url=(
                        "https://t.me/"
                        + REQUIRED_CHANNEL.lstrip("@")
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 گپ",
                    url=(
                        "https://t.me/"
                        + REQUIRED_GROUP.lstrip("@")
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ بررسی عضویت",
                    callback_data="check_membership"
                )
            ],
        ]
    )


async def require_membership(
    update,
    context
):
    user = update.effective_user

    ok = await check_membership(
        context.bot,
        user.id
    )

    if ok:
        return True

    text = (
        "🔒 عضویت اجباری\n\n"
        "برای استفاده از ربات ابتدا "
        "در کانال و گپ عضو شوید.\n\n"
        "بعد از عضویت روی «بررسی عضویت» بزنید."
    )

    if update.callback_query:

        await update.callback_query.message.reply_text(
            text,
            reply_markup=membership_keyboard()
        )

    elif update.message:

        await update.message.reply_text(
            text,
            reply_markup=membership_keyboard()
        )

    return False


# =========================================================
# شماره تلفن
# =========================================================

def phone_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 تأیید شماره تلفن",
                    request_contact=True
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def ask_phone(
    update,
    context
):

    await update.message.reply_text(
        "📱 برای ادامه باید شماره تلفن خود "
        "را تأیید کنید.\n\n"
        "⚠️ فقط شماره‌های ایران با پیش‌شماره "
        "+98 پذیرفته می‌شوند.",
        reply_markup=phone_keyboard()
    )


# =========================================================
# منوی اصلی
# =========================================================

def main_keyboard(user_id):

    rows = [
        [
            "🎮 بازی",
            "💰 موجودی",
        ],
        [
            "💳 واریز",
            "💸 برداشت",
        ],
        [
            "🔄 انتقال",
            "🆘 پشتیبانی",
        ],
    ]

    if is_owner(user_id):
        rows.append(
            ["⚙️ پنل مدیریت"]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🔙 بازگشت"]
        ],
        resize_keyboard=True
    )


# =========================================================
# بررسی دسترسی
# =========================================================

async def user_is_verified(
    update,
    context
):

    user = update.effective_user

    if not user:
        return False

    ensure_user(user.id)

    if not data["users"][
        str(user.id)
    ].get("verified", False):

        return False

    return True


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

    # اول عضویت
    if not await require_membership(
        update,
        context
    ):
        return

    # بعد شماره
    if not data["users"][
        str(user.id)
    ].get("verified", False):

        await ask_phone(
            update,
            context
        )

        return

    await update.message.reply_text(
        "👋 خوش آمدید.\n\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# بررسی دکمه عضویت
# =========================================================

async def membership_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    ok = await check_membership(
        context.bot,
        user_id
    )

    if not ok:

        await query.answer(
            "❌ هنوز در کانال و گپ عضو نشده‌اید.",
            show_alert=True
        )

        return

    ensure_user(user_id)

    if not data["users"][
        str(user_id)
    ].get("verified", False):

        await query.message.reply_text(
            "✅ عضویت تأیید شد.\n\n"
            "حالا شماره تلفن خود را تأیید کنید.",
            reply_markup=phone_keyboard()
        )

        return

    await query.message.reply_text(
        "✅ عضویت شما تأیید شد.",
        reply_markup=main_keyboard(
            user_id
        )
    )


# =========================================================
# شماره تلفن
# =========================================================

async def handle_contact(
    update,
    context
):

    user = update.effective_user
    contact = update.message.contact

    if not user or not contact:
        return

    create_user(user)

    # فقط شماره‌ای که واقعاً متعلق به همان کاربر است
    if contact.user_id != user.id:

        await update.message.reply_text(
            "❌ لطفاً شماره خودتان را "
            "با دکمه تأیید ارسال کنید."
        )

        return

    phone = contact.phone_number.strip()

    # حذف فاصله و -
    phone = phone.replace(
        " ",
        ""
    ).replace(
        "-",
        ""
    )

    # تبدیل 0098 به +98
    if phone.startswith("0098"):
        phone = "+" + phone[2:]

    if not phone.startswith("+98"):

        await update.message.reply_text(
            "❌ فقط شماره‌های ایران "
            "با +98 پذیرفته می‌شوند.",
            reply_markup=phone_keyboard()
        )

        return

    data["users"][
        str(user.id)
    ]["phone"] = phone

    data["users"][
        str(user.id)
    ]["verified"] = True

    save_data()

    await update.message.reply_text(
        "✅ شماره تلفن تأیید شد.\n\n"
        "🎉 ورود شما کامل شد.",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# موجودی
# =========================================================

async def balance_command(
    update,
    context
):

    user = update.effective_user

    if not await user_is_verified(
        update,
        context
    ):
        await start(update, context)
        return

    await update.message.reply_text(
        "💰 موجودی شما:\n\n"
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# بازی
# =========================================================

async def game_menu(
    update,
    context
):

    uid = update.effective_user.id

    USER_STATE[uid] = {
        "step": "game_amount"
    }

    await update.message.reply_text(
        "🎮 بازی\n\n"
        f"حداقل بازی: {MIN_GAME:,} DOGS\n\n"
        "⚠️ حداکثر بازی ندارد.\n\n"
        "مبلغ بازی را ارسال کنید.\n\n"
        "مثال:\n"
        "500",
        reply_markup=back_keyboard()
    )


async def handle_game(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    if state.get("step") != "game_amount":
        return False

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

        return True

    if amount < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل بازی "
            f"{MIN_GAME:,} DOGS است."
        )

        return True

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS"
        )

        return True

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return True

    game_id = (
        f"G{int(time.time() * 1000)}"
        f"_{uid}"
    )

    # نتیجه بازی
    won = random.choice(
        [True, False]
    )

    game = {
        "id": game_id,
        "user_id": uid,
        "amount": amount,
        "status": "finished",
        "won": won,
        "created": datetime.now().isoformat(),
    }

    if won:

        # 500 -> 900
        prize = int(
            amount * 1.8
        )

        # 500 -> 100
        owner_profit = (
            amount
            - int(amount * 0.8)
        )

        # برای 500:
        # owner_profit = 100

        add_balance(
            uid,
            prize
        )

        if get_owner_id():
            add_balance(
                get_owner_id(),
                owner_profit
            )

        game["prize"] = prize
        game["owner_profit"] = owner_profit

        data["games"][game_id] = game
        save_data()

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "🎉 برنده شدید!\n\n"
            f"🎮 بازی: {amount:,} DOGS\n"
            f"🏆 جایزه: {prize:,} DOGS\n\n"
            f"💰 موجودی: "
            f"{get_balance(uid):,} DOGS",
            reply_markup=main_keyboard(
                uid
            )
        )

    else:

        if get_owner_id():
            add_balance(
                get_owner_id(),
                amount
            )

        game["prize"] = 0
        game["owner_profit"] = amount

        data["games"][game_id] = game
        save_data()

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ باختید.\n\n"
            f"🎮 مبلغ بازی: "
            f"{amount:,} DOGS\n\n"
            f"💰 موجودی: "
            f"{get_balance(uid):,} DOGS",
            reply_markup=main_keyboard(
                uid
            )
        )

    return True


# =========================================================
# انتقال
# =========================================================

async def transfer_command(
    update,
    context
):

    message = update.message

    if not message:
        return

    if not message.reply_to_message:

        await message.reply_text(
            "🔄 انتقال\n\n"
            "روی پیام کاربر ریپلای کنید.\n\n"
            "سپس بنویسید:\n"
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
            "❌ مبلغ صحیح نیست."
        )

        return

    if amount <= 0:

        await message.reply_text(
            "❌ مبلغ صحیح نیست."
        )

        return

    sender = update.effective_user

    receiver = (
        message
        .reply_to_message
        .from_user
    )

    if receiver.id == sender.id:

        await message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )

        return

    create_user(sender)
    create_user(receiver)

    if not remove_balance(
        sender.id,
        amount
    ):

        await message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return

    add_balance(
        receiver.id,
        amount
    )

    await message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {receiver.first_name}\n\n"
        f"💳 موجودی شما: "
        f"{get_balance(sender.id):,} DOGS"
    )

    try:

        await context.bot.send_message(
            receiver.id,
            "💰 انتقال دریافت شد.\n\n"
            f"مبلغ: {amount:,} DOGS\n"
            f"از طرف: {sender.first_name}\n\n"
            f"💳 موجودی: "
            f"{get_balance(receiver.id):,} DOGS"
        )

    except Exception:
        pass


# =========================================================
# واریز
# =========================================================

async def deposit_start(
    update,
    context
):

    uid = update.effective_user.id

    USER_STATE[uid] = {
        "step": "deposit_amount"
    }

    await update.message.reply_text(
        "💳 واریز\n\n"
        f"حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"
        "مبلغ واریز را وارد کنید.\n\n"
        "مثال:\n"
        "5000",
        reply_markup=back_keyboard()
    )


async def handle_deposit_amount(
    update,
    context
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
            "❌ مبلغ صحیح نیست."
        )

        return True

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(
            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است."
        )

        return True

    deposit_id = (
        f"D{int(time.time() * 1000)}"
        f"_{uid}"
    )

    data["deposits"][deposit_id] = {
        "id": deposit_id,
        "user_id": uid,
        "amount": amount,
        "status": "waiting_receipt",
        "created": datetime.now().isoformat(),
    }

    save_data()

    USER_STATE[uid] = {
        "step": "deposit_receipt",
        "deposit_id": deposit_id,
    }

    await update.message.reply_text(
        "💳 اطلاعات واریز:\n\n"
        f"ULTRA\n"
        f"مبلغ: {amount:,} DOGS\n"
        f"ولت: {ULTRA_WALLET}\n\n"
        "📸 بعد از واریز، رسید را ارسال کنید."
    )

    return True


async def handle_deposit_receipt(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    if state.get("step") != "deposit_receipt":
        return False

    deposit_id = state.get(
        "deposit_id"
    )

    deposit = data["deposits"].get(
        deposit_id
    )

    if not deposit:

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return True

    deposit["status"] = "pending"

    save_data()

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=
                    f"dep_ok:{deposit_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=
                    f"dep_no:{deposit_id}"
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

    owner = get_owner_id()

    try:

        if update.message.photo:

            await context.bot.send_photo(
                chat_id=owner,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                reply_markup=buttons
            )

        elif update.message.document:

            await context.bot.send_document(
                chat_id=owner,
                document=update.message.document.file_id,
                caption=caption,
                reply_markup=buttons
            )

        else:

            await context.bot.send_message(
                chat_id=owner,
                text=(
                    caption
                    + "\n\n"
                    + (
                        update.message.text
                        or ""
                    )
                ),
                reply_markup=buttons
            )

    except Exception:

        await update.message.reply_text(
            "❌ ارسال رسید برای مالک انجام نشد."
        )

        return True

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ رسید دریافت شد.\n\n"
        "برای مالک ارسال شد.\n"
        "⏳ منتظر بررسی باشید.",
        reply_markup=main_keyboard(
            uid
        )
    )

    return True


# =========================================================
# تأیید واریز
# =========================================================

async def deposit_decision(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    action, deposit_id = (
        query.data.split(
            ":",
            1
        )
    )

    deposit = data["deposits"].get(
        deposit_id
    )

    if not deposit:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if deposit["status"] != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
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
            amount
        )

        save_data()

        try:

            await context.bot.send_message(
                uid,
                "✅ واریز تأیید شد.\n\n"
                f"💰 مبلغ: "
                f"{amount:,} DOGS\n"
                f"💳 موجودی: "
                f"{get_balance(uid):,} DOGS"
            )

        except Exception:
            pass

        await query.message.reply_text(
            "✅ واریز تأیید شد."
        )

    else:

        deposit["status"] = "rejected"

        save_data()

        try:

            await context.bot.send_message(
                uid,
                "❌ واریز شما رد شد."
            )

        except Exception:
            pass

        await query.message.reply_text(
            "❌ واریز رد شد."
        )

    try:
        await query.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass


# =========================================================
# برداشت
# =========================================================

async def withdraw_start(
    update,
    context
):

    uid = update.effective_user.id

    if get_balance(uid) < MIN_WITHDRAW:

        await update.message.reply_text(
            "💸 برداشت\n\n"
            f"حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n\n"
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی: "
            f"{get_balance(uid):,} DOGS",
            reply_markup=main_keyboard(
                uid
            )
        )

        return

    USER_STATE[uid] = {
        "step": "withdraw_amount"
    }

    await update.message.reply_text(
        "💸 برداشت\n\n"
        f"حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n"
        "حداکثر برداشت: ندارد\n\n"
        "تعداد برداشت را وارد کنید.",
        reply_markup=back_keyboard()
    )


async def handle_withdraw_amount(
    update,
    context
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
            "❌ مبلغ صحیح نیست."
        )

        return True

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."
        )

        return True

    if amount > get_balance(uid):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return True

    USER_STATE[uid] = {
        "step": "withdraw_id",
        "amount": amount,
    }

    await update.message.reply_text(
        "✅ مبلغ ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "🆔 حالا آیدی عددی دریافت‌کننده "
        "را ارسال کنید.\n\n"
        "مثال:\n"
        "123456789"
    )

    return True


async def handle_withdraw_id(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    try:

        target_id = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی باید عددی باشد."
        )

        return True

    amount = int(
        state["amount"]
    )

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        USER_STATE.pop(
            uid,
            None
        )

        return True

    withdraw_id = (
        f"W{int(time.time() * 1000)}"
        f"_{uid}"
    )

    data["withdraws"][withdraw_id] = {
        "id": withdraw_id,
        "user_id": uid,
        "target_id": target_id,
        "amount": amount,
        "status": "pending",
        "created": datetime.now().isoformat(),
    }

    save_data()

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید برداشت",
                    callback_data=
                    f"with_ok:{withdraw_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد برداشت",
                    callback_data=
                    f"with_no:{withdraw_id}"
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
            f"🆔 دریافت‌کننده: {target_id}\n\n"
            f"📋 درخواست: {withdraw_id}",
            reply_markup=buttons
        )

    except Exception:

        add_balance(
            uid,
            amount
        )

        data["withdraws"].pop(
            withdraw_id,
            None
        )

        save_data()

        await update.message.reply_text(
            "❌ درخواست برای مالک ارسال نشد.\n\n"
            "💰 مبلغ به موجودی شما برگشت."
        )

        USER_STATE.pop(
            uid,
            None
        )

        return True

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"🆔 آیدی دریافت‌کننده: {target_id}\n\n"
        "⏳ منتظر تأیید مالک باشید.",
        reply_markup=main_keyboard(
            uid
        )
    )

    return True


# =========================================================
# تأیید برداشت
# =========================================================

async def withdraw_decision(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    action, withdraw_id = (
        query.data.split(
            ":",
            1
        )
    )

    req = data["withdraws"].get(
        withdraw_id
    )

    if not req:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if req["status"] != "pending":

        await query.message.reply_text(
            "⚠️ قبلاً بررسی شده."
        )

        return

    uid = int(
        req["user_id"]
    )

    amount = int(
        req["amount"]
    )

    target_id = int(
        req["target_id"]
    )

    if action == "with_ok":

        req["status"] = "approved"

        save_data()

        # فقط پیام خصوصی به کاربر
        # هیچ پیام برداشت شدی در گپ ارسال نمی‌شود.
        try:

            await context.bot.send_message(
                uid,
                "✅ درخواست برداشت شما تأیید شد.\n\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"🆔 آیدی دریافت‌کننده: {target_id}"
            )

        except Exception:
            pass

        await query.message.reply_text(
            "✅ برداشت تأیید شد."
        )

    else:

        req["status"] = "rejected"

        add_balance(
            uid,
            amount
        )

        save_data()

        try:

            await context.bot.send_message(
                uid,
                "❌ درخواست برداشت رد شد.\n\n"
                f"💰 مبلغ {amount:,} DOGS "
                "به موجودی شما برگشت."
            )

        except Exception:
            pass

        await query.message.reply_text(
            "❌ برداشت رد شد و مبلغ برگشت."
        )

    try:

        await query.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass


# =========================================================
# پنل مدیریت
# =========================================================

async def admin_panel(
    update,
    context
):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ دسترسی ندارید."
        )

        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 شارژ موجودی",
                    callback_data="admin_charge"
                ),
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data="admin_deduct"
                ),
            ],
            [
                InlineKeyboardButton(
                    "👥 تعداد کاربران",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="admin_transfer_owner"
                )
            ],
        ]
    )

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"👑 مالک فعلی: {get_owner_id()}\n"
        f"👥 کاربران: {len(data['users']):,}",
        reply_markup=keyboard
    )


# =========================================================
# دکمه‌های پنل
# =========================================================

async def admin_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    uid = query.from_user.id

    if not is_owner(uid):

        await query.answer(
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    if query.data == "admin_users":

        await query.message.reply_text(
            "👥 تعداد کاربران:\n\n"
            f"{len(data['users']):,}"
        )

        return

    if query.data == "admin_charge":

        USER_STATE[uid] = {
            "step": "admin_charge"
        }

        await query.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return

    if query.data == "admin_deduct":

        USER_STATE[uid] = {
            "step": "admin_deduct"
        }

        await query.message.reply_text(
            "➖ کسر موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return

    if query.data == "admin_transfer_owner":

        USER_STATE[uid] = {
            "step": "admin_transfer_owner"
        }

        await query.message.reply_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "123456789\n\n"
            "⚠️ بعد از انتقال، مالک قبلی "
            "دسترسی پنل مدیریت را از دست می‌دهد."
        )

        return


# =========================================================
# عملیات پنل مدیریت
# =========================================================

async def handle_admin_action(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    step = state.get("step")

    if step not in (
        "admin_charge",
        "admin_deduct",
        "admin_transfer_owner"
    ):
        return False

    if not is_owner(uid):
        return True

    text = update.message.text.strip()

    # انتقال مالکیت
    if step == "admin_transfer_owner":

        try:
            new_owner = int(text)
        except ValueError:

            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )

            return True

        if new_owner <= 0:

            await update.message.reply_text(
                "❌ آیدی صحیح نیست."
            )

            return True

        if new_owner == uid:

            await update.message.reply_text(
                "❌ این آیدی خود شماست."
            )

            return True

        ensure_user(new_owner)

        old_owner = get_owner_id()

        data["owner_id"] = new_owner

        save_data()

        USER_STATE.pop(
            uid,
            None
        )

        try:

            await context.bot.send_message(
                new_owner,
                "👑 شما مالک جدید ربات شدید.\n\n"
                "⚙️ پنل مدیریت برای شما فعال شد."
            )

        except Exception:
            pass

        await update.message.reply_text(
            "✅ انتقال مالکیت انجام شد.\n\n"
            f"👑 مالک قبلی: {old_owner}\n"
            f"👑 مالک جدید: {new_owner}"
        )

        return True

    parts = text.split()

    if len(parts) != 2:

        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

        return True

    try:

        target_id = int(parts[0])

        amount = int(
            parts[1].replace(",", "")
        )

    except ValueError:

        await update.message.reply_text(
            "❌ اطلاعات صحیح نیست."
        )

        return True

    if target_id <= 0 or amount <= 0:

        await update.message.reply_text(
            "❌ اطلاعات صحیح نیست."
        )

        return True

    ensure_user(target_id)

    if step == "admin_charge":

        add_balance(
            target_id,
            amount
        )

        result = (
            "✅ موجودی شارژ شد.\n\n"
            f"🆔 {target_id}\n"
            f"💰 +{amount:,} DOGS\n"
            f"💳 موجودی: "
            f"{get_balance(target_id):,} DOGS"
        )

    else:

        if not remove_balance(
            target_id,
            amount
        ):

            await update.message.reply_text(
                "❌ موجودی کاربر کافی نیست."
            )

            return True

        result = (
            "✅ موجودی کسر شد.\n\n"
            f"🆔 {target_id}\n"
            f"💰 -{amount:,} DOGS\n"
            f"💳 موجودی: "
            f"{get_balance(target_id):,} DOGS"
        )

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        result,
        reply_markup=main_keyboard(uid)
    )

    return True


# =========================================================
# پشتیبانی
# =========================================================

async def support(
    update,
    context
):

    await update.message.reply_text(
        "🆘 پشتیبانی\n\n"
        "پیام خود را ارسال کنید."
    )


# =========================================================
# بازگشت
# =========================================================

async def back(
    update,
    context
):

    uid = update.effective_user.id

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(
        "🔙 برگشت",
        reply_markup=main_keyboard(uid)
    )


# =========================================================
# مسیریابی فایل/عکس رسید
# =========================================================

async def media_router(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if (
        state
        and state.get("step")
        == "deposit_receipt"
    ):

        await handle_deposit_receipt(
            update,
            context
        )


# =========================================================
# مسیریابی پیام
# =========================================================

async def text_router(
    update,
    context
):

    if not update.message:
        return

    user = update.effective_user

    if not user:
        return

    create_user(user)

    uid = user.id
    text = update.message.text.strip()

    # -----------------------------------------------------
    # عضویت اجباری
    # -----------------------------------------------------

    if not await check_membership(
        context.bot,
        uid
    ):

        await update.message.reply_text(
            "🔒 ابتدا در کانال و گپ عضو شوید.",
            reply_markup=membership_keyboard()
        )

        return

    # -----------------------------------------------------
    # شماره
    # -----------------------------------------------------

    if not data["users"][
        str(uid)
    ].get("verified", False):

        await update.message.reply_text(
            "📱 ابتدا شماره تلفن خود را "
            "با دکمه تأیید کنید.",
            reply_markup=phone_keyboard()
        )

        return

    # -----------------------------------------------------
    # انتقال
    # -----------------------------------------------------

    if text.startswith("انتقال "):

        await transfer_command(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # بازگشت
    # -----------------------------------------------------

    if text == "🔙 بازگشت":

        await back(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # وضعیت
    # -----------------------------------------------------

    state = USER_STATE.get(uid)

    if state:

        step = state.get("step")

        if step == "game_amount":

            if await handle_game(
                update,
                context
            ):
                return

        if step == "deposit_amount":

            if await handle_deposit_amount(
                update,
                context
            ):
                return

        if step == "withdraw_amount":

            if await handle_withdraw_amount(
                update,
                context
            ):
                return

        if step == "withdraw_id":

            if await handle_withdraw_id(
                update,
                context
            ):
                return

        if step in (
            "admin_charge",
            "admin_deduct",
            "admin_transfer_owner"
        ):

            if await handle_admin_action(
                update,
                context
            ):
                return

        if step == "deposit_receipt":

            await update.message.reply_text(
                "📸 لطفاً رسید را به صورت عکس "
                "یا فایل ارسال کنید."
            )

            return

    # -----------------------------------------------------
    # منوی اصلی
    # -----------------------------------------------------

    if text == "🎮 بازی":

        await game_menu(
            update,
            context
        )

    elif text == "💰 موجودی":

        await balance_command(
            update,
            context
        )

    elif text == "💳 واریز":

        await deposit_start(
            update,
            context
        )

    elif text == "💸 برداشت":

        await withdraw_start(
            update,
            context
        )

    elif text == "🔄 انتقال":

        await transfer_command(
            update,
            context
        )

    elif text == "🆘 پشتیبانی":

        await support(
            update,
            context
        )

    elif text == "⚙️ پنل مدیریت":

        await admin_panel(
            update,
            context
        )


# =========================================================
# خطا
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "BOT ERROR:",
        context.error
    )

    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    if OWNER_ID == 0:
        raise RuntimeError(
            "OWNER_ID تنظیم نشده یا عددی نیست."
        )

    if REQUIRED_CHANNEL.startswith("@YOUR_"):
        raise RuntimeError(
            "REQUIRED_CHANNEL را تنظیم کنید."
        )

    if REQUIRED_GROUP.startswith("@YOUR_"):
        raise RuntimeError(
            "REQUIRED_GROUP را تنظیم کنید."
        )

    if not data.get("owner_id"):
        data["owner_id"] = OWNER_ID

    save_data()

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

    # بررسی عضویت
    app.add_handler(
        CallbackQueryHandler(
            membership_callback,
            pattern=r"^check_membership$"
        )
    )

    # واریز
    app.add_handler(
        CallbackQueryHandler(
            deposit_decision,
            pattern=r"^dep_(ok|no):"
        )
    )

    # برداشت
    app.add_handler(
        CallbackQueryHandler(
            withdraw_decision,
            pattern=r"^with_(ok|no):"
        )
    )

    # پنل
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # شماره تلفن
    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            handle_contact
        )
    )

    # عکس / فایل رسید
    app.add_handler(
        MessageHandler(
            filters.PHOTO |
            filters.Document.ALL,
            media_router
        )
    )

    # متن
    app.add_handler(
        MessageHandler(
            filters.TEXT &
            ~filters.COMMAND,
            text_router
        )
    )

    app.add_error_handler(
        error_handler
    )

    print("==============================")
    print("BOT STARTED")
    print("OWNER:", get_owner_id())
    print("MIN GAME:", MIN_GAME)
    print("NO MAX GAME")
    print("==============================")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
