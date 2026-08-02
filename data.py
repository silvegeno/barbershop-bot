"""
Данные барбершопа BARBERVAULT: услуги, мастера, расписание.
Загружаются из CSV-файлов — администратор может редактировать в Excel.
"""
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_csv(filename: str) -> list[dict]:
    """Читает CSV-файл и возвращает список словарей (первая строка = заголовки)."""
    path = os.path.join(BASE_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


# Услуги → {key: {name, price (int), duration_min (int), category}}
_services_raw = _load_csv("services.csv")
SERVICES: dict[str, dict] = {}
for row in _services_raw:
    SERVICES[row["key"]] = {
        "name": row["name"],
        "price": int(row["price"]),
        "duration_min": int(row["duration_min"]),
        "category": row["category"],
    }

# Мастера → {key: {name, specialty}}
_barbers_raw = _load_csv("barbers.csv")
BARBERS: dict[str, dict] = {}
for row in _barbers_raw:
    BARBERS[row["key"]] = {
        "name": row["name"],
        "specialty": row["specialty"],
    }

# Рабочие часы: ПН–СБ 10:00–21:00 (11 слотов), ВС — выходной
TIME_SLOTS = [
    "10:00", "11:00", "12:00", "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00", "19:00", "20:00",
]

# Дни недели
WEEKDAYS = {
    0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс",
}

# Воскресенье — выходной (пропускаем при генерации дат)
DAY_OFF = {6}  # Sunday

# Логотип (устарело, не используется — см. FSInputFile("logo.png"))
LOGO = ""