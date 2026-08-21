import json
import os
import random
import asyncio
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


# =====================
# SETTINGS
# =====================

BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8552447077

GROUP_LINK = "https://t.me/TAK_B_ET"

SUPPORT = "@CyyFr"

DOGS_WALLET = "UQDuzMkT20XQbE4YLy5ZK7-pJzduzLPOoqhzIbOBJy3SpsiY"

MIN_WITHDRAW = 10000
REF_REWARD = 50

DATA_FILE = "data.json"


# =====================
# DATA
# =====================

DEFAULT = {
    "users": {},
    "games": {},
    "owner": OWNER_ID,
    "settings": {
        "bot": True,
        "channel": "",
        "group": ""
    }
}


def save():
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)


def load():

    if not os.path.exists(DATA_FILE):
        return DEFAULT

    try:
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            return json.load(f)

    except:
        return DEFAULT


data = load()


# =====================
# USERS
# =====================


def create_user(user):

    uid=str(user.id)

    if uid not in data["users"]:

        data["users"][uid]={
            "id":user.id,
            "name":user.first_name or "",
            "username":user.username or "",
            "balance":0,
            "refs":[],
            "ref_by":None,
            "date":datetime.now().isoformat()
        }

        save()

    return data["users"][uid]



def user(uid):

    return data["users"].get(str(uid))



def balance(uid):

    u=user(uid)

    if not u:
        return 0

    return int(u["balance"])



def add_balance(uid,amount):

    u=user(uid)

    if u:
        u["balance"]+=int(amount)
        save()



def remove_balance(uid,amount):

    u=user(uid)

    if not u:
        return False

    if u["balance"] < amount:
        return False

    u["balance"]-=int(amount)
    save()

    return True



def owner(uid):

    return int(uid)==int(data["owner"])



# =====================
# KEYBOARD
# =====================


def keyboard(uid):

    buttons=[

        [
        InlineKeyboardButton("💰 برداشت",callback_data="withdraw"),
        InlineKeyboardButton("💳 واریز",callback_data="deposit")
        ],

        [
        InlineKeyboardButton("👤 پروفایل",callback_data="profile"),
        InlineKeyboardButton("👥 زیرمجموعه",callback_data="ref")
        ],

        [
        InlineKeyboardButton("🎮 بازی",callback_data="game")
        ]

    ]


    if owner(uid):

        buttons.append(
            [
            InlineKeyboardButton(
                "⚙️ پنل مالک",
                callback_data="admin"
            )
            ]
        )


    return InlineKeyboardMarkup(buttons)



# =====================
# START
# =====================


async def start(update,context):

    u=update.effective_user

    create_user(u)


    await update.message.reply_text(
        "🤖 خوش آمدید\n\n"
        f"💰 موجودی: {balance(u.id):,} DOGS",
        reply_markup=keyboard(u.id)
                 )
    # =====================
# PROFILE
# =====================

async def profile(query):

    uid=query.from_user.id
    u=user(uid)

    await query.edit_message_text(
        "👤 پروفایل\n\n"
        f"🆔 آیدی: {uid}\n"
        f"👤 نام: {u['name']}\n"
        f"💰 موجودی: {balance(uid):,} DOGS\n"
        f"👥 زیرمجموعه: {len(u['refs'])}"
    )



# =====================
# REF
# =====================

async def ref(query,context):

    uid=query.from_user.id

    bot=await context.bot.get_me()

    link=f"https://t.me/{bot.username}?start={uid}"


    await query.edit_message_text(
        "👥 زیرمجموعه گیری\n\n"
        f"لینک شما:\n{link}\n\n"
        f"🎁 هر دعوت موفق: {REF_REWARD} DOGS"
    )



# =====================
# GAME
# =====================


async def game_menu(query):

    await query.edit_message_text(
        "🎮 بازی دوستان\n\n"
        "مبلغ بازی را با دستور زیر در گپ بزن:\n\n"
        "بازی 500",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                InlineKeyboardButton(
                    "❌ بستن",
                    callback_data="home"
                )
                ]
            ]
        )
    )



