from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.queries import (get_user, create_user, get_student_by_name,
                        link_student_to_user, get_absences, save_proof_photo)
from utils.keyboards import main_menu_admin, main_menu_starost, main_menu_student
from utils.formatters import format_absences_text
from services.schedule import fetch_schedule, format_schedule, get_today_subjects

router = Router()


class RegisterState(StatesGroup):
    waiting_last_name  = State()
    waiting_first_name = State()


def _menu_kb(role: str):
    if role in ("admin", "superadmin"):
        return main_menu_admin()
    if role == "starost":
        return main_menu_starost()
    return main_menu_student()


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_user(msg.from_user.id)
    if not user:
        await create_user(msg.from_user.id)
        user = await get_user(msg.from_user.id)

    role = user["role"]
    name = msg.from_user.first_name or "студент"

    if role in ("admin", "superadmin"):
        greeting = f"👋 Привет, {name}! Вы администратор."
    elif role == "starost":
        greeting = f"👋 Привет, {name}! Вы вошли как *староста*."
    else:
        if user.get("student_id"):
            greeting = f"👋 Привет, {name}! Вы зарегистрированы."
        else:
            greeting = (
                f"👋 Привет, {name}!\n\n"
                "Используйте /register чтобы привязать свой аккаунт к списку группы."
            )
    await msg.answer(greeting, reply_markup=_menu_kb(role), parse_mode="Markdown")


@router.message(Command("register"))
async def cmd_register(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if not user:
        await create_user(msg.from_user.id)
    if user and user.get("student_id"):
        await msg.answer("✅ Вы уже зарегистрированы.")
        return
    await state.set_state(RegisterState.waiting_last_name)
    await msg.answer("Введите вашу *фамилию*:", parse_mode="Markdown")


@router.message(RegisterState.waiting_last_name)
async def register_last_name(msg: Message, state: FSMContext):
    await state.update_data(last_name=msg.text.strip())
    await state.set_state(RegisterState.waiting_first_name)
    await msg.answer("Введите ваше *имя*:", parse_mode="Markdown")


@router.message(RegisterState.waiting_first_name)
async def register_first_name(msg: Message, state: FSMContext):
    data = await state.get_data()
    last_name  = data["last_name"]
    first_name = msg.text.strip()
    await state.clear()

    student = await get_student_by_name(last_name, first_name)
    if not student:
        await msg.answer(
            f"❌ Студент *{last_name} {first_name}* не найден в списке группы.\n"
            "Убедитесь в правильности написания или обратитесь к старосте.",
            parse_mode="Markdown"
        )
        return

    if student.get("tg_id") and student["tg_id"] != msg.from_user.id:
        await msg.answer("❌ Этот студент уже привязан к другому аккаунту.")
        return

    await link_student_to_user(msg.from_user.id, student["id"])
    user = await get_user(msg.from_user.id)
    await msg.answer(
        f"✅ Вы зарегистрированы как *{last_name} {first_name}*!",
        reply_markup=_menu_kb(user["role"]),
        parse_mode="Markdown"
    )


@router.message(F.text == "📋 Мои пропуски")
async def my_absences(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user or not user.get("student_id"):
        await msg.answer("Сначала зарегистрируйтесь: /register")
        return
    absences = await get_absences(student_id=user["student_id"])
    text = format_absences_text(absences, "Мои пропуски")
    await msg.answer(text, parse_mode="Markdown")


@router.message(F.text == "📅 Расписание")
async def schedule_handler(msg: Message):
    await msg.answer("⏳ Загружаю расписание...")
    lessons = await fetch_schedule()
    text = format_schedule(lessons)
    await msg.answer(text[:4000] or "Расписание не найдено.")


@router.message(F.photo)
async def handle_photo(msg: Message):
    user = await get_user(msg.from_user.id)
    if not user or not user.get("student_id"):
        await msg.answer("Сначала зарегистрируйтесь: /register")
        return
    file_id = msg.photo[-1].file_id
    caption = msg.caption or ""
    await save_proof_photo(user["student_id"], file_id, caption)
    await msg.answer("✅ Справка сохранена. Администратор её проверит.")
