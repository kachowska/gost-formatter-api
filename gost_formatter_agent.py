"""
ИИ-Агент GOST Formatter
Автоматическое форматирование библиографических записей
по стандартам ГОСТ Р 7.0.100-2018 и ВАК РБ
"""

import json
import asyncio
import logging
from typing import List, Dict, Optional
from anthropic import Anthropic, AsyncAnthropic
from dataclasses import dataclass
from enum import Enum


class Standard(Enum):
    """Поддерживаемые стандарты"""
    GOST_2018 = "GOST_2018"  # ГОСТ Р 7.0.100-2018 (РФ, Казахстан)
    VAK_RB = "VAK_RB"  # ВАК Республики Беларусь


@dataclass
class Source:
    """Структура библиографического источника"""
    id: int
    type: str  # book, article, dissertation, etc.
    authors: List[str]
    title: str
    year: int
    publisher: Optional[str] = None
    city: Optional[str] = None
    pages: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    language: str = "ru"


@dataclass
class FormattedResult:
    """Результат форматирования"""
    id: int
    original: str
    formatted: str
    errors_fixed: List[str]
    confidence: int  # 0-100%
    standard_used: Standard


class GOSTFormatterAgent:
    """
    Главный класс агента для форматирования библиографии
    """

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.logger = logging.getLogger(__name__)

        # Системный промпт с правилами
        self.system_prompt = self._build_system_prompt()

        # Статистика
        self.stats = {
            "processed": 0,
            "errors_fixed": 0,
            "avg_confidence": 0
        }

    def _build_system_prompt(self) -> str:
        """Создает системный промпт с полными правилами"""
        return """Ты - специализированный AI-агент для форматирования библиографических записей.

ТВОЯ МИССИЯ: Обеспечить 100% корректность форматирования по стандартам ГОСТ Р 7.0.100-2018 и ВАК РБ.

СТАНДАРТЫ:
1. ГОСТ Р 7.0.100-2018 (Россия, Казахстан)
2. ВАК РБ (Беларусь)

ПРАВИЛА ПУНКТУАЦИИ (КРИТИЧЕСКИ ВАЖНО):
- Тире: " – " (длинное тире U+2013 с пробелами)
- Двоеточие: " : " (с пробелами)
- Запятая: ", " (с пробелом после)
- Точка: ". " (с пробелом после)
- Косая черта: " / " (с пробелами)
- Двойная косая черта: " // " (с пробелами, для статей)

ФОРМАТ АВТОРОВ:
- 1-4 автора: Фамилия, И. О., Фамилия, И. О., Фамилия, И. О.
- Более 4 авторов: Фамилия, И. О. [и др.]
- После названия повторить всех авторов: / И. О. Фамилия, И. О. Фамилия

ШАБЛОНЫ ПО ТИПАМ:

1. КНИГА (ГОСТ):
Фамилия, И. О. Название книги / И. О. Фамилия, И. О. Фамилия. – Город : Издательство, Год. – Кол-во с.

Пример:
Иванов, И. И. Основы программирования / И. И. Иванов, П. П. Петров. – Москва : Наука, 2023. – 320 с.

2. СТАТЬЯ ИЗ ЖУРНАЛА (ГОСТ):
Фамилия, И. О. Название статьи / И. О. Фамилия // Название журнала. – Год. – Т. X, № Y. – С. X-Y.

Пример:
Сидоров, С. С. Новые методы анализа / С. С. Сидоров // Вестник науки. – 2024. – Т. 15, № 3. – С. 45-52.

3. ДИССЕРТАЦИЯ (ГОСТ):
Фамилия, И. О. Название диссертации : дис. ... канд. наук : код специальности / И. О. Фамилия. – Город, Год. – Кол-во с.

4. ЭЛЕКТРОННЫЙ РЕСУРС (ГОСТ):
Фамилия, И. О. Название / И. О. Фамилия. – URL: https://... (дата обращения: ДД.ММ.ГГГГ).

ВАК РБ - аналогичные правила, но с особенностями:
- Для официальных документов: особый формат с номерами и датами
- Для многотомных изданий: указание "в X т." после названия

ЭТАПЫ РАБОТЫ:
1. Проанализируй входные данные
2. Нормализуй авторов (правильный формат инициалов)
3. Создай запись по шаблону
4. Провалидируй пунктуацию и пробелы
5. Верни JSON с результатом

ФОРМАТ ОТВЕТА (только JSON, без markdown):
{
  "formatted": "полная отформатированная запись",
  "errors_fixed": ["список исправленных ошибок"],
  "confidence": 95
}

ЗАПРЕЩЕНО:
- Использовать короткое тире (-) вместо длинного (–)
- Пропускать пробелы вокруг знаков препинания
- Изменять порядок элементов
- Добавлять информацию, которой нет во входных данных

КАЧЕСТВО: 100% точность - это единственный приемлемый результат."""

    def format_single(self, source: Source, standard: Standard) -> FormattedResult:
        """
        Форматирует один источник

        Args:
            source: Исходные данные источника
            standard: Стандарт форматирования (GOST или VAK)

        Returns:
            FormattedResult с отформатированной записью
        """
        # Формируем запрос
        user_prompt = f"""Отформатируй библиографический источник по стандарту {standard.value}.

Данные источника:
{json.dumps(source.__dict__, ensure_ascii=False, indent=2)}

Верни только JSON с полями: formatted, errors_fixed, confidence."""

        # Отправляем в Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Проверяем и логируем ответ Claude
        response_text = response.content[0].text if response.content else ""
        self.logger.info("Claude ответ format_single (первые 500 символов): %s", response_text[:500])
        
        if not response_text or not response_text.strip():
            raise ValueError("Claude вернул пустой ответ. Проверьте API ключ и баланс кредитов на console.anthropic.com")
        
        # Попытка парсинга JSON
        try:
            # Убираем возможные markdown блоки
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```")[1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                clean_text = clean_text.strip()
            
            result_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            self.logger.exception("Не удалось распарсить JSON от Claude в format_single; ответ: %s", response_text)
            raise ValueError(f"Claude вернул некорректный JSON: {e!r}") from e

        # Обновляем статистику
        self.stats["processed"] += 1
        self.stats["errors_fixed"] += len(result_json["errors_fixed"])

        return FormattedResult(
            id=source.id,
            original=f"{source.authors[0] if source.authors else ''} - {source.title}",
            formatted=result_json["formatted"],
            errors_fixed=result_json["errors_fixed"],
            confidence=result_json["confidence"],
            standard_used=standard
        )

    def format_batch(
        self,
        sources: List[Source],
        standard: Standard,
        batch_size: int = 20
    ) -> List[FormattedResult]:
        """
        Форматирует пакет источников (синхронная версия)

        Args:
            sources: Список источников
            standard: Стандарт форматирования
            batch_size: Размер пакета (по умолчанию 20)

        Returns:
            Список отформатированных результатов
        """
        results = []

        for i in range(0, len(sources), batch_size):
            batch = sources[i:i + batch_size]

            # Формируем запрос для батча
            sources_json = [s.__dict__ for s in batch]
            user_prompt = f"""Отформатируй следующие {len(batch)} источников по стандарту {standard.value}.

Источники:
{json.dumps(sources_json, ensure_ascii=False, indent=2)}

Для каждого источника создай библиографическую запись.

Верни JSON-массив с результатами:
[
  {{
    "id": 1,
    "formatted": "...",
    "errors_fixed": [...],
    "confidence": 95
  }},
  ...
]"""

            # Отправляем в Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Проверяем и логируем ответ Claude
            response_text = response.content[0].text if response.content else ""
            self.logger.info("Claude ответ format_batch (первые 300 символов): %s", response_text[:300])
            
            if not response_text or not response_text.strip():
                raise ValueError("Claude вернул пустой ответ в format_batch")
            
            # Попытка парсинга JSON
            try:
                clean_text = response_text.strip()
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("```")[1]
                    if clean_text.startswith("json"):
                        clean_text = clean_text[4:]
                    clean_text = clean_text.strip()
                
                batch_results = json.loads(clean_text)
            except json.JSONDecodeError as e:
                self.logger.exception("Не удалось распарсить JSON от Claude в format_batch; ответ: %s", response_text[:1000])
                raise ValueError(f"Claude вернул некорректный JSON: {e!r}") from e

            # Конвертируем в FormattedResult
            for r in batch_results:
                original_source = next(s for s in batch if s.id == r["id"])
                results.append(FormattedResult(
                    id=r["id"],
                    original=f"{original_source.authors[0]} - {original_source.title}",
                    formatted=r["formatted"],
                    errors_fixed=r["errors_fixed"],
                    confidence=r["confidence"],
                    standard_used=standard
                ))

            # Обновляем статистику
            self.stats["processed"] += len(batch_results)
            self.stats["errors_fixed"] += sum(len(r["errors_fixed"]) for r in batch_results)

        return results

    async def format_batch_async(
        self,
        sources: List[Source],
        standard: Standard,
        batch_size: int = 20,
        max_concurrent: int = 5
    ) -> List[FormattedResult]:
        """
        Форматирует пакет источников параллельно (асинхронная версия)

        Args:
            sources: Список источников
            standard: Стандарт форматирования
            batch_size: Размер одного пакета
            max_concurrent: Максимум параллельных запросов

        Returns:
            Список отформатированных результатов
        """
        # Разбиваем на батчи
        batches = [sources[i:i + batch_size] for i in range(0, len(sources), batch_size)]

        # Семафор для ограничения параллельности
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_one_batch(batch: List[Source]) -> List[FormattedResult]:
            async with semaphore:
                sources_json = [s.__dict__ for s in batch]
                user_prompt = f"""Отформатируй {len(batch)} источников по стандарту {standard.value}.

Источники:
{json.dumps(sources_json, ensure_ascii=False, indent=2)}

Верни JSON-массив результатов."""

                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )

                # Проверяем и логируем ответ Claude
                response_text = response.content[0].text if response.content else ""
                self.logger.info("Claude async ответ (первые 300 символов): %s", response_text[:300])
                
                if not response_text or not response_text.strip():
                    raise ValueError("Claude вернул пустой ответ в async format_batch")
                
                # Попытка парсинга JSON
                try:
                    clean_text = response_text.strip()
                    if clean_text.startswith("```"):
                        clean_text = clean_text.split("```")[1]
                        if clean_text.startswith("json"):
                            clean_text = clean_text[4:]
                        clean_text = clean_text.strip()
                    
                    batch_results = json.loads(clean_text)
                except json.JSONDecodeError as e:
                    self.logger.exception("Не удалось распарсить JSON от Claude в async format_batch; ответ: %s", response_text[:1000])
                    raise ValueError(f"Claude вернул некорректный JSON: {e!r}") from e

                return [
                    FormattedResult(
                        id=r["id"],
                        original=f"{next(s for s in batch if s.id == r['id']).title}",
                        formatted=r["formatted"],
                        errors_fixed=r["errors_fixed"],
                        confidence=r["confidence"],
                        standard_used=standard
                    )
                    for r in batch_results
                ]

        # Обрабатываем все батчи параллельно
        all_results = await asyncio.gather(*[process_one_batch(b) for b in batches])

        # Объединяем результаты
        results = [item for sublist in all_results for item in sublist]

        # Обновляем статистику
        self.stats["processed"] += len(results)
        self.stats["errors_fixed"] += sum(len(r.errors_fixed) for r in results)

        return results

    def parse_unstructured_text(self, text: str) -> List[Source]:
        """
        Парсит неструктурированный текст со списком источников

        Args:
            text: Текст с источниками (нумерованный список)

        Returns:
            Список распарсенных источников
        """
        user_prompt = f"""Извлеки библиографические данные из следующего текста.

Текст может содержать список источников в любом формате.

Текст:
{text}

Для каждого источника извлеки:
- id (порядковый номер)
- type (book, article, dissertation, conference, etc.)
- authors (массив строк "Фамилия, И. О.")
- title
- year
- publisher, city (если книга)
- journal, volume, issue, pages (если статья)
- doi, url (если есть)

Верни JSON-массив объектов.

Пример:
[
  {{
    "id": 1,
    "type": "book",
    "authors": ["Иванов, И. И.", "Петров, П. П."],
    "title": "Название книги",
    "year": 2023,
    "city": "Москва",
    "publisher": "Наука",
    "pages": "320"
  }},
  ...
]"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system="Ты - эксперт по извлечению библиографических данных. Анализируй текст и извлекай структурированную информацию.",
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Проверяем и логируем ответ Claude
        response_text = response.content[0].text if response.content else ""
        self.logger.info("Claude ответ parse_unstructured_text (первые 500 символов): %s", response_text[:500])
        
        if not response_text or not response_text.strip():
            raise ValueError("Claude вернул пустой ответ. Возможно проблема с API ключом или кредитами.")
        
        # Попытка парсинга JSON
        try:
            # Убираем возможные markdown блоки
            clean_text = response_text.strip()
            if clean_text.startswith("```"):
                # Извлекаем JSON из markdown блока
                clean_text = clean_text.split("```")[1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                clean_text = clean_text.strip()
            
            parsed_data = json.loads(clean_text)
        except json.JSONDecodeError as e:
            self.logger.exception("Не удалось распарсить JSON от Claude в parse_unstructured_text; ответ: %s", response_text[:1000])
            raise ValueError(f"Claude вернул некорректный JSON: {e!r}") from e

        # Конвертируем в Source объекты
        sources = []
        for data in parsed_data:
            sources.append(Source(
                id=data["id"],
                type=data["type"],
                authors=data.get("authors", []),
                title=data["title"],
                year=data["year"],
                publisher=data.get("publisher"),
                city=data.get("city"),
                pages=data.get("pages"),
                journal=data.get("journal"),
                volume=data.get("volume"),
                issue=data.get("issue"),
                doi=data.get("doi"),
                url=data.get("url"),
                language=data.get("language", "ru")
            ))

        return sources

    def export_to_bibtex(self, results: List[FormattedResult]) -> str:
        """Экспортирует результаты в BibTeX формат"""
        bibtex_entries = []

        for r in results:
            # Упрощенная конвертация (можно расширить)
            entry = f"""@misc{{ref{r.id},
  title = {{{r.formatted}}},
  year = {{unknown}}
}}"""
            bibtex_entries.append(entry)

        return "\n\n".join(bibtex_entries)

    def export_to_text(self, results: List[FormattedResult]) -> str:
        """Экспортирует результаты в текстовый список"""
        return "\n".join([f"{r.id}. {r.formatted}" for r in results])

    def get_statistics(self) -> Dict:
        """Возвращает статистику работы агента"""
        return {
            "processed_total": self.stats["processed"],
            "errors_fixed": self.stats["errors_fixed"],
            "avg_confidence": self.stats.get("avg_confidence", 0)
        }


# ==================== ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ====================

def example_single_source():
    """Пример: форматирование одного источника"""
    agent = GOSTFormatterAgent(api_key="your-api-key-here")

    source = Source(
        id=1,
        type="book",
        authors=["Иванов, И. И.", "Петров, П. П."],
        title="Основы машинного обучения",
        year=2023,
        city="Москва",
        publisher="Наука",
        pages="320"
    )

    result = agent.format_single(source, Standard.GOST_2018)

    print("Отформатированная запись:")
    print(result.formatted)
    print(f"\nИсправлено ошибок: {len(result.errors_fixed)}")
    print(f"Уверенность: {result.confidence}%")


def example_batch_processing():
    """Пример: пакетная обработка 50 источников"""
    agent = GOSTFormatterAgent(api_key="your-api-key-here")

    # Создаем 50 тестовых источников
    sources = []
    for i in range(1, 51):
        sources.append(Source(
            id=i,
            type="article" if i % 2 == 0 else "book",
            authors=[f"Автор{i}, А. А."],
            title=f"Название работы номер {i}",
            year=2020 + (i % 5),
            city="Минск" if i % 3 == 0 else "Москва",
            publisher="Издательство",
            journal="Журнал" if i % 2 == 0 else None,
            pages="100-110" if i % 2 == 0 else "250"
        ))

    # Форматируем батчами
    results = agent.format_batch(sources, Standard.VAK_RB, batch_size=20)

    print(f"Обработано источников: {len(results)}")
    print(f"Общая статистика: {agent.get_statistics()}")

    # Экспортируем в текст
    text_output = agent.export_to_text(results)
    with open("bibliography.txt", "w", encoding="utf-8") as f:
        f.write(text_output)

    print("Результаты сохранены в bibliography.txt")


async def example_async_processing():
    """Пример: параллельная обработка 100 источников"""
    agent = GOSTFormatterAgent(api_key="your-api-key-here")

    # Создаем 100 источников
    sources = [
        Source(
            id=i,
            type="book",
            authors=[f"Фамилия{i}, И. О."],
            title=f"Исследование {i}",
            year=2024,
            city="Москва",
            publisher="Наука",
            pages="200"
        )
        for i in range(1, 101)
    ]

    # Обрабатываем параллельно (5 батчей по 20 источников одновременно)
    results = await agent.format_batch_async(
        sources,
        Standard.GOST_2018,
        batch_size=20,
        max_concurrent=5
    )

    print(f"Обработано: {len(results)} источников")
    print("Первые 3 результата:")
    for r in results[:3]:
        print(f"{r.id}. {r.formatted}")


def example_parse_text():
    """Пример: парсинг неструктурированного текста"""
    agent = GOSTFormatterAgent(api_key="your-api-key-here")

    # Текст со списком источников в произвольном формате
    text = """
    1. Иванов И.И., Петров П.П. Основы программирования. М.: Наука, 2023. 320 с.
    2. Сидоров С.С. Новые методы анализа // Вестник науки. 2024. Т. 15, № 3. С. 45-52.
    3. Козлов, А.Б. Искусственный интеллект, Минск, БГУ, 2022, 400 стр
    """

    # Парсим текст
    sources = agent.parse_unstructured_text(text)

    print(f"Распознано источников: {len(sources)}")

    # Форматируем по ГОСТ
    results = agent.format_batch(sources, Standard.GOST_2018)

    print("\nОтформатированные записи:")
    for r in results:
        print(f"{r.id}. {r.formatted}")


if __name__ == "__main__":
    print("ИИ-Агент GOST Formatter")
    print("=" * 50)
    print("\nДоступные примеры:")
    print("1. example_single_source() - один источник")
    print("2. example_batch_processing() - 50 источников")
    print("3. example_async_processing() - 100 источников параллельно")
    print("4. example_parse_text() - парсинг текста")
    print("\nЗамените 'your-api-key-here' на ваш ключ Anthropic API")
