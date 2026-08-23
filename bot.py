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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
except:
    OWNER_ID = 0

REQUIRED_CHANNEL = "@TAK_BE_T"
REQUIRED_GROUP = "@TAK_B_ET"

DATA_FILE = "data.json"

MIN_GAME = 500
MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DEFAULT_REF_REWARD = 50


# =========================================================
# DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_enabled": True,
    "ref_reward": DEFAULT_REF_REWARD,
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}


def fresh_data():
    return json.loads(json.dumps(DEFAULT_DATA))


def load_data():
    if not os.path.exists(DATA_FILE):
        return fresh_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)

        if not isinstance(d, dict):
            return fresh_data()

        default = fresh_data()

        for k, v in default.items():
            if k not in d:
                d[k] = v

        for k in ("users", "deposits", "withdraws", "games"):
            if not isinstance(d.get(k), dict):
                d[k] = {}

        return d

    except Exception as e:
        print("LOAD ERROR:", e)
        return fresh_data()


data = load_data()


def save_data():
    try:
        tmp = DATA_FILE + ".tmp"

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(tmp, DATA_FILE)

    except Exception as e:
        print("SAVE ERROR:", e)


# =========================================================
# OWNER
# =========================================================

def get_owner_id():
    try:
        return int(data.get("owner", OWNER_ID))
    except:
        return OWNER_ID


def is_owner(uid):
    try:
        return int(uid) == get_owner_id()
    except:
        return False


# =========================================================
# BOT ON/OFF
# =========================================================

def bot_enabled():
    return bool(data.get("bot_enabled", True))


def can_use_bot(uid):
    if is_owner(uid):
        return True

    return bot_enabled()


# =========================================================
# USERS
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

    else:
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

    save_data()


def get_user(uid):
    return data["users"].get(str(uid))


def get_balance(uid):
    u = get_user(uid)

    if not u:
        return 0

    try:
        return int(u.get("balance", 0))
    except:
        return 0


def set_balance(uid, amount):
    uid = str(uid)

    if uid not in data["users"]:
        return False

    try:
        amount = int(amount)
    except:
        return False

    if amount < 0:
        amount = 0

    data["users"][uid]["balance"] = amount
    save_data()

    return True


def add_balance(uid, amount):
    try:
        amount = int(amount)
    except:
        return False

    if amount < 0:
        return False

    return set_balance(
        uid,
        get_balance(uid) + amount,
    )


def remove_balance(uid, amount):
    try:
        amount = int(amount)
    except:
        return False

    if amount < 0:
        return False

    current = get_balance(uid)

    if current < amount:
        return False

    return set_balance(
        uid,
        current - amount,
    )


# =========================================================
# STATE
# =========================================================

STATE = {}
LAST_ACTION = {}


def clear_state(uid):
    STATE.pop(uid, None)


