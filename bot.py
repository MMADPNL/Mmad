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

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8552447077

FORCE_CHANNEL = "@TAK_B_ET"
FORCE_GROUP = "@TAK_B_ET"

ULTRA_ID = "@CyyFr"
ULTRA_WALLET = "@CyyFr"

EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "data.json"

# =========================
# DATA
# =========================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "bot_status": True,
    "ref_reward": 50,
    "users": {},
    "deposits": {},
    "withdraws": {},
}


def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if not isinstance(d, dict):
                    return json.loads(json.dumps(DEFAULT_DATA))
                for k, v in DEFAULT_DATA.items():
                    if k not in d:
                        d[k] = json.loads(json.dumps(v))
                return d
    except Exception as e:
        print("LOAD ERROR:", e)
    return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


def save_data():
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception:
        traceback.print_exc()


# =========================
# ANTI BUG / STATE
# =========================

CLICK = {}
DEPOSIT_DATA = {}
WITHDRAW_DATA = {}
TRANSFER_DATA = {}
OWNER_STATE = {}
GAMES = {}


def anti_spam(uid, seconds=1.5):
    now = time.time()
    key = str(uid)
    old = CLICK.get(key, 0)
    if now - old < seconds:
        return False
    CLICK[key] = now
    return True


# =========================
# USER SYSTEM
# =========================

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
        }
        save_data()
        return

    u = data["users"][uid]
    u["id"] = user.id
    u["name"] = user.first_name or u.get("name", "")
    u["username"] = user.username or u.get("username", "")
    u.setdefault("phone", "")
    u.setdefault("balance", 0)
    u.setdefault("refs", 0)
    u.setdefault("ref_by", None)


def get_balance(uid):
    try:
        return int(data["users"][str(uid)]["balance"])
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

    data["users"][uid]["balance"] = get_balance(uid) + amount
    if data["users"][uid]["balance"] < 0:
        data["users"][uid]["balance"] = 0
    save_data()
    return True


def remove_balance(uid, amount):
    try:
        amount = int(amount)
    except Exception:
        return False
    if amount < 0 or get_balance(uid) < amount:
        return False
    return add_balance(uid, -amount)


def is_owner(uid):
    try:
        return int(uid) == int(data.get("owner", OWNER_ID))
    except Exception:
        return False


# =========================
# KEYBOARDS
# =========================

def main_keyboard(uid):
    buttons = [
        ["💳 واریزی", "💰 برداشت"],
        ["👥 زیرمجموعه", "🎧 پشتیبانی"],
        ["👤 پروفایل", "👥 انتقال"],
    ]
    if is_owner(uid):
        buttons.append(["⚙️ پنل مدیریت"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def back_keyboard():
    return ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)


def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 کانال", url="https://t.me/TAK_B_ET")],
        [InlineKeyboardButton("👥 گپ", url="https://t.me/TAK_B_ET")],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")],
    ])


def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 ارسال شماره", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# =========================
# FORCE JOIN
# =========================

async def check_join(user_id, context):
    try:
        for chat in [FORCE_CHANNEL, FORCE_GROUP]:
            member = await context.bot.get_chat_member(chat, user_id)
            if member.status in ["left", "kicked"]:
                return False
        return True
    except Exception as e:
        print("JOIN ERROR:", e)
        return False


# =========================
# REFERRAL
# =========================

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

    reward = int(data.get("ref_reward", 50))
    add_balance(ref_id, reward)
    save_data()


# =========================
# START / PHONE
# =========================

async def start(update, context):
    user = update.effective_user
    create_user(user)

    await process_referral(update, context)

    if not await check_join(user.id, context):
        await update.message.reply_text(
            "❌ ابتدا عضو کانال و گپ شوید.",
            reply_markup=join_keyboard(),
        )
        return

    if not data["users"][str(user.id)].get("phone"):
        await update.message.reply_text(
            "📱 شماره خود را ارسال کنید.\n\nفقط شماره ایران +98 قبول است.",
            reply_markup=phone_keyboard(),
        )
        return

    await update.message.reply_text(
        "✅ ورود موفق شد.\n\n"
        f"💰 موجودی شما: {get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id),
    )


def clean_phone(phone):
    if not phone:
        return None

    phone = phone.replace(" ", "").replace("-", "")

    if phone.startswith("0098"):
        phone = "+" + phone[2:]
    elif phone.startswith("98"):
        phone = "+" + phone

    if phone.startswith("+98"):
        return phone
    return None


