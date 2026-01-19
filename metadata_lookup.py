"""
Модуль для получения метаданных из внешних API

Поддерживаемые API:
- CrossRef REST API (по DOI)
- Open Library API (по ISBN)
"""

import re
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MetadataResult:
    """Результат поиска метаданных"""
    success: bool
    source: str  # "crossref", "openlibrary", "manual"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MetadataLookup:
    """Класс для поиска метаданных по DOI и ISBN"""
    
    CROSSREF_API = "https://api.crossref.org/works"
    OPENLIBRARY_API = "https://openlibrary.org/api/books"
    
    # Regex для определения идентификаторов
    DOI_PATTERN = re.compile(r'^10\.\d{4,}/[^\s]+$')
    ISBN_10_PATTERN = re.compile(r'^(\d{9}[\dXx]|\d{1,5}-\d{1,7}-\d{1,7}-[\dXx])$')
    ISBN_13_PATTERN = re.compile(r'^(97[89]\d{10}|97[89]-\d{1,5}-\d{1,7}-\d{1,7}-\d)$')
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
    
    def detect_identifier(self, text: str) -> tuple[str, str]:
        """
        Определяет тип идентификатора
        
        Returns:
            tuple: (тип: "doi"|"isbn"|"unknown", очищенное значение)
        """
        text = text.strip()
        
        # Проверяем DOI
        if self.DOI_PATTERN.match(text):
            return ("doi", text)
        
        # Очищаем ISBN от дефисов для проверки
        clean_isbn = text.replace("-", "").replace(" ", "")
        
        # ISBN-13
        if len(clean_isbn) == 13 and clean_isbn.isdigit():
            return ("isbn", clean_isbn)
        
        # ISBN-10
        if len(clean_isbn) == 10:
            return ("isbn", clean_isbn)
        
        return ("unknown", text)
    
    def lookup_by_doi(self, doi: str) -> MetadataResult:
        """
        Получает метаданные статьи по DOI из CrossRef
        
        Args:
            doi: DOI статьи (например, "10.1038/nature12373")
            
        Returns:
            MetadataResult с данными или ошибкой
        """
        try:
            url = f"{self.CROSSREF_API}/{doi}"
            response = self.client.get(url, headers={
                "User-Agent": "GOST-Formatter/1.0 (mailto:support@example.com)"
            })
            
            if response.status_code == 404:
                return MetadataResult(
                    success=False,
                    source="crossref",
                    error=f"DOI не найден: {doi}"
                )
            
            response.raise_for_status()
            data = response.json()
            
            work = data.get("message", {})
            
            # Извлекаем авторов
            authors = []
            for author in work.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    # Формат: Фамилия, И. О.
                    initials = ". ".join([n[0] + "." for n in given.split() if n]) if given else ""
                    authors.append(f"{family}, {initials}".strip(", "))
            
            # Извлекаем название журнала
            container = work.get("container-title", [])
            journal = container[0] if container else ""
            
            # Извлекаем год
            published = work.get("published", {}).get("date-parts", [[None]])
            year = published[0][0] if published[0] else None
            
            # Извлекаем страницы
            pages = work.get("page", "")
            
            # Извлекаем том и выпуск
            volume = work.get("volume", "")
            issue = work.get("issue", "")
            
            # Название
            titles = work.get("title", [])
            title = titles[0] if titles else ""
            
            return MetadataResult(
                success=True,
                source="crossref",
                data={
                    "type": "article",
                    "authors": authors,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "doi": doi,
                    "publisher": work.get("publisher", ""),
                    "url": f"https://doi.org/{doi}"
                }
            )
            
        except httpx.HTTPError as e:
            return MetadataResult(
                success=False,
                source="crossref",
                error=f"Ошибка HTTP: {str(e)}"
            )
        except Exception as e:
            return MetadataResult(
                success=False,
                source="crossref",
                error=f"Ошибка: {str(e)}"
            )
    
    def lookup_by_isbn(self, isbn: str) -> MetadataResult:
        """
        Получает метаданные книги по ISBN из Open Library
        
        Args:
            isbn: ISBN-10 или ISBN-13
            
        Returns:
            MetadataResult с данными или ошибкой
        """
        try:
            # Очищаем ISBN
            clean_isbn = isbn.replace("-", "").replace(" ", "")
            
            url = f"{self.OPENLIBRARY_API}?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data"
            response = self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            key = f"ISBN:{clean_isbn}"
            if key not in data:
                return MetadataResult(
                    success=False,
                    source="openlibrary",
                    error=f"ISBN не найден: {isbn}"
                )
            
            book = data[key]
            
            # Извлекаем авторов
            authors = []
            for author in book.get("authors", []):
                name = author.get("name", "")
                if name:
                    # Пытаемся разобрать на фамилию и инициалы
                    parts = name.split()
                    if len(parts) >= 2:
                        # Предполагаем: Имя Фамилия или Фамилия Имя
                        authors.append(name)
                    else:
                        authors.append(name)
            
            # Извлекаем издателей
            publishers = book.get("publishers", [])
            publisher = publishers[0].get("name", "") if publishers else ""
            
            # Извлекаем год
            publish_date = book.get("publish_date", "")
            year = None
            if publish_date:
                # Ищем 4-значный год
                year_match = re.search(r'\b(19|20)\d{2}\b', publish_date)
                if year_match:
                    year = int(year_match.group())
            
            # Количество страниц
            pages = book.get("number_of_pages", "")
            
            return MetadataResult(
                success=True,
                source="openlibrary",
                data={
                    "type": "book",
                    "authors": authors,
                    "title": book.get("title", ""),
                    "year": year,
                    "publisher": publisher,
                    "pages": str(pages) if pages else "",
                    "isbn": clean_isbn,
                    "url": book.get("url", "")
                }
            )
            
        except httpx.HTTPError as e:
            return MetadataResult(
                success=False,
                source="openlibrary",
                error=f"Ошибка HTTP: {str(e)}"
            )
        except Exception as e:
            return MetadataResult(
                success=False,
                source="openlibrary",
                error=f"Ошибка: {str(e)}"
            )
    
    def lookup(self, identifier: str) -> MetadataResult:
        """
        Автоматически определяет тип идентификатора и ищет метаданные
        
        Args:
            identifier: DOI или ISBN
            
        Returns:
            MetadataResult с данными
        """
        id_type, clean_value = self.detect_identifier(identifier)
        
        if id_type == "doi":
            return self.lookup_by_doi(clean_value)
        elif id_type == "isbn":
            return self.lookup_by_isbn(clean_value)
        else:
            return MetadataResult(
                success=False,
                source="unknown",
                error=f"Не удалось определить тип идентификатора: {identifier}"
            )
    
    def __del__(self):
        """Закрываем HTTP клиент"""
        if hasattr(self, 'client'):
            self.client.close()


# Глобальный экземпляр для повторного использования
_lookup_instance: Optional[MetadataLookup] = None


def get_metadata_lookup() -> MetadataLookup:
    """Получает или создаёт экземпляр MetadataLookup"""
    global _lookup_instance
    if _lookup_instance is None:
        _lookup_instance = MetadataLookup()
    return _lookup_instance
