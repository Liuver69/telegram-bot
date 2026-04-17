python
import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ContextTypes
)

# 🔥 LOGS (para Railway)
logging.basicConfig(level=logging.INFO)

# 🔑 CONFIG
TOKEN = os.getenv("TOKEN")  # IMPORTANTE: viene de Railway
GROUP_ID = -3956381851  # ⚠️ CAMBIA ESTO
ADMIN_ID = 7813841188       # ⚠️ CAMBIA ESTO

DB_FILE = "db.json"

if not TOKEN:
    raise ValueError("❌ TOKEN no encontrado. Configura la variable en Railway")


# 📂 BASE DE DATOS
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "invites": {},
            "links": {},
            "config": {"required_invites": 3}
        }


def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)


db = load_db()


# 🔹 /start → generar link único
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)

        invite_link = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            creates_join_request=True,
            name=f"user_{user_id}"
        )

        db["links"][invite_link.invite_link] = user_id
        db["invites"].setdefault(user_id, 0)
        save_db(db)

        required = db["config"]["required_invites"]

        text = f"""
🔥 Debes invitar {required} personas para entrar.

Tu link único:
{invite_link.invite_link}

Invitados: {db["invites"][user_id]}/{required}
"""

        await update.message.reply_text(text)

    except Exception as e:
        logging.error(f"Error en /start: {e}")


# 🔹 Detectar solicitudes de entrada
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.chat_join_request.from_user
        invite = update.chat_join_request.invite_link

        link = invite.invite_link if invite else None
        user_id = str(user.id)

        # Sumar invitación
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
                    text=f"❌ Necesitas invitar {required} personas.\n"
                         f"Llevas: {invites}\n\n"
                         f"Usa /start para obtener tu link."
                )
            except:
                pass

    except Exception as e:
        logging.error(f"Error en join_request: {e}")


# 🔹 PANEL ADMIN
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("⚙️ Configurar invites", callback_data="config_invites")],
        [InlineKeyboardButton("📊 Estadísticas", callback_data="stats")],
        [InlineKeyboardButton("🗑 Resetear usuarios", callback_data="reset")],
    ]

    await update.message.reply_text(
        "🔧 Panel Admin",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 🔹 BOTONES
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data == "config_invites":
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data="set_1"),
                InlineKeyboardButton("3", callback_data="set_3"),
                InlineKeyboardButton("5", callback_data="set_5"),
                InlineKeyboardButton("10", callback_data="set_10"),
            ]
        ]

        await query.edit_message_text(
            "Selecciona cantidad de invitados:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("set_"):
        value = int(data.split("_")[1])
        db["config"]["required_invites"] = value
        save_db(db)

        await query.edit_message_text(f"✅ Ahora se requieren {value} invitados")

    elif data == "stats":
        total_users = len(db["invites"])
        total_invites = sum(db["invites"].values())
        required = db["config"]["required_invites"]

        await query.edit_message_text(
            f"📊 Usuarios: {total_users}\n"
            f"👥 Invitaciones: {total_invites}\n"
            f"🎯 Requeridas: {required}"
        )

    elif data == "reset":
        db["invites"] = {}
        db["links"] = {}
        save_db(db)

        await query.edit_message_text("🗑 Base de datos reiniciada")


# 🚀 MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot corriendo correctamente...")
    app.run_polling()


if __name__ == "__main__":
    main()
```
            
