import json
import os
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

SUPPORT_USERNAME = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000

DATA_FILE = "bot_data.json"


# =========================
# DATABASE
# =========================

DEFAULT_DATA = {
    "users": {},
    "deposits": {},
    "withdraws": {},
    "referrals": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True
    }
}


def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        for key, value in DEFAULT_DATA.items():

            if key not in data:
                data[key] = value

        return data

    except Exception:
        return DEFAULT_DATA.copy()


data = load_data()


def save_data():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


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
            "balance": 0,
            "referrals": 0,
            "referred_by": None,
            "date": datetime.now().isoformat()
        }

        save_data()

    else:

        # بروزرسانی نام و یوزرنیم
        data["users"][uid]["name"] = (
            user.first_name or ""
        )

        data["users"][uid]["username"] = (
            user.username or ""
        )

        save_data()

    return data["users"][uid]


def get_user(uid):

    return data["users"].get(
        str(uid)
    )


def balance(uid):

    user = get_user(uid)

    if not user:
        return 0

    return int(
        user.get(
            "balance",
            0
        )
    )


def add_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    user["balance"] = (
        int(user.get("balance", 0))
        + int(amount)
    )

    save_data()

    return True


def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:
        return False

    if balance(uid) < int(amount):
        return False

    user["balance"] -= int(amount)

    save_data()

    return True


def is_owner(uid):

    return int(uid) == int(
        data.get(
            "owner",
            OWNER_ID
        )
    )


# =========================
# MAIN KEYBOARD
# =========================

def main_keyboard(uid):

    rows = [

        [
            "💳 واریزی",
            "👥 زیر مجموعه"
        ],

        [
            "👤 پروفایل",
            "💰 برداشت"
        ]

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


# =========================
# BACK KEYBOARD
# =========================

def back_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                "🔙 برگشت"
            ]
        ],
        resize_keyboard=True
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(

        "🤖 به ربات خوش آمدید.\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌های زیر را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )
        )

# =========================
# PROFILE
# =========================

async def show_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    uid = user.id
    profile_data = get_user(uid)

    name = profile_data.get(
        "name",
        ""
    )

    username = profile_data.get(
        "username",
        ""
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

    referrals = int(
        profile_data.get(
            "referrals",
            0
        )
    )

    await update.message.reply_text(

        "👤 پروفایل شما\n\n"

        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {name}\n"
        f"🔹 یوزرنیم: {username_text}\n\n"

        f"💰 موجودی: {balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه‌ها: {referrals}",

        reply_markup=back_keyboard()
    )


# =========================
# REFERRAL
# =========================

async def show_referrals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    uid = user.id

    bot_username = context.bot.username

    referral_link = (
        f"https://t.me/{bot_username}?start=ref_{uid}"
    )

    referrals = int(
        get_user(uid).get(
            "referrals",
            0
        )
    )

    await update.message.reply_text(

        "👥 زیرمجموعه‌گیری\n\n"

        "🔗 لینک اختصاصی شما:\n"
        f"{referral_link}\n\n"

        f"👥 تعداد زیرمجموعه‌ها: {referrals}\n\n"

        "📢 لینک بالا را برای دوستان خود ارسال کنید.",

        reply_markup=back_keyboard()
    )


# =========================
# DEPOSIT MENU
# =========================

async def show_deposit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    context.user_data["state"] = "deposit_receipt"

    await update.message.reply_text(

        "💳 واریزی DOGS\n\n"

        "💎 روش واریز:\n\n"

        f"آدرس کیف پول:\n"
        f"{DOGS_WALLET}\n\n"

        f"🔻 حداقل واریز: "
        f"{MIN_DEPOSIT:,} DOGS\n\n"

        "1️⃣ ابتدا DOGS را به آدرس بالا واریز کنید.\n"
        "2️⃣ سپس عکس رسید یا لینک تراکنش را همینجا ارسال کنید.\n"
        "3️⃣ بعد از آن مقدار DOGS را وارد کنید.\n\n"

        "📸 منتظر رسید شما هستیم.",

        reply_markup=back_keyboard()
    )


# =========================
# RECEIVE DEPOSIT RECEIPT
# =========================

async def handle_deposit_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if update.message.photo:

        photo = update.message.photo[-1]

        context.user_data["receipt"] = (
            f"📸 رسید تصویری\n"
            f"File ID: {photo.file_id}"
        )

    elif update.message.text:

        text = update.message.text.strip()

        if not text:

            await update.message.reply_text(
                "❌ رسید یا لینک تراکنش را ارسال کنید."
            )

            return

        context.user_data["receipt"] = text

    else:

        await update.message.reply_text(
            "❌ لطفاً عکس رسید یا لینک تراکنش را ارسال کنید."
        )

        return

    context.user_data["state"] = "deposit_amount"

    await update.message.reply_text(

        "✅ رسید دریافت شد.\n\n"

        "💰 حالا مقدار DOGS واریزی را به صورت عدد ارسال کنید.\n\n"

        f"🔻 حداقل واریز: {MIN_DEPOSIT:,} DOGS\n\n"

        "مثال:\n"
        "5000",

        reply_markup=back_keyboard()
    )


# =========================
# RECEIVE DEPOSIT AMOUNT
# =========================

async def handle_deposit_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار DOGS را به صورت عدد ارسال کنید."
        )

        return

    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(

            "❌ فقط عدد ارسال کنید.\n\n"
            "مثال:\n"
            "5000"

        )

        return

    if amount < MIN_DEPOSIT:

        await update.message.reply_text(

            f"❌ حداقل واریز "
            f"{MIN_DEPOSIT:,} DOGS است.\n\n"

            f"💰 مبلغ واردشده: "
            f"{amount:,} DOGS"

        )

        return

    receipt = context.user_data.get(
        "receipt",
        "بدون رسید"
    )

    uid = user.id

    # هر درخواست یک شناسه جدا دارد
    request_id = (
        f"{uid}_{int(datetime.now().timestamp())}"
    )

    data["deposits"][request_id] = {

        "id": request_id,

        "user_id": uid,

        "name": user.first_name or "",

        "username": user.username or "",

        "amount": amount,

        "receipt": receipt,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    context.user_data.clear()

    await update.message.reply_text(

        "✅ درخواست واریز ثبت شد.\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        "⏳ درخواست شما برای مالک ارسال شد.\n"
        "پس از تأیید، موجودی شما افزایش پیدا می‌کند.",

        reply_markup=main_keyboard(uid)
    )

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (

        "💳 واریزی جدید\n\n"

        f"👤 نام: {user.first_name or 'بدون نام'}\n"
        f"🆔 آیدی: {uid}\n"
        f"🔹 یوزرنیم: {username}\n\n"

        f"💰 مبلغ: {amount:,} DOGS\n\n"

        f"📝 رسید:\n{receipt}\n\n"

        f"🆔 شناسه درخواست:\n{request_id}"

    )

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=owner_text

        )

    except Exception as e:

        print(
            f"❌ خطا در ارسال واریزی به مالک: {e}"
        )


