import json
import os
import random
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
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


# GAME SETTINGS

MIN_GAME = 500
MAX_GAME = 20000
GAME_FEE = 100


DATA_FILE = "bot_data.json"

# =========================
# DATABASE
# =========================

DEFAULT_DATA = {

    "users": {},

    "deposits": {},

    "withdraws": {},

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


        for key in DEFAULT_DATA:

            if key not in data:

                data[key] = DEFAULT_DATA[key]


        return data


    except:

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

            "date": datetime.now().isoformat()

        }

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
        +
        int(amount)
    )

    save_data()

    return True



def remove_balance(uid, amount):

    user = get_user(uid)

    if not user:

        return False


    if balance(uid) < amount:

        return False


    user["balance"] -= amount

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
# KEYBOARDS
# =========================

def back_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]
        ]
    )


def main_keyboard(uid):

    rows = [

        [
            InlineKeyboardButton(
                "💳 واریز",
                callback_data="deposit"
            ),

            InlineKeyboardButton(
                "💰 برداشت",
                callback_data="withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "👤 پروفایل",
                callback_data="profile"
            ),

            InlineKeyboardButton(
                "🎮 بازی",
                callback_data="game_info"
            )
        ],

        [
            InlineKeyboardButton(
                "🎧 پشتیبانی",
                callback_data="support"
            )
        ]

    ]

    if is_owner(uid):

        rows.append(
            [
                InlineKeyboardButton(
                    "⚙️ پنل مالک",
                    callback_data="admin"
                )
            ]
        )

    return InlineKeyboardMarkup(rows)


def admin_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🟢 روشن / 🔴 خاموش",
                    callback_data="admin_toggle"
                )
            ],

            [
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 برگشت",
                    callback_data="home"
                )
            ]
        ]
    )


# =========================
# START
# =========================

async def start(update, context):

    user = update.effective_user

    if not user:
        return

    create_user(user)

    await update.message.reply_text(

        "🤖 خوش آمدید\n\n"
        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS",

        reply_markup=main_keyboard(
            user.id
        )
        )

# =========================
# PROFILE
# =========================

async def profile(query):

    uid = query.from_user.id

    user = get_user(uid)

    if not user:

        create_user(
            query.from_user
        )

        user = get_user(uid)

    name = user.get(
        "name",
        ""
    )

    username = user.get(
        "username",
        ""
    )

    username_text = (
        f"@{username}"
        if username
        else "ندارد"
    )

    await query.edit_message_text(

        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {name}\n"
        f"🔹 یوزرنیم: {username_text}\n\n"
        f"💰 موجودی: {balance(uid):,} DOGS",

        reply_markup=back_button()
    )


# =========================
# GAME INFO
# =========================

async def game_info(query):

    await query.edit_message_text(

        "🎮 بازی دو نفره\n\n"

        "برای ساخت بازی داخل گپ بنویسید:\n\n"

        "بازی 500\n\n"

        f"💰 حداقل شرط: {MIN_GAME:,} DOGS\n"
        f"💰 حداکثر شرط: {MAX_GAME:,} DOGS\n"
        f"👑 کارمزد مالک: {GAME_FEE:,} DOGS",

        reply_markup=back_button()
    )

# =========================
# DEPOSIT SYSTEM
# =========================

async def deposit_menu(query):

    await query.edit_message_text(

        "💳 روش واریز را انتخاب کنید:",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💎 اولترا",
                        callback_data="ultra"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💎 صرافی",
                        callback_data="exchange"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ]
        )
    )


# =========================
# ULTRA DEPOSIT
# =========================

async def ultra(query, context):

    context.user_data["state"] = "deposit_receipt"

    await query.edit_message_text(

        "💎 اولترا\n\n"

        f"به این آیدی DOGS بزنید:\n"
        f"{ULTRA_ID}\n\n"

        "بعد از واریز:\n"
        "1️⃣ عکس رسید یا لینک تراکنش را ارسال کنید\n"
        "2️⃣ بعد مقدار DOGS را بفرستید\n\n"

        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()
    )


