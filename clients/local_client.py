import gc
import json
import threading
import re
import time
import multiprocessing
from io import BytesIO
from typing import Optional, Union

import easyocr
import numpy as np
from PIL import Image

from utils import load_config, log, log_print
from .base_client import BaseClient


class LocalClient(BaseClient):
    client_type: str = "local"

    def __init__(self, max_retries=3, gpu=False):
        self.config = load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-K][1-7]$'))
        self.client_type = 'local'
        self.reader = None
        self.max_retries = max_retries
        self.gpu = gpu
        self._reader_lock = threading.Lock()

        cpu_count = multiprocessing.cpu_count()
        max_threads_limit = max(1, cpu_count // 4)
        json_threads = self.config.get("CONCURRENCY", 1)
        self.max_threads = min(json_threads, max_threads_limit)
        log_print(f"[DEBUG] CPU核心数: {cpu_count}, 最大限制线程数: {max_threads_limit}, JSON配置线程数: {json_threads}, 最终设置线程数: {self.max_threads}")

        self._initialize_reader()

    def _initialize_reader(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                log_print(f"[DEBUG] 正在尝试加载OCR模型 (尝试 {retry_count + 1}/{self.max_retries})...")
                with self._reader_lock:
                    self.reader = easyocr.Reader(['en'], gpu=self.gpu)
                log("INFO", "OCR模型加载成功")
                return
            except (ImportError, RuntimeError, OSError) as e:
                error_msg = f"模型加载失败: {str(e)}"
                log("ERROR", error_msg)
                log_print(f"[ERROR] {error_msg}")
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = min(2 ** retry_count, 10)
                    log_print(f"[DEBUG] {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    log("ERROR", f"达到最大重试次数 ({self.max_retries})，无法加载OCR模型")
                    raise RuntimeError(f"无法加载OCR模型，错误: {str(e)}")

    def get_img(self, img_file):
        return img_file

    def optimized_preprocess_from_image(self, image: Image.Image, filename: str, max_size=800):
        try:
            # 使用上下文管理器确保图像文件正确关闭
            log_print(f"[DEBUG] 正在预处理图像: {filename}")
            img_width, img_height = image.size
            log_print(f"[DEBUG] 原始图像 - 尺寸: {img_width}x{img_height}, 模式: {image.mode}")

            if not self.gpu and max(image.size) > max_size:
                scale = max_size / max(image.size)
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                log_print(f"[DEBUG] 图像已缩放至: {new_size}")
            elif self.gpu:
                log_print(f"[DEBUG] 使用GPU加速，不缩放图像")

            # 验证图像模式并转换为灰度
            if image.mode not in ['L', 'RGB', 'RGBA']:
                log_print(f"[WARNING] 不支持的图像模式: {image.mode}，转换为RGB")
                image = image.convert('RGB')
            gray_image = image.convert('L')
            result = np.array(gray_image)
            return result
        except (IOError, ValueError, TypeError) as e:
            error_msg = f"图像预处理错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            log("错误", f"图像预处理失败: {filename}")
            return None

    def extract_matches(self, texts):
        for text in texts:
            if self.pattern.fullmatch(text.strip()):
                return text.strip().upper()
        return None

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        """
        在本地执行OCR识别

        参数:
            image_source: 图像源（文件路径或字节数据）
            is_url: 是否为URL

        返回:
            str: 识别结果或None
        """
        self.validate_image_source(image_source, is_url)
        start_time = time.time()
        filename = self.get_image_filename(image_source, is_url)

        # 处理图像源
        if is_url:
            # 对于URL，需要先下载图像
            import requests
            try:
                response = requests.get(image_source, timeout=10)
                response.raise_for_status()
                img_data = response.content
                with Image.open(BytesIO(img_data)) as img:
                    processed_image = self.optimized_preprocess_from_image(img, filename, max_size=300)
            except requests.exceptions.RequestException as e:
                log("错误", f"图像下载失败")
                return None
        else:
            # 对于二进制数据
            with Image.open(BytesIO(image_source)) as img:
                processed_image = self.optimized_preprocess_from_image(img, filename, max_size=300)

        if processed_image is not None:
            try:
                # 添加图像信息日志，帮助诊断异常图像
                img_height, img_width = processed_image.shape[:2]
                log_print(f"[DEBUG] 处理图像 - 尺寸: {img_width}x{img_height}")

                with self._reader_lock:
                    result = self.reader.readtext(processed_image, detail=0)
                log_print(f"[DEBUG] OCR原始识别结果: {result}")
                matched_result = self.extract_matches(result)
                raw_result = json.dumps({"texts": result})
                processing_time = time.time() - start_time

                log_print(f"[DEBUG] 本地OCR识别完成，耗时: {processing_time:.2f}秒")

                if matched_result:
                    log("成功", f"识别结果: {matched_result}")
                    return matched_result
                else:
                    log("警告", f"未识别到有效结果")
                    return None
            except (RuntimeError, ValueError) as e:
                # 捕获并记录内存访问错误等严重异常
                error_type = type(e).__name__
                error_msg = f"OCR识别严重异常 ({error_type}): {str(e)}"
                log("ERROR", error_msg)
                log_print(f"[ERROR] {error_msg}")
                # 记录异常图像路径，便于后续分析
                log_print(f"[ERROR] 异常图像路径: {filename}")
                return None
            finally:
                # 确保图像处理后释放内存
                try:
                    if 'processed_image' in locals() and processed_image is not None:
                        del processed_image
                        # 强制进行垃圾回收
                        gc.collect()
                except (TypeError, AttributeError, OSError) as e:
                    log_print(f"[WARNING] 图像资源释放失败: {str(e)}")
        else:
            log("ERROR", "图像预处理失败")
            log_print("[ERROR] 图像预处理失败")
            return None