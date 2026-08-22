import os
import json
import time
import random
import traceback
import asyncio
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

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_B_ET"

ULTRA_ID = "@CyyFr"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "data.json"

# =========================================================
# داده اولیه
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_status": True,
    "ref_reward": 50,
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}


def load_data():
    default = json.loads(json.dumps(DEFAULT_DATA))

    try:
        if not os.path.exists(DATA_FILE):
            return default

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            result = json.load(f)

        if not isinstance(result, dict):
            return default

        for key, value in default.items():
            if key not in result:
                result[key] = value

        return result

    except Exception:
        traceback.print_exc()
        return default


data = load_data()


def save_data():
    try:
        tmp = DATA_FILE + ".tmp"

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(tmp, DATA_FILE)

    except Exception:
        traceback.print_exc()


# =========================================================
# وضعیت‌ها
# =========================================================

CLICK = {}

DEPOSIT_DATA = {}
WITHDRAW_DATA = {}
TRANSFER_DATA = {}
OWNER_STATE = {}

GAMES = {}


# =========================================================
# ضد اسپم
# =========================================================

def anti_spam(uid, seconds=1.5):
    now = time.time()
    key = str(uid)

    old = CLICK.get(key, 0)

    if now - old < seconds:
        return False

    CLICK[key] = now
    return True


# =========================================================
# کاربران
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


def get_balance(uid):
    try:
        return int(
            data["users"][str(uid)].get("balance", 0)
        )
    except Exception:
        return 0


def add_balance(uid, amount):
    uid = str(uid)

    if uid not in data["users"]:
        return False

    try:
        amount = int(amount)
    except Exception:
        return False

    data["users"][uid]["balance"] = (
        get_balance(uid) + amount
    )

    if data["users"][uid]["balance"] < 0:
        data["users"][uid]["balance"] = 0

    save_data()
    return True


def remove_balance(uid, amount):
    try:
        amount = int(amount)
    except Exception:
        return False

    if amount < 0:
        return False

    if get_balance(uid) < amount:
        return False

    return add_balance(uid, -amount)


def is_owner(uid):
    try:
        return int(uid) == int(
            data.get("owner", OWNER_ID)
        )
    except Exception:
        return False


# =========================================================
# کیبورد اصلی
# =========================================================

