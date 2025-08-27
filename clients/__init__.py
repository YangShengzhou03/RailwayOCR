"""OCR客户端包，提供不同OCR服务的客户端实现

包含阿里云、百度和本地OCR客户端的统一入口"""
from .ali_client import AliClient
from .baidu_client import BaiduClient
from .local_client import LocalClient

__all__ = ['AliClient', 'BaiduClient', 'LocalClient']