# =========================
# WITHDRAW MENU
# =========================

async def show_withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    create_user(user)

    uid = user.id

    current_balance = balance(uid)

    if current_balance < MIN_WITHDRAW:

        await update.message.reply_text(

            "💰 برداشت DOGS\n\n"

            f"💳 موجودی شما: "
            f"{current_balance:,} DOGS\n\n"

            f"❌ حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n\n"

            "برای ثبت برداشت باید حداقل "
            "۱۰,۰۰۰ DOGS موجودی داشته باشید.",

            reply_markup=back_keyboard()
        )

        return

    context.user_data.clear()

    context.user_data["state"] = "withdraw_address"

    await update.message.reply_text(

        "💰 برداشت DOGS\n\n"

        f"💳 موجودی شما: "
        f"{current_balance:,} DOGS\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "1️⃣ آدرس کیف پول DOGS خود را ارسال کنید.",

        reply_markup=back_keyboard()
    )


# =========================
# WITHDRAW ADDRESS
# =========================

async def handle_withdraw_address(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message.text:

        await update.message.reply_text(
            "❌ لطفاً آدرس کیف پول DOGS را ارسال کنید."
        )

        return

    address = update.message.text.strip()

    if len(address) < 10:

        await update.message.reply_text(
            "❌ آدرس کیف پول معتبر نیست."
        )

        return

    context.user_data["withdraw_address"] = address

    context.user_data["state"] = "withdraw_amount"

    await update.message.reply_text(

        "✅ آدرس کیف پول دریافت شد.\n\n"

        f"💳 آدرس:\n{address}\n\n"

        "2️⃣ حالا مقدار DOGS برای برداشت را ارسال کنید.\n\n"

        f"🔻 حداقل برداشت: "
        f"{MIN_WITHDRAW:,} DOGS\n\n"

        "مثال:\n"
        "10000",

        reply_markup=back_keyboard()
        )

# =========================
# WITHDRAW AMOUNT
# =========================

async def handle_withdraw_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not update.message.text:

        await update.message.reply_text(
            "❌ مقدار برداشت را به صورت عدد ارسال کنید."
        )

        return

    try:

        amount = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(

            "❌ فقط عدد ارسال کنید.\n\n"
            "مثال:\n"
            "10000"

        )

        return

    # =========================
    # MIN WITHDRAW
    # =========================

    if amount < MIN_WITHDRAW:

        await update.message.reply_text(

            "❌ مبلغ برداشت کمتر از حد مجاز است.\n\n"

            f"🔻 حداقل برداشت: "
            f"{MIN_WITHDRAW:,} DOGS\n\n"

            f"💰 مبلغ واردشده: "
            f"{amount:,} DOGS"

        )

        return

    # =========================
    # CHECK BALANCE
    # =========================

    current_balance = balance(user.id)

    if current_balance < amount:

        await update.message.reply_text(

            "❌ موجودی کافی نیست.\n\n"

            f"💳 موجودی شما: "
            f"{current_balance:,} DOGS\n\n"

            f"💰 مبلغ برداشت: "
            f"{amount:,} DOGS"

        )

        return

    # =========================
    # WALLET ADDRESS
    # =========================

    address = context.user_data.get(
        "withdraw_address"
    )

    if not address:

        context.user_data["state"] = (
            "withdraw_address"
        )

        await update.message.reply_text(

            "❌ آدرس کیف پول پیدا نشد.\n\n"
            "لطفاً دوباره آدرس کیف پول DOGS "
            "خود را ارسال کنید."

        )

        return

    # =========================
    # CREATE REQUEST ID
    # =========================

    request_id = (
        f"{user.id}_{int(datetime.now().timestamp())}"
    )

    # =========================
    # DEDUCT BALANCE
    # =========================

    success = remove_balance(
        user.id,
        amount
    )

    if not success:

        await update.message.reply_text(

            "❌ برداشت انجام نشد.\n\n"
            "موجودی شما تغییر نکرد."

        )

        return

    # =========================
    # SAVE WITHDRAW
    # =========================

    data["withdraws"][request_id] = {

        "id": request_id,

        "user_id": user.id,

        "name": user.first_name or "",

        "username": user.username or "",

        "address": address,

        "amount": amount,

        "status": "pending",

        "date": datetime.now().isoformat()

    }

    save_data()

    new_balance = balance(
        user.id
    )

    # =========================
    # CLEAR STATE
    # =========================

    context.user_data.clear()

    # =========================
    # USER MESSAGE
    # =========================

    await update.message.reply_text(

        "✅ درخواست برداشت ثبت شد.\n\n"

        f"💰 مبلغ برداشت: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس کیف پول:\n"
        f"{address}\n\n"

        f"💰 موجودی جدید: "
        f"{new_balance:,} DOGS\n\n"

        "⏳ درخواست شما برای مالک ارسال شد.\n"
        "پس از بررسی، نتیجه برای شما ارسال می‌شود.",

        reply_markup=main_keyboard(
            user.id
        )
    )

    # =========================
    # OWNER MESSAGE
    # =========================

    username = (
        f"@{user.username}"
        if user.username
        else "ندارد"
    )

    owner_text = (

        "💰 درخواست برداشت جدید\n\n"

        f"👤 نام: "
        f"{user.first_name or 'بدون نام'}\n"

        f"🆔 آیدی: "
        f"{user.id}\n"

        f"🔹 یوزرنیم: "
        f"{username}\n\n"

        f"💰 مبلغ: "
        f"{amount:,} DOGS\n\n"

        f"💳 آدرس کیف پول:\n"
        f"{address}\n\n"

        f"💰 موجودی فعلی کاربر:\n"
        f"{new_balance:,} DOGS\n\n"

        f"🆔 شناسه درخواست:\n"
        f"{request_id}"

    )

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=owner_text

        )

    except Exception as e:

        print(
            f"❌ خطا در ارسال برداشت به مالک: {e}"
        )

        # اگر ارسال درخواست به مالک شکست خورد،
        # پول کاربر برگردانده می‌شود.

        add_balance(
            user.id,
            amount
        )

        withdraw = data["withdraws"].get(
            request_id
        )

        if withdraw:

            withdraw["status"] = "failed"

            save_data()

        await update.message.reply_text(

            "⚠️ ارسال درخواست به مالک ناموفق بود.\n\n"
            "مبلغ به موجودی شما برگشت داده شد.",

            reply_markup=main_keyboard(
                user.id
            )
        )


