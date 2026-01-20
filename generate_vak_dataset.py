#!/usr/bin/env python3
"""
Generator for VAK RB bibliography dataset.
Creates 1000+ variations based on official patterns.
"""

import json
import random
from typing import List, Dict

# ============================================================================
# DATA BANKS
# ============================================================================

SURNAMES_RU = [
    "Иванов", "Петров", "Сидоров", "Козлов", "Новиков", "Федоров", "Смирнов",
    "Волков", "Кузнецов", "Соколов", "Попов", "Лебедев", "Морозов", "Павлов",
    "Семенов", "Голубев", "Виноградов", "Богданов", "Воробьев", "Михайлов",
    "Егоров", "Никитин", "Соловьев", "Яковлев", "Захаров", "Борисов", "Орлов",
    "Киселев", "Андреев", "Макаров", "Степанов", "Николаев", "Алексеев",
    "Григорьев", "Сергеев", "Романов", "Васильев", "Дмитриев", "Тимофеев"
]

SURNAMES_BY = [
    "Іваноў", "Казлоў", "Новік", "Кавалёў", "Петрыкаў", "Васілеўскі", "Каваленя",
    "Жылінскі", "Шыла", "Краўчанка", "Лукашэвіч", "Дубаневіч", "Багдановіч",
    "Купала", "Колас", "Машэра", "Скарына", "Гусоўскі", "Быкаў", "Караткевіч",
    "Адамовіч", "Гілевіч", "Танк", "Брыль", "Барадулін", "Верабей", "Грачыха",
    "Врублеўскі", "Аляхновіч", "Валатоўская", "Бараноўскі", "Ермакова"
]

INITIALS = [
    "А. В.", "И. П.", "С. Н.", "О. А.", "Н. М.", "В. И.", "Е. П.", "М. А.",
    "Д. В.", "К. С.", "Л. Ф.", "П. В.", "Р. Г.", "Т. А.", "Ю. С.", "Б. Н.",
    "Г. И.", "Ж. К.", "З. М.", "Э. Р.", "В. В.", "А. А.", "Н. Н.", "С. С.",
    "И. И.", "М. М.", "Д. А.", "Л. В.", "О. В.", "Е. А.", "А. Л.", "В. Ф."
]

CITIES = [
    "Минск", "Мінск", "Мн.", "Гомель", "Брест", "Гродно", "Могилёв", "Витебск",
    "М.", "СПб.", "Москва", "Санкт-Петербург", "Киев", "Ростов н/Д", "Новосибирск"
]

CITIES_BELARUS = ["Минск", "Мінск", "Мн.", "Гомель", "Брест", "Гродно", "Могилёв", "Витебск", "Горки"]

PUBLISHERS = [
    "Беларуская навука", "Бел. навука", "Вышэйшая школа", "БДУ", "БГУ", "БНТУ",
    "Юрайт", "Амалфея", "Аверсэв", "Народная асвета", "Право и экономика",
    "Голас Радзімы", "Медиал", "БГУИР", "ГрГМУ", "БрГУ", "ГГУ", "Колорград",
    "Экономэнерго", "Юнипак", "Госстандарт", "Белэнерго", "Ковчег", "Энергопресс",
    "Дашков и К°", "Наука-Спектр", "Лань", "Планета музыки", "ОИЯИ"
]

PUBLISHERS_BELARUS = [
    "Беларуская навука", "Бел. навука", "Вышэйшая школа", "БДУ", "БГУ", "БНТУ",
    "Амалфея", "Аверсэв", "Народная асвета", "Право и экономика", "БГУИР",
    "ГрГМУ", "БрГУ", "ГГУ", "Колорград", "Госстандарт", "Ковчег"
]

JOURNALS = [
    "Весці НАН Беларусі", "Вестник БГУ", "Вопросы экономики", "Нар. асвета",
    "Беларуская думка", "Журнал Белорусского государственного университета. Филология",
    "Весн. Віцеб. дзярж. ун-та", "Зб. навук. пр.", "Доклады НАН Беларуси",
    "Вестник БНТУ", "Белорус. экон. журн.", "Труды БГТУ", "Проблемы управления",
    "Информатика", "Математика и информатика", "Право.by", "Юстиция Беларуси"
]

NEWSPAPERS = [
    "Сельская газета", "Совет. Белоруссия", "Белорус. лес. газ.", "Рэспубліка",
    "Звязда", "Народная газета", "SB.BY. Беларусь сегодня", "Белорусская нива"
]