async def create_game(update,amount):

    uid=update.effective_user.id


    if balance(uid)<amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )
        return


    if uid in data["games"]:

        await update.message.reply_text(
            "❌ شما یک بازی فعال دارید"
        )
        return


    remove_balance(uid,amount)


    data["games"][uid]={
        "owner":uid,
        "amount":amount,
        "player":None
    }

    save()


    await update.message.reply_text(
        "🎮 بازی ساخته شد\n\n"
        f"💰 مبلغ: {amount} DOGS\n\n"
        "دوست شما می‌تواند وارد شود:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                InlineKeyboardButton(
                    "🎮 بازی با دوستان",
                    callback_data=f"join_{uid}"
                )
                ],
                [
                InlineKeyboardButton(
                    "❌ لغو",
                    callback_data=f"cancel_{uid}"
                )
                ]
            ]
        )
    )



async def join_game(query):

    uid=query.from_user.id

    owner_id=int(
        query.data.split("_")[1]
    )


    if owner_id not in data["games"]:

        await query.answer(
            "بازی تمام شده",
            show_alert=True
        )
        return


    game=data["games"][owner_id]


    if game["player"]:

        await query.answer(
            "یک نفر وارد شده",
            show_alert=True
        )
        return


    if uid==owner_id:

        return


    if balance(uid)<game["amount"]:

        await query.answer(
            "موجودی کافی نیست",
            show_alert=True
        )
        return


    remove_balance(
        uid,
        game["amount"]
    )


    game["player"]=uid

    save()


    await query.edit_message_text(
        "🎮 بازی شروع شد..."
    )


    await asyncio.sleep(2)


    a=random.randint(1,6)
    b=random.randint(1,6)


    amount=game["amount"]


    if a>b:

        winner=owner_id

    elif b>a:

        winner=uid

    else:

        add_balance(owner_id,amount)
        add_balance(uid,amount)

        del data["games"][owner_id]
        save()

        await query.message.reply_text(
            "🤝 مساوی شد\nمبلغ برگشت داده شد"
        )
        return



    add_balance(
        winner,
        int(amount*1.8)
    )


    fee=int(amount*0.2)

    add_balance(
        data["owner"],
        fee
    )


    await query.message.reply_text(
        "🏆 نتیجه بازی\n\n"
        f"برنده: {winner}\n"
        f"🎁 جایزه: {int(amount*1.8)} DOGS\n"
        f"💰 کارمزد مالک: {fee} DOGS"
    )


    del data["games"][owner_id]
    save()



async def cancel_game(query):

    uid=query.from_user.id

    owner_id=int(
        query.data.split("_")[1]
    )


    if uid!=owner_id:

        return


    game=data["games"].get(owner_id)


    if game:

        add_balance(
            uid,
            game["amount"]
        )

        del data["games"][owner_id]

        save()


    await query.edit_message_text(
        "❌ بازی لغو شد\nمبلغ برگشت داده شد"
    )



# =====================
# TRANSFER REPLY
# =====================


async def transfer(update):

    if not update.message.reply_to_message:
        return


    text=update.message.text


    try:

        amount=int(
            text.split()[1]
        )

    except:

        return


    sender=update.effective_user.id

    target=update.message.reply_to_message.from_user.id


    if sender==target:
        return


    if balance(sender)<amount:

        await update.message.reply_text(
            "❌ موجودی کافی نیست"
        )
        return


    remove_balance(
        sender,
        amount
    )

    add_balance(
        target,
        amount
    )


    await update.message.reply_text(
        "✅ انتقال انجام شد\n\n"
        f"💰 مقدار: {amount:,} DOGS"
    )# =====================
# DEPOSIT
# =====================

async def deposit_menu(query,context):

    context.user_data["state"]="deposit"


    await query.edit_message_text(
        "💳 واریز DOGS\n\n"
        "یکی را انتخاب کنید:\n\n"
        "اولترا:\n"
        "@CyyFr\n\n"
        "صرافی:\n"
        f"{DOGS_WALLET}\n\n"
        "بعد از واریز شات یا لینک تراکنش را ارسال کنید."
    )



