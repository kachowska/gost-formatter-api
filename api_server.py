"""
FastAPI веб-сервис для ИИ-Агента GOST Formatter
Обрабатывает запросы от фронтенда и возвращает отформатированные записи
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import json

# ВАЖНО: Сначала импортируем классы агента
from gost_formatter_agent import (
    GOSTFormatterAgent,
    Source,
    Standard,
    FormattedResult
)

# Инициализация FastAPI
app = FastAPI(
    title="GOST Formatter API",
    description="API для форматирования библиографических записей по ГОСТ и ВАК",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ИСПРАВЛЕНО: Правильная инициализация агента с чтением из переменной окружения
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("⚠️  WARNING: ANTHROPIC_API_KEY не установлен!")
    print("Установите его: export ANTHROPIC_API_KEY='your-key'")
else:
    print(f"✅ API ключ найден: {api_key[:20]}...")

agent = GOSTFormatterAgent(api_key=api_key)


# ==================== МОДЕЛИ ДАННЫХ ====================

class SourceRequest(BaseModel):
    """Модель входного источника"""
    id: int = 1
    type: str = "book"
    authors: Optional[List[str]] = []
    title: Optional[str] = ""
    year: Optional[int] = None
    publisher: Optional[str] = None
    city: Optional[str] = None
    pages: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    language: str = "ru"


class SingleFormatRequest(BaseModel):
    """Запрос на форматирование одного источника"""
    source: SourceRequest
    standard: str


class BatchFormatRequest(BaseModel):
    """Запрос на пакетное форматирование"""
    sources: List[SourceRequest]
    standard: str
    batch_size: Optional[int] = 20


class TextParseRequest(BaseModel):
    """Запрос на парсинг текста"""
    text: str


class FormatResponse(BaseModel):
    """Ответ с отформатированной записью"""
    id: int
    original: str
    formatted: str
    errors_fixed: List[str]
    confidence: int
    standard_used: str


class BatchFormatResponse(BaseModel):
    """Ответ на пакетное форматирование"""
    results: List[FormatResponse]
    total: int
    success: int
    processing_time: float


# ==================== ЭНДПОИНТЫ ====================

@app.get("/")
async def root():
    """Главная страница - веб-интерфейс"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    # Fallback to JSON if HTML not found
    return {
        "service": "GOST Formatter API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "format_single": "/api/format/single",
            "format_batch": "/api/format/batch",
            "parse": "/api/parse",
            "stats": "/api/stats",
            "docs": "/docs"
        }
    }


@app.get("/api/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "ok",
        "service": "GOST Formatter",
        "api_key_set": bool(os.getenv("ANTHROPIC_API_KEY"))
    }


@app.post("/api/format/single", response_model=FormatResponse)
async def format_single_source(request: SingleFormatRequest):
    """Форматирует один библиографический источник"""
    try:
        # Конвертируем в Source (с дефолтами для None значений)
        source = Source(
            id=request.source.id or 1,
            type=request.source.type or "book",
            authors=request.source.authors or [],
            title=request.source.title or "",
            year=request.source.year or 0,
            publisher=request.source.publisher,
            city=request.source.city,
            pages=request.source.pages,
            journal=request.source.journal,
            volume=request.source.volume,
            issue=request.source.issue,
            doi=request.source.doi,
            url=request.source.url,
            language=request.source.language or "ru"
        )

        # Определяем стандарт
        standard = Standard.GOST_2018 if request.standard == "GOST_2018" else Standard.VAK_RB

        # Форматируем
        result = agent.format_single(source, standard)

        return FormatResponse(
            id=result.id,
            original=result.original,
            formatted=result.formatted,
            errors_fixed=result.errors_fixed,
            confidence=result.confidence,
            standard_used=result.standard_used.value
        )

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ОШИБКА ФОРМАТИРОВАНИЯ: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка форматирования: {str(e)}")


@app.post("/api/format/batch", response_model=BatchFormatResponse)
async def format_batch_sources(request: BatchFormatRequest):
    """Форматирует пакет источников"""
    import time

    try:
        start_time = time.time()

        # Конвертируем в Source
        sources = [
            Source(
                id=s.id,
                type=s.type,
                authors=s.authors,
                title=s.title,
                year=s.year,
                publisher=s.publisher,
                city=s.city,
                pages=s.pages,
                journal=s.journal,
                volume=s.volume,
                issue=s.issue,
                doi=s.doi,
                url=s.url,
                language=s.language
            )
            for s in request.sources
        ]

        # Определяем стандарт
        standard = Standard.GOST_2018 if request.standard == "GOST_2018" else Standard.VAK_RB

        # Форматируем асинхронно
        results = await agent.format_batch_async(
            sources,
            standard,
            batch_size=request.batch_size,
            max_concurrent=5
        )

        processing_time = time.time() - start_time

        # Конвертируем результаты
        formatted_results = [
            FormatResponse(
                id=r.id,
                original=r.original,
                formatted=r.formatted,
                errors_fixed=r.errors_fixed,
                confidence=r.confidence,
                standard_used=r.standard_used.value
            )
            for r in results
        ]

        return BatchFormatResponse(
            results=formatted_results,
            total=len(formatted_results),
            success=len(formatted_results),
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ОШИБКА ПАКЕТНОГО ФОРМАТИРОВАНИЯ: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.post("/api/parse")
async def parse_unstructured_text(request: TextParseRequest):
    """Парсит неструктурированный текст"""
    try:
        sources = agent.parse_unstructured_text(request.text)

        return {
            "success": True,
            "sources_found": len(sources),
            "sources": [
                {
                    "id": s.id,
                    "type": s.type,
                    "authors": s.authors,
                    "title": s.title,
                    "year": s.year,
                    "publisher": s.publisher,
                    "city": s.city,
                    "pages": s.pages,
                    "journal": s.journal
                }
                for s in sources
            ]
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ОШИБКА ПАРСИНГА: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@app.get("/api/stats")
async def get_statistics():
    """Получить статистику"""
    stats = agent.get_statistics()
    return stats


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("GOST Formatter API Server")
    print("=" * 60)
    print("\n✅ Запуск сервера на http://localhost:8000")
    print("\n📍 Доступные эндпоинты:")
    print("  GET  /                      - Информация об API")
    print("  GET  /api/health            - Проверка работоспособности")
    print("  POST /api/format/single     - Форматирование одного источника")
    print("  POST /api/format/batch      - Пакетное форматирование")
    print("  POST /api/parse             - Парсинг текста")
    print("  GET  /api/stats             - Статистика")
    print("\n📚 Документация: http://localhost:8000/docs")
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
