from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 Студенты"),   KeyboardButton(text="📋 Пропуски")],
        [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="📊 Отчёты")],
        [KeyboardButton(text="⚙️ Управление")],
    ], resize_keyboard=True)


def main_menu_starost() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 Студенты"),   KeyboardButton(text="📋 Пропуски")],
        [KeyboardButton(text="📅 Расписание"), KeyboardButton(text="📊 Отчёты")],
    ], resize_keyboard=True)


def main_menu_student() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мои пропуски")],
        [KeyboardButton(text="📅 Расписание")],
    ], resize_keyboard=True)


def students_list_kb(students: list) -> InlineKeyboardMarkup:
    buttons = []
    for s in students:
        name = f"{s['last_name']} {s['first_name']}"
        linked = "✅ " if s.get("tg_id") else ""
        buttons.append([InlineKeyboardButton(
            text=f"{linked}{name}",
            callback_data=f"student:{s['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def student_actions_kb(student_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Пропуски студента", callback_data=f"st_abs:{student_id}")],
        [InlineKeyboardButton(text="📄 Отчёт Word",        callback_data=f"st_docx:{student_id}")],
        [InlineKeyboardButton(text="🖼 Справки",           callback_data=f"st_photos:{student_id}")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить студента", callback_data=f"st_del:{student_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="students_list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def disciplines_kb(disciplines: list, action: str = "abs_disc") -> InlineKeyboardMarkup:
    buttons = []
    for d in disciplines:
        buttons.append([InlineKeyboardButton(
            text=d["name"],
            callback_data=f"{action}:{d['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новая дисциплина", callback_data=f"{action}:new")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def report_period_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Этот месяц",   callback_data="report:month")],
        [InlineKeyboardButton(text="📅 Этот семестр", callback_data="report:semester")],
        [InlineKeyboardButton(text="📅 Всё время",    callback_data="report:all")],
        [InlineKeyboardButton(text="🔍 Свой период",  callback_data="report:custom")],
    ])


def confirm_kb(yes_data: str, no_data: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да",   callback_data=yes_data),
            InlineKeyboardButton(text="❌ Нет",  callback_data=no_data),
        ]
    ])