async def phone_receive(update, context):
    user = update.effective_user

    if not update.message.contact:
        return

    contact = update.message.contact

    if contact.user_id != user.id:
        await update.message.reply_text("❌ فقط شماره خودتان را ارسال کنید.")
        return

    phone = clean_phone(contact.phone_number)

    if not phone:
        await update.message.reply_text("❌ فقط شماره ایران +98 قبول است.")
        return

    create_user(user)
    data["users"][str(user.id)]["phone"] = phone
    save_data()

    await update.message.reply_text(
        "✅ شماره تایید شد.",
        reply_markup=main_keyboard(user.id),
    )


# =========================
# REFERRAL MENU
# =========================

async def referral_menu(update, context):
    user = update.effective_user
    create_user(user)

    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    refs = data["users"][str(user.id)].get("refs", 0)
    reward = int(data.get("ref_reward", 50))

    await update.message.reply_text(
        "👥 سیستم زیرمجموعه\n\n"
        f"🔗 لینک دعوت شما:\n{link}\n\n"
        f"👥 تعداد زیرمجموعه: {refs}\n"
        f"💰 جایزه هر نفر: {reward:,} DOGS",
        reply_markup=main_keyboard(user.id),
    )


# =========================
# DEPOSIT
# =========================

async def deposit_start(update, context):
    user = update.effective_user
    create_user(user)

    if not anti_spam(user.id):
        return

    keyboard = [
        [InlineKeyboardButton("🐶 ULTRA / DOGS", callback_data="dep_ultra")],
        [InlineKeyboardButton("💱 صرافی", callback_data="dep_exchange")],
    ]

    await update.message.reply_text(
        "💳 روش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def deposit_type(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    if q.data == "dep_ultra":
        DEPOSIT_DATA[uid] = {"type": "ULTRA", "step": "amount"}
        text = (
            "🐶 واریز ULTRA\n\n"
            "مقدار DOGS را وارد کنید.\n"
            "حداقل واریز: 5000 DOGS"
        )
    else:
        DEPOSIT_DATA[uid] = {"type": "EXCHANGE", "step": "amount"}
        text = (
            "💱 واریز صرافی\n\n"
            "مبلغ را وارد کنید.\n"
            "بعد از آن ولت نمایش داده می‌شود."
        )

    await q.message.edit_text(text)


async def deposit_amount(update, context):
    uid = update.effective_user.id

    if uid not in DEPOSIT_DATA:
        return
    if DEPOSIT_DATA[uid].get("step") != "amount":
        return

    try:
        amount = int(update.message.text.replace(",", "").strip())
    except Exception:
        await update.message.reply_text("❌ مقدار فقط عدد باشد.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ مقدار نامعتبر است.")
        return

    typ = DEPOSIT_DATA[uid]["type"]

    if typ == "ULTRA" and amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز DOGS برابر {MIN_DEPOSIT:,} است."
        )
        return

    DEPOSIT_DATA[uid]["amount"] = amount
    DEPOSIT_DATA[uid]["step"] = "receipt"

    if typ == "ULTRA":
        text = (
            f"💳 فرصت واریز:\n\n"
            f"ULTRA {amount:,} DOGS {ULTRA_ID}\n\n"
            f"حداقل واریز {MIN_DEPOSIT:,} DOGS\n\n"
            "شات خود یا پیام رسید را ارسال کنید."
        )
    else:
        text = (
            "💱 صرافی\n\n"
            f"مبلغ وارد شده: {amount:,}\n\n"
            f"ولت:\n`{EXCHANGE_WALLET}`\n\n"
            "به این ولت بزنید و شات یا لینک هش تراکنش ارسال کنید."
        )

    await update.message.reply_text(text, parse_mode="Markdown")


def deposit_buttons(req_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"dep_ok:{req_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"dep_no:{req_id}"),
        ]
    ])


async def send_deposit_to_owner(update, context, req):
    owner = data.get("owner", OWNER_ID)
    req_id = req["request_id"]

    caption = (
        "💳 درخواست واریزی جدید\n\n"
        f"🆔 درخواست: {req_id}\n"
        f"👤 کاربر: {req['user_id']}\n"
        f"💰 نوع: {req['type']}\n"
        f"📊 مبلغ: {req['amount']:,}\n\n"
        "بررسی کنید."
    )

    markup = deposit_buttons(req_id)

    if req["kind"] == "photo":
        await context.bot.send_photo(
            chat_id=owner,
            photo=req["content"],
            caption=caption,
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=owner,
            text=caption + "\n\n🧾 رسید پیام:\n" + req["content"],
            reply_markup=markup,
        )