def anti_spam(uid, seconds=0.7):
    now = time.time()

    old = LAST_ACTION.get(uid, 0)

    if now - old < seconds:
        return False

    LAST_ACTION[uid] = now

    return True


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):
    rows = [
        ["🎮 بازی", "💰 موجودی"],
        ["💳 واریزی", "💸 برداشت"],
        ["👥 زیرمجموعه", "👤 پروفایل"],
        ["🔄 انتقال", "🎧 پشتیبانی"],
    ]

    if is_owner(uid):
        rows.append(["⚙️ پنل مدیریت"])

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
        [[
            KeyboardButton(
                "📱 ارسال شماره",
                request_contact=True,
            )
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def join_keyboard():
    return InlineKeyboardMarkup([
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
    ])


# =========================================================
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    if bot_enabled():
        power_button = "🔴 خاموش کردن ربات"
        power_callback = "bot_off"
    else:
        power_button = "🟢 روشن کردن ربات"
        power_callback = "bot_on"

    return InlineKeyboardMarkup([
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
                "📊 آمار موجودی",
                callback_data="adm_stats",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎁 جایزه رفرال",
                callback_data="adm_reward",
            ),
        ],
        [
            InlineKeyboardButton(
                power_button,
                callback_data=power_callback,
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
    ])


# =========================================================
# JOIN
# =========================================================

async def check_join(uid, context):
    for chat in (
        REQUIRED_CHANNEL,
        REQUIRED_GROUP,
    ):
        try:
            member = await context.bot.get_chat_member(
                chat,
                uid,
            )

            if member.status in ("left", "kicked"):
                return False

        except Exception as e:
            print("JOIN ERROR:", e)
            return False

    return True


async def require_access(update, context):
    user = update.effective_user

    if not user:
        return False

    uid = user.id

    create_user(user)

    if not can_use_bot(uid):
        await update.effective_message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )
        return False

    if not await check_join(uid, context):
        await update.effective_message.reply_text(
            "🔒 ابتدا در کانال و گپ عضو شوید.",
            reply_markup=join_keyboard(),
        )
        return False

    if not data["users"][str(uid)].get("phone"):
        await update.effective_message.reply_text(
            "📱 ابتدا شماره خود را تأیید کنید.\n\n"
            "⚠️ فقط شماره‌های +98 پذیرفته می‌شوند.",
            reply_markup=phone_keyboard(),
        )
        return False

    return True


# =========================================================
# START
# =========================================================

async def start(update, context):
    user = update.effective_user

    if not user:
        return

    create_user(user)

    # رفرال
    if context.args:
        try:
            ref_id = int(context.args[0])

            if (
                ref_id != user.id
                and str(ref_id) in data["users"]
                and not data["users"][str(user.id)].get("ref_by")
            ):
                data["users"][str(user.id)]["ref_by"] = ref_id

                data["users"][str(ref_id)]["refs"] += 1

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
                        f"💰 موجودی: "
                        f"{get_balance(ref_id):,} DOGS",
                    )
                except:
                    pass

        except:
            pass

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

    if not data["users"][str(user.id)].get("phone"):
        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\n"
            "⚠️ فقط شماره‌های +98 قبول می‌شود.",
            reply_markup=phone_keyboard(),
        )
        return

    if not can_use_bot(user.id):
        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )
        return

    await update.message.reply_text(
        "👋 خوش آمدید.\n\n"
        f"💰 موجودی: "
        f"{get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# PHONE
# =========================================================

def normalize_phone(phone):
    phone = str(phone or "").strip()

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

    return "+" + digits


async def phone_handler(update, context):
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

    data["users"][str(user.id)]["phone"] = phone

    save_data()

    await update.message.reply_text(
        "✅ شماره با موفقیت تأیید شد.",
        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# JOIN CALLBACK
# =========================================================

async def check_join_callback(update, context):
    query = update.callback_query

    try:
        await query.answer()
    except:
        pass

    uid = query.from_user.id

    create_user(query.from_user)

    if not await check_join(uid, context):
        await query.message.reply_text(
            "❌ هنوز عضو کانال و گپ نشده‌اید.",
            reply_markup=join_keyboard(),
        )
        return

    if not data["users"][str(uid)].get("phone"):
        await query.message.reply_text(
            "✅ عضویت تأیید شد.\n\n"
            "📱 حالا شماره خود را ارسال کنید.",
            reply_markup=phone_keyboard(),
        )
        return

    await query.message.reply_text(
        "✅ آماده استفاده هستید.",
        reply_markup=main_keyboard(uid),
    )


# =========================================================
# BALANCE
# =========================================================

async def balance(update, context):
    uid = update.effective_user.id

    await update.message.reply_text(
        "💰 موجودی شما:\n\n"
        f"{get_balance(uid):,} DOGS"
    )


# =========================================================
# PROFILE
# =========================================================

async def profile(update, context):
    uid = update.effective_user.id
    user = data["users"][str(uid)]

    username = user.get("username")

    if username:
        username = "@" + username
    else:
        username = "ندارد"

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {user.get('name', '')}\n"
        f"🔹 یوزرنیم: {username}\n"
        f"📱 شماره: {user.get('phone') or 'ثبت نشده'}\n"
        f"💰 موجودی: {get_balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه: {user.get('refs', 0)}"
    )


# =========================================================
# REFERRAL
# =========================================================

async def referral(update, context):
    uid = update.effective_user.id

    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={uid}"

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    refs = int(
        data["users"][str(uid)].get(
            "refs",
            0,
        )
    )

    await update.message.reply_text(
        "👥 زیرمجموعه\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{link}\n\n"
        f"👥 تعداد رفرال: {refs}\n"
        f"🎁 جایزه هر رفرال: {reward:,} DOGS"
    )


# =========================================================
# GAME
# =========================================================

async def game_command(update, context):
    uid = update.effective_user.id

    if not await require_access(update, context):
        return

    text = update.message.text.strip()

    m = re.fullmatch(
        r"بازی\s+([\d,]+)",
        text,
        re.IGNORECASE,
    )

    if not m:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500"
        )
        return

    amount = int(
        m.group(1).replace(",", "")
    )

    if amount < MIN_GAME:
        await update.message.reply_text(
            "❌ حداقل بازی 500 DOGS است."
        )
        return

    if get_balance(uid) < amount:
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    if not remove_balance(uid, amount):
        return

    game_id = f"G{time.time_ns()}"

    data["games"][game_id] = {
        "creator": uid,
        "amount": amount,
        "status": "waiting",
        "created_at": int(time.time()),
    }

    save_data()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 بازی با دوستان",
                callback_data=f"join_game:{game_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"cancel_game:{game_id}",
            )
        ],
    ])

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else user.first_name
    )

    await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"👤 بازیکن: {username}\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
        "👥 یک نفر می‌تواند وارد این بازی شود.",
        reply_markup=keyboard,
    )


