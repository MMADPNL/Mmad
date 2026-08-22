import os
import json
import time
import random
import asyncio
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8552447077

ULTRA_ADDRESS = "@CyyFr"
EXCHANGE_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

MIN_GAME = 500
MAX_GAME = 20000

DATA_FILE = "data.json"

# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "owner": OWNER_ID,
    "enabled": True,
    "channel": "",
    "group": "",
    "users": {},
    "deposits": {},
    "withdraws": {},
    "games": {},
}

# Locks prevent double-clicks / duplicate processing.
user_locks = {}
game_locks = {}
data_lock = asyncio.Lock()


def get_user_lock(uid):
    uid = int(uid)
    if uid not in user_locks:
        user_locks[uid] = asyncio.Lock()
    return user_locks[uid]


def get_game_lock(gid):
    if gid not in game_locks:
        game_locks[gid] = asyncio.Lock()
    return game_locks[gid]


# =========================================================
# SAFE DATA
# =========================================================

def merge_defaults(obj):
    if not isinstance(obj, dict):
        obj = {}

    for key, value in DEFAULT_DATA.items():
        if key not in obj:
            obj[key] = {} if isinstance(value, dict) else value

    for key in ("users", "deposits", "withdraws", "games"):
        if not isinstance(obj.get(key), dict):
            obj[key] = {}

    return obj


def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return merge_defaults(json.load(f))
    except Exception:
        print("LOAD ERROR")
        traceback.print_exc()

    return merge_defaults(DEFAULT_DATA.copy())


data = load_data()


def save_data():
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception:
        print("SAVE ERROR")
        traceback.print_exc()


# =========================================================
# USERS / BALANCE
# =========================================================

def create_user(user):
    uid = str(user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "date": datetime.now().isoformat(),
        }
        save_data()
        return

    old = data["users"][uid]
    old["name"] = user.first_name or ""
    old["username"] = user.username or ""


def get_balance(uid):
    user = data["users"].get(str(uid))
    if not user:
        return 0
    try:
        return int(user.get("balance", 0))
    except Exception:
        return 0


def add_balance(uid, amount):
    uid = str(uid)
    if uid not in data["users"]:
        return False
    data["users"][uid]["balance"] = get_balance(uid) + int(amount)
    save_data()
    return True


def remove_balance(uid, amount):
    uid = str(uid)
    amount = int(amount)

    if uid not in data["users"]:
        return False

    if get_balance(uid) < amount:
        return False

    data["users"][uid]["balance"] -= amount
    save_data()
    return True


def is_owner(uid):
    try:
        return int(uid) == int(data.get("owner", OWNER_ID))
    except Exception:
        return False


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):
    rows = [
        ["💳 واریزی", "💰 برداشت"],
        ["👤 پروفایل", "🎧 پشتیبانی"],
        ["👥 انتقال"],
    ]

    if is_owner(uid):
        rows.append(["⚙️ پنل مدیریت"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_keyboard():
    enabled = bool(data.get("enabled", True))
    status = "🟢 روشن" if enabled else "🔴 خاموش"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🤖 ربات: {status}", callback_data="admin_toggle")],
        [
            InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
            InlineKeyboardButton("📢 کانال اجباری", callback_data="admin_channel"),
        ],
        [
            InlineKeyboardButton("👥 گپ اجباری", callback_data="admin_group"),
        ],
    ])


# =========================================================
# START / PROFILE
# =========================================================

async def start(update, context):
    user = update.effective_user
    create_user(user)

    await update.message.reply_text(
        "🤖 خوش آمدید\n\n"
        f"👤 {user.first_name or ''}\n"
        f"💰 موجودی: {get_balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id),
    )


async def profile(update, context):
    user = update.effective_user
    create_user(user)

    await update.message.reply_text(
        "👤 پروفایل\n\n"
        f"🆔 آیدی: {user.id}\n"
        f"💰 موجودی: {get_balance(user.id):,} DOGS"
    )


# =========================================================
# SUPPORT - LOCKED STATE
# =========================================================

