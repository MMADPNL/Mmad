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

OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()

try:
    ENV_OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else 0
except ValueError:
    ENV_OWNER_ID = 0


DATA_FILE = "data.json"

MIN_GAME = 500
MAX_GAME = 20000

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

WINNER_PRIZE = 900
OWNER_PROFIT = 100

ULTRA_WALLET = "@CyyFr"


# =========================================================
# DATA
# =========================================================

def default_data():
    return {
        "owner_id": ENV_OWNER_ID,
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

            saved = json.load(f)

        base = default_data()

        if isinstance(saved, dict):
            base.update(saved)

        if not isinstance(base.get("users"), dict):
            base["users"] = {}

        if not isinstance(base.get("deposits"), dict):
            base["deposits"] = {}

        if not isinstance(base.get("withdraws"), dict):
            base["withdraws"] = {}

        if not isinstance(base.get("games"), dict):
            base["games"] = {}

        return base

    except Exception:

        return default_data()


data = load_data()


# اگر owner_id قبلاً در فایل ذخیره نشده بود
if not isinstance(data.get("owner_id"), int):
    data["owner_id"] = ENV_OWNER_ID

if data.get("owner_id", 0) == 0 and ENV_OWNER_ID:
    data["owner_id"] = ENV_OWNER_ID


def save_data():

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


# =========================================================
# OWNER
# =========================================================

def get_owner_id():

    try:
        return int(data.get("owner_id", 0))
    except Exception:
        return 0


def is_owner(user_id):

    return (
        get_owner_id() != 0
        and int(user_id) == get_owner_id()
    )


# =========================================================
# USERS
# =========================================================

def create_user(user):

    uid = str(user.id)

    if uid not in data["users"]:

        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "کاربر",
            "username": user.username or "",
            "balance": 0,
        }

        save_data()

    else:

        data["users"][uid]["id"] = user.id

        if user.first_name:
            data["users"][uid]["name"] = user.first_name

        if user.username:
            data["users"][uid]["username"] = user.username


def ensure_user_id(user_id):

    uid = str(user_id)

    if uid not in data["users"]:

        data["users"][uid] = {
            "id": int(user_id),
            "name": "کاربر",
            "username": "",
            "balance": 0,
        }

        save_data()


def get_balance(user_id):

    ensure_user_id(user_id)

    return int(
        data["users"]
        [str(user_id)]
        .get("balance", 0)
    )


def set_balance(user_id, amount):

    ensure_user_id(user_id)

    data["users"][
        str(user_id)
    ]["balance"] = max(
        0,
        int(amount)
    )

    save_data()


def add_balance(user_id, amount):

    current = get_balance(user_id)

    set_balance(
        user_id,
        current + int(amount)
    )


def remove_balance(user_id, amount):

    amount = int(amount)

    current = get_balance(user_id)

    if amount < 0:
        return False

    if current < amount:
        return False

    set_balance(
        user_id,
        current - amount
    )

    return True


# =========================================================
# USER STATE
# =========================================================

USER_STATE = {}


# =========================================================
# KEYBOARDS
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
# START
# =========================================================

