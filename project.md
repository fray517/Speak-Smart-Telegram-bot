# SpeakSmart — MVP Telegram-бот (языковая практика + поддержка)


## 1) Контекст и цель

**Заказчик:** LinguaBridge (EdTech).  
**Цель MVP:** Telegram-бот, который:
1) даёт **голосовую практику** (бот → voice prompt → пользователь отвечает voice → распознавание → простая проверка → фидбек),
2) отвечает на **FAQ**,
3) при необходимости **эскалирует** в оператора внутри Telegram (через бот-посредник).

**Требования запуска:** локально, без веб-сервера, **polling**, Python 3.10+.

---

## 2) Скоуп MVP

### Must-have (MVP)
- aiogram (v3 предпочтительно) + polling
- Команды: `/start`, `/help`, `/practice`, `/support`, `/cancel`
- Приём текстовых и голосовых сообщений
- Режим **Practice**:
  - отправка заранее записанной фразы (voice из файла)
  - приём voice ответа
  - распознавание речи (Whisper или Google Speech)
  - сравнение с эталоном (ключевые слова/простая метрика)
  - обратная связь пользователю
- Режим **Support**:
  - поиск ответа в FAQ (JSON)
  - если не найдено — предложение “передать оператору”
- **Оператор**:
  - уведомление оператора о новом обращении
  - возможность отвечать пользователю **через бота** (relay)
- Хранение (SQLite или JSON): история диалогов, трекинг сессий, лог ошибок
- Структура: `handlers/`, `services/`, `utils/`
- PEP8 + README

### Nice-to-have (после MVP)
- Меню-кнопки (ReplyKeyboard/Inline)
- Выбор языка/уровня/набора фраз
- Более умное сравнение (Levenshtein / word overlap / fuzzy)
- Очередь/тикеты поддержки, статусы, несколько операторов
- Админ-панель (простые команды для оператора)

### Non-goals (в MVP не делаем)
- Вебхук, деплой, оплату/подписки
- Полноценный LMS/профили уровней/контент-менеджмент
- Сложная оценка произношения (phoneme scoring) — только текстовое сравнение

---

## 3) Ключевые пользовательские сценарии

### Practice
1. Пользователь: `/practice`
2. Бот: отправляет voice prompt (файл) + краткую инструкцию
3. Пользователь: отправляет voice ответ
4. Бот:
   - скачивает voice
   - конвертирует в wav (через ffmpeg)
   - распознаёт текст
   - сравнивает с эталоном (keywords)
   - возвращает фидбек + (опционально) распознанный текст
5. Бот предлагает: следующая фраза / повтор / выход

### Support
1. Пользователь: `/support` или просто пишет вопрос
2. Бот: ищет ответ в FAQ JSON
3. Если найдено — отвечает
4. Если не найдено — предлагает “Передать оператору”
5. При согласии — создаёт тикет, уведомляет оператора, начинает relay-диалог

### Operator relay (надёжный вариант)
- Бот пересылает оператору сообщение пользователя (как текст, плюс метаданные: user_id, username).
- Оператор **отвечает на это сообщение** в чате с ботом (reply).
- Бот отправляет ответ операторa пользователю.
- Бот логирует оба направления.

---

## 4) Технологии и зависимости

- Python 3.10+
- aiogram v3 (предпочтительно)
- aiosqlite (если SQLite)
- speech stack:
  - **вариант A (рекомендуется для MVP):** `openai-whisper` (локально) или `faster-whisper`
  - **вариант B:** `speech_recognition` + Google Speech API (сетевой)
- ffmpeg (для конвертации ogg/opus → wav)
- logging

> В коде делаем абстракцию `SpeechRecognizer` и переключаем реализацию через env/config.

---

## 5) Архитектура и модули

### Принцип
- Handlers — только роутинг/диалоги/состояния
- Services — бизнес-логика (speech, practice, faq, operator)
- Utils — конфиг, логгер, хелперы, нормализация текста
- Storage — репозиторий/DAO (SQLite)

### FSM состояния (aiogram)
- `Mode.practice_wait_answer`
- `Mode.support_wait_question`
- `Mode.operator_active` (для пользователей в режиме оператора/тикета)

---

## 6) Структура проекта (предлагаемая)
handlers/
  common.py             # /start /help /cancel
  practice.py           # /practice, обработка voice в практике
  support.py            # /support, FAQ, эскалация
  operator.py           # ответы оператора (reply relay)

services/
  practice_service.py   # выбор фраз, сравнение, фидбек
  faq_service.py        # поиск по FAQ
  operator_service.py   # тикеты, routing в оператора
  speech/
    base.py             # интерфейс SpeechRecognizer
    whisper_impl.py     # Whisper реализация
    google_impl.py      # SpeechRecognition реализация
  audio_service.py      # скачивание/конвертация voice (ffmpeg)

storage/
  db.py                 # init + connection
  repositories.py       # методы записи/чтения
  models.py             # dataclasses/typing для сущностей
  migrations.sql        # схема таблиц

utils/
  text_norm.py          # нормализация/keywords
  time.py
  exceptions.py


---

## 7) Данные и схема хранения (SQLite)

### Таблицы (минимум)
**users**
- user_id (PK)
- username
- first_seen_at

**sessions**
- id (PK)
- user_id (FK)
- mode (practice/support)
- started_at
- ended_at

**messages**
- id (PK)
- user_id
- direction (`in`/`out`/`operator_in`/`operator_out`)
- msg_type (`text`/`voice`)
- text (nullable)
- file_id (nullable)
- created_at

