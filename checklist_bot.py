# -*- coding: utf-8 -*-
"""
Автономный Telegram-бот «Чек-лист по использованию ИИ».

Что умеет:
  • при /start отправляет анимацию (data-flow.mp4) и интерактивный чек-лист;
  • пункты отмечаются нажатием кнопок прямо в чате (✅ / ⬜);
  • показывает прогресс и сохраняет отметки для КАЖДОГО пользователя;
  • НЕ требует веб-хостинга — нужен только токен бота и Python.

Запуск:
    pip install -r requirements.txt
    export BOT_TOKEN="НОВЫЙ_ТОКЕН_ОТ_BOTFATHER"      # Windows: set BOT_TOKEN=...
    python checklist_bot.py

(опционально) export WEBAPP_URL="https://.../checklist-standalone.html"
    — тогда в чек-листе появится кнопка «Открыть красивую версию» (Mini App).

ВАЖНО: токен берётся из переменной окружения, в коде он НЕ хранится.
"""

import os
import json
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL")  # необязательно

if not BOT_TOKEN:
    raise SystemExit("Задайте переменную окружения BOT_TOKEN (токен от @BotFather).")

BASE = Path(__file__).resolve().parent
ANIM_FILE = BASE / "data-flow.mp4"
STATE_FILE = BASE / "state.json"

# ----------------------------------------------------------------------------
# Содержимое чек-листа: разделы и пункты (заголовок, пояснение)
# ----------------------------------------------------------------------------
SECTIONS = [
    ("🟢 Правильное использование ИИ", [
        ("Чётко формулирую цель", "понимаю, какой результат нужен"),
        ("Даю контекст", "кто я, для кого и зачем"),
        ("Проверяю факты и цифры", "сверяю с надёжными источниками"),
        ("Берегу конфиденциальность", "не ввожу пароли и личные данные"),
        ("Мыслю критически", "ответ — черновик, а не истина"),
        ("Использую ИИ как помощника", "решение оставляю за собой"),
        ("Дорабатываю итерациями", "улучшаю результат шаг за шагом"),
        ("Указываю участие ИИ", "там, где это важно"),
    ]),
    ("🟣 Анатомия сильного промпта", [
        ("Задал роль и экспертизу", "«Ты — эксперт в…»"),
        ("Описал задачу конкретно", "без размытых формулировок"),
        ("Добавил контекст и аудиторию", "для кого и в какой ситуации"),
        ("Задал формат и объём", "список, таблица, длина"),
        ("Привёл пример результата", "few-shot повышает точность"),
        ("Указал тон и стиль", "формальный, дружелюбный…"),
        ("Разбил задачу на шаги", "диалог вместо стены текста"),
    ]),
    ("🔴 Чего избегать (усвоено)", [
        ("Слепое доверие", "без проверки фактов"),
        ("Размытые запросы", "«сделай хорошо»"),
        ("Личные данные в чате", "пароли, документы"),
        ("Подмена экспертизы", "ответ ИИ как профессиональный"),
        ("Один огромный запрос", "вместо диалога"),
        ("Отказ от своего мышления", "перекладывать ответственность"),
    ]),
]

# Плоский список пунктов с устойчивыми id (1..N)
ITEMS = []  # list of (id, title, desc)
_id = 0
for _title, _items in SECTIONS:
    for _t, _d in _items:
        _id += 1
        ITEMS.append((_id, _t, _d))
TOTAL = len(ITEMS)

# ----------------------------------------------------------------------------
# Хранилище отметок (простой JSON-файл): { "user_id": [1, 4, 7, ...] }
# ----------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text("utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), "utf-8")
    except Exception:
        pass


STATE = load_state()


def checked_set(user_id: int) -> set:
    return set(STATE.get(str(user_id), []))


def store_checked(user_id: int, ids: set) -> None:
    STATE[str(user_id)] = sorted(ids)
    save_state(STATE)


# ----------------------------------------------------------------------------
# Отрисовка текста и клавиатуры
# ----------------------------------------------------------------------------
def progress_bar(done: int, total: int, width: int = 14) -> str:
    filled = round(width * done / total) if total else 0
    return "▰" * filled + "▱" * (width - filled)


def render_text(done_ids: set) -> str:
    done = len(done_ids)
    pct = round(done / TOTAL * 100) if TOTAL else 0
    lines = [
        "🧠 <b>Чек-лист по использованию ИИ</b>",
        f"Прогресс: <b>{done}/{TOTAL}</b> · {pct}%",
        progress_bar(done, TOTAL),
        "",
    ]
    n = 0
    for sec_title, sec_items in SECTIONS:
        lines.append(f"<b>{sec_title}</b>")
        for _t, _d in sec_items:
            n += 1
            mark = "✅" if n in done_ids else "⬜"
            lines.append(f"{mark} <b>{n}.</b> {_t} — <i>{_d}</i>")
        lines.append("")
    lines.append("Нажимай номера ниже, чтобы отмечать пункты 👇")
    return "\n".join(lines)


def render_keyboard(done_ids: set) -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, _t, _d in ITEMS:
        mark = "✅" if i in done_ids else f"{i}"
        row.append(InlineKeyboardButton(mark, callback_data=f"t:{i}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    controls = [InlineKeyboardButton("🔄 Сбросить", callback_data="reset"),
                InlineKeyboardButton("🎬 Анимация", callback_data="anim")]
    rows.append(controls)

    if WEBAPP_URL:
        rows.append([InlineKeyboardButton("🌐 Открыть красивую версию",
                                          web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(rows)


# ----------------------------------------------------------------------------
# Хендлеры
# ----------------------------------------------------------------------------
async def send_animation(chat, context) -> None:
    if ANIM_FILE.exists():
        try:
            with open(ANIM_FILE, "rb") as f:
                await context.bot.send_animation(chat_id=chat.id, animation=f)
        except Exception:
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    done_ids = checked_set(user_id)
    await send_animation(update.effective_chat, context)
    await update.message.reply_text(
        render_text(done_ids),
        reply_markup=render_keyboard(done_ids),
        parse_mode=ParseMode.HTML,
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    done_ids = checked_set(user_id)

    if data == "anim":
        await query.answer("Отправил анимацию ⬆️")
        await send_animation(query.message.chat, context)
        return

    if data == "reset":
        done_ids = set()
        await query.answer("Сброшено")
    elif data.startswith("t:"):
        i = int(data[2:])
        if i in done_ids:
            done_ids.remove(i)
        else:
            done_ids.add(i)
        if len(done_ids) == TOTAL:
            await query.answer("Готово! Все пункты отмечены 🎉")
        else:
            await query.answer()
    else:
        await query.answer()
        return

    store_checked(user_id, done_ids)
    try:
        await query.edit_message_text(
            render_text(done_ids),
            reply_markup=render_keyboard(done_ids),
            parse_mode=ParseMode.HTML,
        )
    except BadRequest:
        pass  # сообщение не изменилось — игнорируем


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды:\n/start — показать чек-лист и анимацию\n"
        "Отметки сохраняются автоматически для каждого пользователя."
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    print("Бот запущен. Откройте его в Telegram и отправьте /start")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
