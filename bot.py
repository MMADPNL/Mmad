import json
import os
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

ULTRA_ID = "@CyyFr"

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

    "games": {},

    "owner": OWNER_ID,


    "settings": {

        "bot_status": True,

        "force_channel": "",

        "force_group": ""

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

            old_data = json.load(f)


        for key in DEFAULT_DATA:

            if key not in old_data:

                old_data[key] = DEFAULT_DATA[key]


        return old_data


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

    return data["users"].get(str(uid))



def balance(uid):

    user = get_user(uid)

    if not user:

        return 0


    return int(
        user.get("balance", 0)
    )



def add_balance(uid, amount):

    user = get_user(uid)


    if not user:

        return False


    user["balance"] = int(
        user.get("balance", 0)
    ) + int(amount)


    save_data()

    return True



def remove_balance(uid, amount):

    user = get_user(uid)


    if not user:

        return False



    if int(user.get("balance", 0)) < int(amount):

        return False



    user["balance"] -= int(amount)


    save_data()

    return True



def is_owner(uid):

    return int(uid) == int(
        data.get("owner", OWNER_ID)
    )



def set_owner(uid):

    data["owner"] = int(uid)

    save_data()

# =========================
# KEYBOARDS
# =========================

def back_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="home"
            )
        ]
    ])


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
        rows.append([
            InlineKeyboardButton(
                "⚙️ پنل مالک",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(rows)


def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🟢 روشن / 🔴 خاموش ربات",
                callback_data="admin_toggle"
            )
        ],
        [
            InlineKeyboardButton(
                "📢 چنل اجباری",
                callback_data="admin_channel"
            ),
            InlineKeyboardButton(
                "👥 گپ اجباری",
                callback_data="admin_group"
            )
        ],
        [
            InlineKeyboardButton(
                "👑 انتقال مالکیت",
                callback_data="admin_transfer"
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
    ])


# =========================
# START
# =========================

async def start(update, context):

    try:

        user = update.effective_user

        if not user:
            return

        create_user(user)

        await update.message.reply_text(
            "🤖 خوش آمدید\n\n"
            f"💰 موجودی شما:\n"
            f"{balance(user.id):,} DOGS",
            reply_markup=main_keyboard(user.id)
        )

    except Exception as e:

        print("START ERROR:", e)


# =========================
# PROFILE
# =========================

async def profile(query):

    uid = query.from_user.id

    user = get_user(uid)

    if not user:

        create_user(query.from_user)

        user = get_user(uid)

    await query.edit_message_text(
        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {user.get('name', '')}\n"
        f"💰 موجودی: {balance(uid):,} DOGS",
        reply_markup=back_button()
    )


# =========================
# GAME INFO
# =========================

async def game_info(query):

    await query.edit_message_text(
        "🎮 بازی دو نفره\n\n"
        "برای ساخت بازی در گروه بنویسید:\n"
        "بازی 500\n\n"
        "💰 حداقل: 500 DOGS\n"
        "💰 حداکثر: 20,000 DOGS\n"
        "👑 کارمزد مالک: 100 DOGS",
        reply_markup=back_button()
        )

# =========================
# DEPOSIT MENU
# =========================

async def deposit_menu(query):

    await query.edit_message_text(
        "💳 روش واریز را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
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
        ])
    )


# =========================
# ULTRA
# =========================

async def ultra(query, context):

    context.user_data["state"] = "deposit"

    await query.edit_message_text(
        "💎 اولترا\n\n"
        f"به این آیدی DOGS بزنید:\n"
        f"{ULTRA_ID}\n\n"
        "بعد از واریز، شات یا پیام رسید خود را ارسال کنید.\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",
        reply_markup=back_button()
    )


# =========================
# EXCHANGE
# =========================

async def exchange(query, context):

    context.user_data["state"] = "deposit"

    await query.edit_message_text(
        "💎 صرافی\n\n"
        f"به این ولت DOGS بزنید:\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از واریز، شات یا لینک تراکنش خود را ارسال کنید.\n"
        "توسط مالک بررسی و تایید می‌شود.\n\n"
        f"💰 حداقل واریز: {MIN_DEPOSIT:,} DOGS",
        reply_markup=back_button()
    )