# =========================
# EXCHANGE DEPOSIT
# =========================

async def exchange(query, context):

    context.user_data["state"] = "deposit_receipt"

    await query.edit_message_text(

        "💎 صرافی\n\n"

        f"ولت DOGS:\n"
        f"{DOGS_WALLET}\n\n"

        "بعد از واریز:\n"
        "1️⃣ رسید را ارسال کنید\n"
        "2️⃣ مقدار DOGS را وارد کنید\n\n"

        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",

        reply_markup=back_button()
    )

# =========================
# DEPOSIT RECEIPT HANDLER
# =========================

async def handle_deposit(update, context):

    user = update.effective_user

    if not user or not update.message:
        return

    state = context.user_data.get("state")


    # =====================
    # RECEIVE RECEIPT
    # =====================

    if state == "deposit_receipt":

        if update.message.photo:

            photo = update.message.photo[-1]

            context.user_data["receipt"] = (
                f"📸 عکس رسید\n"
                f"File ID: {photo.file_id}"
            )

        elif update.message.text:

            context.user_data["receipt"] = (
                update.message.text.strip()
            )

        else:

            await update.message.reply_text(
                "❌ لطفاً عکس رسید یا لینک تراکنش ارسال کنید."
            )

            return


        context.user_data["state"] = "deposit_amount"


        await update.message.reply_text(

            "✅ رسید دریافت شد.\n\n"

            "💰 حالا مقدار DOGS واریزی را ارسال کنید.\n\n"

            f"حداقل واریز: {MIN_DEPOSIT:,} DOGS"

        )

        return


    # =====================
    # RECEIVE AMOUNT
    # =====================

    if state == "deposit_amount":

        if not update.message.text:

            await update.message.reply_text(
                "❌ لطفاً مقدار DOGS را به صورت عدد ارسال کنید."
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
                f"{MIN_DEPOSIT:,} DOGS است."

            )

            return


        receipt = context.user_data.get(
            "receipt",
            "بدون رسید"
        )


        # =====================
        # SAVE DEPOSIT
        # =====================

        data["deposits"][str(user.id)] = {

            "user_id": user.id,

            "name": user.first_name or "",

            "username": user.username or "",

            "amount": amount,

            "receipt": receipt,

            "status": "pending",

            "date": datetime.now().isoformat()

        }


        save_data()


        # ذخیره قبل از پاک کردن state
        context.user_data.clear()


        # =====================
        # USER MESSAGE
        # =====================

        await update.message.reply_text(

            "✅ درخواست واریز ثبت شد.\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n"

            "⏳ منتظر تأیید مالک باشید."

        )


        # =====================
        # OWNER MESSAGE
        # =====================

        owner_text = (

            "💳 واریز جدید\n\n"

            f"👤 کاربر: {user.first_name or 'بدون نام'}\n"
            f"🆔 آیدی: {user.id}\n"

            f"🔹 یوزرنیم: "
            f"@{user.username if user.username else 'ندارد'}\n\n"

            f"💰 مقدار: {amount:,} DOGS\n\n"

            f"📝 رسید:\n{receipt}"

        )


        try:

            await context.bot.send_message(

                chat_id=OWNER_ID,

                text=owner_text,

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ تایید",
                                callback_data=f"ok_dep_{user.id}"
                            ),

                            InlineKeyboardButton(
                                "❌ رد",
                                callback_data=f"no_dep_{user.id}"
                            )
                        ]
                    ]
                )

            )

        except Exception as e:

            print(
                f"❌ خطا در ارسال واریز به مالک: {e}"
            )

        return

