from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.queries import (set_user_role, get_user, get_all_students,
                        get_all_disciplines, get_absences, get_student_photos,
                        remove_student, get_student_total_hours)
from services.docx_export import generate_full_report, generate_student_report
from utils.keyboards import (students_list_kb, student_actions_kb,
                              report_period_kb, confirm_kb)
from utils.formatters import (format_students_list, format_student_summary,
                               format_absences_text, semester_dates, month_dates)
from config import SUPER_ADMIN_IDS

router = Router()


def is_admin(user) -> bool:
    return user and user["role"] in ("admin", "superadmin")


class AdminState(StatesGroup):
    waiting_admin_id = State()


@router.message(Command("addadmin"))
async def cmd_addadmin(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not is_admin(user):
        return
    await state.set_state(AdminState.waiting_admin_id)
    await msg.answer(
        "Перешлите мне любое сообщение от пользователя, которого хотите сделать администратором, "
        "или введите его Telegram ID:"
    )


@router.message(AdminState.waiting_admin_id)
async def set_admin(msg: Message, state: FSMContext):
    await state.clear()
    tg_id = None
    if msg.forward_from:
        tg_id = msg.forward_from.id
    else:
        try:
            tg_id = int(msg.text.strip())
        except ValueError:
            await msg.answer("❌ Неверный формат. Введите числовой ID.")
            return
    await set_user_role(tg_id, "admin")
    await msg.answer(f"✅ Пользователь {tg_id} назначен администратором.")


@router.message(Command("addstarost"))
async def cmd_addstarost(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not is_admin(user):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /addstarost <telegram_id>")
        return
    try:
        tg_id = int(parts[1])
    except ValueError:
        await msg.answer("❌ Неверный ID.")
        return
    await set_user_role(tg_id, "starost")
    await msg.answer(f"✅ Пользователь {tg_id} назначен старостой.")


@router.message(Command("rmadmin"))
async def cmd_rmadmin(msg: Message):
    user = await get_user(msg.from_user.id)
    if user["role"] != "superadmin":
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /rmadmin <telegram_id>")
        return
    tg_id = int(parts[1])
    await set_user_role(tg_id, "student")
    await msg.answer(f"✅ Права администратора у {tg_id} сняты.")


@router.message(F.text == "👥 Студенты")
async def students_menu(msg: Message):
    user = await get_user(msg.from_user.id)
    if not is_admin(user) and user["role"] != "starost":
        return
    students = await get_all_students()
    text = format_students_list(students)
    kb   = students_list_kb(students)
    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "students_list")
async def cb_students_list(cb: CallbackQuery):
    user = await get_user(cb.from_user.id)
    if not is_admin(user) and user["role"] != "starost":
        return
    students = await get_all_students()
    text = format_students_list(students)
    kb   = students_list_kb(students)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("student:"))
async def cb_student_detail(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    user = await get_user(cb.from_user.id)
    students = await get_all_students()
    student = next((s for s in students if s["id"] == student_id), None)
    if not student:
        await cb.answer("Студент не найден.")
        return
    total = await get_student_total_hours(student_id)
    text = format_student_summary(student, total)
    kb   = student_actions_kb(student_id, is_admin=is_admin(user))
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("st_abs:"))
async def cb_student_absences(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    absences = await get_absences(student_id=student_id)
    students = await get_all_students()
    student  = next((s for s in students if s["id"] == student_id), None)
    name = f"{student['last_name']} {student['first_name']}" if student else "Студент"
    text = format_absences_text(absences, f"Пропуски — {name}")
    await cb.message.answer(text, parse_mode="Markdown")
    await cb.answer()


@router.callback_query(F.data.startswith("st_docx:"))
async def cb_student_docx(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    await cb.answer("⏳ Генерирую документ...")
    buf = await generate_student_report(student_id)
    if not buf:
        await cb.message.answer("Нет пропусков для этого студента.")
        return
    from aiogram.types import BufferedInputFile
    students = await get_all_students()
    student = next((s for s in students if s["id"] == student_id), None)
    fname = f"absences_{student['last_name']}.docx" if student else "absences.docx"
    await cb.message.answer_document(
        BufferedInputFile(buf.read(), filename=fname),
        caption="📄 Индивидуальный отчёт"
    )


@router.callback_query(F.data.startswith("st_photos:"))
async def cb_student_photos(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    photos = await get_student_photos(student_id)
    if not photos:
        await cb.answer("Нет прикреплённых справок.", show_alert=True)
        return
    await cb.answer()
    for p in photos:
        await cb.message.answer_photo(p["file_id"], caption=p["caption"] or "")


@router.callback_query(F.data.startswith("st_del:"))
async def cb_student_delete_confirm(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    await cb.message.edit_text(
        "⚠️ Удалить студента? Все его пропуски тоже будут удалены.",
        reply_markup=confirm_kb(f"st_del_yes:{student_id}")
    )


@router.callback_query(F.data.startswith("st_del_yes:"))
async def cb_student_delete(cb: CallbackQuery):
    student_id = int(cb.data.split(":")[1])
    await remove_student(student_id)
    await cb.message.edit_text("✅ Студент удалён.")


@router.message(F.text == "📊 Отчёты")
async def reports_menu(msg: Message):
    user = await get_user(msg.from_user.id)
    if not is_admin(user) and user["role"] != "starost":
        return
    await msg.answer("Выберите период для отчёта:", reply_markup=report_period_kb())


@router.callback_query(F.data.startswith("report:"))
async def cb_report(cb: CallbackQuery):
    period = cb.data.split(":")[1]
    await cb.answer("⏳ Генерирую...")

    date_from = date_to = None
    if period == "month":
        date_from, date_to = month_dates()
    elif period == "semester":
        date_from, date_to = semester_dates()

    buf = await generate_full_report(date_from=date_from, date_to=date_to)

    from aiogram.types import BufferedInputFile
    from datetime import date
    fname = f"report_{date.today().strftime('%Y%m%d')}.docx"
    await cb.message.answer_document(
        BufferedInputFile(buf.read(), filename=fname),
        caption="📊 Сводный отчёт по пропускам"
    )
