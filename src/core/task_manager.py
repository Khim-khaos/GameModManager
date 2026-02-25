# src/core/task_manager.py
import concurrent.futures
import logging
import threading
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)

class TaskManager:
    """Менеджер фоновых задач."""

    def __init__(self, max_workers: int = 5): # Ограничиваем количество одновременных потоков
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.futures: Dict[concurrent.futures.Future, str] = {} # Сопоставление Future с описанием задачи
        self._lock = threading.Lock() # Для потокобезопасности доступа к futures

    def submit_task(self, func: Callable, *args, description: str = "Задача", **kwargs) -> concurrent.futures.Future:
        """
        Отправляет задачу в пул потоков.
        :param func: Функция для выполнения.
        :param args: Позиционные аргументы функции.
        :param description: Описание задачи для логов.
        :param kwargs: Именованные аргументы функции.
        :return: Future объект.
        """
        future = self.executor.submit(func, *args, **kwargs)
        with self._lock:
            self.futures[future] = description
        logger.debug(f"[TaskManager] Задача '{description}' отправлена.")
        # Добавляем callback для очистки после завершения
        future.add_done_callback(self._task_done_callback)
        return future

    def _task_done_callback(self, future: concurrent.futures.Future):
        """Callback, вызываемый при завершении задачи."""
        with self._lock:
            description = self.futures.pop(future, "Неизвестная задача")
        try:
            # Получаем результат, чтобы пробросить исключения
            result = future.result()
            logger.debug(f"[TaskManager] Задача '{description}' завершена успешно.")
            # Можно добавить событие или callback для уведомления UI
        except Exception as e:
            logger.error(f"[TaskManager] Задача '{description}' завершена с ошибкой: {e}")

    def shutdown(self, wait: bool = True):
        """Завершает работу пула потоков."""
        logger.info("[TaskManager] Завершение работы...")
        self.executor.shutdown(wait=wait)
        logger.info("[TaskManager] Работа завершена.")

# Глобальный экземпляр (или использовать DI)
task_manager = TaskManager()

# В main.py при выходе:
# import atexit
# atexit.register(task_manager.shutdown) # Или явно вызвать при закрытии главного окна