# =========================
# ADMIN DEPOSIT CALLBACK
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass


    user = query.from_user

    # فقط مالک
    if not is_owner(user.id):

        await query.answer(
            "❌ شما دسترسی ندارید.",
            show_alert=True
        )

        return


    action = query.data


    # =========================
    # ACCEPT DEPOSIT
    # =========================

    if action.startswith("ok_dep_"):

        try:

            uid = int(
                action.split("_")[2]
            )

        except:

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        deposit = data["deposits"].get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return


        if deposit.get("status") == "accepted":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً تأیید شده است."
            )

            return


        if deposit.get("status") == "rejected":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً رد شده است."
            )

            return


        amount = int(
            deposit.get(
                "amount",
                0
            )
        )


        # اطمینان از وجود کاربر
        if not get_user(uid):

            deposit_user = {

                "id": uid,

                "name": deposit.get(
                    "name",
                    ""
                ),

                "username": deposit.get(
                    "username",
                    ""
                ),

                "balance": 0,

                "date": datetime.now().isoformat()

            }

            data["users"][str(uid)] = deposit_user


        # اضافه کردن موجودی
        add_balance(
            uid,
            amount
        )


        deposit["status"] = "accepted"

        deposit["accepted_date"] = (
            datetime.now().isoformat()
        )

        deposit["accepted_by"] = (
            user.id
        )


        save_data()


        # پیام مالک
        await query.edit_message_text(

            "✅ واریز تأیید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n"

            f"💳 موجودی جدید: "
            f"{balance(uid):,} DOGS"

        )


        # پیام کاربر
        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ واریز شما تأیید شد.\n\n"

                    f"➕ {amount:,} DOGS به موجودی شما اضافه شد.\n\n"

                    f"💰 موجودی جدید:\n"
                    f"{balance(uid):,} DOGS"

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام تأیید به کاربر: {e}"
            )

        return


    # =========================
    # REJECT DEPOSIT
    # =========================

    if action.startswith("no_dep_"):

        try:

            uid = int(
                action.split("_")[2]
            )

        except:

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        deposit = data["deposits"].get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return


        if deposit.get("status") == "accepted":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً تأیید شده است."
            )

            return


        if deposit.get("status") == "rejected":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً رد شده است."
            )

            return


        deposit["status"] = "rejected"

        deposit["rejected_date"] = (
            datetime.now().isoformat()
        )

        deposit["rejected_by"] = (
            user.id
        )


        save_data()


        # پیام مالک
        await query.edit_message_text(

            "❌ واریز رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: "
            f"{int(deposit.get('amount', 0)):,} DOGS"

        )


        # پیام کاربر
        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "❌ درخواست واریز شما رد شد.\n\n"

                    "اگر فکر می‌کنید اشتباهی رخ داده، "
                    "با پشتیبانی تماس بگیرید."

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام رد واریز به کاربر: {e}"
            )

        return

# =========================
# WITHDRAW SYSTEM
# =========================

MIN_WITHDRAW = 10_000


async def withdraw_menu(query, context):

    uid = query.from_user.id

    user = get_user(uid)

    if not user:

        create_user(query.from_user)

    current_balance = balance(uid)

    if current_balance < MIN_WITHDRAW:

        await query.edit_message_text(

            "💰 برداشت DOGS\n\n"

            f"💳 موجودی شما: {current_balance:,} DOGS\n\n"

            "❌ حداقل برداشت: 10,000 DOGS\n\n"

            "برای برداشت حداقل باید ۱۰ کا DOGS موجودی داشته باشید.",

            reply_markup=back_button()

        )

        return


    context.user_data["state"] = "withdraw_address"

    await query.edit_message_text(

        "💰 برداشت DOGS\n\n"

        f"💳 موجودی شما: {current_balance:,} DOGS\n\n"

        "🔻 حداقل برداشت: 10,000 DOGS\n\n"

        "1️⃣ ابتدا آدرس کیف پول DOGS خود را ارسال کنید."

    )


# =========================
# WITHDRAW HANDLER
# =========================

