"""
Работа с файлом bookings.csv — сохранение и загрузка записей.
Формат CSV (открывается в Excel): id,date,time,service,barber,price,client_name,phone,email,booked_at
"""
import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKINGS_PATH = os.path.join(BASE_DIR, "bookings.csv")
COLUMNS = ["id", "date", "time", "service", "price", "barber",
           "client_name", "phone", "email", "booked_at"]


def _ensure_file():
    """Создаёт файл с заголовками, если его нет."""
    if not os.path.exists(BOOKINGS_PATH):
        with open(BOOKINGS_PATH, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(COLUMNS)


def load_booked_slots() -> dict[str, dict]:
    """
    Загружает все записи из CSV.
    Возвращает словарь {slot_key: booking_dict}, где slot_key = "YYYY-MM-DD|HH:MM".
    """
    _ensure_file()
    booked: dict[str, dict] = {}
    with open(BOOKINGS_PATH, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            slot_key = f"{row['date']}|{row['time']}"
            booked[slot_key] = row
    return booked


def save_booking(booking: dict) -> None:
    """
    Сохраняет одну запись в CSV.
    booking: {date, time, service, price, barber, client_name, phone, email}
    """
    _ensure_file()
    # Генерируем ID = количество строк (без заголовка)
    with open(BOOKINGS_PATH, encoding="utf-8-sig") as fh:
        row_count = sum(1 for _ in fh) - 1  # минус заголовок

    with open(BOOKINGS_PATH, "a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            row_count + 1,
            booking["date"],
            booking["time"],
            booking["service"],
            booking["price"],
            booking["barber"],
            booking.get("client_name", ""),
            booking.get("phone", ""),
            booking.get("email", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ])