# 客户端包初始化文件

# 导出客户端类以便外部访问
from .ali_client import AliClient
from .baidu_client import BaiduClient
from .local_client import LocalClient

__all__ = ['AliClient', 'BaiduClient', 'LocalClient']