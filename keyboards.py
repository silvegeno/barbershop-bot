"""
Клавиатуры и кнопки для бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from data import SERVICES, BARBERS, TIME_SLOTS, WEEKDAYS


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


def barbers_keyboard() -> InlineKeyboardMarkup:
    """Выбор мастера."""
    builder = InlineKeyboardBuilder()
    for key, barber in BARBERS.items():
        builder.button(
            text=f"{barber['name']} ({barber['specialty']})",
            callback_data=f"barber:{key}"
        )
    builder.button(text="⬅️ Назад", callback_data="back_to_services")
    builder.adjust(1)
    return builder.as_markup()


def dates_keyboard() -> InlineKeyboardMarkup:
    """Выбор даты: 7 ближайших РАБОЧИХ дней (ВС — выходной)."""
    builder = InlineKeyboardBuilder()
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    added = 0
    offset = 0
    while added < 7:
        d = today + timedelta(days=offset)
        offset += 1
        if d.weekday() == 6:  # Воскресенье — выходной
            continue
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


def time_keyboard(date_str: str, booked_slots: set) -> InlineKeyboardMarkup:
    """Выбор времени. Занятые слоты помечаются."""
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    for slot in TIME_SLOTS:
        slot_key = f"{date_str}|{slot}"
        # Если дата сегодня — не показываем прошедшие слоты
        if date_str == today_str:
            slot_hour, slot_min = map(int, slot.split(":"))
            if slot_hour < now.hour or (slot_hour == now.hour and slot_min <= now.minute):
                continue

        if slot_key in booked_slots:
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


def privacy_keyboard() -> InlineKeyboardMarkup:
    """Согласие на обработку ПД."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен", callback_data="privacy_accept")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()
