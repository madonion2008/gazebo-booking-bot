import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputFile
from ics import Calendar, Event
from config import BOT_TOKEN, ADMIN_USERNAME

# Логування
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Підключення до SQLite
conn = sqlite3.connect('bookings.db')
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

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply(
        "Привіт! Це бот для бронювання альтанки 🏕️\n\n"
        "Команди:\n"
        "/book — забронювати альтанку\n"
        "/schedule — переглянути всі бронювання\n"
        "/admin — адмін-меню"
    )

@dp.message_handler(commands=['book'])
async def cmd_book(message: types.Message):
    await message.reply(
        "Введіть бронювання у форматі:\n"
        "`YYYY-MM-DD HH:MM HH:MM Коментар (опційно)`\n"
        "Наприклад:\n"
        "`2025-08-10 14:00 17:00 Зустріч з сім’єю`",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['schedule'])
async def cmd_schedule(message: types.Message):
    c.execute("SELECT id, date, start_time, end_time, username, comment FROM bookings ORDER BY date, start_time")
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

@dp.message_handler(lambda m: m.text and m.text.count(' ') >= 3)
async def handler_save(message: types.Message):
    parts = message.text.split(' ', 3)
    date_str, start_str, end_str = parts[0], parts[1], parts[2]
    comment = parts[3] if len(parts) > 3 else ''
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        datetime.strptime(start_str, '%H:%M')
        datetime.strptime(end_str, '%H:%M')
    except ValueError:
        await message.reply("❌ Формат дати/часу невірний.")
        return

    # Перевірка конфлікту
    c.execute("""
        SELECT COUNT(*) FROM bookings
        WHERE date=?
          AND ((start_time<=? AND end_time>?)
            OR (start_time<? AND end_time>=?))
    """, (date_str, start_str, start_str, end_str, end_str))
    if c.fetchone()[0] > 0:
        await message.reply("⚠️ Цей час зайнятий.")
        return

    username = message.from_user.username or str(message.from_user.id)
    c.execute("INSERT INTO bookings(username, date, start_time, end_time, comment) VALUES(?,?,?,?,?)",
              (username, date_str, start_str, end_str, comment))
    conn.commit()
    bid = c.lastrowid

    # Генерація .ics
    cal = Calendar()
    ev = Event()
    ev.name = "Бронювання альтанки"
    ev.begin = f"{date_str}T{start_str}:00"
    ev.end = f"{date_str}T{end_str}:00"
    ev.description = f"@{username}\n{comment}"
    cal.events.add(ev)
    ics_file = f"booking_{bid}.ics"
    with open(ics_file, 'w', encoding='utf-8') as f:
        f.writelines(cal)

    await message.reply(f"✅ Ваше бронювання #{bid} збережено!")
    await message.reply_document(InputFile(ics_file))

@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        return await message.reply("🚫 Доступ заборонено.")
    await message.reply(
        "Адмін-команди:\n"
        "/schedule — переглянути всі бронювання\n"
        "/delete <id> — видалити бронювання"
    )

@dp.message_handler(lambda m: m.text and m.text.startswith('/delete '))
async def cmd_delete(message: types.Message):
    if message.from_user.username != ADMIN_USERNAME:
        return await message.reply("🚫 Доступ заборонено.")
    try:
        bid = int(message.text.split()[1])
    except:
        return await message.reply("❌ Використання: /delete <id>")
    c.execute("DELETE FROM bookings WHERE id=?", (bid,))
    if c.rowcount == 0:
        await message.reply(f"❌ Бронювання #{bid} не знайдено.")
    else:
        conn.commit()
        await message.reply(f"✅ Бронювання #{bid} видалено.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
