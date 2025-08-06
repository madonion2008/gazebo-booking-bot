import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Налаштування ---
BOT_TOKEN = "8346638943:AAHY4JVG3jyoWMW33z3wvx_ltx9XmKOI-LQ"  # <-- Вставте сюди токен від BotFather

# Створюємо словник для зберігання бронювань. У реальному проекті це буде база даних.
# Формат: { "YYYY-MM-DD HH:MM": user_id }
bookings = {}

# --- Логіка бота ---

# Функція для генерації вільних слотів на сьогодні
def get_available_slots():
    """Повертає список вільних слотів на сьогодні."""
    slots = []
    now = datetime.now()
    # Генеруємо слоти, наприклад, з 10:00 до 21:00
    for hour in range(10, 22):
        slot_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        # Показуємо слоти, які ще не пройшли
        if slot_time > now:
            slots.append(slot_time.strftime("%Y-%m-%d %H:%M"))
    return slots

# Обробник команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє вітальне повідомлення."""
    await update.message.reply_text(
        "👋 Вітаю! Я допоможу вам забронювати альтанку.\n\n"
        "Доступні команди:\n"
        "/book - Переглянути вільні слоти та забронювати\n"
        "/mybookings - Перевірити ваші бронювання"
    )

# Обробник команди /book
async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує вільні слоти у вигляді кнопок."""
    available_slots = get_available_slots()
    
    keyboard = []
    for slot in available_slots:
        # Перевіряємо, чи слот не зайнятий
        if slot not in bookings:
            # Текст кнопки: "15:00", дані, що відправляться: "book_2025-08-06 15:00"
            button_text = datetime.strptime(slot, "%Y-%m-%d %H:%M").strftime("%H:%M")
            callback_data = f"book_{slot}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    if not keyboard:
        await update.message.reply_text("На жаль, на сьогодні вільних слотів немає. 😔")
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Оберіть вільний час для бронювання:", reply_markup=reply_markup)

# Обробник натискання на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє натискання на inline-кнопки."""
    query = update.callback_query
    await query.answer() # Обов'язково відповідаємо на запит

    # Розбираємо дані, що прийшли з кнопки. Наприклад, "book_2025-08-06 15:00"
    action, value = query.data.split("_", 1)

    if action == "book":
        user_id = query.from_user.id
        user_name = query.from_user.full_name

        # Перевіряємо ще раз, раптом хтось забронював, поки ви обирали
        if value in bookings:
            await query.edit_message_text(text=f"На жаль, час {value} вже хтось встиг забронювати. 😥")
            return

        # Записуємо бронювання
        bookings[value] = {"id": user_id, "name": user_name}
        booked_time = datetime.strptime(value, "%Y-%m-%d %H:%M").strftime("%d.%m о %H:%M")
        await query.edit_message_text(text=f"✅ Чудово! Альтанку заброньовано на {booked_time}.")
        print(f"Нове бронювання: {value} користувачем {user_name} ({user_id})") # для логів

# Обробник команди /mybookings
async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує активні бронювання користувача."""
    user_id = update.message.from_user.id
    user_active_bookings = []
    for slot, booking_info in bookings.items():
        if booking_info["id"] == user_id:
            # Показуємо лише актуальні бронювання
            if datetime.strptime(slot, "%Y-%m-%d %H:%M") > datetime.now():
                user_active_bookings.append(slot)
    
    if not user_active_bookings:
        await update.message.reply_text("У вас немає активних бронювань.")
    else:
        bookings_text = "Ваші активні бронювання:\n"
        for slot in sorted(user_active_bookings):
            bookings_text += f"- {datetime.strptime(slot, '%Y-%m-%d %H:%M').strftime('%d.%m.%Y о %H:%M')}\n"
        await update.message.reply_text(bookings_text)


def main() -> None:
    """Запуск бота."""
    # Створюємо додаток та передаємо йому токен
    application = Application.builder().token(BOT_TOKEN).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CommandHandler("mybookings", my_bookings))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаємо бота
    print("Бот запущений...")
    application.run_polling()

if __name__ == "__main__":
    main()