ORGANIZATIONS = [
    "НАН Беларуси", "Белорус. гос. ун-т", "Бел. гос. ун-т", "БГУ",
    "Белорус. гос. ун-т информатики и радиоэлектроники", "БГУИР",
    "Бел. нац. техн. ун-т", "БНТУ", "Гомел. гос. ун-т", "ГГУ",
    "Гродн. гос. ун-т", "ГрГУ", "Гродн. гос. мед. ун-т", "ГрГМУ",
    "Брест. гос. ун-т", "БрГУ", "Белорус. гос. пед. ун-т", "БГПУ",
    "Бел. гос. мед. ун-т", "БГМУ", "Бел. гос. с.-х. акад.",
    "Нац. центр правовой информ. Респ. Беларусь", "М-во юстиции Респ. Беларусь"
]

# Book titles by domain
BOOK_TITLES = {
    "economics": [
        "Основы экономики", "Экономическая теория", "Макроэкономика", "Микроэкономика",
        "Финансовый менеджмент", "Инвестиционный анализ", "Бухгалтерский учет",
        "Ревизия и аудит", "Налоговое планирование", "Международная торговля",
        "Экономика предприятия", "Управление проектами", "Маркетинг"
    ],
    "law": [
        "Теория государства и права", "Конституционное право", "Гражданское право",
        "Уголовное право", "Административное право", "Трудовое право",
        "Международное право", "Финансовое право", "Налоговое право",
        "Экологическое право", "Семейное право", "Арбитражный процесс"
    ],
    "tech": [
        "Информационные технологии", "Программирование", "Базы данных",
        "Компьютерные сети", "Искусственный интеллект", "Машинное обучение",
        "Кибербезопасность", "Веб-разработка", "Мобильные приложения",
        "Робототехника", "Системный анализ", "Автоматизация производства"
    ],
    "science": [
        "Методы исследования", "Математический анализ", "Теоретическая физика",
        "Органическая химия", "Молекулярная биология", "Генетика",
        "Экология", "Геология", "Астрономия", "Статистика"
    ],
    "humanities": [
        "История Беларуси", "Философия", "Социология", "Политология",
        "Культурология", "Психология", "Педагогика", "Лингвистика",
        "Литературоведение", "Искусствоведение", "Религиоведение"
    ],
    "medicine": [
        "Анатомия человека", "Физиология", "Терапия", "Хирургия",
        "Педиатрия", "Кардиология", "Неврология", "Онкология",
        "Фармакология", "Микробиология", "Иммунология"
    ]
}

ARTICLE_TITLES = [
    "Анализ данных в современных условиях",
    "Проблемы развития и перспективы",
    "Методологические подходы к исследованию",
    "Современные тенденции развития",
    "Актуальные вопросы и пути решения",
    "Инновационные методы в практике",
    "Теоретические основы и практическое применение",
    "Сравнительный анализ подходов",
    "Особенности функционирования системы",
    "Оптимизация процессов управления",
    "Направления совершенствования механизма",
    "Эффективность применения методов",
    "Роль и значение в современных условиях",
    "Перспективы внедрения инноваций",
    "Комплексный подход к решению проблем"
]

LAW_TITLES = [
    "О государственном регулировании", "Об охране окружающей среды",
    "О защите прав потребителей", "О предпринимательской деятельности",
    "О государственных закупках", "Об образовании", "О здравоохранении",
    "О социальной защите", "О труде и занятости", "О налогообложении",
    "О банках и банковской деятельности", "О ценных бумагах",
    "О местном управлении", "О государственной службе", "О безопасности"
]

PATENT_TITLES = [
    "Способ обработки материалов", "Устройство для измерения",
    "Метод определения содержания", "Способ получения композиции",
    "Устройство для автоматизации", "Способ очистки воды",
    "Метод анализа данных", "Устройство контроля параметров",
    "Способ синтеза соединений", "Устройство для диагностики",
    "Метод оптимизации процесса", "Способ защиты информации"
]

DISSERTATION_TOPICS = [
    "Развитие системы управления",
    "Совершенствование методов анализа",
    "Повышение эффективности процессов",
    "Формирование механизма регулирования",
    "Оптимизация структуры организации",
    "Моделирование социально-экономических систем",
    "Разработка инструментария оценки",
    "Исследование закономерностей развития"
]

CONFERENCE_TITLES = [
    "Актуальные проблемы науки и образования",
    "Инновационные технологии в производстве",
    "Современные методы исследования",
    "Перспективы развития отрасли",
    "Научные достижения молодых ученых",
    "Компьютерные системы и сети",
    "Информационные технологии и управление",
    "Актуальные проблемы дизайна и дизайн-образования"
]