async def support(update, context):
    context.user_data.clear()
    context.user_data["state"] = "support"

    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        "پیامت رو ارسال کن."
    )


async def support_message(update, context):
    if context.user_data.get("state") != "support":
        return False

    user = update.effective_user
    text = update.message.text or ""

    if not text.strip():
        await update.message.reply_text("❌ پیام خالی است.")
        return True

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "🎧 پیام پشتیبانی جدید\n\n"
                f"👤 نام: {user.first_name or ''}\n"
                f"🆔 آیدی: {user.id}\n"
                f"🔹 یوزرنیم: @{user.username if user.username else 'ندارد'}\n\n"
                f"💬 پیام:\n{text}"
            ),
        )
        context.user_data.clear()
        await update.message.reply_text("✅ پیام شما سریع برای مالک ارسال شد.")
    except Exception:
        await update.message.reply_text("❌ ارسال پیام انجام نشد. دوباره تلاش کنید.")

    return True


# =========================================================
# DEPOSIT
# =========================================================

async def deposit_menu(update, context):
    context.user_data.clear()

    await update.message.reply_text(
        "💳 واریز DOGS\n\nروش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🟣 اولترا", callback_data="dep_method_ultra"),
                InlineKeyboardButton("🏦 صرافی", callback_data="dep_method_exchange"),
            ]
        ]),
    )


async def deposit_select(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "dep_method_ultra":
        method = "ultra"
    elif q.data == "dep_method_exchange":
        method = "exchange"
    else:
        return

    context.user_data.clear()
    context.user_data["state"] = "dep_amount"
    context.user_data["method"] = method

    await q.message.reply_text(
        f"💰 مقدار DOGS را وارد کنید.\n\nحداقل واریز: {MIN_DEPOSIT:,} DOGS"
    )


async def deposit_amount(update, context):
    if context.user_data.get("state") != "dep_amount":
        return False

    try:
        amount = int((update.message.text or "").strip())
    except Exception:
        await update.message.reply_text("❌ فقط عدد ارسال کنید.")
        return True

    if amount < MIN_DEPOSIT:
        await update.message.reply_text(
            f"❌ حداقل واریز {MIN_DEPOSIT:,} DOGS است."
        )
        return True

    method = context.user_data.get("method")
    if method not in ("ultra", "exchange"):
        context.user_data.clear()
        await update.message.reply_text("❌ درخواست واریز منقضی شد. دوباره شروع کنید.")
        return True

    context.user_data["amount"] = amount
    context.user_data["state"] = "dep_receipt"

    if method == "ultra":
        text = (
            "🟣 واریز اولترا\n\n"
            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"
            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"
            f"{ULTRA_ADDRESS}\n\n"
            "فرصت مثال:\n\n"
            f"\"ULTRA {amount} DOGS\"\n"
            f"\"{ULTRA_ADDRESS}\"\n\n"
            "پس از ارسال، رسید را در همین چت ارسال کنید.\n\n"
            "📸 شات یا پیام تراکنش را بفرستید.\n\n"
            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"
        )
    else:
        text = (
            "🏦 واریز صرافی\n\n"
            f"💰 مبلغ واریز شما: {amount:,} DOGS\n\n"
            "لطفاً DOGS مورد نظر را از طریق صرافی به این ولت بزنید:\n\n"
            f"{EXCHANGE_WALLET}\n\n"
            f"مبلغ: {amount:,} DOGS\n\n"
            "پس از ارسال، شات یا لینک هش تراکنش را در همین چت ارسال کنید.\n\n"
            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅"
        )

    await update.message.reply_text(text)
    return True


async def deposit_receipt(update, context):
    if context.user_data.get("state") != "dep_receipt":
        return False

    user = update.effective_user
    amount = context.user_data.get("amount")
    method = context.user_data.get("method")

    if not amount or method not in ("ultra", "exchange"):
        context.user_data.clear()
        await update.message.reply_text("❌ درخواست واریز منقضی شده.")
        return True

    if update.message.photo:
        receipt = update.message.photo[-1].file_id
        receipt_type = "photo"
    elif update.message.text:
        receipt = update.message.text.strip()
        receipt_type = "text"
    else:
        await update.message.reply_text("❌ فقط عکس یا متن رسید ارسال کنید.")
        return True

    req = f"DEP_{user.id}_{time.time_ns()}"

    data["deposits"][req] = {
        "id": req,
        "user": user.id,
        "name": user.first_name or "",
        "username": user.username or "",
        "amount": int(amount),
        "method": method,
        "receipt": receipt,
        "type": receipt_type,
        "status": "pending",
    }
    save_data()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید شما ثبت شد.\n\n⏳ منتظر تأیید مالک باشید."
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"dep_approve_{req}"),
            InlineKeyboardButton("❌ رد", callback_data=f"dep_reject_{req}"),
        ]
    ])

    caption = (
        "💳 واریزی جدید\n\n"
        f"👤 نام: {user.first_name or ''}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"💳 روش: {method}\n\n"
        f"🆔 درخواست: {req}"
    )

    try:
        if receipt_type == "photo":
            await context.bot.send_photo(
                chat_id=OWNER_ID,
                photo=receipt,
                caption=caption,
                reply_markup=buttons,
            )
        else:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=caption + f"\n\n📎 رسید:\n{receipt}",
                reply_markup=buttons,
            )
    except Exception:
        print("DEPOSIT OWNER SEND ERROR")
        traceback.print_exc()

    return True