def main_keyboard(uid):
    buttons = [
        ["💳 واریزی", "💰 برداشت"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
        ["👤 پروفایل", "👥 انتقال"],
        ["🎮 بازی"],
    ]

    if is_owner(uid):
        buttons.append(["⚙️ پنل مدیریت"])

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
# عضویت اجباری
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

        # اگر ربات دسترسی بررسی عضویت نداشت
        # کاربر را عبور نمی‌دهیم.
        return False


# =========================================================
# شماره
# =========================================================

def clean_phone(phone):
    if not phone:
        return None

    phone = str(phone)
    phone = phone.replace(" ", "")
    phone = phone.replace("-", "")
    phone = phone.replace("(", "")
    phone = phone.replace(")", "")

    if phone.startswith("0098"):
        phone = "+" + phone[2:]

    elif phone.startswith("98"):
        phone = "+" + phone

    if not phone.startswith("+98"):
        return None

    if len(phone) < 12:
        return None

    return phone


async def phone_receive(update, context):
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
            "❌ فقط شماره ایران با +98 قبول است."
        )
        return

    create_user(user)

    data["users"][str(user.id)]["phone"] = phone

    save_data()

    await update.message.reply_text(
        "✅ شماره شما با موفقیت تایید شد.",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# زیرمجموعه
# =========================================================

async def process_referral(update, context):
    if not context.args:
        return

    try:
        ref_id = int(context.args[0])
    except Exception:
        return

    user = update.effective_user

    if ref_id == user.id:
        return

    create_user(user)

    uid = str(user.id)

    if data["users"][uid].get("ref_by"):
        return

    if str(ref_id) not in data["users"]:
        return

    data["users"][uid]["ref_by"] = ref_id

    data["users"][str(ref_id)]["refs"] = int(
        data["users"][str(ref_id)].get("refs", 0)
    ) + 1

    reward = int(
        data.get("ref_reward", 50)
    )

    add_balance(ref_id, reward)

    save_data()


async def referral_menu(update, context):
    user = update.effective_user

    create_user(user)

    bot = await context.bot.get_me()

    link = (
        f"https://t.me/{bot.username}"
        f"?start={user.id}"
    )

    refs = int(
        data["users"][str(user.id)].get(
            "refs",
            0
        )
    )

    reward = int(
        data.get("ref_reward", 50)
    )

    await update.message.reply_text(
        "👥 سیستم زیرمجموعه\n\n"
        f"🔗 لینک دعوت شما:\n{link}\n\n"
        f"👥 تعداد زیرمجموعه: {refs}\n"
        f"💰 جایزه هر نفر: {reward:,} DOGS",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# START
# =========================================================

async def start(update, context):
    user = update.effective_user

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
            "❌ برای استفاده از ربات ابتدا عضو کانال و گپ شوید.",
            reply_markup=join_keyboard()
        )
        return

    if not data["users"][str(user.id)].get("phone"):
        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\n"
            "فقط شماره ایران با +98 قبول است.",
            reply_markup=phone_keyboard()
        )
        return

    await update.message.reply_text(
        "✅ ورود موفق بود.\n\n"
        f"💰 موجودی: {get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# بررسی عضویت
# =========================================================

async def check_join_callback(update, context):
    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if await check_join(uid, context):

        create_user(q.from_user)

        if not data["users"][str(uid)].get("phone"):

            try:
                await q.message.delete()
            except Exception:
                pass

            await context.bot.send_message(
                uid,
                "📱 شماره خود را ارسال کنید.\n\n"
                "فقط شماره ایران با +98 قبول است.",
                reply_markup=phone_keyboard()
            )

        else:

            await q.message.reply_text(
                "✅ عضویت شما تایید شد.",
                reply_markup=main_keyboard(uid)
            )

    else:

        await q.answer(
            "❌ هنوز عضو کانال و گپ نشده‌اید.",
            show_alert=True
        )


# =========================================================
# واریز
# =========================================================

async def deposit_start(update, context):
    uid = update.effective_user.id

    create_user(update.effective_user)

    if not anti_spam(uid):
        return

    DEPOSIT_DATA[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(
        "💳 واریز ULTRA\n\n"
        f"حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"
        "مقدار DOGS را وارد کنید:",
        reply_markup=back_keyboard()
    )


async def deposit_amount(update, context):
    uid = update.effective_user.id

    state = DEPOSIT_DATA.get(uid)

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
            "❌ مقدار فقط باید عدد باشد."
        )
        return

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."
        )
        return

    state["amount"] = amount
    state["step"] = "receipt"

    await update.message.reply_text(
        "💳 فرصت واریز:\n\n"
        f"ULTRA {amount:,} DOGS {ULTRA_ID}\n\n"
        f"حداقل واریز {MIN_DEPOSIT:,} DOGS\n\n"
        "📸 شات خود یا رسید پیام را ارسال کنید.\n\n"
        "⏳ بعد از ارسال رسید، درخواست سریعاً برای مالک ارسال می‌شود."
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
            )
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
        f"💰 مبلغ: {req['amount']:,} DOGS\n"
        f"💳 روش: ULTRA\n\n"
        "لطفاً بررسی کنید."
    )

    markup = deposit_buttons(req_id)

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


async def deposit_receipt(update, context):
    uid = update.effective_user.id

    state = DEPOSIT_DATA.get(uid)

    if not state:
        return

    if state.get("step") != "receipt":
        return

    amount = int(
        state["amount"]
    )

    req_id = (
        f"D{int(time.time()*1000)}"
        f"_{uid}"
    )

    if update.message.photo:

        req = {
            "request_id": req_id,
            "user_id": uid,
            "amount": amount,
            "type": "ULTRA",
            "kind": "photo",
            "content": update.message.photo[-1].file_id,
            "status": "pending",
            "created": datetime.now().isoformat()
        }

    elif update.message.text:

        req = {
            "request_id": req_id,
            "user_id": uid,
            "amount": amount,
            "type": "ULTRA",
            "kind": "text",
            "content": update.message.text.strip(),
            "status": "pending",
            "created": datetime.now().isoformat()
        }

    else:

        await update.message.reply_text(
            "❌ لطفاً عکس رسید یا متن/لینک رسید را ارسال کنید."
        )
        return

    data["deposits"][req_id] = req

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

    DEPOSIT_DATA.pop(uid, None)

    await update.message.reply_text(
        "✅ رسید شما ارسال شد.\n"
        "⏳ منتظر تایید مالک باشید.",
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

    try:
        action, req_id = q.data.split(
            ":",
            1
        )
    except Exception:
        return

    req = data["deposits"].get(req_id)

    if not req:
        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )
        return

    if req.get("status") != "pending":
        await q.message.reply_text(
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
                f"💰 مبلغ: {req['amount']:,} DOGS\n"
                f"💳 موجودی جدید: {get_balance(uid):,} DOGS"
            )
        except Exception:
            pass

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(
            "✅ واریز تایید شد."
        )

    else:

        req["status"] = "rejected"

        save_data()

        try:
            await context.bot.send_message(
                uid,
                "❌ رسید واریز شما رد شد."
            )
        except Exception:
            pass

        await q.message.edit_reply_markup(
            reply_markup=None
        )

        await q.message.reply_text(
            "❌ واریز رد شد."
        )