SPECIALTY_CODES = [
    "08.00.05", "08.00.01", "12.00.01", "12.00.03", "05.13.01", "05.13.06",
    "07.00.02", "07.00.09", "09.00.01", "10.01.01", "14.01.05", "14.00.27",
    "01.01.02", "01.04.07", "02.00.03", "03.02.08", "17.00.09", "13.00.01"
]

STANDARD_PREFIXES = ["ГОСТ", "СТБ", "ТКП", "СТБ ISO", "ГОСТ Р", "ТР ТС", "СТП"]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def random_author() -> tuple:
    """Returns (surname, initials) for Russian or Belarusian author."""
    if random.random() < 0.7:
        surname = random.choice(SURNAMES_RU)
    else:
        surname = random.choice(SURNAMES_BY)
    initials = random.choice(INITIALS)
    return surname, initials

def random_year(start: int = 2015, end: int = 2025) -> int:
    return random.randint(start, end)

def random_pages(min_p: int = 50, max_p: int = 600) -> int:
    return random.randint(min_p, max_p)

def random_page_range(max_pages: int = 300) -> tuple:
    start = random.randint(5, max_pages - 20)
    end = start + random.randint(3, 50)
    return start, end

def random_volume() -> int:
    return random.randint(1, 30)

def random_issue() -> int:
    return random.randint(1, 12)

def random_city(belarus_only: bool = False) -> str:
    if belarus_only:
        return random.choice(CITIES_BELARUS)
    return random.choice(CITIES)

def random_publisher(belarus_only: bool = False) -> str:
    if belarus_only:
        return random.choice(PUBLISHERS_BELARUS)
    return random.choice(PUBLISHERS)

def random_journal() -> str:
    return random.choice(JOURNALS)

def random_organization() -> str:
    return random.choice(ORGANIZATIONS)

def random_date() -> str:
    day = random.randint(1, 28)
    month = random.choice(["янв.", "февр.", "марта", "апр.", "мая", "июня",
                           "июля", "авг.", "сент.", "окт.", "нояб.", "дек."])
    year = random_year()
    return f"{day} {month} {year} г."

def random_date_short() -> str:
    day = str(random.randint(1, 28)).zfill(2)
    month = str(random.randint(1, 12)).zfill(2)
    year = random_year()
    return f"{day}.{month}.{year}"

def random_book_title(domain: str = None) -> str:
    if domain and domain in BOOK_TITLES:
        return random.choice(BOOK_TITLES[domain])
    domain = random.choice(list(BOOK_TITLES.keys()))
    return random.choice(BOOK_TITLES[domain])

def random_article_title() -> str:
    return random.choice(ARTICLE_TITLES)

def random_law_title() -> str:
    return random.choice(LAW_TITLES)

def random_patent_title() -> str:
    return random.choice(PATENT_TITLES)

def random_dissertation_topic() -> str:
    return random.choice(DISSERTATION_TOPICS)

def random_conference_title() -> str:
    return random.choice(CONFERENCE_TITLES)

# ============================================================================
# GENERATORS FOR EACH TYPE
# ============================================================================

def generate_book_1_3_authors() -> str:
    """Книга 1-3 автора."""
    num_authors = random.randint(1, 3)
    authors = [random_author() for _ in range(num_authors)]

    # First author in inverted form
    first = f"{authors[0][0]}, {authors[0][1]}"
    title = random_book_title()

    # Type of publication
    pub_types = ["учеб. пособие", "учеб.-метод. пособие", "монография", "практикум", ""]
    pub_type = random.choice(pub_types)

    # All authors after slash
    all_authors = ", ".join([f"{a[1]} {a[0]}" for a in authors])

    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    year = random_year()
    pages = random_pages()

    # Build the reference
    if pub_type:
        result = f"{first} {title} : {pub_type} / {all_authors}. – {city} : {publisher}, {year}. – {pages} с."
    else:
        result = f"{first} {title} / {all_authors}. – {city} : {publisher}, {year}. – {pages} с."

    # Sometimes add edition
    if random.random() < 0.2:
        edition = random.choice(["2-е изд.", "3-е изд.", "2-е изд., стер.", "Изд. 2-е", "2-е изд., перераб."])
        result = result.replace(f". – {city}", f". – {edition}. – {city}")

    return result


