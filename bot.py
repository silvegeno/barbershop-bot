"""
Чат-бот для записи в барбершоп Острый стиль.
Кейс 4.2 — Telegram-бот с пошаговой записью.
"""
import asyncio
import logging
import os
import re
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from data import SERVICES, BARBERS, WEEKDAYS
from keyboards import (
    start_keyboard, services_keyboard, barbers_keyboard,
    dates_keyboard, time_keyboard, confirm_keyboard, done_keyboard,
    skip_email_keyboard, privacy_notice_keyboard,
)
from bookings import (
    generate_weekly_schedule, get_client, is_slot_available, save_booking, save_client,
    unavailable_slots,
)

load_dotenv()

# Абсолютный путь к папке бота (надёжно при запуске через systemd)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# FSM — состояния диалога записи
# ---------------------------------------------------------------------------
class Booking(StatesGroup):
    choosing_service = State()
    choosing_barber = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    entering_email = State()
    confirming = State()


async def notify_admin_about_booking(
    bot: Bot,
    service: dict,
    barber: dict,
    date_label: str,
    time_str: str,
    client_name: str,
    phone: str,
    email: str,
) -> None:
    """Отправляет администратору сообщение о новой подтверждённой записи."""
    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
    if not admin_id or not admin_id.isdigit():
        logging.warning("ADMIN_TELEGRAM_ID не задан или содержит некорректное значение")
        return

    text = (
        "🔔 <b>Новая запись!</b>\n\n"
        f"💈 Услуга: {service['name']}\n"
        f"👤 Мастер: {barber['name']}\n"
        f"📅 Дата: {date_label} в {time_str}\n"
        f"⏱ Длительность: {service['duration_min']} мин\n"
        f"💰 Цена: {service['price']} ₽\n\n"
        f"👤 Клиент: {client_name}\n"
        f"📱 Телефон: {phone}\n"
        f"📧 Email: {email or '—'}"
    )
    try:
        await bot.send_message(chat_id=int(admin_id), text=text, parse_mode="HTML")
    except Exception:
        # Запись уже сохранена: сбой уведомления не должен отменять её для клиента.
        logging.exception("Не удалось отправить уведомление администратору")


# ===========================================================================
# ОБРАБОТЧИКИ
# ===========================================================================

async def cmd_start(message: Message, state: FSMContext):
    """Главный экран — /start."""
    await state.clear()
    await message.answer_photo(
        photo=FSInputFile(os.path.join(BASE_DIR, "logo.png")),
        caption=(
            "Добро пожаловать в барбершоп Острый стиль! ✂️\n\n"
            "Здесь ты можешь быстро записаться к мастеру:\n"
            "• 3 профессиональных барбера\n"
            "• Запись за 30 секунд"
        ),
        reply_markup=start_keyboard(),
        parse_mode="HTML",
    )


# --- О нас ---
async def about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "🏆 Барбершоп Острый стиль — мужские стрижки с 2019 года.\n\n"
        "Наши мастера:\n"
        f"• {BARBERS['ivan']['name']} — {BARBERS['ivan']['specialty']}\n"
        f"• {BARBERS['dmitry']['name']} — {BARBERS['dmitry']['specialty']}\n"
        f"• {BARBERS['artur']['name']} — {BARBERS['artur']['specialty']}\n\n"
        "📍 Москва, Воронежская ул., 44, корп. 1А\n"
        "🕐 Ежедневно 10:00 – 20:00",
        reply_markup=start_keyboard(),
    )


# --- Шаг 1: Выбор услуги ---
async def book_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Booking.choosing_service)
    await callback.message.delete()
    await callback.message.answer(
        "✂️ <b>Шаг 1 из 7 — Выбери услугу:</b>",
        reply_markup=services_keyboard(),
        parse_mode="HTML",
    )


async def service_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    service_key = callback.data.split(":")[1]
    service = SERVICES[service_key]
    await state.update_data(service_key=service_key)
    await state.set_state(Booking.choosing_barber)
    await callback.message.edit_text(
        f"✅ <b>Услуга:</b> {service['name']} — {service['price']} ₽\n\n"
        f"👤 <b>Шаг 2 из 7 — Выбери мастера:</b>",
        reply_markup=barbers_keyboard(),
        parse_mode="HTML",
    )


# --- Шаг 2: Выбор мастера ---
async def barber_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    barber_key = callback.data.split(":")[1]
    barber = BARBERS[barber_key]
    await state.update_data(barber_key=barber_key)
    await state.set_state(Booking.choosing_date)
    await callback.message.edit_text(
        f"✅ <b>Мастер:</b> {barber['name']}\n\n"
        f"📅 <b>Шаг 3 из 7 — Выбери дату:</b>",
        reply_markup=dates_keyboard(),
        parse_mode="HTML",
    )