async def start(update, context):

    if not update.effective_user:
        return

    user = update.effective_user

    create_user(user)

    await update.message.reply_text(

        "👋 سلام\n\n"
        "به ربات خوش آمدید.\n\n"
        f"💰 موجودی شما: "
        f"{get_balance(user.id):,} DOGS\n\n"
        "از منوی زیر انتخاب کنید.",

        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# BALANCE
# =========================================================

async def balance_command(update, context):

    user = update.effective_user

    create_user(user)

    await update.message.reply_text(

        "💰 موجودی شما:\n\n"
        f"{get_balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# GAME MENU
# =========================================================

async def game_menu(update, context):

    uid = update.effective_user.id

    await update.message.reply_text(

        "🎮 بازی\n\n"

        f"حداقل بازی: "
        f"{MIN_GAME:,} DOGS\n"

        f"حداکثر بازی: "
        f"{MAX_GAME:,} DOGS\n\n"

        "💡 مبلغ بازی را ارسال کنید.\n\n"

        "مثال:\n"
        "500",

        reply_markup=back_keyboard()
    )

    USER_STATE[uid] = {
        "step": "game_amount"
    }


# =========================================================
# GAME
# =========================================================

async def handle_game(update, context):

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

    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر بازی "
            f"{MAX_GAME:,} DOGS است."
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
            "❌ خطا در ثبت بازی."
        )

        return True

    # =====================================================
    # نتیجه بازی
    # =====================================================

    # برای نمونه، نتیجه تصادفی است.
    # بازی 500:
    # برنده 900
    # مالک 100
    #
    # در حالت باخت، مبلغ بازی برنمی‌گردد.

    player_wins = random.choice(
        [True, False]
    )

    game_id = (
        f"G{int(time.time() * 1000)}"
        f"_{uid}"
    )

    game_data = {
        "id": game_id,
        "user_id": uid,
        "amount": amount,
        "status": "finished",
        "winner": player_wins,
        "created": datetime.now().isoformat(),
    }

    data["games"][game_id] = game_data

    if player_wins:

        # برای مبلغ 500 دقیقاً 900
        # برای مبالغ دیگر متناسب با همان نسبت
        winner_amount = int(
            amount * 1.8
        )

        owner_amount = (
            amount
            - winner_amount
            if amount >= winner_amount
            else int(amount * 0.2)
        )

        # حالت اصلی موردنظر:
        # 500 -> 900 + 100
        #
        # مبلغ 500 از بازیکن کسر شده.
        # 900 به برنده برمی‌گردد.
        # 100 به مالک می‌رسد.

        add_balance(
            uid,
            winner_amount
        )

        if get_owner_id():

            add_balance(
                get_owner_id(),
                owner_amount
            )

        game_data["winner_amount"] = winner_amount
        game_data["owner_amount"] = owner_amount

        save_data()

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(

            "🎉 برنده شدید!\n\n"

            f"🎮 مبلغ بازی: "
            f"{amount:,} DOGS\n\n"

            f"🏆 جایزه شما: "
            f"{winner_amount:,} DOGS\n\n"

            f"💰 موجودی جدید: "
            f"{get_balance(uid):,} DOGS",

            reply_markup=main_keyboard(
                uid
            )
        )

    else:

        game_data["winner_amount"] = 0
        game_data["owner_amount"] = amount

        if get_owner_id():

            add_balance(
                get_owner_id(),
                amount
            )

        save_data()

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(

            "❌ باختید.\n\n"

            f"🎮 مبلغ بازی: "
            f"{amount:,} DOGS\n\n"

            f"💰 موجودی جدید: "
            f"{get_balance(uid):,} DOGS",

            reply_markup=main_keyboard(
                uid
            )
        )

    return True


# =========================================================
# TRANSFER
# انتقال 500 با ریپلای
# =========================================================

async def transfer_command(update, context):

    message = update.message

    if not message:
        return

    if not message.reply_to_message:

        await message.reply_text(

            "🔄 انتقال\n\n"

            "برای انتقال روی پیام "
            "کاربر ریپلای کنید.\n\n"

            "سپس بنویسید:\n\n"

            "انتقال 500"
        )

        return

    parts = message.text.strip().split()

    if len(parts) != 2:

        await message.reply_text(

            "❌ فرمت صحیح:\n\n"
            "انتقال 500"
        )

        return

    try:

        amount = int(
            parts[1].replace(
                ",",
                ""
            )
        )

    except ValueError:

        await message.reply_text(
            "❌ مبلغ صحیح نیست."
        )

        return

    if amount <= 0:

        await message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
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

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n"

        f"👤 گیرنده: "
        f"{receiver.first_name}\n\n"

        f"💳 موجودی شما: "
        f"{get_balance(sender.id):,} DOGS"
    )

    try:

        await context.bot.send_message(

            receiver.id,

            "💰 انتقال دریافت کردید.\n\n"

            f"مبلغ: "
            f"{amount:,} DOGS\n"

            f"از طرف: "
            f"{sender.first_name}\n\n"

            f"💳 موجودی: "
            f"{get_balance(receiver.id):,} DOGS"
        )

    except Exception:
        pass


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update, context):

    uid = update.effective_user.id

    USER_STATE[uid] = {
        "step": "deposit_amount"
    }

    await update.message.reply_text(

        "💳 واریز\n\n"

        "فرصت واریز مثال:\n\n"

        f"ULTRA 5000 DOGS "
        f"{ULTRA_WALLET}\n\n"

        f"حداقل واریز "
        f"{MIN_DEPOSIT:,}\n\n"

        "تعداد واریزی را وارد کنید.\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()
    )