def generate_book_4plus_authors() -> str:
    """Книга 4+ авторов (начинается с названия)."""
    title = random_book_title()
    first_author = random_author()

    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    year = random_year()
    pages = random_pages()

    result = f"{title} / {first_author[1]} {first_author[0]} [и др.]. – {city} : {publisher}, {year}. – {pages} с."

    return result


def generate_journal_article() -> str:
    """Статья в журнале."""
    author = random_author()
    title = random_article_title()
    journal = random_journal()
    year = random_year()
    vol = random_volume() if random.random() < 0.5 else None
    issue = random_issue()
    start_p, end_p = random_page_range(200)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    if vol:
        result = f"{first} {title} / {all_authors} // {journal}. – {year}. – Т. {vol}, № {issue}. – С. {start_p}–{end_p}."
    else:
        result = f"{first} {title} / {all_authors} // {journal}. – {year}. – № {issue}. – С. {start_p}–{end_p}."

    return result


def generate_collection_article() -> str:
    """Статья в сборнике."""
    author = random_author()
    title = random_article_title()
    collection_title = f"{random.choice(['Актуальные проблемы', 'Современные вопросы', 'Научные труды'])} {random.choice(['науки', 'экономики', 'права', 'образования'])}"

    org = random_organization()
    city = random_city(belarus_only=True)
    year = random_year()
    start_p, end_p = random_page_range(300)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} / {all_authors} // {collection_title} : сб. науч. ст. / {org}. – {city}, {year}. – С. {start_p}–{end_p}."

    return result


def generate_law() -> str:
    """Закон/нормативный акт."""
    law_types = [
        ("Закон Респ. Беларусь", "№"),
        ("Декрет Президента Респ. Беларусь", "№"),
        ("Указ Президента Респ. Беларусь", "№"),
        ("постановление Совета Министров Респ. Беларусь", "№"),
        ("приказ М-ва юстиции Респ. Беларусь", "№"),
        ("постановление М-ва здравоохранения Респ. Беларусь", "№"),
    ]

    law_type, num_prefix = random.choice(law_types)
    title = random_law_title()
    date = random_date()
    num = random.randint(1, 500)

    # Various formats
    formats = [
        f"{title} : {law_type}, {date}, {num_prefix} {num} // Нац. реестр правовых актов Респ. Беларусь. – {random_year()}. – № {random_issue()}. – Ст. {random.randint(1, 500)}.",
        f"{title} : {law_type}, {date}, {num_prefix} {num}-З // Ведамасцi Нац. сходу Рэсп. Беларусь. – {random_year()}. – № {random_issue()}. – Арт. {random.randint(100, 500)}.",
        f"{title} : утв. {law_type.replace('Закон Респ. Беларусь', 'постановлением М-ва юстиции Респ. Беларусь')} {date.replace(' г.', '')}, {num_prefix} {num}. – Мн. : Нац. центр правовой информ. Респ. Беларусь, {random_year()}. – {random_pages(50, 200)} с.",
    ]

    return random.choice(formats)


def generate_standard() -> str:
    """Стандарт (ГОСТ, СТБ, ТКП)."""
    prefix = random.choice(STANDARD_PREFIXES)
    number = f"{random.randint(1, 9999)}-{random_year()}"

    titles = [
        "Система стандартов по информации",
        "Общие технические требования",
        "Методы испытаний",
        "Правила приемки",
        "Технические условия",
        "Нормы проектирования"
    ]
    title = random.choice(titles)

    intro_date = random_date_short()
    city = random_city(belarus_only=True)
    publisher = random.choice(["Госстандарт", "Бел. гос. ин-т стандартизации и сертификации"])
    year = random_year()
    pages = random.randint(3, 50)

    result = f"{title} : {prefix} {number}. – Введ. {intro_date}. – {city} : {publisher}, {year}. – {pages} с."

    return result


def generate_patent() -> str:
    """Патент."""
    title = random_patent_title()
    patent_types = [
        ("пат. BY", random.randint(10000, 99999)),
        ("а. с. SU", random.randint(100000, 999999)),
        ("полез. модель RU", random.randint(10000, 99999)),
        ("пат. RU", random.randint(1000000, 9999999)),
    ]

    ptype, pnum = random.choice(patent_types)

    num_inventors = random.randint(1, 5)
    inventors = [random_author() for _ in range(num_inventors)]
    inventors_str = ", ".join([f"{a[1]} {a[0]}" for a in inventors])

    pub_date = random_date_short()

    result = f"{title} : {ptype} {pnum} / {inventors_str}. – Опубл. {pub_date}."

    return result


