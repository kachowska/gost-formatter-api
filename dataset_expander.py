"""
Генератор вариаций для расширения датасета ВАК

На основе оригинальных примеров создаёт вариации,
сохраняя ТОЧНУЮ структуру и пунктуацию.
"""

import json
import random
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple

# =============================================
# СЛОВАРИ ДЛЯ ГЕНЕРАЦИИ РЕАЛИСТИЧНЫХ ДАННЫХ
# =============================================

# Белорусские и российские фамилии
SURNAMES = [
    # Белорусские
    "Іваноў", "Казлоў", "Новік", "Кавалёў", "Петрыкаў", "Васілеўскі", "Мікалаеў",
    "Сідарэнка", "Бабрыкаў", "Маслоўскі", "Шышко", "Ярмолік", "Купала", "Колас",
    "Багдановіч", "Мележ", "Караткевіч", "Быкаў", "Адамовіч", "Шамякін",
    # Русские
    "Иванов", "Петров", "Сидоров", "Козлов", "Новиков", "Морозов", "Волков",
    "Соколов", "Попов", "Лебедев", "Семёнов", "Егоров", "Павлов", "Кузнецов",
    "Степанов", "Николаев", "Орлов", "Андреев", "Макаров", "Захаров",
    "Федоров", "Михайлов", "Беляев", "Тарасов", "Белов", "Комаров",
]

# Инициалы
INITIALS = [
    "А. А.", "А. В.", "А. И.", "А. Н.", "А. П.", "А. С.",
    "В. А.", "В. В.", "В. И.", "В. М.", "В. Н.", "В. П.",
    "Г. А.", "Г. В.", "Д. А.", "Д. В.", "Е. А.", "Е. В.",
    "И. А.", "И. В.", "И. И.", "И. П.", "М. А.", "М. В.",
    "Н. А.", "Н. В.", "Н. И.", "Н. Н.", "О. А.", "О. В.",
    "П. А.", "П. В.", "П. П.", "С. А.", "С. В.", "С. И.",
]

# Издательства Беларуси
PUBLISHERS_BY = [
    "Беларуская навука", "Вышэйшая школа", "БДУ", "БДТУ", "БНТУ",
    "Беларусь", "Народная асвета", "Аверсэв", "Полымя", "Мастацкая літаратура",
    "Юнипак", "Тэхналогія", "ГрДУ", "ВДУ", "МагДУ", "БрДУ",
    "Белорусская наука", "Белорусский Дом печати", "Право и экономика",
    "Четыре четверти", "Книжный Дом", "Медисонт", "Белорусский дом печати",
]

# Издательства России
PUBLISHERS_RU = [
    "Наука", "Просвещение", "Высшая школа", "Юрайт", "ИНФРА-М",
    "Академия", "Дрофа", "Питер", "БХВ-Петербург", "Флинта",
    "Дашков и К°", "URSS", "Издательский дом МГУ", "Статут",
    "Проспект", "КноРус", "Эксмо", "АСТ", "Манн, Иванов и Фербер",
]

# Города
CITIES_BY = ["Мінск", "Минск", "Мн.", "Гомель", "Брэст", "Гродна", "Віцебск", "Магілёў"]
CITIES_RU = ["М.", "Москва", "СПб.", "Санкт-Петербург", "Новосибирск", "Екатеринбург"]

# Журналы
JOURNALS = [
    "Весці НАН Беларусі", "Доклады НАН Беларуси", "Журнал БГУ",
    "Вестник БНТУ", "Известия НАН Беларуси", "Наука и инновации",
    "Вопросы экономики", "Проблемы теории и практики управления",
    "Экономист", "Финансы и кредит", "Право и экономика",
    "Государство и право", "Журнал российского права",
]

# Названия книг/статей (шаблоны)
TITLE_TEMPLATES = {
    "book": [
        "Основы {field}",
        "{Field} в современных условиях",
        "Теория и практика {field_gen}",
        "Методология {field_gen}",
        "{Field}: учебное пособие",
        "Введение в {field_acc}",
        "Современные проблемы {field_gen}",
        "{Field} и инновации",
        "Развитие {field_gen} в XXI веке",
    ],
    "article": [
        "К вопросу о {field_prep}",
        "Исследование {field_gen}",
        "Анализ {field_gen} в условиях глобализации",
        "Проблемы и перспективы развития {field_gen}",
        "Новые подходы к {field_dat}",
        "Оценка эффективности {field_gen}",
    ]
}

