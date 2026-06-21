from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date
 
from db.queries import (get_user, add_student, get_all_students,
                        get_or_create_discipline, get_all_disciplines,
                        add_absence, get_absences, delete_absence)
from utils.keyboards import disciplines_kb, students_list_kb
from utils.formatters import format_absences_text
from services.schedule import get_today_subjects, get_today_lessons
 
router = Router()
 
 
def is_starost(user) -> bool:
    return user and user["role"] in ("starost", "admin", "superadmin")
 
 
class AddStudentState(StatesGroup):
    waiting_name = State()
 
 
class AddAbsenceState(StatesGroup):
    select_student    = State()
    select_discipline = State()
    select_lesson     = State()   # новый шаг — выбор пары
    enter_date        = State()
    enter_hours       = State()
    enter_reason      = State()
 
 
@router.message(Command("addstudent"))
async def cmd_addstudent(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not is_starost(user):
        return
    await state.set_state(AddStudentState.waiting_name)
    await msg.answer(
        "Введите *фамилию и имя* студента через пробел:\n"
        "Например: `Иванов Иван`\n\n"
        "Можно отправить несколько строк — каждая строка = один студент.",
        parse_mode="Markdown"
    )
 
 
@router.message(AddStudentState.waiting_name)
async def process_add_student(msg: Message, state: FSMContext):
    await state.clear()
    lines = [l.strip() for l in msg.text.strip().splitlines() if l.strip()]
    added = []
    errors = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            errors.append(f"❌ «{line}» — нужны фамилия и имя")
            continue
        last_name  = parts[0]
        first_name = " ".join(parts[1:])
        sid = await add_student(last_name, first_name)
        if sid:
            added.append(f"✅ {last_name} {first_name}")
        else:
            errors.append(f"⚠️ {last_name} {first_name} — уже существует")
 
    result = "\n".join(added + errors) or "Ничего не добавлено."
    await msg.answer(f"Результат:\n{result}")
 
 
@router.message(F.text == "📋 Пропуски")
async def absences_menu(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not is_starost(user):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Отметить пропуск",       callback_data="abs:add")],
        [InlineKeyboardButton(text="📋 Пропуски по студенту",   callback_data="abs:by_student")],
        [InlineKeyboardButton(text="📋 Пропуски по дисциплине", callback_data="abs:by_disc")],
    ])
    await msg.answer("Управление пропусками:", reply_markup=kb)
 
 
# ── ШАГ 1: выбор студента ────────────────────────────────────────────────────
 
@router.callback_query(F.data == "abs:add")
async def cb_add_absence_start(cb: CallbackQuery, state: FSMContext):
    user = await get_user(cb.from_user.id)
    if not is_starost(user):
        return
    students = await get_all_students()
    if not students:
        await cb.answer("Список студентов пуст. Сначала добавьте студентов.", show_alert=True)
        return
    await state.set_state(AddAbsenceState.select_student)
    await cb.message.edit_text("Выберите студента:", reply_markup=students_list_kb(students))
 
 
# ── ШАГ 2: выбор дисциплины ──────────────────────────────────────────────────
 