# =========================================================
# WITHDRAW
# =========================================================

async def withdraw_menu(update, context):
    user = update.effective_user
    create_user(user)

    context.user_data.clear()

    if get_balance(user.id) < MIN_WITHDRAW:
        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی: {get_balance(user.id):,} DOGS\n"
            f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS"
        )
        return

    context.user_data["state"] = "wd_amount"

    await update.message.reply_text(
        "💰 برداشت DOGS\n\n"
        f"مبلغ را وارد کنید.\nحداقل: {MIN_WITHDRAW:,} DOGS"
    )


async def withdraw_amount(update, context):
    if context.user_data.get("state") != "wd_amount":
        return False

    user = update.effective_user

    try:
        amount = int((update.message.text or "").strip())
    except Exception:
        await update.message.reply_text("❌ فقط عدد ارسال کنید.")
        return True

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW:,} DOGS است."
        )
        return True

    if get_balance(user.id) < amount:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return True

    context.user_data["withdraw_amount"] = amount
    context.user_data["state"] = "wd_address"

    await update.message.reply_text(
        "📍 حالا آیدی یا ولت دریافت را ارسال کنید."
    )
    return True


async def withdraw_address(update, context):
    if context.user_data.get("state") != "wd_address":
        return False

    user = update.effective_user
    amount = context.user_data.get("withdraw_amount")
    address = (update.message.text or "").strip()

    if not amount or not address:
        await update.message.reply_text("❌ اطلاعات برداشت ناقص است.")
        return True

    async with get_user_lock(user.id):
        if get_balance(user.id) < amount:
            context.user_data.clear()
            await update.message.reply_text("❌ موجودی دیگر کافی نیست.")
            return True

        if not remove_balance(user.id, amount):
            context.user_data.clear()
            await update.message.reply_text("❌ خطا در کسر موجودی.")
            return True

        req = f"WD_{user.id}_{time.time_ns()}"

        data["withdraws"][req] = {
            "id": req,
            "user": user.id,
            "amount": int(amount),
            "address": address,
            "status": "pending",
        }
        save_data()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        "⏳ منتظر تأیید مالک باشید."
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"wd_approve_{req}"),
            InlineKeyboardButton("❌ رد", callback_data=f"wd_reject_{req}"),
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "💰 برداشت جدید\n\n"
                f"👤 آیدی کاربر: {user.id}\n"
                f"💰 مبلغ: {amount:,} DOGS\n\n"
                f"📍 آدرس/آیدی:\n{address}\n\n"
                f"🆔 درخواست: {req}"
            ),
            reply_markup=buttons,
        )
    except Exception:
        print("WITHDRAW OWNER SEND ERROR")
        traceback.print_exc()

    return True


