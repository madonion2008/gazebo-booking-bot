import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Налаштування ---
BOT_TOKEN = "8346638943:AAHY4JVG3jyoWMW33z3wvx_ltx9XmKOI-LQ"  # <-- Вставте сюди токен від BotFather

# Словник для зберігання бронювань. У реальному проекті це буде база даних.
# Формат: { "YYYY-MM-DD HH:MM": {"id": user_id, "name": user_name} }
bookings = {}

# --- ОСНОВНІ ФУНКЦІЇ ---

# Обробник команди /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Відправляє вітальне повідомлення з переліком команд."""
    await update.message.reply_text(
        "👋 Вітаю! Я допоможу вам забронювати альтанку.\n\n"
        "Доступні команди:\n"
        "/book - Забронювати альтанку\n"
        "/mybookings - Мої бронювання (тут можна скасувати)\n"
        "/view_bookings - Переглянути всі бронювання на дату"
    )

# Крок 1 бронювання: вибір дня
async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує кнопки для вибору дня бронювання (на 7 днів уперед)."""
    keyboard = []
    today = datetime.now()
    for i in range(7):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        button_text = day.strftime("%A, %d.%m") # Напр. "Середа, 06.08"
        callback_data = f"select_day_{date_str}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Будь ласка, оберіть день для бронювання:", reply_markup=reply_markup)

# Перегляд своїх бронювань
async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує активні бронювання користувача з можливістю скасування."""
    user_id = update.message.from_user.id
    user_active_bookings = []
    
    # Шукаємо всі бронювання цього користувача
    for slot, booking_info in bookings.items():
        if booking_info["id"] == user_id and datetime.strptime(slot, "%Y-%m-%d %H:%M") > datetime.now():
            user_active_bookings.append(slot)
    
    if not user_active_bookings:
        await update.message.reply_text("У вас немає активних бронювань.")
        return

    keyboard = []
    for slot in sorted(user_active_bookings):
        slot_dt = datetime.strptime(slot, "%Y-%m-%d %H:%M")
        button_text = f"❌ Скасувати {slot_dt.strftime('%d.%m о %H:%M')}"
        callback_data = f"cancel_{slot}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Ваші активні бронювання:", reply_markup=reply_markup)

# Перегляд усіх бронювань (для адміністратора)
async def view_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Крок 1: Просить обрати день для перегляду всіх бронювань."""
    keyboard = []
    today = datetime.now()
    for i in range(7):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        button_text = day.strftime("%A, %d.%m")
        callback_data = f"view_day_{date_str}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Оберіть день для перегляду бронювань:", reply_markup=reply_markup)


# --- ОБРОБНИК НАТИСКАННЯ НА КНОПКИ (Callback) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє всі натискання на inline-кнопки."""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    # --- Логіка вибору дня і показу слотів ---
    if data.startswith("select_day_"):
        date_str = data.split("_")[2]
        day = datetime.strptime(date_str, "%Y-%m-%d")
        
        keyboard = []
        # Генеруємо слоти з 10:00 до 21:00 для обраного дня
        for hour in range(10, 22):
            slot_dt = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_str = slot_dt.strftime("%Y-%m-%d %H:%M")
            
            # Показуємо тільки майбутні слоти
            if slot_dt > datetime.now():
                # Перевіряємо, чи слот вільний
                if slot_str not in bookings:
                    button_text = slot_dt.strftime("%H:%M")
                    callback_data = f"book_{slot_str}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        if not keyboard:
            await query.edit_message_text(text=f"На {day.strftime('%d.%m')} вільних слотів немає. 😔")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"Оберіть вільний час на {day.strftime('%d.%m')}:", reply_markup=reply_markup)

    # --- Логіка фінального бронювання ---
    elif data.startswith("book_"):
        slot_str = data.replace("book_", "")
        user_id = query.from_user.id
        user_name = query.from_user.full_name

        if slot_str in bookings:
            await query.edit_message_text(text=f"На жаль, цей час вже хтось встиг забронювати. 😥")
            return

        bookings[slot_str] = {"id": user_id, "name": user_name}
        booked_time = datetime.strptime(slot_str, "%Y-%m-%d %H:%M").strftime("%d.%m о %H:%M")
        await query.edit_message_text(text=f"✅ Чудово! Альтанку заброньовано на {booked_time}.")
        print(f"Нове бронювання: {slot_str} користувачем {user_name} ({user_id})")

    # --- Логіка скасування бронювання ---
    elif data.startswith("cancel_"):
        slot_to_cancel = data.replace("cancel_", "")
        
        # Перевіряємо, чи це дійсно бронювання цього користувача
        if slot_to_cancel in bookings and bookings[slot_to_cancel]["id"] == query.from_user.id:
            del bookings[slot_to_cancel]
            cancelled_time = datetime.strptime(slot_to_cancel, "%Y-%m-%d %H:%M").strftime("%d.%m о %H:%M")
            await query.edit_message_text(text=f"✅ Ваше бронювання на {cancelled_time} скасовано.")
            print(f"Скасовано бронювання: {slot_to_cancel}")
        else:
            await query.edit_message_text(text="Не вдалося скасувати бронювання. Можливо, воно вже неактуальне.")

    # --- Логіка перегляду всіх бронювань на день ---
    elif data.startswith("view_day_"):
        date_str = data.split("_")[2]
        
        day_bookings = []
        for slot, info in bookings.items():
            if slot.startswith(date_str):
                day_bookings.append((slot, info))
        
        if not day_bookings:
            await query.edit_message_text(text=f"На {datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m')} немає жодного бронювання.")
            return
            
        response_text = f"Бронювання на {datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')}:\n\n"
        for slot, info in sorted(day_bookings):
            time = datetime.strptime(slot, "%Y-%m-%d %H:%M").strftime("%H:%M")
            user_name = info.get('name', 'N/A')
            response_text += f"• {time} - {user_name}\n"
            
        await query.edit_message_text(text=response_text)


def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book))
    application.add_handler(CommandHandler("mybookings", my_bookings))
    application.add_handler(CommandHandler("view_bookings", view_bookings))
    
    # Додаємо обробник для всіх кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущений...")
    application.run_polling()

if __name__ == "__main__":
    main()