# =========================================================
# برداشت
# =========================================================

async def withdraw_start(update, context):
    uid = update.effective_user.id

    create_user(update.effective_user)

    balance = get_balance(uid)

    if balance < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است.\n\n"
            f"💰 موجودی شما: {balance:,} DOGS"
        )
        return

    WITHDRAW_DATA[uid] = {
        "step": "amount"
    }

    await update.message.reply_text(
        "💰 برداشت DOGS\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,}\n"
        f"موجودی: {balance:,}\n\n"
        "مقدار برداشت را ارسال کنید:",
        reply_markup=back_keyboard()
    )


async def withdraw_amount(update, context):
    uid = update.effective_user.id

    state = WITHDRAW_DATA.get(uid)

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
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    state["amount"] = amount
    state["step"] = "wallet"

    await update.message.reply_text(
        "📥 آدرس ولت مقصد را ارسال کنید:"
    )


async def withdraw_wallet(update, context):
    uid = update.effective_user.id

    state = WITHDRAW_DATA.get(uid)

    if not state:
        return

    if state.get("step") != "wallet":
        return

    wallet = update.message.text.strip()

    if len(wallet) < 10:

        await update.message.reply_text(
            "❌ آدرس ولت نامعتبر است."
        )
        return

    amount = int(state["amount"])

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        WITHDRAW_DATA.pop(uid, None)
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

    data["withdraws"][req_id] = req

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
            )
        ]
    ])

    try:

        await context.bot.send_message(
            data.get("owner", OWNER_ID),
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

        data["withdraws"].pop(
            req_id,
            None
        )

        save_data()

        await update.message.reply_text(
            "❌ ارسال درخواست به مالک انجام نشد؛ مبلغ به موجودی برگشت."
        )
        return

    WITHDRAW_DATA.pop(uid, None)

    await update.message.reply_text(
        "✅ درخواست برداشت ارسال شد.\n"
        "⏳ مبلغ تا تعیین تکلیف درخواست رزرو شده.",
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

    try:
        action, req_id = q.data.split(
            ":",
            1
        )
    except Exception:
        return

    req = data["withdraws"].get(req_id)

    if not req:
        await q.message.reply_text(
            "❌ درخواست پیدا نشد."
        )
        return

    if req.get("status") != "pending":
        await q.message.reply_text(
            "⚠️ قبلاً بررسی شده."
        )
        return

    uid = req["user_id"]

    if action == "with_ok":

        req["status"] = "approved"

        text = (
            "✅ برداشت شما تایید شد.\n\n"
            f"💰 مبلغ: {req['amount']:,} DOGS\n"
            "پرداخت طبق ولت ثبت‌شده انجام می‌شود."
        )

        owner_text = "✅ برداشت تایید شد."

    else:

        req["status"] = "rejected"

        add_balance(
            uid,
            req["amount"]
        )

        text = (
            "❌ برداشت شما رد شد.\n\n"
            f"💰 مبلغ {req['amount']:,} DOGS "
            "به موجودی شما برگشت."
        )

        owner_text = "❌ برداشت رد شد و مبلغ برگشت."

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
# انتقال
# =========================================================

def find_user_by_username(username):
    username = username.lstrip("@").lower()

    for uid, user in data["users"].items():

        saved = str(
            user.get("username", "")
        ).lower()

        if saved == username:
            return int(uid)

    return None


async def transfer_start(update, context):
    uid = update.effective_user.id

    create_user(update.effective_user)

    # انتقال با ریپلای
    if update.message.reply_to_message:

        target = update.message.reply_to_message.from_user

        if target.id == uid:
            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )
            return

        if target.is_bot:
            await update.message.reply_text(
                "❌ به ربات نمی‌توانید انتقال دهید."
            )
            return

        create_user(target)

        TRANSFER_DATA[uid] = {
            "target": target.id
        }

        # اگر دستور همراه مبلغ بود
        if context.args:

            try:
                amount = int(
                    context.args[0]
                    .replace(",", "")
                )

                await do_transfer(
                    update,
                    context,
                    target.id,
                    amount
                )

                TRANSFER_DATA.pop(
                    uid,
                    None
                )

                return

            except Exception:
                pass

        await update.message.reply_text(
            f"👤 گیرنده: {target.first_name}\n\n"
            "💰 مقدار انتقال را ارسال کنید.\n"
            "مثال: 500"
        )
        return

    # انتقال با username یا ID
    if context.args:

        target_raw = context.args[0]

        target_id = None

        try:
            target_id = int(target_raw)
        except Exception:
            target_id = find_user_by_username(
                target_raw
            )

        if not target_id:
            await update.message.reply_text(
                "❌ کاربر پیدا نشد."
            )
            return

        if str(target_id) not in data["users"]:

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را فعال نکرده است."
            )
            return

        if target_id == uid:

            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )
            return

        # اگر مبلغ هم داده شده
        if len(context.args) >= 2:

            try:
                amount = int(
                    context.args[1]
                    .replace(",", "")
                )
            except Exception:

                await update.message.reply_text(
                    "❌ مبلغ نامعتبر است."
                )
                return

            await do_transfer(
                update,
                context,
                target_id,
                amount
            )

            return

        TRANSFER_DATA[uid] = {
            "target": target_id
        }

        await update.message.reply_text(
            "💰 مقدار DOGS را ارسال کنید."
        )

        return

    await update.message.reply_text(
        "👥 انتقال DOGS\n\n"
        "مثال مستقیم:\n"
        "انتقال 500\n\n"
        "برای انتقال به کاربر مشخص، روی پیام او ریپلای کنید:\n"
        "انتقال 500\n\n"
        "یا:\n"
        "/transfer @username 500"
    )


