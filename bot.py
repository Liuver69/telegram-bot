import json
import os
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("TOKEN")

DB_FILE = "db.json"


# ---------------- DATABASE ---------------- #

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "admin_id": None,
            "groups": {},
            "messages": {},
            "interval": 300
        }
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


db = load_db()


# ---------------- HELPERS ---------------- #

def is_admin(user_id):
    return db.get("admin_id") == user_id


# ---------------- COMMANDS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Bot activo")


async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db["admin_id"] = user_id
    save_db(db)

    await update.message.reply_text("✅ Admin configurado correctamente")


async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)

    db["groups"][chat_id] = True
    save_db(db)

    await update.message.reply_text("✅ Grupo agregado al sistema")


async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)
    text = update.message.text.replace("/setmessage", "").strip()

    db["messages"][chat_id] = text
    save_db(db)

    await update.message.reply_text("✅ Mensaje guardado para este grupo")


async def setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        seconds = int(context.args[0])
        db["interval"] = seconds
        save_db(db)

        await update.message.reply_text(f"✅ Intervalo actualizado: {seconds}s")
    except:
        await update.message.reply_text("❌ Usa /setinterval 300")


# ---------------- AUTO MESSAGES ---------------- #

async def broadcast(context: ContextTypes.DEFAULT_TYPE):
    for chat_id, enabled in db["groups"].items():
        if not enabled:
            continue

        message = db["messages"].get(chat_id, "Mensaje automático del bot 🔥")

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                protect_content=True  # 🔥 evita reenvío
            )
        except Exception as e:
            print("Error enviando a", chat_id, e)


# ---------------- NEW MEMBERS ---------------- #

async def on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if update.chat_member.new_chat_member.status == "member":
        await context.bot.send_message(
            chat.id,
            f"👋 Bienvenido {user.first_name}",
            protect_content=True
        )


# ---------------- MAIN ---------------- #

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setadmin", setadmin))
    app.add_handler(CommandHandler("addgroup", addgroup))
    app.add_handler(CommandHandler("setmessage", setmessage))
    app.add_handler(CommandHandler("setinterval", setinterval))

    # eventos
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_join))

    # scheduler mensajes
    job = app.job_queue
    job.run_repeating(broadcast, interval=db["interval"], first=10)

    print("🔥 BOT MULTI-GRUPO ACTIVO")
    app.run_polling()


if __name__ == "__main__":
    main()
