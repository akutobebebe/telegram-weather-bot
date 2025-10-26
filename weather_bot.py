import asyncio
import logging
import sys
import os
import aiohttp
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from keyboards import get_start_keyboard, get_favorites_keyboard, get_back_keyboard

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==================== БАЗА ДАНИХ ====================
def init_db():
    """Ініціалізація бази даних"""
    conn = sqlite3.connect('weather_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            city_name TEXT NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, city_name)
        )
    ''')
    conn.commit()
    conn.close()

def add_favorite_city(user_id: int, city_name: str) -> bool:
    """Додає місто до улюблених"""
    try:
        conn = sqlite3.connect('weather_bot.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO favorites (user_id, city_name) VALUES (?, ?)',
            (user_id, city_name.lower())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Місто вже є в улюблених

def remove_favorite_city(user_id: int, city_name: str) -> bool:
    """Видаляє місто з улюблених"""
    conn = sqlite3.connect('weather_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM favorites WHERE user_id = ? AND city_name = ?',
        (user_id, city_name.lower())
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_favorite_cities(user_id: int) -> list:
    """Отримує список улюблених міст користувача"""
    conn = sqlite3.connect('weather_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT city_name FROM favorites WHERE user_id = ? ORDER BY added_date DESC',
        (user_id,)
    )
    cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cities

def is_favorite(user_id: int, city_name: str) -> bool:
    """Перевіряє, чи місто в улюблених"""
    conn = sqlite3.connect('weather_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT COUNT(*) FROM favorites WHERE user_id = ? AND city_name = ?',
        (user_id, city_name.lower())
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# ==================== FSM СТАНИ ====================
class WeatherForm(StatesGroup):
    waiting_for_city = State()
    waiting_for_favorite_action = State()

# ==================== ПОГОДНІ ФУНКЦІЇ ====================
def get_weather_emoji(weather_id: int) -> str:
    """Повертає емодзі відповідно до коду погоди"""
    if 200 <= weather_id < 300:
        return "⛈️"
    elif 300 <= weather_id < 600:
        return "🌧️"
    elif 600 <= weather_id < 700:
        return "❄️"
    elif weather_id == 800:
        return "☀️"
    elif 801 <= weather_id < 900:
        return "☁️"
    else:
        return "🌤️"

async def get_weather(city: str, user_id: int = None):
    """Отримує погоду для міста"""
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "ua"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return "❌ Не вдалося отримати дані про погоду. Спробуйте пізніше."
                
                data = await response.json()
                
                if data.get("cod") != 200:
                    return f"❌ Місто '{city}' не знайдено. Спробуйте іншу назву."
                
                temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                description = data['weather'][0]['description']
                humidity = data['main']['humidity']
                wind_speed = data['wind']['speed']
                weather_id = data['weather'][0]['id']
                emoji = get_weather_emoji(weather_id)
                
                # Перевірка чи місто в улюблених
                is_fav = is_favorite(user_id, city) if user_id else False
                fav_status = "⭐ В улюблених" if is_fav else ""
                
                return (
                    f"{emoji} <b>Погода в місті {city.capitalize()}</b> {fav_status}\n\n"
                    f"🌡️ Температура: <b>{temp}°C</b>\n"
                    f"🤔 Відчувається як: <b>{feels_like}°C</b>\n"
                    f"📝 Опис: {description.capitalize()}\n"
                    f"💧 Вологість: {humidity}%\n"
                    f"💨 Швидкість вітру: {wind_speed} м/с"
                )
    except aiohttp.ClientError:
        return "❌ Помилка з'єднання. Перевірте інтернет-з'єднання."
    except Exception as e:
        logging.error(f"Помилка при отриманні погоди: {e}")
        return "❌ Виникла несподівана помилка. Спробуйте пізніше."

# ==================== ОБРОБНИКИ ====================
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обробник команди /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    logging.info(f"Користувач {user_id} (@{username}) запустив бота")
    
    await message.answer(
        f"Привіт, <b>{message.from_user.full_name}</b>! 👋\n\n"
        f"Я допоможу дізнатися погоду в будь-якому місті світу.\n"
        f"Ви можете додавати міста до улюблених для швидкого доступу! ⭐",
        reply_markup=get_start_keyboard()
    )

@dp.message(F.text == "🌤️ Дізнатися погоду")
async def get_weather_handler(message: Message, state: FSMContext):
    """Початок процесу отримання погоди"""
    await message.answer(
        "🏙️ <b>Введіть назву міста:</b>\n\n"
        "Наприклад: Київ, Львів, London, Paris",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(WeatherForm.waiting_for_city)

@dp.message(F.text == "⭐ Улюблені міста")
async def show_favorites_handler(message: Message):
    """Показує список улюблених міст"""
    user_id = message.from_user.id
    cities = get_favorite_cities(user_id)
    
    if not cities:
        await message.answer(
            "📭 <b>У вас поки немає улюблених міст</b>\n\n"
            "Щоб додати місто до улюблених:\n"
            "1. Дізнайтеся погоду в місті\n"
            "2. Натисніть кнопку '⭐ Додати до улюблених'",
            reply_markup=get_start_keyboard()
        )
        return
    
    keyboard = get_favorites_keyboard(cities)
    
    cities_list = "\n".join([f"⭐ {city.capitalize()}" for city in cities])
    await message.answer(
        f"<b>📌 Ваші улюблені міста ({len(cities)}):</b>\n\n"
        f"{cities_list}\n\n"
        f"Натисніть на місто, щоб подивитися погоду:",
        reply_markup=keyboard
    )

@dp.message(F.text == "📚 Допомога")
async def help_handler(message: Message):
    """Показує довідку"""
    await message.answer(
        "<b>📚 Як користуватися ботом:</b>\n\n"
        "🌤️ <b>Дізнатися погоду</b> - введіть назву міста\n\n"
        "⭐ <b>Улюблені міста</b> - зберігайте улюблені міста для швидкого доступу\n\n"
        "💡 <b>Підказка:</b> Після перегляду погоди ви можете додати місто до улюблених!",
        reply_markup=get_start_keyboard()
    )

@dp.message(F.text == "⬅️ Назад")
async def go_back_to_main_menu(message: Message, state: FSMContext):
    """Повернення в головне меню"""
    await state.clear()
    await message.answer(
        "🏠 Ви в головному меню",
        reply_markup=get_start_keyboard()
    )

@dp.message(WeatherForm.waiting_for_city)
async def get_city_and_show_weather(message: Message, state: FSMContext):
    """Обробник міста від користувача"""
    city = message.text.strip()
    
    # Валідація
    if not city or len(city) < 2:
        await message.answer("❌ Введіть коректну назву міста (мінімум 2 символи)")
        return
    
    if len(city) > 50:
        await message.answer("❌ Назва міста занадто довга")
        return
    
    # Отримуємо погоду
    user_id = message.from_user.id
    weather_report = await get_weather(city, user_id)
    
    # Перевіряємо чи місто знайдено
    if "не знайдено" in weather_report.lower():
        await message.answer(weather_report, reply_markup=get_back_keyboard())
        return
    
    await message.answer(weather_report)
    
    # Пропонуємо додати до улюблених
    is_fav = is_favorite(user_id, city)
    
    if is_fav:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🗑️ Видалити з улюблених")],
                [types.KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Це місто вже в ваших улюблених! ⭐",
            reply_markup=keyboard
        )
    else:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="⭐ Додати до улюблених")],
                [types.KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Хочете додати це місто до улюблених?",
            reply_markup=keyboard
        )
    
    # Зберігаємо місто в стані
    await state.update_data(current_city=city)
    await state.set_state(WeatherForm.waiting_for_favorite_action)

@dp.message(WeatherForm.waiting_for_favorite_action, F.text == "⭐ Додати до улюблених")
async def add_to_favorites_handler(message: Message, state: FSMContext):
    """Додає місто до улюблених"""
    data = await state.get_data()
    city = data.get('current_city')
    user_id = message.from_user.id
    
    if add_favorite_city(user_id, city):
        await message.answer(
            f"✅ Місто <b>{city.capitalize()}</b> додано до улюблених! ⭐",
            reply_markup=get_start_keyboard()
        )
    else:
        await message.answer(
            f"ℹ️ Місто <b>{city.capitalize()}</b> вже є в улюблених!",
            reply_markup=get_start_keyboard()
        )
    
    await state.clear()

@dp.message(WeatherForm.waiting_for_favorite_action, F.text == "🗑️ Видалити з улюблених")
async def remove_from_favorites_handler(message: Message, state: FSMContext):
    """Видаляє місто з улюблених"""
    data = await state.get_data()
    city = data.get('current_city')
    user_id = message.from_user.id
    
    if remove_favorite_city(user_id, city):
        await message.answer(
            f"🗑️ Місто <b>{city.capitalize()}</b> видалено з улюблених",
            reply_markup=get_start_keyboard()
        )
    else:
        await message.answer(
            f"❌ Не вдалося видалити місто",
            reply_markup=get_start_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("fav_"))
async def favorite_city_callback(callback: CallbackQuery):
    """Обробник натискання на улюблене місто"""
    city = callback.data.replace("fav_", "")
    user_id = callback.from_user.id
    
    await callback.answer()
    
    weather_report = await get_weather(city, user_id)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🗑️ Видалити з улюблених", callback_data=f"remove_{city}")],
        [types.InlineKeyboardButton(text="🔄 Оновити", callback_data=f"fav_{city}")]
    ])
    
    await callback.message.answer(weather_report, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("remove_"))
async def remove_favorite_callback(callback: CallbackQuery):
    """Видаляє місто з улюблених через callback"""
    city = callback.data.replace("remove_", "")
    user_id = callback.from_user.id
    
    if remove_favorite_city(user_id, city):
        await callback.answer(f"✅ {city.capitalize()} видалено!", show_alert=True)
        
        # Оновлюємо список
        cities = get_favorite_cities(user_id)
        if cities:
            keyboard = get_favorites_keyboard(cities)
            cities_list = "\n".join([f"⭐ {c.capitalize()}" for c in cities])
            await callback.message.edit_text(
                f"<b>📌 Ваші улюблені міста ({len(cities)}):</b>\n\n"
                f"{cities_list}\n\n"
                f"Натисніть на місто, щоб подивитися погоду:",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text("📭 У вас більше немає улюблених міст")
    else:
        await callback.answer("❌ Помилка", show_alert=True)

# ==================== ЗАПУСК БОТА ====================
async def main() -> None:
    """Головна функція запуску бота"""
    init_db()
    logging.info("База даних ініціалізована")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот вимкнений.")