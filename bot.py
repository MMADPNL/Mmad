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
except Exception:
    OWNER_ID = 0

REQUIRED_CHANNEL = "@TAK_BE_T"
REQUIRED_GROUP = "@TAK_B_ET"

DATA_FILE = "data.json"

MIN_GAME = 500
GAME_PRIZE_RATE = 1.8
GAME_OWNER_FEE_RATE = 0.2

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DEFAULT_REF_REWARD = 50

# اطلاعات واریز
DEPOSIT_NETWORK = "ULTRA"
DEPOSIT_CURRENCY = "DOGS"
DEPOSIT_ID = "@CyyFr"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_enabled": True,
    "ref_reward": DEFAULT_REF_REWARD,

    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},

    "stats": {
        "approved_deposits": 0,
        "approved_withdraws": 0,
        "ref_paid": 0,
        "games_count": 0,
    },
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

        if not isinstance(
            loaded.get("stats"),
            dict,
        ):
            loaded["stats"] = {}

        loaded["stats"].setdefault(
            "approved_deposits",
            0,
        )
        loaded["stats"].setdefault(
            "approved_withdraws",
            0,
        )
        loaded["stats"].setdefault(
            "ref_paid",
            0,
        )
        loaded["stats"].setdefault(
            "games_count",
            0,
        )

        loaded.setdefault(
            "bot_enabled",
            True,
        )

        loaded.setdefault(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )

        return loaded

    except Exception as error:
        print(
            "LOAD DATA ERROR:",
            error,
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
            error,
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
# BOT STATUS
# =========================================================

def bot_is_enabled():
    return bool(
        data.get(
            "bot_enabled",
            True,
        )
    )


# =========================================================
# USER
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


def clear_state(user_id):
    STATE.pop(
        user_id,
        None,
    )


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
            "💳 واریزی",
            "💸 برداشت",
        ],
        [
            "👥 زیرمجموعه",
            "👤 پروفایل",
        ],
        [
            "🔄 انتقال",
            "🎧 پشتیبانی",
        ],
    ]

    if is_owner(user_id):
        rows.append(
            [
                "⚙️ پنل مدیریت",
            ]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                "🔙 برگشت",
            ]
        ],
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
# JOIN
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
                error,
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

    uid = user.id

    create_user(user)

    if not is_owner(uid):
        if not bot_is_enabled():
            await update.effective_message.reply_text(
                "🔴 ربات موقتاً خاموش است.\n\n"
                "⏳ لطفاً بعداً دوباره تلاش کنید."
            )
            return False

    if not await check_join(
        uid,
        context,
    ):
        await update.effective_message.reply_text(
            "🔒 ابتدا در کانال و گپ عضو شوید.",
            reply_markup=join_keyboard(),
        )

        return False

    user_data = data["users"].get(
        str(uid),
        {},
    )

    if not user_data.get("phone"):
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

    data["stats"][
        "ref_paid"
    ] = int(
        data["stats"].get(
            "ref_paid",
            0,
        )
    ) + reward

    save_data()

    try:
        await context.bot.send_message(
            ref_id,
            "🎉 زیرمجموعه جدید!\n\n"
            f"🎁 جایزه: {reward:,} DOGS\n"
            f"💰 موجودی: "
            f"{get_balance(ref_id):,} DOGS",
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

    if not is_owner(user.id):
        if not bot_is_enabled():
            await update.message.reply_text(
                "🔴 ربات موقتاً خاموش است."
            )
            return

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

    if not user:
        return

    create_user(user)

    info = data["users"][
        str(user.id)
    ]

    username = info.get(
        "username",
        "",
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

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
        f"🆔 شناسه: {user.id}\n"
        f"👤 نام: {info.get('name', '')}\n"
        f"🔹 یوزرنیم: {username_text}\n"
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

    if not user:
        return

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
        "👥 زیرمجموعه‌گیری\n\n"
        f"🔗 لینک دعوت شما:\n"
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

def game_join_keyboard(game_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 بازی با دوستان",
                    callback_data=f"game_join:{game_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ لغو",
                    callback_data=f"game_cancel:{game_id}",
                ),
            ],
        ]
    )


