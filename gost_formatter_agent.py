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

        # Загружаем справочник примеров ВАК РБ
        self.vak_rb_reference = self._load_vak_reference()

        # Системный промпт с правилами
        self.system_prompt = self._build_system_prompt()

        # Статистика
        self.stats = {
            "processed": 0,
            "errors_fixed": 0,
            "avg_confidence": 0
        }

    def _load_vak_reference(self) -> Dict:
        """Загружает упрощённый датасет примеров ВАК РБ"""
        import os
        
        # Сначала пробуем упрощённый датасет (96 примеров, простая структура)
        dataset_paths = [
            os.path.join(os.path.dirname(__file__), "vak_examples_simple.json"),
            os.path.join(os.path.dirname(__file__), "vak_training_dataset.json"),
        ]
        
        for dataset_path in dataset_paths:
            try:
                with open(dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Определяем структуру
                    if 'examples' in data:
                        count = len(data.get('examples', []))
                    else:
                        count = len(data.get('records', []))
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
        """Получает релевантные примеры из упрощённого датасета"""
        detected_type = self._detect_document_type(text)
        
        # Поддержка обоих форматов: новый (examples) и старый (records)
        examples = self.vak_rb_reference.get('examples', [])
        if not examples:
            records = self.vak_rb_reference.get('records', [])
            examples = [{'type': r.get('source_type'), 'example': r.get('formatted_output')} 
                       for r in records if not r.get('is_variation')]
        
        # Фильтруем примеры по типу
        matching = [e for e in examples if e.get('type') == detected_type]
        
        # Если нет точных совпадений, берём похожие типы
        if not matching:
            similar_types = {
                'book_1_3_authors': ['book_4plus_authors', 'book_collective_author'],
                'book_4plus_authors': ['book_1_3_authors', 'book_collective_author'],
                'journal_article': ['newspaper_article', 'collection_article'],
                'law': ['standard'],
            }
            for similar in similar_types.get(detected_type, []):
                matching = [e for e in examples if e.get('type') == similar]
                if matching:
                    break
        
        # Если всё ещё нет — берём любые
        if not matching:
            matching = examples[:max_examples]
        
        # Формируем текст с примерами
        examples_text = []
        for ex in matching[:max_examples]:
            ex_type = ex.get('type', 'unknown')
            ex_text = ex.get('example', '')
            examples_text.append(f"[{ex_type}] {ex_text}")
        
        return "\n".join(examples_text)

    def _build_system_prompt(self) -> str:
        """Создает системный промпт с паттернами форматирования на основе анализа 1000 примеров ВАК"""
        
        # Паттерны форматирования, извлечённые из датасета vak.gov.by
        PATTERNS = """
══════════════════════════════════════════════════════════════
ПАТТЕРНЫ ФОРМАТИРОВАНИЯ ПО ТИПАМ ИСТОЧНИКОВ (АНАЛИЗ vak.gov.by)
══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│ 1. КНИГА (1-3 АВТОРА)                                       │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} : {подзаголовок} / {И. О. Автор}. – {Город} : {Издательство}, {Год}. – {N} с.

ПРИМЕР:
  Дробышевский, Н. П. Ревизия и аудит : учеб.-метод. пособие / Н. П. Дробышевский. – Минск : Амалфея : Мисанта, 2013. – 415 с.

ОСОБЕННОСТИ:
  • НАЧИНАЕТСЯ с фамилии автора (Фамилия, И. О.)
  • После названия косая черта (/) и повтор автора (И. О. Фамилия)
  • Город : Издательство через тире

┌─────────────────────────────────────────────────────────────┐
│ 2. КНИГА (4+ АВТОРОВ)                                       │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} / {И. О. Автор1} [и др.]. – {Город} : {Издательство}, {Год}. – {N} с.

ПРИМЕР:
  Закономерности формирования и совершенствования системы движений спортсменов / В. А. Боровая [и др.]. – Гомель : Гомел. гос. ун-т, 2013. – 173 с.

ОСОБЕННОСТИ:
  • НАЧИНАЕТСЯ с названия (не с автора!)
  • [и др.] после первого автора
  • Косая черта перед авторами

┌─────────────────────────────────────────────────────────────┐
│ 3. СТАТЬЯ ИЗ ЖУРНАЛА                                        │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название статьи} / {И. О. Автор} // {Название журнала}. – {Год}. – Т. {X}, № {Y}. – С. {XX–YY}.

ПРИМЕР:
  Белинский, В. Г. Рассуждение / В. Г. Белинский // Полн. собр. соч. : в 13 т. – М., 1953. – Т. 1. – С. 15–17.

ОСОБЕННОСТИ:
  • ДВОЙНАЯ КОСАЯ (//) перед названием журнала
  • Том и номер через запятую: Т. 5, № 3
  • Страницы: С. 45–52 (через длинное тире)

┌─────────────────────────────────────────────────────────────┐
│ 4. СТАТЬЯ ИЗ ГАЗЕТЫ / ОНЛАЙН-СМИ                            │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} / {И. О. Автор} // {Газета/Сайт}. – URL: {ссылка}. – Дата публ.: {ДД.ММ.ГГГГ}.

ПРИМЕР:
  Ватыль, В. Беларусь развивается и идет по пути консолидации общества / В. Ватыль // SB.BY. Беларусь сегодня. – URL: https://www.sb.by/... – Дата публ.: 12.09.2024.

┌─────────────────────────────────────────────────────────────┐
│ 5. ДИССЕРТАЦИЯ                                              │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} : дис. ... {степень} : {специальность} / {И. О. Автор}. – {Город}, {Год}. – {N} л.

ПРИМЕР:
  Врублеўскі, Ю. У. Гістарыяграфія гісторыі ўзнікнення... : дыс. ... канд. гіст. навук : 07.00.09 / Ю. У. Врублеўскі. – Мінск, 2013. – 148 л.

ОСОБЕННОСТИ:
  • "дис. ..." или "дыс. ..." (три точки!)
  • Листы (л.), не страницы

┌─────────────────────────────────────────────────────────────┐
│ 6. АВТОРЕФЕРАТ ДИССЕРТАЦИИ                                  │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} : автореф. дис. ... {степень} : {специальность} / {И. О. Автор} ; {организация}. – {Город}, {Год}. – {N} с.

ПРИМЕР:
  Горянов, А. В. Эволюция сельской дворянской усадьбы... : автореф. дис. ... канд. ист. наук : 07.00.02 / А. В. Горянов ; Моск. гос. ун-т. – М., 2004. – 28 с.

┌─────────────────────────────────────────────────────────────┐
│ 7. ЗАКОНОДАТЕЛЬНЫЙ АКТ                                      │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название закона} : {дата принятия} № {номер} // {Источник публикации}. – URL: {ссылка} (дата обращения: {ДД.ММ.ГГГГ}).

ПРИМЕР:
  Конституция Республики Беларусь : с изм. и доп., принятыми на респ. референдумах 24 нояб. 1996 г. и 17 окт. 2004 г. – Минск : Нац. центр правовой информ. Респ. Беларусь, 2016. – 62 с.

ОСОБЕННОСТИ:
  • НАЧИНАЕТСЯ с названия закона (не с автора!)
  • Указывается дата принятия и номер
  • Может быть ссылка на КонсультантПлюс или pravo.by

┌─────────────────────────────────────────────────────────────┐
│ 8. СТАНДАРТ (ГОСТ, СТБ, ТКП, ТР ТС)                         │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} : {код стандарта} : {даты}. – {Город} : {Издательство}, {Год}. – {N} с.

ПРИМЕР:
  О безопасности оборудования... : ТР ТС 032/2013 : принят 02.07.2013 : вступ. в силу 01.02.2014. – Минск : Экономэнерго, 2013. – 38 с.

┌─────────────────────────────────────────────────────────────┐
│ 9. ПАТЕНТ / АВТОРСКОЕ СВИДЕТЕЛЬСТВО                         │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} : {пат./а. с.} {страна} {номер} / {авторы}. – Опубл. {ДД.ММ.ГГГГ}.

ПРИМЕР:
  Аспирационный счетчик ионов : а. с. SU 935780 / Б. Н. Блинов, А. В. Шолух. – Опубл. 15.06.1982.

ОСОБЕННОСТИ:
  • НАЧИНАЕТСЯ с названия изобретения
  • а. с. = авторское свидетельство, пат. = патент
  • Код страны: SU, RU, BY и т.д.

┌─────────────────────────────────────────────────────────────┐
│ 10. МАТЕРИАЛЫ КОНФЕРЕНЦИИ                                   │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} : материалы {N} {конференции}, {место}, {даты} / {организация} ; редкол.: {редактор} [и др.]. – {Город} : {Издательство}, {Год}. – {N} с.

ПРИМЕР:
  Информационные технологии и управление : материалы 49 науч. конф., Минск, 6–10 мая 2013 г. / БГУИР ; редкол.: Л. Ю. Шилин [и др.]. – Минск : БГУИР, 2013. – 103 с.

┌─────────────────────────────────────────────────────────────┐
│ 11. ЭЛЕКТРОННЫЙ РЕСУРС / САЙТ                               │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} [Электронный ресурс]. – Режим доступа: {URL}. – Дата доступа: {ДД.ММ.ГГГГ}.

ПРИМЕР:
  Национальный правовой Интернет-портал Республики Беларусь [Электронный ресурс]. – Режим доступа: http://www.pravo.by. – Дата доступа: 24.06.2024.

ОСОБЕННОСТИ:
  • [Электронный ресурс] после названия
  • "Режим доступа:" или "URL:"

┌─────────────────────────────────────────────────────────────┐
│ 12. МНОГОТОМНОЕ ИЗДАНИЕ                                     │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} : у {N} т. / {И. О. Автор}. – {изд.}. – {Город} : {Издательство}, {Год}. – {N} т.

ПРИМЕР:
  Багдановіч, М. Поўны збор твораў : у 3 т. / М. Багдановіч. – 2-е выд. – Мінск : Беларус. навука, 2001. – 3 т.

┌─────────────────────────────────────────────────────────────┐
│ 13. ПРЕПРИНТ                                                │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. {Название} / {И. О. Автор}. – {Город} : {Издательство}, {Год}. – {N} с. – (Препринт / {организация} ; № {N}).

ПРИМЕР:
  Велесницкий, В. Ф. Конечные группы с заданными свойствами / В. Ф. Велесницкий. – Гомель : ГГУ, 2013. – 15 с. – (Препринт / Гомел. гос. ун-т ; № 2).

┌─────────────────────────────────────────────────────────────┐
│ 14. ОТЧЁТ О НИР                                             │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Название} : отчет о НИР ({тип}) : {номер} / {организация} ; рук. {руководитель} ; исполн.: {исполнители}. – {Город}, {Год}. – {N} с. – № ГР {номер}.

ПРИМЕР:
  Состояние и перспективы развития... : отчет о НИР (заключ.) : 06-02 / Рос. кн. палата ; рук. А. А. Джиго ; исполн.: В. П. Смирнова [и др.]. – М., 2000. – 250 с.

┌─────────────────────────────────────────────────────────────┐
│ 15. РЕЦЕНЗИЯ                                                │
└─────────────────────────────────────────────────────────────┘
ПАТТЕРН: {Автор}. [Рецензия] / {И. О. Автор} // {Журнал}. – {Год}. – № {N}. – С. {XX–YY}. – Рец. на кн.: {данные книги}.

ПРИМЕР:
  Грачыха, Т. А. [Рэцэнзія] / Т. А. Грачыха // Весн. Віцеб. дзярж. ун-та. – 2013. – № 1. – С. 127–128. – Рэц. на кн.: ...
"""
        
        # Собираем примеры из упрощённого датасета
        examples = self.vak_rb_reference.get('examples', [])
        if not examples:
            records = self.vak_rb_reference.get('records', [])
            examples = [{'type': r.get('source_type'), 'example': r.get('formatted_output')} 
                       for r in records if not r.get('is_variation')]
        
        examples_by_type = {}
        for ex in examples:
            ex_type = ex.get('type', 'unknown')
            if ex_type not in examples_by_type:
                examples_by_type[ex_type] = []
            if len(examples_by_type[ex_type]) < 1:
                examples_by_type[ex_type].append(ex.get('example', ''))
        
        return f"""Ты — эксперт по библиографическому оформлению по стандартам ГОСТ Р 7.0.100-2018 и ВАК Республики Беларусь.

ТВОЯ БАЗА ЗНАНИЙ: 1000 официальных примеров с сайта vak.gov.by. Ты знаешь ТОЧНУЮ структуру и пунктуацию для каждого типа источника.

══════════════════════════════════════════
⚠️ КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО ⚠️
══════════════════════════════════════════
ЕСЛИ ВВОД УЖЕ ПРАВИЛЬНО ОТФОРМАТИРОВАН — ВЕРНИ ЕГО БЕЗ ИЗМЕНЕНИЙ!

Признаки правильного форматирования:
• Длинное тире (–) с пробелами
• Правильная структура: Автор. Название / И. О. Автор // Журнал. – Год. – Т. X, № Y. – С. XX–YY.
• Все данные на месте (том, номер, страницы, год)

Если ввод содержит все необходимые элементы и правильную пунктуацию:
→ formatted = ввод БЕЗ ИЗМЕНЕНИЙ
→ errors_fixed = []
→ confidence = 100

══════════════════════════════════════════
ПРАВИЛА ПУНКТУАЦИИ (НАРУШЕНИЕ = ОШИБКА)
══════════════════════════════════════════
• Тире: " – " (длинное U+2013, с пробелами с обеих сторон)
• Двоеточие: " : " (с пробелами, перед издательством/подзаголовком)
• Косая черта: " / " (пробелы, перед повтором авторов)
• Двойная косая: " // " (для статей — перед названием журнала/сборника)
• Точка с запятой: " ; " (между редактором и организацией)
• После сокращений: пробел ("Т. 5", "№ 3", "С. 45–52", "с.")
{PATTERNS}
══════════════════════════════════════════
ФОРМАТ ОТВЕТА (строго JSON, без markdown)
══════════════════════════════════════════
{{
  "formatted": "готовая библиографическая запись",
  "errors_fixed": ["список исправлений"],
  "confidence": 95
}}

══════════════════════════════════════════
АЛГОРИТМ РАБОТЫ
══════════════════════════════════════════
0. СНАЧАЛА ПРОВЕРЬ: ввод уже правильный? Если ДА → верни его без изменений!
1. ОПРЕДЕЛИ ТИП источника по ключевым словам
2. НАЙДИ соответствующий ПАТТЕРН из списка выше
3. ЗАПОЛНИ паттерн данными пользователя
4. ПРОВЕРЬ пунктуацию (тире, пробелы, сокращения)
5. ВЕРНИ JSON с результатом

══════════════════════════════════════════
🚫 СТРОГО ЗАПРЕЩЕНО
══════════════════════════════════════════
✗ УДАЛЯТЬ данные из ввода (том, номер, страницы, год, издательство)
✗ Короткое тире (-) вместо длинного (–)
✗ Пропуск пробелов: "М.:Наука" вместо "М. : Наука"
✗ Добавление данных, которых нет в исходнике
✗ Изменение порядка элементов

⚠️ УДАЛЕНИЕ ДАННЫХ ИЗ ВВОДА = КРИТИЧЕСКАЯ ОШИБКА!
Если во вводе есть "Т. 15, № 3" — они ДОЛЖНЫ быть в выводе!

ТОЧНОСТЬ 100% — это единственный приемлемый результат."""

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
                examples_section = f"\n\nПРИМЕРЫ ПРАВИЛЬНОГО ФОРМАТИРОВАНИЯ ПО ВАК РБ:\n{examples}\n"
        
        # Если есть оригинальный текст — передаём его Claude для сверки
        original_section = ""
        if original_text:
            original_section = f"""

⚠️ ОРИГИНАЛЬНЫЙ ТЕКСТ ВВОДА (СВЕРЯЙСЯ С НИМ!):
{original_text}

ВАЖНО: Все данные из оригинала ДОЛЖНЫ быть в выводе!
Если в оригинале есть "Т. 15, № 3" — они ОБЯЗАНЫ быть в результате.
"""
        
        user_prompt = f"""Отформатируй библиографический источник по стандарту {standard.value}.
{examples_section}{original_section}
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
            
            # Добавляем примеры для ВАК РБ
            examples_section = ""
            if standard == Standard.VAK_RB:
                # Собираем текст первого источника для определения типа
                first_source = batch[0]
                sample_text = f"{first_source.authors[0] if first_source.authors else ''} {first_source.title}"
                examples = self._get_relevant_examples(sample_text, max_examples=4)
                if examples:
                    examples_section = f"\n\nПРИМЕРЫ ПРАВИЛЬНОГО ФОРМАТИРОВАНИЯ ПО ВАК РБ:\n{examples}\n"
            
            user_prompt = f"""Отформатируй следующие {len(batch)} источников по стандарту {standard.value}.
{examples_section}
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
