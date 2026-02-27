# src/core/steam_workshop_service.py
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse, parse_qs, urljoin
from src.models.mod import ModDependency
from src.core.process_monitor import CacheManager

logger = logging.getLogger(__name__)

class SteamWorkshopService:
    """Сервис для взаимодействия со Steam Workshop."""

    _SURROGATE_PATTERN = re.compile(r"[\ud800-\udfff]")

    def __init__(self):
        self.session = requests.Session()
        self.cache_manager = CacheManager()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Минимум 1 секунда между запросами
        self.max_retries = 3  # Максимальное количество повторных попыток
        # Можно добавить retries, адаптеры и т.д. при необходимости
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        })

    def _wait_for_rate_limit(self):
        """Ожидание для соблюдения лимитов запросов"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"[SteamWorkshopService] Ожидание {sleep_time:.2f}с для соблюдения лимитов")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_request_with_retry(self, url: str, timeout: int = 15) -> Optional[requests.Response]:
        """Выполняет запрос с повторными попытками при 429 ошибках"""
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()
                response = self.session.get(url, timeout=timeout)
                
                if response.status_code == 429:
                    # Too Many Requests - ждем и повторяем
                    wait_time = min(60, (2 ** attempt) + random.uniform(0, 1))  # Экспоненциальная задержка
                    logger.warning(f"[SteamWorkshopService] 429 ошибка, попытка {attempt + 1}/{self.max_retries}, ожидание {wait_time:.1f}с")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"[SteamWorkshopService] Ошибка запроса после {self.max_retries} попыток: {e}")
                    return None
                logger.warning(f"[SteamWorkshopService] Попытка {attempt + 1} не удалась: {e}")
                time.sleep(1)
        
        return None

    def get_mod_details(self, mod_id: str) -> Optional[Dict[str, any]]:
        """
        Получает название, автора, описание, теги и зависимости мода с кэшированием.
        :param mod_id: ID мода.
        :return: Словарь с ключами 'title', 'author', 'description', 'tags', 'dependencies' или None при ошибке.
        """
        cache_key = f"mod_details_{mod_id}"
        
        # Проверяем кэш
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.debug(f"[SteamWorkshopService/Details] Используем кэш для мода {mod_id}")
            return cached_data
        
        # Если нет в кэше, загружаем данные
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            response = self._make_request_with_retry(url)
            if not response:
                logger.warning(f"[SteamWorkshopService/Details] Не удалось получить данные для мода {mod_id} после {self.max_retries} попыток")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Извлечение названия ---
            title_elem = soup.find('div', class_='workshopItemTitle')
            raw_title = title_elem.text if title_elem else mod_id
            title = self._sanitize_text(raw_title, default=mod_id)

            # --- Извлечение автора ---
            # Более точный способ найти автора
            author_elem = soup.find('div', class_='friendBlockContent')
            raw_author = author_elem.text if author_elem else "Неизвестен"
            author = self._sanitize_text(raw_author, default="Неизвестен")

            # --- Извлечение описания ---
            # Попытка найти описание
            desc_elem = soup.find('div', class_='workshopItemDescription') or soup.find('div', id='highlightContentDescription')
            raw_description = desc_elem.text if desc_elem else "Нет описания"
            description = self._sanitize_text(raw_description, default="Нет описания")

            # --- Извлечение тегов и зависимостей ---
            tags, dependencies = self._extract_tags_and_dependencies(soup)
            tags = [self._sanitize_text(tag) for tag in tags]

            result = {
                'title': title,
                'author': author,
                'description': description,
                'tags': tags,
                'dependencies': dependencies
            }
            
            # Сохраняем в кэш на 1 час (3600 секунд)
            self.cache_manager.set(cache_key, result, ttl=3600.0)
            logger.debug(f"[SteamWorkshopService/Details] Загружены и закэшированы данные для мода {mod_id}")
            
            return result
        except Exception as e:
            logger.error(f"[SteamWorkshopService/Details] Ошибка при парсинге деталей мода {mod_id}: {e}")
        return None

    def get_mod_update_info(self, mod_id: str) -> Optional[Dict[str, str]]:
        """
        Получает дату обновления, размер файла и URL изображения с кэшированием.
        :param mod_id: ID мода.
        :return: Словарь с ключами 'updated_date', 'file_size', 'image_url' или None при ошибке.
        """
        cache_key = f"mod_update_info_{mod_id}"
        
        # Проверяем кэш
        cached_data = self.cache_manager.get(cache_key)
        if cached_data:
            logger.debug(f"[SteamWorkshopService/UpdateInfo] Используем кэш для мода {mod_id}")
            return cached_data
        
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
        try:
            response = self._make_request_with_retry(url)
            if not response:
                logger.warning(f"[SteamWorkshopService/UpdateInfo] Не удалось получить данные для мода {mod_id} после {self.max_retries} попыток")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Извлечение даты обновления ---
            updated_date = "Неизвестно"
            # Метод 1: Поиск по классам, используемым Steam
            # Updated: 17 Oct, 2023 @ 10:34am
            updated_label = soup.find('div', class_='detailsStatLeft', string=re.compile(r'.*Updated.*|.*Обновлено.*', re.I))
            if updated_label:
                updated_value = updated_label.find_next('div', class_='detailsStatRight')
                if updated_value:
                    updated_date = self._sanitize_text(updated_value.text, default="Неизвестно")

            # --- Извлечение размера файла ---
            file_size = "Неизвестно"
            # Метод 1: Поиск по классам, используемым Steam
            # Size: 25.991 MB
            size_label = soup.find('div', class_='detailsStatLeft', string=re.compile(r'.*Size.*|.*Размер.*', re.I))
            if size_label:
                size_value = size_label.find_next('div', class_='detailsStatRight')
                if size_value:
                    file_size = self._sanitize_text(size_value.text, default="Неизвестно")

            # --- Извлечение URL изображения ---
            image_url = None
            # Поиск превью-изображения
            preview_img = soup.find('img', id='previewImageMain')
            if preview_img and preview_img.get('src'):
                image_url = preview_img['src']
            
            # Если не нашли основное изображение, ищем другие варианты
            if not image_url:
                # Поиск в модальной галерее
                modal_img = soup.find('div', class_='modalPreviewImage')
                if modal_img:
                    img_tag = modal_img.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag['src']
                
                # Поиск в списке скриншотов
                if not image_url:
                    screenshot_img = soup.find('img', class_='workshopItemPreviewImage')
                    if screenshot_img and screenshot_img.get('src'):
                        image_url = screenshot_img['src']

            result = {
                'updated_date': updated_date,
                'file_size': file_size,
                'image_url': image_url
            }
            
            # Сохраняем в кэш на 30 минут (1800 секунд)
            self.cache_manager.set(cache_key, result, ttl=1800.0)
            logger.debug(f"[SteamWorkshopService/UpdateInfo] Загружены и закэшированы данные для мода {mod_id}")
            
            return result
        except Exception as e:
            logger.error(f"[SteamWorkshopService/UpdateInfo] Ошибка при парсинге инфо об обновлении мода {mod_id}: {e}")
        return None

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Извлекает URL основного изображения превью мода.
        :param soup: BeautifulSoup объект страницы мода.
        :return: URL изображения или None.
        """
        image_url = None
        try:
            # Стратегия 1: Искать по ID 'previewImage' (часто используется)
            preview_image_by_id = soup.find('img', id='previewImage')
            if preview_image_by_id and preview_image_by_id.get('src'):
                image_url = preview_image_by_id['src']
                logger.debug(f"[SteamWorkshopService/Image] Найдено по ID 'previewImage': {image_url}")
                return image_url

            # Стратегия 2: Искать по классу 'workshopItemPreviewImageMain' (основное изображение)
            preview_image_main = soup.find('img', class_='workshopItemPreviewImageMain')
            if preview_image_main and preview_image_main.get('src'):
                image_url = preview_image_main['src']
                logger.debug(f"[SteamWorkshopService/Image] Найдено по классу 'workshopItemPreviewImageMain': {image_url}")
                return image_url

            # Стратегия 3: Искать по классу 'workshopItemPreviewImage' внутри 'workshopItemPreviewHolder'
            # Это соответствует вашему примеру HTML
            holder = soup.find('div', class_='workshopItemPreviewHolder')
            if holder:
                preview_image_in_holder = holder.find('img', class_='workshopItemPreviewImage')
                if preview_image_in_holder and preview_image_in_holder.get('src'):
                    image_url = preview_image_in_holder['src']
                    logger.debug(f"[SteamWorkshopService/Image] Найдено по классу 'workshopItemPreviewImage' внутри 'workshopItemPreviewHolder': {image_url}")
                    return image_url

            # Стратегия 4: Искать первое изображение с классом 'workshopItemPreviewImage' (fallback)
            preview_image_fallback = soup.find('img', class_='workshopItemPreviewImage')
            if preview_image_fallback and preview_image_fallback.get('src'):
                image_url = preview_image_fallback['src']
                logger.debug(f"[SteamWorkshopService/Image] Найдено по классу 'workshopItemPreviewImage' (fallback): {image_url}")
                return image_url

            # Если ничего не найдено
            logger.debug("[SteamWorkshopService/Image] URL изображения не найден.")
            return None
        except Exception as e:
            logger.error(f"[SteamWorkshopService/Image] Ошибка при извлечении URL изображения: {e}")
            return None

    def _extract_tags_and_dependencies(self, soup: BeautifulSoup) -> Tuple[List[str], List[str]]:
        """
        Извлекает теги и зависимости из BeautifulSoup объекта страницы мода.
        :param soup: BeautifulSoup объект страницы мода.
        :return: Кортеж (список тегов, список ID зависимостей).
        """
        tags = []
        dependencies = []
        try:
            # --- Извлечение тегов ---
            # Ищем все элементы div с классом 'workshopTags'
            tag_containers = soup.find_all('div', class_='workshopTags')
            logger.debug(f"[SteamWorkshopService/TagsDeps] Найдено {len(tag_containers)} контейнеров тегов.")
            all_tags = []
            for container in tag_containers:
                # Ищем все ссылки <a> внутри контейнера
                tag_links = container.find_all('a', href=True)
                for link in tag_links:
                    # Текст ссылки - это и есть тег
                    tag_text = link.get_text()
                    clean_tag = self._sanitize_text(tag_text)
                    if clean_tag:
                        all_tags.append(clean_tag)
                        logger.debug(f"[SteamWorkshopService/TagsDeps/Tags] Найден тег: '{tag_text}'")

            tags = list(dict.fromkeys(all_tags)) # Убираем дубликаты, сохраняя порядок
            logger.debug(f"[SteamWorkshopService/TagsDeps] Извлечены теги: {tags}")

            # --- Извлечение зависимостей ---
            # Ищем контейнер зависимостей по его ID
            dependencies_container = soup.find('div', id='RequiredItems')
            if dependencies_container:
                logger.debug("[SteamWorkshopService/TagsDeps] Найден контейнер зависимостей по ID 'RequiredItems'.")
                # Ищем все ссылки на моды внутри контейнера
                # Уточняем поиск: ссылки с атрибутом href, содержащим 'filedetails/?id='
                links = dependencies_container.find_all('a', href=lambda href: href and 'filedetails/?id=' in href)
                for link in links:
                    href = link.get('href', '')
                    # Используем urljoin для корректной обработки URL
                    full_href = urljoin("https://steamcommunity.com/", href)
                    parsed_url = urlparse(full_href)
                    query_params = parse_qs(parsed_url.query)
                    dep_id_list = query_params.get('id', [])
                    if dep_id_list:
                        dependencies.append(dep_id_list[0])
                        logger.debug(f"[SteamWorkshopService/TagsDeps/Deps] Найдена зависимость: {dep_id_list[0]}")
            else:
                logger.info("[SteamWorkshopService/TagsDeps] Контейнер зависимостей по ID 'RequiredItems' не найден. Попытка альтернативного метода.")
                # Альтернативный метод: поиск в скриптах
                # Этот метод ищет вызовы JS функций, которые открывают popup с деталями мода
                # ShowFileDescriptionPopup( '123456789' ) или ShowFileDescriptionPopup( "123456789" )
                pattern = re.compile(r'ShowFileDescriptionPopup\(\s*["\'](\d+)["\']\s*\)')
                script_tags = soup.find_all('script')
                found_in_scripts = False
                for script in script_tags:
                    if script.string:
                        matches = pattern.findall(script.string)
                        if matches:
                            found_in_scripts = True
                            for match in matches:
                                dependencies.append(match)
                                logger.debug(f"[SteamWorkshopService/TagsDeps/Deps/Script] Найдена зависимость: {match}")
                if not found_in_scripts:
                    logger.info("[SteamWorkshopService/TagsDeps] Зависимости в скриптах не найдены.")

            # Убираем дубликаты из зависимостей
            dependencies = list(dict.fromkeys(dependencies))
            logger.debug(f"[SteamWorkshopService/TagsDeps] Итоговый список зависимостей: {dependencies}")

        except Exception as e:
            logger.error(f"[SteamWorkshopService/TagsDeps] Ошибка при извлечении тегов/зависимостей: {e}")

        return tags, dependencies

    def _sanitize_text(self, text: Optional[str], default: str = "") -> str:
        """Удаляет суррогатные символы и нормализует текст для безопасного сохранения."""
        if not text:
            return default
        if isinstance(text, bytes):
            try:
                text = text.decode('utf-8', errors='ignore')
            except Exception:
                return default
        cleaned = self._SURROGATE_PATTERN.sub('', text)
        cleaned = cleaned.strip()
        return cleaned if cleaned else default

    def get_mod_dependencies_raw(self, mod_id: str) -> List[str]:
        """
        Получает список ID зависимостей мода (сырые данные).
        :param mod_id: ID мода.
        :return: Список строк с ID зависимостей.
        """
        # Используем уже реализованный метод
        details = self.get_mod_details(mod_id)
        if details and 'dependencies' in details:
            return details['dependencies']
        return []

    def get_collection_mods(self, collection_id: str) -> List[str]:
        """
        Получает список ID модов из коллекции.
        :param collection_id: ID коллекции.
        :return: Список строк с ID модов.
        """
        mod_ids = []
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Метод: BeautifulSoup - ищем ссылки на моды
            # Фильтруем ссылки, которые ведут на страницы модов (а не коллекций)
            links = soup.find_all('a', href=re.compile(r'sharedfiles/filedetails/\?id=\d+'))
            potential_mod_ids = []
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    parsed_url = urlparse(full_url)
                    query_params = parse_qs(parsed_url.query)
                    mod_id_list = query_params.get('id', [])
                    if mod_id_list:
                        potential_mod_id = mod_id_list[0]
                        # Простая проверка: если ID в URL совпадает с collection_id, это сама коллекция
                        # или можно проверить, есть ли внутри элемент, указывающий на тип "Collection"
                        # Пока просто исключим саму коллекцию
                        if potential_mod_id != collection_id:
                            potential_mod_ids.append(potential_mod_id)

            # Убираем дубликаты
            mod_ids = list(set(potential_mod_ids))
            logger.info(f"[SteamWorkshopService/Collection] Коллекция {collection_id} распарсена. Найдено {len(mod_ids)} уникальных модов (исключая саму коллекцию).")
            return mod_ids

        except requests.RequestException as e:
            logger.error(f"[SteamWorkshopService/Collection] Сетевая ошибка при парсинге коллекции {collection_id}: {e}")
        except Exception as e:
            logger.error(f"[SteamWorkshopService/Collection] Ошибка парсинга коллекции {collection_id}: {e}")
        return mod_ids

    def get_mod_dependency_details(self, mod_id: str, installed_mod_ids: Optional[Set[str]] = None) -> List[ModDependency]:
        """
        Получает детали зависимостей мода (ID, название, статус установлен/не установлен).
        :param mod_id: ID мода.
        :param installed_mod_ids: Набор (set) ID установленных модов для проверки статуса.
        :return: Список объектов ModDependency.
        """
        if installed_mod_ids is None:
            installed_mod_ids = set()

        # Получаем список ID зависимостей
        raw_deps = self.get_mod_dependencies_raw(mod_id)
        dependency_items = []
        for dep_id in raw_deps:
            # Получаем детали зависимости (название)
            details = self.get_mod_details(dep_id)
            dep_name = details['title'] if details and details.get('title') else f"Мод ({dep_id})"
            # Проверяем, установлена ли зависимость
            is_installed = dep_id in installed_mod_ids
            # Создаем объект ModDependency
            dependency_items.append(ModDependency(mod_id=dep_id, name=dep_name, is_installed=is_installed))
        return dependency_items

    def invalidate_cache(self, mod_id: str = None):
        """
        Инвалидация кэша для конкретного мода или всего кэша.
        
        :param mod_id: ID мода для очистки (опционально).
        """
        if mod_id:
            # Очищаем кэш для конкретного мода
            self.cache_manager.invalidate(f"mod_details_{mod_id}")
            self.cache_manager.invalidate(f"mod_update_info_{mod_id}")
            logger.info(f"[SteamWorkshopService] Кэш очищен для мода {mod_id}")
        else:
            # Очищаем весь кэш
            self.cache_manager.clear()
            logger.info("[SteamWorkshopService] Весь кэш очищен")
    
    def get_cached_mods(self, mod_ids: List[str]) -> Dict[str, Dict[str, any]]:
        """
        Возвращает данные для модов, которые есть в кэше.
        
        :param mod_ids: Список ID модов для проверки.
        :return: Словарь {mod_id: cached_data} только для модов с кэшем.
        """
        cached_mods = {}
        for mod_id in mod_ids:
            cached_data = self.cache_manager.get(f"mod_details_{mod_id}")
            if cached_data:
                cached_mods[mod_id] = cached_data
        return cached_mods
    
    def preload_missing_mods(self, mod_ids: List[str]) -> Dict[str, bool]:
        """
        Загружает данные для модов, которых нет в кэше.
        
        :param mod_ids: Список ID модов для проверки и загрузки.
        :return: Словарь {mod_id: success} с результатами загрузки.
        """
        results = {}
        for mod_id in mod_ids:
            cache_key = f"mod_details_{mod_id}"
            if not self.cache_manager.get(cache_key):
                # Мода нет в кэше, загружаем
                details = self.get_mod_details(mod_id)
                results[mod_id] = details is not None
            else:
                results[mod_id] = True  # Уже в кэше
        return results

# Глобальный экземпляр (или использовать DI)
steam_workshop_service = SteamWorkshopService()
