# app/data/__init__.py
# 统一暴露数据层接口，方便外部调用
# 根据重构后的数据协议，移除不存在的接口，仅保留当前有效对象和方法。

from .core.database import init_db, get_db_connection, get_db_path
from .dao.activity_dao import ActivityDAO, StatsDAO
from .services.history_service import ActivityHistoryManager

__all__ = [
    'init_db',
    'get_db_connection',
    'get_db_path',
    'ActivityDAO',
    'StatsDAO',
    'ActivityHistoryManager'
]