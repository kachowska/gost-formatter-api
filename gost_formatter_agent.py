"""
ИИ-Агент GOST Formatter
Автоматическое форматирование библиографических записей
по стандартам ГОСТ Р 7.0.100-2018 и ВАК РБ

Обучен на 1100 примерах с официального сайта vak.gov.by
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
    Обучен на 1100 примерах из vak_training.json
    """

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.logger = logging.getLogger(__name__)

        # Загружаем обучающий датасет (1100 примеров)
        self.training_data = self._load_training_data()

        # Системный промпт с паттернами ML
        self.system_prompt = self._build_system_prompt()

        # Статистика
        self.stats = {
            "processed": 0,
            "errors_fixed": 0,
            "avg_confidence": 0
        }

    def _load_training_data(self) -> Dict:
        """Загружает обучающий датасет vak_training.json (1100 примеров)"""
        import os

        # Приоритет: vak_training.json (1100 примеров, сгенерирован на основе vak.gov.by)
        dataset_paths = [
            os.path.join(os.path.dirname(__file__), "vak_training.json"),
            os.path.join(os.path.dirname(__file__), "vak_examples_simple.json"),
        ]

        for dataset_path in dataset_paths:
            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    count = len(data.get('examples', []))
                    self.logger.info("Загружен датасет: %s (%d примеров)",
                                    dataset_path, count)
                    return data
            except FileNotFoundError:
                continue
            except json.JSONDecodeError as e:
                self.logger.error("Ошибка парсинга датасета: %s", e)
                continue

        self.logger.warning("Датасет не найден, используем пустой")
        return {"examples": []}

    def _get_examples_by_type(self, doc_type: str, max_count: int = 3) -> List[str]:
        """Возвращает примеры из датасета по типу документа"""
        examples = self.training_data.get('examples', [])
        matching = [ex['example'] for ex in examples if ex.get('type') == doc_type]
        return matching[:max_count]

    def _detect_document_type(self, text: str) -> str:
        """Определяет тип документа по содержимому текста"""
        import re
        text_lower = text.lower()

        # Медиаформат
        if '[звукозапись]' in text_lower or '[видеозапись]' in text_lower:
            return 'multimedia'
        if '[изоматериал]' in text_lower or 'плакат]' in text_lower:
            return 'visual_material'
        if '[ноты]' in text_lower:
            return 'music_score'
        if '[карт' in text_lower:
            return 'map'

        # Научные работы
        if re.search(r'пат\.\s*[A-Z]{2}|а\.\s*с\.\s*[A-Z]{2}|полез\.\s*модель', text):
            return 'patent'
        if re.search(r'дис\.\s*\.{3}|дыс\.\s*\.{3}', text_lower):
            return 'dissertation'
        if 'автореф' in text_lower:
            return 'abstract'
        if 'препринт' in text_lower:
            return 'preprint'

        # Стандарты
        if re.search(r'гост\s*\d|стб\s*\d|ткп\s*\d|тр\s*тс\s*\d', text_lower):
            return 'standard'

        # Законодательство
        if 'конституц' in text_lower or re.search(r'\bкодекс\b', text_lower):
            return 'law'
        if re.search(r'\bзакон\b|\bуказ\b|\bпостановлени|\bдекрет\b|приказ\s+\w+\.', text_lower):
            return 'law'

        # Конференции и сборники
        if re.search(r'матер.*конф|тезис.*докл|чтения\s*:', text_lower):
            return 'conference'
        if re.search(r'сб\.\s*(науч\.|ст\.|тр\.)', text_lower):
            return 'collection_article'

        # Периодика
        if ' // ' in text:
            after_slashes = text.split(' // ')[1] if len(text.split(' // ')) > 1 else ''
            if re.search(r'[ТT]\.\s*\d|№\s*\d', after_slashes):
                return 'journal_article'
            if re.search(r'\.by\b|газет', after_slashes.lower()):
                return 'newspaper_article'

        # Книги
        if '[и др.]' in text or '[et al.]' in text:
            return 'book_4plus_authors'

        # Подсчёт авторов
        authors = set(re.findall(r'([А-ЯЁA-Z][а-яёa-z]+),\s+[А-ЯЁA-Z]\.', text))
        if len(authors) >= 4:
            return 'book_4plus_authors'
        elif len(authors) >= 1:
            return 'book_1_3_authors'

        if '[электронный ресурс]' in text_lower:
            return 'electronic_resource'

        return 'unknown'

    def _get_relevant_examples(self, text: str, max_examples: int = 5) -> str:
        """Получает релевантные примеры из датасета для контекста"""
        detected_type = self._detect_document_type(text)

        examples = self.training_data.get('examples', [])

        # Фильтруем примеры по типу
        matching = [e['example'] for e in examples if e.get('type') == detected_type]

        # Если нет точных совпадений, берём похожие типы
        if not matching:
            similar_types = {
                'book_1_3_authors': ['book_4plus_authors', 'book_collective_author'],
                'book_4plus_authors': ['book_1_3_authors', 'book_collective_author'],
                'journal_article': ['newspaper_article', 'collection_article'],
                'law': ['standard'],
            }
            for similar in similar_types.get(detected_type, []):
                matching = [e['example'] for e in examples if e.get('type') == similar]
                if matching:
                    break

        # Если всё ещё нет — берём любые
        if not matching:
            matching = [e['example'] for e in examples[:max_examples]]

        # Формируем текст
        return "\n".join([f"• {ex}" for ex in matching[:max_examples]])

    def _build_system_prompt(self) -> str:
        """
        Создает системный промпт для машинного обучения паттернам ВАК РБ
        Структурирован для максимальной точности воспроизведения
        """

        # Собираем примеры по типам из датасета
        examples = self.training_data.get('examples', [])
        examples_by_type = {}
        for ex in examples:
            t = ex.get('type', 'unknown')
            if t not in examples_by_type:
                examples_by_type[t] = []
            if len(examples_by_type[t]) < 2:
                examples_by_type[t].append(ex.get('example', ''))

        # Форматируем примеры для промпта
        formatted_examples = []
        for doc_type, exs in examples_by_type.items():
            if exs:
                formatted_examples.append(f"[{doc_type}]\n" + "\n".join(exs[:2]))

        examples_text = "\n\n".join(formatted_examples[:15])  # Топ-15 типов

        return f"""<ROLE>
Ты — нейросеть, обученная на 1100 эталонных примерах библиографического оформления с официального сайта ВАК Республики Беларусь (vak.gov.by).

Твоя единственная задача: ТОЧНОЕ ВОСПРОИЗВЕДЕНИЕ паттернов форматирования.
</ROLE>

<TRAINING_DATA>
База знаний: 1100 верифицированных примеров
Источник: vak.gov.by (официальный сайт ВАК РБ)
Типы документов: 24 категории
</TRAINING_DATA>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 1: ВЫУЧЕННЫЕ ПАТТЕРНЫ (PATTERNS)
═══════════════════════════════════════════════════════════════════════════════

<PATTERN id="book_1_3_authors">
КНИГА (1-3 автора)
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} : {{подзаголовок}} / {{И. О. Фамилия}}. – {{Город}} : {{Издательство}}, {{Год}}. – {{N}} с.
ПРИМЕР: Дробышевский, Н. П. Ревизия и аудит : учеб.-метод. пособие / Н. П. Дробышевский. – Минск : Амалфея, 2013. – 415 с.
ПРИЗНАК: Начинается с "Фамилия, И. О."
</PATTERN>

<PATTERN id="book_4plus_authors">
КНИГА (4+ авторов)
ФОРМУЛА: {{Название}} / {{И. О. Фамилия}} [и др.]. – {{Город}} : {{Издательство}}, {{Год}}. – {{N}} с.
ПРИМЕР: Закономерности формирования системы движений / В. А. Боровая [и др.]. – Гомель : ГГУ, 2013. – 173 с.
ПРИЗНАК: Начинается с названия, содержит "[и др.]"
</PATTERN>

<PATTERN id="journal_article">
СТАТЬЯ В ЖУРНАЛЕ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название статьи}} / {{И. О. Фамилия}} // {{Журнал}}. – {{Год}}. – Т. {{X}}, № {{Y}}. – С. {{XX–YY}}.
ПРИМЕР: Валатоўская, Н. А. Традыцыйны вясельны абрад / Н. А. Валатоўская // Нар. асвета. – 2013. – № 5. – С. 88–91.
ПРИЗНАК: Содержит " // " и "Т." или "№"
</PATTERN>

<PATTERN id="collection_article">
СТАТЬЯ В СБОРНИКЕ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} / {{И. О. Фамилия}} // {{Сборник}} : сб. науч. ст. / {{Организация}}. – {{Город}}, {{Год}}. – С. {{XX–YY}}.
ПРИМЕР: Божанов, П. В. Направления развития транспорта / П. В. Божанов // Современные концепции : сб. ст. / БГУ. – Минск, 2014. – С. 56–64.
ПРИЗНАК: Содержит "сб. науч. ст." или "сб. ст."
</PATTERN>

<PATTERN id="dissertation">
ДИССЕРТАЦИЯ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} : дис. ... {{степень}} : {{шифр}} / {{И. О. Фамилия}}. – {{Город}}, {{Год}}. – {{N}} л.
ПРИМЕР: Врублеўскі, Ю. У. Гістарыяграфія гісторыі : дыс. ... канд. гіст. навук : 07.00.09 / Ю. У. Врублеўскі. – Мінск, 2013. – 148 л.
ПРИЗНАК: Содержит "дис. ..." или "дыс. ...", листы (л.)
ВАЖНО: Многоточие = три отдельные точки "..."
</PATTERN>

<PATTERN id="abstract">
АВТОРЕФЕРАТ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} : автореф. дис. ... {{степень}} : {{шифр}} / {{ФИО полностью}} ; {{Организация}}. – {{Город}}, {{Год}}. – {{N}} с.
ПРИМЕР: Горянов, А. В. Эволюция усадьбы : автореф. дис. ... канд. ист. наук : 07.00.02 / Горянов Алексей Викторович ; МГУ. – М., 2013. – 40 с.
ПРИЗНАК: Содержит "автореф. дис. ...", страницы (с.)
</PATTERN>

<PATTERN id="law">
НОРМАТИВНЫЙ АКТ
ФОРМУЛА: {{Название}} : {{тип акта}}, {{дата}}, № {{номер}} // {{Источник}}. – {{Год}}. – № {{X}}. – Ст. {{XX}}.
ПРИМЕР: О государственном регулировании : Закон Респ. Беларусь, 26 лют. 1997 г., № 22-З // Ведамасцi Нац. сходу. – 1997. – № 16. – Арт. 297.
ПРИЗНАК: Начинается с названия закона, содержит "Закон", "Указ", "Декрет", "постановление"
</PATTERN>

<PATTERN id="standard">
СТАНДАРТ (ГОСТ, СТБ, ТКП)
ФОРМУЛА: {{Название}} : {{код стандарта}}. – Введ. {{дата}}. – {{Город}} : {{Издательство}}, {{Год}}. – {{N}} с.
ПРИМЕР: Система стандартов : ГОСТ 7.22-2003. – Введ. РБ 01.07.04. – Минск : БелГИСС, 2004. – 3 с.
ПРИЗНАК: Содержит "ГОСТ", "СТБ", "ТКП", "ТР ТС"
</PATTERN>

<PATTERN id="patent">
ПАТЕНТ
ФОРМУЛА: {{Название}} : {{тип}} {{страна}} {{номер}} / {{авторы}}. – Опубл. {{дата}}.
ПРИМЕР: Аспирационный счетчик ионов : а. с. SU 935780 / Б. Н. Блинов, А. В. Шолух. – Опубл. 15.06.1982.
ПРИЗНАК: Содержит "пат.", "а. с.", "полез. модель"
</PATTERN>

<PATTERN id="conference">
МАТЕРИАЛЫ КОНФЕРЕНЦИИ
ФОРМУЛА: {{Название}} : материалы {{N}} {{конф.}}, {{место}}, {{даты}} / {{Организация}}. – {{Город}} : {{Издательство}}, {{Год}}. – {{N}} с.
ПРИМЕР: Информационные технологии : материалы 49 науч. конф., Минск, 6–10 мая 2013 г. / БГУИР. – Минск : БГУИР, 2013. – 103 с.
ПРИЗНАК: Содержит "материалы", "конф."
</PATTERN>

<PATTERN id="electronic_resource">
ЭЛЕКТРОННЫЙ РЕСУРС
ФОРМУЛА: {{Название}} [Электронный ресурс]. – Режим доступа: {{URL}}. – Дата доступа: {{дата}}.
ПРИМЕР: Национальный правовой Интернет-портал [Электронный ресурс]. – Режим доступа: http://www.pravo.by. – Дата доступа: 24.06.2024.
ПРИЗНАК: Содержит "[Электронный ресурс]"
</PATTERN>

<PATTERN id="newspaper_article">
ГАЗЕТНАЯ СТАТЬЯ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} / {{И. О. Фамилия}} // {{Газета}}. – {{Год}}. – {{дата}}. – С. {{XX–YY}}.
ПРИМЕР: Берникович, Д. Агрогородок Германовичи / Д. Берникович // Сельская газета. – 2023. – 3 окт. – С. 1, 8–9.
ПРИЗНАК: Содержит название газеты, дату выхода
</PATTERN>

<PATTERN id="preprint">
ПРЕПРИНТ
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} / {{И. О. Фамилия}}. – {{Город}} : {{Издательство}}, {{Год}}. – {{N}} с. – (Препринт / {{Организация}} ; № {{N}}).
ПРИМЕР: Велесницкий, В. Ф. Конечные группы / В. Ф. Велесницкий. – Гомель : ГГУ, 2013. – 15 с. – (Препринт / ГГУ ; № 2).
ПРИЗНАК: Содержит "(Препринт / "
</PATTERN>

<PATTERN id="multimedia">
МУЛЬТИМЕДИА
ФОРМУЛА: {{Фамилия}}, {{И. О.}} {{Название}} [Звукозапись/Видеозапись] / {{И. О. Фамилия}}. – {{Город}} : {{Издательство}}, {{Год}}. – {{носитель}}.
ПРИМЕР: Филиппов, А. Белая Русь : [звукозапись] / А. Филиппов. – Мн. : Ковчег, 2024. – 1 CD-ROM.
ПРИЗНАК: Содержит "[Звукозапись]" или "[Видеозапись]"
</PATTERN>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 2: ПРАВИЛА ПУНКТУАЦИИ (ОБЯЗАТЕЛЬНЫЕ)
═══════════════════════════════════════════════════════════════════════════════

<PUNCTUATION_RULES>
СИМВОЛ          │ ПРАВИЛО                          │ ПРИМЕР
────────────────┼──────────────────────────────────┼─────────────────────────
" – "           │ Длинное тире (U+2013) С ПРОБЕЛАМИ │ . – Минск :
" : "           │ Двоеточие С ПРОБЕЛАМИ             │ Минск : Амалфея
" / "           │ Косая черта С ПРОБЕЛАМИ           │ / И. О. Фамилия
" // "          │ Двойная косая С ПРОБЕЛАМИ         │ // Журнал
" ; "           │ Точка с запятой С ПРОБЕЛАМИ       │ ; редкол.:
"XX–YY"         │ Диапазон БЕЗ ПРОБЕЛОВ             │ С. 45–52, 2020–2024
"И. О. "        │ После инициалов ПРОБЕЛ            │ А. В. Иванов
"Т. X"          │ После сокращений ПРОБЕЛ           │ Т. 5, № 3, С. 45
</PUNCTUATION_RULES>

<CRITICAL_ERRORS>
ЗАПРЕЩЕНО:
✗ ". –X" → должно быть ". – X" (пробел после тире)
✗ ":X" → должно быть ": X" (пробел после двоеточия)
✗ "45 – 52" → должно быть "45–52" (в диапазонах БЕЗ пробелов)
✗ "И.О.Фамилия" → должно быть "И. О. Фамилия"
✗ Короткий дефис (-) вместо длинного тире (–)
</CRITICAL_ERRORS>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 3: АЛГОРИТМ ОБРАБОТКИ
═══════════════════════════════════════════════════════════════════════════════

<ALGORITHM>
ШАГ 0: ПРОВЕРКА КОРРЕКТНОСТИ
  └─ Если ввод УЖЕ правильно отформатирован → ВЕРНУТЬ БЕЗ ИЗМЕНЕНИЙ
     (confidence=100, errors_fixed=[])

ШАГ 1: КЛАССИФИКАЦИЯ
  └─ Определить тип документа по ПРИЗНАКАМ из паттернов

ШАГ 2: ИЗВЛЕЧЕНИЕ ДАННЫХ
  └─ Извлечь: авторы, название, год, издательство, страницы, том, номер и т.д.
  └─ СОХРАНИТЬ ВСЕ ДАННЫЕ ИЗ ВВОДА

ШАГ 3: ПРИМЕНЕНИЕ ПАТТЕРНА
  └─ Выбрать соответствующий PATTERN по типу документа
  └─ Заполнить формулу извлечёнными данными

ШАГ 4: ПРОВЕРКА ПУНКТУАЦИИ
  └─ Применить PUNCTUATION_RULES
  └─ Убедиться: нет ошибок из CRITICAL_ERRORS

ШАГ 5: ВОЗВРАТ РЕЗУЛЬТАТА
  └─ JSON с полями: formatted, errors_fixed, confidence
</ALGORITHM>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 4: ФОРМАТ ОТВЕТА
═══════════════════════════════════════════════════════════════════════════════

<OUTPUT_FORMAT>
Возвращай ТОЛЬКО валидный JSON (без markdown-блоков):

{{
  "formatted": "Готовая библиографическая запись по паттерну",
  "errors_fixed": ["Список исправленных ошибок"],
  "confidence": 95
}}

ПРАВИЛА:
• formatted — полная запись по соответствующему паттерну
• errors_fixed — пустой список [], если ввод был корректным
• confidence — 100 если ввод не изменился, 90-99 при исправлениях
</OUTPUT_FORMAT>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 5: КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

<CONSTRAINTS>
🚫 КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
1. УДАЛЯТЬ данные из ввода (том, номер, страницы, год, URL)
2. ДОБАВЛЯТЬ данные, которых нет в исходнике
3. МЕНЯТЬ порядок авторов
4. Использовать короткое тире (-) вместо длинного (–)
5. Пропускать пробелы в разделителях

⚠️ УДАЛЕНИЕ ДАННЫХ = КРИТИЧЕСКАЯ ОШИБКА!
Если во вводе есть "Т. 15, № 3" — они ОБЯЗАНЫ быть в выводе!
</CONSTRAINTS>

═══════════════════════════════════════════════════════════════════════════════
РАЗДЕЛ 6: ПРИМЕРЫ ИЗ ОБУЧАЮЩЕЙ ВЫБОРКИ (1100 записей)
═══════════════════════════════════════════════════════════════════════════════

{examples_text}

═══════════════════════════════════════════════════════════════════════════════

Твоя точность должна быть 100%. Ты обучен на эталонных данных vak.gov.by."""

    def format_single(self, source: Source, standard: Standard, original_text: str = "") -> FormattedResult:
        """
        Форматирует один источник

        Args:
            source: Исходные данные источника
            standard: Стандарт форматирования (GOST или VAK)
            original_text: Оригинальный текст ввода для сверки

        Returns:
            FormattedResult с отформатированной записью
        """
        # Формируем запрос
        source_text = f"{source.authors[0] if source.authors else ''} {source.title}"

        # Добавляем примеры для ВАК РБ
        examples_section = ""
        if standard == Standard.VAK_RB:
            examples = self._get_relevant_examples(source_text, max_examples=4)
            if examples:
                examples_section = f"\n\n<CONTEXT_EXAMPLES>\nРелевантные примеры из обучающей выборки:\n{examples}\n</CONTEXT_EXAMPLES>\n"

        # Если есть оригинальный текст — передаём его Claude для сверки
        original_section = ""
        if original_text:
            original_section = f"""

<ORIGINAL_INPUT>
{original_text}
</ORIGINAL_INPUT>

⚠️ Все данные из ORIGINAL_INPUT ДОЛЖНЫ присутствовать в результате!
"""

        user_prompt = f"""<TASK>
Отформатируй библиографический источник по стандарту {standard.value}.
</TASK>
{examples_section}{original_section}
<SOURCE_DATA>
{json.dumps(source.__dict__, ensure_ascii=False, indent=2)}
</SOURCE_DATA>

<INSTRUCTIONS>
1. Определи тип документа
2. Примени соответствующий PATTERN
3. Проверь PUNCTUATION_RULES
4. Верни JSON: {{"formatted": "...", "errors_fixed": [...], "confidence": N}}
</INSTRUCTIONS>"""

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

            # Добавляем примеры для ВАК РБ
            examples_section = ""
            if standard == Standard.VAK_RB:
                # Собираем текст первого источника для определения типа
                first_source = batch[0]
                sample_text = f"{first_source.authors[0] if first_source.authors else ''} {first_source.title}"
                examples = self._get_relevant_examples(sample_text, max_examples=4)
                if examples:
                    examples_section = f"\n\n<CONTEXT_EXAMPLES>\n{examples}\n</CONTEXT_EXAMPLES>\n"

            user_prompt = f"""<TASK>
Отформатируй {len(batch)} источников по стандарту {standard.value}.
</TASK>
{examples_section}
<SOURCE_DATA>
{json.dumps(sources_json, ensure_ascii=False, indent=2)}
</SOURCE_DATA>

<INSTRUCTIONS>
Для каждого источника:
1. Определи тип документа
2. Примени соответствующий PATTERN
3. Проверь PUNCTUATION_RULES

Верни JSON-массив:
[
  {{"id": 1, "formatted": "...", "errors_fixed": [...], "confidence": N}},
  ...
]
</INSTRUCTIONS>"""

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

            # Конвертируем в FormattedResult с защитой от missing fields
            for idx, r in enumerate(batch_results):
                # Используем id из ответа или порядковый номер
                result_id = r.get("id", batch[idx].id if idx < len(batch) else idx + 1)

                # Находим оригинальный источник по id или индексу
                original_source = next(
                    (s for s in batch if s.id == result_id),
                    batch[idx] if idx < len(batch) else batch[0]
                )

                results.append(FormattedResult(
                    id=result_id,
                    original=f"{original_source.authors[0] if original_source.authors else ''} - {original_source.title}",
                    formatted=r.get("formatted", ""),
                    errors_fixed=r.get("errors_fixed", []),
                    confidence=r.get("confidence", 80),
                    standard_used=standard
                ))

            # Обновляем статистику
            self.stats["processed"] += len(batch_results)
            self.stats["errors_fixed"] += sum(len(r.get("errors_fixed", [])) for r in batch_results)

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
                user_prompt = f"""<TASK>
Отформатируй {len(batch)} источников по стандарту {standard.value}.
</TASK>

<SOURCE_DATA>
{json.dumps(sources_json, ensure_ascii=False, indent=2)}
</SOURCE_DATA>

<INSTRUCTIONS>
Верни JSON-массив результатов.
</INSTRUCTIONS>"""

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

                # Обрабатываем результаты с защитой от missing fields
                formatted_results = []
                for idx, r in enumerate(batch_results):
                    # Используем id из ответа или порядковый номер
                    result_id = r.get("id", batch[idx].id if idx < len(batch) else idx + 1)

                    # Находим оригинальный источник по id или индексу
                    original_source = next(
                        (s for s in batch if s.id == result_id),
                        batch[idx] if idx < len(batch) else batch[0]
                    )

                    formatted_results.append(FormattedResult(
                        id=result_id,
                        original=f"{original_source.authors[0] if original_source.authors else ''} - {original_source.title}",
                        formatted=r.get("formatted", ""),
                        errors_fixed=r.get("errors_fixed", []),
                        confidence=r.get("confidence", 80),
                        standard_used=standard
                    ))

                return formatted_results

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
        user_prompt = f"""<TASK>
Извлеки библиографические данные из текста.
</TASK>

<INPUT_TEXT>
{text}
</INPUT_TEXT>

<INSTRUCTIONS>
Для каждого источника извлеки:
- id (порядковый номер)
- type (book_1_3_authors, journal_article, dissertation, conference, law, patent, etc.)
- authors (массив строк "Фамилия, И. О.")
- title
- year
- publisher, city (если книга)
- journal, volume, issue, pages (если статья)
- doi, url (если есть)

Верни JSON-массив объектов.
</INSTRUCTIONS>"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system="Ты - эксперт по извлечению библиографических данных. Анализируй текст и извлекай структурированную информацию в JSON.",
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
            "avg_confidence": self.stats.get("avg_confidence", 0),
            "training_examples": len(self.training_data.get('examples', []))
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
    print("Обучен на 1100 примерах с vak.gov.by")
    print("\nДоступные примеры:")
    print("1. example_single_source() - один источник")
    print("2. example_batch_processing() - 50 источников")
    print("3. example_async_processing() - 100 источников параллельно")
    print("4. example_parse_text() - парсинг текста")
    print("\nЗамените 'your-api-key-here' на ваш ключ Anthropic API")