async def deposit_receipt(update, context):
    uid = update.effective_user.id

    if uid not in DEPOSIT_DATA:
        return
    if DEPOSIT_DATA[uid].get("step") != "receipt":
        return

    req_id = f"D{int(time.time()*1000)}_{uid}"
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
            "created": datetime.now().isoformat(),
        }
    elif update.message.text and info["type"] == "EXCHANGE":
        text = update.message.text.strip()
        req = {
            "request_id": req_id,
            "user_id": uid,
            "type": info["type"],
            "amount": info["amount"],
            "kind": "text",
            "content": text,
            "status": "pending",
            "created": datetime.now().isoformat(),
        }
    else:
        await update.message.reply_text(
            "❌ برای این درخواست فقط عکس رسید یا لینک/متن هش تراکنش ارسال کنید."
        )
        return

    data["deposits"][req_id] = req
    save_data()

    try:
        await send_deposit_to_owner(update, context, req)
    except Exception:
        traceback.print_exc()
        await update.message.reply_text("❌ ارسال درخواست به مالک انجام نشد.")
        return

    DEPOSIT_DATA.pop(uid, None)

    await update.message.reply_text(
        "✅ رسید پیام ارسال شد.\n"
        "⏳ منتظر تایید مالک باشید.",
        reply_markup=main_keyboard(uid),
    )


async def deposit_decision(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("❌ فقط مالک.", show_alert=True)
        return

    try:
        action, req_id = q.data.split(":", 1)
        req = data["deposits"].get(req_id)
    except Exception:
        req = None

    if not req:
        await q.message.reply_text("❌ درخواست پیدا نشد.")
        return

    if req.get("status") != "pending":
        await q.message.reply_text("⚠️ این درخواست قبلاً بررسی شده.")
        return

    uid = req["user_id"]

    if action == "dep_ok":
        req["status"] = "approved"
        add_balance(uid, req["amount"])
        msg = f"✅ واریز {req['amount']:,} تایید شد و موجودی اضافه شد."
        try:
            await context.bot.send_message(uid, msg)
        except Exception:
            pass
        await q.message.edit_reply_markup(reply_markup=None)
        await q.message.reply_text(f"✅ واریز کاربر {uid} تایید شد.")
    else:
        req["status"] = "rejected"
        save_data()
        try:
            await context.bot.send_message(uid, "❌ درخواست واریز شما رد شد.")
        except Exception:
            pass
        await q.message.edit_reply_markup(reply_markup=None)
        await q.message.reply_text(f"❌ واریز کاربر {uid} رد شد.")

    save_data()


# =========================
# WITHDRAW
# =========================

async def withdraw_start(update, context):
    uid = update.effective_user.id
    create_user(update.effective_user)

    if get_balance(uid) < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است.\n"
            f"💰 موجودی: {get_balance(uid):,} DOGS"
        )
        return

    WITHDRAW_DATA[uid] = {"step": "amount"}

    await update.message.reply_text(
        f"💰 مقدار برداشت را وارد کنید.\n\n"
        f"حداقل: {MIN_WITHDRAW:,} DOGS\n"
        f"موجودی: {get_balance(uid):,} DOGS",
        reply_markup=back_keyboard(),
    )


async def withdraw_amount(update, context):
    uid = update.effective_user.id

    if uid not in WITHDRAW_DATA or WITHDRAW_DATA[uid].get("step") != "amount":
        return

    try:
        amount = int(update.message.text.replace(",", "").strip())
    except Exception:
        await update.message.reply_text("❌ فقط عدد ارسال کنید.")
        return

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return

    if get_balance(uid) < amount:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    WITHDRAW_DATA[uid] = {"step": "wallet", "amount": amount}
    await update.message.reply_text(
        "📥 آدرس ولت مقصد را ارسال کنید."
    )


