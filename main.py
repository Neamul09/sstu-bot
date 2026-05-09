import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import Config
from handlers.onboarding import onboarding_handler, approval_handler
from handlers.timetable import timetable_view_handler, timetable_nav_handler, timetable_add_handler, routine_view_handler, routine_upload_handler, slot_delete_handler, notify_instant_handler, notify_sched_handler
from handlers.deadlines import deadline_view_handler, deadline_nav_handler, deadline_add_handler, deadline_delete_handler
from handlers.notices import notice_view_handler, notice_nav_handler, notice_post_handler, notice_delete_handler, notice_search_handler
from handlers.admin import teacher_class_handler
from handlers.menu import menu_handler, handle_menu_click, lang_toggle_handler, settings_view_handler, pref_toggle_handler, profile_back_handler
from handlers.poll import poll_handler, poll_view_handler, poll_delete_handler
from handlers.manage_class import manage_class_handler
from handlers.manage_users import students_list_handler
from handlers.results import results_nav_handler, results_back_handler, results_add_handler, result_file_handler
from handlers.resources import res_view_handler, res_nav_handler, res_click_handler, res_add_handler, res_delete_handler, res_search_handler
from utils.scheduler import start_scheduler
from database import Database

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for health checks
app = Flask(__name__)

@app.route("/")
def health_check():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def start_bot():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    # Start the Flask health check server in a background thread
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Health check server started in background.")

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).read_timeout(30).connect_timeout(30).build()

    # Callback Approval Handler (Must go early)
    application.add_handler(approval_handler)

    # Conversation Handlers (Must go before fallbacks)
    application.add_handler(onboarding_handler)
    application.add_handler(timetable_add_handler)
    application.add_handler(deadline_add_handler)
    application.add_handler(notice_post_handler)
    application.add_handler(res_add_handler)
    application.add_handler(res_search_handler)
    application.add_handler(notice_search_handler)
    application.add_handler(routine_upload_handler)
    application.add_handler(manage_class_handler)
    application.add_handler(notify_sched_handler)
    application.add_handler(results_add_handler)
    
    # Command Handlers
    application.add_handler(timetable_view_handler)
    application.add_handler(deadline_view_handler)
    application.add_handler(notice_view_handler)
    application.add_handler(res_view_handler)
    application.add_handler(teacher_class_handler)
    application.add_handler(menu_handler)
    application.add_handler(poll_handler)
    application.add_handler(poll_view_handler)
    
    # Callback Nav Handlers
    application.add_handler(timetable_nav_handler)
    application.add_handler(deadline_nav_handler)
    application.add_handler(notice_nav_handler)
    application.add_handler(res_nav_handler)
    application.add_handler(res_click_handler)
    application.add_handler(lang_toggle_handler)
    application.add_handler(settings_view_handler)
    application.add_handler(pref_toggle_handler)
    application.add_handler(profile_back_handler)
    
    # Management Callbacks
    application.add_handler(notice_delete_handler)
    application.add_handler(deadline_delete_handler)
    application.add_handler(res_delete_handler)
    application.add_handler(slot_delete_handler)
    application.add_handler(poll_delete_handler)
    application.add_handler(routine_view_handler)
    application.add_handler(notify_instant_handler)
    application.add_handler(results_nav_handler)
    application.add_handler(results_back_handler)
    application.add_handler(result_file_handler)
    application.add_handler(students_list_handler)

    # Persistent Menu clicks
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_click))

    application.add_error_handler(error_handler)

    # Start Scheduler
    start_scheduler(application)

    # Start the Bot
    logger.info("Bot started... (Approval System Live)")
    application.run_polling()

if __name__ == "__main__":
    try:
        start_bot()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
