import json
import os
import random
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

# اولترا
ULTRA_ADDRESS = "@CyyFr"

# صرافی
EXCHANGE_WALLET = (
    "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"
)

# حداقل واریز
MIN_DEPOSIT = 5000

# حداقل برداشت
MIN_WITHDRAW = 10000

# بازی
MIN_GAME = 500
MAX_GAME = 20000

# درصد سهم مالک
GAME_FEE_PERCENT = 10

# رفرال
REFERRAL_REWARD = 50

# اجبار عضویت
FORCED_CHANNEL = "@TAK_BE_T"
FORCED_GROUP = "@TAK_B_ET"

# فایل اطلاعات
DATA_FILE = "bot_data.json"


# =========================================================
# DEFAULT DATA
# =========================================================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "forced_channel": FORCED_CHANNEL,
        "forced_group": FORCED_GROUP,
    },
}


# =========================================================
# DATABASE
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        base = json.loads(json.dumps(DEFAULT_DATA))

        if isinstance(loaded, dict):
            for key, value in loaded.items():
                if key == "settings" and isinstance(value, dict):
                    base["settings"].update(value)
                else:
                    base[key] = value

        return base

    except Exception as e:
        print("LOAD DATA ERROR:", e)
        return json.loads(json.dumps(DEFAULT_DATA))


data = load_data()


def save_data():
    temp_file = DATA_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print("SAVE DATA ERROR:", e)


# =========================================================
# USER
# =========================================================

def create_user(user):
    uid = str(user.id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "date": datetime.now().isoformat(),
        }

        save_data()

    else:
        data["users"][uid]["name"] = user.first_name or ""
        data["users"][uid]["username"] = user.username or ""

        if "balance" not in data["users"][uid]:
            data["users"][uid]["balance"] = 0

        if "referrals" not in data["users"][uid]:
            data["users"][uid]["referrals"] = 0

        if "referred_by" not in data["users"][uid]:
            data["users"][uid]["referred_by"] = None

        save_data()

    return data["users"][uid]


def get_user(uid):
    return data["users"].get(str(uid))


def balance(uid):
    user = get_user(uid)

    if not user:
        return 0

    return int(user.get("balance", 0))


def add_balance(uid, amount):
    user = get_user(uid)

    if not user:
        return False

    user["balance"] = balance(uid) + int(amount)
    save_data()

    return True


def remove_balance(uid, amount):
    user = get_user(uid)
    amount = int(amount)

    if not user:
        return False

    if balance(uid) < amount:
        return False

    user["balance"] -= amount
    save_data()

    return True


def is_owner(uid):
    return int(uid) == int(
        data.get("owner", OWNER_ID)
    )


def user_display(uid):
    user = get_user(uid)

    if not user:
        return str(uid)

    username = user.get("username", "")

    if username:
        return f"@{username}"

    name = user.get("name", "")

    if name:
        return name

    return str(uid)


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(uid):
    rows = [
        [
            "💳 واریزی",
            "👥 زیر مجموعه",
        ],
        [
            "👤 پروفایل",
            "💰 برداشت",
        ],
    ]

    if is_owner(uid):
        rows.append(
            [
                "⚙️ پنل مدیریت"
            ]
        )

    rows.append(
        [
            "🎧 پشتیبانی"
        ]
    )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


def back_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                "🔙 برگشت"
            ]
        ],
        resize_keyboard=True
    )


# =========================================================
# FORCED JOIN
# =========================================================