async def withdraw_wallet(update, context):
    uid = update.effective_user.id

    if uid not in WITHDRAW_DATA or WITHDRAW_DATA[uid].get("step") != "wallet":
        return

    wallet = update.message.text.strip()
    if len(wallet) < 5:
        await update.message.reply_text("❌ آدرس ولت نامعتبر است.")
        return

    amount = WITHDRAW_DATA[uid]["amount"]
    req_id = f"W{int(time.time()*1000)}_{uid}"

    if not remove_balance(uid, amount):
        await update.message.reply_text("❌ موجودی کافی نیست.")
        WITHDRAW_DATA.pop(uid, None)
        return

    req = {
        "request_id": req_id,
        "user_id": uid,
        "amount": amount,
        "wallet": wallet,
        "status": "pending",
        "created": datetime.now().isoformat(),
    }
    data["withdraws"][req_id] = req
    save_data()

    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید برداشت", callback_data=f"with_ok:{req_id}"),
            InlineKeyboardButton("❌ رد برداشت", callback_data=f"with_no:{req_id}"),
        ]
    ])

    await context.bot.send_message(
        data.get("owner", OWNER_ID),
        "💰 درخواست برداشت جدید\n\n"
        f"🆔 {req_id}\n"
        f"👤 کاربر: {uid}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"📥 ولت:\n{wallet}",
        reply_markup=markup,
    )

    WITHDRAW_DATA.pop(uid, None)

    await update.message.reply_text(
        "✅ درخواست برداشت ارسال شد.\n"
        "⏳ مبلغ تا تعیین تکلیف درخواست رزرو شده.",
        reply_markup=main_keyboard(uid),
    )


async def withdraw_decision(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("❌ فقط مالک.", show_alert=True)
        return

    action, req_id = q.data.split(":", 1)
    req = data["withdraws"].get(req_id)

    if not req or req.get("status") != "pending":
        await q.message.reply_text("⚠️ درخواست قبلاً بررسی شده یا وجود ندارد.")
        return

    uid = req["user_id"]

    if action == "with_ok":
        req["status"] = "approved"
        text = (
            f"✅ برداشت {req['amount']:,} DOGS تایید شد.\n"
            "پرداخت را طبق اطلاعات ثبت‌شده انجام دهید."
        )
        owner_text = "✅ برداشت تایید شد."
    else:
        req["status"] = "rejected"
        add_balance(uid, req["amount"])
        text = (
            f"❌ برداشت {req['amount']:,} DOGS رد شد.\n"
            "مبلغ به موجودی شما برگشت."
        )
        owner_text = "❌ برداشت رد شد."

    save_data()
    try:
        await context.bot.send_message(uid, text)
    except Exception:
        pass

    await q.message.edit_reply_markup(reply_markup=None)
    await q.message.reply_text(owner_text)


# =========================
# TRANSFER
# =========================

def find_user_by_username(username):
    username = username.lstrip("@").lower()
    for uid, u in data["users"].items():
        if str(u.get("username", "")).lower() == username:
            return int(uid)
    return None


async def transfer_start(update, context):
    uid = update.effective_user.id
    create_user(update.effective_user)

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if target.id == uid:
            await update.message.reply_text("❌ نمی‌توانید به خودتان انتقال دهید.")
            return
        create_user(target)
        TRANSFER_DATA[uid] = {"step": "amount", "target": target.id}
        await update.message.reply_text(
            f"👤 گیرنده: {target.first_name}\n"
            "💰 مقدار DOGS را ارسال کنید."
        )
        return

    if context.args:
        raw = context.args[0]
        target_id = None

        try:
            target_id = int(raw)
        except Exception:
            target_id = find_user_by_username(raw)

        if not target_id or str(target_id) not in data["users"]:
            await update.message.reply_text("❌ کاربر پیدا نشد.")
            return
        if target_id == uid:
            await update.message.reply_text("❌ نمی‌توانید به خودتان انتقال دهید.")
            return

        TRANSFER_DATA[uid] = {"step": "amount", "target": target_id}
        await update.message.reply_text("💰 مقدار DOGS را ارسال کنید.")
        return

    await update.message.reply_text(
        "👥 انتقال DOGS\n\n"
        "روش ۱: روی پیام کاربر ریپلای کنید و /transfer بزنید.\n"
        "روش ۲: /transfer @username\n"
        "روش ۳: /transfer user_id"
    )


async def transfer_amount(update, context):
    uid = update.effective_user.id

    if uid not in TRANSFER_DATA or TRANSFER_DATA[uid].get("step") != "amount":
        return

    try:
        amount = int(update.message.text.replace(",", "").strip())
    except Exception:
        return

    if amount <= 0:
        await update.message.reply_text("❌ مقدار نامعتبر است.")
        return

    target = TRANSFER_DATA[uid]["target"]

    if target == uid:
        await update.message.reply_text("❌ انتقال به خودتان ممکن نیست.")
        TRANSFER_DATA.pop(uid, None)
        return

    if get_balance(uid) < amount:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        TRANSFER_DATA.pop(uid, None)
        return

    remove_balance(uid, amount)
    add_balance(target, amount)

    TRANSFER_DATA.pop(uid, None)

    await update.message.reply_text(
        f"✅ انتقال انجام شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"👤 گیرنده: {target}",
        reply_markup=main_keyboard(uid),
    )

    try:
        await context.bot.send_message(
            target,
            f"💰 مبلغ {amount:,} DOGS از طرف یک کاربر به شما انتقال داده شد."
        )
    except Exception:
        pass


# =========================
# PROFILE / SUPPORT
# =========================

async def profile(update, context):
    uid = update.effective_user.id
    create_user(update.effective_user)
    u = data["users"][str(uid)]

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"🆔 ID: {uid}\n"
        f"👤 نام: {u.get('name','')}\n"
        f"📱 شماره: {u.get('phone') or 'ثبت نشده'}\n"
        f"👥 زیرمجموعه: {u.get('refs',0)}\n"
        f"💰 موجودی: {get_balance(uid):,} DOGS",
        reply_markup=main_keyboard(uid),
    )