async def handle_withdraw(update, context):

    user = update.effective_user

    if not user or not update.message:
        return


    state = context.user_data.get("state")


    # =========================
    # RECEIVE WALLET ADDRESS
    # =========================

    if state == "withdraw_address":

        if not update.message.text:

            await update.message.reply_text(
                "❌ لطفاً آدرس کیف پول DOGS را ارسال کنید."
            )

            return


        address = update.message.text.strip()


        if len(address) < 10:

            await update.message.reply_text(
                "❌ آدرس کیف پول نامعتبر است."
            )

            return


        context.user_data["withdraw_address"] = address

        context.user_data["state"] = "withdraw_amount"


        await update.message.reply_text(

            "✅ آدرس کیف پول دریافت شد.\n\n"

            f"💳 آدرس:\n{address}\n\n"

            "2️⃣ حالا مقدار DOGS برای برداشت را ارسال کنید.\n\n"

            "🔻 حداقل برداشت: 10,000 DOGS"

        )

        return


    # =========================
    # RECEIVE AMOUNT
    # =========================

    if state == "withdraw_amount":

        if not update.message.text:

            await update.message.reply_text(
                "❌ مقدار برداشت را ارسال کنید."
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


        # حداقل برداشت = 10 کا
        if amount < MIN_WITHDRAW:

            await update.message.reply_text(

                "❌ مبلغ برداشت کمتر از حد مجاز است.\n\n"

                "🔻 حداقل برداشت: 10,000 DOGS\n"

                f"💳 مبلغ واردشده: {amount:,} DOGS"

            )

            return


        current_balance = balance(user.id)


        if current_balance < amount:

            await update.message.reply_text(

                "❌ موجودی کافی نیست.\n\n"

                f"💳 موجودی شما: {current_balance:,} DOGS\n"

                f"💰 مبلغ برداشت: {amount:,} DOGS"

            )

            return


        address = context.user_data.get(
            "withdraw_address"
        )


        if not address:

            context.user_data["state"] = "withdraw_address"

            await update.message.reply_text(
                "❌ آدرس کیف پول پیدا نشد.\n\n"
                "لطفاً دوباره آدرس کیف پول را ارسال کنید."
            )

            return


        # =========================
        # DEDUCT BALANCE
        # =========================

        success = remove_balance(
            user.id,
            amount
        )


        if not success:

            await update.message.reply_text(
                "❌ برداشت انجام نشد."
            )

            return


        # =========================
        # SAVE WITHDRAW
        # =========================

        data["withdraws"][str(user.id)] = {

            "user_id": user.id,

            "name": user.first_name or "",

            "username": user.username or "",

            "address": address,

            "amount": amount,

            "status": "pending",

            "date": datetime.now().isoformat()

        }


        save_data()


        new_balance = balance(user.id)


        context.user_data.clear()


        # =========================
        # USER MESSAGE
        # =========================

        await update.message.reply_text(

            "✅ درخواست برداشت ثبت شد.\n\n"

            f"💰 مبلغ برداشت: {amount:,} DOGS\n"

            f"💳 موجودی جدید: {new_balance:,} DOGS\n\n"

            "⏳ درخواست شما برای مالک ارسال شد."

        )


        # =========================
        # OWNER MESSAGE
        # =========================

        owner_text = (

            "💰 درخواست برداشت جدید\n\n"

            f"👤 نام: {user.first_name or 'بدون نام'}\n"

            f"🆔 آیدی: {user.id}\n"

            f"🔹 یوزرنیم: "
            f"@{user.username if user.username else 'ندارد'}\n\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            f"💳 آدرس کیف پول:\n"
            f"{address}\n\n"

            f"💳 موجودی فعلی کاربر:\n"
            f"{new_balance:,} DOGS"

        )


        try:

            await context.bot.send_message(

                chat_id=OWNER_ID,

                text=owner_text,

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ پرداخت شد",
                                callback_data=f"ok_wd_{user.id}"
                            ),

                            InlineKeyboardButton(
                                "❌ رد برداشت",
                                callback_data=f"no_wd_{user.id}"
                            )
                        ]
                    ]
                )

            )

        except Exception as e:

            print(
                f"❌ خطا در ارسال درخواست برداشت: {e}"
            )

        return

