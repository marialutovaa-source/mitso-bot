# МИТСО — Бот учёта пропусков

Telegram-бот для старосты: ведение пропусков, экспорт в Word, интеграция с расписанием.

---

## Быстрый старт

### 1. Создать бота
- Написать @BotFather → `/newbot` → скопировать токен

### 2. Узнать свой Telegram ID
- Написать @userinfobot — покажет твой числовой ID

### 3. Деплой на Railway (бесплатно, ноут не нужен)

1. Зарегистрируйся на https://railway.app
2. New Project → Deploy from GitHub repo (или загрузи папку)
3. Добавь PostgreSQL: New → Database → PostgreSQL
4. В настройках проекта добавь переменные окружения:
   ```
   BOT_TOKEN=<твой токен>
   DATABASE_URL=<PostgreSQL URL из Railway>
   SUPER_ADMIN_IDS=<твой telegram id>
   ```
5. Railway автоматически запустит `Procfile`

### 4. Настроить расписание

Открой `services/schedule.py` и заполни `GROUP_PARAMS`:

1. Перейди на https://apps.mitso.by/frontend/web/schedule/group-schedule
2. Открой DevTools (F12) → Network → XHR
3. Выбери группу и нажми «Показать»
4. Найди запрос к `group-schedule`, посмотри параметры
5. Перенеси их в `GROUP_PARAMS`

---

## Роли

| Роль | Возможности |
|------|-------------|
| **superadmin** | Всё. Назначается через `SUPER_ADMIN_IDS` |
| **admin** | Управление ролями, все отчёты, просмотр справок |
| **starost** | Добавление студентов, отметка пропусков, отчёты |
| **student** | Просмотр своих пропусков, отправка справок, регистрация |

---

## Команды

| Команда | Кто | Описание |
|---------|-----|----------|
| `/start` | Все | Начало работы |
| `/register` | Студент | Привязать аккаунт к своему имени |
| `/addstudent` | Старoста+ | Добавить студента(ов) в список |
| `/addadmin` | Админ | Назначить администратора |
| `/addstarost <id>` | Админ | Назначить старосту |
| `/rmadmin <id>` | Суперадмин | Снять права администратора |

---

## Структура проекта

```
mitso_bot/
├── main.py                  # Точка входа
├── config.py                # Переменные окружения
├── requirements.txt
├── Procfile                 # Для Railway
├── .env.example             # Пример .env
├── handlers/
│   ├── common.py            # /start, /register, фото, расписание
│   ├── admin.py             # Управление ролями, отчёты
│   └── starost.py           # Студенты, пропуски
├── db/
│   ├── models.py            # Создание таблиц
│   └── queries.py           # Все запросы к БД
├── services/
│   ├── schedule.py          # Парсер расписания МИТСО
│   └── docx_export.py       # Генерация Word-отчётов
└── utils/
    ├── keyboards.py         # Клавиатуры
    └── formatters.py        # Форматирование текста
```