async def check_forced_join(update, context):
    user = update.effective_user

    if not user:
        return False

    if is_owner(user.id):
        return True

    channel = data["settings"].get(
        "forced_channel"
    )

    group = data["settings"].get(
        "forced_group"
    )

    missing = []

    checks = [
        (channel, "کانال"),
        (group, "گپ"),
    ]

    for chat_id, title in checks:

        if not chat_id:
            continue

        try:
            member = await context.bot.get_chat_member(
                chat_id,
                user.id
            )

            if member.status in (
                "left",
                "kicked"
            ):
                missing.append(
                    (
                        chat_id,
                        title
                    )
                )

        except Exception as e:
            print(
                f"JOIN CHECK ERROR {chat_id}: {e}"
            )

            # اگر چک کردن ممکن نبود،
            # کاربر را بی دلیل قفل نکن
            continue

    if not missing:
        return True

    buttons = []

    for chat_id, title in missing:

        username = str(chat_id)

        if username.startswith("@"):
            link = (
                "https://t.me/"
                + username[1:]
            )
        else:
            link = "https://t.me/TAK_BE_T"

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📢 عضویت در {title}",
                    url=link
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="check_join"
            )
        ]
    )

    text = (
        "🔒 برای استفاده از ربات "
        "ابتدا باید عضو موارد زیر شوید:\n\n"
    )

    for _, title in missing:
        text += f"• {title}\n"

    text += (
        "\nبعد از عضویت روی "
        "«بررسی عضویت» بزنید."
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    return False


# =========================================================
# BOT STATUS
# =========================================================

async def bot_available(update, context):
    user = update.effective_user

    if user and is_owner(user.id):
        return True

    if not data["settings"].get("bot", True):

        if update.callback_query:
            await update.callback_query.answer(
                "❌ ربات خاموش است.",
                show_alert=True
            )

        elif update.message:
            await update.message.reply_text(
                "❌ ربات موقتاً خاموش است."
            )

        return False

    return await check_forced_join(
        update,
        context
    )


# =========================================================
# START
# =========================================================

async def start(update, context):
    user = update.effective_user

    if not user:
        return

    create_user(user)

    if update.effective_chat.type != "private":

        await update.message.reply_text(
            "🤖 ربات فعال است.\n\n"
            "🎮 برای بازی بنویسید:\n"
            "بازی 500\n\n"
            f"💰 حداقل بازی: {MIN_GAME:,} DOGS\n"
            f"💰 حداکثر بازی: {MAX_GAME:,} DOGS",
            reply_markup=ReplyKeyboardRemove()
        )

        return

    if not await bot_available(update, context):
        return

    # =====================================================
    # REFERRAL
    # =====================================================

    if context.args:

        arg = context.args[0]

        if arg.startswith("ref_"):

            try:
                ref_id = int(arg[4:])

                if (
                    ref_id != user.id
                    and get_user(ref_id)
                ):

                    current = get_user(user.id)

                    if current.get("referred_by") is None:

                        current["referred_by"] = ref_id

                        ref_user = get_user(ref_id)

                        ref_user["referrals"] = (
                            int(
                                ref_user.get(
                                    "referrals",
                                    0
                                )
                            ) + 1
                        )

                        ref_user["balance"] = (
                            balance(ref_id)
                            + REFERRAL_REWARD
                        )

                        save_data()

            except Exception as e:
                print("REF ERROR:", e)

    context.user_data.clear()

    await update.message.reply_text(
        "🤖 به ربات خوش آمدید.\n\n"
        f"👤 {user.first_name}\n\n"
        f"💰 موجودی:\n"
        f"{balance(user.id):,} DOGS\n\n"
        "یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# PROFILE
# =========================================================

async def show_profile(update, context):
    user = update.effective_user

    create_user(user)

    profile = get_user(user.id)

    username = profile.get(
        "username",
        ""
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

    await update.message.reply_text(
        "👤 پروفایل شما\n\n"
        f"🆔 آیدی: {user.id}\n"
        f"👤 نام: {profile.get('name', '')}\n"
        f"🔹 یوزرنیم: {username_text}\n\n"
        f"💰 موجودی: {balance(user.id):,} DOGS\n"
        f"👥 زیرمجموعه: {profile.get('referrals', 0)}\n"
        f"🎁 پاداش هر رفرال: {REFERRAL_REWARD} DOGS",
        reply_markup=back_keyboard()
    )


# =========================================================
# REFERRAL
# =========================================================

async def show_referrals(update, context):
    user = update.effective_user

    create_user(user)

    bot_username = context.bot.username or "YourBot"

    link = (
        f"https://t.me/"
        f"{bot_username}"
        f"?start=ref_{user.id}"
    )

    referrals = get_user(user.id).get(
        "referrals",
        0
    )

    await update.message.reply_text(
        "👥 زیرمجموعه‌گیری\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"{link}\n\n"
        f"👥 تعداد رفرال: {referrals}\n\n"
        f"🎁 هر رفرال: {REFERRAL_REWARD} DOGS",
        reply_markup=back_keyboard()
    )


# =========================================================
# DEPOSIT MENU
# =========================================================

async def show_deposit(update, context):
    context.user_data.clear()

    await update.message.reply_text(
        "💳 واریزی DOGS\n\n"
        "روش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🟣 اولترا",
                        callback_data="deposit_ultra"
                    ),
                    InlineKeyboardButton(
                        "🏦 صرافی",
                        callback_data="deposit_exchange"
                    )
                ]
            ]
        )
    )


# =========================================================
# DEPOSIT METHOD
# =========================================================

async def deposit_method_callback(update, context):
    query = update.callback_query

    await query.answer()

    if not await bot_available(update, context):
        return

    if query.data == "deposit_ultra":

        method = "اولترا"

        context.user_data.clear()

        context.user_data["state"] = "deposit_amount"

        context.user_data["deposit_method"] = method

        await query.message.reply_text(
            "🟣 واریز اولترا\n\n"
            "💰 مبلغ واریز را وارد کنید:\n\n"
            "مثال:\n"
            "5000\n\n"
            f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS",
            reply_markup=back_keyboard()
        )

    elif query.data == "deposit_exchange":

        method = "صرافی"

        context.user_data.clear()

        context.user_data["state"] = "deposit_amount"

        context.user_data["deposit_method"] = method

        await query.message.reply_text(
            "🏦 واریز صرافی\n\n"
            "💰 مبلغ واریز را وارد کنید:\n\n"
            "مثال:\n"
            "5000\n\n"
            f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS",
            reply_markup=back_keyboard()
        )