async def do_transfer(
    update,
    context,
    target_id,
    amount
):
    uid = update.effective_user.id

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

    if target_id == uid:

        await update.message.reply_text(
            "❌ نمی‌توانید به خودتان انتقال دهید."
        )
        return False

    if str(target_id) not in data["users"]:

        await update.message.reply_text(
            "❌ گیرنده پیدا نشد."
        )
        return False

    if get_balance(uid) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return False

    if not remove_balance(
        uid,
        amount
    ):

        await update.message.reply_text(
            "❌ انتقال انجام نشد."
        )
        return False

    if not add_balance(
        target_id,
        amount
    ):

        add_balance(
            uid,
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
        f"👤 گیرنده: {target_id}\n"
        f"💳 موجودی شما: {get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(uid)
    )

    try:

        await context.bot.send_message(
            target_id,
            "💰 یک انتقال برای شما انجام شد.\n\n"
            f"مبلغ: {amount:,} DOGS\n"
            f"💳 موجودی جدید: {get_balance(target_id):,} DOGS"
        )

    except Exception:
        pass

    return True


# =========================================================
# انتقال فارسی
# =========================================================

async def transfer_farsi(update, context):
    text = update.message.text.strip()

    parts = text.split()

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
            "❌ مبلغ باید عدد باشد."
        )
        return

    uid = update.effective_user.id

    # اگر ریپلای است
    if update.message.reply_to_message:

        target = (
            update.message.reply_to_message.from_user
        )

        if target.id == uid:

            await update.message.reply_text(
                "❌ نمی‌توانید به خودتان انتقال دهید."
            )
            return

        create_user(target)

        await do_transfer(
            update,
            context,
            target.id,
            amount
        )

        return

    await update.message.reply_text(
        "❌ برای انتقال باید روی پیام گیرنده ریپلای کنید.\n\n"
        "مثال:\n"
        "روی پیام شخص بزنید و بنویسید:\n"
        "انتقال 500"
    )


# =========================================================
# پروفایل
# =========================================================

async def profile(update, context):
    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    user = data["users"][str(uid)]

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {user.get('name','')}\n"
        f"📱 شماره: {user.get('phone') or 'ثبت نشده'}\n"
        f"👥 زیرمجموعه: {user.get('refs',0)}\n"
        f"💰 موجودی: {get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(uid)
    )


