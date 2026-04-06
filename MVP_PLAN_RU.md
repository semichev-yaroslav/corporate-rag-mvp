# MVP-план: локальный RAG для корпоративных документов на Windows-ноутбуке

## Краткое резюме
- Цель: сделать локальное приложение для поиска по архиву `DOCX` и в основном текстовых `PDF` документов компании с ответами через Telegram-бота.
- Зафиксированный стек MVP:
  - хост: ноутбук на `Windows 11` с `NVIDIA RTX Laptop GPU 8 GB VRAM`
  - среда запуска: `WSL2 + Ubuntu 22.04`
  - backend: `Python 3.11 + FastAPI`
  - Telegram: `aiogram`, режим `long polling`
  - БД: `PostgreSQL 16 + pgvector`
  - локальные эмбеддинги: `ai-sage/Giga-Embeddings-instruct`
  - режим загрузки эмбеддинг-модели: `4-bit` для надежной работы на ноутбуке
  - генерация ответа: `ChatGPT API` через `OpenAI Responses API`
- Документы, текст, метаданные, эмбеддинги, индекс и поиск живут локально на ноутбуке.
- Во внешний API уходит только вопрос пользователя и найденные релевантные фрагменты.
- Все основные пользовательские и продуктовые сущности фиксируются на русском языке.

## Жестко зафиксированные решения
- Основной язык проекта: русский.
- Пользовательские промпты, формат ответа, тестовые кейсы, документация MVP и бизнес-логика должны быть на русском.
- Эмбеддинг-модель в MVP не меняем на другую.
- Полную `BF16/FP16` загрузку `Giga-Embeddings-instruct` в MVP не используем.
- Telegram `webhook` не используем, только `long polling`.
- OCR не входит в MVP.
- Веб-админка не входит в MVP.
- Роли доступа и ACL по документам не входят в MVP.
- Облачный деплой не входит в MVP.
- Локальную LLM вместо ChatGPT API в MVP не добавляем.
- До этапа retrieval запрос в LLM не отправляем.

## Что входит в MVP
- Индексация до `100` документов.
- Поддержка `DOCX` и текстовых `PDF`.
- Ручной запуск переиндексации.
- Вопросы вида:
  - «Был ли у нас договор с ООО X?»
  - «Когда заканчивается договор с ООО X?»
  - «На какую сумму у нас договор с ООО X?»
- Короткий ответ с `1-3` источниками.
- Telegram-бот для личного использования, пока ноутбук включен.

## Что не входит в MVP
- OCR для сканов.
- Групповые Telegram-чаты.
- Постоянная доступность 24/7.
- Автоматическое отслеживание папки.
- Разграничение доступа по типам документов.
- Облачное хранилище.
- Миграция на локальную генеративную модель.
- Продвинутая observability-платформа.

## Критерии успеха
- Система полностью запускается на ноутбуке через `WSL2`.
- `Giga-Embeddings-instruct` в `4-bit` режиме стабильно отдает эмбеддинги без `CUDA out of memory` на типовых батчах.
- Бот отвечает на основные вопросы по договорам с цитированием источников.
- Точность на наборе из `30-50` реальных вопросов не ниже `85%`.
- Каждый положительный ответ содержит минимум один источник.
- Если подтверждения нет, система явно сообщает об этом и не выдумывает.

## Целевая среда
- `Windows 11`
- `WSL2` с `Ubuntu 22.04`
- `Python 3.11`
- `NVIDIA RTX Laptop GPU 8 GB VRAM`
- минимум `40 GB` свободного места на диске
- установленный драйвер NVIDIA с поддержкой `WSL`

## Почему используем WSL2
- `WSL2` это Linux внутри Windows с настоящим Linux-ядром.
- Для `torch`, `CUDA`, `transformers`, `bitsandbytes` и Hugging Face-стека это более предсказуемая среда, чем native Windows.
- Все прикладные сервисы запускаются внутри `WSL2`, а не в Windows Python.

