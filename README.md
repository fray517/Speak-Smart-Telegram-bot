# SpeakSmart — Telegram-бот (MVP)

## Возможности

- **Practice**: бот присылает голосовую фразу (prompt), пользователь отвечает голосом,
  бот распознаёт (Whisper) и даёт фидбек по ключевым словам.
- **Support**: бот отвечает из `data/faq.json`, иначе создаёт тикет и уведомляет оператора.
- **Operator relay**: оператор отвечает **reply** на сообщение бота — ответ уходит пользователю.
- **Закрытие тикета**: команда `/close 123` или кнопка **«Закрыть тикет»**.
- **Хранение истории**: SQLite (`data/speaksMart.sqlite3`) + лог в `data/logs/app.log`.

## Требования

- Windows 10/11
- Python **3.11+** (подойдёт и 3.10+, но проект сейчас тестировался на 3.11)
- Telegram Bot Token
- `ffmpeg.exe` (явный путь в `FFMPEG_PATH`)

## Установка и запуск (PowerShell)

```powershell
cd "C:\Users\feden\My_Project\zerocoder\Speak-Smart-Telegram-bot"

# 1) venv
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# 2) зависимости
python -m pip install --upgrade pip
pip install -r .\requirements.txt

# 3) env
Copy-Item .\env.example .\.env
notepad .\.env

# 4) запуск
python .\main.py
```

## Настройка .env

Файл `.env` нужно создать из `env.example`. Важные переменные:

- **`BOT_TOKEN`**: токен Telegram-бота.
- **`OPERATOR_ID`**: `user_id` оператора (число).
  Узнать можно командой `/myid` у бота.
- **`FFMPEG_PATH`**: полный путь до `ffmpeg.exe`.
  Проверка:

```powershell
& "C:\Path\To\ffmpeg\bin\ffmpeg.exe" -version
```

## Whisper (распознавание)

Проект поддерживает `faster-whisper` или `openai-whisper`. Рекомендуется `faster-whisper`.

```powershell
.\venv\Scripts\python.exe -m pip install faster-whisper
```

На Windows используется CPU-режим (без CUDA).

## Генерация voice prompts (20 фраз)

Скрипт генерирует `assets/phrases/en/001.ogg ... 020.ogg` на основе
`assets/practice_sets.json`.

```powershell
.\venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\venv\Scripts\python.exe .\scripts\generate_practice_prompts.py
```

## Команды бота

- `/start` — приветствие
- `/help` — подсказка
- `/practice` — практика (кнопки: Следующая / Повтор / Выход)
- `/support` — поддержка (FAQ → оператор)
- `/cancel` — сброс режима и скрытие клавиатур
- `/myid` — показать `user_id`, `chat_id` и `OPERATOR_ID`
- `/ping_operator` — проверка доставки сообщений оператору

## Как отвечать оператору

1) В чате с ботом дождитесь сообщения “Новый тикет #…”.
2) Нажмите **Reply** на это сообщение и напишите ответ — бот перешлёт пользователю.
3) Закройте тикет кнопкой **«Закрыть тикет»** или командой `/close 123`.