def generate_dissertation() -> str:
    """Диссертация."""
    author = random_author()
    topic = random_dissertation_topic()

    degree_types = [
        ("дис. ... канд.", "канд."),
        ("дис. ... д-ра", "д-ра"),
        ("дыс. ... канд.", "канд."),  # Belarusian
    ]
    degree, _ = random.choice(degree_types)

    science_types = ["экон. наук", "юрид. наук", "техн. наук", "филол. наук",
                     "ист. наук", "мед. наук", "пед. наук", "филос. наук"]
    science = random.choice(science_types)

    code = random.choice(SPECIALTY_CODES)
    city = random_city(belarus_only=True)
    year = random_year()
    pages = random.randint(120, 300)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {topic} : {degree} {science} : {code} / {all_authors}. – {city}, {year}. – {pages} л."

    return result


def generate_conference() -> str:
    """Материалы конференции."""
    title = random_conference_title()

    conf_types = ["материалы", "сб. ст.", "тезисы докл."]
    conf_type = random.choice(conf_types)

    conf_levels = ["Междунар.", "Респ.", "регион."]
    conf_level = random.choice(conf_levels)

    conf_forms = ["науч. конф.", "науч.-практ. конф.", "науч. конф. аспирантов, магистрантов и студентов"]
    conf_form = random.choice(conf_forms)

    city = random_city(belarus_only=True)

    # Date range
    day1 = random.randint(1, 20)
    day2 = day1 + random.randint(1, 5)
    month = random.choice(["янв.", "февр.", "марта", "апр.", "мая", "июня",
                           "июля", "авг.", "сент.", "окт.", "нояб.", "дек."])
    year = random_year()
    date_str = f"{day1}–{day2} {month} {year} г."

    org = random_organization()
    publisher = random_publisher(belarus_only=True)
    pages = random_pages(50, 500)

    result = f"{title} : {conf_type} {conf_level} {conf_form}, {city}, {date_str} / {org}. – {city} : {publisher}, {year}. – {pages} с."

    return result


def generate_electronic_resource() -> str:
    """Электронный ресурс."""
    titles = [
        "Национальный правовой Интернет-портал Республики Беларусь",
        "Официальный сайт Президента Республики Беларусь",
        "Национальный статистический комитет Республики Беларусь",
        "Министерство образования Республики Беларусь",
        "Научная электронная библиотека",
        "Электронная библиотека диссертаций"
    ]

    urls = [
        "http://www.pravo.by",
        "http://www.president.gov.by",
        "http://www.belstat.gov.by",
        "http://www.edu.gov.by",
        "http://www.elibrary.ru",
        "http://www.dissercat.com"
    ]

    idx = random.randint(0, len(titles) - 1)
    title = titles[idx]
    url = urls[idx]

    date = random_date_short()

    # Two formats
    if random.random() < 0.5:
        result = f"{title} [Электронный ресурс]. – Режим доступа: {url}. – Дата доступа: {date}."
    else:
        result = f"{title} : [сайт]. – Мн., 2003–2025. – URL: {url} (дата обращения: {date})."

    return result


def generate_newspaper_article() -> str:
    """Газетная статья."""
    author = random_author()
    title = random_article_title()
    newspaper = random.choice(NEWSPAPERS)
    year = random_year()

    day = random.randint(1, 28)
    month = random.choice(["янв.", "февр.", "марта", "апр.", "мая", "июня",
                           "июля", "авг.", "сент.", "окт.", "нояб.", "дек."])

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    # Newspaper pages are typically 1-20
    start_p = random.randint(1, 15)
    end_p = start_p + random.randint(1, 5)

    result = f"{first} {title} / {all_authors} // {newspaper}. – {year}. – {day} {month} – С. {start_p}–{end_p}."

    return result


def generate_preprint() -> str:
    """Препринт."""
    author = random_author()
    title = random_article_title()

    org = random_organization()
    city = random_city(belarus_only=True)
    year = random_year()
    pages = random.randint(10, 30)
    number = random.randint(1, 50)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} / {all_authors}. – {city} : {org.split(';')[0].strip()}, {year}. – {pages} с. – (Препринт / {org} ; № {number})."

    return result


