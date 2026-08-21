import os
import json
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 8552447077

DATA_FILE = "bot_data.json"

MIN_WITHDRAW = 10000
REF_REWARD = 50

DEFAULT = {
    "users": {},
    "pending_withdrawals": {},
    "pending_deposits": {},
    "settings": {
        "enabled": True,
        "channel": "",
        "group": ""
    },
    "owner_id": OWNER_ID
}


def save():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load():
    if not os.path.exists(DATA_FILE):
        return DEFAULT
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT


data = load()


def ensure(user):
    uid = str(user.id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "balance": 0,
            "refs": []
        }
        save()


def bal(uid):
    u = data["users"].get(str(uid))
    return int(u.get("balance", 0)) if u else 0


def add(uid, amount):
    if str(uid) in data["users"]:
        data["users"][str(uid)]["balance"] += int(amount)
        save()
        return True
    return False


def remove(uid, amount):
    if bal(uid) >= amount:
        data["users"][str(uid)]["balance"] -= int(amount)
        save()
        return True
    return False


def owner(uid):
    return int(uid) == int(data.get("owner_id", OWNER_ID))


def keyboard(uid):
    rows = [
        [
            InlineKeyboardButton("💰 برداشت", callback_data="withdraw"),
            InlineKeyboardButton("💳 واریز", callback_data="deposit")
        ],
        [
            InlineKeyboardButton("👤 پروفایل", callback_data="profile"),
            InlineKeyboardButton("👥 زیرمجموعه", callback_data="ref")
        ],
        [
            InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")
        ]
    ]
    if owner(uid):
        rows.append([InlineKeyboardButton("⚙️ پنل مالک", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure(update.effective_user)
    await update.message.reply_text(
        f"🤖 خوش آمدید\n\n💰 موجودی: {bal(update.effective_user.id):,} DOGS",
        reply_markup=keyboard(update.effective_user.id)
    )


async def callback(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    ensure(q.from_user)

    if q.data == "admin":
        if owner(uid):
            await q.edit_message_text(
                "⚙️ پنل مالک\n\n"
                "🟢/🔴 روشن خاموش ربات\n"
                "📢 چنل اجباری\n"
                "👥 گپ اجباری\n"
                "📊 آمار"
            )
        else:
            await q.answer("دسترسی ندارید", show_alert=True)

    elif q.data == "profile":
        await q.edit_message_text(
            f"👤 پروفایل\n\n🆔 {uid}\n💰 {bal(uid):,} DOGS",
            reply_markup=keyboard(uid)
        )

    elif q.data == "withdraw":
        context.user_data["state"] = "withdraw"
        await q.edit_message_text("مقدار برداشت را ارسال کنید.")

    elif q.data == "deposit":
        context.user_data["state"] = "deposit"
        await q.edit_message_text("رسید واریز را ارسال کنید.")

    elif q.data == "support":
        context.user_data["state"] = "support"
        await q.edit_message_text("پیام پشتیبانی را ارسال کنید.")

    elif q.data == "ref":
        await q.edit_message_text("👥 لینک زیرمجموعه بعدا ساخته می‌شود.")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure(user)
    text = (update.message.text or "").strip()

    # انتقال برای همه
    if text.startswith("انتقال"):
        p = text.split()
        if len(p) < 2:
            return await update.message.reply_text("مثال: انتقال 1000")

        try:
            amount = int(p[1])
        except:
            return

        target = None

        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user.id
        elif len(p) >= 3:
            target = int(p[2])

        if not target or target == user.id:
            return await update.message.reply_text("❌ مقصد اشتباه")

        ensure(update.message.reply_to_message.from_user) if update.message.reply_to_message else None

        if remove(user.id, amount) and add(target, amount):
            await update.message.reply_text("✅ انتقال انجام شد.")
        else:
            await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    state = context.user_data.get("state")

    if state == "support":
        await context.bot.send_message(OWNER_ID, f"🎧 پشتیبانی\n{user.id}\n{text}")
        context.user_data.clear()
        return await update.message.reply_text("✅ ارسال شد.")

    if state == "deposit":
        did = str(random.randint(10000000,99999999))
        data["pending_deposits"][did] = {"user":user.id,"text":text}
        save()
        context.user_data.clear()
        return await update.message.reply_text("✅ رسید ارسال شد.")

    if state == "withdraw":
        try:
            amount=int(text)
        except:
            return
        if remove(user.id, amount):
            await update.message.reply_text("✅ درخواست برداشت ثبت شد.")
        else:
            await update.message.reply_text("❌ موجودی کافی نیست.")
        context.user_data.clear()
        return

    await update.message.reply_text("از منو استفاده کنید.", reply_markup=keyboard(user.id))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    print("BOT STARTED")
    app.run_polling()


if __name__ == "__main__":
    main()
