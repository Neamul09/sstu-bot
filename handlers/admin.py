from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from database import Database

async def teacher_add_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = Database.get_user(update.effective_user.id)
    if not user or user["role"] not in ["ADMIN", "TEACHER"]:
        await update.message.reply_text("Unauthorized.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: `/add_class <Dept>_<Sem>`\nExample: `/add_class CSE_1`")
        return

    class_id = context.args[0]
    Database.add_teacher_class(update.effective_user.id, class_id)
    await update.message.reply_text(f"✅ Class {class_id} linked to your account.")

teacher_class_handler = CommandHandler("add_class", teacher_add_class)