async def game_callback(update, context):
    query = update.callback_query

    try:
        await query.answer()
    except:
        pass

    uid = query.from_user.id

    if not can_use_bot(uid):
        return

    try:
        action, game_id = query.data.split(":", 1)
    except:
        return

    game = data["games"].get(game_id)

    if not game:
        await query.message.reply_text(
            "❌ بازی پیدا نشد."
        )
        return

    if game["status"] != "waiting":
        await query.message.reply_text(
            "❌ این بازی دیگر قابل ورود نیست."
        )
        return

    creator = int(game["creator"])
    amount = int(game["amount"])

    if action == "cancel_game":
        if uid != creator:
            await query.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True,
            )
            return

        game["status"] = "cancelled"

        add_balance(
            creator,
            amount,
        )

        save_data()

        try:
            await query.message.edit_text(
                "❌ بازی لغو شد.\n\n"
                f"💰 {amount:,} DOGS به موجودی برگشت."
            )
        except:
            pass

        return

    if action != "join_game":
        return

    if uid == creator:
        await query.answer(
            "❌ خودتان نمی‌توانید وارد بازی خودتان شوید.",
            show_alert=True,
        )
        return

    if get_balance(uid) < amount:
        await query.answer(
            "❌ موجودی کافی ندارید.",
            show_alert=True,
        )
        return

    if not remove_balance(uid, amount):
        return

    game["status"] = "playing"
    game["opponent"] = uid

    save_data()

    # بازی خودکار
    winner = random.choice([
        creator,
        uid,
    ])

    loser = (
        uid
        if winner == creator
        else creator
    )

    prize = amount * 2

    add_balance(
        winner,
        prize,
    )

    game["status"] = "finished"
    game["winner"] = winner
    game["loser"] = loser

    save_data()

    winner_user = get_user(winner)
    loser_user = get_user(loser)

    winner_name = (
        winner_user.get("name", "")
        if winner_user
        else str(winner)
    )

    loser_name = (
        loser_user.get("name", "")
        if loser_user
        else str(loser)
    )

    try:
        await query.message.edit_text(
            "🎮 بازی شروع شد!\n\n"
            f"👤 بازیکن اول: {creator}\n"
            f"👤 بازیکن دوم: {uid}\n\n"
            "🏁 بازی تمام شد.\n\n"
            f"🏆 برنده: {winner_name}\n"
            f"❌ بازنده: {loser_name}\n"
            f"💰 جایزه: {prize:,} DOGS"
        )
    except:
        pass

    # پیام خصوصی برنده
    try:
        await context.bot.send_message(
            winner,
            "🎉 تبریک!\n\n"
            "🏆 شما برنده بازی شدید.\n"
            f"💰 جایزه: {prize:,} DOGS\n"
            f"💳 موجودی: {get_balance(winner):,} DOGS",
        )
    except:
        pass

    # پیام خصوصی بازنده
    try:
        await context.bot.send_message(
            loser,
            "❌ متأسفانه باختید.\n\n"
            f"💸 مبلغ بازی: {amount:,} DOGS\n"
            f"💳 موجودی: {get_balance(loser):,} DOGS",
        )
    except:
        pass


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(update, context):
    uid = update.effective_user.id

    STATE[uid] = {
        "step": "deposit_amount"
    }

    await update.message.reply_text(
        "💳 واریزی\n\n"
        "💰 حداقل واریز: 5,000 DOGS\n\n"
        "مبلغ را وارد کنید.",
        reply_markup=back_keyboard(),
    )