def generate_multimedia() -> str:
    """Звуко- или видеозапись."""
    author = random_author()

    titles = ["Симфония", "Концерт", "Музыкальные вечера", "Народные песни",
              "Классическая музыка", "Джазовые композиции"]
    title = random.choice(titles)

    media_types = ["[Звукозапись]", "[Видеозапись]"]
    media_type = random.choice(media_types)

    formats = ["1 зв. диск", "1 CD-ROM", "1 DVD video", "1 диск"]
    media_format = random.choice(formats)

    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    year = random_year()

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} {media_type} / {all_authors}. – {city} : {publisher}, {year}. – {media_format}."

    return result


def generate_map() -> str:
    """Карта."""
    regions = ["Беларусь", "Европа", "Минская область", "Гомельская область",
               "Брестская область", "Гродненская область"]
    region = random.choice(regions)

    map_types = ["полит.-адм. карта", "физ. карта", "турист. карта", "автомоб. карта"]
    map_type = random.choice(map_types)

    scales = ["1 : 500 000", "1 : 1 000 000", "1 : 2 500 000", "1 : 10 500 000"]
    scale = random.choice(scales)

    city = random_city(belarus_only=True)
    publisher = random.choice(["Белкартография", "АГТ Геоцентр", "Белгеодезия"])
    year = random_year()

    result = f"{region} [Карты] : [{map_type}]. – {scale}. – {city} : {publisher}, {year}. – 1 к."

    return result


def generate_music_score() -> str:
    """Ноты."""
    author = random_author()

    titles = ["Романсы", "Сонаты", "Прелюдии", "Этюды", "Вальсы", "Полонезы", "Регтаймы"]
    title = random.choice(titles)

    instruments = ["для фортепиано", "для скрипки с фортепиано", "для тенора с фортепиано",
                   "для хора", "для оркестра"]
    instrument = random.choice(instruments)

    city = random_city(belarus_only=True)
    publisher = random.choice(["Белорус. гос. акад. музыки", "Лань", "Планета музыки"])
    year = random_year()
    pages = random.randint(20, 100)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} [Ноты] : {instrument} / {all_authors}. – {city} : {publisher}, {year}. – {pages} с."

    return result


def generate_visual_material() -> str:
    """Изоматериал."""
    titles = ["С праздником!", "Поздравляем!", "9 мая. С праздником Победы!",
              "С Новым годом!", "Белорусские пейзажи"]
    title = random.choice(titles)

    material_types = ["[плакат]", "[открытка]", "[репродукция]"]
    material_type = random.choice(material_types)

    city = random_city(belarus_only=True)
    publisher = random.choice(["Полиграфкомбинат им. Я. Коласа", "Нац. б-ка Беларуси", "Белпринт"])
    year = random_year()

    result = f"{title} : {material_type}. – {city} : {publisher}, {year}. – 1 л."

    return result


def generate_archive() -> str:
    """Архивный материал."""
    archive_types = [
        "Архив суда Ленинского района г. Минска",
        "Национальный архив Республики Беларусь",
        "Архив Министерства внутренних дел Республики Беларусь",
        "Государственный архив Минской области"
    ]
    archive = random.choice(archive_types)

    year = random_year(2000, 2020)
    case_num = random.randint(1, 999)

    # Different formats
    formats = [
        f"{archive} за {year} г. – Уголовное дело № {case_num}/{str(year)[2:]} ({random.randint(1, 20)}).",
        f"{archive}. – Ф. {random.randint(1, 100)}. Оп. {random.randint(1, 10)}. Д. {random.randint(1, 100)}. Л. {random.randint(1, 300)}.",
    ]

    return random.choice(formats)


def generate_research_report() -> str:
    """Отчет о НИР."""
    title = random_article_title()

    org = random_organization()
    leader = random_author()

    executors = [random_author() for _ in range(random.randint(2, 4))]
    executors_str = ", ".join([f"{a[1]} {a[0]}" for a in executors])

    city = random_city(belarus_only=True)
    year = random_year()
    pages = random.randint(50, 300)
    gr_num = f"{random_year(2015, 2020)}{random.randint(1000, 9999)}"

    result = f"{title} : отчет о НИР (заключ.) / {org} ; рук. {leader[1]} {leader[0]} ; исполн.: {executors_str}. – {city}, {year}. – {pages} с. – № ГР {gr_num}."

    return result


def generate_deposited() -> str:
    """Депонированная рукопись."""
    author = random_author()
    title = random_article_title()

    org = random_organization()
    city = random_city()
    year = random_year(2010, 2020)
    pages = random.randint(10, 50)

    dep_orgs = ["ИНИОН РАН", "ВИНИТИ", "БелИСА"]
    dep_org = random.choice(dep_orgs)
    dep_date = random_date_short()
    dep_num = random.randint(50000, 70000)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} / {all_authors} ; {org}. – {city}, {year}. – {pages} с. – Деп. в {dep_org} {dep_date}, № {dep_num}."

    return result


