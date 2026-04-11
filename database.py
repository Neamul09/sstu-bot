from supabase import create_client, Client
from config import Config

# Supabase Client setup
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

class Database:
    supabase = supabase

    @staticmethod
    def get_user(user_id: int):
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None

    @staticmethod
    def create_user(user_data: dict):
        return supabase.table("users").insert(user_data).execute()

    @staticmethod
    def update_user(user_id: int, user_data: dict):
        return supabase.table("users").update(user_data).eq("id", user_id).execute()

    @staticmethod
    def get_timetable(class_id: str, day_of_week: int):
        return supabase.table("timetable").select("*").eq("class_id", class_id).eq("day_of_week", day_of_week).order("start_time").execute().data

    @staticmethod
    def add_timetable_slot(slot_data: dict):
        return supabase.table("timetable").insert(slot_data).execute()

    @staticmethod
    def get_deadlines(class_id: str):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return supabase.table("deadlines").select("*").eq("class_id", class_id).gt("due_datetime", now).order("due_datetime").execute().data

    @staticmethod
    def add_deadline(deadline_data: dict):
        return supabase.table("deadlines").insert(deadline_data).execute()

    @staticmethod
    def get_notices(class_id: str, limit: int = 5):
        return supabase.table("notices").select("*").eq("class_id", class_id).order("created_at", desc=True).limit(limit).execute().data

    @staticmethod
    def add_notice(notice_data: dict):
        return supabase.table("notices").insert(notice_data).execute()

    @staticmethod
    def get_teacher_classes(teacher_id: int):
        return supabase.table("teacher_classes").select("class_id").eq("teacher_id", teacher_id).execute().data

    @staticmethod
    def add_teacher_class(teacher_id: int, class_id: str):
        return supabase.table("teacher_classes").insert({"teacher_id": teacher_id, "class_id": class_id}).execute()

    @staticmethod
    def cancel_class(slot_id: str, cancel_date: str, reason: str = None):
        return supabase.table("cancelled_classes").insert({"slot_id": slot_id, "cancel_date": cancel_date, "reason": reason}).execute()

    @staticmethod
    def is_class_cancelled(slot_id: str, cancel_date: str):
        res = supabase.table("cancelled_classes").select("*").eq("slot_id", slot_id).eq("cancel_date", cancel_date).execute()
        return len(res.data) > 0

    @staticmethod
    def get_resources(class_id: str, limit: int = 100):
        # returns list of resources ordered by created_at desc
        res = supabase.table("resources").select("*").eq("class_id", class_id).order("created_at", desc=True).limit(limit).execute()
        return res.data

    @staticmethod
    def add_resource(resource_data: dict):
        return supabase.table("resources").insert(resource_data).execute()

    @staticmethod
    def delete_notice(notice_id: str):
        return supabase.table("notices").delete().eq("id", notice_id).execute()

    @staticmethod
    def delete_deadline(deadline_id: str):
        return supabase.table("deadlines").delete().eq("id", deadline_id).execute()

    @staticmethod
    def delete_resource(resource_id: str):
        return supabase.table("resources").delete().eq("id", resource_id).execute()

    @staticmethod
    def delete_timetable_slot(slot_id: str):
        return supabase.table("timetable").delete().eq("id", slot_id).execute()

    @staticmethod
    def add_class_override(override_data: dict):
        return supabase.table("class_overrides").insert(override_data).execute()

    @staticmethod
    def get_class_overrides(slot_id: str, date: str):
        return supabase.table("class_overrides").select("*").eq("slot_id", slot_id).eq("override_date", date).execute().data

    @staticmethod
    def set_class_config(class_id: str, config_data: dict):
        # upsert logic for class configs
        return supabase.table("class_configs").upsert({"class_id": class_id, **config_data}).execute()

    @staticmethod
    def get_class_config(class_id: str):
        res = supabase.table("class_configs").select("*").eq("class_id", class_id).execute()
        return res.data[0] if res.data else None

    # --- Polls ---
    @staticmethod
    def add_poll(poll_data: dict):
        return supabase.table("polls").insert(poll_data).execute()

    @staticmethod
    def get_polls(class_id: str, limit: int = 5):
        return supabase.table("polls").select("*").eq("class_id", class_id).eq("is_active", True).order("created_at", desc=True).limit(limit).execute().data

    @staticmethod
    def delete_poll(poll_id: str):
        return supabase.table("polls").delete().eq("id", poll_id).execute()

    # --- Search ---
    @staticmethod
    def search_notices(class_id: str, query: str):
        return supabase.table("notices").select("*").eq("class_id", class_id).ilike("content", f"%{query}%").order("created_at", desc=True).execute().data

    @staticmethod
    def search_resources(class_id: str, query: str):
        return supabase.table("resources").select("*").eq("class_id", class_id).or_(f"title.ilike.%{query}%,description.ilike.%{query}%").order("created_at", desc=True).execute().data
