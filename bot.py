import os
import json
import random
import asyncio
import time
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
# تنظیمات
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "توکن_بات_را_اینجا_بگذار")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

DATA_FILE = "data.json"

MIN_GAME = 500
MAX_GAME = 20000

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

# مثال:
# بازی 500
# برنده 900
# مالک 100
WINNER_RATE = 1.8
OWNER_RATE = 0.2


# =========================================================
# داده
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "withdraws": {},
            "deposits": {},
            "games": {},
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("users", {})
        data.setdefault("withdraws", {})
        data.setdefault("deposits", {})
        data.setdefault("games", {})

        return data

    except Exception:
        return {
            "users": {},
            "withdraws": {},
            "deposits": {},
            "games": {},
        }


data = load_data()


def save_data():
    temp = DATA_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp, DATA_FILE)


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
            "balance": 0,
        }

        save_data()


def get_balance(uid):
    uid = str(uid)

    if uid not in data["users"]:
        return 0

    return int(data["users"][uid].get("balance", 0))


def set_balance(uid, amount):
    uid = str(uid)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": int(uid),
            "name": "کاربر",
            "username": "",
            "balance": 0,
        }

    data["users"][uid]["balance"] = max(
        0,
        int(amount)
    )

    save_data()


def add_balance(uid, amount):
    set_balance(
        uid,
        get_balance(uid) + int(amount)
    )


def remove_balance(uid, amount):
    amount = int(amount)

    if get_balance(uid) < amount:
        return False

    set_balance(
        uid,
        get_balance(uid) - amount
    )

    return True


# =========================================================
# مالک
# =========================================================

def is_owner(uid):
    return int(uid) == OWNER_ID


# =========================================================
# کیبورد
# =========================================================

def main_keyboard(uid):
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

    if is_owner(uid):
        rows.append(
            ["⚙️ پنل مدیریت"]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [["🔙 بازگشت"]],
        resize_keyboard=True
    )


# =========================================================
# وضعیت‌های موقت کاربران
# =========================================================

USER_STATE = {}

GAMES = {}


# =========================================================
# START
# =========================================================

async def start(update, context):

    if not update.effective_user:
        return

    user = update.effective_user

    create_user(user)

    await update.message.reply_text(
        "👋 سلام!\n\n"
        "به ربات خوش آمدید.\n\n"
        f"💰 موجودی شما: {get_balance(user.id):,} DOGS\n\n"
        "از منوی زیر استفاده کنید.",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# موجودی
# =========================================================

async def show_balance(update, context):

    uid = update.effective_user.id

    create_user(update.effective_user)

    await update.message.reply_text(
        "💰 موجودی شما\n\n"
        f"{get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(uid)
    )


# =========================================================
# بازی
# =========================================================

async def game_menu(update, context):

    uid = update.effective_user.id

    await update.message.reply_text(
        "🎮 انتخاب بازی\n\n"
        "🎲 تاس\n"
        "🎳 بولینگ\n"
        "🏀 بسکتبال\n\n"
        f"💰 حداقل بازی: {MIN_GAME:,}\n"
        f"💰 حداکثر بازی: {MAX_GAME:,}\n\n"
        "نام بازی را ارسال کنید.",
        reply_markup=ReplyKeyboardMarkup(
            [
                ["🎲 تاس"],
                ["🎳 بولینگ"],
                ["🏀 بسکتبال"],
                ["🔙 بازگشت"],
            ],
            resize_keyboard=True
        )
    )


async def select_game(update, context, game_type):

    uid = update.effective_user.id

    USER_STATE[uid] = {
        "type": "game_amount",
        "game": game_type,
    }

    await update.message.reply_text(
        f"{game_type}\n\n"
        f"حداقل بازی: {MIN_GAME:,}\n"
        f"حداکثر بازی: {MAX_GAME:,}\n\n"
        "💰 مبلغ بازی را وارد کنید:\n\n"
        "مثال:\n"
        "500",
        reply_markup=back_keyboard()
    )


async def game_amount(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if state.get("type") != "game_amount":
        return

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except Exception:
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    if amount < MIN_GAME:
        await update.message.reply_text(
            f"❌ حداقل مبلغ بازی {MIN_GAME:,} DOGS است."
        )
        return

    if amount > MAX_GAME:
        await update.message.reply_text(
            f"❌ حداکثر مبلغ بازی {MAX_GAME:,} DOGS است."
        )
        return

    if get_balance(uid) < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی: {get_balance(uid):,} DOGS"
        )
        return

    game_type = state["game"]

    # پول بازی از بازیکن کم می‌شود
    if not remove_balance(uid, amount):
        await update.message.reply_text(
            "❌ خطا در موجودی."
        )
        return

    game_id = str(
        int(time.time() * 1000)
    ) + str(uid)

    GAMES[game_id] = {
        "id": game_id,
        "creator": uid,
        "amount": amount,
        "game": game_type,
        "created": time.time(),
    }

    USER_STATE.pop(uid, None)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 پیوستن به بازی",
                callback_data=f"join:{game_id}"
            )
        ]
    ])

    await update.message.reply_text(
        "🎮 بازی ساخته شد!\n\n"
        f"🎯 نوع: {game_type}\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "بازیکن دوم می‌تواند وارد بازی شود.",
        reply_markup=keyboard
    )


