"""飞桨本地OCR客户端实现，提供离线图像识别功能"""
import gc
import re
import threading
import time
from io import BytesIO
from typing import Optional, Union

from paddleocr import PaddleOCR
import numpy as np
import requests
from PIL import Image, ImageEnhance, ImageFilter

from utils import load_config, log, log_print
from .base_client import BaseClient


class PaddleClient(BaseClient):
    """本地OCR客户端，继承BaseClient实现离线图像识别"""

    client_type: str = "paddle"

    def __init__(self, max_retries=1):
        self.config = load_config()
        self.pattern = re.compile(self.config.get("RE", r'.*'))
        self.client_type = 'paddle'
        self.ocr = None
        self.max_retries = max_retries
        self._ocr_lock = threading.Lock()
        self._is_initializing = False
        self._is_cleaning = False  # 初始化清理状态标志
        self.recognition_attempts = self.config.get("RECOGNITION_ATTEMPTS", 2)
        self.max_threads = 1
        self._initialize_ocr()

    def _initialize_ocr(self):
        """初始化PaddleOCR引擎，处理模型加载与重试逻辑"""

        if self._is_initializing:
            log_print("[PaddleOCR] 模型初始化中，其他线程等待中...")
            while self._is_initializing:
                time.sleep(0.1)
            if self.ocr is None:
                log("WARNING", "PaddleOCR初始化完成但ocr引擎仍为None")
            return

        retry_count = 0
        self.ocr = None
        while retry_count < self.max_retries:
            try:
                self._is_initializing = True

                with self._ocr_lock:
                    self.ocr = PaddleOCR(
                                use_angle_cls=True,
                                lang='en'
                            )
                self._is_initializing = False
                return
            except (ImportError, RuntimeError, OSError) as e:
                log("ERROR", f"PaddleOCR模型加载失败: {str(e)}")
                log_print(f"[PaddleOCR] 模型加载异常: {str(e)} (重试次数: {retry_count}/{self.max_retries})")
                retry_count += 1
                self.ocr = None
                if retry_count < self.max_retries:
                    wait_time = min(2 ** retry_count, 10)
                    time.sleep(wait_time)
                else:
                    self._is_initializing = False
                    log("ERROR", f"PaddleOCR模型加载失败: 已尝试{self.max_retries}次仍无法加载")
                    raise RuntimeError(f"无法加载PaddleOCR模型，错误: {str(e)}") from e

    def get_img(self, img_file):
        """获取并验证图像文件

        处理图像文件输入，确保其有效性并返回可用的图像文件对象。

        参数:
            img_file: 图像文件对象或路径

        返回:
            有效的图像文件对象
        """
        return img_file

    def optimized_preprocess_from_image(self, image: Image.Image, filename: str,
                                        max_size=800, enhance_attempt=0):
        """
        优化图像预处理

        对输入图像进行尺寸调整、格式转换和增强处理，
        提高OCR识别准确率。

        参数:
            image: PIL图像对象
            filename: 图像文件名用于日志记录
            max_size: 最大尺寸限制
            enhance_attempt: 增强尝试次数，控制处理强度

        返回:
            numpy数组格式的预处理图像或None
        """
        try:
            # 获取图像尺寸但不存储未使用的变量
            if max(image.size) > max_size:
                scale = max_size / max(image.size)
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            if image.mode not in ['L', 'RGB', 'RGBA']:
                log("WARNING", "不支持的图像格式，已自动转换")
                log_print(f"[本地预处理] 图像模式转换: {image.mode}→RGB (文件: {filename})")
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

            # 确保图像是3D数组（H, W, C），PaddleOCR需要RGB格式
            if len(np_image.shape) == 2:
                np_image = np.stack((np_image,) * 3, axis=-1)

            return np_image
        except (IOError, ValueError, TypeError) as e:
            error_msg = f"图像预处理错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            log("ERROR", f"图像预处理失败: {filename}")
            return None

    def extract_matches(self, texts):
        """从识别文本中提取匹配的模式

        参数:
            texts: OCR识别返回的文本列表

        返回:
            匹配的模式字符串(如A1, B2等)或None
        """
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

        # 参数校验
        try:
            self.validate_image_source(image_source, is_url)
        except ValueError as e:
            log("ERROR", f"参数校验失败: {str(e)}")
            return None

        try:
            if is_url:
                try:
                    response = requests.get(image_source, timeout=10)
                    response.raise_for_status()
                    img_data = response.content
                    original_image = Image.open(BytesIO(img_data))
                except requests.exceptions.RequestException as e:
                    log("ERROR", f"图像下载失败: {str(e)}")
                    log_print(f"[本地OCR] URL下载异常: {str(e)} (URL: {image_source[:50]}...)")
                    return None
            else:
                try:
                    original_image = Image.open(BytesIO(image_source))
                except (IOError, OSError) as e:
                    log("ERROR", f"无法打开图像文件: {str(e)}")
                    log_print(f"[ERROR] 文件不是有效的图像格式或已损坏: {filename}")
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

                        # 双重检查锁定模式
                        if self.ocr is None:
                            log_print("[PaddleOCR] OCR引擎未就绪，触发重新初始化...")
                            self._initialize_ocr()

                            if self.ocr is None:
                                log_print("[ERROR] PaddleOCR引擎初始化失败，无法继续识别")
                                continue

                        with self._ocr_lock:
                            if self.ocr is None:
                                log_print("[ERROR] PaddleOCR引擎在锁定期间变为None，无法继续识别")
                                continue

                            try:
                                # 使用PaddleOCR进行识别（尝试两种API调用方式）
                                try:
                                    result = self.ocr.ocr(processed_image)
                                except Exception:
                                    result = self.ocr.predict(processed_image)
                                
                                # 提取识别文本 - 处理多种格式的结果
                                recognized_texts = []
                                
                                if not result:
                                    continue
                                    
                                # 处理不同格式的结果
                                if isinstance(result, list) and len(result) > 0:
                                    # 新版本格式：列表包含OCRResult对象
                                    first_result = result[0]
                                    
                                    if hasattr(first_result, 'rec_texts') and hasattr(first_result, 'rec_scores'):
                                        # OCRResult对象格式
                                        rec_texts = first_result.rec_texts
                                        rec_scores = first_result.rec_scores
                                    elif isinstance(first_result, dict):
                                        # 字典格式
                                        rec_texts = first_result.get('rec_texts', [])
                                        rec_scores = first_result.get('rec_scores', [])
                                    else:
                                        # 传统列表格式
                                        rec_texts = []
                                        rec_scores = []
                                        for word_info in first_result:
                                            if len(word_info) >= 2 and isinstance(word_info[1], (list, tuple)) and len(word_info[1]) >= 2:
                                                rec_texts.append(str(word_info[1][0]))
                                                rec_scores.append(float(word_info[1][1]))
                                
                                # 确保文本和置信度长度一致
                                if len(rec_texts) != len(rec_scores):
                                    # 取最小长度继续处理
                                    min_len = min(len(rec_texts), len(rec_scores))
                                    rec_texts = rec_texts[:min_len]
                                    rec_scores = rec_scores[:min_len]
                                
                                # 过滤低置信度结果
                                for text, score in zip(rec_texts, rec_scores):
                                    if score >= 0.3 and text and str(text).strip():
                                        recognized_texts.append(str(text).strip())
                            except Exception as e:
                                error_type = type(e).__name__
                                error_msg = f"PaddleOCR识别异常 ({error_type}): {str(e)}"
                                log("ERROR", error_msg)
                                log_print(f"[ERROR] {error_msg}")
                                if attempt < self.max_retries - 1:
                                    wait_time = min(2 ** attempt, 10)
                                    log("INFO", f"将在{wait_time}秒后重试...")
                                    time.sleep(wait_time)
                                    continue
                                return None

                        matched_result = self.extract_matches(recognized_texts)

                        if matched_result:
                            return matched_result

                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = f"PaddleOCR识别异常 (尝试 {attempt + 1}, {error_type}): {str(e)}"
                    log("ERROR", error_msg)
                    log_print(f"[ERROR] {error_msg}")
                    continue
                finally:
                    # 确保所有图像资源都被释放
                    for var in ['processed_image', 'enhanced_img', 'gray_img', 'thresh_img']:
                        if var in locals():
                            try:
                                del locals()[var]
                            except (RuntimeError, ValueError, TypeError) as e:
                                log("WARNING", f"释放资源 {var} 失败: {str(e)}")
                    gc.collect()
                    # 短暂延迟减轻CPU压力
                    time.sleep(0.01)
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
                    del original_image
                if 'processed_image' in locals() and processed_image is not None:
                    del processed_image
                gc.collect()
            except (TypeError, AttributeError, OSError, TypeError, AttributeError, OSError) as e:
                log_print(f"[WARNING] 图像资源释放失败: {str(e)}")

    def validate_image_source(self, image_source, is_url):
        """验证图像源格式

        重写基类方法，验证图像源是否符合要求格式。

        参数:
            image_source: 图像源数据
            is_url: 是否为URL格式

        抛出:
            ValueError: 当图像源格式不符合要求时
        """
        if is_url and not isinstance(image_source, str):
            raise ValueError("URL必须是字符串类型")
        if not is_url and not isinstance(image_source, bytes):
            raise ValueError("非URL图像源必须是字节类型")
