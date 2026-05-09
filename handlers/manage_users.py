from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import Database, supabase
from config import Config
from utils.helpers import build_menu

async def view_students_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = Database.get_user(query.from_user.id)
    if not user or user["role"] not in [Config.ROLE_CR, Config.ROLE_ADMIN]:
        await query.edit_message_text("❌ Access denied.")
        return

    # If Admin, show Batch Selection
    if user["role"] == Config.ROLE_ADMIN:
        data = query.data.split("_")
        if query.data == "view_students_list":
            # Show Dept selection
            buttons = [InlineKeyboardButton(dept, callback_data=f"lstdept_{i}") for i, dept in enumerate(Config.DEPARTMENTS)]
            await query.edit_message_text(
                "👑 *Admin Panel*: Select Department:",
                reply_markup=build_menu(buttons, n_cols=1),
                parse_mode="Markdown"
            )
            return
        elif data[0] == "lstdept":
            dept_idx = int(data[1])
            dept = Config.DEPARTMENTS[dept_idx]
            context.user_data["admin_lst_dept"] = dept
            # Show Sem selection
            buttons = [InlineKeyboardButton(f"Sem {sem}", callback_data=f"lstsem_{sem}") for sem in Config.SEMESTERS]
            await query.edit_message_text(
                f"🏢 Dept: *{dept}*\nSelect Semester:",
                reply_markup=build_menu(buttons, n_cols=2),
                parse_mode="Markdown"
            )
            return
        elif data[0] == "lstsem":
            dept = context.user_data.get("admin_lst_dept")
            sem = data[1]
            await display_list(update, context, dept, sem)
            return

    # If CR, just show their own batch
    else:
        await display_list(update, context, user["department"], user["semester"])

async def display_list(update: Update, context: ContextTypes.DEFAULT_TYPE, dept: str, sem: str):
    query = update.callback_query
    
    # Fetch approved students
    res = supabase.table("users").select("*") \
        .eq("department", dept) \
        .eq("semester", int(sem)) \
        .eq("is_approved", True) \
        .order("student_id") \
        .execute()
    
    students = res.data
    
    text = f"👥 *Student Directory*\n🏢 Batch: {dept} - Sem {sem}\n"
    text += f"📊 Total: {len(students)} registered\n\n"
    
    if not students:
        text += "_No students registered yet._"
    else:
        for i, s in enumerate(students, 1):
            role_icon = "⭐" if s["role"] == Config.ROLE_CR else "👤"
            text += f"{i}. {role_icon} *{s['full_name']}*\n   └ ID: `{s['student_id']}`\n"
            if len(text) > 3500: # Simple pagination guard
                text += "\n...(List too long to display all)"
                break

    kb = [[InlineKeyboardButton("⬅️ Back", callback_data="view_students_list")]] if Database.get_user(query.from_user.id)["role"] == Config.ROLE_ADMIN else []
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode="Markdown")

students_list_handler = CallbackQueryHandler(view_students_list, pattern="^(view_students_list|lstdept_|lstsem_)")
