import json
import os
import random
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
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

# واریز و برداشت
MIN_DEPOSIT = 5000
MIN_WITHDRAW = 10000


# =========================
# GAME SETTINGS
# =========================

MIN_GAME = 500
MAX_GAME = 20000
GAME_FEE = 0


# =========================
# DATA FILE
# =========================

DATA_FILE = "bot_data.json"

# =========================
# MAIN KEYBOARD (PRIVATE ONLY)
# =========================

def main_keyboard(uid, chat_type="private"):

    # اگر گروه بود اصلاً کیبورد نساز
    if chat_type != "private":
        return None

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
# BACK KEYBOARD (PRIVATE ONLY)
# =========================

def back_keyboard(chat_type="private"):

    if chat_type != "private":
        return None

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

    chat_type = update.effective_chat.type

    await update.message.reply_text(

        "🤖 به ربات خوش آمدید.\n\n"

        f"👤 {user.first_name}\n"

        f"💰 موجودی شما:\n"
        f"{balance(user.id):,} DOGS\n\n"

        "یکی از گزینه‌های زیر را انتخاب کنید:",

        reply_markup=main_keyboard(
            user.id,
            chat_type
        )
    )

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




    

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    MessageHandler(
        filters.TEXT
        & filters.Regex(r"^بازی\s+\d+$"),
        game_command
    )
)

# =========================
# NORMAL BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text
    user = update.effective_user

    if text == "👤 پروفایل":
        await show_profile(update, context)

    elif text == "👥 زیر مجموعه":
        await show_referrals(update, context)

    elif text == "💳 واریزی":
        await show_deposit(update, context)

    elif text == "💰 برداشت":
        await show_withdraw(update, context)

    elif text == "🎧 پشتیبانی":
        await show_support(update, context)

    elif text == "🔙 برگشت":
        await go_home(update, context)


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


    # START
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # دکمه های کیبورد پیوی
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            button_handler
        )
    )


    # عکس و متن برای واریز و برداشت
    app.add_handler(
        MessageHandler(
            (
                filters.TEXT |
                filters.PHOTO
            )
            & ~filters.COMMAND,
            message_handler
        )
    )


    # بازی داخل گروه
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(
                r"^بازی\s+\d+$"
            ),
            game_command
        )
    )


    # دکمه های بازی
    app.add_handler(
        CallbackQueryHandler(
            game_callback,
            pattern=r"^(join_game|cancel_game)$"
        )
    )


    print("==============================")
    print("✅ BOT STARTED")
    print("==============================")


    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
