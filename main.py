import logging
import sqlite3
import os
from datetime import datetime, timezone
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputFile
from config import BOT_TOKEN, ADMIN_USERNAME

# —————— Health-check HTTP server ——————
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Запускаємо HTTP сервер в окремому потоці
Thread(target=run_health_server, daemon=True).start()

# —————— Telegram-бот ——————
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# SQLite
conn = sqlite3.connect("bookings.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        comment TEXT
    )
''')
conn.commit()

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply(
        "Привіт! Це бот для бронювання альтанки 🏕️\n\n"
        "Команди:\n"
        "/book — забронювати альтанку\n"
        "/schedule — переглянути всі бронювання\n"
        "/admin — адмін-меню"
    )

@dp.message_handler(commands=["book"])
async def cmd_book(message: types.Message):
    await message.reply(
        "Введіть бронювання у форматі:\n"
        "`YYYY-MM-DD HH:MM HH:MM Коментар (опційно)`\n"
        "Наприклад:\n"
        "`2025-08-10 14:00 17:00 Зустріч з сім’єю`",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=["schedule"])
async def cmd_schedule(message: types.Message):
    c.execute(
        "SELECT id, date, start_time, end_time, username, comment "
        "FROM bookings ORDER BY date, start_time"
    )
    rows = c.fetchall()
    if not rows:
        await message.reply("Наразі немає жодного бронювання.")
        return
    lines = ["Графік бронювань:"]
    for bid, date, st, et, user, comment in rows:
        line = f"[{bid}] {date} {st}–{et} від @{user}"
        if comment:
            line += f" — {comment}"
        lines.append(line)
    await message.reply("\n".join(lines))

@dp.message_handler(lambda m: m.text and m.text.count(" ") >= 3)
async def handler_save(message: types.Message):
    parts = message.text.split(" ", 3)
    date_str, start_str, end_str = parts[0], parts[1], parts[2]
    comment = parts[3] if len(parts) > 3 else ""
    # Перевірка формату
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        datetime.strptime(start_str, "%H:%M")
        datetime.strptime(end_str, "%H:%M")
    except ValueError:
        return await message.reply("❌ Формат дати/часу невірний.")

    # Конфлікт
    c.execute("""
        SELECT COUNT(*) FROM bookings
         WHERE date=?
           AND ((start_time<=? AND end_time>?)
             OR (start_time<? AND end_time>=?))
    """, (date_str, start_str, start_str, end_str, end_str))
    if c.fetchone()[0] > 0:
        return await message.reply("⚠️ Цей час зайнятий.")

    username = message.from_user.username or str(message.from_user.id)
    c.execute(
        "INSERT INTO bookings(username, date, start_time, end_time, comment) VALUES(?,?,?,?,?)",
        (username, date_str, start_str, end_str, comment)
    )
    conn.commit()
    bid = c.lastrowid

    # Ручне .ics
    ics_file = f"booking_{bid}.ics"
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = f"{date_str.replace('-', '')}T{start_str.replace(':','')}00Z"
    dtend   = f"{date_str.replace('-', '')}T{end_str.replace(':','')}00Z"
    ics_text = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CityLake//GazeboBookingBot//EN",
        "BEGIN:VEVENT",
