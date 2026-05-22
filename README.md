# VideoDigest

[![CI](https://github.com/mcl0udZY/hseproject_videoanalyser/actions/workflows/ci.yml/badge.svg)](https://github.com/mcl0udZY/hseproject_videoanalyser/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)

VideoDigest — учебный веб-сервис для автоматического реферирования видеоконтента.  
Пользователь загружает видео, сервис распознаёт речь, формирует текстовую расшифровку, краткое содержание, выделяет ключевые фрагменты и показывает результат в браузере.

Проект выполнен в рамках курсовой работы НИУ ВШЭ:

> Исследование алгоритмов и разработка системы автоматического реферирования видеоконтента: от распознавания речи до семантического анализа

## Демо

Видео с демонстрацией работы проекта:

[Открыть демонстрацию на Rutube](https://rutube.ru/video/private/ecb5c8bed4d5f722443a1daef838ad8c/?p=8FTURPX6EusO1L95jIUZMA)

В видео показан основной сценарий: загрузка файла, запуск обработки, ожидание результата и просмотр итоговых материалов.

## Содержание

- [Что умеет проект](#что-умеет-проект)
- [Как работает сервис](#как-работает-сервис)
- [Стек технологий](#стек-технологий)
- [Быстрый запуск](#быстрый-запуск)
- [Запуск для разработки](#запуск-для-разработки)
- [API](#api)
- [Тесты и CI](#тесты-и-ci)
- [Структура проекта](#структура-проекта)
- [Команда и вклад участников](#команда-и-вклад-участников)
- [Статус проекта](#статус-проекта)

## Что умеет проект

- загружать видео через веб-интерфейс;
- создавать задачу на обработку;
- показывать статус и прогресс выполнения;
- распознавать речь в видео;
- формировать текстовую расшифровку;
- строить краткое содержание;
- выделять ключевые фрагменты;
- собирать итоговое highlight-видео;
- показывать результат на отдельной странице;
- хранить список задач в dashboard;
- отдавать результаты через API;
- автоматически проверяться через GitHub Actions.

## Как работает сервис

Общий сценарий работы:

1. Пользователь открывает главную страницу.
2. Выбирает видеофайл и параметры обработки.
3. Backend принимает файл и создаёт задачу.
4. Задача отправляется в очередь.
5. Worker обрабатывает видео в фоне.
6. Сервис сохраняет расшифровку, summary, highlights и итоговые файлы.
7. Пользователь открывает страницу результата и получает готовые материалы.

Упрощённая схема:

```text
Browser
  ↓
FastAPI
  ↓
SQLite
  ↓
Redis / RQ
  ↓
Worker
  ↓
FFmpeg + faster-whisper + text processing
  ↓
Result files
  ↓
Result page
```

## Стек технологий

| Технология | Для чего используется |
|---|---|
| Python 3.11 | основной язык backend-части |
| FastAPI | API и веб-маршруты |
| Jinja2 | HTML-шаблоны |
| HTML / CSS / JavaScript | пользовательский интерфейс |
| SQLite | хранение задач и статусов |
| Redis | очередь задач |
| RQ | запуск фоновой обработки |
| FFmpeg | работа с видео и аудио |
| faster-whisper | распознавание речи |
| Docker Compose | запуск проекта в контейнерах |
| pytest | автоматические тесты |
| Ruff | проверка Python-кода |
| GitHub Actions | автоматический запуск проверок |

## Быстрый запуск

Проект можно запустить через Docker Compose:

```bash
docker compose up --build
```

После запуска:

```text
http://localhost:8000
```

Дополнительные страницы:

```text
http://localhost:8000/dashboard
http://localhost:8000/docs
```

## Запуск для разработки

Клонировать репозиторий:

```bash
git clone https://github.com/mcl0udZY/hseproject_videoanalyser.git
cd hseproject_videoanalyser
```

Создать виртуальное окружение:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Установить зависимости:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
```

Запустить backend локально:

```bash
cd backend
uvicorn app.main:app --reload
```

## API

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/api/health` | проверка состояния сервиса |
| `POST` | `/api/jobs/upload` | загрузка видео и создание задачи |
| `GET` | `/api/jobs` | получение списка задач |
| `GET` | `/api/jobs/{job_id}` | получение информации по задаче |
| `GET` | `/files/{job_id}/{file_path}` | получение файла результата |
| `GET` | `/` | главная страница |
| `GET` | `/dashboard` | панель задач |
| `GET` | `/result/{job_id}` | страница результата |

Пример проверки:

```bash
curl http://localhost:8000/api/health
```

Ожидаемый ответ:

```json
{
  "status": "ok"
}
```

## Тесты и CI

В проект добавлены автоматические тесты для основных частей сервиса:

- API;
- веб-страниц;
- загрузки видео;
- получения списка задач;
- получения конкретной задачи;
- выдачи файлов результата;
- текстовых функций;
- фоновой обработки задач с mock-зависимостями вместо реального запуска Whisper и FFmpeg.

Локальный запуск проверок:

```bash
cd backend
python -m ruff check app tests
python -m pytest -q
```

В GitHub Actions настроен CI. Проверки запускаются при `push` и `pull request`.

Сейчас CI выполняет:

```bash
ruff check app tests
pytest -q
```

## Структура проекта

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   ├── static/
│   │   │   ├── app.js
│   │   │   └── style.css
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── dashboard.html
│   │   │   ├── index.html
│   │   │   └── result.html
│   │   ├── utils/
│   │   │   ├── ffmpeg.py
│   │   │   └── text.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── queue.py
│   │   ├── schemas.py
│   │   ├── tasks.py
│   │   └── worker.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_tasks.py
│   │   └── test_text_utils.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Команда и вклад участников

Проект выполнен командой из трёх человек.

| Участник | Зона ответственности | Основные файлы |
|---|---|---|
| Иванов Кирилл | обработка видео, очередь задач, worker, FFmpeg, текстовая обработка | `backend/app/queue.py`, `backend/app/worker.py`, `backend/app/tasks.py`, `backend/app/utils/ffmpeg.py`, `backend/app/utils/text.py` |
| Солнышкин Федор | backend, API, модели данных, база, конфигурация, Docker | `backend/app/main.py`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/db.py`, `backend/app/config.py`, `backend/requirements.txt`, `backend/Dockerfile`, `docker-compose.yml`, `README.md` |
| Мельников Данила | пользовательский интерфейс, страницы, стили, клиентская логика | `backend/app/templates/base.html`, `backend/app/templates/index.html`, `backend/app/templates/dashboard.html`, `backend/app/templates/result.html`, `backend/app/static/style.css`, `backend/app/static/app.js` |

## Статус проекта

Проект является учебным прототипом.  
В нём реализован полный базовый сценарий: загрузка видео, обработка, получение расшифровки, summary, highlights и просмотр результата через веб-интерфейс.

Что можно улучшить дальше:

- добавить авторизацию пользователей;
- расширить настройки обработки видео;
- улучшить качество summary;
- добавить поддержку более крупных файлов;
- вынести хранение результатов во внешнее файловое хранилище;
- добавить историю обработок для разных пользователей;
- расширить набор тестов для edge cases.