# =========================================================
# DEPOSIT AMOUNT
# =========================================================

async def handle_deposit_amount(update, context):
    try:
        amount = int(
            update.message.text.strip()
        )

    except Exception:
        await update.message.reply_text(
            "❌ فقط عدد وارد کنید.\n\n"
            "مثال:\n"
            "5000"
        )
        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(
            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است.\n\n"
            "مبلغ دیگری وارد کنید."
        )

        return

    method = context.user_data.get(
        "deposit_method"
    )

    context.user_data["deposit_amount"] = amount

    context.user_data["state"] = "deposit_receipt"

    # =====================================================
    # ULTRA
    # =====================================================

    if method == "اولترا":

        await update.message.reply_text(
            "🟣 واریز اولترا\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را به این آیدی بزنید:\n\n"

            f"{ULTRA_ADDRESS}\n\n"

            "فرصت مثال:\n\n"

            f'"ULTRA {amount} DOGS"\n'
            f'"{ULTRA_ADDRESS}"\n\n'

            "پس از ارسال، رسید را در همین چت ارسال کنید.\n\n"

            "📸 شات یا لینک هش تراکنش را بفرستید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅",

            reply_markup=back_keyboard()
        )

    # =====================================================
    # EXCHANGE
    # =====================================================

    else:

        await update.message.reply_text(
            "🏦 واریز صرافی\n\n"

            f"💰 مبلغ واریز شما: "
            f"{amount:,} DOGS\n\n"

            "لطفاً DOGS مورد نظر را "
            "از طریق صرافی به این ولت بزنید:\n\n"

            f"{EXCHANGE_WALLET}\n\n"

            f"مبلغ: {amount:,} DOGS\n\n"

            "پس از ارسال، شات یا لینک هش تراکنش "
            "را در همین چت ارسال کنید.\n\n"

            "پس از تأیید ادمین، مبلغ شما واریز خواهد شد ✅",

            reply_markup=back_keyboard()
        )


# =========================================================
# DEPOSIT RECEIPT
# =========================================================

async def handle_deposit_receipt(update, context):
    user = update.effective_user

    amount = context.user_data.get(
        "deposit_amount"
    )

    method = context.user_data.get(
        "deposit_method"
    )

    if not amount or not method:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ اطلاعات واریزی پیدا نشد.\n"
            "لطفاً دوباره از بخش واریزی شروع کنید.",
            reply_markup=main_keyboard(user.id)
        )

        return

    # =====================================================
    # PHOTO
    # =====================================================

    if update.message.photo:

        photo = update.message.photo[-1]

        receipt_type = "photo"

        receipt = photo.file_id

        caption = update.message.caption or ""

    # =====================================================
    # TEXT / HASH / LINK
    # =====================================================

    elif update.message.text:

        receipt_type = "text"

        receipt = update.message.text.strip()

        caption = ""

        if not receipt:

            await update.message.reply_text(
                "❌ شات یا لینک هش تراکنش را ارسال کنید."
            )

            return

    else:

        await update.message.reply_text(
            "❌ لطفاً شات یا لینک هش تراکنش را ارسال کنید."
        )

        return

    request_id = (
        f"{user.id}_"
        f"{int(datetime.now().timestamp() * 1000)}"
    )

    data["deposits"][request_id] = {
        "id": request_id,
        "user_id": user.id,
        "name": user.first_name or "",
        "username": user.username or "",
        "amount": amount,
        "method": method,
        "receipt": receipt,
        "receipt_type": receipt_type,
        "caption": caption,
        "status": "pending",
        "date": datetime.now().isoformat(),
    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        f"💳 روش: {method}\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        "⏳ درخواست برای مالک ارسال شد.\n"
        "پس از تأیید، موجودی شما افزایش پیدا می‌کند.",
        reply_markup=main_keyboard(user.id)
    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (
        "💳 واریزی جدید\n\n"
        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n\n"
        f"💳 روش: {method}\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"🆔 شناسه درخواست:\n"
        f"{request_id}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"ok_dep_{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"no_dep_{request_id}"
                )
            ]
        ]
    )

    try:

        # =================================================
        # اگر شات است، خود عکس برای مالک ارسال شود
        # =================================================

        if receipt_type == "photo":

            full_caption = (
                owner_text
                + "\n\n"
                "📸 رسید کاربر در تصویر بالا است."
            )

            if caption:
                full_caption += (
                    "\n\n📝 توضیح کاربر:\n"
                    + caption
                )

            await context.bot.send_photo(
                chat_id=data["owner"],
                photo=receipt,
                caption=full_caption,
                reply_markup=keyboard
            )

        # =================================================
        # اگر لینک یا هش است
        # =================================================

        else:

            await context.bot.send_message(
                chat_id=data["owner"],
                text=(
                    owner_text
                    + "\n\n"
                    "📄 رسید / هش تراکنش:\n"
                    + receipt
                ),
                reply_markup=keyboard
            )

    except Exception as e:

        print(
            "❌ خطا در ارسال رسید به مالک:",
            e
        )

        try:

            await context.bot.send_message(
                chat_id=data["owner"],
                text=(
                    owner_text
                    + "\n\n"
                    "⚠️ ارسال عکس ناموفق بود.\n"
                    "File ID:\n"
                    f"{receipt}"
                ),
                reply_markup=keyboard
            )

        except Exception as e2:

            print(
                "❌ ارسال جایگزین هم ناموفق بود:",
                e2
            )


