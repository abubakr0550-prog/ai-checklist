# -*- coding: utf-8 -*-
"""
Телеграм-бот, который открывает чек-лист «Использование ИИ» как Telegram Mini App.

Запуск:
    pip install -r requirements.txt
    export BOT_TOKEN="<новый токен из @BotFather>"      # Windows: set BOT_TOKEN=...
    export WEBAPP_URL="https://ваш-домен/checklist-standalone.html"
    python bot.py

ВАЖНО: токен НЕ хранится в коде — он читается из переменной окружения.
URL обязательно должен быть HTTPS (требование Telegram для Mini Apps).
"""

import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonWebApp,
)
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")  # https://.../checklist-standalone.html

if not BOT_TOKEN or not WEBAPP_URL:
    raise SystemExit(
        "Задайте переменные окружения BOT_TOKEN и WEBAPP_URL перед запуском."
    )

WELCOME = (
    "🧠 <b>Чек-лист по использованию ИИ</b>\n\n"
    "Правильная работа с ИИ и создание промптов: в чём уникальность технологии, "
    "привычки осознанного пользователя, анатомия сильного промпта и частые ошибки.\n\n"
    "Нажми кнопку ниже, чтобы открыть интерактивный чек-лист 👇"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Открыть чек-лист", web_app=WebAppInfo(url=WEBAPP_URL))]]
    )
    await update.message.reply_text(WELCOME, reply_markup=keyboard, parse_mode="HTML")


async def post_init(app: Application) -> None:
    # Постоянная кнопка «Чек-лист» рядом с полем ввода сообщения
    await app.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Чек-лист", web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )


def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    print("Бот запущен. Откройте его в Telegram и отправьте /start")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