async def deposit_amount(update, context):
    uid = update.effective_user.id

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            "❌ حداقل واریز 5,000 DOGS است."
        )
        return

    deposit_id = f"D{time.time_ns()}"

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
        "💳 واریزی\n\n"
        f"ULTRA {amount:,} DOGS @CyyFr\n\n"
        "📸 بعد از پرداخت، رسید را ارسال کنید."
    )


async def deposit_receipt(update, context):
    uid = update.effective_user.id

    state = STATE.get(uid, {})

    deposit_id = state.get("id")

    deposit = data["deposits"].get(
        deposit_id
    )

    if not deposit:
        clear_state(uid)
        return

    deposit["status"] = "pending"

    save_data()

    amount = int(deposit["amount"])

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=f"dep_ok:{deposit_id}",
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"dep_no:{deposit_id}",
            ),
        ]
    ])

    caption = (
        "💳 واریزی جدید\n\n"
        f"ULTRA {amount:,} DOGS @CyyFr\n\n"
        f"👤 کاربر: {uid}\n"
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
                caption + "\n\n" + (
                    update.message.text or ""
                ),
                reply_markup=keyboard,
            )

    except Exception as e:
        print("DEPOSIT ERROR:", e)

        await update.message.reply_text(
            "❌ ارسال رسید برای مالک انجام نشد."
        )
        return

    clear_state(uid)

    await update.message.reply_text(
        "✅ رسید برای مالک ارسال شد.\n\n"
        "⏳ منتظر بررسی باشید.",
        reply_markup=main_keyboard(uid),
    )


async def deposit_callback(update, context):
    query = update.callback_query

    if not is_owner(query.from_user.id):
        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True,
        )
        return

    try:
        await query.answer()
    except:
        pass

    action, deposit_id = query.data.split(":", 1)

    dep = data["deposits"].get(deposit_id)

    if not dep or dep["status"] != "pending":
        return

    uid = int(dep["user_id"])
    amount = int(dep["amount"])

    if action == "dep_ok":
        dep["status"] = "approved"

        add_balance(
            uid,
            amount,
        )

        user_text = (
            "✅ واریزی شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی: {get_balance(uid):,} DOGS"
        )

        admin_text = (
            "✅ واریزی تأیید شد."
        )

    else:
        dep["status"] = "rejected"

        user_text = (
            "❌ واریزی شما رد شد."
        )

        admin_text = (
            "❌ واریزی رد شد."
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
    except:
        pass

    try:
        await query.message.edit_reply_markup(
            reply_markup=None
        )
    except:
        pass


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_start(update, context):
    uid = update.effective_user.id

    STATE[uid] = {
        "step": "withdraw_amount"
    }

    await update.message.reply_text(
        "💸 برداشت\n\n"
        "💰 حداقل برداشت: 10,000 DOGS\n\n"
        "مبلغ برداشت را وارد کنید.",
        reply_markup=back_keyboard(),
    )


async def withdraw_amount(update, context):
    uid = update.effective_user.id

    try:
        amount = int(
            update.message.text
            .replace(",", "")
            .strip()
        )
    except:
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
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "👤 آیدی خودتان را وارد کنید.\n\n"
        "مثال:\n"
        "@username"
    )