# =========================================================
# WITHDRAW
# =========================================================

async def show_withdraw(update, context):
    user = update.effective_user

    create_user(user)

    current = balance(user.id)

    if current < MIN_WITHDRAW:

        await update.message.reply_text(
            "💰 برداشت DOGS\n\n"
            f"💳 موجودی کل شما: {current:,} DOGS\n\n"
            "📜 قوانین برداشت:\n"
            f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
            "💸 کارمزد: بدون کارمزد\n\n"
            "❌ موجودی شما برای برداشت کافی نیست.",
            reply_markup=back_keyboard()
        )

        return

    context.user_data.clear()

    context.user_data["state"] = "withdraw_amount"

    await update.message.reply_text(
        "💰 برداشت DOGS\n\n"
        f"💳 موجودی کل شما: {current:,} DOGS\n\n"
        "📜 قوانین برداشت:\n"
        f"🔻 حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n"
        "💸 کارمزد: بدون کارمزد\n\n"
        "💰 مبلغ خود را وارد کنید.\n"
        "مثال: 10000",
        reply_markup=back_keyboard()
    )


# =========================================================
# WITHDRAW AMOUNT
# =========================================================

async def handle_withdraw_amount(update, context):
    user = update.effective_user

    try:

        amount = int(
            update.message.text.strip()
        )

    except Exception:

        await update.message.reply_text(
            "❌ فقط عدد ارسال کنید.\n\n"
            "مثال:\n"
            "10000"
        )

        return

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(
            f"❌ حداقل برداشت "
            f"{MIN_WITHDRAW:,} DOGS است."
        )

        return

    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💳 موجودی: {balance(user.id):,} DOGS"
        )

        return

    context.user_data["withdraw_amount"] = amount

    context.user_data["state"] = "withdraw_address"

    await update.message.reply_text(
        f"💰 مبلغ برداشت: {amount:,} DOGS\n\n"
        "لطفاً آدرس کیف پول DOGS خود را ارسال کنید.\n\n"
        "پس از ارسال آدرس، درخواست برای مالک ارسال می‌شود "
        "تا تأیید یا رد شود.",
        reply_markup=back_keyboard()
    )


# =========================================================
# WITHDRAW ADDRESS
# =========================================================

async def handle_withdraw_address(update, context):
    user = update.effective_user

    address = (
        update.message.text
        or ""
    ).strip()

    if len(address) < 10:

        await update.message.reply_text(
            "❌ آدرس کیف پول معتبر نیست."
        )

        return

    amount = context.user_data.get(
        "withdraw_amount"
    )

    if not amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ مبلغ برداشت پیدا نشد.\n"
            "دوباره از بخش برداشت شروع کنید.",
            reply_markup=main_keyboard(user.id)
        )

        return

    if balance(user.id) < amount:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ موجودی شما دیگر کافی نیست.",
            reply_markup=main_keyboard(user.id)
        )

        return

    # پول تا زمان بررسی مالک رزرو می‌شود
    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return

    request_id = (
        f"{user.id}_"
        f"{int(datetime.now().timestamp() * 1000)}"
    )

    data["withdraws"][request_id] = {
        "id": request_id,
        "user_id": user.id,
        "name": user.first_name or "",
        "username": user.username or "",
        "address": address,
        "amount": amount,
        "status": "pending",
        "date": datetime.now().isoformat(),
    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(
        "✅ درخواست برداشت ثبت شد.\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n"
        f"💳 آدرس:\n{address}\n\n"
        "⏳ منتظر تأیید مالک باشید.",
        reply_markup=main_keyboard(user.id)
    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (
        "💰 برداشت جدید\n\n"
        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {user.id}\n"
        f"🔹 یوزرنیم: {username}\n\n"
        f"💰 مبلغ: {amount:,} DOGS\n\n"
        f"💳 آدرس:\n{address}\n\n"
        f"🆔 شناسه:\n{request_id}\n\n"
        "⚠️ مبلغ از موجودی کاربر رزرو شده است."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=f"ok_wd_{request_id}"
                ),
                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=f"no_wd_{request_id}"
                )
            ]
        ]
    )

    try:

        await context.bot.send_message(
            chat_id=data["owner"],
            text=owner_text,
            reply_markup=keyboard
        )

    except Exception as e:

        print(
            "❌ خطا در ارسال برداشت به مالک:",
            e
        )

        add_balance(
            user.id,
            amount
        )

        data["withdraws"][request_id]["status"] = "failed"

        save_data()


