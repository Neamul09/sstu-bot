import json
import os

_translations = {
    "en": {
        "welcome_back": "👋 Welcome back, *{name}*!\nUse the /menu command to navigate.",
        "welcome_start": "🎓 *Welcome to the SSTU Bot!*\n\nLet's get you registered so you can see your class schedules and deadlines.\n\nFirst, please type your *Full Name*:",
        "ask_id": "Nice to meet you, *{name}*!\n\nWhat is your *Student ID*? (e.g., BSSE1501)",
        "ask_dept": "Got it! Which department do you belong to?",
        "ask_sem": "🏢 *Department*: {dept}\n\nNow, select your current Semester:",
        "reg_complete": "✅ *Registration Successful!*\n\n👤 *Name*: {name} (ID: {student_id})\n🏢 *Class*: {dept} - Semester {sem}\n\nYou are officially signed in. Use the /menu command to open your dashboard.",
        "reg_cancelled": "❌ Registration cancelled. Send /start to begin again.",
        
        "menu_timetable": "📅 Timetable",
        "menu_deadlines": "🚨 Deadlines",
        "menu_notices": "📢 Notices",
        "menu_resources": "📚 Resources",
        "menu_profile": "⚙️ My Profile",
        "lang_toggle_btn": "🌍 Switch to Bangla (বাংলা)",
        "lang_switched": "✅ Language updated successfully!",
        
        "profile_title": "👤 *Your Profile*\n\nName: {name}\nStudent ID: {student_id}\nRole: {role}\nDepartment: {dept}\nSemester: {sem}",
        
        "notice_board_title": "📢 *Notice Board*\n_Class: {dept} Semester {sem}_\n\n",
        "notice_empty": "No notices here yet.",
        "notice_from": "📢 *New Notice* from {author} ({role})\n",
        "post_notice_prompt": "📝 *Post New Notice*\n\nPlease type the *Notice Content* or upload a File/Photo with a Caption:\n_(Tip: Keep it clear and concise)_",
        "action_cancelled": "❌ Action Cancelled.",
        
        "res_library_title": "📚 *Shared Resources Library*\n_Class: {dept} Semester {sem}_",
        "res_empty": "No resources have been shared yet! Let your CRs know they can share links and files here.",
        "res_count": "Showing {count} total resources:",
        "btn_add_res": "➕ Add Resource",
        
        # New translation strings for buttons
        "btn_add_notice": "➕ Post Notice",
        "btn_newer": "⬅️ Newer",
        "btn_older": "Older ➡️",
        
        "btn_delete": "🗑️ Delete",
        "btn_edit": "✏️ Edit",
        "btn_cancel_class": "🚫 Cancel Class",
        "btn_reschedule": "🕒 Reschedule",
        "btn_routine_img": "🖼️ Official Routine",
        "btn_upload_routine": "📤 Upload Routine",
        "confirm_delete": "⚠️ Are you sure you want to delete this?",
        "ask_routine_img": "Please upload the *Image* of the Weekly Routine:",
        "routine_updated": "✅ Routine Image updated successfully!",
        
        "btn_search": "🔍 Search",
        "search_prompt": "🔍 *Search Board*\n\nEnter a keyword to search for in your section's library or board:",
        "search_results": "🔍 *Search Results for '{query}'*:\n\n",
        "search_none": "❌ No results found matching your query.",
        
        # We can add more strings here easily as the app scales
    },
    "bn": {
        "welcome_back": "👋 স্বাগতম, *{name}*!\nমেনু ব্যবহার করতে /menu কমান্ড দিন।",
        "welcome_start": "🎓 *এসএসটিউ বটে স্বাগতম!*\n\nচলুন আপনার রেজিস্ট্রেশন সম্পন্ন করি যাতে আপনি ক্লাসের রুটিন ও নোটিশ দেখতে পারেন।\n\nপ্রথমে, আপনার *পূর্ণ নাম* লিখুন:",
        "ask_id": "আপনার সাথে পরিচিত হয়ে ভালো লাগলো, *{name}*!\n\nআপনার *স্টুডেন্ট আইডি* কত? (যেমন: BSSE1501)",
        "ask_dept": "ধন্যবাদ! আপনি কোন ডিপার্টমেন্টের ছাত্র/ছাত্রী?",
        "ask_sem": "🏢 *ডিপার্টমেন্ট*: {dept}\n\nএখন আপনার বর্তমান সেমিস্টার নির্বাচন করুন:",
        "reg_complete": "✅ *রেজিস্ট্রেশন সফল হয়েছে!*\n\n👤 *নাম*: {name} (আইডি: {student_id})\n🏢 *ক্লাস*: {dept} - সেমিস্টার {sem}\n\nআপনি আনুষ্ঠানিকভাবে লগইন করেছেন। মূল ড্যাশবোর্ড খুলতে /menu কমান্ড ব্যবহার করুন।",
        "reg_cancelled": "❌ রেজিস্ট্রেশন বাতিল করা হয়েছে। আবার শুরু করতে /start লিখুন।",
        
        "menu_timetable": "📅 ক্লাসের রুটিন",
        "menu_deadlines": "🚨 ডেডলাইনসমূহ",
        "menu_notices": "📢 নোটিশ বোর্ড",
        "menu_resources": "📚 ক্লাসের রিসোর্স",
        "menu_profile": "⚙️ আমার প্রোফাইল",
        "lang_toggle_btn": "🌍 Switch to English",
        "lang_switched": "✅ ভাষা সফলভাবে পরিবর্তন করা হয়েছে!",
        
        "profile_title": "👤 *আপনার প্রোফাইল*\n\nনাম: {name}\nআইডি: {student_id}\nরোল: {role}\nবিভাগ: {dept}\nসেমিস্টার: {sem}",
        
        "notice_board_title": "📢 *নোটিশ বোর্ড*\n_ক্লাস: {dept} সেমিস্টার {sem}_\n\n",
        "notice_empty": "এখানে কোনো নোটিশ নেই।",
        "notice_from": "📢 *নতুন নোটিশ* - প্রেরক: {author} ({role})\n",
        "post_notice_prompt": "📝 *নতুন নোটিশ পোস্ট করুন*\n\ দয়া করে নোটিশের বিষয়বস্তু লিখুন অথবা ক্যাপশনসহ একটি ছবি/ফাইল আপলোড করুন:",
        "action_cancelled": "❌ কার্যক্রম বাতিল করা হয়েছে।",
        
        "res_library_title": "📚 *সংগৃহীত রিসোর্স লাইব্রেরি*\n_ক্লাস: {dept} সেমিস্টার {sem}_",
        "res_empty": "এখনো কোনো রিসোর্স শেয়ার করা হয়নি! আপনার CR-কে ফাইল বা লিংক শেয়ার করতে বলুন।",
        "res_count": "মোট {count}টি রিসোর্স পাওয়া গেছে:",
        "btn_add_res": "➕ রিসোর্স যোগ করুন",
        
        "btn_add_notice": "➕ নোটিশ পোস্ট করুন",
        "btn_newer": "⬅️ নতুন",
        "btn_older": "পুরানো ➡️",
        
        "btn_delete": "🗑️ মুছে ফেলুন",
        "btn_edit": "✏️ পরিবর্তন করুন",
        "btn_cancel_class": "🚫 ক্লাস বাতিল",
        "btn_reschedule": "🕒 সময় পরিবর্তন",
        "btn_routine_img": "🖼️ অফিসিয়াল রুটিন",
        "btn_upload_routine": "📤 রুটিন আপলোড",
        "confirm_delete": "⚠️ আপনি কি নিশ্চিত যে এটি মুছে ফেলতে চান?",
        "ask_routine_img": "সাপ্তাহিক রুটিনের *ছবি* আপলোড করুন:",
        "routine_updated": "✅ রুটিন ছবি সফলভাবে আপডেট করা হয়েছে!",
        
        "btn_search": "🔍 খুঁজুন",
        "search_prompt": "🔍 *খুঁজুন*\n\nআপনার সেকশনের লাইব্রেরি বা বোর্ডে কিছু খুঁজতে একটি কীওয়ার্ড লিখুন:",
        "search_results": "🔍 *'{query}' এর জন্য ফলাফল*:\n\n",
        "search_none": "❌ আপনার কীওয়ার্ডের সাথে মেলা কোনো ফলাফল পাওয়া যায়নি।",
    }
}

def t(key: str, lang: str = "en", **kwargs) -> str:
    """Fetch localized string from dictionary based on user's lang preference"""
    if lang not in _translations:
        lang = "en"
    
    val = _translations[lang].get(key, _translations["en"].get(key, key))
    
    if kwargs:
        try:
            val = val.format(**kwargs)
        except KeyError:
            pass # In case formatting keys are missed
            
    return val
