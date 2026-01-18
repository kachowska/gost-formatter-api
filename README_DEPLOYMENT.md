# 🚀 Развертывание ИИ-Агента GOST Formatter

Полное руководство по запуску системы форматирования библиографических записей с использованием Claude Haiku 4.5.

---

## 📋 Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Требования](#требования)
3. [Установка](#установка)
4. [Запуск](#запуск)
5. [Использование](#использование)
6. [API Endpoints](#api-endpoints)
7. [Примеры использования](#примеры-использования)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Архитектура системы

```
┌─────────────────┐
│  Web Frontend   │  ← gost-formatter-api-integrated.html
│   (HTML/JS)     │
└────────┬────────┘
         │ HTTP API
         ↓
┌─────────────────┐
│   FastAPI       │  ← api_server.py
│   Backend       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  GOST Agent     │  ← gost_formatter_agent.py
│  (Core Logic)   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Claude Haiku    │  ← Anthropic API
│     4.5         │
└─────────────────┘
```

**Компоненты**:
1. **Web Frontend**: Интерфейс для пользователей
2. **FastAPI Backend**: REST API сервер
3. **GOST Agent**: Основная логика форматирования
4. **Claude Haiku 4.5**: AI-модель для обработки

---

## ⚙️ Требования

### Системные требования
- **Python**: 3.8+
- **ОС**: Linux, macOS, Windows
- **RAM**: минимум 2GB
- **Интернет**: для доступа к Anthropic API

### Python библиотеки
```bash
anthropic>=0.20.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6
```

### API ключи
- **Anthropic API Key**: получить на https://console.anthropic.com/

---

## 📦 Установка

### Шаг 1: Клонирование файлов

Скопируйте следующие файлы в рабочую директорию:
```
project/
├── gost_formatter_agent.py          # Основной агент
├── api_server.py                    # FastAPI сервер
├── gost-formatter-api-integrated.html  # Веб-интерфейс
├── requirements.txt                 # Зависимости
└── README_DEPLOYMENT.md             # Эта инструкция
```

### Шаг 2: Создание виртуального окружения

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Шаг 3: Установка зависимостей

Создайте файл `requirements.txt`:
```txt
anthropic>=0.20.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6
aiofiles>=23.0.0
```

Установите:
```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка API ключа

**Вариант 1: Переменная окружения (рекомендуется)**
```bash
# Linux/macOS
export ANTHROPIC_API_KEY="your-api-key-here"

# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-api-key-here"

# Windows CMD
set ANTHROPIC_API_KEY=your-api-key-here
```

**Вариант 2: Файл .env**
```bash
# Создайте файл .env
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

Добавьте в начало `api_server.py`:
```python
from dotenv import load_dotenv
load_dotenv()

# Инициализация агента
import os
agent = GOSTFormatterAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

**Вариант 3: Прямо в коде (НЕ для продакшена)**
```python
# В api_server.py, строка ~40
agent = GOSTFormatterAgent(api_key="your-api-key-here")
```

---

## 🚀 Запуск

### Способ 1: Локальный запуск (для разработки)

**1. Запустите API сервер:**
```bash
python api_server.py
```

Вы увидите:
```
GOST Formatter API Server
============================================================
Запуск сервера на http://localhost:8000

Доступные эндпоинты:
  GET  /                      - Информация об API
  GET  /api/health            - Проверка работоспособности
  POST /api/format/single     - Форматирование одного источника
  POST /api/format/batch      - Пакетное форматирование
  ...

Документация: http://localhost:8000/docs
============================================================
```

**2. Откройте веб-интерфейс:**
```bash
# Просто откройте в браузере:
open gost-formatter-api-integrated.html
# или
google-chrome gost-formatter-api-integrated.html
```

### Способ 2: Запуск через uvicorn

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### Способ 3: Docker (для продакшена)

**Создайте `Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gost_formatter_agent.py .
COPY api_server.py .

ENV ANTHROPIC_API_KEY=""

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Соберите и запустите:**
```bash
# Сборка
docker build -t gost-formatter .

# Запуск
docker run -d \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your-key" \
  --name gost-formatter-api \
  gost-formatter
```

### Способ 4: Production (nginx + gunicorn)

**Установите gunicorn:**
```bash
pip install gunicorn
```

**Запустите:**
```bash
gunicorn api_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

**Настройте nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

---

## 💻 Использование

### Веб-интерфейс

1. **Откройте** `gost-formatter-api-integrated.html` в браузере
2. **Проверьте** подключение API (зеленая точка = ✅)
3. **Выберите режим**:
   - **Один источник**: для быстрого форматирования
   - **Пакетная обработка**: для 50-100 источников

#### Режим 1: Один источник

1. Выберите стандарт (ГОСТ или ВАК)
2. Выберите тип источника (книга, статья и т.д.)
3. Вставьте данные в любом формате
4. Нажмите "Форматировать"
5. Скопируйте результат

**Пример ввода:**
```
Иванов И.И., Петров П.П. Основы машинного обучения. М.: Наука, 2023. 320 с.
```

**Результат:**
```
Иванов, И. И. Основы машинного обучения / И. И. Иванов, П. П. Петров. – Москва : Наука, 2023. – 320 с.
```

#### Режим 2: Пакетная обработка

1. Вставьте список из 50-100 источников
2. Выберите стандарт
3. Нажмите "Обработать пакетом"
4. Дождитесь завершения (15-30 секунд)
5. Скачайте результат (.txt или BibTeX)

**Пример ввода:**
```
1. Иванов И.И. Название 1. М.: Наука, 2023. 320 с.
2. Петров П.П. Название 2 // Журнал. 2024. Т. 15, № 3. С. 45-52.
3. Сидоров С.С. Название 3. Минск: БГУ, 2022. 400 с.
...
50. Козлов А.Б. Название 50 // Конференция. 2025. С. 100-105.
```

**Статистика:**
- Обработано: 50
- Исправлено ошибок: 127
- Время: 18.5 секунд

---

## 🔌 API Endpoints

### 1. Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "GOST Formatter"
}
```

### 2. Format Single Source
```http
POST /api/format/single
Content-Type: application/json
```

**Request:**
```json
{
  "source": {
    "id": 1,
    "type": "book",
    "authors": ["Иванов, И. И.", "Петров, П. П."],
    "title": "Основы программирования",
    "year": 2023,
    "city": "Москва",
    "publisher": "Наука",
    "pages": "320"
  },
  "standard": "GOST_2018"
}
```

**Response:**
```json
{
  "id": 1,
  "original": "Иванов, И. И. - Основы программирования",
  "formatted": "Иванов, И. И. Основы программирования / И. И. Иванов, П. П. Петров. – Москва : Наука, 2023. – 320 с.",
  "errors_fixed": [
    "Исправлен формат авторов",
    "Добавлены пробелы вокруг тире"
  ],
  "confidence": 98,
  "standard_used": "GOST_2018"
}
```

### 3. Format Batch
```http
POST /api/format/batch
Content-Type: application/json
```

**Request:**
```json
{
  "sources": [
    { "id": 1, "type": "book", "authors": [...], ... },
    { "id": 2, "type": "article", "authors": [...], ... },
    ...
  ],
  "standard": "VAK_RB",
  "batch_size": 20
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "original": "...",
      "formatted": "...",
      "errors_fixed": [...],
      "confidence": 95,
      "standard_used": "VAK_RB"
    },
    ...
  ],
  "total": 50,
  "success": 50,
  "processing_time": 18.5
}
```

### 4. Parse Unstructured Text
```http
POST /api/parse
Content-Type: application/json
```

**Request:**
```json
{
  "text": "1. Иванов И.И. Название. М.: Наука, 2023. 320 с.\n2. Петров П.П. Статья // Журнал. 2024. С. 10-20."
}
```

**Response:**
```json
{
  "success": true,
  "sources_found": 2,
  "sources": [
    {
      "id": 1,
      "type": "book",
      "authors": ["Иванов, И. И."],
      "title": "Название",
      "year": 2023,
      "city": "Москва",
      "publisher": "Наука",
      "pages": "320"
    },
    {
      "id": 2,
      "type": "article",
      "authors": ["Петров, П. П."],
      "title": "Статья",
      "journal": "Журнал",
      "year": 2024,
      "pages": "10-20"
    }
  ]
}
```

### 5. Export to BibTeX
```http
POST /api/export/bibtex
Content-Type: application/json
```

**Request:**
```json
{
  "sources": [...],
  "standard": "GOST_2018"
}
```

**Response:**
```json
{
  "success": true,
  "format": "bibtex",
  "content": "@misc{ref1,\n  title = {...},\n  year = {2023}\n}\n\n@misc{ref2,...}"
}
```

### 6. Get Statistics
```http
GET /api/stats
```

**Response:**
```json
{
  "processed_total": 150,
  "errors_fixed": 387,
  "avg_confidence": 96.5
}
```

### 7. Validate Reference
```http
POST /api/validate
Content-Type: application/json
```

**Request:**
```json
{
  "formatted_text": "Иванов, И.И. Название / И.И. Иванов. - Москва: Наука, 2023. - 320 с.",
  "standard": "GOST_2018"
}
```

**Response:**
```json
{
  "valid": false,
  "errors": [
    "Пробелы после инициалов (должно быть: И. И.)",
    "Тире должно быть длинным (–), а не коротким (-)",
    "Пробелы вокруг двоеточия (должно быть: ' : ')"
  ],
  "corrected": "Иванов, И. И. Название / И. И. Иванов. – Москва : Наука, 2023. – 320 с."
}
```

---

## 📝 Примеры использования

### Python (через requests)

```python
import requests

# Форматирование одного источника
response = requests.post('http://localhost:8000/api/format/single', json={
    "source": {
        "id": 1,
        "type": "book",
        "authors": ["Иванов, И. И."],
        "title": "Основы Python",
        "year": 2024,
        "city": "Москва",
        "publisher": "Питер",
        "pages": "400"
    },
    "standard": "GOST_2018"
})

result = response.json()
print(result['formatted'])
```

### JavaScript (fetch)

```javascript
// Пакетное форматирование
const sources = [
  { id: 1, type: 'book', authors: ['Иванов, И. И.'], title: 'Название 1', year: 2023 },
  { id: 2, type: 'article', authors: ['Петров, П. П.'], title: 'Название 2', year: 2024 }
];

const response = await fetch('http://localhost:8000/api/format/batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sources, standard: 'VAK_RB', batch_size: 20 })
});

const results = await response.json();
console.log(`Обработано: ${results.total} источников за ${results.processing_time} секунд`);
```

### cURL

```bash
# Проверка здоровья API
curl http://localhost:8000/api/health

# Парсинг текста
curl -X POST http://localhost:8000/api/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Иванов И.И. Название. М.: Наука, 2023. 320 с."}'

# Статистика
curl http://localhost:8000/api/stats
```

---

## 🐛 Troubleshooting

### Проблема 1: API недоступен

**Симптомы**: Красная точка в веб-интерфейсе, ошибка "API недоступен"

**Решение**:
```bash
# Проверьте, запущен ли сервер
ps aux | grep api_server

# Проверьте порт
lsof -i :8000

# Перезапустите сервер
python api_server.py
```

### Проблема 2: Ошибка Anthropic API

**Симптомы**: Ошибка "Invalid API key" или "Rate limit exceeded"

**Решение**:
```bash
# Проверьте ключ
echo $ANTHROPIC_API_KEY

# Проверьте квоту на https://console.anthropic.com/

# Обновите ключ
export ANTHROPIC_API_KEY="new-key-here"
```

### Проблема 3: Медленная обработка

**Симптомы**: Пакетная обработка занимает >60 секунд

**Решение**:
```python
# В api_server.py увеличьте параллелизм
results = await agent.format_batch_async(
    sources,
    standard,
    batch_size=20,
    max_concurrent=10  # Было 5, стало 10
)
```

### Проблема 4: CORS ошибка

**Симптомы**: Ошибка "CORS policy" в браузере

**Решение**:
```python
# В api_server.py измените:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или укажите конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Проблема 5: Неправильное форматирование

**Симптомы**: Результат не соответствует стандарту ГОСТ/ВАК

**Решение**:
```python
# 1. Используйте валидацию
response = requests.post('http://localhost:8000/api/validate', json={
    "formatted_text": "ваша запись",
    "standard": "GOST_2018"
})

# 2. Проверьте системный промпт в gost_formatter_agent.py
# 3. Добавьте больше примеров из PDF в промпт
```

---

## 📊 Производительность

### Тесты скорости

| Количество источников | Время обработки | Стоимость (Haiku) |
|-----------------------|-----------------|-------------------|
| 1                     | 1-2 сек         | $0.0001           |
| 20                    | 5-10 сек        | $0.002            |
| 50                    | 12-20 сек       | $0.005            |
| 100                   | 20-35 сек       | $0.010            |

### Оптимизация

**1. Кэширование:**
```python
# Добавьте Redis для кэширования результатов
import redis
cache = redis.Redis(host='localhost', port=6379)

def format_with_cache(source, standard):
    cache_key = f"{standard}:{hash(str(source))}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    result = agent.format_single(source, standard)
    cache.setex(cache_key, 3600, json.dumps(result))  # TTL 1 час
    return result
```

**2. Батчинг:**
```python
# Увеличьте размер батча для больших объемов
results = agent.format_batch(sources, standard, batch_size=50)
```

**3. Параллелизм:**
```python
# Используйте async версию для больших нагрузок
results = await agent.format_batch_async(
    sources,
    standard,
    max_concurrent=10  # Больше параллельных запросов
)
```

---

## 🔐 Безопасность

### Рекомендации для продакшена

1. **Используйте HTTPS**:
```bash
# Настройте SSL через nginx или Let's Encrypt
```

2. **Добавьте аутентификацию**:
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/api/format/single")
async def format_single(
    request: SingleFormatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Проверка токена
    if credentials.credentials != "your-secret-token":
        raise HTTPException(status_code=401, detail="Unauthorized")
    ...
```

3. **Rate limiting**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/format/batch")
@limiter.limit("10/minute")  # Максимум 10 запросов в минуту
async def format_batch(...):
    ...
```

4. **Валидация входных данных**:
```python
class SourceRequest(BaseModel):
    id: int = Field(..., ge=1, le=1000000)
    title: str = Field(..., min_length=1, max_length=500)
    authors: List[str] = Field(..., max_items=20)
    year: int = Field(..., ge=1800, le=2030)
```

---

## 📚 Дополнительные ресурсы

- **Anthropic Documentation**: https://docs.anthropic.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **ГОСТ Р 7.0.100-2018**: Официальный стандарт РФ
- **ВАК РБ**: Стандарт Республики Беларусь

---

## 🤝 Поддержка

Если возникли проблемы:
1. Проверьте логи сервера
2. Используйте `/api/health` для диагностики
3. Проверьте API ключ Anthropic
4. Убедитесь, что все зависимости установлены

---

## 📄 Лицензия

MIT License - свободное использование для любых целей.

---

**Готово! Система полностью развернута и готова к работе.** 🎉
