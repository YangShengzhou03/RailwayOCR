from abc import ABC, abstractmethod
from typing import Optional, Union
import base64
import os

from utils import log


class BaseClient(ABC):
    """客户端基类，定义统一的OCR识别接口"""
    client_type: str = "base"

    @abstractmethod
    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        """
        统一的图像识别接口

        参数:
            image_source: 图像来源，可以是URL字符串或二进制数据
            is_url: 如果为True，表示image_source是URL；如果为False，表示是二进制数据

        返回:
            识别到的匹配字符串（如A1、B2等），未识别到则返回None
        """
        pass

    def process_recognition_result(self, result, image_source, is_url):
        """处理识别结果的通用逻辑"""
        filename = self.get_image_filename(image_source, is_url)
        if result:
            log("INFO", f"识别成功: {result} (文件: {filename})")
            return result
        else:
            log("WARNING", f"未识别到有效内容 (文件: {filename})")
            return None

    @staticmethod
    def validate_image_source(image_source: Union[str, bytes], is_url: bool) -> None:
        """验证图像来源的有效性"""
        if is_url:
            if not isinstance(image_source, str) or not (
                image_source.startswith('http://') or image_source.startswith('https://')):
                raise ValueError("当is_url=True时，image_source必须是有效的HTTP/HTTPS URL")
        else:
            if not isinstance(image_source, bytes):
                raise ValueError("当is_url=False时，image_source必须是二进制数据")

    @staticmethod
    def encode_image_to_base64(image_path: str) -> bytes:
        """将图像文件编码为base64字符串"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read())

    @staticmethod
    def get_image_filename(image_source: Union[str, bytes], is_url: bool) -> str:
        """获取图像的文件名"""
        if is_url and isinstance(image_source, str):
            return os.path.basename(image_source.split('?')[0])
        elif not is_url and isinstance(image_source, bytes):
            return "binary_image"
        return "unknown_image"

    def __str__(self) -> str:
        return f"{self.client_type}_client"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.client_type} at {hex(id(self))}>"