async def support(update, context):
    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "برای ارتباط با پشتیبانی پیام خود را ارسال کنید."
    )


# =========================
# OWNER PANEL
# =========================

def owner_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 شارژ موجودی", callback_data="adm_add"),
            InlineKeyboardButton("➖ کسر موجودی", callback_data="adm_remove"),
        ],
        [
            InlineKeyboardButton("👥 جایزه زیرمجموعه", callback_data="adm_reward"),
            InlineKeyboardButton("📋 واریزی‌ها", callback_data="adm_deposits"),
        ],
        [
            InlineKeyboardButton("💸 برداشت‌ها", callback_data="adm_withdraws"),
            InlineKeyboardButton("👑 انتقال مالکیت", callback_data="adm_owner"),
        ],
        [
            InlineKeyboardButton("📊 آمار", callback_data="adm_stats"),
        ],
    ])


async def owner_panel(update, context):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text("❌ دسترسی ندارید.")
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=owner_panel_keyboard(),
    )


async def owner_panel_callback(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("❌ فقط مالک.", show_alert=True)
        return

    action = q.data

    if action == "adm_add":
        OWNER_STATE[q.from_user.id] = {"action": "add", "step": "user"}
        await q.message.reply_text("🆔 آیدی کاربر را ارسال کنید.")

    elif action == "adm_remove":
        OWNER_STATE[q.from_user.id] = {"action": "remove", "step": "user"}
        await q.message.reply_text("🆔 آیدی کاربر را ارسال کنید.")

    elif action == "adm_reward":
        OWNER_STATE[q.from_user.id] = {"action": "reward", "step": "amount"}
        await q.message.reply_text(
            f"💰 جایزه فعلی: {int(data.get('ref_reward',50)):,} DOGS\n"
            "مقدار جدید را ارسال کنید."
        )

    elif action == "adm_owner":
        OWNER_STATE[q.from_user.id] = {"action": "owner", "step": "user"}
        await q.message.reply_text("👑 آیدی مالک جدید را ارسال کنید.")

    elif action == "adm_deposits":
        pending = [
            x for x in data["deposits"].values()
            if x.get("status") == "pending"
        ]
        if not pending:
            await q.message.reply_text("📋 درخواست واریز معلقی وجود ندارد.")
        else:
            text = "📋 واریزی‌های در انتظار:\n\n"
            for x in pending[-20:]:
                text += (
                    f"🆔 {x['request_id']}\n"
                    f"👤 {x['user_id']} | {x['amount']:,} | {x['type']}\n\n"
                )
            await q.message.reply_text(text)

    elif action == "adm_withdraws":
        pending = [
            x for x in data["withdraws"].values()
            if x.get("status") == "pending"
        ]
        if not pending:
            await q.message.reply_text("💸 برداشت معلقی وجود ندارد.")
        else:
            text = "💸 برداشت‌های در انتظار:\n\n"
            for x in pending[-20:]:
                text += (
                    f"🆔 {x['request_id']}\n"
                    f"👤 {x['user_id']} | {x['amount']:,}\n"
                    f"ولت: {x['wallet']}\n\n"
                )
            await q.message.reply_text(text)

    elif action == "adm_stats":
        users = len(data["users"])
        total = sum(get_balance(uid) for uid in data["users"])
        await q.message.reply_text(
            "📊 آمار\n\n"
            f"👥 کاربران: {users}\n"
            f"💰 مجموع موجودی: {total:,} DOGS"
        )


async def owner_state_receive(update, context):
    uid = update.effective_user.id

    if not is_owner(uid) or uid not in OWNER_STATE:
        return

    state = OWNER_STATE[uid]

    try:
        value = int(update.message.text.replace(",", "").strip())
    except Exception:
        value = None

    if state["action"] in ["add", "remove"]:
        if state["step"] == "user":
            if value is None or str(value) not in data["users"]:
                await update.message.reply_text("❌ آیدی کاربر معتبر نیست.")
                return
            state["target"] = value
            state["step"] = "amount"
            await update.message.reply_text("💰 مقدار DOGS را ارسال کنید.")
            return

        if state["step"] == "amount":
            if value is None or value <= 0:
                await update.message.reply_text("❌ مقدار نامعتبر است.")
                return

            if state["action"] == "add":
                add_balance(state["target"], value)
                msg = f"✅ {value:,} DOGS اضافه شد."
            else:
                if get_balance(state["target"]) < value:
                    await update.message.reply_text("❌ موجودی کاربر کافی نیست.")
                    return
                remove_balance(state["target"], value)
                msg = f"✅ {value:,} DOGS کسر شد."

            OWNER_STATE.pop(uid, None)
            await update.message.reply_text(msg)
            return

    if state["action"] == "reward":
        if value is None or value < 0:
            await update.message.reply_text("❌ مقدار نامعتبر است.")
            return
        data["ref_reward"] = value
        save_data()
        OWNER_STATE.pop(uid, None)
        await update.message.reply_text(
            f"✅ جایزه زیرمجموعه روی {value:,} DOGS تنظیم شد."
        )
        return

    if state["action"] == "owner":
        if value is None or str(value) not in data["users"]:
            await update.message.reply_text("❌ کاربر باید قبلاً داخل ربات ثبت شده باشد.")
            return

        new_owner = value
        OWNER_STATE[uid] = {
            "action": "owner_confirm",
            "target": new_owner,
        }

        await update.message.reply_text(
            f"⚠️ انتقال مالکیت\n\n"
            f"👑 مالک جدید: {new_owner}\n\n"
            "تایید می‌کنید؟",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ تایید", callback_data=f"owner_yes:{new_owner}"),
                    InlineKeyboardButton("❌ لغو", callback_data="owner_no"),
                ]
            ]),
        )