# =========================================================
# پشتیبانی
# =========================================================

async def support(update, context):
    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "پیام خود را ارسال کنید.\n"
        "پیام شما برای مالک ارسال می‌شود."
    )


# =========================================================
# بازی
# =========================================================

def game_keyboard(game_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🎮 ورود به بازی",
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


async def game_create(update, context, amount=None):

    chat = update.effective_chat

    if chat.type not in [
        "group",
        "supergroup"
    ]:

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ قابل انجام است."
        )
        return

    user = update.effective_user

    create_user(user)

    if amount is None:

        if context.args:

            try:
                amount = int(
                    context.args[0]
                    .replace(",", "")
                )
            except Exception:

                await update.message.reply_text(
                    "❌ مبلغ بازی باید عدد باشد.\n\n"
                    "مثال:\n"
                    "بازی 500"
                )
                return

        else:

            await update.message.reply_text(
                "🎮 بازی\n\n"
                f"حداقل بازی: {MIN_GAME:,} DOGS\n"
                f"حداکثر بازی: {MAX_GAME:,} DOGS\n\n"
                "مثال:\n"
                "بازی 500"
            )
            return

    if amount < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل بازی {MIN_GAME:,} DOGS است."
        )
        return

    if amount > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر بازی {MAX_GAME:,} DOGS است."
        )
        return

    if get_balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    # رزرو مبلغ
    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )
        return

    game_id = (
        f"{chat.id}_"
        f"{int(time.time()*1000)}"
    )

    GAMES[game_id] = {
        "chat_id": chat.id,
        "message_id": None,
        "creator": user.id,
        "creator_name": user.first_name or "",
        "bet": amount,
        "status": "waiting",
        "joiner": None
    }

    data["games"][game_id] = GAMES[game_id]

    save_data()

    try:

        msg = await update.message.reply_text(
            "🎮 فرصت بازی\n\n"
            f"💰 مبلغ بازی: {amount:,} DOGS\n"
            f"👤 سازنده: {user.first_name}\n\n"
            "👥 یک نفر می‌تواند وارد بازی شود.\n\n"
            "روی دکمه ورود بزنید.",
            reply_markup=game_keyboard(game_id)
        )

        GAMES[game_id]["message_id"] = msg.message_id

        save_data()

    except Exception:

        add_balance(
            user.id,
            amount
        )

        GAMES.pop(
            game_id,
            None
        )

        data["games"].pop(
            game_id,
            None
        )

        save_data()

        await update.message.reply_text(
            "❌ ساخت بازی انجام نشد و مبلغ برگشت."
        )


async def game_join_callback(update, context):

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
        game = data["games"].get(game_id)

    if not game:

        await q.answer(
            "❌ بازی پیدا نشد.",
            show_alert=True
        )
        return

    uid = q.from_user.id

    if action == "game_cancel":

        if uid != game["creator"]:

            await q.answer(
                "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                show_alert=True
            )
            return

        if game["status"] != "waiting":

            await q.answer(
                "❌ این بازی قابل لغو نیست.",
                show_alert=True
            )
            return

        add_balance(
            game["creator"],
            game["bet"]
        )

        game["status"] = "cancelled"

        data["games"][game_id] = game

        save_data()

        await q.message.edit_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {game['bet']:,} DOGS "
            "به سازنده برگشت."
        )

        return

    if action != "game_join":
        return

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
            "❌ موجودی کافی نیست.",
            show_alert=True
        )
        return

    game["joiner"] = uid
    game["joiner_name"] = (
        q.from_user.first_name or ""
    )
    game["status"] = "playing"

    data["games"][game_id] = game

    save_data()

    await q.message.edit_text(
        "🎮 بازی شروع شد!\n\n"
        f"👤 بازیکن اول: {game['creator_name']}\n"
        f"👤 بازیکن دوم: {game['joiner_name']}\n"
        f"💰 مبلغ بازی: {game['bet']:,} DOGS\n\n"
        "🎲 در حال مشخص کردن نتیجه..."
    )

    await asyncio.sleep(1)

    winner = random.choice([
        game["creator"],
        game["joiner"]
    ])

    loser = (
        game["joiner"]
        if winner == game["creator"]
        else game["creator"]
    )

    prize = game["bet"] * 2

    add_balance(
        winner,
        prize
    )

    game["winner"] = winner
    game["loser"] = loser
    game["status"] = "finished"

    data["games"][game_id] = game

    save_data()

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

    result = (
        "🏆 نتیجه بازی\n\n"
        f"🥇 برنده: {winner_name}\n"
        f"💔 بازنده: {loser_name}\n\n"
        f"💰 جایزه: {prize:,} DOGS"
    )

    await q.message.edit_text(
        result
    )

    try:

        await context.bot.send_message(
            winner,
            result + "\n\n"
            "🎉 تبریک! جایزه به موجودی شما اضافه شد."
        )

    except Exception:
        pass

    try:

        await context.bot.send_message(
            loser,
            result + "\n\n"
            "❌ متأسفانه این بازی را باختید."
        )

    except Exception:
        pass