# --- Шаг 3: Выбор даты ---
async def date_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    date_str = callback.data.split(":")[1]
    await state.update_data(date_str=date_str)

    data = await state.get_data()
    barber = BARBERS[data["barber_key"]]
    service = SERVICES[data["service_key"]]
    unavailable = unavailable_slots(date_str, barber["name"], service["duration_min"])

    d = datetime.strptime(date_str, "%Y-%m-%d")
    label = f"{d.strftime('%d.%m')} ({WEEKDAYS[d.weekday()]})"

    await state.set_state(Booking.choosing_time)
    await callback.message.edit_text(
        f"✅ <b>Дата:</b> {label}\n\n"
        f"🕐 <b>Шаг 4 из 7 — Выбери время:</b>",
        reply_markup=time_keyboard(date_str, unavailable),
        parse_mode="HTML",
    )


# --- Шаг 4: Выбор времени ---
async def time_chosen(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    time_str = callback.data.removeprefix("time:")
    data = await state.get_data()
    service = SERVICES[data["service_key"]]
    barber = BARBERS[data["barber_key"]]
    if not is_slot_available(data["date_str"], time_str, barber["name"], service["duration_min"]):
        await callback.message.edit_text(
            "⚠️ Это время только что заняли или услуга не успевает до закрытия. Выбери другое.",
            reply_markup=time_keyboard(
                data["date_str"],
                unavailable_slots(data["date_str"], barber["name"], service["duration_min"]),
            ),
        )
        return
    await state.update_data(time_str=time_str)

    client = get_client(callback.from_user.id)
    if client:
        await state.update_data(
            telegram_id=callback.from_user.id,
            client_name=client["client_name"],
            phone=client["phone"],
            email=client.get("email", ""),
        )
        await state.set_state(Booking.confirming)
        # Экран выбора времени больше не нужен: подтверждение должно быть
        # единственным активным сообщением в этом сценарии.
        await callback.message.delete()
        await show_confirmation(callback.message, state)
        return

    await state.update_data(telegram_id=callback.from_user.id)
    await state.set_state(Booking.entering_name)

    # Удаляем сообщение с выбором времени и шлём запрос имени
    await callback.message.delete()
    await callback.message.answer(
        "👤 <b>Шаг 5 из 7 — Введи имя:</b>\n\n"
        "<i>Как к тебе обращаться?</i>\n\n"
        "Перед вводом ознакомься с политикой обработки персональных данных.",
        reply_markup=privacy_notice_keyboard(),
        parse_mode="HTML",
    )


# --- Шаг 5: Ввод имени ---
async def name_entered(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Имя должно быть не короче 2 символов. Попробуй ещё раз:")
        return

    await state.update_data(client_name=name)
    await state.set_state(Booking.entering_phone)

    # Удаляем сообщение с именем (приватность)
    await message.delete()
    await message.answer(
        "📱 <b>Шаг 6 из 7 — Введи телефон:</b>\n\n"
        "<i>В формате +7XXXXXXXXXX или 8XXXXXXXXXX</i>\n"
        "Нужен, чтобы барбершоп мог связаться с тобой.",
        parse_mode="HTML",
    )


# --- Шаг 6: Ввод телефона ---
async def phone_entered(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Простая валидация: +7/8 и 10-11 цифр
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10 or len(digits) > 11:
        await message.answer("⚠️ Неверный формат. Введи телефон в формате +7XXXXXXXXXX:")
        return

    await state.update_data(phone=phone)
    await state.set_state(Booking.entering_email)

    await message.delete()
    await message.answer(
        "📧 <b>Шаг 7 из 7 — Email (по желанию):</b>\n\n"
        "<i>Для отправки подтверждения записи. Можно пропустить.</i>",
        reply_markup=skip_email_keyboard(),
        parse_mode="HTML",
    )


# --- Шаг 7: Ввод email (или пропуск) ---
async def email_entered(message: Message, state: FSMContext):
    email = message.text.strip()
    await state.update_data(email=email)
    await state.set_state(Booking.confirming)

    await message.delete()
    await show_confirmation(message, state)


async def skip_email(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(email="")
    await state.set_state(Booking.confirming)

    await callback.message.delete()
    await show_confirmation(callback.message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показывает проверку записи для нового или повторного клиента."""
    data = await state.get_data()
    service = SERVICES[data["service_key"]]
    barber = BARBERS[data["barber_key"]]
    date_str = data["date_str"]
    time_str = data["time_str"]
    d = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{d.strftime('%d.%m.%Y')} ({WEEKDAYS[d.weekday()]})"

    text = (
        f"📋 <b>Проверь данные записи:</b>\n\n"
        f"💈 <b>Услуга:</b> {service['name']}\n"
        f"👤 <b>Мастер:</b> {barber['name']}\n"
        f"📅 <b>Дата:</b> {date_label}\n"
        f"🕐 <b>Время:</b> {time_str}\n"
        f"⏱ <b>Длительность:</b> ~{service['duration_min']} мин\n"
        f"💰 <b>Цена:</b> {service['price']} ₽\n\n"
        f"👤 <b>Имя:</b> {data['client_name']}\n"
        f"📱 <b>Телефон:</b> {data['phone']}\n"
        f"📧 <b>Email:</b> {data.get('email') or '—'}\n\n"
        f"Всё верно?"
    )
    await message.answer(text, reply_markup=confirm_keyboard(), parse_mode="HTML")


# --- Финальное подтверждение ---
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    service = SERVICES[data["service_key"]]
    barber = BARBERS[data["barber_key"]]
    date_str = data["date_str"]
    time_str = data["time_str"]

    # Проверка: не занят ли слот
    if not is_slot_available(date_str, time_str, barber["name"], service["duration_min"]):
        await callback.message.edit_text(
            "⚠️ К сожалению, это время только что заняли. Выбери другое.",
            reply_markup=dates_keyboard(),
        )
        await state.set_state(Booking.choosing_date)
        return

    # Сохраняем карточку нового клиента и подтверждённую запись.
    if not get_client(data["telegram_id"]):
        save_client({
            "telegram_id": data["telegram_id"],
            "client_name": data["client_name"],
            "phone": data["phone"],
            "email": data.get("email", ""),
        })
    save_booking({
        "date": date_str,
        "time": time_str,
        "service": service["name"],
        "price": service["price"],
        "barber": barber["name"],
        "duration_min": service["duration_min"],
        "telegram_id": data["telegram_id"],
        "client_name": data["client_name"],
        "phone": data["phone"],
        "email": data.get("email", ""),
    })

    d = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{d.strftime('%d.%m.%Y')} ({WEEKDAYS[d.weekday()]})"

    await notify_admin_about_booking(
        bot=bot,
        service=service,
        barber=barber,
        date_label=date_label,
        time_str=time_str,
        client_name=data["client_name"],
        phone=data["phone"],
        email=data.get("email", ""),
    )

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Запись подтверждена!</b>\n\n"
        f"💈 {service['name']}\n"
        f"👤 Мастер: {barber['name']}\n"
        f"📅 {date_label} в {time_str}\n"
        f"💰 {service['price']} ₽\n\n"
        "📍 Ждём тебя по адресу: Воронежская ул., 44, корп. 1А\n"
        "\n"
        "<i>Хорошего дня и острого стиля! 🪒</i>",
        reply_markup=done_keyboard(),
        parse_mode="HTML",
    )


async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "❌ Запись отменена.\nЕсли передумаешь — жми «Записаться».",
        reply_markup=start_keyboard(),
    )


# --- Навигация «Назад» ---
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile(os.path.join(BASE_DIR, "logo.png")),
        caption="Добро пожаловать в барбершоп Острый стиль! ✂️\n\nЧто хочешь сделать?",
        reply_markup=start_keyboard(),
        parse_mode="HTML",
    )


async def back_to_services(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Booking.choosing_service)
    await callback.message.edit_text(
        "✂️ <b>Шаг 1 из 7 — Выбери услугу:</b>",
        reply_markup=services_keyboard(),
        parse_mode="HTML",
    )


async def back_to_barbers(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Booking.choosing_barber)
    await callback.message.edit_text(
        "👤 <b>Шаг 2 из 7 — Выбери мастера:</b>",
        reply_markup=barbers_keyboard(),
        parse_mode="HTML",
    )


async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Booking.choosing_date)
    await callback.message.edit_text(
        "📅 <b>Шаг 3 из 7 — Выбери дату:</b>",
        reply_markup=dates_keyboard(),
        parse_mode="HTML",
    )


async def ignore_click(callback: CallbackQuery):
    await callback.answer("Этот слот уже занят 😔", show_alert=False)


# ===========================================================================
# ТОЧКА ВХОДА
# ===========================================================================
async def main():
    token = os.getenv("BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("❌ Ошибка: установите BOT_TOKEN в файле .env")
        return

    generate_weekly_schedule()
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # --- Команды ---
    dp.message.register(cmd_start, Command("start"))

    # --- Главное меню ---
    dp.callback_query.register(about, F.data == "about")
    dp.callback_query.register(book_start, F.data == "book")

    # --- Шаги записи (callback) ---
    dp.callback_query.register(service_chosen, F.data.startswith("service:"))
    dp.callback_query.register(barber_chosen, F.data.startswith("barber:"))
    dp.callback_query.register(date_chosen, F.data.startswith("date:"))
    dp.callback_query.register(time_chosen, F.data.startswith("time:"))

    # --- Сбор контактов (message handlers — только в соответствующих состояниях) ---
    dp.message.register(name_entered, Booking.entering_name)
    dp.message.register(phone_entered, Booking.entering_phone)
    dp.message.register(email_entered, Booking.entering_email)

    # --- Пропуск email (callback) ---
    dp.callback_query.register(skip_email, F.data == "skip_email")

    # --- Подтверждение ---
    dp.callback_query.register(confirm_booking, F.data == "confirm")
    dp.callback_query.register(cancel_booking, F.data == "cancel")

    # --- Навигация ---
    dp.callback_query.register(back_to_start, F.data == "back_to_start")
    dp.callback_query.register(back_to_services, F.data == "back_to_services")
    dp.callback_query.register(back_to_barbers, F.data == "back_to_barbers")
    dp.callback_query.register(back_to_dates, F.data == "back_to_dates")

    # --- Игнор занятых слотов ---
    dp.callback_query.register(ignore_click, F.data == "ignore")

    print("🚀 Бот запущен. Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
