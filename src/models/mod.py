# src/models/mod.py
# -*- coding: utf-8 -*-
"""Модель мода"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class ModDependency:
    """Зависимость мода"""
    mod_id: str
    name: str = ""
    is_installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект зависимости в словарь для сериализации."""
        return {
            'mod_id': self.mod_id,
            'name': self.name,
            'is_installed': self.is_installed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModDependency':
        """Создает объект зависимости из словаря."""
        return cls(
            mod_id=data['mod_id'],
            name=data.get('name', ''), # name может отсутствовать
            is_installed=data.get('is_installed', False)
        )

@dataclass
class Mod:
    """Модель мода"""

    mod_id: str
    name: str = ""
    author: str = ""
    description: str = ""
    created_date: Optional[datetime] = None           # Дата создания мода Steam
    updated_date: Optional[datetime] = None           # Дата последнего обновления мода Steam 
    install_date: Optional[datetime] = None           # Дата установки локально
    local_update_date: Optional[datetime] = None     # Дата последнего локального обновления
    file_size: int = 0                                # Размер в байтах
    dependencies: List[ModDependency] = field(default_factory=list)
    is_enabled: bool = True
    local_path: str = ""
    workshop_url: str = ""

    # Убрали __post_init__, так как default_factory делает то же самое

    @property
    def has_dependencies(self) -> bool:
        """Проверяет, есть ли у мода зависимости."""
        return len(self.dependencies) > 0
    
    @property
    def formatted_file_size(self) -> str:
        """Возвращает размер файла в удобочитаемом формате."""
        if self.file_size == 0:
            return "Неизвестно"
        
        size = self.file_size
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
    
    @property 
    def formatted_install_date(self) -> str:
        """Возвращает дату установки в удобочитаемом формате."""
        if not self.install_date:
            return "Неизвестно"
        return self.install_date.strftime("%d.%m.%Y %H:%M")
    
    @property
    def formatted_updated_date(self) -> str:
        """Возвращает дату последнего обновления Steam в удобочитаемом формате."""
        if not self.updated_date:
            return "Неизвестно"
        return self.updated_date.strftime("%d.%m.%Y %H:%M")
    
    @property
    def formatted_local_update_date(self) -> str:
        """Возвращает дату локального обновления в удобочитаемом формате."""
        if not self.local_update_date:
            return "Неизвестно"
        return self.local_update_date.strftime("%d.%m.%Y %H:%M")

    @property
    def all_dependencies_installed(self) -> bool:
        """Проверяет, установлены ли все зависимости."""
        return all(dep.is_installed for dep in self.dependencies)

    def add_dependency(self, dependency: ModDependency):
        """Добавляет зависимость к моду."""
        # Проверка на дубликаты по mod_id
        if not any(dep.mod_id == dependency.mod_id for dep in self.dependencies):
            self.dependencies.append(dependency)

    def set_dependency_installed_status(self, dep_mod_id: str, is_installed: bool):
        """Устанавливает статус установленности для зависимости по её ID."""
        for dep in self.dependencies:
            if dep.mod_id == dep_mod_id:
                dep.is_installed = is_installed
                break

    def to_dict(self) -> dict:
        """Преобразует объект мода в словарь для сериализации."""
        return {
            'mod_id': self.mod_id,
            'name': self.name,
            'author': self.author,
            'description': self.description,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'install_date': self.install_date.isoformat() if self.install_date else None,
            'local_update_date': self.local_update_date.isoformat() if self.local_update_date else None,
            'file_size': self.file_size,
            'dependencies': [dep.to_dict() for dep in self.dependencies],
            'is_enabled': self.is_enabled,
            'local_path': self.local_path,
            'workshop_url': self.workshop_url
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Mod':
        """Создает объект мода из словаря."""
        # Безопасное извлечение и парсинг дат
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                return datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                # Можно добавить логирование здесь, если нужно
                return None

        dependencies_data = data.get('dependencies', [])
        dependencies = [ModDependency.from_dict(dep_data) for dep_data in dependencies_data]

        return cls(
            mod_id=data['mod_id'],
            name=data.get('name', ''),
            author=data.get('author', ''),
            description=data.get('description', ''),
            created_date=parse_date(data.get('created_date')),
            updated_date=parse_date(data.get('updated_date')),
            install_date=parse_date(data.get('install_date')),
            local_update_date=parse_date(data.get('local_update_date')),
            file_size=data.get('file_size', 0),
            dependencies=dependencies,
            is_enabled=data.get('is_enabled', True),
            local_path=data.get('local_path', ''),
            workshop_url=data.get('workshop_url', '')
        )

    def __repr__(self) -> str:
        """Строковое представление объекта для отладки."""
        return (f"Mod(mod_id='{self.mod_id}', name='{self.name}', "
                f"author='{self.author}', is_enabled={self.is_enabled}, "
                f"has_dependencies={self.has_dependencies})")