async def game_text(update, context):

    text = update.message.text.strip()

    parts = text.split()

    if len(parts) != 2:

        await update.message.reply_text(
            "🎮 بازی\n\n"
            f"حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"حداکثر بازی: {MAX_GAME:,} DOGS\n\n"
            "مثال:\n"
            "بازی 500"
        )
        return

    try:

        amount = int(
            parts[1].replace(",", "")
        )

    except Exception:

        await update.message.reply_text(
            "❌ مبلغ بازی باید عدد باشد.\n\n"
            "مثال:\n"
            "بازی 500"
        )
        return

    await game_create(
        update,
        context,
        amount
    )


# =========================================================
# پنل مدیریت
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


async def owner_panel(update, context):

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


async def owner_panel_callback(update, context):

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id

    if not is_owner(uid):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )
        return

    action = q.data

    if action == "adm_add":

        OWNER_STATE[uid] = {
            "action": "add",
            "step": "user"
        }

        await q.message.reply_text(
            "💰 شارژ موجودی\n\n"
            "🆔 آیدی کاربر را ارسال کنید."
        )

    elif action == "adm_remove":

        OWNER_STATE[uid] = {
            "action": "remove",
            "step": "user"
        }

        await q.message.reply_text(
            "➖ کسر موجودی\n\n"
            "🆔 آیدی کاربر را ارسال کنید."
        )

    elif action == "adm_reward":

        OWNER_STATE[uid] = {
            "action": "reward",
            "step": "amount"
        }

        await q.message.reply_text(
            f"👥 جایزه فعلی: "
            f"{int(data.get('ref_reward',50)):,} DOGS\n\n"
            "مقدار جدید را ارسال کنید."
        )

    elif action == "adm_owner":

        OWNER_STATE[uid] = {
            "action": "owner",
            "step": "user"
        }

        await q.message.reply_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی مالک جدید را ارسال کنید."
        )

    elif action == "adm_deposits":

        pending = [
            x for x in data["deposits"].values()
            if x.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "📋 واریزی معلقی وجود ندارد."
            )
            return

        text = "📋 واریزی‌های در انتظار:\n\n"

        for item in pending[-20:]:

            text += (
                f"🆔 {item['request_id']}\n"
                f"👤 {item['user_id']}\n"
                f"💰 {item['amount']:,} DOGS\n\n"
            )

        await q.message.reply_text(
            text
        )

    elif action == "adm_withdraws":

        pending = [
            x for x in data["withdraws"].values()
            if x.get("status") == "pending"
        ]

        if not pending:

            await q.message.reply_text(
                "💸 برداشت معلقی وجود ندارد."
            )
            return

        text = "💸 برداشت‌های در انتظار:\n\n"

        for item in pending[-20:]:

            text += (
                f"🆔 {item['request_id']}\n"
                f"👤 {item['user_id']}\n"
                f"💰 {item['amount']:,} DOGS\n"
                f"📥 {item['wallet']}\n\n"
            )

        await q.message.reply_text(
            text
        )

    elif action == "adm_stats":

        users = len(
            data["users"]
        )

        total = sum(
            get_balance(uid)
            for uid in data["users"]
        )

        await q.message.reply_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total:,} DOGS\n"
            f"📋 واریزی‌ها: {len(data['deposits'])}\n"
            f"💸 برداشت‌ها: {len(data['withdraws'])}\n"
            f"🎮 بازی‌ها: {len(data['games'])}"
        )


# =========================================================
# دریافت وضعیت مالک
# =========================================================