# =========================
# ADMIN WITHDRAW CALLBACK
# =========================

async def admin_withdraw_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass

    user = query.from_user

    # فقط مالک
    if not is_owner(user.id):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return

    action = query.data


    # =========================
    # WITHDRAW ACCEPTED
    # =========================

    if action.startswith("ok_wd_"):

        try:

            uid = int(
                action.split("_")[2]
            )

        except:

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        withdraw = data["withdraws"].get(
            str(uid)
        )


        if not withdraw:

            await query.edit_message_text(
                "❌ درخواست برداشت پیدا نشد."
            )

            return


        status = withdraw.get(
            "status"
        )


        if status == "accepted":

            await query.edit_message_text(
                "⚠️ این برداشت قبلاً تأیید شده است."
            )

            return


        if status == "rejected":

            await query.edit_message_text(
                "⚠️ این برداشت قبلاً رد شده است."
            )

            return


        amount = int(
            withdraw.get(
                "amount",
                0
            )
        )


        withdraw["status"] = "accepted"

        withdraw["accepted_date"] = (
            datetime.now().isoformat()
        )

        withdraw["accepted_by"] = (
            user.id
        )


        save_data()


        # پیام مالک
        await query.edit_message_text(

            "✅ برداشت تأیید شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ: {amount:,} DOGS\n\n"

            "💳 وضعیت: پرداخت شد"

        )


        # پیام کاربر
        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "✅ برداشت شما انجام شد.\n\n"

                    f"💰 مبلغ پرداخت‌شده: "
                    f"{amount:,} DOGS\n\n"

                    "💳 وضعیت: پرداخت شد"

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام برداشت به کاربر: {e}"
            )

        return


    # =========================
    # WITHDRAW REJECTED
    # =========================

    if action.startswith("no_wd_"):

        try:

            uid = int(
                action.split("_")[2]
            )

        except:

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        withdraw = data["withdraws"].get(
            str(uid)
        )


        if not withdraw:

            await query.edit_message_text(
                "❌ درخواست برداشت پیدا نشد."
            )

            return


        status = withdraw.get(
            "status"
        )


        if status == "accepted":

            await query.edit_message_text(
                "⚠️ این برداشت قبلاً تأیید شده است."
            )

            return


        if status == "rejected":

            await query.edit_message_text(
                "⚠️ این برداشت قبلاً رد شده است."
            )

            return


        amount = int(
            withdraw.get(
                "amount",
                0
            )
        )


        # =========================
        # RETURN MONEY
        # =========================

        if not get_user(uid):

            await query.edit_message_text(
                "❌ کاربر پیدا نشد."
            )

            return


        add_balance(
            uid,
            amount
        )


        withdraw["status"] = "rejected"

        withdraw["rejected_date"] = (
            datetime.now().isoformat()
        )

        withdraw["rejected_by"] = (
            user.id
        )


        save_data()


        # پیام مالک
        await query.edit_message_text(

            "❌ برداشت رد شد.\n\n"

            f"👤 کاربر: {uid}\n"

            f"💰 مبلغ برگشتی: {amount:,} DOGS\n\n"

            "💳 مبلغ به موجودی کاربر برگشت داده شد."

        )


        # پیام کاربر
        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(

                    "❌ درخواست برداشت شما رد شد.\n\n"

                    f"↩️ مبلغ برگشتی: "
                    f"{amount:,} DOGS\n\n"

                    f"💰 موجودی جدید:\n"
                    f"{balance(uid):,} DOGS"

                )

            )

        except Exception as e:

            print(
                f"❌ ارسال پیام رد برداشت: {e}"
            )

        return

