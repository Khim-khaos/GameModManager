# -*- coding: utf-8 -*-
"""
Настройка логирования
"""
import os
import logging
from loguru import logger
from src.constants import LOGS_DIR

def setup_logger():
    """Настройка логирования"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    logger.remove()
    log_file = os.path.join(LOGS_DIR, "app.log")
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        encoding="utf-8"
    )
    logger.add(
        lambda msg: print(msg, end=''),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

__all__ = ['logger', 'setup_logger']