# =========================================================
# DEPOSIT / WITHDRAW APPROVE-REJECT
# =========================================================

async def approve_reject(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("⛔ فقط مالک می‌تواند.", show_alert=True)
        return

    parts = q.data.split("_", 2)
    if len(parts) != 3:
        return

    kind, action, req = parts
    store = data["deposits"] if kind == "dep" else data["withdraws"]

    async with data_lock:
        item = store.get(req)

        if not item:
            await q.edit_message_reply_markup(reply_markup=None)
            await q.answer("درخواست پیدا نشد.", show_alert=True)
            return

        if item.get("status") != "pending":
            await q.answer("⚠️ این درخواست قبلاً بررسی شده.", show_alert=True)
            return

        uid = int(item["user"])

        if kind == "dep":
            if action == "approve":
                add_balance(uid, int(item["amount"]))
                item["status"] = "approved"
                save_data()

                await q.edit_message_text(
                    "✅ واریز تایید شد\n\n"
                    f"💰 مبلغ: {int(item['amount']):,} DOGS"
                )
                try:
                    await context.bot.send_message(
                        uid,
                        "✅ واریز شما تایید شد.\n\n"
                        f"💰 +{int(item['amount']):,} DOGS\n"
                        f"💳 موجودی: {get_balance(uid):,} DOGS"
                    )
                except Exception:
                    pass
            else:
                item["status"] = "rejected"
                save_data()

                await q.edit_message_text("❌ واریز رد شد.")
                try:
                    await context.bot.send_message(uid, "❌ واریز شما رد شد.")
                except Exception:
                    pass

        elif kind == "wd":
            if action == "approve":
                item["status"] = "approved"
                save_data()

                await q.edit_message_text(
                    "✅ برداشت تایید شد\n\n"
                    f"💰 مبلغ: {int(item['amount']):,} DOGS"
                )
                try:
                    await context.bot.send_message(
                        uid,
                        "✅ برداشت شما تایید شد.\n\n"
                        f"💰 مبلغ: {int(item['amount']):,} DOGS"
                    )
                except Exception:
                    pass
            else:
                item["status"] = "rejected"
                add_balance(uid, int(item["amount"]))
                save_data()

                await q.edit_message_text(
                    "❌ برداشت رد شد\n\n"
                    f"💰 {int(item['amount']):,} DOGS به موجودی برگشت."
                )
                try:
                    await context.bot.send_message(
                        uid,
                        "❌ برداشت شما رد شد.\n\n"
                        f"💰 +{int(item['amount']):,} DOGS برگشت داده شد.\n"
                        f"💳 موجودی: {get_balance(uid):,} DOGS"
                    )
                except Exception:
                    pass


# =========================================================
# TRANSFER IN GROUP / PRIVATE
# Usage: reply to a user's message, then: انتقال 500
# =========================================================

async def transfer_command(update, context):
    user = update.effective_user
    create_user(user)

    if len(update.message.text.split()) != 2:
        await update.message.reply_text(
            "❌ فرمت صحیح:\n"
            "روی پیام شخص ریپلای کن و بنویس:\n"
            "انتقال 500"
        )
        return

    try:
        amount = int(update.message.text.split()[1])
    except Exception:
        await update.message.reply_text("❌ مبلغ باید عدد باشد.")
        return

    if amount <= 0:
        await update.message.reply_text("❌ مبلغ نامعتبر است.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ برای انتقال باید روی پیام گیرنده ریپلای کنی."
        )
        return

    target = update.message.reply_to_message.from_user

    if not target or target.is_bot:
        await update.message.reply_text("❌ انتقال به ربات امکان‌پذیر نیست.")
        return

    if target.id == user.id:
        await update.message.reply_text("❌ نمی‌توانی به خودت انتقال بدهی.")
        return

    create_user(target)

    first, second = sorted([user.id, target.id])

    async with get_user_lock(first):
        async with get_user_lock(second):
            if get_balance(user.id) < amount:
                await update.message.reply_text("❌ موجودی کافی نیست.")
                return

            if not remove_balance(user.id, amount):
                await update.message.reply_text("❌ انتقال انجام نشد.")
                return

            add_balance(target.id, amount)

    await update.message.reply_text(
        "✅ انتقال انجام شد.\n\n"
        f"👤 گیرنده: {target.first_name or target.id}\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"💳 موجودی شما: {get_balance(user.id):,} DOGS"
    )

    # Private notifications, errors here must not break the transfer.
    try:
        await context.bot.send_message(
            user.id,
            f"📤 انتقال انجام شد\n\n"
            f"💰 -{amount:,} DOGS\n"
            f"👤 گیرنده: {target.first_name or target.id}\n"
            f"💳 موجودی: {get_balance(user.id):,} DOGS"
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            target.id,
            f"📥 انتقال دریافت شد\n\n"
            f"💰 +{amount:,} DOGS\n"
            f"👤 فرستنده: {user.first_name or user.id}\n"
            f"💳 موجودی: {get_balance(target.id):,} DOGS"
        )
    except Exception:
        pass


# =========================================================
# GAME
# =========================================================

async def game_command(update, context):
    # Game command remains high-priority and only works in groups.
    if update.effective_chat.type == "private":
        return

    if not data.get("enabled", True):
        return

    user = update.effective_user
    create_user(user)

    parts = (update.message.text or "").strip().split()
    if len(parts) != 2:
        await update.message.reply_text(
            f"❌ فرمت:\nبازی 500\n\n"
            f"حداقل: {MIN_GAME:,}\n"
            f"حداکثر: {MAX_GAME:,}"
        )
        return

    try:
        amount = int(parts[1])
    except Exception:
        await update.message.reply_text("❌ مبلغ بازی باید عدد باشد.")
        return

    if amount < MIN_GAME or amount > MAX_GAME:
        await update.message.reply_text(
            f"❌ مبلغ بازی باید بین {MIN_GAME:,} تا {MAX_GAME:,} DOGS باشد."
        )
        return

    async with get_user_lock(user.id):
        if get_balance(user.id) < amount:
            await update.message.reply_text("❌ موجودی کافی نیست.")
            return

    # Very unlikely collision-safe ID.
    gid = f"G_{update.effective_chat.id}_{user.id}_{time.time_ns()}"

    data["games"][gid] = {
        "id": gid,
        "owner": user.id,
        "owner_name": user.first_name or "",
        "amount": amount,
        "chat": update.effective_chat.id,
        "status": "waiting",
        "created": time.time(),
    }
    save_data()

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👥 بازی با دوستان",
                callback_data=f"game_join_{gid}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=f"game_cancel_{gid}"
            )
        ],
    ])

    await update.message.reply_text(
        "🎮 بازی جدید\n\n"
        f"💰 مبلغ بازی: {amount:,} DOGS\n\n"
        f"👤 سازنده: {user.first_name or user.id}\n\n"
        "یک نفر می‌تواند وارد بازی شود.",
        reply_markup=kb,
    )


