#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pc-diag Telegram bot (long polling, без внешних зависимостей).
Токен берётся из переменной окружения TELEGRAM_BOT_TOKEN
или из файла <проект>/.dev.vars строкой: TELEGRAM_BOT_TOKEN=123:AA...
Запуск: python bot/pc_diag_bot.py
"""
import os
import sys
import json
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
TOKEN_FILE = os.path.join(PROJECT_DIR, ".dev.vars")

LINKS = {
    "site": "https://pc-diag.ru/",
    "download": "https://github.com/progerman666/pc-diag/releases/latest",
    "vk": "https://vk.ru/club243150004",
    "tg": "https://t.me/remont_teh_ru",
    "github": "https://github.com/progerman666/pc-diag",
}

WELCOME = (
    "👋 Привет! Это бот <b>pc-diag</b> — бесплатной диагностики Windows.\n\n"
    "За 60 секунд покажет:\n"
    "• здоровье дисков и износ SSD (SMART)\n"
    "• ошибки Event Log за 24 часа\n"
    "• сеть: шлюз, DNS, пинг и потери пакетов\n"
    "• службы, автозагрузку и «прожорливые» процессы\n\n"
    "Скачай и проверь свой ПК:"
)

KEYBOARD = {
    "inline_keyboard": [
        [{"text": "⬇️ Скачать pc-diag", "url": LINKS["download"]}],
        [
            {"text": "🌐 Сайт", "url": LINKS["site"]},
            {"text": "💬 VK", "url": LINKS["vk"]},
        ],
        [{"text": "📣 Telegram-канал", "url": LINKS["tg"]}],
    ]
}

token = None


def load_token():
    env = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env and env.strip():
        return env.strip()
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip()
    return None


def api(method, payload):
    url = "https://api.telegram.org/bot%s/%s" % (token, method)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    return api("sendMessage", payload)


def main():
    global token
    token = load_token()
    if not token:
        print("TELEGRAM_BOT_TOKEN не найден (env или .dev.vars)")
        sys.exit(1)
    print("pc-diag bot запущен. Ctrl+C для остановки.")
    offset = 0
    while True:
        try:
            res = api("getUpdates", {"offset": offset, "timeout": 30})
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = (msg.get("text") or "").strip().lower()
                if text.startswith("/start") or text.startswith("/help"):
                    send(chat_id, WELCOME, KEYBOARD)
                elif text.startswith("/download"):
                    send(
                        chat_id,
                        "⬇️ Скачать pc-diag:",
                        {
                            "inline_keyboard": [
                                [{"text": "Скачать (GitHub)", "url": LINKS["download"]}]
                            ]
                        },
                    )
                elif text:
                    send(chat_id, "Нажми /start, чтобы получить ссылки 👇", KEYBOARD)
        except KeyboardInterrupt:
            print("Остановлен.")
            break
        except Exception as exc:  # noqa: BLE001
            print("error:", exc)
            time.sleep(3)


if __name__ == "__main__":
    main()