async def owner_transfer_decision(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("❌ فقط مالک.", show_alert=True)
        return

    if q.data == "owner_no":
        OWNER_STATE.pop(q.from_user.id, None)
        await q.message.reply_text("❌ انتقال مالکیت لغو شد.")
        return

    try:
        new_owner = int(q.data.split(":", 1)[1])
    except Exception:
        await q.message.reply_text("❌ خطا.")
        return

    if str(new_owner) not in data["users"]:
        await q.message.reply_text("❌ کاربر پیدا نشد.")
        return

    old_owner = data.get("owner", OWNER_ID)
    data["owner"] = new_owner
    save_data()
    OWNER_STATE.pop(q.from_user.id, None)

    await q.message.reply_text(
        f"✅ انتقال مالکیت انجام شد.\n"
        f"👑 مالک جدید: {new_owner}"
    )

    try:
        await context.bot.send_message(
            new_owner,
            "👑 شما مالک جدید ربات شدید."
        )
    except Exception:
        pass


# =========================
# GAME SYSTEM - GROUP
# =========================

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
                "❌ لغو",
                callback_data=f"game_cancel:{game_id}"
            )
        ],
    ])


async def game_create(update, context):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ بازی باید داخل گپ انجام شود.")
        return

    if update.effective_chat.username:
        pass

    user = update.effective_user
    create_user(user)

    if not await check_join(user.id, context):
        await update.message.reply_text("❌ ابتدا عضو کانال و گپ شوید.")
        return

    if not context.args:
        await update.message.reply_text(
            f"🎮 ساخت بازی\n\n"
            f"استفاده: /game 500\n"
            f"حداقل: {MIN_GAME:,}\n"
            f"حداکثر: {MAX_GAME:,}"
        )
        return

    try:
        bet = int(context.args[0].replace(",", ""))
    except Exception:
        await update.message.reply_text("❌ مبلغ بازی عدد باشد.")
        return

    if bet < MIN_GAME or bet > MAX_GAME:
        await update.message.reply_text(
            f"❌ مبلغ بازی باید بین {MIN_GAME:,} و {MAX_GAME:,} DOGS باشد."
        )
        return

    if get_balance(user.id) < bet:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    # Reserve creator stake.
    if not remove_balance(user.id, bet):
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    game_id = f"{update.effective_chat.id}_{int(time.time()*1000)}"

    GAMES[game_id] = {
        "chat_id": update.effective_chat.id,
        "message_id": None,
        "creator": user.id,
        "creator_name": user.first_name or "",
        "bet": bet,
        "status": "waiting",
        "joiner": None,
    }

    msg = await update.message.reply_text(
        f"🎮 بازی {bet:,} DOGS ساخته شد!\n\n"
        f"👤 سازنده: {user.first_name}\n"
        "👥 یک نفر می‌تواند وارد بازی شود.\n\n"
        "برای ورود روی «بازی با دوستان» بزنید.",
        reply_markup=game_keyboard(game_id),
    )

    GAMES[game_id]["message_id"] = msg.message_id