# =========================================================
# SUPPORT
# =========================================================

async def show_support(update, context):

    await update.message.reply_text(
        "🎧 پشتیبانی\n\n"
        f"👤 {SUPPORT_USERNAME}",
        reply_markup=back_keyboard()
    )


# =========================================================
# HOME
# =========================================================

async def go_home(update, context):
    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(
        "🏠 منوی اصلی\n\n"
        f"💰 موجودی: {balance(user.id):,} DOGS",
        reply_markup=main_keyboard(user.id)
    )


# =========================================================
# GAME
# =========================================================

ACTIVE_GAMES = {}


async def game_command(update, context):
    user = update.effective_user

    if not user:
        return

    if update.effective_chat.type == "private":

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ انجام می‌شود."
        )

        return

    if not await bot_available(update, context):
        return

    create_user(user)

    try:

        parts = (
            update.message.text
            .strip()
            .split()
        )

        if len(parts) != 2:
            raise ValueError

        amount = int(parts[1])

    except Exception:

        await update.message.reply_text(
            "❌ فرمت اشتباه است.\n\n"
            "مثال:\n"
            "بازی 500"
        )

        return

    if amount < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل شرط "
            f"{MIN_GAME:,} DOGS است."
        )

        return

    if amount > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر شرط "
            f"{MAX_GAME:,} DOGS است."
        )

        return

    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ در این گپ یک بازی فعال است."
        )

        return

    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست.\n\n"
            f"💰 موجودی: {balance(user.id):,} DOGS"
        )

        return

    remove_balance(
        user.id,
        amount
    )

    ACTIVE_GAMES[chat_id] = {
        "creator": user.id,
        "amount": amount
    }

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎮 ورود به بازی",
                    callback_data="join_game"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ لغو بازی",
                    callback_data="cancel_game"
                )
            ]
        ]
    )

    await update.message.reply_text(
        "🎮 بازی ساخته شد\n\n"
        f"👤 سازنده: {user_display(user.id)}\n\n"
        f"💰 شرط: {amount:,} DOGS\n\n"
        "👥 نفر دوم وارد شود.",
        reply_markup=keyboard
    )


# =========================================================
# GAME CALLBACK
# =========================================================

async def game_callback(update, context):
    query = update.callback_query

    user = query.from_user

    if not await bot_available(update, context):
        return

    chat_id = query.message.chat.id

    game = ACTIVE_GAMES.get(chat_id)

    if not game:

        await query.answer(
            "❌ بازی فعال نیست.",
            show_alert=True
        )

        return

    if query.data == "cancel_game":

        if user.id != game["creator"]:

            await query.answer(
                "❌ فقط سازنده می‌تواند لغو کند.",
                show_alert=True
            )

            return

        add_balance(
            user.id,
            game["amount"]
        )

        del ACTIVE_GAMES[chat_id]

        await query.answer()

        await query.edit_message_text(
            "❌ بازی لغو شد.\n\n"
            f"💰 مبلغ {game['amount']:,} DOGS "
            "برگشت داده شد."
        )

        return

    if user.id == game["creator"]:

        await query.answer(
            "❌ نمی‌توانید وارد بازی خودتان شوید.",
            show_alert=True
        )

        return

    create_user(user)

    amount = game["amount"]

    if balance(user.id) < amount:

        await query.answer(
            "❌ موجودی کافی نیست.",
            show_alert=True
        )

        return

    remove_balance(
        user.id,
        amount
    )

    winner = random.choice(
        [
            game["creator"],
            user.id
        ]
    )

    if winner == game["creator"]:
        loser = user.id
    else:
        loser = game["creator"]

    # مجموع پول بازی
    total_pot = amount * 2

    # 10 درصد مالک
    owner_fee = (
        total_pot
        * GAME_FEE_PERCENT
        // 100
    )

    # 90 درصد برنده
    winner_prize = (
        total_pot
        - owner_fee
    )

    add_balance(
        winner,
        winner_prize
    )

    owner_id = data.get(
        "owner",
        OWNER_ID
    )

    if not get_user(owner_id):

        data["users"][str(owner_id)] = {
            "id": owner_id,
            "name": "OWNER",
            "username": "",
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "date": datetime.now().isoformat()
        }

        save_data()

    add_balance(
        owner_id,
        owner_fee
    )

    del ACTIVE_GAMES[chat_id]

    await query.answer()

    await query.edit_message_text(
        "🎮 نتیجه بازی\n\n"
        f"🏆 برنده:\n"
        f"{user_display(winner)}\n\n"
        f"💰 دریافتی برنده: "
        f"{winner_prize:,} DOGS\n\n"
        f"👑 سهم مالک: "
        f"{owner_fee:,} DOGS\n\n"
        f"😢 بازنده:\n"
        f"{user_display(loser)}"
    )