## Архитектура
- `telegram-bot` получает сообщения от пользователя через `long polling`.
- `app-api` нормализует запрос, делает поиск, вызывает OpenAI и формирует ответ.
- `embedder` это локальный сервис, который держит `Giga-Embeddings-instruct` и выдает эмбеддинги по локальному HTTP.
- `indexer` парсит документы, режет их на чанки, извлекает метаданные, получает эмбеддинги и пишет все в БД.
- `PostgreSQL + pgvector` хранит документы, метаданные, чанки, векторы и логи запросов.

## Структура репозитория
- `README.md`
- `MVP_PLAN_RU.md`
- `pyproject.toml`
- `.env.example`
- `src/app/main.py`
- `src/app/config.py`
- `src/app/api/query.py`
- `src/app/bot/polling.py`
- `src/app/bot/handlers.py`
- `src/app/db/models.py`
- `src/app/db/session.py`
- `src/app/db/migrations/`
- `src/app/ingest/importer.py`
- `src/app/ingest/parsers/docx_parser.py`
- `src/app/ingest/parsers/pdf_parser.py`
- `src/app/ingest/chunking.py`
- `src/app/ingest/metadata_extraction.py`
- `src/app/retrieval/query_parser.py`
- `src/app/retrieval/hybrid_search.py`
- `src/app/retrieval/rerank.py`
- `src/app/providers/openai_generator.py`
- `src/app/providers/embedding_client.py`
- `src/embedder/service.py`
- `src/embedder/model_loader.py`
- `src/embedder/schemas.py`
- `scripts/reindex.py`
- `scripts/run_bot.py`
- `scripts/run_api.py`
- `tests/`

## Публичные интерфейсы
- `POST /api/query`
- `POST /api/admin/reindex`
- `GET /api/admin/documents`
- `GET /api/admin/health`
- локальный embedding service:
  - `POST /embed`
  - request: `{"texts": ["..."], "task_type": "query" | "document"}`
  - response: `{"model_id": "...", "quantization": "4bit", "dimensions": 2048, "vectors": [[...]]}`

## Важные типы и контракты
- `QueryRequest`
  - `user_id: str`
  - `chat_id: str`
  - `text: str`
  - `trace_id: str`
- `QueryResponse`
  - `answer: str`
  - `confidence: float`
  - `citations: list[Citation]`
  - `matched_documents: list[MatchedDocument]`
  - `latency_ms: int`
- `Citation`
  - `document_id: str`
  - `file_name: str`
  - `page_from: int | None`
  - `page_to: int | None`
  - `section_title: str | None`
  - `snippet: str`
- `EmbeddingProvider`
  - `embed_documents(texts: list[str]) -> list[list[float]]`
  - `embed_query(text: str) -> list[float]`

## Схема данных
- `documents`
  - `id`
  - `file_path`
  - `file_name`
  - `file_hash`
  - `file_type`
  - `status`
  - `created_at`
  - `updated_at`
- `document_metadata`
  - `document_id`
  - `doc_type`
  - `counterparty_raw`
  - `counterparty_normalized`
  - `document_number`
  - `document_date`
  - `start_date`
  - `end_date`
  - `amount`
  - `currency`
- `chunks`
  - `id`
  - `document_id`
  - `chunk_index`
  - `text`
  - `embedding vector(2048)`
  - `page_from`
  - `page_to`
  - `section_title`
  - `token_count`
- `users`
  - `telegram_user_id`
  - `is_allowed`
- `query_logs`
  - `id`
  - `telegram_user_id`
  - `question`
  - `normalized_question`
  - `answer`
  - `confidence`
  - `latency_ms`
  - `created_at`

## Полный поток данных
1. Пользователь пишет в Telegram-бот.
2. Бот получает update через `long polling`.
3. Проверяется `telegram_user_id` по локальному allowlist.
4. Query parser выделяет сущности: контрагент, тип документа, дата, сумма, номер документа.
5. Запускается hybrid retrieval:
  - точный и fuzzy-поиск по метаданным
  - full-text поиск по тексту чанков
  - vector search по `pgvector`
