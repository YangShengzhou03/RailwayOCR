import gc
import re
import threading
import time
from io import BytesIO
from typing import Optional, Union

import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

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
        self._is_initializing = False
        self.recognition_attempts = self.config.get("RECOGNITION_ATTEMPTS", 2)
        self.max_threads = 1
        log_print("[DEBUG] 线程数已强制设置为1")
        self._initialize_reader()

    def _initialize_reader(self):
        if self._is_initializing:
            log_print("[DEBUG] 已有线程正在初始化OCR模型，等待完成...")
            while self._is_initializing:
                time.sleep(0.1)
            return

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self._is_initializing = True

                with self._reader_lock:
                    self.reader = easyocr.Reader(
                        ['en'],
                        gpu=self.gpu,
                        model_storage_directory=self.config.get('MODEL_DIR', None),
                        download_enabled=self.config.get('ALLOW_DOWNLOAD', True)
                    )
                log("INFO", "OCR模型加载成功")
                self._is_initializing = False
                return
            except (ImportError, RuntimeError, OSError) as e:
                error_msg = f"模型加载失败: {str(e)}"
                log("ERROR", error_msg)
                log_print(f"[ERROR] {error_msg}")
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = min(2 ** retry_count, 10)
                    time.sleep(wait_time)
                else:
                    self._is_initializing = False
                    log("ERROR", f"达到最大重试次数 ({self.max_retries})，无法加载OCR模型")
                    raise RuntimeError(f"无法加载OCR模型，错误: {str(e)}")

    def get_img(self, img_file):
        return img_file

    def optimized_preprocess_from_image(self, image: Image.Image, filename: str, max_size=800, enhance_attempt=0):
        try:
            img_width, img_height = image.size

            if not self.gpu and max(image.size) > max_size:
                scale = max_size / max(image.size)
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            if image.mode not in ['L', 'RGB', 'RGBA']:
                log_print(f"[WARNING] 不支持的图像模式: {image.mode}，转换为RGB")
                image = image.convert('RGB')

            if enhance_attempt == 0:
                gray_image = image.convert('L')
                enhancer = ImageEnhance.Contrast(gray_image)
                gray_image = enhancer.enhance(1.2)
            elif enhance_attempt == 1:
                gray_image = image.convert('L')
                enhancer = ImageEnhance.Contrast(gray_image)
                gray_image = enhancer.enhance(1.8)
                gray_image = gray_image.filter(ImageFilter.SHARPEN)
            elif enhance_attempt == 2:
                gray_image = image.convert('L')
                threshold = 128
                gray_image = gray_image.point(lambda p: p > threshold and 255)

            np_image = np.array(gray_image)

            min_val = np.min(np_image)
            max_val = np.max(np_image)
            if max_val > min_val:
                np_image = ((np_image - min_val) / (max_val - min_val) * 255).astype(np.uint8)

            return np_image
        except (IOError, ValueError, TypeError) as e:
            error_msg = f"图像预处理错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            log("错误", f"图像预处理失败: {filename}")
            return None

    def extract_matches(self, texts):
        for text in texts:
            cleaned_text = text.strip().replace(' ', '').replace('\n', '')
            if self.pattern.fullmatch(cleaned_text):
                return cleaned_text.upper()

        for text in texts:
            cleaned_text = text.strip().replace(' ', '').replace('\n', '')
            match = self.pattern.search(cleaned_text)
            if match:
                return match.group().upper()

        return None

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        if image_source is None:
            log("ERROR", "图像源不能为空")
            return None

        start_time = time.time()
        filename = self.get_image_filename(image_source, is_url)
        processed_image = None
        original_image = None

        try:
            if is_url:
                import requests
                try:
                    response = requests.get(image_source, timeout=10)
                    response.raise_for_status()
                    img_data = response.content
                    original_image = Image.open(BytesIO(img_data))
                except requests.exceptions.RequestException as e:
                    log("错误", f"图像下载失败: {str(e)}")
                    return None
            else:
                try:
                    original_image = Image.open(BytesIO(image_source))
                except (IOError, OSError) as e:
                    log("ERROR", f"无法打开图像: {str(e)}")
                    return None

            for attempt in range(self.recognition_attempts):
                try:
                    max_size = 300 if attempt == 0 else 400
                    processed_image = self.optimized_preprocess_from_image(
                        original_image.copy(),
                        filename,
                        max_size=max_size,
                        enhance_attempt=attempt
                    )

                    if processed_image is not None:
                        img_height, img_width = processed_image.shape[:2]

                        if self.reader is None:
                            log_print("[WARNING] OCR阅读器未初始化，尝试重新初始化")
                            self._initialize_reader()

                            if self.reader is None:
                                log_print("[ERROR] OCR阅读器初始化失败，无法继续识别")
                                continue

                        with self._reader_lock:
                            if self.reader is None:
                                log_print("[ERROR] OCR阅读器在锁定期间变为None，无法继续识别")
                                continue

                            if attempt == 0:
                                result = self.reader.readtext(
                                    processed_image,
                                    detail=0,
                                    contrast_ths=0.1,
                                    adjust_contrast=0.5
                                )
                            else:
                                result = self.reader.readtext(
                                    processed_image,
                                    detail=0,
                                    contrast_ths=0.05,
                                    adjust_contrast=0.7,
                                    text_threshold=0.7
                                )

                        matched_result = self.extract_matches(result)

                        if matched_result:
                            processing_time = time.time() - start_time

                            log("成功", f"识别结果: {matched_result}")
                            return matched_result

                except (RuntimeError, ValueError) as e:
                    error_type = type(e).__name__
                    error_msg = f"OCR识别异常 (尝试 {attempt + 1}, {error_type}): {str(e)}"
                    log("ERROR", error_msg)
                    log_print(f"[ERROR] {error_msg}")
                    continue
                finally:
                    if 'processed_image' in locals():
                        del processed_image
                        gc.collect()

            processing_time = time.time() - start_time

            log("警告", f"未识别到有效结果")
            return None

        except Exception as e:
            error_msg = f"识别过程中发生意外错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            return None
        finally:
            try:
                if original_image is not None:
                    original_image.close()
                if 'processed_image' in locals() and processed_image is not None:
                    del processed_image
                gc.collect()
            except (TypeError, AttributeError, OSError) as e:
                log_print(f"[WARNING] 图像资源释放失败: {str(e)}")
                log_print("[ERROR] 图像预处理失败")
                return None

    def validate_image_source(self, image_source, is_url):
        if is_url and not isinstance(image_source, str):
            raise ValueError("URL必须是字符串类型")
        if not is_url and not isinstance(image_source, bytes):
            raise ValueError("非URL图像源必须是字节类型")

    def get_image_filename(self, image_source, is_url):
        if is_url:
            return image_source.split('/')[-1].split('?')[0]
        else:
            return "binary_image_data"

    def cleanup(self):
        try:
            with self._reader_lock:
                if self.reader is not None:
                    del self.reader
                    self.reader = None
            gc.collect()

        except Exception as e:
            log_print(f"[WARNING] 清理资源时出错: {str(e)}")