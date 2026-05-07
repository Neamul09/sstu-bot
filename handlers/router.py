import re
from database import Database
from handlers.timetable import view_timetable
from handlers.deadlines import view_deadlines
from handlers.notices import view_notices
from handlers.resources import view_resources
from handlers.poll import poll_handler # This might need careful import or separate view function

KEYWORDS = {
    'timetable': [
        'routine', 'timetable', 'schedule', 'class', 'today', 'tomorrow', 
        'রুটিন', 'ক্লাস', 'পিরিয়ড', 'সময়সূচী',
        'kobe class', 'kkhon class', 'routine ki', 'routine kbe', 'ajk class'
    ],
    'deadlines': [
        'assignment', 'deadline', 'exam', 'test', 'due', 'homework', 'task',
        'অ্যাসাইনমেন্ট', 'পরীক্ষা', 'টেস্ট', 'হোমওয়ার্ক',
        'porikkha', 'homework ki', 'due date', 'deadline kobe'
    ],
    'notices': [
        'notice', 'announcement', 'update', 'news', 'board', 'notification',
        'নোটিশ', 'ঘোষণা', 'খবর',
        'ki notice', 'notish', 'notis'
    ],
    'resources': [
        'notes', 'pdf', 'file', 'slide', 'material', 'book', 'resource', 'lecture',
        'নোট', 'বই', 'স্লাইড', 'লেকচার',
        'slide kuthay', 'lekha', 'boio', 'material ache'
    ]
}

async def heuristic_router(update, context):
    text = update.message.text.lower().strip()
    
    # Check Timetable
    if any(word in text for word in KEYWORDS['timetable']):
        return await view_timetable(update, context)
    
    # Check Deadlines
    if any(word in text for word in KEYWORDS['deadlines']):
        return await view_deadlines(update, context)
        
    # Check Notices
    if any(word in text for word in KEYWORDS['notices']):
        return await view_notices(update, context)
        
    # Check Resources
    if any(word in text for word in KEYWORDS['resources']):
        return await view_resources(update, context)
    
    return False
