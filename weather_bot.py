import asyncio
import logging
import sys
import os
import aiohttp

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties

from keyboards import get_start_keyboard
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY") 


bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()



class WeatherForm(StatesGroup):
    waiting_for_city = State()



async def get_weather(city: str):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city, #місто
        "appid": WEATHER_API_KEY, #ключ
        "units": "metric", #одиниці вимірювання
        "lang": "ua" #мова
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                return "Не вдалося отримати дані про погоду. Спробуйте пізніше."

            data = await response.json()

            if data.get("cod") != 200:
                return f"Місто '{city}' не знайдено. Спробуйте іншу назву."

            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            description = data['weather'][0]['description']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']

            return (
                f"<b>Погода в місті {city.capitalize()}:</b>\n"
                f"🌡️ Температура: {temp}°C\n"
                f"🤔 Відчувається як: {feels_like}°C\n"
                f"📝 Опис: {description.capitalize()}\n"
                f"💧 Вологість: {humidity}%\n"
                f"💨 Швидкість вітру: {wind_speed} м/с"
            )


# --- Обробники (хендлери) ---

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обробник команди /start."""
    await message.answer(
        f"Привіт, <b>{message.from_user.full_name}</b>! Натисніть кнопку, щоб дізнатись погоду.",
        reply_markup=get_start_keyboard()
    )

@dp.callback_query(lambda c: c.data == 'get_weather_button')
async def process_weather_press(callback: CallbackQuery, state: FSMContext):
    """Обробник натискання на інлайн-кнопку 'Дізнатися погоду'."""
    await callback.answer()
    await callback.message.answer("Введіть назву міста:")
    await state.set_state(WeatherForm.waiting_for_city)

@dp.message(WeatherForm.waiting_for_city)
async def get_city_and_show_weather(message: Message, state: FSMContext):
    """Обробник, що ловить місто від користувача і показує погоду."""
    city = message.text
    weather_report = await get_weather(city)
    await message.answer(weather_report)
    await state.clear()


async def main() -> None:
    # Запускает процесс получения апдейтов от Telegram
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений.")