# =========================
# WITHDRAW
# =========================

async def withdraw_menu(query, context):

    context.user_data["state"] = "withdraw"

    await query.edit_message_text(
        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW:,} DOGS\n\n"
        "مقدار DOGS را به صورت عدد ارسال کنید.",
        reply_markup=back_button()
    )


# =========================
# SUPPORT
# =========================

async def support(query, context):

    context.user_data["state"] = "support"

    await query.edit_message_text(
        "🎧 پشتیبانی\n\n"
        f"{SUPPORT_USERNAME}\n\n"
        "پیام خود را ارسال کنید.",
        reply_markup=back_button()
    )

# =========================
# CALLBACK HANDLER
# =========================

async def callback_handler(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user = query.from_user

    if not user:
        return

    create_user(user)

    action = query.data


    # =====================
    # HOME
    # =====================

    if action == "home":

        await query.edit_message_text(
            "🤖 منوی اصلی\n\n"
            f"💰 موجودی: {balance(user.id):,} DOGS",
            reply_markup=main_keyboard(user.id)
        )

        return


    # =====================
    # PROFILE
    # =====================

    if action == "profile":

        await profile(query)

        return


    # =====================
# DEPOSIT
# =====================

if state == "deposit":

    receipt = text

    if update.message.photo:

        receipt = (
            "📸 عکس رسید ارسال شد\n"
            f"🆔 کاربر: {user.id}\n"
            f"📝 توضیحات: {text if text else 'بدون توضیح'}"
        )

    elif not text:

        await update.message.reply_text(
            "❌ لطفاً عکس رسید، لینک تراکنش یا متن رسید را ارسال کنید."
        )

        return


    uid = str(user.id)

    data["deposits"][uid] = {

        "receipt": receipt,
        "status": "pending",
        "time": datetime.now().isoformat()

    }

    save_data()

    context.user_data.clear()


    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ توسط مالک بررسی و تایید می‌شود."
    )


    # =====================
    # SEND TO OWNER
    # =====================

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(
                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"👤 نام: {user.first_name or '-'}\n\n"
                f"📝 رسید:\n{receipt}"
            ),

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


        # اگر عکس بود، خود عکس را هم برای مالک بفرست

        if update.message.photo:

            await context.bot.send_photo(

                chat_id=OWNER_ID,

                photo=update.message.photo[-1].file_id,

                caption=(
                    f"📸 عکس رسید واریز\n"
                    f"👤 کاربر: {user.id}\n"
                    f"📝 {text if text else 'بدون توضیح'}"
                )

            )


    except Exception as e:

        print(
            f"Deposit owner notification error: {e}"
        )


    return


    # =====================
    # SEND TO OWNER
    # =====================

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(
                "💳 واریز جدید\n\n"
                f"👤 کاربر: {user.id}\n"
                f"👤 نام: {user.first_name or '-'}\n\n"
                f"📝 رسید:\n{receipt}"
            ),

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


        # اگر عکس بود، خود عکس را هم برای مالک بفرست

        if update.message.photo:

            await context.bot.send_photo(

                chat_id=OWNER_ID,

                photo=update.message.photo[-1].file_id,

                caption=(
                    f"📸 عکس رسید واریز\n"
                    f"👤 کاربر: {user.id}\n"
                    f"📝 {text if text else 'بدون توضیح'}"
                )

            )


    except Exception as e:

        print(
            f"Deposit owner notification error: {e}"
        )


    return


    # =====================
    # WITHDRAW
    # =====================

    if action == "withdraw":

        await withdraw_menu(query, context)

        return


    # =====================
    # SUPPORT
    # =====================

    if action == "support":

        await support(query, context)

        return


    # =====================
    # GAME INFO
    # =====================

    if action == "game_info":

        await game_info(query)

        return


    # =====================
    # ADMIN PANEL
    # =====================

    if action == "admin":

        if not is_owner(user.id):

            try:
                await query.answer(
                    "❌ دسترسی ندارید",
                    show_alert=True
                )
            except Exception:
                pass

            return


        bot_status = data.get(
            "settings",
            {}
        ).get(
            "bot",
            True
        )

        status_text = (
            "🟢 روشن"
            if bot_status
            else
            "🔴 خاموش"
        )


        await query.edit_message_text(
            "⚙️ پنل مالک\n\n"
            f"وضعیت ربات: {status_text}",
            reply_markup=admin_keyboard()
        )

        return


    # =====================
    # ADMIN TOGGLE
    # =====================

    if action == "admin_toggle":

        if not is_owner(user.id):
            return


        if "settings" not in data:
            data["settings"] = {}


        current = data["settings"].get(
            "bot",
            True
        )

        data["settings"]["bot"] = not current

        save_data()


        status_text = (
            "🟢 روشن"
            if data["settings"]["bot"]
            else
            "🔴 خاموش"
        )


        await query.edit_message_text(
            "⚙️ پنل مالک\n\n"
            f"وضعیت ربات: {status_text}",
            reply_markup=admin_keyboard()
        )

        return


    # =====================
    # ADMIN CHANNEL
    # =====================

    if action == "admin_channel":

        if not is_owner(user.id):
            return


        context.user_data["admin_state"] = "channel"


        await query.edit_message_text(
            "📢 چنل اجباری\n\n"
            "آیدی یا یوزرنیم چنل را ارسال کنید.\n\n"
            "مثال:\n"
            "@Channel",
            reply_markup=back_button()
        )

        return


    # =====================
    # ADMIN GROUP
    # =====================

    if action == "admin_group":

        if not is_owner(user.id):
            return


        context.user_data["admin_state"] = "group"


        await query.edit_message_text(
            "👥 گپ اجباری\n\n"
            "آیدی یا یوزرنیم گپ را ارسال کنید.\n\n"
            "مثال:\n"
            "@Group",
            reply_markup=back_button()
        )

        return


    # =====================
    # ADMIN TRANSFER
    # =====================

    if action == "admin_transfer":

        if not is_owner(user.id):
            return


        context.user_data["admin_state"] = "transfer_owner"


        await query.edit_message_text(
            "👑 انتقال مالکیت\n\n"
            "آیدی عددی مالک جدید را ارسال کنید.\n\n"
            "مثال:\n"
            "123456789",
            reply_markup=back_button()
        )

        return


    # =====================
    # ADMIN STATS
    # =====================

    if action == "admin_stats":

        if not is_owner(user.id):
            return


        users_count = len(data.get("users", {}))

        total_balance = sum(
            int(u.get("balance", 0))
            for u in data.get("users", {}).values()
        )


        await query.edit_message_text(
            "📊 آمار ربات\n\n"
            f"👤 تعداد کاربران: {users_count}\n"
            f"💰 مجموع موجودی: {total_balance:,} DOGS",
            reply_markup=admin_keyboard()
        )

        return

# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update, context):

    if not update.message:
        return

    user = update.effective_user

    if not user:
        return

    create_user(user)

    text = (update.message.text or "").strip()

    if not text:
        return


    # =====================
    # OWNER ADMIN STATES
    # =====================

    admin_state = context.user_data.get("admin_state")


    if is_owner(user.id) and admin_state:

        # -----------------
        # CHANNEL
        # -----------------

        if admin_state == "channel":

            if "settings" not in data:
                data["settings"] = {}

            data["settings"]["channel"] = text

            save_data()

            context.user_data.pop("admin_state", None)

            await update.message.reply_text(
                "✅ چنل اجباری ثبت شد.\n\n"
                f"📢 چنل: {text}",
                reply_markup=admin_keyboard()
            )

            return


        # -----------------
        # GROUP
        # -----------------

        if admin_state == "group":

            if "settings" not in data:
                data["settings"] = {}

            data["settings"]["group"] = text

            save_data()

            context.user_data.pop("admin_state", None)

            await update.message.reply_text(
                "✅ گپ اجباری ثبت شد.\n\n"
                f"👥 گپ: {text}",
                reply_markup=admin_keyboard()
            )

            return


        # -----------------
        # TRANSFER OWNER
        # -----------------

        if admin_state == "transfer_owner":

            try:

                new_owner = int(text)

            except ValueError:

                await update.message.reply_text(
                    "❌ آیدی باید عددی باشد.\n\n"
                    "مثال:\n"
                    "123456789"
                )

                return


            if new_owner <= 0:

                await update.message.reply_text(
                    "❌ آیدی نامعتبر است."
                )

                return


            data["owner"] = new_owner

            save_data()

            context.user_data.pop("admin_state", None)

            await update.message.reply_text(
                "✅ مالکیت منتقل شد.\n\n"
                f"👑 مالک جدید: {new_owner}"
            )

            return


    # =====================
    # WITHDRAW
    # =====================

    state = context.user_data.get("state")


    if state == "withdraw":

        try:

            amount = int(text)

        except ValueError:

            await update.message.reply_text(
                "❌ فقط عدد ارسال کنید."
            )

            return


        if amount < MIN_WITHDRAW:

            await update.message.reply_text(
                f"❌ حداقل برداشت "
                f"{MIN_WITHDRAW:,} DOGS است."
            )

            return


        if not remove_balance(
            user.id,
            amount
        ):

            await update.message.reply_text(
                "❌ موجودی کافی نیست."
            )

            return


        data["withdraws"][str(user.id)] = {

            "user_id": user.id,

            "amount": amount,

            "status": "pending",

            "date": datetime.now().isoformat()

        }

        save_data()


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(
            "✅ درخواست برداشت ثبت شد.\n\n"
            f"💰 مقدار: {amount:,} DOGS\n"
            "⏳ منتظر بررسی مالک باشید."
        )


        try:

            await context.bot.send_message(

                chat_id=OWNER_ID,

                text=(
                    "💰 برداشت جدید\n\n"
                    f"👤 کاربر: {user.id}\n"
                    f"💰 مقدار: {amount:,} DOGS"
                )

            )

        except Exception as e:

            print(
                "WITHDRAW OWNER MESSAGE ERROR:",
                e
            )

        return


    # =====================
    # DEPOSIT RECEIPT
    # =====================

    if state == "deposit":

        if len(text) < 2:

            await update.message.reply_text(
                "❌ رسید یا لینک تراکنش معتبر ارسال کنید."
            )

            return


        data["deposits"][str(user.id)] = {

            "user_id": user.id,

            "receipt": text,

            "status": "pending",

            "date": datetime.now().isoformat()

        }

        save_data()


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(
            "✅ رسید شما ارسال شد.\n\n"
            "⏳ توسط مالک بررسی و تایید می‌شود."
        )


        try:

            await context.bot.send_message(

                chat_id=OWNER_ID,

                text=(
                    "💳 واریز جدید\n\n"
                    f"👤 کاربر: {user.id}\n"
                    f"👤 نام: {user.first_name or '-'}\n\n"
                    f"📝 رسید / لینک:\n{text}"
                ),

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
                "DEPOSIT OWNER MESSAGE ERROR:",
                e
            )

        return


    # =====================
    # SUPPORT
    # =====================

    if state == "support":

        try:

            await context.bot.send_message(

                chat_id=OWNER_ID,

                text=(
                    "🎧 پیام پشتیبانی\n\n"
                    f"👤 کاربر: {user.id}\n"
                    f"👤 نام: {user.first_name or '-'}\n\n"
                    f"💬 پیام:\n{text}"
                )

            )

        except Exception as e:

            print(
                "SUPPORT OWNER MESSAGE ERROR:",
                e
            )


        context.user_data.pop(
            "state",
            None
        )


        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد."
        )

        return


    # =====================
    # NO ACTIVE STATE
    # =====================

    # اگر پیام معمولی بود، چیزی اجرا نکن
    return

