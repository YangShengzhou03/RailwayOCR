"""OCR客户端基类模块

提供OCR客户端的抽象基类定义，包含通用的验证和处理方法
"""
from abc import ABC, abstractmethod
from typing import Optional, Union
import base64
import gc
import os
import re
import time

from utils import log, log_print


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

    def extract_matches(self, texts, pattern: re.Pattern):
        """从识别文本中提取匹配的模式

        参数:
            texts: OCR识别返回的文本列表
            pattern: 正则表达式模式对象

        返回:
            匹配的模式字符串(如A1, B2等)或None
        """
        for text in texts:
            cleaned_text = text.strip().replace(' ', '').replace('\n', '')
            if pattern.fullmatch(cleaned_text):
                return cleaned_text.upper()

        for text in texts:
            cleaned_text = text.strip().replace(' ', '').replace('\n', '')
            match = pattern.search(cleaned_text)
            if match:
                return match.group().upper()

        return None

    def handle_ocr_error(self, error_msg, attempt, max_retries):
        """处理OCR识别错误，包含重试逻辑
        
        参数:
            error_msg: 错误消息
            attempt: 当前尝试次数
            max_retries: 最大重试次数
            
        返回:
            bool: 是否继续重试
        """
        log("ERROR", error_msg)
        log_print(f"[ERROR] {error_msg}")
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 10)
            log("INFO", f"将在{wait_time}秒后重试...")
            time.sleep(wait_time)
            return True
        return False

    def handle_general_exception(self, error_msg, exception_type=""):
        """处理通用异常
        
        参数:
            error_msg: 错误消息
            exception_type: 异常类型名称
        """
        log("ERROR", error_msg)
        if exception_type:
            log_print(f"[ERROR] {exception_type}: {error_msg}")
        else:
            log_print(f"[ERROR] {error_msg}")

    def cleanup_resources(self, local_vars, resource_names):
        """清理图像处理资源
        
        参数:
            local_vars: locals()字典
            resource_names: 需要清理的资源名称列表
        """
        for var_name in resource_names:
            if var_name in local_vars and local_vars[var_name] is not None:
                try:
                    del local_vars[var_name]
                except (RuntimeError, ValueError, TypeError) as e:
                    log("WARNING", f"释放资源 {var_name} 失败: {str(e)}")
        gc.collect()
        time.sleep(0.01)

    def handle_initialization_retry(self, retry_count, max_retries, error_msg, engine_name):
        """处理初始化重试逻辑
        
        参数:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
            error_msg: 错误消息
            engine_name: 引擎名称
            
        返回:
            bool: 是否继续重试
        """
        log("ERROR", error_msg)
        log_print(f"[{engine_name}] 模型加载异常: {error_msg} (重试次数: {retry_count}/{max_retries})")
        if retry_count < max_retries - 1:
            wait_time = min(2 ** retry_count, 10)
            time.sleep(wait_time)
            return True
        return False