def generate_multivolume() -> str:
    """Многотомное издание."""
    author = random_author()

    titles = ["Полное собрание сочинений", "Избранные труды", "Собрание сочинений",
              "Поўны збор твораў", "История Беларуси"]
    title = random.choice(titles)

    volumes = random.randint(2, 10)
    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    year_start = random_year(2010, 2020)
    year_end = year_start + random.randint(1, 5)

    first = f"{author[0]}, {author[1]}"
    all_authors = f"{author[1]} {author[0]}"

    result = f"{first} {title} : у {volumes} т. / {all_authors}. – {city} : {publisher}, {year_start}–{year_end}. – {volumes} т."

    return result


def generate_abstract() -> str:
    """Автореферат диссертации."""
    author = random_author()
    topic = random_dissertation_topic()

    degree_types = [
        ("автореф. дис. ... канд.", "канд."),
        ("автореф. дис. ... д-ра", "д-ра"),
    ]
    degree, _ = random.choice(degree_types)

    science_types = ["экон. наук", "юрид. наук", "техн. наук", "мед. наук", "пед. наук"]
    science = random.choice(science_types)

    code = random.choice(SPECIALTY_CODES)

    # Full name
    full_name = f"{author[0]} {random.choice(['Александр', 'Елена', 'Сергей', 'Наталья', 'Владимир', 'Ольга'])} {random.choice(['Викторович', 'Александровна', 'Николаевич', 'Владимировна', 'Петрович', 'Сергеевна'])}"

    org = random_organization()
    city = random_city(belarus_only=True)
    year = random_year()
    pages = random.randint(20, 50)

    first = f"{author[0]}, {author[1]}"

    result = f"{first} {topic} : {degree} {science} : {code} / {full_name} ; {org}. – {city}, {year}. – {pages} с."

    return result


def generate_review() -> str:
    """Рецензия."""
    reviewer = random_author()

    reviewed_author = random_author()
    reviewed_title = random_book_title()

    journal = random_journal()
    year = random_year()
    issue = random_issue()

    # Reviews are short - typically 2-5 pages
    start_p = random.randint(50, 150)
    end_p = start_p + random.randint(2, 5)

    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    book_year = year - random.randint(0, 2)
    book_pages = random_pages()

    first = f"{reviewer[0]}, {reviewer[1]}"
    all_reviewers = f"{reviewer[1]} {reviewer[0]}"

    result = f"{first} [Рецензия] / {all_reviewers} // {journal}. – {year}. – № {issue}. – С. {start_p}–{end_p}. – Рец. на кн.: {reviewed_title} / {reviewed_author[1]} {reviewed_author[0]}. – {city} : {publisher}, {book_year}. – {book_pages} с."

    return result


def generate_catalog() -> str:
    """Каталог."""
    titles = [
        "Каталог инновационных разработок",
        "Каталог древесных растений",
        "Каталог продукции",
        "Каталог научных изданий"
    ]
    title = random.choice(titles)

    org = random_organization()
    compilers = [random_author() for _ in range(random.randint(1, 2))]
    compilers_str = ", ".join([f"{a[1]} {a[0]}" for a in compilers])

    editor = random_author()
    city = random_city(belarus_only=True)
    publisher = random_publisher(belarus_only=True)
    year = random_year()
    pages = random_pages(100, 500)

    result = f"{title} / {org} ; сост.: {compilers_str} ; отв. ред. {editor[1]} {editor[0]}. – {city} : {publisher}, {year}. – {pages} с."

    return result


def generate_methodical_guide() -> str:
    """Методические указания."""
    topics = ["Математика", "Физика", "Химия", "Программирование", "Экономика", "Право"]
    topic = random.choice(topics)

    guide_types = ["метод. указания", "метод. рекомендации", "метод. пособие"]
    guide_type = random.choice(guide_types)

    activities = ["к практ. занятиям", "к лаб. работам", "к курсовому проектированию",
                  "к дипломному проектированию"]
    activity = random.choice(activities)

    org = random_organization()
    compiler = random_author()
    city = random_city(belarus_only=True)
    publisher = random.choice([org.split(';')[0].strip(), random_publisher(belarus_only=True)])
    year = random_year()
    pages = random.randint(20, 80)

    result = f"{topic} : {guide_type} {activity} / {org} ; сост. {compiler[1]} {compiler[0]}. – {city} : {publisher}, {year}. – {pages} с."

    return result