# =========================
# ADMIN CALLBACKS
# =========================

async def admin_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass

    user = query.from_user

    if not user:
        return

    # فقط مالک
    if not is_owner(user.id):

        try:
            await query.answer(
                "❌ دسترسی ندارید",
                show_alert=True
            )
        except Exception:
            pass

        return


    action = query.data


    # =====================
    # ACCEPT DEPOSIT
    # =====================

    if action.startswith("ok_dep_"):

        try:
            uid = int(
                action.split("_")[2]
            )
        except (ValueError, IndexError):

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        deposit = data.get(
            "deposits",
            {}
        ).get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return


        # ضد دوبار تایید
        if deposit.get("status") == "accepted":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً تایید شده است."
            )

            return


        # اگر قبلاً رد شده
        if deposit.get("status") == "rejected":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً رد شده است."
            )

            return


        deposit["status"] = "accepted"

        save_data()


        # مبلغ قابل شارژ
        amount = int(
            deposit.get(
                "amount",
                MIN_DEPOSIT
            )
        )


        # برای رسیدهای قدیمی که مبلغ نداشتند
        if amount < MIN_DEPOSIT:

            amount = MIN_DEPOSIT


        add_balance(
            uid,
            amount
        )


        try:

            await query.edit_message_text(

                "✅ واریز تایید شد\n\n"
                f"👤 کاربر: {uid}\n"
                f"💰 مبلغ شارژ: {amount:,} DOGS"

            )

        except Exception as e:

            print(
                "EDIT ACCEPT ERROR:",
                e
            )


        # اطلاع به کاربر
        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(
                    "✅ واریز شما تایید شد.\n\n"
                    f"💰 مبلغ اضافه‌شده: "
                    f"{amount:,} DOGS\n"
                    f"💳 موجودی جدید: "
                    f"{balance(uid):,} DOGS"
                )

            )

        except Exception as e:

            print(
                "USER ACCEPT MESSAGE ERROR:",
                e
            )


        return


    # =====================
    # REJECT DEPOSIT
    # =====================

    if action.startswith("no_dep_"):

        try:
            uid = int(
                action.split("_")[2]
            )
        except (ValueError, IndexError):

            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )

            return


        deposit = data.get(
            "deposits",
            {}
        ).get(
            str(uid)
        )


        if not deposit:

            await query.edit_message_text(
                "❌ درخواست واریز پیدا نشد."
            )

            return


        # ضد دوبار رد / تایید
        if deposit.get("status") == "rejected":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً رد شده است."
            )

            return


        if deposit.get("status") == "accepted":

            await query.edit_message_text(
                "⚠️ این واریز قبلاً تایید شده است."
            )

            return


        deposit["status"] = "rejected"

        save_data()


        try:

            await query.edit_message_text(

                "❌ واریز رد شد\n\n"
                f"👤 کاربر: {uid}"

            )

        except Exception as e:

            print(
                "EDIT REJECT ERROR:",
                e
            )


        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(
                    "❌ واریز شما رد شد.\n\n"
                    "در صورت اشتباه، با پشتیبانی تماس بگیرید."
                )

            )

        except Exception as e:

            print(
                "USER REJECT MESSAGE ERROR:",
                e
            )


        return


