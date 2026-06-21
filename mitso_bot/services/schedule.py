"""
Парсер расписания с apps.mitso.by

КАК НАЙТИ ПРАВИЛЬНЫЕ ПАРАМЕТРЫ:
1. Открой https://apps.mitso.by/frontend/web/schedule/group-schedule в Chrome
2. Открой DevTools (F12) → вкладка Network
3. Выбери свою группу, курс, тип обучения — нажми «Показать»
4. В Network найди запрос к group-schedule (обычно XHR/Fetch)
5. Скопируй Form Data или Query String параметры
6. Вставь их в GROUP_PARAMS ниже

Типичные параметры МИТСО (уточни по DevTools):
  GroupScheduleSearch[educationType] = 1   (1=дневное, 2=заочное)
  GroupScheduleSearch[course]        = 3   (номер курса)
  GroupScheduleSearch[group]         = 123 (id группы из dropdown)
"""

import aiohttp
from bs4 import BeautifulSoup
from datetime import date
from config import SCHEDULE_URL

GROUP_PARAMS = {
    "GroupScheduleSearch[educationType]": "1",
    "GroupScheduleSearch[course]": "1",
    "GroupScheduleSearch[group]": "",
}


async def fetch_schedule(week_offset: int = 0) -> list[dict]:
    """
    Возвращает список пар на неделю:
    [{"date": "2024-09-02", "time": "08:00", "subject": "Математика", "type": "лек", "room": "305"}, ...]
    """
    params = dict(GROUP_PARAMS)
    if week_offset:
        params["week"] = str(week_offset)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": SCHEDULE_URL,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(SCHEDULE_URL, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()

    return _parse_schedule_html(html)


def _parse_schedule_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    lessons = []

    for row in soup.select("table.table tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        try:
            lessons.append({
                "date":    cells[0].get_text(strip=True),
                "time":    cells[1].get_text(strip=True),
                "subject": cells[2].get_text(strip=True),
                "type":    cells[3].get_text(strip=True) if len(cells) > 3 else "",
                "room":    cells[4].get_text(strip=True) if len(cells) > 4 else "",
            })
        except Exception:
            continue

    return lessons


async def get_today_subjects() -> list[str]:
    schedule = await fetch_schedule()
    today_str = date.today().strftime("%d.%m.%Y")
    subjects = []
    for item in schedule:
        if today_str in item.get("date", ""):
            name = item.get("subject", "").strip()
            if name and name not in subjects:
                subjects.append(name)
    return subjects


async def get_week_subjects() -> list[str]:
    schedule = await fetch_schedule()
    subjects = []
    for item in schedule:
        name = item.get("subject", "").strip()
        if name and name not in subjects:
            subjects.append(name)
    return subjects


def format_schedule(lessons: list[dict]) -> str:
    if not lessons:
        return "Расписание не найдено или пусто."
    lines = []
    current_date = None
    for item in lessons:
        if item["date"] != current_date:
            current_date = item["date"]
            lines.append(f"\n📅 {current_date}")
        lines.append(f"  {item['time']} | {item['subject']} ({item['type']}) — ауд. {item['room']}")
    return "\n".join(lines).strip()