async def game_callback(update, context):
    q = update.callback_query
    await q.answer()

    try:
        action, game_id = q.data.split(":", 1)
    except Exception:
        return

    game = GAMES.get(game_id)
    if not game:
        await q.message.reply_text("❌ بازی پیدا نشد.")
        return

    uid = q.from_user.id

    if action == "game_cancel":
        if uid != game["creator"]:
            await q.answer("❌ فقط سازنده می‌تواند لغو کند.", show_alert=True)
            return
        if game["status"] != "waiting":
            await q.answer("❌ بازی دیگر قابل لغو نیست.", show_alert=True)
            return

        add_balance(game["creator"], game["bet"])
        game["status"] = "cancelled"

        await q.message.edit_text(
            f"❌ بازی لغو شد.\n{game['bet']:,} DOGS به سازنده برگشت."
        )
        return

    if action == "game_join":
        if game["status"] != "waiting":
            await q.answer("❌ این بازی قبلاً شروع شده.", show_alert=True)
            return

        if uid == game["creator"]:
            await q.answer("❌ سازنده نمی‌تواند وارد بازی خودش شود.", show_alert=True)
            return

        create_user(q.from_user)

        if get_balance(uid) < game["bet"]:
            await q.answer("❌ موجودی کافی نیست.", show_alert=True)
            return

        if not remove_balance(uid, game["bet"]):
            await q.answer("❌ موجودی کافی نیست.", show_alert=True)
            return

        game["joiner"] = uid
        game["joiner_name"] = q.from_user.first_name or ""
        game["status"] = "playing"

        await q.message.edit_text(
            f"🎮 بازی شروع شد!\n\n"
            f"👤 بازیکن ۱: {game['creator_name']}\n"
            f"👤 بازیکن ۲: {game['joiner_name']}\n"
            f"💰 شرط هر نفر: {game['bet']:,} DOGS\n\n"
            "🎲 در حال تعیین نتیجه..."
        )

        # Random fair winner. Both stakes were already reserved.
        winner = random.choice([game["creator"], game["joiner"]])
        loser = game["joiner"] if winner == game["creator"] else game["creator"]

        # Winner receives the total pot.
        pot = game["bet"] * 2
        add_balance(winner, pot)

        game["winner"] = winner
        game["loser"] = loser
        game["status"] = "finished"
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
            f"💰 جایزه: {pot:,} DOGS"
        )

        await q.message.edit_text(result)

        for player in [winner, loser]:
            try:
                if player == winner:
                    await context.bot.send_message(
                        player,
                        result + "\n\n🎉 تبریک! مبلغ بازی به موجودی شما اضافه شد."
                    )
                else:
                    await context.bot.send_message(
                        player,
                        result + "\n\n❌ این بازی را باختید."
                    )
            except Exception:
                pass


# =========================
# SIMPLE TEXT ROUTER
# =========================