async def owner_state_receive(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):
        return

    state = OWNER_STATE.get(uid)

    if not state:
        return

    text = update.message.text.strip()

    action = state.get("action")
    step = state.get("step")

    # شارژ / کسر
    if action in [
        "add",
        "remove"
    ]:

        if step == "user":

            try:
                target = int(
                    text.replace(",", "")
                )
            except Exception:

                await update.message.reply_text(
                    "❌ آیدی باید عدد باشد."
                )
                return

            if str(target) not in data["users"]:

                await update.message.reply_text(
                    "❌ کاربر پیدا نشد."
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
                    "❌ مقدار نامعتبر است."
                )
                return

            if amount <= 0:

                await update.message.reply_text(
                    "❌ مقدار باید بیشتر از صفر باشد."
                )
                return

            target = state["target"]

            if action == "add":

                add_balance(
                    target,
                    amount
                )

                message = (
                    f"✅ {amount:,} DOGS "
                    "به موجودی اضافه شد."
                )

                try:
                    await context.bot.send_message(
                        target,
                        f"💰 {amount:,} DOGS "
                        "به موجودی شما اضافه شد."
                    )
                except Exception:
                    pass

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

                message = (
                    f"✅ {amount:,} DOGS "
                    "از موجودی کسر شد."
                )

                try:
                    await context.bot.send_message(
                        target,
                        f"➖ {amount:,} DOGS "
                        "از موجودی شما کسر شد."
                    )
                except Exception:
                    pass

            OWNER_STATE.pop(
                uid,
                None
            )

            await update.message.reply_text(
                message,
                reply_markup=main_keyboard(uid)
            )

            return

    # جایزه
    if action == "reward":

        try:
            amount = int(
                text.replace(",", "")
            )
        except Exception:

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
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
            f"✅ جایزه زیرمجموعه روی "
            f"{amount:,} DOGS تنظیم شد."
        )

        return

    # انتقال مالکیت
    if action == "owner" and step == "user":

        try:
            new_owner = int(
                text.replace(",", "")
            )
        except Exception:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است."
            )
            return

        if str(new_owner) not in data["users"]:

            await update.message.reply_text(
                "❌ کاربر باید قبلاً ربات را فعال کرده باشد."
            )
            return

        OWNER_STATE[uid] = {
            "action": "owner_confirm",
            "target": new_owner
        }

        await update.message.reply_text(
            "⚠️ انتقال مالکیت\n\n"
            f"👑 مالک جدید: {new_owner}\n\n"
            "آیا تایید می‌کنید؟",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ تایید",
                        callback_data=f"owner_yes:{new_owner}"
                    ),
                    InlineKeyboardButton(
                        "❌ لغو",
                        callback_data="owner_no"
                    )
                ]
            ])
        )

        return