# =========================================================
# ADMIN DEPOSIT
# =========================================================

async def admin_deposit_callback(update, context):
    query = update.callback_query

    await query.answer()

    if not is_owner(query.from_user.id):
        return

    request_id = query.data.split("_", 2)[2]

    request = data["deposits"].get(request_id)

    if not request:

        await query.edit_message_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request["status"] != "pending":

        await query.answer(
            "این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = request["user_id"]

    if query.data.startswith("ok_dep_"):

        add_balance(
            uid,
            request["amount"]
        )

        request["status"] = "approved"

        await query.edit_message_text(
            "✅ واریز تأیید شد.\n\n"
            f"👤 کاربر: {user_display(uid)}\n"
            f"💰 مبلغ: {request['amount']:,} DOGS"
        )

        try:

            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "✅ واریز شما تأیید شد.\n\n"
                    f"💰 مبلغ: +{request['amount']:,} DOGS\n\n"
                    f"💳 موجودی جدید: "
                    f"{balance(uid):,} DOGS"
                )
            )

        except Exception:
            pass

    else:

        request["status"] = "rejected"

        await query.edit_message_text(
            "❌ واریز رد شد.\n\n"
            f"👤 کاربر: {user_display(uid)}\n"
            f"💰 مبلغ: {request['amount']:,} DOGS"
        )

        try:

            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "❌ درخواست واریز شما رد شد.\n\n"
                    "در صورت اشتباه با پشتیبانی تماس بگیرید."
                )
            )

        except Exception:
            pass

    request["checked_at"] = datetime.now().isoformat()

    save_data()


# =========================================================
# ADMIN WITHDRAW
# =========================================================

async def admin_withdraw_callback(update, context):
    query = update.callback_query

    await query.answer()

    if not is_owner(query.from_user.id):
        return

    request_id = query.data.split("_", 2)[2]

    request = data["withdraws"].get(request_id)

    if not request:

        await query.edit_message_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request["status"] != "pending":

        await query.answer(
            "این درخواست قبلاً بررسی شده.",
            show_alert=True
        )

        return

    uid = request["user_id"]

    if query.data.startswith("ok_wd_"):

        request["status"] = "approved"

        await query.edit_message_text(
            "✅ برداشت تأیید شد.\n\n"
            f"👤 کاربر: {user_display(uid)}\n\n"
            f"💰 مبلغ: {request['amount']:,} DOGS\n\n"
            f"💳 آدرس:\n{request['address']}\n\n"
            "⚠️ بعد از واریز واقعی، مالک این درخواست را تأیید کرده است."
        )

        try:

            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "✅ برداشت شما تأیید شد.\n\n"
                    f"💰 مبلغ: {request['amount']:,} DOGS\n\n"
                    "پرداخت توسط مالک تأیید شد."
                )
            )

        except Exception:
            pass

    else:

        add_balance(
            uid,
            request["amount"]
        )

        request["status"] = "rejected"

        await query.edit_message_text(
            "❌ برداشت رد شد.\n\n"
            f"👤 کاربر: {user_display(uid)}\n\n"
            f"💰 مبلغ برگشتی: "
            f"{request['amount']:,} DOGS"
        )

        try:

            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "❌ درخواست برداشت شما رد شد.\n\n"
                    f"💰 مبلغ "
                    f"{request['amount']:,} DOGS "
                    "به موجودی برگشت داده شد.\n\n"
                    f"💳 موجودی جدید: "
                    f"{balance(uid):,} DOGS"
                )
            )

        except Exception:
            pass

    request["checked_at"] = datetime.now().isoformat()

    save_data()


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 روشن/خاموش ربات",
                    callback_data="adm_toggle_bot"
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 کانال اجباری",
                    callback_data="adm_channel"
                ),
                InlineKeyboardButton(
                    "👥 گپ اجباری",
                    callback_data="adm_group"
                )
            ],
            [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="adm_transfer"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="adm_stats"
                )
            ]
        ]
    )