async def join_game(update, context):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    create_user(q.from_user)

    game_id = q.data.split(":", 1)[1]

    game = GAMES.get(game_id)

    if not game:
        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )
        return

    creator = game["creator"]
    amount = game["amount"]

    if uid == creator:
        await q.answer(
            "❌ نمی‌توانید وارد بازی خودتان شوید.",
            show_alert=True
        )
        return

    if get_balance(uid) < amount:
        await q.answer(
            "❌ موجودی کافی نیست.",
            show_alert=True
        )
        return

    if not remove_balance(uid, amount):
        await q.answer(
            "❌ خطا در موجودی.",
            show_alert=True
        )
        return

    game["joiner"] = uid

    # -----------------------------------------
    # تعیین برنده
    # -----------------------------------------

    winner = random.choice([
        creator,
        uid
    ])

    loser = (
        uid
        if winner == creator
        else creator
    )

    # -----------------------------------------
    # تقسیم:
    #
    # بازی 500
    # برنده 900
    # مالک 100
    # -----------------------------------------

    winner_prize = int(
        amount * WINNER_RATE
    )

    owner_profit = int(
        amount * OWNER_RATE
    )

    # جایزه برنده
    add_balance(
        winner,
        winner_prize
    )

    # سود مالک
    if OWNER_ID != 0:
        add_balance(
            OWNER_ID,
            owner_profit
        )

    winner_name = "برنده"
    loser_name = "بازنده"

    try:
        winner_user = await context.bot.get_chat(winner)
        winner_name = winner_user.first_name or "برنده"
    except Exception:
        pass

    try:
        loser_user = await context.bot.get_chat(loser)
        loser_name = loser_user.first_name or "بازنده"
    except Exception:
        pass

    # -----------------------------------------
    # پیام بازی
    # -----------------------------------------

    await q.edit_message_text(
        "🏆 بازی تمام شد\n\n"
        f"🥇 برنده: {winner_name}\n"
        f"💔 بازنده: {loser_name}\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"🎁 جایزه برنده: {winner_prize:,} DOGS"
    )

    # -----------------------------------------
    # پیام خصوصی برنده
    # -----------------------------------------

    try:
        await context.bot.send_message(
            winner,
            "🎉 تبریک!\n\n"
            "شما برنده بازی شدید.\n\n"
            f"🎮 مبلغ بازی: {amount:,} DOGS\n"
            f"💰 جایزه شما: {winner_prize:,} DOGS\n"
            f"💳 موجودی: {get_balance(winner):,} DOGS"
        )
    except Exception:
        pass

    # -----------------------------------------
    # پیام خصوصی بازنده
    # -----------------------------------------

    try:
        await context.bot.send_message(
            loser,
            "❌ شما بازی را باختید.\n\n"
            f"🎮 مبلغ بازی: {amount:,} DOGS\n"
            f"💳 موجودی: {get_balance(loser):,} DOGS"
        )
    except Exception:
        pass

    del GAMES[game_id]