# =====================
# WITHDRAW
# =====================

async def withdraw_menu(query,context):

    context.user_data["state"]="withdraw"


    await query.edit_message_text(
        "💰 برداشت\n\n"
        f"حداقل برداشت: {MIN_WITHDRAW} DOGS\n\n"
        "تعداد را وارد کنید."
    )



# =====================
# ADMIN PANEL
# =====================

async def admin_panel(query):

    if not owner(query.from_user.id):
        return


    await query.edit_message_text(
        "⚙️ پنل مالک\n\n"
        "🟢 روشن/خاموش ربات\n"
        "💬 گپ اجباری\n"
        "📢 چنل اجباری\n"
        "📊 آمار\n"
        "👑 انتقال مالکیت",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                InlineKeyboardButton(
                    "📊 آمار",
                    callback_data="stats"
                )
                ],
                [
                InlineKeyboardButton(
                    "👑 انتقال مالکیت",
                    callback_data="change_owner"
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



async def stats(query):

    if not owner(query.from_user.id):
        return


    await query.edit_message_text(
        "📊 آمار\n\n"
        f"👥 کاربران: {len(data['users'])}\n"
        f"🎮 بازی ها: {len(data['games'])}"
    )



# =====================
# MESSAGE STATES
# =====================


async def text_handler(update,context):

    user=update.effective_user

    create_user(user)

    text=update.message.text


    # انتقال ریپلای

    if text.startswith("انتقال"):

        await transfer(update)
        return



    state=context.user_data.get("state")


    if state=="withdraw":

        try:
            amount=int(text)
        except:
            await update.message.reply_text(
                "❌ عدد ارسال کنید"
            )
            return


        if balance(user.id)<amount:

            await update.message.reply_text(
                "❌ موجودی کافی نیست"
            )
            return


        remove_balance(
            user.id,
            amount
        )


        await update.message.reply_text(
            "✅ درخواست برداشت ارسال شد."
        )


        await context.bot.send_message(
            OWNER_ID,
            "💰 برداشت جدید\n\n"
            f"کاربر: {user.id}\n"
            f"مقدار: {amount} DOGS"
        )


        context.user_data.clear()
        return



    if state=="deposit":


        await update.message.reply_text(
            "✅ رسید ارسال شد.\nمنتظر تایید مالک باشید."
        )


        await context.bot.send_message(
            OWNER_ID,
            "💳 واریز جدید\n\n"
            f"کاربر: {user.id}\n"
            f"{text}"
        )


        context.user_data.clear()
        return



    # بازی

    if text.startswith("بازی"):

        try:

            amount=int(
                text.split()[1]
            )

        except:

            return


        await create_game(
            update,
            amount
        )
        return



    await update.message.reply_text(
        "از منو استفاده کنید."
    )



# =====================
# CALLBACK ALL
# =====================


async def callbacks(update,context):

    query=update.callback_query

    await query.answer()


    action=query.data


    if action=="profile":

        await profile(query)


    elif action=="ref":

        await ref(query,context)


    elif action=="deposit":

        await deposit_menu(
            query,
            context
        )


    elif action=="withdraw":

        await withdraw_menu(
            query,
            context
        )


    elif action=="game":

        await game_menu(query)


    elif action.startswith("join_"):

        await join_game(query)


    elif action.startswith("cancel_"):

        await cancel_game(query)


    elif action=="admin":

        await admin_panel(query)


    elif action=="stats":

        await stats(query)


    elif action=="home":

        await query.edit_message_text(
            "منوی اصلی",
            reply_markup=keyboard(
                query.from_user.id
            )
        )



# =====================
# RUN
# =====================


def main():

    app=Application.builder().token(
        BOT_TOKEN
    ).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            callbacks
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT,
            text_handler
        )
    )


    print("BOT STARTED")

    app.run_polling()



if __name__=="__main__":
    main()