@router.callback_query(AddAbsenceState.select_student, F.data.startswith("student:"))
async def cb_abs_select_student(cb: CallbackQuery, state: FSMContext):
    student_id = int(cb.data.split(":")[1])
    await state.update_data(student_id=student_id)
    await state.set_state(AddAbsenceState.select_discipline)
 
    disciplines    = await get_all_disciplines()
    today_subjects = get_today_subjects()
 
    kb_rows = []
 
    # Пары из расписания сегодня — приоритет вверху
    if today_subjects:
        for subj in today_subjects:
            already = any(d["name"].lower() == subj.lower() for d in disciplines)
            label = f"📚 {subj}" + (" (сегодня)" if not already else "")
            kb_rows.append([InlineKeyboardButton(
                text=label,
                callback_data=f"abs_disc:today:{subj}"
            )])
 
    # Сохранённые дисциплины (которых нет в сегодняшнем расписании)
    for d in disciplines:
        if not any(d["name"].lower() == s.lower() for s in today_subjects):
            kb_rows.append([InlineKeyboardButton(
                text=d["name"],
                callback_data=f"abs_disc:id:{d['id']}"
            )])
 
    kb_rows.append([InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="abs_disc:new")])
    await cb.message.edit_text("Выберите дисциплину:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
 
 
@router.callback_query(AddAbsenceState.select_discipline, F.data.startswith("abs_disc:"))
async def cb_abs_select_disc(cb: CallbackQuery, state: FSMContext):
    parts  = cb.data.split(":", 2)
    action = parts[1]
 
    if action == "new":
        await cb.message.edit_text("Введите название дисциплины:")
        return
 
    if action == "today":
        disc_name = parts[2]
        disc_id   = await get_or_create_discipline(disc_name)
        await state.update_data(discipline_id=disc_id, discipline_name=disc_name)
    elif action == "id":
        disc_id = int(parts[2])
        disciplines = await get_all_disciplines()
        disc = next((d for d in disciplines if d["id"] == disc_id), None)
        await state.update_data(discipline_id=disc_id,
                                discipline_name=disc["name"] if disc else "")
 
    await _ask_lesson(cb.message, state, edit=True)
 
 
@router.message(AddAbsenceState.select_discipline)
async def abs_disc_manual(msg: Message, state: FSMContext):
    disc_id = await get_or_create_discipline(msg.text.strip())
    await state.update_data(discipline_id=disc_id, discipline_name=msg.text.strip())
    await _ask_lesson(msg, state, edit=False)
 
 
# ── ШАГ 3: выбор пары (номер / время) ────────────────────────────────────────
 
async def _ask_lesson(msg_or_cb_msg, state: FSMContext, edit: bool):
    """Предлагает выбрать номер пары из расписания или ввести вручную."""
    data = await state.get_data()
    disc_name = data.get("discipline_name", "")
 
    # Ищем пары из расписания по этой дисциплине (сегодня)
    today_lessons = get_today_lessons(disc_name)
 
    await state.set_state(AddAbsenceState.select_lesson)
 
    kb_rows = []
    if today_lessons:
        for i, lesson in enumerate(today_lessons, 1):
            time_str = lesson.get("time", "")
            ltype    = lesson.get("type", "")
            label    = f"{i}-я пара — {time_str}"
            if ltype:
                label += f" ({ltype})"
            kb_rows.append([InlineKeyboardButton(
                text=label,
                callback_data=f"abs_lesson:{i}:{time_str}"
            )])
 
    # Стандартные пары если расписания нет
    if not kb_rows:
        standard = [
            (1, "08:00 - 09:25"),
            (2, "09:40 - 11:05"),
            (3, "11:35 - 13:00"),
            (4, "13:30 - 14:55"),
            (5, "15:05 - 16:30"),
            (6, "16:40 - 18:05"),
        ]
        for num, time_str in standard:
            kb_rows.append([InlineKeyboardButton(
                text=f"{num}-я пара ({time_str})",
                callback_data=f"abs_lesson:{num}:{time_str}"
            )])
 
    kb_rows.append([InlineKeyboardButton(text="Не указывать пару", callback_data="abs_lesson:0:")])
 
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    text = f"Выберите пару для *{disc_name}*:" if disc_name else "Выберите пару:"
 
    if edit:
        await msg_or_cb_msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg_or_cb_msg.answer(text, reply_markup=kb, parse_mode="Markdown")
 
 
@router.callback_query(AddAbsenceState.select_lesson, F.data.startswith("abs_lesson:"))
async def cb_abs_select_lesson(cb: CallbackQuery, state: FSMContext):
    _, num_str, time_str = cb.data.split(":", 2)
    lesson_num  = int(num_str) if num_str and num_str != "0" else None
    lesson_time = time_str if time_str else None
 
    await state.update_data(lesson_num=lesson_num, lesson_time=lesson_time)
    await state.set_state(AddAbsenceState.enter_date)
 
    today_str = date.today().strftime("%d.%m.%Y")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Сегодня ({today_str})", callback_data="abs_date:today")]
    ])
    await cb.message.edit_text(
        "Укажите дату пропуска (ДД.ММ.ГГГГ) или выберите сегодня:",
        reply_markup=kb
    )
 
 
# ── ШАГ 4: дата ──────────────────────────────────────────────────────────────
 
@router.callback_query(AddAbsenceState.enter_date, F.data == "abs_date:today")
async def cb_abs_date_today(cb: CallbackQuery, state: FSMContext):
    await state.update_data(absence_date=date.today())
    await state.set_state(AddAbsenceState.enter_hours)
    await cb.message.edit_text("Сколько часов пропущено?", reply_markup=_hours_kb())
 
 
@router.message(AddAbsenceState.enter_date)
async def abs_date_manual(msg: Message, state: FSMContext):
    try:
        from datetime import datetime
        d = datetime.strptime(msg.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await msg.answer("❌ Неверный формат даты. Введите как ДД.ММ.ГГГГ")
        return
    await state.update_data(absence_date=d)
    await state.set_state(AddAbsenceState.enter_hours)
    await msg.answer("Сколько часов пропущено?", reply_markup=_hours_kb())
 
 
def _hours_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 ч.", callback_data="abs_hours:2"),
         InlineKeyboardButton(text="4 ч.", callback_data="abs_hours:4")],
        [InlineKeyboardButton(text="6 ч.", callback_data="abs_hours:6"),
         InlineKeyboardButton(text="8 ч.", callback_data="abs_hours:8")],
    ])
 
 