# =========================================================
# انتقال
# =========================================================

async def transfer_start(update, context):

    uid = update.effective_user.id

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "🔄 برای انتقال باید روی پیام شخص موردنظر ریپلای کنید.\n\n"
            "سپس بنویسید:\n"
            "انتقال 500"
        )
        return

    parts = update.message.text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "انتقال 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ صحیح نیست."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )
        return

    target = update.message.reply_to_message.from_user

    if target.id == uid:
        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return

    if not remove_balance(uid, amount):
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    create_user(target)

    add_balance(
        target.id,
        amount
    )

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {target.first_name}"
    )

    try:
        await context.bot.send_message(
            target.id,
            "💰 واریز دریافت کردید.\n\n"
            f"مبلغ: {amount:,} DOGS\n"
            f"فرستنده: {update.effective_user.first_name}\n\n"
            f"موجودی: {get_balance(target.id):,} DOGS"
        )
    except Exception:
        pass


# =========================================================
# واریز
# =========================================================

async def deposit_start(update, context):

    uid = update.effective_user.id

    USER_STATE[uid] = {
        "type": "deposit_amount"
    }

    await update.message.reply_text(
        "💳 واریز DOGS\n\n"
        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
        "مقدار واریزی را وارد کنید.\n\n"
        "مثال:\n"
        "ULTRA 5000 DOGS @CyyFr",
        reply_markup=back_keyboard()
    )


async def deposit_amount(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if state.get("type") != "deposit_amount":
        return

    text = update.message.text.strip()

    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "ULTRA 5000 DOGS @CyyFr"
        )
        return

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ صحیح نیست."
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."
        )
        return

    address = " ".join(parts[2:])

    deposit_id = (
        f"D{int(time.time() * 1000)}_{uid}"
    )

    data["deposits"][deposit_id] = {
        "id": deposit_id,
        "user_id": uid,
        "amount": amount,
        "text": text,
        "address": address,
        "status": "waiting_receipt",
        "created": datetime.now().isoformat(),
    }

    save_data()

    USER_STATE[uid] = {
        "type": "deposit_receipt",
        "deposit_id": deposit_id,
    }

    await update.message.reply_text(
        "💳 فرصت واریز\n\n"
        f"ULTRA {amount:,} DOGS @CyyFr\n\n"
        f"حداقل واریز {MIN_DEPOSIT:,}\n\n"
        "📸 شات خود یا رسید پیام ارسال کنید.\n\n"
        "بعد از ارسال، رسید برای مالک فرستاده می‌شود."
    )


async def deposit_receipt(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if state.get("type") != "deposit_receipt":
        return

    deposit_id = state["deposit_id"]

    deposit = data["deposits"].get(deposit_id)

    if not deposit:
        USER_STATE.pop(uid, None)
        return

    deposit["status"] = "pending"
    save_data()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید واریز",
                callback_data=f"dep_ok:{deposit_id}"
            ),
            InlineKeyboardButton(
                "❌ رد واریز",
                callback_data=f"dep_no:{deposit_id}"
            )
        ]
    ])

    caption = (
        "💳 درخواست واریز جدید\n\n"
        f"👤 کاربر: {uid}\n"
        f"💰 مبلغ: {deposit['amount']:,} DOGS\n"
        f"🆔 درخواست: {deposit_id}\n\n"
        "رسید/مدرک واریز:"
    )

    owner = OWNER_ID

    try:

        if update.message.photo:

            photo = update.message.photo[-1]

            await context.bot.send_photo(
                owner,
                photo.file_id,
                caption=caption,
                reply_markup=keyboard
            )

        elif update.message.document:

            await context.bot.send_document(
                owner,
                update.message.document.file_id,
                caption=caption,
                reply_markup=keyboard
            )

        else:

            await context.bot.send_message(
                owner,
                caption + "\n\n" + update.message.text,
                reply_markup=keyboard
            )

    except Exception:

        await update.message.reply_text(
            "❌ ارسال رسید به مالک انجام نشد."
        )
        return

    USER_STATE.pop(uid, None)

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ برای مالک ارسال شد.\n"
        "بعد از بررسی نتیجه اعلام می‌شود.",
        reply_markup=main_keyboard(uid)
    )