async def withdraw_target(update, context):
    uid = update.effective_user.id
    target = update.message.text.strip()

    if target.isdigit():
        await update.message.reply_text(
            "❌ آیدی عددی قابل قبول نیست."
        )
        return

    amount = int(
        STATE.get(uid, {}).get(
            "amount",
            0,
        )
    )

    if not remove_balance(uid, amount):
        clear_state(uid)
        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    wid = f"W{time.time_ns()}"

    data["withdraws"][wid] = {
        "user_id": uid,
        "target": target,
        "amount": amount,
        "status": "pending",
        "created_at": int(time.time()),
    }

    save_data()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تأیید برداشت",
                callback_data=f"with_ok:{wid}",
            ),
            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data=f"with_no:{wid}",
            ),
        ]
    ])

    try:
        await context.bot.send_message(
            get_owner_id(),
            "💸 درخواست برداشت\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"👤 آیدی: {target}\n"
            f"🆔 درخواست: {wid}",
            reply_markup=keyboard,
        )
    except:
        add_balance(uid, amount)
        data["withdraws"].pop(wid, None)
        save_data()

        await update.message.reply_text(
            "❌ ارسال به مالک انجام نشد.\n"
            "💰 مبلغ برگشت خورد."
        )
        return

    clear_state(uid)

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        "⏳ منتظر تأیید مالک باشید.",
        reply_markup=main_keyboard(uid),
    )


async def withdraw_callback(update, context):
    query = update.callback_query

    if not is_owner(query.from_user.id):
        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True,
        )
        return

    try:
        await query.answer()
    except:
        pass

    action, wid = query.data.split(":", 1)

    req = data["withdraws"].get(wid)

    if not req or req["status"] != "pending":
        return

    uid = int(req["user_id"])
    amount = int(req["amount"])

    if action == "with_ok":
        req["status"] = "approved"

        admin_text = (
            "✅ برداشت تأیید شد."
        )

        user_text = (
            "✅ برداشت شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS"
        )

    else:
        req["status"] = "rejected"

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            "❌ برداشت رد شد و مبلغ برگشت خورد."
        )

        user_text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ {amount:,} DOGS برگشت خورد."
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
    except:
        pass

    try:
        await query.message.edit_reply_markup(
            reply_markup=None
        )
    except:
        pass


# =========================================================
# TRANSFER
# =========================================================

async def transfer_start(update, context):
    await update.message.reply_text(
        "🔄 انتقال موجودی\n\n"
        "روی پیام کاربر ریپلای کنید و بنویسید:\n\n"
        "انتقال 500",
        reply_markup=back_keyboard(),
    )


async def transfer(update, context):
    msg = update.message
    uid = update.effective_user.id

    if not msg.reply_to_message:
        await msg.reply_text(
            "❌ باید روی پیام کاربر ریپلای کنید."
        )
        return

    parts = msg.text.split()

    if len(parts) != 2:
        await msg.reply_text(
            "❌ فرمت:\nانتقال 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(",", "")
        )
    except:
        await msg.reply_text(
            "❌ مبلغ نامعتبر است."
        )
        return

    receiver = msg.reply_to_message.from_user

    if not receiver or receiver.id == uid:
        await msg.reply_text(
            "❌ گیرنده نامعتبر است."
        )
        return

    create_user(receiver)

    if not remove_balance(uid, amount):
        await msg.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    add_balance(
        receiver.id,
        amount,
    )

    await msg.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {receiver.first_name}\n"
        f"💳 موجودی: {get_balance(uid):,} DOGS"
    )

    try:
        await context.bot.send_message(
            receiver.id,
            "💰 انتقال دریافت کردید.\n\n"
            f"➕ مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی: {get_balance(receiver.id):,} DOGS",
        )
    except:
        pass


