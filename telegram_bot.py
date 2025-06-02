import telebot
import sqlite3
import base64
from io import BytesIO
from telebot import types
from datetime import datetime

TOKEN = '8179859032:AAFNqIcy7HKUK7xWg6b-NO3Y3mkz5cVkLo4'
bot = telebot.TeleBot(TOKEN)

DB_PATH = 'detections.db'

# Стартовое сообщение
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Начать"))
    bot.send_message(message.chat.id, "Нажмите 'Начать' для просмотра детекций.", reply_markup=markup)

# Обработка кнопки "Начать"
@bot.message_handler(func=lambda message: message.text == "Начать")
def choose_date(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT date(detection_datetime) FROM detections")
    dates = cursor.fetchall()
    conn.close()

    if dates:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for date in dates:
            markup.add(types.KeyboardButton(date[0]))
        bot.send_message(message.chat.id, "Выберите день, за который хотите проверить детекции:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Нет доступных детекций в базе данных.")

# Выбор даты и отображение результатов
@bot.message_handler(func=lambda message: validate_date(message.text))
def show_detections(message):
    selected_date = message.text
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, detected_class, confidence 
        FROM detections 
        WHERE date(detection_datetime) = ?
    """, (selected_date,))
    
    detections = cursor.fetchall()
    conn.close()

    if detections:
        response = f"📅 Детекции за {selected_date}:\n\n"
        for det in detections:
            response += f"🔸 {det[1]} — {det[2]*100:.2f}% (ID записи: {det[0]})\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Вывести изображения детекций", callback_data=f"image|{selected_date}"))
        markup.add(types.InlineKeyboardButton("Начать с начала", callback_data="restart"))

        bot.send_message(message.chat.id, response, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "За выбранную дату детекций нет.")

# Проверка формата даты
def validate_date(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Обработка callback-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("image|"):
        selected_date = call.data.split("|")[1]
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Получаем все изображения за выбранную дату
        cursor.execute("""
            SELECT image_base64 FROM detections 
            WHERE date(detection_datetime) = ? AND image_base64 IS NOT NULL
        """, (selected_date,))

        images = cursor.fetchall()
        conn.close()

        if images:
            # Используем множество для хранения уникальных изображений
            unique_images = set()
            
            for img_str in images:
                if img_str[0]:  # Если изображение сохранено
                    # Добавляем в множество (дубликаты будут автоматически удалены)
                    unique_images.add(img_str[0])
            
            # Отправляем только уникальные изображения
            for img_str in unique_images:
                try:
                    img_bytes = base64.b64decode(img_str)
                    bot.send_photo(call.message.chat.id, photo=BytesIO(img_bytes))
                except Exception as e:
                    print(f"Ошибка при отправке изображения: {e}")
                    continue
            
            bot.send_message(call.message.chat.id, f"Отправлено {len(unique_images)} уникальных изображений.")
        else:
            bot.send_message(call.message.chat.id, "Изображений за выбранную дату нет.")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Начать с начала", callback_data="restart"))
        bot.send_message(call.message.chat.id, "✅ Готово!", reply_markup=markup)

    elif call.data == "restart":
        start(call.message)

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