async def deposit_decision(update, context):

    q = update.callback_query

    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )
        return

    action, deposit_id = q.data.split(":", 1)

    deposit = data["deposits"].get(
        deposit_id
    )

    if not deposit:
        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )
        return

    if deposit["status"] != "pending":
        await q.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )
        return

    uid = deposit["user_id"]
    amount = int(deposit["amount"])

    if action == "dep_ok":

        deposit["status"] = "approved"
        deposit["approved_at"] = datetime.now().isoformat()

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
                f"💳 موجودی: {get_balance(uid):,} DOGS"
            )
        except Exception:
            pass

        try:
            await q.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await q.message.reply_text(
            "✅ واریز تایید شد."
        )

    elif action == "dep_no":

        deposit["status"] = "rejected"
        deposit["rejected_at"] = datetime.now().isoformat()

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "❌ واریز شما رد شد."
            )
        except Exception:
            pass

        try:
            await q.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await q.message.reply_text(
            "❌ واریز رد شد."
        )


# =========================================================
# برداشت
# =========================================================

async def withdraw_start(update, context):

    uid = update.effective_user.id

    if get_balance(uid) < MIN_WITHDRAW:
        await update.message.reply_text(
            "💸 برداشت\n\n"
            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
            f"موجودی شما: {get_balance(uid):,} DOGS\n\n"
            "❌ موجودی کافی نیست.",
            reply_markup=main_keyboard(uid)
        )
        return

    USER_STATE[uid] = {
        "type": "withdraw_amount"
    }

    await update.message.reply_text(
        "💸 برداشت DOGS\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
        "حداکثر برداشت: ندارد\n\n"
        "💰 تعداد DOGS را وارد کنید:",
        reply_markup=back_keyboard()
    )


async def withdraw_amount(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if state.get("type") != "withdraw_amount":
        return

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except Exception:
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید."
        )
        return

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    if amount > get_balance(uid):
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    USER_STATE[uid] = {
        "type": "withdraw_id",
        "amount": amount,
    }

    await update.message.reply_text(
        "✅ مبلغ ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "🆔 حالا آیدی عددی خود را ارسال کنید:\n\n"
        "مثال:\n"
        "123456789"
    )


async def withdraw_user_id(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if state.get("type") != "withdraw_id":
        return

    try:
        target_id = int(
            update.message.text.strip()
        )
    except Exception:
        await update.message.reply_text(
            "❌ آیدی باید عددی باشد."
        )
        return

    if target_id <= 0:
        await update.message.reply_text(
            "❌ آیدی صحیح نیست."
        )
        return

    amount = int(
        state["amount"]
    )

    if get_balance(uid) < amount:
        USER_STATE.pop(uid, None)

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # رزرو مبلغ
    if not remove_balance(uid, amount):
        await update.message.reply_text(
            "❌ خطا در موجودی."
        )
        return

    withdraw_id = (
        f"W{int(time.time() * 1000)}_{uid}"
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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data=f"with_ok:{withdraw_id}"
            ),
            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"with_no:{withdraw_id}"
            )
        ]
    ])

    try:

        await context.bot.send_message(
            OWNER_ID,
            "💸 درخواست برداشت جدید\n\n"
            f"👤 کاربر: {uid}\n"
            f"🆔 آیدی برداشت: {target_id}\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"📋 درخواست: {withdraw_id}",
            reply_markup=keyboard
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
            "❌ ارسال درخواست به مالک انجام نشد.\n"
            "مبلغ برگشت داده شد."
        )

        USER_STATE.pop(uid, None)

        return

    USER_STATE.pop(uid, None)

    # فقط کاربر پیام می‌گیرد
    # هیچ پیام برداشت در گپ ارسال نمی‌شود

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"🆔 آیدی: {target_id}\n\n"
        "⏳ درخواست برای مالک ارسال شد.",
        reply_markup=main_keyboard(uid)
    )


