from collections import defaultdict
from datetime import date
import calendar


def format_absences_text(absences: list, title: str = "Пропуски") -> str:
    if not absences:
        return f"📋 {title}: пропусков нет."

    by_disc = defaultdict(lambda: {"hours": 0, "entries": []})
    for row in absences:
        disc = row["discipline"]
        by_disc[disc]["hours"] += row["hours"]

        date_str = row["date"].strftime("%d.%m")

        # Добавляем информацию о паре если есть
        lesson_num  = row.get("lesson_num")
        lesson_time = row.get("lesson_time", "")
        if lesson_num:
            pair_str = f"{date_str} ({lesson_num}-я пара"
            if lesson_time:
                pair_str += f", {lesson_time}"
            pair_str += ")"
        else:
            pair_str = date_str

        by_disc[disc]["entries"].append(pair_str)

    lines = [f"📋 *{title}*\n"]
    total = 0
    for disc, data in sorted(by_disc.items()):
        hours     = data["hours"]
        dates_str = ", ".join(data["entries"])
        lines.append(f"• *{disc}*: {hours} ч.\n  _{dates_str}_")
        total += hours
    lines.append(f"\n*Итого:* {total} часов")
    return "\n".join(lines)


def format_student_summary(student, total_hours: int) -> str:
    name   = f"{student['last_name']} {student['first_name']}"
    linked = "✅ привязан к Telegram" if student.get("tg_id") else "❌ не привязан"
    return (
        f"👤 *{name}*\n"
        f"Статус: {linked}\n"
        f"Всего пропусков: *{total_hours} ч.*"
    )


def format_students_list(students: list) -> str:
    if not students:
        return "Список студентов пуст."
    lines = ["👥 *Список студентов:*\n"]
    for i, s in enumerate(students, 1):
        linked = "✅" if s.get("tg_id") else "⬜"
        lines.append(f"{i}. {linked} {s['last_name']} {s['first_name']}")
    return "\n".join(lines)


def semester_dates() -> tuple:
    today = date.today()
    if today.month >= 9:
        return date(today.year, 9, 1), date(today.year, 12, 31)
    else:
        return date(today.year, 1, 1), date(today.year, 6, 30)


def month_dates() -> tuple:
    today    = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)    if not students:
        return "Список студентов пуст."
    lines = ["👥 *Список студентов:*\n"]
    for i, s in enumerate(students, 1):
        linked = "✅" if s.get("tg_id") else "⬜"
        lines.append(f"{i}. {linked} {s['last_name']} {s['first_name']}")
    return "\n".join(lines)


def semester_dates() -> tuple:
    today = date.today()
    if today.month >= 9:
        return date(today.year, 9, 1), date(today.year, 12, 31)
    else:
        return date(today.year, 1, 1), date(today.year, 6, 30)


def month_dates() -> tuple:
    today = date.today()
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)
