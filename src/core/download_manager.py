import asyncio
from core.mod_manager import ModManager
from tqdm import tqdm
from loguru import logger

class DownloadManager:
    def __init__(self, mod_manager):
        self.mod_manager = mod_manager
        self.max_concurrent_downloads = 3  # Максимум одновременных загрузок

    async def download_single_mod(self, game, mod_id, console_tab, progress_bar):
        dependencies = await self.mod_manager.check_dependencies(game.app_id, mod_id, console_tab.parent())
        if dependencies:
            logger.info(f"Найдены зависимости для мода {mod_id}: {dependencies}")
            for dep_id in dependencies:
                self.mod_manager.download_mod(game, dep_id, console_tab)
                await asyncio.sleep(1)
                progress_bar.update(1)
        self.mod_manager.download_mod(game, mod_id, console_tab)
        await asyncio.sleep(1)
        progress_bar.update(1)

    async def process_queue(self, console_tab, parent=None):
        total_mods = len(self.mod_manager.queue)
        if total_mods == 0:
            logger.info("Очередь загрузки пуста")
            return

        progress_bar = tqdm(total=total_mods, desc="Загрузка модов", unit="мод")
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        async def bounded_download(item):
            async with semaphore:
                await self.download_single_mod(item["game"], item["mod_id"], console_tab, progress_bar)

        tasks = [bounded_download(item) for item in self.mod_manager.queue]
        await asyncio.gather(*tasks)

        self.mod_manager.clear_queue()
        progress_bar.close()
        logger.info("Очередь загрузки завершена")