FIELDS = [
    ("экономика", "экономики", "экономике", "экономику", "экономике"),
    ("право", "права", "праву", "право", "праве"),
    ("педагогика", "педагогики", "педагогике", "педагогику", "педагогике"),
    ("психология", "психологии", "психологии", "психологию", "психологии"),
    ("социология", "социологии", "социологии", "социологию", "социологии"),
    ("философия", "философии", "философии", "философию", "философии"),
    ("история", "истории", "истории", "историю", "истории"),
    ("филология", "филологии", "филологии", "филологию", "филологии"),
    ("биология", "биологии", "биологии", "биологию", "биологии"),
    ("физика", "физики", "физике", "физику", "физике"),
    ("химия", "химии", "химии", "химию", "химии"),
    ("математика", "математики", "математике", "математику", "математике"),
    ("информатика", "информатики", "информатике", "информатику", "информатике"),
    ("менеджмент", "менеджмента", "менеджменту", "менеджмент", "менеджменте"),
    ("маркетинг", "маркетинга", "маркетингу", "маркетинг", "маркетинге"),
]

# =============================================
# ФУНКЦИИ ГЕНЕРАЦИИ
# =============================================

def random_author() -> str:
    """Генерирует случайного автора в формате Фамилия, И. О."""
    return f"{random.choice(SURNAMES)}, {random.choice(INITIALS)}"

def random_author_full() -> str:
    """Генерирует автора в формате И. О. Фамилия"""
    initials = random.choice(INITIALS)
    surname = random.choice(SURNAMES)
    return f"{initials} {surname}"

def random_year(min_year: int = 2015, max_year: int = 2025) -> int:
    return random.randint(min_year, max_year)

def random_pages() -> str:
    return str(random.randint(80, 500))

def random_page_range() -> str:
    start = random.randint(5, 200)
    end = start + random.randint(5, 30)
    return f"{start}–{end}"

def random_publisher(country: str = "BY") -> str:
    if country == "BY":
        return random.choice(PUBLISHERS_BY)
    return random.choice(PUBLISHERS_RU)

def random_city(country: str = "BY") -> str:
    if country == "BY":
        return random.choice(CITIES_BY)
    return random.choice(CITIES_RU)

def random_volume() -> str:
    return str(random.randint(1, 50))

def random_issue() -> str:
    return str(random.randint(1, 12))

def gen_id(text: str, idx: int) -> str:
    return hashlib.md5(f"{text[:30]}_{idx}".encode()).hexdigest()[:12]