async def game_callback(update, context):
    q = update.callback_query
    await q.answer()

    user = q.from_user

    if q.data.startswith("game_cancel_"):
        gid = q.data[len("game_cancel_"):]

        async with get_game_lock(gid):
            game = data["games"].get(gid)

            if not game:
                await q.answer("بازی پیدا نشد.", show_alert=True)
                return

            if game["status"] != "waiting":
                await q.answer("این بازی قبلاً تمام شده.", show_alert=True)
                return

            if int(game["owner"]) != user.id:
                await q.answer("فقط سازنده بازی می‌تواند لغو کند.", show_alert=True)
                return

            game["status"] = "cancelled"
            save_data()

        await q.edit_message_text("❌ بازی لغو شد.")
        return

    if not q.data.startswith("game_join_"):
        return

    gid = q.data[len("game_join_"):]

    async with get_game_lock(gid):
        game = data["games"].get(gid)

        if not game:
            await q.answer("بازی پیدا نشد.", show_alert=True)
            return

        if game["status"] != "waiting":
            await q.answer("⚠️ این بازی قبلاً وارد شده یا تمام شده.", show_alert=True)
            return

        if int(game["owner"]) == user.id:
            await q.answer("❌ خودت نمی‌توانی وارد بازی خودت شوی.", show_alert=True)
            return

        create_user(user)

        amount = int(game["amount"])
        owner_id = int(game["owner"])

        # Lock both players in deterministic order.
        first, second = sorted([owner_id, user.id])

        async with get_user_lock(first):
            async with get_user_lock(second):
                if get_balance(owner_id) < amount:
                    game["status"] = "cancelled"
                    save_data()
                    await q.edit_message_text(
                        "❌ بازی لغو شد؛ موجودی سازنده کافی نیست."
                    )
                    return

                if get_balance(user.id) < amount:
                    await q.answer("❌ موجودی شما کافی نیست.", show_alert=True)
                    return

                if not remove_balance(owner_id, amount):
                    await q.answer("❌ خطا در موجودی بازیکن اول.", show_alert=True)
                    return

                if not remove_balance(user.id, amount):
                    # Roll back player 1 immediately.
                    add_balance(owner_id, amount)
                    await q.answer("❌ خطا در موجودی بازیکن دوم.", show_alert=True)
                    return

                # Total pot = 2 * amount.
                # Winner receives 90%, owner gets 10%.
                total = amount * 2
                winner_prize = int(total * 0.90)
                owner_fee = total - winner_prize

                winner = random.choice([owner_id, user.id])
                loser = user.id if winner == owner_id else owner_id

                add_balance(winner, winner_prize)
                add_balance(OWNER_ID, owner_fee)

                game["status"] = "done"
                game["player2"] = user.id
                game["winner"] = winner
                game["loser"] = loser
                game["prize"] = winner_prize
                game["owner_fee"] = owner_fee
                save_data()

        winner_balance = get_balance(winner)
        loser_balance = get_balance(loser)

        await q.edit_message_text(
            "🎮 نتیجه بازی\n\n"
            f"👤 بازیکن اول: {owner_id}\n"
            f"👤 بازیکن دوم: {user.id}\n\n"
            f"🏆 برنده: {winner}\n"
            f"❌ بازنده: {loser}\n\n"
            f"💰 جایزه برنده: {winner_prize:,} DOGS\n"
            f"👑 سهم مالک: {owner_fee:,} DOGS"
        )

        # Private result messages.
        try:
            await context.bot.send_message(
                winner,
                "🏆 تبریک! برنده بازی شدی 🎉\n\n"
                f"💰 مبلغ اضافه‌شده: +{winner_prize:,} DOGS\n"
                f"💳 موجودی جدید: {winner_balance:,} DOGS"
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                loser,
                "❌ بازی را باختی.\n\n"
                f"💸 مبلغ باخته‌شده: -{amount:,} DOGS\n"
                f"💳 موجودی جدید: {loser_balance:,} DOGS"
            )
        except Exception:
            pass


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update, context):
    user = update.effective_user

    if not is_owner(user.id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=admin_keyboard()
    )