# =========================================================
# ADMIN
# =========================================================

async def admin_panel(update, context):
    uid = update.effective_user.id

    if not is_owner(uid):
        await update.message.reply_text(
            "❌ فقط مالک دسترسی دارد."
        )
        return

    total_balance = sum(
        get_balance(int(x))
        for x in data["users"]
    )

    status = (
        "🟢 روشن"
        if bot_enabled()
        else "🔴 خاموش"
    )

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"🤖 وضعیت ربات: {status}\n"
        f"👥 کاربران: {len(data['users']):,}\n"
        f"💰 مجموع موجودی: {total_balance:,} DOGS\n"
        f"🎁 جایزه رفرال: {reward:,} DOGS\n"
        f"👑 مالک: {get_owner_id()}",
        reply_markup=admin_keyboard(),
    )


async def admin_callback(update, context):
    query = update.callback_query
    uid = query.from_user.id

    if not is_owner(uid):
        await query.answer(
            "❌ فقط مالک دسترسی دارد.",
            show_alert=True,
        )
        return

    try:
        await query.answer()
    except:
        pass

    action = query.data

    # روشن کردن
    if action == "bot_on":
        data["bot_enabled"] = True
        save_data()

        await query.message.edit_text(
            "🟢 ربات روشن شد.\n\n"
            "کاربران دوباره می‌توانند از ربات استفاده کنند.",
            reply_markup=admin_keyboard(),
        )
        return

    # خاموش کردن
    if action == "bot_off":
        data["bot_enabled"] = False
        save_data()

        await query.message.edit_text(
            "🔴 ربات خاموش شد.\n\n"
            "کاربران عادی دیگر نمی‌توانند از ربات استفاده کنند.\n"
            "مالک همچنان به پنل مدیریت دسترسی دارد.",
            reply_markup=admin_keyboard(),
        )
        return

    if action == "adm_close":
        await query.message.reply_text(
            "🏠 پنل بسته شد.",
            reply_markup=main_keyboard(uid),
        )
        return

    # آمار
    if action == "adm_stats":
        users = list(data["users"].values())

        balances = [
            int(u.get("balance", 0))
            for u in users
        ]

        total = sum(balances) if balances else 0
        maximum = max(balances) if balances else 0
        minimum = min(balances) if balances else 0

        await query.message.reply_text(
            "📊 آمار موجودی\n\n"
            f"👥 تعداد کاربران: {len(users):,}\n"
            f"💰 مجموع موجودی: {total:,} DOGS\n"
            f"🔝 بیشترین موجودی: {maximum:,} DOGS\n"
            f"🔻 کمترین موجودی: {minimum:,} DOGS\n"
            f"🎁 جایزه رفرال: "
            f"{int(data.get('ref_reward', 50)):,} DOGS"
        )
        return

    # شارژ
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

    # کسر
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

    # جایزه
    if action == "adm_reward":
        STATE[uid] = {
            "step": "admin_reward"
        }

        await query.message.reply_text(
            "🎁 جایزه رفرال\n\n"
            f"مبلغ فعلی: "
            f"{int(data.get('ref_reward', 50)):,} DOGS\n\n"
            "مبلغ جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "100",
            reply_markup=back_keyboard(),
        )
        return

    # انتقال مالکیت
    if action == "adm_owner":
        STATE[uid] = {
            "step": "admin_owner"
        }

        await query.message.reply_text(
            "👑 آیدی عددی مالک جدید را بفرستید.",
            reply_markup=back_keyboard(),
        )
        return


# =========================================================
# ADMIN STATE
# =========================================================

