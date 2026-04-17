import json
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = 7813841188  # CAMBIA ESTO

DB_FILE = "db.json"

if not TOKEN:
    raise ValueError("TOKEN no encontrado")


# ================= DB =================
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "groups": {},
            "invites": {},
            "links": {},
            "config": {
                "required_invites": 3
            }
        }


def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)


db = load_db()

SELECTED_GROUP = {}
ADMIN_STATE = {}


# ================= HELPERS =================
def get_group(chat_id):
    chat_id = str(chat_id)

    if chat_id not in db["groups"]:
        db["groups"][chat_id] = {
            "auto_msg": "🔥 Mensaje por defecto",
            "interval": 10,
            "media": None,
            "buttons": []
        }
        save_db(db)

    return db["groups"][chat_id]


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    group = get_group(chat_id)

    invite_link = await context.bot.create_chat_invite_link(
        chat_id=chat_id,
        creates_join_request=True,
        name=f"user_{user_id}"
    )

    db["links"][invite_link.invite_link] = user_id
    db["invites"].setdefault(user_id, 0)
    save_db(db)

    buttons = [
        [InlineKeyboardButton(b["text"], url=b["url"])]
        for b in group["buttons"]
    ]

    text = f"""
<b>Invita {db["config"]["required_invites"]} personas</b>

<a href="{invite_link.invite_link}">🔗 Tu link</a>

<tg-spoiler>Comparte para desbloquear acceso</tg-spoiler>
"""

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        protect_content=True
    )


# ================= JOIN REQUEST =================
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    invite = update.chat_join_request.invite_link

    link = invite.invite_link if invite else None
    user_id = str(user.id)

    if link and link in db["links"]:
        inviter_id = db["links"][link]

        if inviter_id != user_id:
            db["invites"][inviter_id] = db["invites"].get(inviter_id, 0) + 1
            save_db(db)

    invites = db["invites"].get(user_id, 0)
    required = db["config"]["required_invites"]

    if invites >= required:
        await update.chat_join_request.approve()
    else:
        await update.chat_join_request.decline()

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Necesitas {required} invites. Llevas {invites}",
                protect_content=True
            )
        except:
            pass


# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Grupos", callback_data="groups")],
        [InlineKeyboardButton("⚙️ Config global", callback_data="config")],
    ]

    await update.message.reply_text(
        "🔧 PANEL ADMIN",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CALLBACKS =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    # LISTAR GRUPOS
    if data == "groups":
        keyboard = []

        for g in db["groups"]:
            keyboard.append([
                InlineKeyboardButton(f"Grupo {g}", callback_data=f"select_{g}")
            ])

        await query.edit_message_text(
            "Selecciona grupo:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # SELECCIONAR GRUPO
    elif data.startswith("select_"):
        group_id = data.replace("select_", "")
        SELECTED_GROUP[ADMIN_ID] = group_id

        keyboard = [
            [InlineKeyboardButton("✏️ Mensaje", callback_data="edit_msg")],
            [InlineKeyboardButton("⏱ Intervalo", callback_data="edit_time")],
            [InlineKeyboardButton("🔗 Botones", callback_data="edit_btn")],
        ]

        await query.edit_message_text(
            f"Grupo: {group_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # EDITAR MENSAJE
    elif data == "edit_msg":
        ADMIN_STATE[ADMIN_ID] = "msg"
        await query.edit_message_text("Envía nuevo mensaje (HTML permitido)")

    # EDITAR TIEMPO
    elif data == "edit_time":
        ADMIN_STATE[ADMIN_ID] = "time"
        await query.edit_message_text("Envía intervalo en minutos")

    # EDITAR BOTONES
    elif data == "edit_btn":
        ADMIN_STATE[ADMIN_ID] = "btn"
        await query.edit_message_text("Envía: Texto | URL")


# ================= ADMIN INPUT =================
async def admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    state = ADMIN_STATE.get(ADMIN_ID)
    group_id = SELECTED_GROUP.get(ADMIN_ID)

    if not group_id:
        return

    group = get_group(group_id)

    # MENSAJE
    if state == "msg":
        group["auto_msg"] = update.message.text
        save_db(db)
        await update.message.reply_text("Mensaje actualizado")

    # TIEMPO
    elif state == "time":
        group["interval"] = int(update.message.text)
        save_db(db)
        await update.message.reply_text("Intervalo actualizado")

    # BOTONES
    elif state == "btn":
        try:
            text, url = update.message.text.split("|")
            group["buttons"].append({
                "text": text.strip(),
                "url": url.strip()
            })
            save_db(db)
            await update.message.reply_text("Botón agregado")
        except:
            await update.message.reply_text("Formato incorrecto")

    ADMIN_STATE[ADMIN_ID] = None


# ================= AUTO MESSAGES =================
async def auto_messages(app):
    while True:
        for group_id, cfg in db["groups"].items():
            try:
                buttons = [
                    [InlineKeyboardButton(b["text"], url=b["url"])]
                    for b in cfg["buttons"]
                ]

                await app.bot.send_message(
                    chat_id=group_id,
                    text=cfg["auto_msg"],
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
                    protect_content=True
                )

            except Exception as e:
                logging.error(e)

        await asyncio.sleep(60)


# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_messages))

    asyncio.create_task(auto_messages(app))

    print("🔥 BOT MULTI-GRUPO ACTIVO")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
