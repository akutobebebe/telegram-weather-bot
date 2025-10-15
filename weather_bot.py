import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message
from keyboards import get_start_keyboard
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ==> ДОБАВЬТЕ ЭТОТ БЛОК ДЛЯ ПРОВЕРКИ <==
if not TOKEN:
    print("ОШИБКА: Токен не найден!")
    print("Проверьте, что у вас есть файл .env и в нём прописан BOT_TOKEN.")
    # Если токена нет, нет смысла продолжать
    exit()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart()) #цей дикоратор ловить команду старт 
async def command_start(message: Message):
    await message.answer(f"Привіт, <b>{message.from_user.full_name}</b>!",
    reply_markup=get_start_keyboard()
    )

    
async def main() -> None:
    # Запускает процесс получения апдейтов от Telegram
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений.")
