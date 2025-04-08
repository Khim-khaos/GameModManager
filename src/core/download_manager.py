import threading
from loguru import logger
from core.mod_manager import ModManager

class DownloadManager:
    def __init__(self, steamcmd_path, complete_callback, progress_callback):
        self.mod_manager = ModManager(steamcmd_path)
        self.complete_callback = complete_callback
        self.progress_callback = progress_callback
        self.is_running = False
        self.thread = None

    def start(self):
        if not self.is_running:
            if not self.mod_manager.download_queue:
                logger.warning("Очередь загрузки пуста, загрузка не начата")
                return
            self.is_running = True
            self.thread = threading.Thread(target=self.download_loop, daemon=True)
            self.thread.start()
            logger.info("Менеджер загрузок запущен")
        else:
            logger.warning("Менеджер загрузок уже запущен")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
        logger.info("Менеджер загрузок остановлен")

    def download_loop(self):
        while self.is_running and self.mod_manager.download_queue:
            logger.info(f"Начинается загрузка следующего мода из очереди: {self.mod_manager.download_queue[0]}")
            success = self.mod_manager.download_next(self.progress_callback)
            self.complete_callback(success)
            if success:
                logger.info("Мод успешно загружен")
            else:
                logger.error("Ошибка при загрузке мода")
        self.is_running = False
        logger.info("Все моды из очереди загружены или процесс остановлен")