class DatasetExpander:
    """Расширитель датасета на основе паттернов"""
    
    def __init__(self, original_dataset_path: str):
        with open(original_dataset_path, 'r', encoding='utf-8') as f:
            self.original = json.load(f)
        
        self.records = self.original.get('records', [])
        self.expanded = []
        self.idx = 0
    
    def create_variation(self, record: Dict, variation_num: int) -> Dict:
        """Создаёт вариацию записи, сохраняя структуру"""
        formatted = record['formatted_output']
        source_type = record['source_type']
        
        # Паттерны замены для разных элементов
        new_formatted = formatted
        
        # 1. Заменяем года
        years = re.findall(r'\b(19|20)\d{2}\b', new_formatted)
        for year in years:
            new_year = str(random_year())
            new_formatted = new_formatted.replace(year, new_year, 1)
        
        # 2. Заменяем количество страниц (XXX с.)
        page_match = re.search(r'(\d{2,3})\s*с\.', new_formatted)
        if page_match:
            new_formatted = new_formatted.replace(
                page_match.group(0), 
                f"{random_pages()} с."
            )
        
        # 3. Заменяем диапазон страниц (С. XX–YY)
        range_match = re.search(r'С\.\s*\d+[–—-]\d+', new_formatted)
        if range_match:
            new_formatted = new_formatted.replace(
                range_match.group(0),
                f"С. {random_page_range()}"
            )
        
        # 4. Заменяем том (Т. X)
        vol_match = re.search(r'Т\.\s*\d+', new_formatted)
        if vol_match:
            new_formatted = new_formatted.replace(
                vol_match.group(0),
                f"Т. {random_volume()}"
            )
        
        # 5. Заменяем номер (№ X)
        issue_match = re.search(r'№\s*\d+', new_formatted)
        if issue_match:
            new_formatted = new_formatted.replace(
                issue_match.group(0),
                f"№ {random_issue()}"
            )
        
        # 6. Заменяем авторов (Фамилия, И. О.)
        author_pattern = r'([А-ЯЁA-Z][а-яёa-z]+),\s+([А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]?\.?)'
        authors_found = re.findall(author_pattern, new_formatted)
        
        author_mapping = {}
        for surname, initials in authors_found:
            if surname not in author_mapping:
                new_surname = random.choice(SURNAMES)
                new_initials = random.choice(INITIALS)
                author_mapping[surname] = (new_surname, new_initials)
        
        for old_surname, (new_surname, new_initials) in author_mapping.items():
            # Заменяем "Фамилия, И. О."
            new_formatted = re.sub(
                rf'{old_surname},\s+[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]?\.?',
                f'{new_surname}, {new_initials}',
                new_formatted
            )
            # Заменяем "И. О. Фамилия"
            new_formatted = re.sub(
                rf'[А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]?\.\s*{old_surname}',
                f'{new_initials} {new_surname}',
                new_formatted
            )
        
        return {
            'id': gen_id(new_formatted, self.idx),
            'source_type': source_type,
            'country_standard': 'BY',
            'formatted_output': new_formatted,
            'is_variation': True,
            'original_id': record.get('id', ''),
            'variation_number': variation_num
        }
    
    def expand(self, target_count: int = 1000, variations_per_record: int = 8) -> List[Dict]:
        """Расширяет датасет до целевого количества
        
        Args:
            target_count: Целевое количество записей
            variations_per_record: Макс. вариаций на одну оригинальную запись
        """
        self.expanded = []
        self.idx = 0
        
        # Включаем оригинальные записи (копируем, чтобы не мутировать оригинал)
        for record in self.records:
            record_copy = record.copy()
            record_copy['is_variation'] = False
            self.expanded.append(record_copy)
            self.idx += 1
        
        # Фильтруем записи для вариаций (исключаем unknown)
        records_to_vary = [r for r in self.records if r.get('source_type') != 'unknown']
        
        if not records_to_vary:
            return self.expanded
        
        # Генерируем вариации с учётом variations_per_record
        variation_counts = {r.get('id', i): 0 for i, r in enumerate(records_to_vary)}
        
        while len(self.expanded) < target_count:
            for record in records_to_vary:
                if len(self.expanded) >= target_count:
                    break
                
                record_id = record.get('id', '')
                current_count = variation_counts.get(record_id, 0)
                
                # Проверяем лимит вариаций для данной записи
                if current_count >= variations_per_record:
                    continue
                
                variation = self.create_variation(record, current_count)
                self.expanded.append(variation)
                self.idx += 1
                variation_counts[record_id] = current_count + 1
            
            # Если все записи достигли лимита, сбрасываем счётчики
            if all(c >= variations_per_record for c in variation_counts.values()):
                variation_counts = {k: 0 for k in variation_counts}
        
        return self.expanded
    
    def save(self, output_path: str, records: List[Dict]):
        """Сохраняет расширенный датасет"""
        # Считаем статистику
        type_stats = {}
        originals = 0
        variations = 0
        
        for r in records:
            t = r.get('source_type', 'unknown')
            type_stats[t] = type_stats.get(t, 0) + 1
            if r.get('is_variation'):
                variations += 1
            else:
                originals += 1
        
        dataset = {
            'metadata': {
                'source': 'vak.gov.by + generated variations',
                'generated_at': datetime.now().isoformat(),
                'total_records': len(records),
                'original_records': originals,
                'generated_variations': variations,
                'type_distribution': type_stats
            },
            'records': records
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        return dataset['metadata']


if __name__ == "__main__":
    print("🔄 Расширение датасета ВАК...")
    
    expander = DatasetExpander('vak_training_dataset.json')
    print(f"Оригинальных записей: {len(expander.records)}")
    
    # Расширяем до 1000 записей
    expanded = expander.expand(target_count=1000)
    print(f"После расширения: {len(expanded)}")
    
    # Сохраняем
    metadata = expander.save('vak_training_dataset_expanded.json', expanded)
    
    print("\n✅ Готово!")
    print(f"Оригиналов: {metadata['original_records']}")
    print(f"Вариаций: {metadata['generated_variations']}")
    print(f"Всего: {metadata['total_records']}")
    
    print("\nРаспределение по типам:")
    for t, c in sorted(metadata['type_distribution'].items(), key=lambda x: -x[1])[:10]:
        print(f"  {t}: {c}")
