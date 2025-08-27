"""OCR客户端基类模块

提供OCR客户端的抽象基类定义，包含通用的验证和处理方法
"""
from abc import ABC, abstractmethod
from typing import Optional, Union
import base64
import os

from utils import log


class BaseClient(ABC):
    """OCR客户端抽象基类
    
    定义OCR客户端的基本接口和通用功能方法
    """
    client_type: str

    @abstractmethod
    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        """识别图像中的文本内容
        
        Args:
            image_source: 图像源，可以是文件路径、字节数据或URL
            is_url: 是否为URL图像源
            
        Returns:
            Optional[str]: 识别到的文本内容，识别失败返回None
        """

    def validate_image_source(self, image_source: Union[str, bytes], is_url: bool):
        """验证图像源格式
        
        Args:
            image_source: 图像源数据
            is_url: 是否为URL格式
            
        Raises:
            ValueError: 当图像源格式不符合要求时抛出
        """
        if is_url:
            if not isinstance(image_source, str) or not image_source.startswith(
                ('http://', 'https://')):
                raise ValueError("URL格式不正确，必须以http://或https://开头")
        else:
            if not isinstance(image_source, bytes):
                raise ValueError("非URL模式下，image_source必须是字节类型")

    def process_recognition_result(self, result: Optional[str],
                                  image_source: Union[str, bytes],
                                  is_url: bool) -> Optional[str]:
        """处理识别结果
        
        Args:
            result: 识别结果
            image_source: 图像源
            is_url: 是否为URL格式
            
        Returns:
            Optional[str]: 处理后的结果或None
        """
        if result:
            log("INFO", f"识别成功: {result}")
            return result
        
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
        if not is_url and isinstance(image_source, bytes):
            return "binary_image"
        return "unknown_image"

    def __str__(self) -> str:
        return f"{self.client_type}_client"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.client_type} at {hex(id(self))}>"
    