import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ContextTypes
)

# 🔑 CONFIG
TOKEN = "AQUI_TU_TOKEN"
GROUP_ID = -1001234567890  # ID de tu grupo
ADMIN_ID = 123456789       # TU ID

DB_FILE = "db.json"


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


# 🔹 Detectar solicitudes de entrada
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    link = update.chat_join_request.invite_link.invite_link

    user_id = str(user.id)

    # Sumar invitación al dueño del link
    if link in db["links"]:
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

        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Necesitas invitar {required} personas.\n"
                 f"Llevas: {invites}\n\n"
                 f"Usa /start para obtener tu link."
        )


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


# 🔹 BOTONES DEL PANEL
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    # CONFIG INVITES
    if data == "config_invites":
        keyboard = [
            [InlineKeyboardButton("1", callback_data="set_1"),
             InlineKeyboardButton("3", callback_data="set_3"),
             InlineKeyboardButton("5", callback_data="set_5"),
             InlineKeyboardButton("10", callback_data="set_10")]
        ]

        await query.edit_message_text(
            "Selecciona cantidad de invitados:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("set_"):
        value = int(data.split("_")[1])
        db["config"]["required_invites"] = value
        save_db(db)

        await query.edit_message_text(
            f"✅ Ahora se requieren {value} invitados"
        )

    # ESTADÍSTICAS
    elif data == "stats":
        total_users = len(db["invites"])
        total_invites = sum(db["invites"].values())
        required = db["config"]["required_invites"]

        await query.edit_message_text(
            f"📊 Usuarios registrados: {total_users}\n"
            f"👥 Invitaciones totales: {total_invites}\n"
            f"🎯 Requeridas: {required}"
        )

    # RESET
    elif data == "reset":
        db["invites"] = {}
        db["links"] = {}
        save_db(db)

        await query.edit_message_text("🗑 Base de datos reiniciada")


# 🚀 MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(ChatJoinRequestHandler(handle_join_request))
app.add_handler(CallbackQueryHandler(button_handler))

print("🤖 Bot corriendo...")
app.run_polling()