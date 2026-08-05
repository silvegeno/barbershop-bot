"""
Клавиатуры и кнопки для бота.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from data import SERVICES, TIME_SLOTS, WEEKDAYS, barbers_for_service


def start_keyboard() -> InlineKeyboardMarkup:
    """Главное меню: кнопка 'Записаться'."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться", callback_data="book")
    builder.button(text="ℹ️ О нас", callback_data="about")
    builder.adjust(1)
    return builder.as_markup()


def services_keyboard() -> InlineKeyboardMarkup:
    """Выбор услуги."""
    builder = InlineKeyboardBuilder()
    for key, service in SERVICES.items():
        builder.button(
            text=f"{service['name']} — {service['price']} ₽",
            callback_data=f"service:{key}"
        )
    builder.button(text="⬅️ Назад", callback_data="back_to_start")
    builder.adjust(1)
    return builder.as_markup()


def barbers_keyboard(service_key: str) -> InlineKeyboardMarkup:
    """Выбор мастера, выполняющего выбранную услугу."""
    builder = InlineKeyboardBuilder()
    for key, barber in barbers_for_service(service_key).items():
        builder.button(
            text=f"{barber['name']} — {barber['specialty_short']}",
            callback_data=f"barber:{key}"
        )
    builder.button(text="⬅️ Назад", callback_data="back_to_services")
    builder.adjust(1)
    return builder.as_markup()


def dates_keyboard() -> InlineKeyboardMarkup:
    """Выбор даты: семь ближайших календарных дней."""
    builder = InlineKeyboardBuilder()
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    added = 0
    offset = 0
    while added < 7:
        d = today + timedelta(days=offset)
        offset += 1
        label = f"{d.strftime('%d.%m')} ({WEEKDAYS[d.weekday()]})"
        if d.date() == today.date():
            label = f"📌 Сегодня {label}"
        elif d.date() == tomorrow.date():
            label = f"🔜 Завтра {label}"
        builder.button(text=label, callback_data=f"date:{d.strftime('%Y-%m-%d')}")
        added += 1
    builder.button(text="⬅️ Назад", callback_data="back_to_barbers")
    builder.adjust(1)
    return builder.as_markup()


def time_keyboard(date_str: str, unavailable: set[str]) -> InlineKeyboardMarkup:
    """Выбор времени. Занятые слоты помечаются."""
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    for slot in TIME_SLOTS:
        # Если дата сегодня — не показываем прошедшие слоты
        if date_str == today_str:
            slot_hour, slot_min = map(int, slot.split(":"))
            if slot_hour < now.hour or (slot_hour == now.hour and slot_min <= now.minute):
                continue

        if slot in unavailable:
            builder.button(text=f"❌ {slot} (занято)", callback_data="ignore")
        else:
            builder.button(text=f"🕐 {slot}", callback_data=f"time:{slot}")
    builder.button(text="⬅️ Назад", callback_data="back_to_dates")
    builder.adjust(3)
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm")
    builder.button(text="❌ Отменить", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def done_keyboard() -> InlineKeyboardMarkup:
    """После успешной записи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться ещё", callback_data="book")
    builder.button(text="🏠 В начало", callback_data="back_to_start")
    builder.adjust(1)
    return builder.as_markup()


def skip_email_keyboard() -> InlineKeyboardMarkup:
    """Пропустить ввод email."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip_email")
    builder.adjust(1)
    return builder.as_markup()


def privacy_notice_keyboard() -> InlineKeyboardMarkup:
    """Ссылка на политику до ввода персональных данных."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📜 Политика обработки персональных данных",
        url="https://apetr.net/bot-personal-data.html",
    )
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()
