import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, MessageReactionHandler, ContextTypes, filters
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Преобразуем в число

# Определяем путь для сохранения аудио
AUDIO_FOLDER = "static/audio"
# Создаём папку если её нет
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# В начале файла добавим отладочный вывод
print(f"ADMIN_ID type: {type(ADMIN_ID)}, value: {ADMIN_ID}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для сбора голосовых сообщений. Отправь мне голосовое сообщение длительностью до 10 секунд."
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    voice = update.message.voice
    user = update.message.from_user
    
    print(f"Получено голосовое от: {user.first_name} (ID: {user.id})")
    print(f"Длительность: {voice.duration} секунд")
    
    if voice.duration > 10:
        await update.message.reply_text(
            "Извините, но голосовое сообщение должно быть не длиннее 10 секунд!"
        )
        return
    
    try:
        # Скачиваем файл
        file = await context.bot.get_file(voice.file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{AUDIO_FOLDER}/voice_{timestamp}.ogg"
        await file.download_to_drive(filename)
        print(f"Голосовое сообщение сохранено как: {filename}")

        # Отправляем файл админу как новое голосовое
        if user.id != ADMIN_ID:
            print(f"Отправляю сообщение админу (ID: {ADMIN_ID})")
            # Пробуем отправить напрямую через file_id
            await context.bot.send_voice(
                chat_id=ADMIN_ID,
                voice=voice.file_id,  # Используем оригинальный file_id вместо файла
                caption=f"От: {user.first_name} (@{user.username})"
            )
            print("Сообщение успешно отправлено")
    
    except Exception as e:
        print(f"Ошибка при обработке сообщения: {e}")
        print(f"Тип ошибки: {type(e)}")
        print(f"File ID: {voice.file_id}")  # Добавим вывод file_id для отладки
        await update.message.reply_text("Произошла ошибка при обработке сообщения.")
        return
    
    await update.message.reply_text("Спасибо! Ваше голосовое сообщение принято.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.message.from_user
    text = update.message.text
    
    print(f"Получено текстовое от: {user.first_name} (ID: {user.id})")
    print(f"Текст: {text}")
    
    try:
        if user.id != ADMIN_ID:
            print(f"Пересылаю сообщение админу (ID: {ADMIN_ID})")
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
    except Exception as e:
        print(f"Ошибка при пересылке текста: {e}")
        print(f"Тип ошибки: {type(e)}")
    
    await update.message.reply_text("Сообщение получено!")

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик реакций на сообщения"""
    try:
        reaction = update.message_reaction
        chat_id = reaction.chat.id
        message_id = reaction.message_id
        
        # Проверяем, что это лайк 👍
        if "👍" not in reaction.new_reaction:
            return
            
        # Получаем информацию о сообщении
        message = await context.bot.get_message(
            chat_id=chat_id,
            message_id=message_id
        )
        
        # Проверяем, что это голосовое сообщение
        if not hasattr(message, 'voice'):
            return
            
        # Считаем количество лайков
        likes_count = sum(1 for reaction in message.reactions if "👍" in reaction.emoji)
        print(f"Голосовое сообщение получило лайк! Всего лайков: {likes_count}")
        
        # Если набралось 30 лайков
        if likes_count == 30:
            print("Набрано 30 лайков! Отправляю голосовое админу...")
            # Пересылаем сообщение админу
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=chat_id,
                message_id=message_id
            )
            
    except Exception as e:
        print(f"Ошибка при обработке реакции: {e}")

def main():
    """Запуск бота"""
    # Настраиваем получение обновлений о реакциях
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .arbitrary_callback_data(True)
        .get_updates_http_version("1.1")
        .http_version("1.1")
        .build()
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageReactionHandler(handle_reaction))
    
    print("Бот запущен...")
    print("Ожидаю реакции на сообщения...")
    application.run_polling(allowed_updates=["message", "message_reaction"])

if __name__ == '__main__':
    main()
