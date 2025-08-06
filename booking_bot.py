# booking_bot.py

import logging
import sqlite3
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from ics import Calendar, Event

# ——————  ВСТАВТЕ СВІЙ ТОКЕН ТУТ  ——————
BOT_TOKEN = "8346638943:AAHY4JVG3jyoWMW33z3wvx_ltx9XmKOI-LQ"
ADMIN_USERNAME = "plo_anton"    # без @

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Підключення до SQLite
conn = sqlite3.connect("bookings.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        comment TEXT
    )
""")
conn.commit()


# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Це бот для бронювання альтанки 🏕️\n\n"
        "Команди:\n"
        "/book — забронювати альтанку\n"
        "/schedule — переглянути всі бронювання\n"
        "/admin — адміністративне меню"
    )


# /book
async def book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введіть бронювання у форматі:\n"
        "`YYYY-MM-DD HH:MM HH:MM Коментар (опційно)`\n"
        "Наприклад:\n"
        "`2025-08-10 14:00 17:00 Зустріч з сім’єю`",
        parse_mode="Markdown",
    )


# /schedule
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT id, date, start_time, end_time, username, comment FROM bookings ORDER BY date, start_time")
    rows = c.fetchall()
    if not rows:
        await update.message.reply_text("Наразі немає жодного бронювання.")
        return
    lines = ["Графік бронювань:"]
    for bid, date, st, et, user, comment in rows:
        line = f"[{bid}] {date} {st}–{et} від @{user}"
        if comment:
            line += f" — {comment}"
        lines.append(line)
    await update.message.reply_text("\n".join(lines))


# Save booking (обробка тексту)
async def save_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split(" ", 3)
    if len(parts) < 3:
        await update.message.reply_text("❌ Невірний формат. Спробуйте /book знову.")
        return

    date_str, start_str, end_str = parts[0], parts[1], parts[2]
    comment = parts[3] if len(parts) > 3 else ""

    # Перевірка формату
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        datetime.strptime(start_str, "%H:%M")
        datetime.strptime(end_str, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Формат дати/часу невірний. Спробуйте ще раз.")
        return

    # Перевірка конфліктів
    c.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE date=?
          AND ((start_time<=? AND end_time>?)
               OR (start_time<? AND end_time>=?))
    """, (date_str, start_str, start_str, end_str, end_str))
    if c.fetchone()[0] > 0:
        await update.message.reply_text("⚠️ Цей час зайнятий. Оберіть інший.")
        return

    username = update.message.from_user.username or str(update.message.from_user.id)
    c.execute("""
        INSERT INTO bookings(username, date, start_time, end_time, comment)
        VALUES(?,?,?,?,?)
    """, (username, date_str, start_str, end_str, comment))
    conn.commit()
    bid = c.lastrowid

    # Генерація .ics
    cal = Calendar()
    ev = Event()
    ev.name = "Бронювання альтанки"
    ev.begin = f"{date_str}T{start_str}:00"
    ev.end = f"{date_str}T{end_str}:00"
    ev.description = f"Користувач: @{username}\n{comment}"
    cal.events.add(ev)
    ics
