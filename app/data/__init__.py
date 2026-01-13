# app/data/__init__.py
# 统一暴露数据层接口，方便外部调用

from .core.database import init_db, get_db_connection
from .dao.user_dao import UserDAO
from .dao.activity_dao import ActivityDAO, StatsDAO, OcrDAO
from .services.history_service import ActivityHistoryManager

__all__ = [
    'init_db',
    'get_db_connection',
    'UserDAO',
    'ActivityDAO',
    'StatsDAO',
    'OcrDAO',
    'ActivityHistoryManager'
]
