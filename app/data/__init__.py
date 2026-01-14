# app/data/__init__.py
# 统一暴露数据层接口，方便外部调用
# 根据重构后的数据协议，移除不存在的接口，仅保留当前有效对象和方法。

from .core.database import init_db, get_db_connection
from .dao.user_dao import UserDAO
from .services.history_service import ActivityHistoryManager
# 注释或移除已不存在的导入
# from .dao.activity_dao import ActivityDAO, StatsDAO, OcrDAO

__all__ = [
    'init_db',
    'get_db_connection',
    'UserDAO',
    # 'ActivityDAO',  # 已移除
    # 'StatsDAO',     # 已移除
    # 'OcrDAO',       # 已移除
    'ActivityHistoryManager'
]