async def game_create(
    update,
    context,
    amount,
):
    user = update.effective_user

    if not user:
        return

    uid = user.id

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

    game_id = f"G{time.time_ns()}"

    data["games"][game_id] = {
        "id": game_id,
        "creator_id": uid,
        "creator_name": user.first_name or "",
        "creator_username": user.username or "",
        "amount": amount,
        "status": "waiting",
        "player2_id": None,
        "player2_name": "",
        "created_at": int(time.time()),
        "message_id": None,
        "chat_id": None,
    }

    save_data()

    msg = await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
        f"👤 سازنده: {user.first_name or 'کاربر'}\n\n"
        "⏳ منتظر بازیکن دوم...",
        reply_markup=game_join_keyboard(
            game_id
        ),
    )

    data["games"][game_id][
        "message_id"
    ] = msg.message_id

    data["games"][game_id][
        "chat_id"
    ] = msg.chat_id

    save_data()


async def game_command_text(
    update,
    context,
):
    text = update.message.text.strip()

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500"
        )
        return

    try:
        amount = int(
            parts[1].replace(
                ",",
                "",
            )
        )
    except Exception:
        await update.message.reply_text(
            "❌ مبلغ باید عدد باشد.\n\n"
            "مثال:\n"
            "بازی 500"
        )
        return

    await game_create(
        update,
        context,
        amount,
    )