async def text_router(update, context):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    uid = update.effective_user.id

    # Owner state gets priority.
    if uid in OWNER_STATE:
        await owner_state_receive(update, context)
        return

    # Transfer state.
    if uid in TRANSFER_DATA:
        await transfer_amount(update, context)
        return

    # Deposit amount/receipt and withdraw steps.
    if uid in DEPOSIT_DATA:
        if DEPOSIT_DATA[uid].get("step") == "amount":
            await deposit_amount(update, context)
            return
        if DEPOSIT_DATA[uid].get("step") == "receipt":
            await deposit_receipt(update, context)
            return

    if uid in WITHDRAW_DATA:
        if WITHDRAW_DATA[uid].get("step") == "amount":
            await withdraw_amount(update, context)
            return
        if WITHDRAW_DATA[uid].get("step") == "wallet":
            await withdraw_wallet(update, context)
            return

    if text == "💳 واریزی":
        await deposit_start(update, context)
    elif text == "💰 برداشت":
        await withdraw_start(update, context)
    elif text == "👥 زیرمجموعه":
        await referral_menu(update, context)
    elif text == "🎧 پشتیبانی":
        await support(update, context)
    elif text == "👤 پروفایل":
        await profile(update, context)
    elif text == "👥 انتقال":
        await transfer_start(update, context)
    elif text == "⚙️ پنل مدیریت":
        await owner_panel(update, context)
    elif text == "🔙 برگشت":
        await update.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=main_keyboard(uid),
        )


async def photo_router(update, context):
    uid = update.effective_user.id
    if uid in DEPOSIT_DATA:
        await deposit_receipt(update, context)


# =========================
# COMMANDS
# =========================

async def transfer_command(update, context):
    await transfer_start(update, context)


async def game_command(update, context):
    await game_create(update, context)


async def admin_command(update, context):
    await owner_panel(update, context)


async def transfer_owner_command(update, context):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ فقط مالک اجازه دارد.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ استفاده:\n/transferowner ID"
        )
        return

    try:
        new_owner = int(context.args[0])
    except Exception:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return

    if str(new_owner) not in data["users"]:
        await update.message.reply_text(
            "❌ کاربر باید قبلاً داخل ربات ثبت شده باشد."
        )
        return

    data["owner"] = new_owner
    save_data()

    await update.message.reply_text(
        f"✅ انتقال مالکیت انجام شد.\n👑 مالک جدید: {new_owner}"
    )


# =========================
# CALLBACK: JOIN
# =========================

async def check_join_callback(update, context):
    q = update.callback_query
    await q.answer()

    if await check_join(q.from_user.id, context):
        create_user(q.from_user)
        if not data["users"][str(q.from_user.id)].get("phone"):
            try:
                await q.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                q.from_user.id,
                "📱 شماره خود را ارسال کنید.\nفقط شماره ایران +98 قبول است.",
                reply_markup=phone_keyboard(),
            )
        else:
            await q.message.reply_text(
                "✅ عضویت تایید شد.",
                reply_markup=main_keyboard(q.from_user.id),
            )
    else:
        await q.answer(
            "❌ هنوز عضو کانال و گپ نیستید.",
            show_alert=True,
        )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(update, context):
    print("BOT ERROR:", context.error)
    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__,
    )


# =========================
# MAIN
# =========================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("transfer", transfer_command))
    app.add_handler(CommandHandler("transferowner", transfer_owner_command))
    app.add_handler(CommandHandler("game", game_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Callbacks
    app.add_handler(
        CallbackQueryHandler(check_join_callback, pattern=r"^check_join$")
    )
    app.add_handler(
        CallbackQueryHandler(deposit_type, pattern=r"^dep_(ultra|exchange)$")
    )
    app.add_handler(
        CallbackQueryHandler(deposit_decision, pattern=r"^dep_(ok|no):")
    )
    app.add_handler(
        CallbackQueryHandler(withdraw_decision, pattern=r"^with_(ok|no):")
    )
    app.add_handler(
        CallbackQueryHandler(owner_transfer_decision, pattern=r"^owner_(yes|no)")
    )
    app.add_handler(
        CallbackQueryHandler(game_callback, pattern=r"^game_(join|cancel):")
    )
    app.add_handler(
        CallbackQueryHandler(owner_panel_callback, pattern=r"^adm_")
    )

    # Contact
    app.add_handler(
        MessageHandler(filters.CONTACT, phone_receive)
    )

    # Photos
    app.add_handler(
        MessageHandler(filters.PHOTO, photo_router)
    )

    # Text router
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
    )

    app.add_error_handler(error_handler)

    print("BOT STARTED")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
