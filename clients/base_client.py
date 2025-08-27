from abc import ABC, abstractmethod
from typing import Optional, Union
import base64
import os

from utils import log


class BaseClient(ABC):
    client_type: str

    @abstractmethod
    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        pass

    def validate_image_source(self, image_source: Union[str, bytes], is_url: bool):
        if is_url:
            if not isinstance(image_source, str) or not image_source.startswith(('http://', 'https://')):
                raise ValueError("URL格式不正确，必须以http://或https://开头")
        else:
            if not isinstance(image_source, bytes):
                raise ValueError("非URL模式下，image_source必须是字节类型")

    def process_recognition_result(self, result: Optional[str], image_source: Union[str, bytes], is_url: bool) -> Optional[str]:
        if result:
            log("INFO", f"识别成功: {result}")
            return result
        else:
            filename = image_source if is_url else os.path.basename(str(image_source))
            log("WARNING", f"未识别到有效结果: {filename}")
            return None

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