async def game_join_callback(
    update,
    context,
):
    query = update.callback_query

    if not query:
        return

    user = query.from_user
    uid = user.id

    create_user(user)

    try:
        await query.answer()
    except Exception:
        pass

    if not is_owner(uid):
        if not bot_is_enabled():
            try:
                await query.answer(
                    "🔴 ربات خاموش است.",
                    show_alert=True,
                )
            except Exception:
                pass
            return

    game_id = query.data.split(
        ":",
        1,
    )[1]

    game = data["games"].get(
        game_id
    )

    if not game:
        try:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    if game.get("status") != "waiting":
        try:
            await query.answer(
                "❌ این بازی قبلاً شروع شده یا تمام شده.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    creator_id = int(
        game["creator_id"]
    )

    if uid == creator_id:
        try:
            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    if not await check_join(
        uid,
        context,
    ):
        try:
            await query.answer(
                "❌ ابتدا عضو کانال و گپ شوید.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    user_data = data["users"].get(
        str(uid),
        {},
    )

    if not user_data.get("phone"):
        try:
            await query.answer(
                "❌ ابتدا شماره خود را تأیید کنید.",
                show_alert=True,
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                uid,
                "📱 ابتدا شماره خود را با ربات تأیید کنید.",
                reply_markup=phone_keyboard(),
            )
        except Exception:
            pass

        return

    amount = int(
        game["amount"]
    )

    if not remove_balance(
        uid,
        amount,
    ):
        try:
            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    game["player2_id"] = uid
    game["player2_name"] = (
        user.first_name or ""
    )
    game["status"] = "playing"

    save_data()

    try:
        await query.message.edit_text(
            "🎮 بازی شروع شد!\n\n"
            f"👤 بازیکن اول: "
            f"{game['creator_name']}\n"
            f"👤 بازیکن دوم: "
            f"{user.first_name or 'کاربر'}\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n\n"
            "⏳ در حال مشخص کردن نتیجه...",
        )
    except Exception:
        pass

    # کمی تأخیر برای طبیعی‌تر شدن نتیجه
    await asyncio_sleep(1)

    winner_id = random.choice(
        [
            creator_id,
            uid,
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
        game["creator_name"]
        if loser_id == creator_id
        else game["player2_name"]
    )

    prize = int(
        amount * GAME_PRIZE_RATE
    )

    owner_fee = int(
        amount * GAME_OWNER_FEE_RATE
    )

    add_balance(
        winner_id,
        prize,
    )

    if (
        get_owner_id()
        not in (
            creator_id,
            uid,
        )
    ):
        add_balance(
            get_owner_id(),
            owner_fee,
        )

    game["status"] = "finished"
    game["winner_id"] = winner_id
    game["loser_id"] = loser_id
    game["finished_at"] = int(
        time.time()
    )

    data["stats"][
        "games_count"
    ] = int(
        data["stats"].get(
            "games_count",
            0,
        )
    ) + 1

    save_data()

    result = (
        "🏆 بازی تمام شد!\n\n"
        f"👤 بازیکن اول: "
        f"{game['creator_name']}\n"
        f"👤 بازیکن دوم: "
        f"{game['player2_name']}\n\n"
        f"🏆 برنده: {winner_name}\n"
        f"❌ بازنده: {loser_name}\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"🏆 جایزه برنده: {prize:,} DOGS\n"
        f"👑 سهم مالک: {owner_fee:,} DOGS"
    )

    try:
        await query.message.edit_text(
            result
        )
    except Exception:
        try:
            await context.bot.send_message(
                query.message.chat_id,
                result,
            )
        except Exception:
            pass

    winner_private = (
        "🏆 شما برنده شدید!\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"🎁 جایزه: {prize:,} DOGS\n"
        f"💰 موجودی شما: "
        f"{get_balance(winner_id):,} DOGS"
    )

    loser_private = (
        "❌ شما در بازی باختید.\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n"
        f"💰 موجودی شما: "
        f"{get_balance(loser_id):,} DOGS"
    )

    try:
        await context.bot.send_message(
            winner_id,
            winner_private,
        )
    except Exception as error:
        print(
            "WINNER PM ERROR:",
            error,
        )

    try:
        await context.bot.send_message(
            loser_id,
            loser_private,
        )
    except Exception as error:
        print(
            "LOSER PM ERROR:",
            error,
        )


async def asyncio_sleep(seconds):
    import asyncio
    await asyncio.sleep(seconds)


async def game_cancel_callback(
    update,
    context,
):
    query = update.callback_query

    if not query:
        return

    uid = query.from_user.id

    game_id = query.data.split(
        ":",
        1,
    )[1]

    game = data["games"].get(
        game_id
    )

    if not game:
        try:
            await query.answer(
                "❌ بازی پیدا نشد.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    creator_id = int(
        game["creator_id"]
    )

    if uid != creator_id:
        try:
            await query.answer(
                "❌ فقط سازنده بازی می‌تواند آن را لغو کند.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    if game.get("status") != "waiting":
        try:
            await query.answer(
                "❌ این بازی دیگر قابل لغو نیست.",
                show_alert=True,
            )
        except Exception:
            pass
        return

    amount = int(
        game["amount"]
    )

    add_balance(
        creator_id,
        amount,
    )

    game["status"] = "cancelled"

    save_data()

    try:
        await query.answer(
            "✅ بازی لغو شد.",
            show_alert=True,
        )
    except Exception:
        pass

    try:
        await query.message.edit_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {amount:,} DOGS "
            "به موجودی سازنده برگشت."
        )
    except Exception:
        pass


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_start(
    update,
    context,
):
    uid = update.effective_user.id

    STATE[uid] = {
        "step": "deposit_amount",
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
    except Exception:
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

    data["deposits"][
        deposit_id
    ] = {
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
        f"{DEPOSIT_NETWORK} "
        f"{amount:,} "
        f"{DEPOSIT_CURRENCY} "
        f"{DEPOSIT_ID}\n\n"
        "📋 متن بالا را برای واریز استفاده کنید.\n"
        "بعد از پرداخت، رسید را همینجا ارسال کنید."
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

    deposit["status"] = "pending"

    save_data()

    keyboard = InlineKeyboardMarkup(
        [
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
        ]
    )

    amount = int(
        deposit["amount"]
    )

    caption = (
        "💳 واریز جدید\n\n"
        f"👤 کاربر: {uid}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
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
        action, deposit_id = query.data.split(
            ":",
            1,
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

        data["stats"][
            "approved_deposits"
        ] = int(
            data["stats"].get(
                "approved_deposits",
                0,
            )
        ) + amount

        admin_text = (
            "✅ واریز تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS"
        )

        user_text = (
            "✅ واریز شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی: "
            f"{get_balance(uid):,} DOGS"
        )

    else:
        deposit["status"] = "rejected"

        admin_text = (
            "❌ واریز رد شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS"
        )

        user_text = (
            "❌ واریز شما رد شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS"
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
        "step": "withdraw_amount",
    }

    await update.message.reply_text(
        "💸 برداشت\n\n"
        "💰 حداقل برداشت: 10,000 DOGS\n"
        "♾️ حداکثر: ندارد\n\n"
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
    except Exception:
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
        f"💰 مبلغ برداشت: {amount:,} DOGS\n\n"
        "👤 حالا آیدی خودتان را وارد کنید.\n\n"
        "مثال:\n"
        "@username\n\n"
        "⚠️ آیدی عددی یا آدرس کیف پول وارد نکنید."
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
            "آیدی را مثل @username وارد کنید."
        )
        return

    if len(target_id) > 100:
        await update.message.reply_text(
            "❌ آیدی بیش از حد طولانی است."
        )
        return

    amount = int(
        STATE.get(uid, {}).get(
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
        clear_state(uid)

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    withdraw_id = f"W{time.time_ns()}"

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
                    callback_data=f"with_ok:{withdraw_id}",
                ),
                InlineKeyboardButton(
                    "❌ رد برداشت",
                    callback_data=f"with_no:{withdraw_id}",
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
            f"👤 آیدی: {target_id}\n"
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
        action, withdraw_id = query.data.split(
            ":",
            1,
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

        data["stats"][
            "approved_withdraws"
        ] = int(
            data["stats"].get(
                "approved_withdraws",
                0,
            )
        ) + amount

        admin_text = (
            "✅ برداشت تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"👤 آیدی: {target_id}"
        )

        user_text = (
            "✅ برداشت شما تأیید شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS\n"
            f"👤 آیدی: {target_id}"
        )

    else:
        request["status"] = "rejected"

        add_balance(
            uid,
            amount,
        )

        admin_text = (
            "❌ برداشت رد شد.\n\n"
            f"💰 مبلغ: {amount:,} DOGS"
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

async def transfer_start(
    update,
    context,
):
    await update.message.reply_text(
        "🔄 انتقال موجودی\n\n"
        "روی پیام کاربر ریپلای کنید و بنویسید:\n\n"
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

    parts = message.text.strip().split()

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
    except Exception:
        await message.reply_text(
            "❌ مبلغ باید عدد باشد."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ مبلغ باید بیشتر از صفر باشد."
        )
        return

    receiver = (
        message.reply_to_message
        .from_user
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
# ADMIN KEYBOARD
# =========================================================

def admin_keyboard():
    enabled = bot_is_enabled()

    status_button = (
        "🔴 خاموش کردن ربات"
        if enabled
        else "🟢 روشن کردن ربات"
    )

    status_callback = (
        "adm_bot_off"
        if enabled
        else "adm_bot_on"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    status_button,
                    callback_data=status_callback,
                ),
            ],
            [
                InlineKeyboardButton(
                    "📊 آمار موجودی‌ها",
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
            "❌ فقط مالک ربات دسترسی دارد."
        )
        return

    reward = int(
        data.get(
            "ref_reward",
            DEFAULT_REF_REWARD,
        )
    )

    status = (
        "🟢 روشن"
        if bot_is_enabled()
        else "🔴 خاموش"
    )

    total_balance = sum(
        get_balance(uid2)
        for uid2 in data["users"]
    )

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"🤖 وضعیت ربات: {status}\n"
        f"👑 مالک: {get_owner_id()}\n"
        f"👥 کاربران: "
        f"{len(data['users']):,}\n"
        f"💰 مجموع موجودی: "
        f"{total_balance:,} DOGS\n"
        f"🎁 جایزه رفرال: "
        f"{reward:,} DOGS\n\n"
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

    # روشن
    if action == "adm_bot_on":
        data["bot_enabled"] = True

        save_data()

        await query.message.reply_text(
            "🟢 ربات روشن شد."
        )

        try:
            await query.message.edit_reply_markup(
                reply_markup=admin_keyboard()
            )
        except Exception:
            pass

        return

    # خاموش
    if action == "adm_bot_off":
        data["bot_enabled"] = False

        save_data()

        await query.message.reply_text(
            "🔴 ربات خاموش شد.\n\n"
            "مالک همچنان به پنل مدیریت دسترسی دارد."
        )

        try:
            await query.message.edit_reply_markup(
                reply_markup=admin_keyboard()
            )
        except Exception:
            pass

        return

    # بستن
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

    # آمار
    if action == "adm_stats":
        total_balance = sum(
            get_balance(uid2)
            for uid2 in data["users"]
        )

        rich_users = 0
        zero_users = 0

        max_balance = 0
        max_user = None

        for user_id, info in data[
            "users"
        ].items():

            balance = int(
                info.get(
                    "balance",
                    0,
                )
            )

            if balance > 0:
                rich_users += 1
            else:
                zero_users += 1

            if balance > max_balance:
                max_balance = balance
                max_user = info

        if max_user:
            max_name = max_user.get(
                "name",
                "",
            )

            max_id = max_user.get(
                "id",
                "",
            )
        else:
            max_name = "ندارد"
            max_id = "ندارد"

        stats = data.get(
            "stats",
            {},
        )

        await query.message.reply_text(
            "📊 آمار موجودی‌ها\n\n"
            f"👥 تعداد کاربران: "
            f"{len(data['users']):,}\n"
            f"🟢 موجودی‌دارها: "
            f"{rich_users:,}\n"
            f"⚪ بدون موجودی: "
            f"{zero_users:,}\n\n"
            f"💰 مجموع موجودی کاربران:\n"
            f"{total_balance:,} DOGS\n\n"
            f"💳 مجموع واریزی تأییدشده:\n"
            f"{int(stats.get('approved_deposits', 0)):,} DOGS\n\n"
            f"💸 مجموع برداشت تأییدشده:\n"
            f"{int(stats.get('approved_withdraws', 0)):,} DOGS\n\n"
            f"🎁 مجموع جایزه رفرال:\n"
            f"{int(stats.get('ref_paid', 0)):,} DOGS\n\n"
            f"🎮 تعداد بازی‌ها:\n"
            f"{int(stats.get('games_count', 0)):,}\n\n"
            f"🏆 بیشترین موجودی:\n"
            f"{max_name} ({max_id})\n"
            f"{max_balance:,} DOGS"
        )

        return

    # کاربران
    if action == "adm_users":
        await query.message.reply_text(
            "👥 کاربران\n\n"
            f"تعداد کاربران ثبت‌شده: "
            f"{len(data['users']):,}"
        )

        return

    # شارژ
    if action == "adm_add":
        STATE[uid] = {
            "step": "admin_add",
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
            "step": "admin_remove",
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
            "step": "admin_reward",
        }

        current = int(
            data.get(
                "ref_reward",
                DEFAULT_REF_REWARD,
            )
        )

        await query.message.reply_text(
            "🎁 تنظیم جایزه رفرال\n\n"
            f"جایزه فعلی: {current:,} DOGS\n\n"
            "مبلغ جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "100",
            reply_markup=back_keyboard(),
        )

        return

    # انتقال مالکیت
    if action == "adm_owner":
        STATE[uid] = {
            "step": "admin_owner",
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

    valid_steps = (
        "admin_add",
        "admin_remove",
        "admin_reward",
        "admin_owner",
    )

    if step not in valid_steps:
        return False

    if not is_owner(uid):
        return True

    text = update.message.text.strip()

    # جایزه
    if step == "admin_reward":
        try:
            reward = int(
                text.replace(
                    ",",
                    "",
                )
            )
        except Exception:
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
            f"🎁 جایزه هر رفرال: "
            f"{reward:,} DOGS",
            reply_markup=main_keyboard(uid),
        )

        return True

    # مالک
    if step == "admin_owner":
        try:
            new_owner = int(text)
        except Exception:
            await update.message.reply_text(
                "❌ آیدی باید عددی باشد."
            )
            return True

        if new_owner <= 0:
            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )
            return True

        if str(new_owner) not in data[
            "users"
        ]:
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

    # شارژ / کسر
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
    except Exception:
        await update.message.reply_text(
            "❌ آیدی و مبلغ باید عدد باشند."
        )
        return True

    if target_id <= 0 or amount <= 0:
        await update.message.reply_text(
            "❌ اطلاعات نامعتبر است."
        )
        return True

    if str(target_id) not in data[
        "users"
    ]:
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
            f"➕ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} DOGS"
        )

    else:
        if not remove_balance(
            target_id,
            amount,
        ):
            await update.message.reply_text(
                "❌ موجودی کاربر کافی نیست."
            )
            return True

        result = (
            "✅ موجودی کسر شد.\n\n"
            f"👤 کاربر: {target_id}\n"
            f"➖ مبلغ: {amount:,} DOGS\n"
            f"💰 موجودی جدید: "
            f"{get_balance(target_id):,} DOGS"
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
# MEDIA
# =========================================================

async def media_router(
    update,
    context,
):
    uid = update.effective_user.id

    step = STATE.get(
        uid,
        {},
    ).get("step")

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
    text = update.message.text.strip()

    create_user(user)

    if not anti_spam(uid):
        return

    # برگشت
    if text == "🔙 برگشت":
        await go_back(
            update,
            context,
        )
        return

    # =====================================================
    # GAME TEXT
    # بازی 500
    # =====================================================

    if text.startswith("بازی "):
        if not await require_access(
            update,
            context,
        ):
            return

        await game_command_text(
            update,
            context,
        )

        return

    # =====================================================
    # TRANSFER
    # =====================================================

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

    # =====================================================
    # BALANCE
    # فقط یک مسیر برای "موجودی"
    # =====================================================

    if text in (
        "موجودی",
        "💰 موجودی",
    ):
        await balance_message(
            update,
            context,
        )
        return

    # =====================================================
    # ADMIN STATE
    # =====================================================

    if await admin_state(
        update,
        context,
    ):
        return

    # =====================================================
    # STATE
    # =====================================================

    state = STATE.get(
        uid,
        {},
    )

    step = state.get(
        "step"
    )

    if step == "game_amount":
        clear_state(uid)

        await update.message.reply_text(
            "❌ برای بازی باید داخل گپ بنویسید:\n\n"
            "بازی 500"
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

    # =====================================================
    # MAIN BUTTONS
    # =====================================================

    if text == "🎮 بازی":
        if not await require_access(
            update,
            context,
        ):
            return

        await update.message.reply_text(
            "🎮 بازی داخل گپ انجام می‌شود.\n\n"
            "مثال:\n"
            "بازی 500"
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


async def command_balance(
    update,
    context,
):
    try:
        await balance_command(
            update,
            context,
        )
    except Exception as error:
        print(
            "BALANCE ERROR:",
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
        value = query.data or ""

        # عضویت
        if value == "check_join":
            await check_join_callback(
                update,
                context,
            )
            return

        # بازی
        if value.startswith(
            "game_join:"
        ):
            await game_join_callback(
                update,
                context,
            )
            return

        if value.startswith(
            "game_cancel:"
        ):
            await game_cancel_callback(
                update,
                context,
            )
            return

        # واریز
        if (
            value.startswith("dep_ok:")
            or value.startswith("dep_no:")
        ):
            await deposit_callback(
                update,
                context,
            )
            return

        # برداشت
        if (
            value.startswith("with_ok:")
            or value.startswith("with_no:")
        ):
            await withdraw_callback(
                update,
                context,
            )
            return

        # مدیریت
        if value.startswith(
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


# =========================================================
# ERROR
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

    # =====================================================
    # COMMANDS
    # =====================================================

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

    # =====================================================
    # CALLBACK
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    # =====================================================
    # CONTACT
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    # =====================================================
    # PHOTO
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_handler,
        )
    )

    # =====================================================
    # DOCUMENT
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler,
        )
    )

    # =====================================================
    # TEXT
    # فقط یک Text Handler
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    # =====================================================
    # ERROR
    # =====================================================

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
