from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton

def get_start_keyboard() -> ReplyKeyboardMarkup:
    """Головне меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🌤️ Дізнатися погоду")
    builder.button(text="⭐ Улюблені міста")
    builder.button(text="📚 Допомога")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура з кнопкою 'Назад'"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="⬅️ Назад")
    return builder.as_markup(resize_keyboard=True)

def get_favorites_keyboard(cities: list) -> InlineKeyboardMarkup:
    """Створює inline клавіатуру з улюбленими містами"""
    builder = InlineKeyboardBuilder()
    
    # Додаємо кнопки для кожного міста
    for city in cities:
        builder.button(
            text=f"📍 {city.capitalize()}", 
            callback_data=f"fav_{city}"
        )
    
    # Розташовуємо по 2 кнопки в ряду
    builder.adjust(2)
    
    return builder.as_markup()