async def show_admin_panel(update, context):

    status = (
        "روشن ✅"
        if data["settings"].get("bot", True)
        else "خاموش ❌"
    )

    channel = data["settings"].get(
        "forced_channel"
    ) or "خاموش"

    group = data["settings"].get(
        "forced_group"
    ) or "خاموش"

    await update.message.reply_text(
        "⚙️ پنل مدیریت\n\n"
        f"🤖 وضعیت ربات: {status}\n\n"
        f"📢 کانال اجباری: {channel}\n\n"
        f"👥 گپ اجباری: {group}\n\n"
        "🎁 پاداش رفرال: "
        f"{REFERRAL_REWARD} DOGS\n\n"
        "💰 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN PANEL CALLBACK
# =========================================================

async def admin_panel_callback(update, context):
    query = update.callback_query

    await query.answer()

    if not is_owner(query.from_user.id):
        return

    action = query.data

    # =====================================================
    # TOGGLE BOT
    # =====================================================

    if action == "adm_toggle_bot":

        current = data["settings"].get(
            "bot",
            True
        )

        data["settings"]["bot"] = not current

        save_data()

        status = (
            "روشن ✅"
            if data["settings"]["bot"]
            else "خاموش ❌"
        )

        await query.edit_message_text(
            f"🤖 وضعیت ربات: {status}",
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # STATS
    # =====================================================

    if action == "adm_stats":

        users = len(data["users"])

        deposits = len(data["deposits"])

        withdraws = len(data["withdraws"])

        pending_deposits = sum(
            1
            for x in data["deposits"].values()
            if x.get("status") == "pending"
        )

        pending_withdraws = sum(
            1
            for x in data["withdraws"].values()
            if x.get("status") == "pending"
        )

        total_balance = sum(
            int(
                x.get(
                    "balance",
                    0
                )
            )
            for x in data["users"].values()
        )

        await query.edit_message_text(
            "📊 آمار ربات\n\n"
            f"👥 کاربران: {users}\n\n"
            f"💳 کل واریزی‌ها: {deposits}\n"
            f"⏳ واریزی در انتظار: {pending_deposits}\n\n"
            f"💰 کل برداشت‌ها: {withdraws}\n"
            f"⏳ برداشت در انتظار: {pending_withdraws}\n\n"
            f"💵 مجموع موجودی کاربران: "
            f"{total_balance:,} DOGS",
            reply_markup=admin_keyboard()
        )

        return

    # =====================================================
    # CHANNEL
    # =====================================================

    if action == "adm_channel":

        context.user_data["admin_state"] = "channel"

        await query.message.reply_text(
            "📢 کانال اجباری\n\n"
            "یوزرنیم کانال را ارسال کنید.\n\n"
            "مثال:\n"
            "@TAK_BE_T\n\n"
            "برای خاموش کردن:\n"
            "خاموش"
        )

        return

    # =====================================================
    # GROUP
    # =====================================================

    if action == "adm_group":

        context.user_data["admin_state"] = "group"

        await query.message.reply_text(
            "👥 گپ اجباری\n\n"
            "یوزرنیم گپ را ارسال کنید.\n\n"
            "مثال:\n"
            "@TAK_B_ET\n\n"
            "برای خاموش کردن:\n"
            "خاموش"
        )

        return

    # =====================================================
    # TRANSFER OWNER
    # =====================================================

    if action == "adm_transfer":

        context.user_data["admin_state"] = "transfer_owner"

        await query.message.reply_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید."
        )

        return


# =========================================================
# ADMIN TEXT
# =========================================================

async def admin_text(update, context):

    if not update.message:
        return False

    if not is_owner(update.effective_user.id):
        return False

    state = context.user_data.get(
        "admin_state"
    )

    if not state:
        return False

    text = (
        update.message.text or ""
    ).strip()

    # =====================================================
    # CHANNEL
    # =====================================================

    if state == "channel":

        if text.lower() == "خاموش":

            data["settings"]["forced_channel"] = None

        else:

            if not text.startswith("@"):
                text = "@" + text

            data["settings"]["forced_channel"] = text

        save_data()

        context.user_data.pop(
            "admin_state",
            None
        )

        await update.message.reply_text(
            "✅ کانال اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            )
        )

        return True

    # =====================================================
    # GROUP
    # =====================================================

    if state == "group":

        if text.lower() == "خاموش":

            data["settings"]["forced_group"] = None

        else:

            if not text.startswith("@"):
                text = "@" + text

            data["settings"]["forced_group"] = text

        save_data()

        context.user_data.pop(
            "admin_state",
            None
        )

        await update.message.reply_text(
            "✅ گپ اجباری ذخیره شد.",
            reply_markup=main_keyboard(
                update.effective_user.id
            )
        )

        return True

    # =====================================================
    # TRANSFER OWNER
    # =====================================================

    if state == "transfer_owner":

        try:

            new_owner = int(text)

        except Exception:

            await update.message.reply_text(
                "❌ فقط آیدی عددی ارسال کنید."
            )

            return True

        if not get_user(new_owner):

            await update.message.reply_text(
                "❌ این کاربر هنوز در ربات ثبت نشده است.\n\n"
                "ابتدا کاربر /start را بزند."
            )

            return True

        old_owner = data.get("owner")

        data["owner"] = new_owner

        save_data()

        context.user_data.pop(
            "admin_state",
            None
        )

        await update.message.reply_text(
            "✅ انتقال مالکیت انجام شد.\n\n"
            f"👑 مالک جدید: "
            f"{user_display(new_owner)}\n\n"
            "⚠️ از این لحظه مالک جدید "
            "دسترسی پنل مدیریت را دارد."
        )

        try:

            await context.bot.send_message(
                chat_id=new_owner,
                text="👑 شما مالک جدید ربات شدید."
            )

        except Exception:
            pass

        return True

    return False


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button_handler(update, context):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    user = update.effective_user

    if not await bot_available(update, context):
        return

    text = update.message.text

    if text == "👤 پروفایل":

        await show_profile(
            update,
            context
        )

    elif text == "👥 زیر مجموعه":

        await show_referrals(
            update,
            context
        )

    elif text == "💳 واریزی":

        await show_deposit(
            update,
            context
        )

    elif text == "💰 برداشت":

        await show_withdraw(
            update,
            context
        )

    elif text == "🎧 پشتیبانی":

        await show_support(
            update,
            context
        )

    elif text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

    elif text == "⚙️ پنل مدیریت":

        if is_owner(user.id):

            await show_admin_panel(
                update,
                context
            )


# =========================================================
# PRIVATE MESSAGE ROUTER
# =========================================================

async def private_message_router(update, context):

    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    # =====================================================
    # ADMIN
    # =====================================================

    if await admin_text(
        update,
        context
    ):
        return

    # =====================================================
    # BACK
    # =====================================================

    if update.message.text == "🔙 برگشت":

        await go_home(
            update,
            context
        )

        return

    # =====================================================
    # BOT STATUS
    # =====================================================

    if not await bot_available(
        update,
        context
    ):
        return

    state = context.user_data.get(
        "state"
    )

    # =====================================================
    # DEPOSIT
    # =====================================================

    if state == "deposit_amount":

        await handle_deposit_amount(
            update,
            context
        )

        return

    if state == "deposit_receipt":

        await handle_deposit_receipt(
            update,
            context
        )

        return

    # =====================================================
    # WITHDRAW
    # =====================================================

    if state == "withdraw_amount":

        await handle_withdraw_amount(
            update,
            context
        )

        return

    if state == "withdraw_address":

        await handle_withdraw_address(
            update,
            context
        )

        return

    # =====================================================
    # BUTTONS
    # =====================================================

    await button_handler(
        update,
        context
    )


# =========================================================
# CHECK JOIN
# =========================================================

async def check_join_callback(update, context):

    query = update.callback_query

    await query.answer()

    if await check_forced_join(
        update,
        context
    ):

        create_user(query.from_user)

        await query.message.reply_text(
            "✅ عضویت شما تأیید شد.\n\n"
            "حالا /start را بزنید.",
            reply_markup=main_keyboard(
                query.from_user.id
            )
        )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN پیدا نشد"
        )

        return

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # START
    # =====================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # =====================================================
    # GAME
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(
                r"^بازی\s+\d+$"
            ),
            game_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )

    # =====================================================
    # DEPOSIT METHOD
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            deposit_method_callback,
            pattern=r"^deposit_(ultra|exchange)$"
        )
    )

    # =====================================================
    # CHECK JOIN
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            check_join_callback,
            pattern=r"^check_join$"
        )
    )

    # =====================================================
    # DEPOSIT ADMIN
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            admin_deposit_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )

    # =====================================================
    # WITHDRAW ADMIN
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(ok_wd_|no_wd_)"
        )
    )

    # =====================================================
    # ADMIN PANEL
    # =====================================================

    app.add_handler(
        CallbackQueryHandler(
            admin_panel_callback,
            pattern=r"^adm_"
        )
    )

    # =====================================================
    # PRIVATE MESSAGES
    # =====================================================

    app.add_handler(
        MessageHandler(
            (
                filters.TEXT
                |
                filters.PHOTO
            )
            & ~filters.COMMAND,
            private_message_router
        )
    )

    print(
        "================================="
    )

    print(
        "✅ BOT STARTED"
    )

    print(
        "💾 DATA FILE: bot_data.json"
    )

    print(
        "================================="
    )

    app.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
