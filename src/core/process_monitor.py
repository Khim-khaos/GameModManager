# -*- coding: utf-8 -*-
"""
Мониторинг процессов и кэширование данных
"""
import os
import json
import time
import psutil
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from loguru import logger
from src.data.config import PROCESS_CACHE_FILE
from src.core.i18n import _

@dataclass
class CacheEntry:
    """Запись в кэше"""
    data: dict
    timestamp: float
    ttl: float  # Time to live в секундах

    def is_expired(self) -> bool:
        """Проверка, истекло ли время жизни кэша"""
        return time.time() - self.timestamp > self.ttl


class ProcessMonitor:
    """Мониторинг запущенных процессов"""
    
    def __init__(self):
        self._process_cache: Dict[str, Set[str]] = {}
        self._cache_update_time: float = 0
        self._cache_ttl: float = 5.0  # Кэш процессов на 5 секунд
    
    def get_running_processes(self) -> Set[str]:
        """Получение множества запущенных процессов с кэшированием"""
        current_time = time.time()
        
        # Если кэш актуален, возвращаем его
        if current_time - self._cache_update_time < self._cache_ttl:
            return self._process_cache.get('processes', set())
        
        try:
            processes = set()
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_info = proc.info
                    if proc_info['exe']:
                        # Добавляем полный путь и имя файла
                        processes.add(proc_info['exe'].lower())
                        processes.add(os.path.basename(proc_info['exe']).lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            self._process_cache['processes'] = processes
            self._cache_update_time = current_time
            logger.debug(f"Обновлен кэш процессов: {len(processes)} процессов")
            return processes
            
        except Exception as e:
            logger.error(f"Ошибка получения списка процессов: {e}")
            return set()
    
    def is_game_running(self, executable_path: str) -> bool:
        """Проверка, запущена ли игра по пути к исполняемому файлу"""
        if not executable_path or not os.path.exists(executable_path):
            return False
        
        processes = self.get_running_processes()
        exe_lower = executable_path.lower()
        exe_name = os.path.basename(executable_path).lower()
        
        # Проверяем по полному пути и имени файла
        return exe_lower in processes or exe_name in processes


class CacheManager:
    """Менеджер кэша для данных Steam"""
    
    def __init__(self, cache_file: str = None):
        self.cache_file = cache_file or PROCESS_CACHE_FILE
        self._cache: Dict[str, CacheEntry] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Загрузка кэша из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = {
                        key: CacheEntry(
                            data=entry['data'],
                            timestamp=entry['timestamp'],
                            ttl=entry['ttl']
                        )
                        for key, entry in data.items()
                    }
                logger.debug(_("system.cache_loaded", count=len(self._cache)))
            else:
                self._cache = {}
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша: {e}")
            self._cache = {}
    
    def _save_cache(self):
        """Сохранение кэша в файл"""
        try:
            # Очищаем устаревшие записи
            self._cleanup_expired()
            
            data = {
                key: asdict(entry)
                for key, entry in self._cache.items()
            }
            
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Кэш сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")
    
    def _cleanup_expired(self):
        """Очистка устаревших записей кэша"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Удалено устаревших записей кэша: {len(expired_keys)}")
    
    def get(self, key: str, default=None):
        """Получение данных из кэша"""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            logger.debug(f"Данные из кэша: {key}")
            return entry.data
        elif entry:
            logger.debug(f"Кэш устарел: {key}")
            del self._cache[key]
        return default
    
    def set(self, key: str, data: dict, ttl: float = 300.0):
        """Сохранение данных в кэш"""
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
        logger.debug(f"Данные сохранены в кэш: {key} (TTL: {ttl}с)")
        self._save_cache()
    
    def invalidate(self, key: str):
        """Инвалидация конкретного ключа кэша"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Кэш инвалидирован: {key}")
            self._save_cache()
    
    def clear(self):
        """Полная очистка кэша"""
        self._cache.clear()
        logger.info("Кэш полностью очищен")
        self._save_cache()
    
    def get_steam_mods_cache_key(self, app_id: str, mod_ids: List[str]) -> str:
        """Генерация ключа кэша для модов Steam"""
        mod_ids_str = ",".join(sorted(mod_ids))
        return f"steam_mods_{app_id}_{hash(mod_ids_str)}"
    
    def get_steam_game_info_cache_key(self, app_id: str) -> str:
        """Генерация ключа кэша для информации об игре"""
        return f"steam_game_info_{app_id}"