# ── ШАГ 5: часы ──────────────────────────────────────────────────────────────
 
@router.callback_query(AddAbsenceState.enter_hours, F.data.startswith("abs_hours:"))
async def cb_abs_hours(cb: CallbackQuery, state: FSMContext):
    hours = int(cb.data.split(":")[1])
    await state.update_data(hours=hours)
    await state.set_state(AddAbsenceState.enter_reason)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="abs_reason:skip")]
    ])
    await cb.message.edit_text(
        "Причина пропуска (необязательно):\nНапример: болезнь, справка, уважительная",
        reply_markup=kb
    )
 
 
# ── ШАГ 6: причина и сохранение ──────────────────────────────────────────────
 
@router.callback_query(AddAbsenceState.enter_reason, F.data == "abs_reason:skip")
async def cb_abs_reason_skip(cb: CallbackQuery, state: FSMContext):
    await _save_absence(cb.message, state, reason=None, edit=True)
 
 
@router.message(AddAbsenceState.enter_reason)
async def abs_reason_text(msg: Message, state: FSMContext):
    await _save_absence(msg, state, reason=msg.text.strip())
 
 
async def _save_absence(msg_or_msg, state: FSMContext, reason: str = None, edit: bool = False):
    data = await state.get_data()
    await state.clear()
 
    lesson_num  = data.get("lesson_num")
    lesson_time = data.get("lesson_time")
 
    await add_absence(
        student_id    = data["student_id"],
        discipline_id = data["discipline_id"],
        date          = data["absence_date"],
        hours         = data["hours"],
        reason        = reason,
        lesson_num    = lesson_num,
        lesson_time   = lesson_time,
    )
 
    # Формируем читаемый текст о паре
    if lesson_num:
        pair_str = f"\n🕐 Пара: *{lesson_num}-я*"
        if lesson_time:
            pair_str += f" ({lesson_time})"
    else:
        pair_str = ""
 
    text = (
        f"✅ Пропуск записан!\n"
        f"📚 Дисциплина: *{data.get('discipline_name', '')}*\n"
        f"📅 Дата: {data['absence_date'].strftime('%d.%m.%Y')}"
        f"{pair_str}\n"
        f"⏱ Часов: {data['hours']}"
    )
    if reason:
        text += f"\n📝 Причина: {reason}"
 
    if edit:
        await msg_or_msg.edit_text(text, parse_mode="Markdown")
    else:
        await msg_or_msg.answer(text, parse_mode="Markdown")
 
 
# ── Просмотр пропусков ────────────────────────────────────────────────────────
 
@router.callback_query(F.data == "abs:by_student")
async def cb_abs_by_student(cb: CallbackQuery, state: FSMContext):
    students = await get_all_students()
    await cb.message.edit_text("Выберите студента:", reply_markup=students_list_kb(students))
 
 
@router.callback_query(F.data == "abs:by_disc")
async def cb_abs_by_disc(cb: CallbackQuery):
    disciplines = await get_all_disciplines()
    if not disciplines:
        await cb.answer("Дисциплины не найдены.", show_alert=True)
        return
    kb_rows = [[InlineKeyboardButton(text=d["name"], callback_data=f"view_disc:{d['id']}")]
               for d in disciplines]
    await cb.message.edit_text(
        "Выберите дисциплину:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
 
 
@router.callback_query(F.data.startswith("view_disc:"))
async def cb_view_disc(cb: CallbackQuery):
    disc_id    = int(cb.data.split(":")[1])
    absences   = await get_absences(discipline_id=disc_id)
    disciplines = await get_all_disciplines()
    disc = next((d for d in disciplines if d["id"] == disc_id), None)
    title = disc["name"] if disc else "Дисциплина"
    text  = format_absences_text(absences, title)
    await cb.message.answer(text, parse_mode="Markdown")
    await cb.answer()
 
 
@router.message(F.text == "⚙️ Управление")
async def management_menu(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user or user["role"] not in ("admin", "superadmin"):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Назначить администратора", callback_data="mgmt:addadmin")],
        [InlineKeyboardButton(text="📚 Назначить старосту",       callback_data="mgmt:addstarost")],
    ])
    await msg.answer("Управление пользователями:", reply_markup=kb)
 