6. Результаты объединяются детерминированным rank fusion.
7. Выбираются top `4-8` чанков максимум из `3` документов.
8. В OpenAI отправляются только вопрос, найденные чанки и метаданные источников.
9. OpenAI формирует краткий grounded-ответ.
10. Бот отправляет ответ с источниками обратно в Telegram.

## Политика retrieval
- По умолчанию до поиска LLM не вызывается.
- Retrieval обязательно hybrid, а не только по эмбеддингам.
- Точные совпадения по контрагенту и номеру договора имеют повышенный приоритет.
- Если доказательств недостаточно, система отвечает «не найдено подтверждение в проиндексированных документах».
- Pre-search rewrite через LLM в MVP отключен.

## Формат ответа пользователю
- Первая строка: короткий ответ на русском.
- Далее блок `Источники:`
- Затем `1-3` источника:
  - имя файла
  - страница или раздел
  - короткая подтверждающая цитата
- Если подтверждения нет:
  - явно сказать, что в проиндексированных документах надежного подтверждения не найдено
  - при необходимости предложить уточнить контрагента или номер документа

## Правила индексации документов
- Поддерживаются:
  - `DOCX`
  - текстовые `PDF`
- Не поддерживаются в MVP:
  - сканы, которым нужен OCR
- Парсинг:
  - `DOCX` через `python-docx`
  - `PDF` через `PyMuPDF`
- Если текста нет или почти нет:
  - ставим статус `OCR_REQUIRED`
  - исключаем документ из retrieval
  - показываем этот статус в админских командах

## Правила извлечения метаданных
- Сначала детерминированное извлечение:
  - regex для номеров договоров
  - regex для дат
  - regex для сумм и валют
  - шаблоны для `ООО`, `АО`, `ИП`
- Нормализация контрагентов:
  - убрать лишние пробелы
  - нормализовать кавычки
  - сохранить юр. форму
- LLM-извлечение метаданных в MVP не требуется.
- Если поле не извлекается надежно, записать `NULL`.

## Правила chunking
- Размер чанка: `800-1200` токенов
- Перекрытие: `150` токенов
- По возможности сохранять границы страниц
- Предпочитать разбиение по заголовкам и абзацам
- Каждый чанк обязан хранить:
  - исходный документ
  - диапазон страниц
  - заголовок раздела, если есть

## План embedding runtime
- Модель: `ai-sage/Giga-Embeddings-instruct`
- Режим: `4-bit` quantized runtime
- Для пользовательских запросов использовать instruct/query format, рекомендованный для модели.
- Для документов кодировать chunk text как passage/document.
- Размер batch фиксировать консервативно и калибровать под ноутбук.
- Если embedder недоступен, индексация и поиск завершаются явной ошибкой.

## План генерации через OpenAI
- Использовать `Responses API`.
- Выбрать экономичную текстовую модель, достаточную для grounded summarization.
- Prompt генератора должен явно требовать:
  - отвечать только по переданным источникам
  - не выдумывать факты
  - отвечать на русском
  - цитировать источники в фиксированном формате
  - при нехватке данных писать об этом явно
- Генератор должен быть отдельным provider-классом для будущей замены.

## План Telegram-бота
- Использовать только `long polling`.
- Поддерживать только личный чат.
- Бот работает только когда ноутбук включен и процесс запущен.
- Команды:
  - `/start`
  - `/help`
  - `/reindex` только для оператора
  - `/status` только для оператора

## Последовательность настройки окружения
1. Включить `WSL2`.
2. Установить `Ubuntu 22.04`.
3. Проверить работу GPU внутри `WSL2`.
4. Установить `Python 3.11`.
5. Установить `PostgreSQL 16`.
6. Включить `pgvector`.
7. Создать `venv`.
8. Установить backend-зависимости.
9. Установить GPU-совместимый `torch` для `WSL2`.
10. Установить `transformers`, `sentence-transformers`, `bitsandbytes`, `huggingface_hub`.
11. Скачать модель и проверить локальный `embedder`.
12. Создать `.env` с токеном Telegram, ключом OpenAI, локальным URL БД и путями к архиву.