# =========================
# SUPPORT
# =========================

async def show_support(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🎧 پشتیبانی\n\n"

        "برای ارتباط با پشتیبانی از آیدی زیر استفاده کنید:\n\n"

        f"👤 {SUPPORT_USERNAME}\n\n"

        "📩 پیام خود را برای پشتیبانی ارسال کنید.",

        reply_markup=back_keyboard()
    )


# =========================
# BACK
# =========================

async def go_home(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    context.user_data.clear()

    await update.message.reply_text(

        "🏠 منوی اصلی\n\n"

        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌ها را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id
        )
    )

# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد")
        return

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =========================
    # START
    # =========================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # =========================
    # GAME
    # فقط داخل گپ با:
    # بازی 500
    # =========================

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(
                r"^بازی\s+\d+$"
            ),
            game_command
        )
    )

    # =========================
    # GAME BUTTONS
    # فقط دکمه ورود/لغو بازی
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )

    # =========================
    # DEPOSIT ACCEPT / REJECT
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )

    # =========================
    # WITHDRAW ACCEPT / REJECT
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            admin_withdraw_callback,
            pattern=r"^(ok_wd_|no_wd_)"
        )
    )

    # =========================
    # ALL NORMAL KEYBOARD BUTTONS
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # =========================
    # TEXT + PHOTO
    # =========================

    app.add_handler(
        MessageHandler(
            (
                filters.TEXT
                |
                filters.PHOTO
            )
            & ~filters.COMMAND,
            message_handler
        )
    )

    # =========================
    # START BOT
    # =========================

    print("=================================")
    print("✅ BOT STARTED")
    print("🤖 Telegram bot is running...")
    print("=================================")

    app.run_polling(
        drop_pending_updates=True
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
