# Виходимо від офіційного образу Python 3.11
FROM python:3.11-slim

# Створюємо робочу теку
WORKDIR /app

# Копіюємо файли проєкту
COPY . .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Змінні середовища
ENV BOT_TOKEN=${BOT_TOKEN}
ENV ADMIN_USERNAME=${ADMIN_USERNAME}

# Запускаємо бота
CMD ["python", "main.py"]