async def handle_deposit_amount(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    if state.get("step") != "deposit_amount":
        return False

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

        "💳 فرصت واریز:\n\n"

        f"ULTRA {amount:,} DOGS "
        f"{ULTRA_WALLET}\n\n"

        f"حداقل واریز "
        f"{MIN_DEPOSIT:,}\n\n"

        "📸 شات خود یا رسید پیام "
        "ارسال کنید.\n\n"

        "بعد از ارسال، رسید سریع "
        "برای مالک ارسال می‌شود."
    )

    return True


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

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

    dep = data["deposits"].get(
        deposit_id
    )

    if not dep:

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ درخواست واریز پیدا نشد."
        )

        return True

    dep["status"] = "pending"

    save_data()

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تایید",
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

        "💳 درخواست واریز جدید\n\n"

        f"👤 کاربر: {uid}\n"

        f"💰 مبلغ: "
        f"{dep['amount']:,} DOGS\n"

        f"🆔 درخواست: {deposit_id}\n\n"

        "📸 رسید:"
    )

    owner_id = get_owner_id()

    if not owner_id:

        await update.message.reply_text(
            "❌ مالک تنظیم نشده است."
        )

        return True

    try:

        if update.message.photo:

            await context.bot.send_photo(

                chat_id=owner_id,

                photo=
                update.message.photo[-1].file_id,

                caption=caption,

                reply_markup=buttons
            )

        elif update.message.document:

            await context.bot.send_document(

                chat_id=owner_id,

                document=
                update.message.document.file_id,

                caption=caption,

                reply_markup=buttons
            )

        else:

            await context.bot.send_message(

                chat_id=owner_id,

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

        "⏳ منتظر تایید باشید.",

        reply_markup=main_keyboard(
            uid
        )
    )

    return True


# =========================================================
# DEPOSIT DECISION
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
            "❌ فقط مالک.",
            show_alert=True
        )

        return

    action, deposit_id = (
        query.data.split(
            ":",
            1
        )
    )

    dep = data["deposits"].get(
        deposit_id
    )

    if not dep:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if dep.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    uid = int(
        dep["user_id"]
    )

    amount = int(
        dep["amount"]
    )

    if action == "dep_ok":

        dep["status"] = "approved"

        dep["approved_at"] = (
            datetime.now().isoformat()
        )

        add_balance(
            uid,
            amount
        )

        save_data()

        try:

            await context.bot.send_message(

                uid,

                "✅ واریز تایید شد.\n\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n\n"

                f"💳 موجودی: "
                f"{get_balance(uid):,} DOGS"
            )

        except Exception:
            pass

        await query.message.reply_text(
            "✅ واریز تایید شد."
        )

    else:

        dep["status"] = "rejected"

        dep["rejected_at"] = (
            datetime.now().isoformat()
        )

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
# WITHDRAW
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
            f"{MIN_WITHDRAW:,} DOGS\n"

            "حداکثر برداشت: ندارد\n\n"

            f"💰 موجودی شما: "
            f"{get_balance(uid):,} DOGS\n\n"

            "❌ موجودی کافی نیست.",

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

        "💰 تعداد برداشت را وارد کنید.",

        reply_markup=back_keyboard()
    )


async def handle_withdraw_amount(
    update,
    context
):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return False

    if state.get("step") != "withdraw_amount":
        return False

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

            "❌ موجودی کافی نیست.\n\n"

            f"💰 موجودی: "
            f"{get_balance(uid):,} DOGS"
        )

        return True

    USER_STATE[uid] = {

        "step": "withdraw_id",

        "amount": amount,
    }

    await update.message.reply_text(

        "✅ مبلغ ثبت شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        "🆔 آیدی عددی دریافت‌کننده "
        "را وارد کنید.\n\n"

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

    if state.get("step") != "withdraw_id":
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

    if target_id <= 0:

        await update.message.reply_text(
            "❌ آیدی صحیح نیست."
        )

        return True

    amount = int(
        state["amount"]
    )

    if not remove_balance(
        uid,
        amount
    ):

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
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
                    "✅ تایید برداشت",
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

            f"💰 مبلغ: "
            f"{amount:,} DOGS\n"

            f"🆔 آیدی دریافت‌کننده: "
            f"{target_id}\n\n"

            f"📋 درخواست: "
            f"{withdraw_id}",

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

        USER_STATE.pop(
            uid,
            None
        )

        await update.message.reply_text(

            "❌ ارسال درخواست به مالک "
            "انجام نشد.\n\n"

            "💰 مبلغ به موجودی شما برگشت."
        )

        return True

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n"

        f"🆔 آیدی: "
        f"{target_id}\n\n"

        "⏳ برای مالک ارسال شد.",

        reply_markup=main_keyboard(
            uid
        )
    )

    return True


# =========================================================
# WITHDRAW DECISION
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
            "❌ فقط مالک.",
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

    if req.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    uid = int(
        req["user_id"]
    )

    amount = int(
        req["amount"]
    )

    if action == "with_ok":

        req["status"] = "approved"

        req["approved_at"] = (
            datetime.now().isoformat()
        )

        save_data()

        try:

            await context.bot.send_message(

                uid,

                "✅ برداشت شما تایید شد.\n\n"

                f"💰 مبلغ: "
                f"{amount:,} DOGS\n"

                f"🆔 آیدی دریافت‌کننده: "
                f"{req['target_id']}"
            )

        except Exception:
            pass

        await query.message.reply_text(
            "✅ برداشت تایید شد."
        )

    else:

        req["status"] = "rejected"

        req["rejected_at"] = (
            datetime.now().isoformat()
        )

        add_balance(
            uid,
            amount
        )

        save_data()

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
# ADMIN PANEL
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

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 شارژ موجودی",
                    callback_data=
                    "admin_charge"
                ),
                InlineKeyboardButton(
                    "➖ کسر موجودی",
                    callback_data=
                    "admin_deduct"
                ),
            ],
            [
                InlineKeyboardButton(
                    "👥 تعداد کاربران",
                    callback_data=
                    "admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data=
                    "admin_transfer_owner"
                )
            ],
        ]
    )

    await update.message.reply_text(

        "⚙️ پنل مدیریت\n\n"

        f"👑 مالک فعلی:\n"
        f"{get_owner_id()}",

        reply_markup=buttons
    )