## Этапы реализации
1. Поднять каркас репозитория, конфиг, зависимости и `README`.
2. Реализовать схему БД и миграции.
3. Реализовать локальный embedding service и проверить `/embed`.
4. Реализовать парсинг `DOCX` и `PDF`.
5. Реализовать metadata extraction и chunking.
6. Реализовать индексатор и команду ручного реиндекса.
7. Реализовать hybrid retrieval.
8. Реализовать OpenAI answer generation.
9. Реализовать Telegram-бота на `long polling`.
10. Добавить тесты, логирование и набор эталонных вопросов.
11. Откалибровать batch size, retrieval thresholds и размер контекста.

## Порядок разработки
- Первый milestone это не бот, а рабочий локальный `embedder`.
- До основной разработки приложения нужно доказать:
  - `WSL2` работает
  - GPU видна
  - модель загружается
  - `/embed` возвращает векторы
- Если нужно, временно использовать mock embedding provider для параллельной разработки backend, но заменить его до настройки retrieval.

## Тестовые сценарии
- Индексация `DOCX` с обычным договором.
- Индексация текстового `PDF`.
- Отбраковка `PDF` без текста с пометкой `OCR_REQUIRED`.
- Извлечение:
  - контрагента
  - номера договора
  - даты окончания
  - суммы
- Retrieval для вопросов:
  - «Был ли у нас договор с ООО Рога и Копыта?»
  - «Когда заканчивается договор с ООО Ромашка?»
  - «На какую сумму у нас договор с ООО Тест?»
- Неавторизованный пользователь Telegram получает отказ.
- Недоступность embedder дает контролируемую ошибку.
- Недоступность OpenAI дает контролируемую ошибку.
- Ответ без доказательств блокируется formatter-ом.

## Критерии приемки
- Локальный embedder стабильно поднимается на ноутбуке и повторяемо выдает эмбеддинги.
- Индексация до `100` документов проходит успешно.
- Не менее `95%` поддерживаемых документов парсятся без ручного вмешательства.
- Не менее `85%` вопросов из контрольной выборки получают правильный ответ.
- Каждый ответ содержит хотя бы один источник.
- Если доказательств нет или они противоречивы, ответ не должен утверждать неподтвержденный факт.

## Основные риски и меры
- Риск: нехватка GPU-памяти.
  - Мера: `4-bit`, маленький batch, без полной загрузки модели.
- Риск: проблемы совместимости `CUDA` в `WSL2`.
  - Мера: проверить GPU-стек до прикладной разработки.
- Риск: слабое извлечение контрагентов и сумм.
  - Мера: hybrid retrieval и regex extraction.
- Риск: часть PDF окажется сканами.
  - Мера: явно помечать `OCR_REQUIRED` и исключать из MVP.
- Риск: доступность только пока ноутбук включен.
  - Мера: принять как ограничение MVP и использовать `long polling`.

## Явные допущения и defaults
- У целевого ноутбука `NVIDIA RTX Laptop GPU 8 GB VRAM`.
- Пользователь согласен, что система работает только пока ноутбук включен.
- Пользователь согласен использовать `ChatGPT API` для финального ответа.
- Архив MVP небольшой и помещается на локальный диск.
- Большинство PDF в архиве текстовые.
- Основной язык проекта, пользовательского интерфейса, ответов, тестов и документации: русский.

## Внешние источники
- `Giga-Embeddings-instruct`: [https://huggingface.co/ai-sage/Giga-Embeddings-instruct](https://huggingface.co/ai-sage/Giga-Embeddings-instruct)
- статья по установке: [https://vc.ru/ai/2730372-embedddingi-dlya-russkogo-yazyka-v-2026](https://vc.ru/ai/2730372-embedddingi-dlya-russkogo-yazyka-v-2026)
- WSL overview: [https://learn.microsoft.com/en-us/windows/wsl/about](https://learn.microsoft.com/en-us/windows/wsl/about)
- CUDA on WSL: [https://docs.nvidia.com/cuda/wsl-user-guide/](https://docs.nvidia.com/cuda/wsl-user-guide/)
- OpenAI Responses API: [https://developers.openai.com/api/docs/responses](https://developers.openai.com/api/docs/responses)