# =========================
# SUPPORT
# =========================

async def support(query, context):

    await query.edit_message_text(

        "🎧 پشتیبانی\n\n"

        "برای ارتباط با پشتیبانی از طریق آیدی زیر پیام دهید:\n\n"

        f"👤 {SUPPORT_USERNAME}",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home"
                    )
                ]
            ]
        )
    )


# =========================
# GAME SYSTEM
# =========================

ACTIVE_GAMES = {}


def user_display(uid):

    user = get_user(uid)

    if not user:

        return str(uid)


    username = user.get(
        "username",
        ""
    )


    if username:

        return f"@{username}"


    name = user.get(
        "name",
        ""
    )


    if name:

        return name


    return str(uid)


# =========================
# CREATE GAME
# =========================

async def game_command(update, context):

    user = update.effective_user

    if not user:

        return


    create_user(user)


    try:

        parts = update.message.text.split()

        amount = int(parts[1])

    except (ValueError, IndexError):

        await update.message.reply_text(

            "❌ فرمت اشتباه است.\n\n"

            "مثال:\n"
            "بازی 500"

        )

        return


    if amount < MIN_GAME:

        await update.message.reply_text(

            f"❌ حداقل شرط بازی "
            f"{MIN_GAME:,} DOGS است."

        )

        return


    if amount > MAX_GAME:

        await update.message.reply_text(

            f"❌ حداکثر شرط بازی "
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

            f"💰 موجودی شما: "
            f"{balance(user.id):,} DOGS"

        )

        return


    # کسر مبلغ سازنده

    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ خطا در کسر موجودی."
        )

        return


    ACTIVE_GAMES[chat_id] = {

        "creator": user.id,

        "amount": amount,

        "created_at": datetime.now().isoformat()

    }


    await update.message.reply_text(

        "🎮 بازی ساخته شد\n\n"

        f"👤 سازنده: "
        f"{user_display(user.id)}\n\n"

        f"💰 شرط: "
        f"{amount:,} DOGS\n\n"

        "👥 نفر دوم می‌تواند وارد بازی شود.",

        reply_markup=InlineKeyboardMarkup(
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
    )


# =========================
# GAME CALLBACK
# =========================

async def game_callback(update, context):

    query = update.callback_query

    try:

        await query.answer()

    except:

        pass


    user = query.from_user

    chat_id = query.message.chat.id


    if chat_id not in ACTIVE_GAMES:

        await query.answer(
            "❌ این بازی دیگر فعال نیست.",
            show_alert=True
        )

        return


    game = ACTIVE_GAMES[chat_id]


    # =========================
    # CANCEL GAME
    # =========================

    if query.data == "cancel_game":

        if user.id != game["creator"]:

            await query.answer(

                "❌ فقط سازنده بازی می‌تواند آن را لغو کند.",

                show_alert=True

            )

            return


        add_balance(
            user.id,
            game["amount"]
        )


        del ACTIVE_GAMES[chat_id]


        await query.edit_message_text(

            "❌ بازی لغو شد.\n\n"

            f"💰 مبلغ "
            f"{game['amount']:,} DOGS "
            "به سازنده برگشت داده شد."

        )

        return


    # =========================
    # JOIN GAME
    # =========================

    if query.data == "join_game":

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


        if not remove_balance(
            user.id,
            amount
        ):

            await query.answer(

                "❌ خطا در کسر موجودی.",

                show_alert=True

            )

            return


        # =========================
        # CHOOSE WINNER
        # =========================

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


        total_pot = amount * 2


        prize = total_pot - GAME_FEE


        add_balance(
            winner,
            prize
        )


        # کارمزد مالک

        if get_user(OWNER_ID):

            add_balance(
                OWNER_ID,
                GAME_FEE
            )


        else:

            # اگر مالک هنوز کاربر نشده باشد
            data["users"][str(OWNER_ID)] = {

                "id": OWNER_ID,

                "name": "OWNER",

                "username": "",

                "balance": GAME_FEE,

                "date": datetime.now().isoformat()

            }

            save_data()


        del ACTIVE_GAMES[chat_id]


        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"🏆 برنده: "
            f"{user_display(winner)}\n\n"

            f"💰 جایزه: "
            f"{prize:,} DOGS\n\n"

            f"😢 بازنده: "
            f"{user_display(loser)}\n\n"

            f"👑 کارمزد مالک: "
            f"{GAME_FEE:,} DOGS"

        )

        return

