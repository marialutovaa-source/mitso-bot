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
from services.schedule import get_today_subjects

router = Router()


def is_starost(user) -> bool:
    return user and user["role"] in ("starost", "admin", "superadmin")


class AddStudentState(StatesGroup):
    waiting_name = State()


class AddAbsenceState(StatesGroup):
    select_student    = State()
    select_discipline = State()
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
        [InlineKeyboardButton(text="➕ Отметить пропуск",    callback_data="abs:add")],
        [InlineKeyboardButton(text="📋 Пропуски по студенту", callback_data="abs:by_student")],
        [InlineKeyboardButton(text="📋 Пропуски по дисциплине", callback_data="abs:by_disc")],
    ])
    await msg.answer("Управление пропусками:", reply_markup=kb)


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


@router.callback_query(AddAbsenceState.select_student, F.data.startswith("student:"))
async def cb_abs_select_student(cb: CallbackQuery, state: FSMContext):
    student_id = int(cb.data.split(":")[1])
    await state.update_data(student_id=student_id)
    await state.set_state(AddAbsenceState.select_discipline)

    disciplines = await get_all_disciplines()
    today_subjects = await get_today_subjects()

    if today_subjects and not disciplines:
        kb_rows = []
        for subj in today_subjects:
            kb_rows.append([InlineKeyboardButton(
                text=f"📚 {subj} (сегодня)",
                callback_data=f"abs_disc:today:{subj}"
            )])
        kb_rows.append([InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="abs_disc:new")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    else:
        kb_rows = []
        for d in disciplines:
            kb_rows.append([InlineKeyboardButton(
                text=d["name"], callback_data=f"abs_disc:id:{d['id']}"
            )])
        if today_subjects:
            for subj in today_subjects:
                if not any(d["name"].lower() == subj.lower() for d in disciplines):
                    kb_rows.insert(0, [InlineKeyboardButton(
                        text=f"📚 {subj} (из расписания)",
                        callback_data=f"abs_disc:today:{subj}"
                    )])
        kb_rows.append([InlineKeyboardButton(text="✏️ Новая дисциплина", callback_data="abs_disc:new")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    await cb.message.edit_text("Выберите дисциплину:", reply_markup=kb)


@router.callback_query(AddAbsenceState.select_discipline, F.data.startswith("abs_disc:"))
async def cb_abs_select_disc(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":", 2)
    action = parts[1]

    if action == "new":
        await state.update_data(discipline_name=None)
        await cb.message.edit_text("Введите название дисциплины:")
        return

    if action == "today":
        disc_name = parts[2]
        disc_id = await get_or_create_discipline(disc_name)
        await state.update_data(discipline_id=disc_id)
    elif action == "id":
        disc_id = int(parts[2])
        await state.update_data(discipline_id=disc_id)

    await state.set_state(AddAbsenceState.enter_date)
    today_str = date.today().strftime("%d.%m.%Y")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Сегодня ({today_str})", callback_data=f"abs_date:today")]
    ])
    await cb.message.edit_text(
        f"Укажите дату пропуска (ДД.ММ.ГГГГ) или выберите сегодня:",
        reply_markup=kb
    )


@router.message(AddAbsenceState.select_discipline)
async def abs_disc_manual(msg: Message, state: FSMContext):
    disc_id = await get_or_create_discipline(msg.text.strip())
    await state.update_data(discipline_id=disc_id)
    await state.set_state(AddAbsenceState.enter_date)
    today_str = date.today().strftime("%d.%m.%Y")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📅 Сегодня ({today_str})", callback_data="abs_date:today")]
    ])
    await msg.answer("Укажите дату пропуска (ДД.ММ.ГГГГ):", reply_markup=kb)


@router.callback_query(AddAbsenceState.enter_date, F.data == "abs_date:today")
async def cb_abs_date_today(cb: CallbackQuery, state: FSMContext):
    await state.update_data(absence_date=date.today())
    await state.set_state(AddAbsenceState.enter_hours)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 ч.", callback_data="abs_hours:2"),
         InlineKeyboardButton(text="4 ч.", callback_data="abs_hours:4")],
        [InlineKeyboardButton(text="6 ч.", callback_data="abs_hours:6"),
         InlineKeyboardButton(text="8 ч.", callback_data="abs_hours:8")],
    ])
    await cb.message.edit_text("Сколько часов пропущено?", reply_markup=kb)


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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 ч.", callback_data="abs_hours:2"),
         InlineKeyboardButton(text="4 ч.", callback_data="abs_hours:4")],
        [InlineKeyboardButton(text="6 ч.", callback_data="abs_hours:6"),
         InlineKeyboardButton(text="8 ч.", callback_data="abs_hours:8")],
    ])
    await msg.answer("Сколько часов пропущено?", reply_markup=kb)


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


@router.callback_query(AddAbsenceState.enter_reason, F.data == "abs_reason:skip")
async def cb_abs_reason_skip(cb: CallbackQuery, state: FSMContext):
    await _save_absence(cb.message, state, reason=None, edit=True)


@router.message(AddAbsenceState.enter_reason)
async def abs_reason_text(msg: Message, state: FSMContext):
    await _save_absence(msg, state, reason=msg.text.strip())


async def _save_absence(msg_or_msg, state: FSMContext, reason: str = None, edit: bool = False):
    data = await state.get_data()
    await state.clear()

    await add_absence(
        student_id=data["student_id"],
        discipline_id=data["discipline_id"],
        date=data["absence_date"],
        hours=data["hours"],
        reason=reason
    )

    text = (
        f"✅ Пропуск записан!\n"
        f"📚 Дисциплина: будет показана в отчёте\n"
        f"📅 Дата: {data['absence_date'].strftime('%d.%m.%Y')}\n"
        f"⏱ Часов: {data['hours']}"
    )
    if reason:
        text += f"\n📝 Причина: {reason}"

    if edit:
        await msg_or_msg.edit_text(text)
    else:
        await msg_or_msg.answer(text)


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
    disc_id = int(cb.data.split(":")[1])
    absences = await get_absences(discipline_id=disc_id)
    disciplines = await get_all_disciplines()
    disc = next((d for d in disciplines if d["id"] == disc_id), None)
    title = disc["name"] if disc else "Дисциплина"
    text = format_absences_text(absences, title)
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