# =========================================================
# ADMIN CALLBACK
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
            "دیگر پنل مدیریت را نمی‌بیند."
        )

        return


# =========================================================
# ADMIN ACTIONS
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

    # -----------------------------------------------------
    # انتقال مالکیت
    # -----------------------------------------------------

    if step == "admin_transfer_owner":

        try:

            new_owner = int(text)

        except ValueError:

            await update.message.reply_text(

                "❌ آیدی باید عددی باشد.\n\n"

                "مثال:\n"
                "123456789"
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

        ensure_user_id(
            new_owner
        )

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

            f"👑 مالک قبلی: "
            f"{old_owner}\n"

            f"👑 مالک جدید: "
            f"{new_owner}\n\n"

            "⚠️ از این لحظه مالک جدید "
            "دسترسی مدیریت دارد.",

            reply_markup=main_keyboard(
                uid
            )
        )

        return True

    # -----------------------------------------------------
    # شارژ / کسر
    # -----------------------------------------------------

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

        target_id = int(
            parts[0]
        )

        amount = int(
            parts[1].replace(
                ",",
                ""
            )
        )

    except ValueError:

        await update.message.reply_text(
            "❌ اطلاعات صحیح نیست."
        )

        return True

    if target_id <= 0 or amount <= 0:

        await update.message.reply_text(
            "❌ مقدار صحیح نیست."
        )

        return True

    ensure_user_id(
        target_id
    )

    if step == "admin_charge":

        add_balance(
            target_id,
            amount
        )

        result = (

            "✅ موجودی شارژ شد.\n\n"

            f"🆔 آیدی: {target_id}\n"

            f"💰 مبلغ: +{amount:,}\n"

            f"💳 موجودی جدید: "
            f"{get_balance(target_id):,}"
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

            f"🆔 آیدی: {target_id}\n"

            f"💰 مبلغ: -{amount:,}\n"

            f"💳 موجودی جدید: "
            f"{get_balance(target_id):,}"
        )

    USER_STATE.pop(
        uid,
        None
    )

    await update.message.reply_text(

        result,

        reply_markup=main_keyboard(
            uid
        )
    )

    return True


# =========================================================
# SUPPORT
# =========================================================

async def support(update, context):

    await update.message.reply_text(

        "🆘 پشتیبانی\n\n"

        "پیام خود را ارسال کنید."
    )


# =========================================================
# BACK
# =========================================================

async def back(update, context):

    uid = update.effective_user.id

    USER_STATE.pop(
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
# MEDIA
# =========================================================

async def media_router(
    update,
    context
):

    if not update.message:
        return

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
# TEXT ROUTER
# =========================================================

async def text_router(
    update,
    context
):

    if not update.message:
        return

    if not update.effective_user:
        return

    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    text = update.message.text.strip()

    # انتقال با دستور
    if text.startswith("انتقال "):

        await transfer_command(
            update,
            context
        )

        return

    # بازگشت
    if text == "🔙 بازگشت":

        await back(
            update,
            context
        )

        return

    # -----------------------------------------------------
    # State
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

        if step == "deposit_receipt":

            await update.message.reply_text(

                "📸 لطفاً عکس یا فایل رسید "
                "واریز را ارسال کنید."
            )

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

    # -----------------------------------------------------
    # Main menu
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
# ERROR HANDLER
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

    if get_owner_id() == 0:

        raise RuntimeError(
            "OWNER_ID تنظیم نشده یا عددی نیست."
        )

    save_data()

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # تایید / رد واریز
    application.add_handler(
        CallbackQueryHandler(
            deposit_decision,
            pattern=r"^dep_(ok|no):"
        )
    )

    # تایید / رد برداشت
    application.add_handler(
        CallbackQueryHandler(
            withdraw_decision,
            pattern=r"^with_(ok|no):"
        )
    )

    # پنل مدیریت
    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # عکس / فایل رسید
    application.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.Document.ALL,
            media_router
        )
    )

    # پیام‌های متنی
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "================================"
    )

    print(
        "BOT STARTED SUCCESSFULLY"
    )

    print(
        f"OWNER ID: {get_owner_id()}"
    )

    print(
        "================================"
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