# =========================
# ADMIN PANEL
# =========================

async def admin_panel(query):

    uid = query.from_user.id

    if not is_owner(uid):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return


    status = data["settings"].get(
        "bot",
        True
    )


    status_text = (
        "🟢 فعال"
        if status
        else
        "🔴 خاموش"
    )


    await query.edit_message_text(

        "⚙️ پنل مالک\n\n"

        f"🤖 وضعیت ربات: {status_text}\n\n"

        "از گزینه‌های زیر استفاده کنید:",

        reply_markup=admin_keyboard()

    )


# =========================
# ADMIN TOGGLE
# =========================

async def admin_toggle(query):

    uid = query.from_user.id

    if not is_owner(uid):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return


    current = data["settings"].get(
        "bot",
        True
    )


    data["settings"]["bot"] = not current

    save_data()


    new_status = data["settings"]["bot"]


    status_text = (
        "🟢 ربات روشن شد"
        if new_status
        else
        "🔴 ربات خاموش شد"
    )


    await query.answer(
        status_text,
        show_alert=True
    )


    await admin_panel(query)


# =========================
# ADMIN STATS
# =========================

async def admin_stats(query):

    uid = query.from_user.id

    if not is_owner(uid):

        await query.answer(
            "❌ دسترسی ندارید.",
            show_alert=True
        )

        return


    users_count = len(
        data.get(
            "users",
            {}
        )
    )


    deposits = data.get(
        "deposits",
        {}
    )


    withdraws = data.get(
        "withdraws",
        {}
    )


    total_balance = 0

    for user in data.get(
        "users",
        {}
    ).values():

        total_balance += int(
            user.get(
                "balance",
                0
            )
        )


    accepted_deposits = 0

    pending_deposits = 0

    rejected_deposits = 0


    for deposit in deposits.values():

        status = deposit.get(
            "status"
        )


        if status == "accepted":

            accepted_deposits += 1

        elif status == "rejected":

            rejected_deposits += 1

        else:

            pending_deposits += 1


    accepted_withdraws = 0

    pending_withdraws = 0

    rejected_withdraws = 0


    for withdraw in withdraws.values():

        status = withdraw.get(
            "status"
        )


        if status == "accepted":

            accepted_withdraws += 1

        elif status == "rejected":

            rejected_withdraws += 1

        else:

            pending_withdraws += 1


    status = data["settings"].get(
        "bot",
        True
    )


    status_text = (
        "🟢 روشن"
        if status
        else
        "🔴 خاموش"
    )


    await query.edit_message_text(

        "📊 آمار ربات\n\n"

        f"👥 تعداد کاربران: {users_count:,}\n"

        f"💰 مجموع موجودی کاربران: "
        f"{total_balance:,} DOGS\n\n"

        "💳 واریزها:\n"
        f"✅ تایید شده: {accepted_deposits:,}\n"
        f"⏳ در انتظار: {pending_deposits:,}\n"
        f"❌ رد شده: {rejected_deposits:,}\n\n"

        "💰 برداشت‌ها:\n"
        f"✅ پرداخت شده: {accepted_withdraws:,}\n"
        f"⏳ در انتظار: {pending_withdraws:,}\n"
        f"❌ رد شده: {rejected_withdraws:,}\n\n"

        f"🤖 وضعیت ربات: {status_text}",

        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 پنل مالک",
                        callback_data="admin"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 منوی اصلی",
                        callback_data="home"
                    )
                ]
            ]
        )
    )