async def withdraw_decision(update, context):

    q = update.callback_query

    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )
        return

    action, withdraw_id = q.data.split(
        ":",
        1
    )

    req = data["withdraws"].get(
        withdraw_id
    )

    if not req:
        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )
        return

    if req["status"] != "pending":
        await q.message.reply_text(
            "⚠️ قبلاً بررسی شده."
        )
        return

    uid = req["user_id"]
    amount = int(req["amount"])

    if action == "with_ok":

        req["status"] = "approved"
        req["approved_at"] = datetime.now().isoformat()

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "✅ برداشت شما توسط مالک تایید شد.\n\n"
                f"💰 مبلغ: {amount:,} DOGS\n"
                f"🆔 آیدی ثبت‌شده: {req['target_id']}"
            )
        except Exception:
            pass

        try:
            await q.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await q.message.reply_text(
            "✅ برداشت تایید شد."
        )

    elif action == "with_no":

        req["status"] = "rejected"
        req["rejected_at"] = datetime.now().isoformat()

        # برگشت مبلغ
        add_balance(
            uid,
            amount
        )

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "❌ برداشت شما رد شد.\n\n"
                f"💰 مبلغ {amount:,} DOGS به موجودی شما برگشت."
            )
        except Exception:
            pass

        try:
            await q.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await q.message.reply_text(
            "❌ برداشت رد شد و مبلغ برگشت."
        )


# =========================================================
# پنل مدیریت
# =========================================================

async def admin_panel(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):
        await update.message.reply_text(
            "❌ دسترسی ندارید."
        )
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💰 شارژ موجودی",
                callback_data="admin_charge"
            ),
            InlineKeyboardButton(
                "➖ کسر موجودی",
                callback_data="admin_deduct"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 تعداد کاربران",
                callback_data="admin_users"
            )
        ]
    ])

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=keyboard
    )


async def admin_callback(update, context):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if not is_owner(uid):
        return

    if q.data == "admin_charge":

        USER_STATE[uid] = {
            "type": "admin_charge"
        }

        await q.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

    elif q.data == "admin_deduct":

        USER_STATE[uid] = {
            "type": "admin_deduct"
        }

        await q.message.reply_text(
            "➖ کسر موجودی\n\n"
            "فرمت:\n"
            "آیدی مبلغ\n\n"
            "مثال:\n"
            "123456789 50000"
        )

    elif q.data == "admin_users":

        count = len(data["users"])

        await q.message.reply_text(
            f"👥 تعداد کاربران: {count:,}"
        )


# =========================================================
# مدیریت شارژ / کسر
# =========================================================

async def admin_amount(update, context):

    uid = update.effective_user.id

    state = USER_STATE.get(uid)

    if not state:
        return

    if not is_owner(uid):
        return

    if state["type"] not in [
        "admin_charge",
        "admin_deduct"
    ]:
        return

    parts = update.message.text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n"
            "آیدی مبلغ"
        )
        return

    try:
        target = int(parts[0])
        amount = int(
            parts[1].replace(",", "")
        )
    except Exception:
        await update.message.reply_text(
            "❌ اطلاعات صحیح نیست."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )
        return

    create_dummy = type(
        "User",
        (),
        {
            "id": target,
            "first_name": "کاربر",
            "username": ""
        }
    )()

    create_user(create_dummy)

    if state["type"] == "admin_charge":

        add_balance(
            target,
            amount
        )

        text = (
            "✅ موجودی شارژ شد.\n\n"
            f"🆔 کاربر: {target}\n"
            f"💰 مبلغ: +{amount:,}\n"
            f"💳 موجودی جدید: {get_balance(target):,}"
        )

    else:

        if not remove_balance(
            target,
            amount
        ):
            await update.message.reply_text(
                "❌ موجودی کاربر کافی نیست."
            )
            USER_STATE.pop(uid, None)
            return

        text = (
            "✅ موجودی کسر شد.\n\n"
            f"🆔 کاربر: {target}\n"
            f"💰 مبلغ: -{amount:,}\n"
            f"💳 موجودی جدید: {get_balance(target):,}"
        )

    USER_STATE.pop(uid, None)

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(uid)
    )