async def admin_callback(update, context):
    q = update.callback_query
    await q.answer()

    if not is_owner(q.from_user.id):
        await q.answer("⛔ فقط مالک.", show_alert=True)
        return

    if q.data == "admin_toggle":
        data["enabled"] = not bool(data.get("enabled", True))
        save_data()
        await q.edit_message_text(
            "⚙️ پنل مدیریت",
            reply_markup=admin_keyboard()
        )
        return

    if q.data == "admin_stats":
        users = len(data["users"])
        deposits = len(data["deposits"])
        withdraws = len(data["withdraws"])
        games = len(data["games"])

        await q.message.reply_text(
            "📊 آمار\n\n"
            f"👤 کاربران: {users}\n"
            f"💳 واریزی‌ها: {deposits}\n"
            f"💰 برداشت‌ها: {withdraws}\n"
            f"🎮 بازی‌ها: {games}"
        )
        return

    if q.data == "admin_channel":
        context.user_data.clear()
        context.user_data["state"] = "admin_channel"
        await q.message.reply_text(
            "📢 آیدی کانال اجباری را ارسال کن.\n"
            "برای خاموش کردن: خاموش"
        )
        return

    if q.data == "admin_group":
        context.user_data.clear()
        context.user_data["state"] = "admin_group"
        await q.message.reply_text(
            "👥 آیدی گپ اجباری را ارسال کن.\n"
            "برای خاموش کردن: خاموش"
        )
        return