# =========================
# BUTTON CALLBACK
# =========================

async def callback_handler(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except:
        pass


    user = query.from_user

    if not user:
        return


    create_user(user)

    action = query.data


    # =========================
    # HOME
    # =========================

    if action == "home":

        await query.edit_message_text(

            "🤖 منوی اصلی\n\n"

            f"💰 موجودی شما:\n"
            f"{balance(user.id):,} DOGS",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return


    # =========================
    # PROFILE
    # =========================

    if action == "profile":

        await profile(query)

        return


    # =========================
    # DEPOSIT
    # =========================

    if action == "deposit":

        await deposit_menu(query)

        return


    # =========================
    # WITHDRAW
    # =========================

    if action == "withdraw":

        await withdraw_menu(
            query,
            context
        )

        return


    # =========================
    # SUPPORT
    # =========================

    if action == "support":

        await support(
            query,
            context
        )

        return


    # =========================
    # GAME INFO
    # =========================

    if action == "game_info":

        await game_info(query)

        return


    # =========================
    # ULTRA
    # =========================

    if action == "ultra":

        await ultra(
            query,
            context
        )

        return


    # =========================
    # EXCHANGE
    # =========================

    if action == "exchange":

        await exchange(
            query,
            context
        )

        return


    # =========================
    # ADMIN PANEL
    # =========================

    if action == "admin":

        if not is_owner(user.id):

            await query.answer(
                "❌ دسترسی ندارید.",
                show_alert=True
            )

            return


        await admin_panel(query)

        return


    # =========================
    # ADMIN TOGGLE
    # =========================

    if action == "admin_toggle":

        await admin_toggle(query)

        return


    # =========================
    # ADMIN STATS
    # =========================

    if action == "admin_stats":

        await admin_stats(query)

        return

# =========================
# GENERAL MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    if not update.message:
        return

    user = update.effective_user

    if not user:
        return

    create_user(user)

    state = context.user_data.get(
        "state"
    )


    # =========================
    # DEPOSIT STATES
    # =========================

    if state in [
        "deposit_receipt",
        "deposit_amount"
    ]:

        await handle_deposit(
            update,
            context
        )

        return


    # =========================
    # WITHDRAW STATES
    # =========================

    if state in [
        "withdraw_address",
        "withdraw_amount"
    ]:

        await handle_withdraw(
            update,
            context
        )

        return


    # =========================
    # NORMAL MESSAGE
    # =========================

    if update.message.text:

        text = update.message.text.strip()

        if text.startswith("بازی "):

            try:

                amount = int(
                    text.split()[1]
                )

                await game_command(
                    update,
                    context
                )

                return

            except:

                pass


        await update.message.reply_text(

            "❌ دستور یا گزینه نامعتبر است.\n\n"

            "از دکمه‌های منوی اصلی استفاده کنید.",

            reply_markup=main_keyboard(
                user.id
            )

        )

        return


    # =========================
    # OTHER MESSAGE TYPES
    # =========================

    await update.message.reply_text(

        "❌ پیام نامعتبر است.\n\n"
        "لطفاً از گزینه‌های ربات استفاده کنید.",

        reply_markup=main_keyboard(
            user.id
        )

        )

# =========================
# MAIN
# =========================

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
    # GAME COMMAND
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
    # GENERAL BUTTONS
    # =========================

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # =========================
    # GENERAL MESSAGES
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

    print(
        "================================="
    )

    print(
        "✅ BOT STARTED"
    )

    print(
        "🤖 Telegram bot is running..."
    )

    print(
        "================================="
    )


    app.run_polling(
        drop_pending_updates=True
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":

    main()
