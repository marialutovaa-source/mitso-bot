"""
Расписание берётся из пересланных сообщений @mitsoScheldueBot.
Формат:
🥀 среда, 22 апреля
  🍤 08:00 - 09:25 | Лекция | Ауд. 61 | Алгоритмизация и программирование | Соловей С. С.
"""
import re
from datetime import datetime
 
_schedule_cache: list[dict] = []
_schedule_text_cache: str = ""
 
 
def parse_schedule_message(text: str) -> list[dict]:
    lessons = []
    current_date = None
    for line in text.splitlines():
        line = line.strip()
        date_match = re.match(r'[🥀💀🌸]+\s+(\w+),\s+(\d+)\s+(\w+)', line)
        if date_match:
            day_name = date_match.group(1)
            day_num  = date_match.group(2)
            month    = date_match.group(3)
            current_date = f"{day_name}, {day_num} {month}"
            continue
        lesson_match = re.match(r'[🍤🌟⭐]+\s+(\d+:\d+)\s*-\s*(\d+:\d+)\s*\|(.+)', line)
        if lesson_match and current_date:
            time_start = lesson_match.group(1)
            time_end   = lesson_match.group(2)
            rest       = lesson_match.group(3)
            parts = [p.strip() for p in rest.split('|')]
            lesson_type = parts[0] if len(parts) > 0 else ""
            room        = parts[1] if len(parts) > 1 else ""
            subject     = parts[2] if len(parts) > 2 else parts[0]
            teacher     = parts[3] if len(parts) > 3 else ""
            if len(parts) == 1:
                subject     = parts[0]
                lesson_type = ""
                room        = ""
                teacher     = ""
            lessons.append({
                "date":    current_date,
                "time":    f"{time_start} - {time_end}",
                "type":    lesson_type,
                "room":    room,
                "subject": subject,
                "teacher": teacher,
            })
    return lessons
 
 
def save_schedule(text: str):
    global _schedule_cache, _schedule_text_cache
    _schedule_cache      = parse_schedule_message(text)
    _schedule_text_cache = text
 
 
def get_cached_schedule() -> list[dict]:
    return _schedule_cache
 
 
def get_cached_text() -> str:
    return _schedule_text_cache
 
 
def _today_name() -> str:
    day_names = {
        0: "понедельник", 1: "вторник", 2: "среда",
        3: "четверг",     4: "пятница", 5: "суббота", 6: "воскресенье"
    }
    return day_names[datetime.now().weekday()]
 
 
def get_today_subjects() -> list[str]:
    """Возвращает список уникальных названий предметов сегодняшнего дня."""
    today_name = _today_name()
    subjects = []
    for item in _schedule_cache:
        if today_name in item.get("date", "").lower():
            name = item.get("subject", "").strip()
            if name and name not in subjects:
                subjects.append(name)
    return subjects
 
 
def get_today_lessons(subject_name: str = None) -> list[dict]:
    """
    Возвращает пары сегодняшнего дня.
    Если передан subject_name — фильтрует только по этому предмету.
    Каждый элемент: {"time": "08:00 - 09:25", "type": "Лекция", "room": "61", ...}
    """
    today_name = _today_name()
    lessons = []
    for item in _schedule_cache:
        if today_name not in item.get("date", "").lower():
            continue
        if subject_name and item.get("subject", "").lower() != subject_name.lower():
            continue
        lessons.append(item)
    return lessons
 
 
def get_all_subjects() -> list[str]:
    subjects = []
    for item in _schedule_cache:
        name = item.get("subject", "").strip()
        if name and name not in subjects:
            subjects.append(name)
    return subjects
 
 
def format_schedule(lessons: list[dict]) -> str:
    if not lessons:
        return (
            "Расписание не загружено. "
            "Перешлите сообщение от @mitsoScheldueBot старосте командой /setschedule"
        )
    lines = []
    current_date = None
    for item in lessons:
        if item["date"] != current_date:
            current_date = item["date"]
            lines.append(f"\n🗓 *{current_date}*")
        room    = f" | {item['room']}"    if item["room"]    else ""
        teacher = f" | {item['teacher']}" if item["teacher"] else ""
        lines.append(
            f"  `{item['time']}` {item['type']}{room} — *{item['subject']}*{teacher}"
        )
    return "\n".join(lines).strip()
                 subject     = parts[0]
                lesson_type = ""
                room        = ""
                teacher     = ""
            lessons.append({
                "date":    current_date,
                "time":    f"{time_start} - {time_end}",
                "type":    lesson_type,
                "room":    room,
                "subject": subject,
                "teacher": teacher,
            })
    return lessons


def save_schedule(text: str):
    global _schedule_cache, _schedule_text_cache
    _schedule_cache      = parse_schedule_message(text)
    _schedule_text_cache = text


def get_cached_schedule() -> list[dict]:
    return _schedule_cache


def get_cached_text() -> str:
    return _schedule_text_cache


def _today_name() -> str:
    day_names = {
        0: "понедельник", 1: "вторник", 2: "среда",
        3: "четверг",     4: "пятница", 5: "суббота", 6: "воскресенье"
    }
    return day_names[datetime.now().weekday()]


async def get_today_subjects() -> list[str]:
    """Возвращает список уникальных названий предметов сегодняшнего дня."""
    today_name = _today_name()
    subjects = []
    for item in _schedule_cache:
        if today_name in item.get("date", "").lower():
            name = item.get("subject", "").strip()
            if name and name not in subjects:
                subjects.append(name)
    return subjects


async def get_today_lessons(subject_name: str = None) -> list[dict]:
    """
    Возвращает пары сегодняшнего дня.
    Если передан subject_name — фильтрует только по этому предмету.
    Каждый элемент: {"time": "08:00 - 09:25", "type": "Лекция", "room": "61", ...}
    """
    today_name = _today_name()
    lessons = []
    for item in _schedule_cache:
        if today_name not in item.get("date", "").lower():
            continue
        if subject_name and item.get("subject", "").lower() != subject_name.lower():
            continue
        lessons.append(item)
    return lessons


def get_all_subjects() -> list[str]:
    subjects = []
    for item in _schedule_cache:
        name = item.get("subject", "").strip()
        if name and name not in subjects:
            subjects.append(name)
    return subjects


def format_schedule(lessons: list[dict]) -> str:
    if not lessons:
        return (
            "Расписание не загружено. "
            "Перешлите сообщение от @mitsoScheldueBot старосте командой /setschedule"
        )
    lines = []
    current_date = None
    for item in lessons:
        if item["date"] != current_date:
            current_date = item["date"]
            lines.append(f"\n🗓 *{current_date}*")
        room    = f" | {item['room']}"    if item["room"]    else ""
        teacher = f" | {item['teacher']}" if item["teacher"] else ""
        lines.append(
            f"  `{item['time']}` {item['type']}{room} — *{item['subject']}*{teacher}"
        )
    return "\n".join(lines).strip()