async def admin_state(update, context):
    uid = update.effective_user.id

    state = STATE.get(uid, {})
    step = state.get("step")

    if step not in (
        "admin_add",
        "admin_remove",
        "admin_reward",
        "admin_owner",
    ):
        return False

    if not is_owner(uid):
        return True

    text = update.message.text.strip()

    if step == "admin_reward":
        try:
            reward = int(
                text.replace(",", "")
            )
        except:
            await update.message.reply_text(
                "❌ عدد وارد کنید."
            )
            return True

        if reward < 0:
            return True

        data["ref_reward"] = reward
        save_data()

        clear_state(uid)

        await update.message.reply_text(
            "✅ جایزه رفرال تغییر کرد.\n\n"
            f"🎁 جایزه جدید: {reward:,} DOGS",
            reply_markup=main_keyboard(uid),
        )

        return True

    if step == "admin_owner":
        try:
            new_owner = int(text)
        except:
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        if str(new_owner) not in data["users"]:
            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را استارت نکرده."
            )
            return True

        old_owner = get_owner_id()

        data["owner"] = new_owner
        save_data()

        clear_state(uid)

        await update.message.reply_text(
            "✅ مالکیت منتقل شد.\n\n"
            f"👑 مالک قبلی: {old_owner}\n"
            f"👑 مالک جدید: {new_owner}",
            reply_markup=main_keyboard(uid),
        )

        return True

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n"
            "آیدی مبلغ"
        )
        return True

    try:
        target = int(parts[0])
        amount = int(
            parts[1].replace(",", "")
        )
    except:
        await update.message.reply_text(
            "❌ آیدی و مبلغ باید عدد باشند."
        )
        return True

    if str(target) not in data["users"]:
        await update.message.reply_text(
            "❌ کاربر پیدا نشد."
        )
        return True

    if amount <= 0:
        return True

    if step == "admin_add":
        add_balance(
            target,
            amount,
        )

        text_result = (
            "✅ موجودی شارژ شد.\n\n"
            f"👤 کاربر: {target}\n"
            f"➕ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی: {get_balance(target):,} DOGS"
        )

    else:
        if not remove_balance(
            target,
            amount,
        ):
            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )
            return True

        text_result = (
            "✅ موجودی کسر شد.\n\n"
            f"👤 کاربر: {target}\n"
            f"➖ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی: {get_balance(target):,} DOGS"
        )

    clear_state(uid)

    await update.message.reply_text(
        text_result,
        reply_markup=main_keyboard(uid),
    )

    return True


# =========================================================
# SUPPORT / BACK
# =========================================================

async def support(update, context):
    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "پیام خود را ارسال کنید.",
        reply_markup=back_keyboard(),
    )


async def back(update, context):
    uid = update.effective_user.id

    clear_state(uid)

    await update.message.reply_text(
        "🏠 منوی اصلی",
        reply_markup=main_keyboard(uid),
    )


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):
    if not update.message or not update.message.text:
        return

    user = update.effective_user

    if not user:
        return

    uid = user.id
    text = update.message.text.strip()

    create_user(user)

    if not anti_spam(uid):
        return

    # مالک همیشه پنل را داشته باشد
    if text == "⚙️ پنل مدیریت":
        await admin_panel(update, context)
        return

    # برگشت
    if text == "🔙 برگشت":
        await back(update, context)
        return

    # روشن/خاموش بودن
    if not can_use_bot(uid):
        await update.message.reply_text(
            "🔴 ربات در حال حاضر خاموش است."
        )
        return

    # بازی با دستور
    if re.fullmatch(
        r"بازی\s+[\d,]+",
        text,
        re.IGNORECASE,
    ):
        await game_command(update, context)
        return

    # انتقال
    if text.startswith("انتقال "):
        if await require_access(update, context):
            await transfer(update, context)
        return

    # state مدیر
    if await admin_state(update, context):
        return

    state = STATE.get(uid, {})
    step = state.get("step")

    if step == "game_amount":
        await game_command(update, context)
        return

    if step == "deposit_amount":
        if await require_access(update, context):
            await deposit_amount(update, context)
        return

    if step == "withdraw_amount":
        if await require_access(update, context):
            await withdraw_amount(update, context)
        return

    if step == "withdraw_target":
        if await require_access(update, context):
            await withdraw_target(update, context)
        return

    if step == "deposit_receipt":
        await update.message.reply_text(
            "📸 لطفاً رسید را به صورت عکس یا فایل ارسال کنید."
        )
        return

    # دکمه‌ها
    if text == "🎮 بازی":
        if await require_access(update, context):
            await update.message.reply_text(
                "🎮 برای ساخت بازی بنویسید:\n\n"
                "بازی 500"
            )
        return

    if text == "💰 موجودی":
        await balance(update, context)
        return

    if text == "💳 واریزی":
        if await require_access(update, context):
            await deposit_start(update, context)
        return

    if text == "💸 برداشت":
        if await require_access(update, context):
            await withdraw_start(update, context)
        return

    if text == "👥 زیرمجموعه":
        if await require_access(update, context):
            await referral(update, context)
        return

    if text == "👤 پروفایل":
        if await require_access(update, context):
            await profile(update, context)
        return

    if text == "🔄 انتقال":
        if await require_access(update, context):
            await transfer_start(update, context)
        return

    if text == "🎧 پشتیبانی":
        if await require_access(update, context):
            await support(update, context)
        return

    # موجودی متنی فقط همین یک مسیر را دارد
    if text.lower() in (
        "موجودی",
        "balance",
        "/balance",
    ):
        await balance(update, context)
        return