# =========================================================
# پشتیبانی
# =========================================================

async def support(update, context):

    await update.message.reply_text(
        "🆘 پشتیبانی\n\n"
        "پیام خود را ارسال کنید تا بررسی شود."
    )


# =========================================================
# BACK
# =========================================================

async def back(update, context):

    uid = update.effective_user.id

    USER_STATE.pop(uid, None)

    await update.message.reply_text(
        "🔙 برگشت",
        reply_markup=main_keyboard(uid)
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    if not update.effective_user:
        return

    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    text = update.message.text.strip()

    # -------------------------------
    # حالت‌های فعال
    # -------------------------------

    state = USER_STATE.get(uid)

    if state:

        state_type = state.get("type")

        if state_type == "game_amount":
            await game_amount(
                update,
                context
            )
            return

        if state_type == "deposit_amount":
            await deposit_amount(
                update,
                context
            )
            return

        if state_type == "deposit_receipt":

            # رسید عکس / فایل
            if (
                update.message.photo
                or update.message.document
                or update.message.text
            ):
                await deposit_receipt(
                    update,
                    context
                )
                return

        if state_type == "withdraw_amount":
            await withdraw_amount(
                update,
                context
            )
            return

        if state_type == "withdraw_id":
            await withdraw_user_id(
                update,
                context
            )
            return

        if state_type in [
            "admin_charge",
            "admin_deduct"
        ]:
            await admin_amount(
                update,
                context
            )
            return

    # -------------------------------
    # منو
    # -------------------------------

    if text == "💰 موجودی":
        await show_balance(
            update,
            context
        )
        return

    if text == "🎮 بازی":
        await game_menu(
            update,
            context
        )
        return

    if text == "🎲 تاس":
        await select_game(
            update,
            context,
            "🎲 تاس"
        )
        return

    if text == "🎳 بولینگ":
        await select_game(
            update,
            context,
            "🎳 بولینگ"
        )
        return

    if text == "🏀 بسکتبال":
        await select_game(
            update,
            context,
            "🏀 بسکتبال"
        )
        return

    if text == "💳 واریز":
        await deposit_start(
            update,
            context
        )
        return

    if text == "💸 برداشت":
        await withdraw_start(
            update,
            context
        )
        return

    if text == "🔄 انتقال":
        await transfer_start(
            update,
            context
        )
        return

    if text.startswith("انتقال "):
        await transfer_start(
            update,
            context
        )
        return

    if text == "🆘 پشتیبانی":
        await support(
            update,
            context
        )
        return

    if text == "⚙️ پنل مدیریت":
        await admin_panel(
            update,
            context
        )
        return

    if text == "🔙 بازگشت":
        await back(
            update,
            context
        )
        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):

    print(
        "ERROR:",
        context.error
    )

    traceback.print_exc()


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
            "OWNER_ID تنظیم نشده است."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # commands
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # callbacks
    app.add_handler(
        CallbackQueryHandler(
            join_game,
            pattern=r"^join:"
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
            admin_callback,
            pattern=r"^admin_"
        )
    )

    # photo / document برای رسید
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            deposit_receipt
        )
    )

    # text
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    app.add_error_handler(
        error_handler
    )

    print("BOT STARTED")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