async def admin_setting_message(update, context):
    state = context.user_data.get("state")

    if not is_owner(update.effective_user.id):
        return False

    if state not in ("admin_channel", "admin_group"):
        return False

    value = (update.message.text or "").strip()

    if value.lower() == "خاموش":
        value = ""

    if state == "admin_channel":
        data["channel"] = value
        msg = f"📢 کانال اجباری تنظیم شد:\n{value or 'خاموش'}"
    else:
        data["group"] = value
        msg = f"👥 گپ اجباری تنظیم شد:\n{value or 'خاموش'}"

    save_data()
    context.user_data.clear()

    await update.message.reply_text(msg)
    return True


# =========================================================
# TEXT ROUTER
# =========================================================

async def text_router(update, context):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    create_user(user)

    text = update.message.text.strip()

    # These are checked BEFORE generic state handling.
    # This keeps the old "بازی 500" command above the router.
    if text.startswith("بازی "):
        await game_command(update, context)
        return

    if text.startswith("انتقال "):
        await transfer_command(update, context)
        return

    if text == "💳 واریزی":
        await deposit_menu(update, context)
        return

    if text == "💰 برداشت":
        await withdraw_menu(update, context)
        return

    if text == "👤 پروفایل":
        await profile(update, context)
        return

    if text == "🎧 پشتیبانی":
        await support(update, context)
        return

    if text == "👥 انتقال":
        context.user_data.clear()
        context.user_data["state"] = "transfer_help"
        await update.message.reply_text(
            "👥 انتقال DOGS\n\n"
            "روی پیام شخص موردنظر ریپلای کن و بنویس:\n"
            "انتقال 500"
        )
        return

    if text == "⚙️ پنل مدیریت":
        await admin_panel(update, context)
        return

    # Admin settings must be checked before deposit/withdraw states.
    if await admin_setting_message(update, context):
        return

    # Locked state handlers.
    if await support_message(update, context):
        return

    if await deposit_amount(update, context):
        return

    if await deposit_receipt(update, context):
        return

    if await withdraw_amount(update, context):
        return

    if await withdraw_address(update, context):
        return

    if context.user_data.get("state") == "transfer_help":
        await update.message.reply_text(
            "❌ برای انتقال، روی پیام گیرنده ریپلای کن و بنویس:\n"
            "انتقال 500"
        )
        return


async def photo_router(update, context):
    if await deposit_receipt(update, context):
        return


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(update, context):
    print("BOT ERROR:")
    try:
        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )
    except Exception:
        traceback.print_exc()


# =========================================================
# MAIN
# =========================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is missing."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start), group=0)

    # GAME COMMAND IS HIGH PRIORITY
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^بازی\s+\d+$"),
            game_command,
        ),
        group=0,
    )

    # TRANSFER COMMAND
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^انتقال\s+\d+$"),
            transfer_command,
        ),
        group=0,
    )

    # Deposit buttons
    app.add_handler(
        CallbackQueryHandler(
            deposit_select,
            pattern=r"^dep_method_(ultra|exchange)$",
        ),
        group=0,
    )

    # Deposit / Withdraw approve-reject
    app.add_handler(
        CallbackQueryHandler(
            approve_reject,
            pattern=r"^(dep|wd)_(approve|reject)_",
        ),
        group=0,
    )

    # Game buttons
    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^game_(join|cancel)_",
        ),
        group=0,
    )

    # Admin buttons
    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin_",
        ),
        group=0,
    )

    # Photos first: only deposit receipt state can consume them.
    app.add_handler(
        MessageHandler(filters.PHOTO, photo_router),
        group=1,
    )

    # All normal text.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        ),
        group=2,
    )

    app.add_error_handler(error_handler)

    print("BOT STARTED")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