# ============================================================================
# MAIN GENERATION
# ============================================================================

def validate_punctuation(text: str) -> str:
    """Validate and fix common punctuation issues."""
    import re

    # Fix ". –X" -> ". – X" (space after dash, but not in ranges)
    # First, protect ranges like "45–52", "2020–2024"
    range_pattern = re.compile(r'(\d+)–(\d+)')
    ranges = range_pattern.findall(text)

    # Fix missing space after dash in non-range contexts
    text = re.sub(r'\. –([^\s\d])', r'. – \1', text)
    text = re.sub(r'\. – (\d)', lambda m: f'. – {m.group(1)}' if not re.match(r'^\d+–\d+', text[m.end()-1:m.end()+10]) else m.group(0), text)

    # Fix ":X" -> ": X"
    text = re.sub(r':([^\s/])', r': \1', text)

    # Fix double spaces
    text = re.sub(r'  +', ' ', text)

    # Fix "И. О.Слово" -> "И. О. Слово"
    text = re.sub(r'(\w\. \w\.)([А-ЯЁа-яёA-Za-z])', r'\1 \2', text)

    # Ensure no space around dash in ranges
    text = re.sub(r'(\d) – (\d)', r'\1–\2', text)
    text = re.sub(r'(\d)– (\d)', r'\1–\2', text)
    text = re.sub(r'(\d) –(\d)', r'\1–\2', text)

    # Fix "С. X – Y" -> "С. X–Y"
    text = re.sub(r'С\. (\d+) ?– ?(\d+)', r'С. \1–\2', text)

    return text


def generate_dataset(target_count: int = 1100) -> Dict:
    """Generate the complete dataset."""

    # Distribution of types
    distribution = {
        'law': 180,
        'book_1_3_authors': 160,
        'journal_article': 120,
        'collection_article': 80,
        'book_4plus_authors': 70,
        'standard': 60,
        'conference': 50,
        'multimedia': 50,
        'patent': 40,
        'dissertation': 30,
        'electronic_resource': 30,
        'newspaper_article': 30,
        'preprint': 20,
        'map': 20,
        'music_score': 20,
        'visual_material': 20,
        'archive': 20,
        'research_report': 15,
        'deposited': 15,
        'multivolume': 15,
        'abstract': 15,
        'review': 15,
        'catalog': 10,
        'methodical_guide': 15,
    }

    generators = {
        'law': generate_law,
        'book_1_3_authors': generate_book_1_3_authors,
        'journal_article': generate_journal_article,
        'collection_article': generate_collection_article,
        'book_4plus_authors': generate_book_4plus_authors,
        'standard': generate_standard,
        'conference': generate_conference,
        'multimedia': generate_multimedia,
        'patent': generate_patent,
        'dissertation': generate_dissertation,
        'electronic_resource': generate_electronic_resource,
        'newspaper_article': generate_newspaper_article,
        'preprint': generate_preprint,
        'map': generate_map,
        'music_score': generate_music_score,
        'visual_material': generate_visual_material,
        'archive': generate_archive,
        'research_report': generate_research_report,
        'deposited': generate_deposited,
        'multivolume': generate_multivolume,
        'abstract': generate_abstract,
        'review': generate_review,
        'catalog': generate_catalog,
        'methodical_guide': generate_methodical_guide,
    }

    examples = []

    for entry_type, count in distribution.items():
        generator = generators[entry_type]
        for _ in range(count):
            try:
                text = generator()
                text = validate_punctuation(text)
                examples.append({
                    'type': entry_type,
                    'example': text
                })
            except Exception as e:
                print(f"Error generating {entry_type}: {e}")

    # Shuffle
    random.shuffle(examples)

    return {
        'description': 'Датасет для обучения форматированию библиографии ВАК РБ',
        'source': 'Generated based on vak.gov.by patterns',
        'generated_at': '2026-01-20',
        'total_examples': len(examples),
        'type_distribution': {k: v for k, v in distribution.items()},
        'examples': examples
    }


if __name__ == '__main__':
    print("Generating VAK RB bibliography dataset...")

    random.seed(42)  # For reproducibility
    dataset = generate_dataset(1100)

    output_file = 'vak_training.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Generated {dataset['total_examples']} examples")
    print(f"Saved to {output_file}")

    # Print type distribution
    print("\nType distribution:")
    type_counts = {}
    for ex in dataset['examples']:
        t = ex['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