**tickets**
- id (PK)
- user_id
- status (`open`/`closed`)
- created_at
- updated_at
- last_user_message (nullable)

**operator_map**
- id (PK)
- operator_chat_id
- forwarded_message_id
- user_id
- created_at

> `operator_map` нужен, чтобы когда оператор **reply**-ит на конкретное сообщение — мы понимали, какому пользователю отправлять.

Если хотим проще — можно хранить mapping в памяти, но для стабильности лучше SQLite.

---

## 8) FAQ формат (JSON)

`data/faq.json`:
```json
[
  {
    "q": "Как начать практику?",
    "keywords": ["practice", "практика", "начать"],
    "a": "Нажмите /practice и ответьте голосом на фразу."
  }
]

9) Practice set формат

assets/practice_sets.json:

[
  {
    "id": "en_001",
    "file": "assets/phrases/en/001.ogg",
    "expected_text": "How are you today",
    "keywords": ["how", "are", "you", "today"]
  }
]
Сравнение (MVP):

распознанный текст → normalize → tokens

score = (кол-во найденных keywords) / (кол-во keywords)

пороги:

= 0.8 → “Правильно!”

0.5–0.79 → “Почти! Попробуй ещё раз…”

< 0.5 → “Давай повторим. Подсказка: …”

10) Конфигурация (.env)

.env.example:

BOT_TOKEN=...

OPERATOR_IDS=123456789,987654321 (через запятую)

DB_PATH=data/speaksMart.sqlite3

FAQ_PATH=data/faq.json

PRACTICE_SETS_PATH=assets/practice_sets.json

SPEECH_PROVIDER=whisper (whisper | google)

WHISPER_MODEL=base (если whisper)

FFMPEG_PATH=ffmpeg (если нужно явно)

LOG_LEVEL=INFO

11) Error handling & logging

Глобальный middleware/обработчик ошибок:

лог в data/logs/app.log

запись в таблицу messages или отдельную errors (опционально)

На распознавание:

таймауты/исключения → “Не удалось распознать, попробуй ещё раз”

На FAQ:

если файл отсутствует/битый → дефолтный ответ + лог

12) Команды и поведение


/start — приветствие + меню (Practice / Support)


/help — краткая инструкция


/practice — старт практики


/support — режим поддержки


/cancel — сброс состояния и выход из режима


Поведение без команд:


если пользователь в practice и прислал voice → обрабатываем как ответ


если пользователь в support и прислал текст → пытаемся FAQ; если не найдено — эскалация


если пользователь не в режимах → мягко подсказать команды



13) Поэтапный план реализации (таски)
Этап 1 — каркас и запуск


 init проекта, структура папок


 aiogram v3 polling, /start /help /cancel


 config + logging


 SQLite init + users/messages basic log


Этап 2 — voice pipeline


 скачивание voice файла из Telegram


 конвертация ogg/opus → wav (ffmpeg)


 SpeechRecognizer интерфейс + реализация (выбрать провайдер по env)


 сервис practice: выбрать фразу, отправить voice, принять ответ


Этап 3 — проверка и фидбек


 practice_sets.json + загрузчик


 text normalization + keyword scoring


 фидбек: “Правильно/Почти/Повтор”


 команды “следующая/повтор/выход” (кнопки или текст)


Этап 4 — support + FAQ


 faq.json + FAQ service


 режим support, обработка свободного ввода


 если нет ответа → предложить оператору


Этап 5 — оператор (relay)


 уведомление операторов


 создание тикета


 пересылка вопроса оператору с метаданными


 обработка reply от оператора → отправка пользователю


 закрытие тикета (команда оператора /close <ticket_id> или кнопка — можно упростить)


Этап 6 — полировка


 обработка ошибок, тест сценариев


 README: установка, env, запуск python main.py


 рефакторинг, PEP8, комментарии



14) Критерии готовности (Definition of Done)


Бот стабильно работает в Telegram через polling


Practice:


отправляет voice prompt


принимает voice ответ


распознаёт и выдаёт фидбек




Support:


отвечает из FAQ


предлагает эскалацию




Operator:


получает обращение


может ответить пользователю через reply relay




Есть README + структура модулей соблюдена



15) Мини-тестплан (ручной)


/start → меню и подсказки


/practice → бот прислал voice → отправить voice ответ → получить фидбек


Отправить “мусорный” voice → корректная ошибка и повтор


/support → вопрос из FAQ → правильный ответ


/support → вопрос вне FAQ → предложение оператора → согласие → оператор получает сообщение


Оператор reply-ит → пользователь получает ответ


/cancel в любом режиме → сброс



16) Вопросы для уточнения (не блокируют старт — можно принять дефолты)


Целевой язык MVP: только английский (по умолчанию) или сразу несколько?


Набор фраз: сколько voice prompts нужно для демо инвесторам (10/20/50)? Есть ли уже записи и эталонные тексты/keywords?


Распознавание: предпочтение Whisper (локально, тяжелее зависимости) или Google Speech (проще, но внешний сервис/сеть)?


Операторский флоу: достаточно relay через бота (рекомендуется) или оператор должен “напрямую” писать пользователю (в Telegram это не всегда надёжно из-за приватности форвардов)?


Нужен ли лог распознанного текста пользователю (показывать “Я распознал: …”) или скрывать?



17) Дефолтные решения (если не уточняем прямо сейчас)


aiogram v3 + polling


Practice language: EN


Speech provider: Whisper (если доступно) иначе Google fallback


Operator: relay через reply (надёжнее)


Хранилище: SQLite (aiosqlite)



