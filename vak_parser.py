"""
Парсер сайта ВАК Беларусь для создания датасета обучения

Парсит https://vak.gov.by/bibliographicDescription и извлекает
примеры библиографического оформления в структурированный JSON формат.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import hashlib
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class InputMetadata:
    """Метаданные источника"""
    authors: List[str] = None
    title: str = ""
    year: Optional[int] = None
    publisher: Optional[str] = None
    city: Optional[str] = None
    pages: Optional[str] = None
    isbn: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    access_date: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    journal_title: Optional[str] = None
    edition: Optional[str] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []


@dataclass 
class DatasetRecord:
    """Запись датасета для обучения"""
    id: str
    source_type: str
    country_standard: str  # "BY" или "RF"
    input_metadata: Dict[str, Any]
    formatted_output: str
    raw_example: str
    parsing_confidence: float = 1.0


class VAKParser:
    """Парсер сайта ВАК Беларусь"""
    
    VAK_URL = "https://vak.gov.by/bibliographicDescription"
    
    # Типы источников по ВАК
    SOURCE_TYPES = {
        "одним, двумя": "book_1_3_authors",
        "тремя автор": "book_1_3_authors",
        "четырьмя": "book_4plus_authors",
        "более автор": "book_4plus_authors",
        "коллективным автором": "book_collective_author",
        "многотомн": "multivolume",
        "отдельные тома": "multivolume_part",
        "законодательн": "law",
        "правовые акты": "law",
        "стандарт": "standard",
        "авторефер": "abstract",
        "диссертаци": "dissertation",
        "депонирован": "deposited",
        "архивн": "archive",
        "электронн": "electronic_resource",
        "интернет": "electronic_resource",
        "статьи из журнал": "journal_article",
        "газет": "newspaper_article",
        "сборник": "collection_article",
        "материалы конференц": "conference",
        "съезд": "conference",
        "симпозиум": "conference",
        "рецензи": "review",
        "карт": "map",
        "патент": "patent",
        "препринт": "preprint",
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.records: List[DatasetRecord] = []
    
    def fetch_page(self) -> str:
        """Загружает страницу ВАК"""
        response = self.session.get(self.VAK_URL, timeout=30)
        response.raise_for_status()
        return response.text
    
    def detect_source_type(self, header_text: str) -> str:
        """Определяет тип источника по заголовку секции"""
        header_lower = header_text.lower()
        for keyword, source_type in self.SOURCE_TYPES.items():
            if keyword in header_lower:
                return source_type
        return "unknown"
    
    def parse_authors(self, text: str) -> List[str]:
        """Извлекает авторов из библиографической записи"""
        authors = []
        
        # Паттерн: Фамилия, И. О.
        pattern = r'([А-ЯЁA-Z][а-яёa-z]+),\s*([А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]?\.?)'
        matches = re.findall(pattern, text)
        
        for family, initials in matches:
            authors.append(f"{family}, {initials.strip()}")
        
        # Если не нашли, пробуем другой формат
        if not authors:
            # Формат: И. О. Фамилия
            pattern2 = r'([А-ЯЁA-Z]\.\s*[А-ЯЁA-Z]?\.?)\s+([А-ЯЁA-Z][а-яёa-z]+)'
            matches2 = re.findall(pattern2, text)
            for initials, family in matches2[:4]:  # Макс 4 автора
                authors.append(f"{family}, {initials.strip()}")
        
        return authors[:10]  # Максимум 10 авторов
    
    def parse_year(self, text: str) -> Optional[int]:
        """Извлекает год издания"""
        # Ищем 4-значный год в контексте издания
        pattern = r'[,–—]\s*(19[5-9]\d|20[0-2]\d)\s*[.–—]'
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
        
        # Fallback: любой 4-значный год
        pattern2 = r'\b(19[5-9]\d|20[0-2]\d)\b'
        match2 = re.search(pattern2, text)
        if match2:
            return int(match2.group(1))
        
        return None
    
    def parse_title(self, text: str) -> str:
        """Извлекает название"""
        # Название после точки от автора и до /
        pattern = r'[А-ЯЁA-Z]\.\s+([^/]+)\s*/'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Название до двоеточия (для источников без автора)
        pattern2 = r'^([^:]+):'
        match2 = re.search(pattern2, text)
        if match2:
            return match2.group(1).strip()
        
        return ""
    
    def parse_pages(self, text: str) -> Optional[str]:
        """Извлекает количество страниц"""
        # Паттерн: 123 с. или 123 p. или С. 10-20
        pattern = r'[–—]\s*(\d+)\s*[сpсc]\.'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        
        # Диапазон страниц: С. 10-20
        pattern2 = r'[СCС]\.\s*(\d+[–—-]\d+)'
        match2 = re.search(pattern2, text)
        if match2:
            return match2.group(1)
        
        return None
    
    def parse_publisher(self, text: str) -> Optional[str]:
        """Извлекает издательство"""
        # Паттерн: Город : Издательство,
        pattern = r'[–—]\s*[А-ЯЁA-Za-zа-яё]+\s*:\s*([^,]+?),'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def parse_city(self, text: str) -> Optional[str]:
        """Извлекает город издания"""
        # Паттерн: – Город :
        pattern = r'[–—]\s*([А-ЯЁ][а-яё]+(?:\s*;\s*[А-ЯЁ][а-яё]+)?)\s*:'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def parse_journal(self, text: str) -> Optional[str]:
        """Извлекает название журнала"""
        # Паттерн: // Название журнала. –
        pattern = r'//\s*([^.–—]+)[.–—]'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def parse_volume_issue(self, text: str) -> tuple:
        """Извлекает том и номер"""
        volume = None
        issue = None
        
        # Том: Т. 5 или Vol. 5
        vol_pattern = r'[ТT]\.?\s*(\d+)'
        vol_match = re.search(vol_pattern, text, re.IGNORECASE)
        if vol_match:
            volume = vol_match.group(1)
        
        # Номер: № 5 или No. 5
        issue_pattern = r'[№N][оo]?\.?\s*(\d+)'
        issue_match = re.search(issue_pattern, text, re.IGNORECASE)
        if issue_match:
            issue = issue_match.group(1)
        
        return volume, issue
    
    def parse_url(self, text: str) -> Optional[str]:
        """Извлекает URL"""
        pattern = r'(https?://[^\s<>"]+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).rstrip('.')
        return None
    
    def parse_access_date(self, text: str) -> Optional[str]:
        """Извлекает дату обращения"""
        pattern = r'дата\s+обращения[:\s]*(\d{2}\.\d{2}\.\d{4})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def parse_doi(self, text: str) -> Optional[str]:
        """Извлекает DOI"""
        pattern = r'(10\.\d{4,}/[^\s]+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).rstrip('.')
        return None
    
    def generate_id(self, text: str, index: int) -> str:
        """Генерирует уникальный ID"""
        hash_input = f"{text[:50]}_{index}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def parse_example(self, example_text: str, source_type: str, index: int) -> Optional[DatasetRecord]:
        """Парсит один пример в запись датасета"""
        if len(example_text) < 30:
            return None
        
        # Извлекаем метаданные
        metadata = InputMetadata(
            authors=self.parse_authors(example_text),
            title=self.parse_title(example_text),
            year=self.parse_year(example_text),
            publisher=self.parse_publisher(example_text),
            city=self.parse_city(example_text),
            pages=self.parse_pages(example_text),
            journal_title=self.parse_journal(example_text),
            url=self.parse_url(example_text),
            access_date=self.parse_access_date(example_text),
            doi=self.parse_doi(example_text)
        )
        
        volume, issue = self.parse_volume_issue(example_text)
        metadata.volume = volume
        metadata.issue = issue
        
        # Оценка confidence
        confidence = 1.0
        if not metadata.authors:
            confidence -= 0.2
        if not metadata.title:
            confidence -= 0.3
        if not metadata.year:
            confidence -= 0.1
        
        # Создаём запись
        return DatasetRecord(
            id=self.generate_id(example_text, index),
            source_type=source_type,
            country_standard="BY",
            input_metadata=asdict(metadata),
            formatted_output=example_text.strip(),
            raw_example=example_text.strip(),
            parsing_confidence=max(0.3, confidence)
        )
    
    def parse_page(self, html: str) -> List[DatasetRecord]:
        """Парсит всю страницу ВАК"""
        soup = BeautifulSoup(html, 'lxml')
        records = []
        
        # Находим все таблицы с примерами
        tables = soup.find_all('table')
        
        current_source_type = "unknown"
        index = 0
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    # Первая ячейка - тип документа
                    type_cell = cells[0].get_text(strip=True)
                    if type_cell and len(type_cell) > 5:
                        detected_type = self.detect_source_type(type_cell)
                        if detected_type != "unknown":
                            current_source_type = detected_type
                    
                    # Вторая ячейка - пример(ы)
                    example_cell = cells[1]
                    
                    # Разбиваем по переносам строк
                    examples = example_cell.get_text().split('\n')
                    
                    for example in examples:
                        example = example.strip()
                        if len(example) > 40:  # Минимальная длина записи
                            record = self.parse_example(example, current_source_type, index)
                            if record:
                                records.append(record)
                                index += 1
        
        return records
    
    def run(self) -> List[Dict[str, Any]]:
        """Запускает полный парсинг"""
        print("Загрузка страницы ВАК...")
        html = self.fetch_page()
        print(f"Загружено {len(html)} символов")
        
        print("Парсинг примеров...")
        records = self.parse_page(html)
        print(f"Найдено {len(records)} записей")
        
        # Конвертируем в словари
        return [asdict(r) for r in records]
    
    def save_dataset(self, records: List[Dict], filename: str = "vak_training_dataset.json"):
        """Сохраняет датасет в JSON"""
        dataset = {
            "metadata": {
                "source": "vak.gov.by",
                "parsed_at": datetime.now().isoformat(),
                "total_records": len(records),
                "standard": "STB 7.1-2003 / ВАК РБ"
            },
            "records": records
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        print(f"Сохранено в {filename}")
        return filename


if __name__ == "__main__":
    parser = VAKParser()
    records = parser.run()
    
    if records:
        parser.save_dataset(records)
        
        # Выводим статистику по типам
        type_stats = {}
        for r in records:
            t = r['source_type']
            type_stats[t] = type_stats.get(t, 0) + 1
        
        print("\nСтатистика по типам:")
        for t, count in sorted(type_stats.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")
