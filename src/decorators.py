# -*- coding: utf-8 -*-
"""
Декораторы для приложения
"""

import functools
import time
from loguru import logger
import wx

def log_method_calls(func):
    """Декоратор для логирования вызовов методов"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        class_name = args[0].__class__.__name__ if args else "Unknown"
        logger.debug(f"Вызов метода: {class_name}.{func.__name__}")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в методе {class_name}.{func.__name__}: {e}")
            raise
    return wrapper

def measure_time(func):
    """Декоратор для измерения времени выполнения"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"Метод {func.__name__} выполнен за {end_time - start_time:.4f} сек")
        return result
    return wrapper

def wx_call_after(func):
    """Декоратор для вызова в главном потоке wx"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if wx.IsMainThread():
            return func(*args, **kwargs)
        else:
            wx.CallAfter(func, *args, **kwargs)
    return wrapper