# =========================================================
# MEDIA
# =========================================================

async def media_handler(update, context):
    uid = update.effective_user.id

    if not can_use_bot(uid):
        return

    state = STATE.get(uid, {})

    if state.get("step") != "deposit_receipt":
        return

    await deposit_receipt(
        update,
        context,
    )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def callback_router(update, context):
    query = update.callback_query

    if not query:
        return

    try:
        value = query.data or ""

        if value == "check_join":
            await check_join_callback(
                update,
                context,
            )
            return

        if value.startswith("join_game:") or value.startswith("cancel_game:"):
            await game_callback(
                update,
                context,
            )
            return

        if value.startswith("dep_ok:") or value.startswith("dep_no:"):
            await deposit_callback(
                update,
                context,
            )
            return

        if value.startswith("with_ok:") or value.startswith("with_no:"):
            await withdraw_callback(
                update,
                context,
            )
            return

        if value.startswith("adm_") or value in (
            "bot_on",
            "bot_off",
        ):
            await admin_callback(
                update,
                context,
            )
            return

        await query.answer()

    except Exception as e:
        print(
            "CALLBACK ERROR:",
            repr(e),
        )


# =========================================================
# COMMANDS
# =========================================================

async def command_start(update, context):
    await start(update, context)


async def command_balance(update, context):
    user = update.effective_user

    create_user(user)

    if not can_use_bot(user.id):
        await update.message.reply_text(
            "🔴 ربات خاموش است."
        )
        return

    await balance(update, context)


async def command_profile(update, context):
    user = update.effective_user

    create_user(user)

    if await require_access(update, context):
        await profile(update, context)


async def command_ref(update, context):
    user = update.effective_user

    create_user(user)

    if await require_access(update, context):
        await referral(update, context)


async def command_admin(update, context):
    await admin_panel(update, context)


# =========================================================
# ERROR
# =========================================================

async def error_handler(update, context):
    print(
        "BOT ERROR:",
        repr(context.error),
    )

    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__,
    )


# =========================================================
# MAIN
# =========================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
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
            command_start,
        )
    )

    app.add_handler(
        CommandHandler(
            "balance",
            command_balance,
        )
    )

    app.add_handler(
        CommandHandler(
            "profile",
            command_profile,
        )
    )

    app.add_handler(
        CommandHandler(
            "ref",
            command_ref,
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            command_admin,
        )
    )

    # callbacks
    app.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # contact
    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_handler,
        )
    )

    # receipt photo
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            media_handler,
        )
    )

    # receipt document
    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            media_handler,
        )
    )

    # text - فقط یک text handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    app.add_error_handler(
        error_handler
    )

    print(
        "================================"
    )
    print(
        "BOT STARTED"
    )
    print(
        "BOT ENABLED:",
        bot_enabled(),
    )
    print(
        "OWNER:",
        get_owner_id(),
    )
    print(
        "================================"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