# =========================
# OWNER CHARGE
# =========================

async def owner_commands(update, context):

    if not update.message:
        return


    user = update.effective_user

    if not user:
        return


    if not is_owner(user.id):
        return


    text = (
        update.message.text or ""
    ).strip()


    # =====================
    # شارژ آیدی مقدار
    # =====================

    if text.startswith("شارژ"):

        parts = text.split()


        if len(parts) != 3:

            await update.message.reply_text(
                "❌ فرمت اشتباه است.\n\n"
                "مثال:\n"
                "شارژ 123456789 5000"
            )

            return


        try:

            uid = int(parts[1])

            amount = int(parts[2])

        except ValueError:

            await update.message.reply_text(
                "❌ آیدی و مقدار باید عدد باشند."
            )

            return


        if uid <= 0 or amount <= 0:

            await update.message.reply_text(
                "❌ مقدار نامعتبر است."
            )

            return


        if not get_user(uid):

            await update.message.reply_text(
                "❌ این کاربر هنوز ربات را شروع نکرده است."
            )

            return


        add_balance(
            uid,
            amount
        )


        await update.message.reply_text(

            "✅ شارژ انجام شد.\n\n"
            f"👤 کاربر: {uid}\n"
            f"💰 مقدار: {amount:,} DOGS\n"
            f"💳 موجودی جدید: {balance(uid):,} DOGS"

        )


        try:

            await context.bot.send_message(

                chat_id=uid,

                text=(
                    "💰 موجودی شما توسط مالک شارژ شد.\n\n"
                    f"➕ مبلغ: {amount:,} DOGS\n"
                    f"💳 موجودی: {balance(uid):,} DOGS"
                )

            )

        except Exception as e:

            print(
                "CHARGE USER MESSAGE ERROR:",
                e
            )

        return

