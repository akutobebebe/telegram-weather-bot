from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_start_keyboard()-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Погода в місті",
        callback_data="get_weather_button"
    )

    return builder.as_markup()