async def owner_transfer_decision(update, context):

    q = update.callback_query

    await q.answer()

    if not is_owner(q.from_user.id):

        await q.answer(
            "❌ فقط مالک.",
            show_alert=True
        )
        return

    if q.data == "owner_no":

        OWNER_STATE.pop(
            q.from_user.id,
            None
        )

        await q.message.reply_text(
            "❌ انتقال مالکیت لغو شد."
        )

        return

    try:
        new_owner = int(
            q.data.split(":", 1)[1]
        )
    except Exception:

        await q.message.reply_text(
            "❌ آیدی نامعتبر است."
        )
        return

    if str(new_owner) not in data["users"]:

        await q.message.reply_text(
            "❌ کاربر پیدا نشد."
        )
        return

    data["owner"] = new_owner

    save_data()

    OWNER_STATE.pop(
        q.from_user.id,
        None
    )

    await q.message.reply_text(
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
# دستورات مالک
# =========================================================

async def transfer_owner_command(update, context):

    uid = update.effective_user.id

    if not is_owner(uid):

        await update.message.reply_text(
            "❌ فقط مالک اجازه دارد."
        )
        return

    if not context.args:

        await update.message.reply_text(
            "❌ این دستور دیگر لازم نیست.\n\n"
            "از پنل مدیریت > انتقال مالکیت استفاده کنید."
        )
        return

    await update.message.reply_text(
        "⚠️ انتقال مالکیت فقط از داخل پنل مدیریت انجام می‌شود."
    )


# =========================================================
# دستورات
# =========================================================

async def transfer_command(update, context):
    await transfer_start(
        update,
        context
    )


async def game_command(update, context):
    await game_create(
        update,
        context
    )


async def admin_command(update, context):
    await owner_panel(
        update,
        context
    )


# =========================================================
# مسیریاب پیام
# =========================================================

async def text_router(update, context):

    if not update.message:
        return

    if not update.message.text:
        return

    text = update.message.text.strip()

    uid = update.effective_user.id

    create_user(
        update.effective_user
    )

    # -----------------------------------------
    # برگشت
    # -----------------------------------------

    if text == "🔙 برگشت":

        DEPOSIT_DATA.pop(uid, None)
        WITHDRAW_DATA.pop(uid, None)
        TRANSFER_DATA.pop(uid, None)
        OWNER_STATE.pop(uid, None)

        await update.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard(uid)
        )

        return

    # -----------------------------------------
    # انتقال فارسی
    # -----------------------------------------

    if text.startswith("انتقال "):

        if uid in TRANSFER_DATA:
            TRANSFER_DATA.pop(
                uid,
                None
            )

        await transfer_farsi(
            update,
            context
        )

        return

    # -----------------------------------------
    # بازی فارسی
    # -----------------------------------------

    if text == "🎮 بازی":

        await game_create(
            update,
            context
        )

        return

    if text.startswith("بازی "):

        await game_text(
            update,
            context
        )

        return

    # -----------------------------------------
    # وضعیت مالک
    # -----------------------------------------

    if uid in OWNER_STATE:

        await owner_state_receive(
            update,
            context
        )

        return

    # -----------------------------------------
    # انتقال در حال انجام
    # -----------------------------------------

    if uid in TRANSFER_DATA:

        try:

            amount = int(
                text.replace(",", "")
            )

        except Exception:

            await update.message.reply_text(
                "❌ مبلغ باید عدد باشد."
            )
            return

        target = TRANSFER_DATA[uid]["target"]

        await do_transfer(
            update,
            context,
            target,
            amount
        )

        TRANSFER_DATA.pop(
            uid,
            None
        )

        return

    # -----------------------------------------
    # واریز
    # -----------------------------------------

    if uid in DEPOSIT_DATA:

        step = DEPOSIT_DATA[uid].get(
            "step"
        )

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

    # -----------------------------------------
    # برداشت
    # -----------------------------------------

    if uid in WITHDRAW_DATA:

        step = WITHDRAW_DATA[uid].get(
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

    # -----------------------------------------
    # منوی اصلی
    # -----------------------------------------

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


# =========================================================
# عکس رسید
# =========================================================

async def photo_router(update, context):

    uid = update.effective_user.id

    if uid in DEPOSIT_DATA:

        await deposit_receipt(
            update,
            context
        )


# =========================================================
# پشتیبانی: ارسال پیام عادی به مالک
# =========================================================

async def support_message(update, context):

    if not update.message:
        return

    uid = update.effective_user.id

    # اگر کاربر در هیچ فرآیند دیگری نیست
    if (
        uid in DEPOSIT_DATA
        or uid in WITHDRAW_DATA
        or uid in TRANSFER_DATA
        or uid in OWNER_STATE
    ):
        return

    # پیام‌های منوی اصلی
    if update.message.text in [
        "💳 واریزی",
        "💰 برداشت",
        "👥 زیرمجموعه",
        "🎧 پشتیبانی",
        "👤 پروفایل",
        "👥 انتقال",
        "🎮 بازی",
        "⚙️ پنل مدیریت",
        "🔙 برگشت",
    ]:
        return


# =========================================================
# خطا
# =========================================================

async def error_handler(update, context):

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
            "BOT_TOKEN environment variable is missing."
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------
    # Commands
    # -----------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "transfer",
            transfer_command
        )
    )

    app.add_handler(
        CommandHandler(
            "transferowner",
            transfer_owner_command
        )
    )

    app.add_handler(
        CommandHandler(
            "game",
            game_command
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_command
        )
    )

    # -----------------------------------------
    # Callbacks
    # -----------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
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
            owner_transfer_decision,
            pattern=r"^owner_(yes|no)"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            game_join_callback,
            pattern=r"^game_(join|cancel):"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            owner_panel_callback,
            pattern=r"^adm_"
        )
    )

    # -----------------------------------------
    # Contact
    # -----------------------------------------

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            phone_receive
        )
    )

    # -----------------------------------------
    # Photo
    # -----------------------------------------

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_router
        )
    )

    # -----------------------------------------
    # Text
    # -----------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )

    # -----------------------------------------
    # Error
    # -----------------------------------------

    app.add_error_handler(
        error_handler
    )

    print("BOT STARTED")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