# =========================
# GAME SYSTEM
# =========================

MIN_GAME = 500
MAX_GAME = 20000
GAME_FEE = 100

ACTIVE_GAMES = {}


# =========================
# CREATE GAME
# =========================

async def game_command(update, context):

    if not update.message:
        return

    chat = update.effective_chat

    # بازی فقط داخل گروه
    if chat.type not in ("group", "supergroup"):

        await update.message.reply_text(
            "❌ بازی فقط داخل گپ قابل انجام است."
        )

        return


    try:

        parts = update.message.text.strip().split()

        if len(parts) != 2:

            raise ValueError

        amount = int(parts[1])

    except (ValueError, IndexError):

        await update.message.reply_text(
            "❌ فرمت صحیح:\n\n"
            "بازی 500"
        )

        return


    # حداقل
    if amount < MIN_GAME:

        await update.message.reply_text(
            f"❌ حداقل بازی "
            f"{MIN_GAME:,} DOGS است."
        )

        return


    # حداکثر
    if amount > MAX_GAME:

        await update.message.reply_text(
            f"❌ حداکثر بازی "
            f"{MAX_GAME:,} DOGS است."
        )

        return


    user = update.effective_user

    create_user(user)


    # جلوگیری از ساخت چند بازی
    if chat.id in ACTIVE_GAMES:

        await update.message.reply_text(
            "❌ در این گپ یک بازی در انتظار ورود بازیکن است."
        )

        return


    # بررسی موجودی
    if balance(user.id) < amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست."
        )

        return


    # رزرو پول سازنده
    if not remove_balance(
        user.id,
        amount
    ):

        await update.message.reply_text(
            "❌ کسر موجودی انجام نشد؛ دوباره تلاش کنید."
        )

        return


    ACTIVE_GAMES[chat.id] = {

        "creator": user.id,

        "creator_name": (
            user.first_name or ""
        ),

        "amount": amount,

        "message_id": None

    }


    try:

        msg = await update.message.reply_text(

            "🎮 بازی آماده شد\n\n"

            f"👤 سازنده: "
            f"{user.first_name or user.id}\n"

            f"💰 مبلغ بازی: "
            f"{amount:,} DOGS\n\n"

            "یک نفر برای ورود به بازی دکمه زیر را بزند.",

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

        ACTIVE_GAMES[chat.id]["message_id"] = msg.message_id


    except Exception as e:

        # اگر ارسال پیام شکست خورد،
        # پول سازنده برگردد

        add_balance(
            user.id,
            amount
        )

        ACTIVE_GAMES.pop(
            chat.id,
            None
        )

        print(
            "CREATE GAME ERROR:",
            e
        )


# =========================
# GAME CALLBACK
# =========================

async def game_callback(update, context):

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass


    if not query.message:
        return


    chat_id = query.message.chat.id

    user = query.from_user


    game = ACTIVE_GAMES.get(chat_id)


    if not game:

        try:
            await query.answer(
                "❌ این بازی دیگر فعال نیست.",
                show_alert=True
            )
        except Exception:
            pass

        return


    action = query.data


    # =====================
    # CANCEL
    # =====================

    if action == "cancel_game":

        if user.id != game["creator"]:

            try:
                await query.answer(
                    "❌ فقط سازنده می‌تواند بازی را لغو کند.",
                    show_alert=True
                )
            except Exception:
                pass

            return


        amount = game["amount"]


        # برگرداندن مبلغ
        add_balance(
            user.id,
            amount
        )


        ACTIVE_GAMES.pop(
            chat_id,
            None
        )


        try:

            await query.edit_message_text(
                "❌ بازی لغو شد.\n\n"
                f"💰 مبلغ {amount:,} DOGS "
                "به موجودی سازنده برگشت."
            )

        except Exception as e:

            print(
                "CANCEL GAME ERROR:",
                e
            )

        return


    # =====================
    # JOIN
    # =====================

    if action != "join_game":
        return


    # سازنده نمی‌تواند وارد خودش شود
    if user.id == game["creator"]:

        try:
            await query.answer(
                "❌ نمی‌توانید وارد بازی خودتان شوید.",
                show_alert=True
            )
        except Exception:
            pass

        return


    create_user(user)


    amount = game["amount"]


    # بررسی موجودی نفر دوم
    if balance(user.id) < amount:

        try:
            await query.answer(
                "❌ موجودی کافی نیست.",
                show_alert=True
            )
        except Exception:
            pass

        return


    # کسر مبلغ نفر دوم
    if not remove_balance(
        user.id,
        amount
    ):

        try:
            await query.answer(
                "❌ خطا در کسر موجودی؛ دوباره تلاش کنید.",
                show_alert=True
            )
        except Exception:
            pass

        return


    creator_id = game["creator"]


    # =====================
    # تعیین برنده تصادفی
    # =====================

    winner = random.choice(
        [
            creator_id,
            user.id
        ]
    )


    loser = (
        user.id
        if winner == creator_id
        else creator_id
    )


    total = amount * 2

    prize = total - GAME_FEE


    # جایزه برنده
    add_balance(
        winner,
        prize
    )


    # کارمزد مالک
    add_balance(
        OWNER_ID,
        GAME_FEE
    )


    # حذف بازی
    ACTIVE_GAMES.pop(
        chat_id,
        None
    )


    try:

        await query.edit_message_text(

            "🎮 نتیجه بازی\n\n"

            f"🏆 برنده: {winner}\n"

            f"💰 جایزه: "
            f"{prize:,} DOGS\n\n"

            f"👤 بازنده: {loser}\n"

            f"👑 کارمزد مالک: "
            f"{GAME_FEE:,} DOGS"

        )

    except Exception as e:

        print(
            "GAME RESULT ERROR:",
            e
        )

        # بازی تمام شده؛ موجودی‌ها قبلاً ثبت شده‌اند


    return

# =========================
# ADMIN SETTINGS
# =========================

def get_settings():

    if "settings" not in data:
        data["settings"] = {
            "bot": True,
            "channel": "",
            "group": ""
        }

        save_data()

    return data["settings"]


# =========================
# FORCE JOIN CHECK
# =========================

async def check_force_join(update, context):

    user = update.effective_user

    if not user:
        return True

    settings = get_settings()

    channel = settings.get("channel", "")
    group = settings.get("group", "")


    # اگر چیزی تنظیم نشده
    if not channel and not group:
        return True


    for chat in [channel, group]:

        if not chat:
            continue

        try:

            member = await context.bot.get_chat_member(
                chat_id=chat,
                user_id=user.id
            )

            if member.status in (
                "member",
                "administrator",
                "creator"
            ):
                continue


            await update.effective_message.reply_text(
                "⚠️ برای استفاده از ربات ابتدا باید عضو موارد زیر شوید:\n\n"
                f"{chat}\n\n"
                "بعد از عضویت دوباره /start را بزنید."
            )

            return False


        except Exception as e:

            print(
                "FORCE JOIN ERROR:",
                e
            )

            # اگر چنل/گپ قابل بررسی نبود،
            # ربات کاربر را قفل نمی‌کند
            continue


    return True


# =========================
# ADMIN PANEL TEXT
# =========================

async def show_admin_panel(query):

    if not is_owner(query.from_user.id):
        return


    settings = get_settings()

    status = (
        "🟢 روشن"
        if settings.get("bot", True)
        else
        "🔴 خاموش"
    )


    channel = settings.get(
        "channel",
        ""
    ) or "تنظیم نشده"


    group = settings.get(
        "group",
        ""
    ) or "تنظیم نشده"


    await query.edit_message_text(

        "⚙️ پنل مالک\n\n"

        f"🤖 وضعیت ربات: {status}\n"

        f"📢 چنل اجباری: {channel}\n"

        f"👥 گپ اجباری: {group}\n\n"

        "گزینه موردنظر را انتخاب کنید:",

        reply_markup=admin_keyboard()

    )


# =========================
# ADMIN ACTIONS
# =========================

async def admin_settings_callback(
    update,
    context
):

    query = update.callback_query

    try:
        await query.answer()
    except Exception:
        pass


    user = query.from_user


    if not is_owner(user.id):

        try:
            await query.answer(
                "❌ دسترسی ندارید.",
                show_alert=True
            )
        except Exception:
            pass

        return


    action = query.data


    # =====================
    # TOGGLE BOT
    # =====================

    if action == "admin_toggle":

        settings = get_settings()

        settings["bot"] = not settings.get(
            "bot",
            True
        )

        save_data()


        await show_admin_panel(
            query
        )

        return


    # =====================
    # CHANNEL
    # =====================

    if action == "admin_channel":

        context.user_data[
            "admin_state"
        ] = "channel"


        await query.edit_message_text(

            "📢 چنل اجباری\n\n"

            "یوزرنیم یا آیدی چنل را بفرستید.\n\n"

            "مثال:\n"
            "@MyChannel\n\n"

            "برای لغو بنویسید:\n"
            "لغو",

            reply_markup=back_button()

        )

        return


    # =====================
    # GROUP
    # =====================

    if action == "admin_group":

        context.user_data[
            "admin_state"
        ] = "group"


        await query.edit_message_text(

            "👥 گپ اجباری\n\n"

            "یوزرنیم یا آیدی گپ را بفرستید.\n\n"

            "مثال:\n"
            "@MyGroup\n\n"

            "برای لغو بنویسید:\n"
            "لغو",

            reply_markup=back_button()

        )

        return


    # =====================
    # TRANSFER OWNER
    # =====================

    if action == "admin_transfer":

        context.user_data[
            "admin_state"
        ] = "transfer_owner"


        await query.edit_message_text(

            "👑 انتقال مالکیت\n\n"

            "آیدی عددی مالک جدید را ارسال کنید.\n\n"

            "مثال:\n"
            "123456789\n\n"

            "⚠️ بعد از انتقال، آیدی قبلی دیگر مالک نیست.",

            reply_markup=back_button()

        )

        return


    # =====================
    # STATS
    # =====================

    if action == "admin_stats":

        users = data.get(
            "users",
            {}
        )


        total = sum(
            int(
                u.get(
                    "balance",
                    0
                )
            )
            for u in users.values()
        )


        await query.edit_message_text(

            "📊 آمار ربات\n\n"

            f"👤 کاربران: {len(users)}\n"

            f"💰 مجموع موجودی: "
            f"{total:,} DOGS\n"

            f"💳 واریزها: "
            f"{len(data.get('deposits', {}))}\n"

            f"💰 برداشت‌ها: "
            f"{len(data.get('withdraws', {}))}",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 پنل مالک",
                        callback_data="admin"
                    )
                ]
            ])

        )

        return

# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:

        print("❌ BOT_TOKEN پیدا نشد")

        return


    app = Application.builder().token(
        BOT_TOKEN
    ).build()


    # =====================
    # START
    # =====================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # =====================
    # GAME
    # =====================

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(r"^بازی\s+\d+$"),
            game_command
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )


    # =====================
    # DEPOSIT ADMIN
    # =====================

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(ok_dep_|no_dep_)"
        )
    )


    # =====================
    # ADMIN PANEL
    # =====================

    app.add_handler(
        CallbackQueryHandler(
            admin_settings_callback,
            pattern=r"^admin_(toggle|channel|group|transfer|stats)$"
        )
    )


    # =====================
    # GENERAL BUTTONS
    # =====================

    app.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )


    # =====================
    # OWNER COMMANDS
    # =====================

    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.User(
                user_id=OWNER_ID
            ),
            owner_commands
        )
    )


    # =====================
    # NORMAL MESSAGES
    # =====================

    app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
        message_handler
    )
    )


    print(
        "✅ BOT STARTED"
    )


    # =====================
    # RUN
    # =====================

    app.run_polling(
        drop_pending_updates=True
    )


# =========================
# START BOT
# =========================

if __name__ == "__main__":

    main()
