# Local Corporate RAG MVP

Локальный MVP для поиска по корпоративным документам с `FastAPI`, `PostgreSQL + pgvector`, локальным embedder-сервисом и `Telegram`-ботом.

Проект собирался как рабочий пилот для запуска на личном ноутбуке в `Windows 11 + WSL2 + Ubuntu 22.04`. Это не production-развертывание, а демонстрационная версия, которая показывает полный `end-to-end` сценарий:

- загрузка документов в локальную папку;
- ручная переиндексация;
- hybrid retrieval по архиву;
- генерация ответа с источниками;
- работа через `Telegram` и HTTP API.

## Что реализовано

- Индексация `DOCX` и текстовых `PDF`.
- Извлечение базовых метаданных:
  - тип документа;
  - контрагент;
  - номер документа;
  - даты;
  - сумма и валюта.
- Разбиение документов на чанки с перекрытием.
- Локальное вычисление embeddings через отдельный embedder-сервис.
- Hybrid retrieval:
  - metadata search;
  - PostgreSQL full-text search;
  - vector search через `pgvector`.
- Генерация grounded-ответа по найденным фрагментам через `OpenAI Responses API`.
- Telegram-бот для пользовательских запросов.
- Operator API для health-check и ручного reindex.
- Поддержка коротких follow-up вопросов:
  - в LLM передаются последние `10` сообщений переписки;
  - retrieval тоже может использовать недавний контекст диалога.

## Стек

- `Python 3.11`
- `FastAPI`
- `SQLAlchemy`
- `PostgreSQL 16`
- `pgvector`
- `PyMuPDF`
- `python-docx`
- `aiogram`
- `transformers` / `sentence-transformers`
- `OpenAI Python SDK`
- `supervisord`

## Архитектура

### API

- `src/app/main.py` — точка входа `FastAPI`.
- `src/app/api/query.py` — пользовательский endpoint `/api/query`.
- `src/app/api/admin.py` — operator endpoints `/api/admin/*`.

### Индексация

- `src/app/ingest/importer.py` — полный reindex по папке документов.
- `src/app/ingest/parsers/docx_parser.py` — парсинг `DOCX`.
- `src/app/ingest/parsers/pdf_parser.py` — парсинг `PDF`.
- `src/app/ingest/metadata_extraction.py` — извлечение метаданных правилами.
- `src/app/ingest/chunking.py` — разбиение на чанки.

### Retrieval и генерация

- `src/app/retrieval/hybrid_search.py` — hybrid retrieval.
- `src/app/retrieval/query_parser.py` — разбор пользовательского вопроса.
- `src/app/retrieval/rerank.py` — дополнительный rerank по бизнес-сигналам.
- `src/app/providers/openai_generator.py` — генерация ответа по найденным источникам.
- `src/app/services/query_service.py` — orchestration запроса, retrieval и ответа.

### Хранение данных

- `src/app/db/models.py` — SQLAlchemy-модели.
- `src/app/db/repositories.py` — доступ к БД, поиск, query history.
- `src/app/db/migrations/001_initial.sql` — начальная схема БД.

### Embedder

- `src/embedder/service.py` — локальный сервис embeddings.
- `src/embedder/model_loader.py` — загрузка и inference embedding-модели.

Текущая рабочая embedding-модель для локального пилота:

- `intfloat/multilingual-e5-small`

Она выбрана как практичный компромисс для домашнего ПК. Изначально проект ориентировался на более тяжелую модель, но для реального локального deploy эта конфигурация оказалась слишком тяжеловесной.

## Какие документы поддерживаются

Сейчас поддерживаются:

- `.docx`
- `.pdf` с текстовым слоем

Сейчас не поддерживаются полноценно:

- сканированные PDF без OCR;
- изображения;
- `xlsx`, `eml`, архивы почты и другие форматы вне `DOCX/PDF`.

Если при индексации из документа извлечено слишком мало текста, он помечается как `OCR_REQUIRED` и не участвует в нормальном поиске.

## Как работает пайплайн

1. Пользователь кладет документы в локальную папку архива.
2. Оператор запускает `reindex`.
3. Система находит все `DOCX/PDF`, считает их хэш и определяет измененные документы.
4. Из файлов извлекается текст.
5. Из текста извлекаются базовые метаданные.
6. Документ режется на чанки.
7. Для чанков считаются embeddings.
8. Текст, метаданные и векторы сохраняются в `PostgreSQL + pgvector`.
9. При запросе пользователя выполняется metadata search, full-text search и vector search.
10. В LLM отправляются только найденные релевантные фрагменты и контекст диалога.
11. Пользователь получает короткий ответ с источниками.

## Telegram и API

Поддерживаются:

- обычные текстовые вопросы к архиву;
- `/status` — статус системы;
- `/reindex` — ручной reindex;
- `/help`

Основные HTTP endpoints:

- `POST /api/query`
- `GET /api/admin/health`
- `POST /api/admin/reindex`
- `GET /embed`
- `GET /health` для embedder-сервиса

## Быстрый старт

### 1. Требования

- `Windows 11`
- `WSL2`
- `Ubuntu 22.04`
- `Python 3.11`
- `PostgreSQL 16`
- `pgvector`

### 2. Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pip install -e .[embedder]
```

### 3. Конфиг

Скопируйте `.env.example` в `.env` и заполните значения:

- `APP_DATABASE_URL`
- `APP_DOCUMENTS_DIR`
- `APP_OPENAI_API_KEY`
- `APP_TELEGRAM_BOT_TOKEN`
- `APP_ALLOWED_TELEGRAM_USER_IDS`
- `APP_OPERATOR_TELEGRAM_USER_IDS`

### 4. Запуск

```bash
python scripts/run_embedder.py
python scripts/run_api.py
python scripts/run_bot.py
```

Или через `supervisord`:

```bash
bash scripts/start_stack.sh
```

### 5. Переиндексация

```bash
python scripts/reindex.py --force
```

## WSL-скрипты

- `scripts/bootstrap_wsl_app.sh` — bootstrap окружения внутри `WSL2`.
- `scripts/verify_wsl_stack.sh` — быстрая проверка стека.
- `scripts/check_stack.py` — health-проверка по БД, embedder и директории документов.
- `scripts/start_stack.sh` — запуск `embedder + api + bot`.
- `scripts/stop_stack.sh` — остановка стека.
- `scripts/status_stack.sh` — статус процессов и среды.

## Тесты

```bash
python -m pytest
```

В проекте есть unit-тесты для:

- индексации;
- chunking;
- metadata extraction;
- hybrid search;
- query service;
- answer formatting;
- admin health.

## Ограничения MVP

- Это локальный пилот, а не production-сервис.
- Для живой демонстрации сервисы нужно поднимать вручную.
- Сканированные PDF без OCR пока не обрабатываются полноценно.
- Нет web-admin панели.
- Нет фоновой очереди ingestion.
- Нет production-мониторинга и централизованного аудита.

## Статус текущего deploy

Рабочий стенд разворачивался локально на домашнем ПК. Поэтому внешний доступ и тестирование нужно согласовывать по времени, когда ноутбук включен и стек поднят.
