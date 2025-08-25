import json
import os
import shutil
import threading
import time
import json
from json import JSONDecodeError
from datetime import datetime, timedelta
from queue import Queue, Empty

import requests
from PyQt6 import QtCore

from clients import AliClient, BaiduClient, LocalClient
from utils import load_config, log_print, log, MODE_LOCAL


class ProcessingThread(QtCore.QThread):
    file_processed = QtCore.pyqtSignal(dict)
    processing_finished = QtCore.pyqtSignal(list)
    processing_stopped = QtCore.pyqtSignal()
    stats_updated = QtCore.pyqtSignal(int, int, int)
    rate_limit_warning = QtCore.pyqtSignal(str)
    progress_updated = QtCore.pyqtSignal(int, str)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, client, image_files, dest_dir, is_move_mode, parent=None):
        super().__init__(parent)
        self.client_config = client.config if hasattr(client, 'config') else {}
        self.image_files = image_files
        self.dest_dir = dest_dir
        self.is_move_mode = is_move_mode
        self.is_running = True
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.counter_lock = threading.Lock()  # 计数器线程锁
        self.file_lock = threading.Lock()  # 文件操作线程锁
        self.lock = threading.Lock()
        # 初始化配置相关属性
        cpu_count = os.cpu_count() or 4
        self.worker_count = min(max(1, cpu_count // 2), 8)
        self.max_requests_per_minute = 60
        self.backoff_factor = 2.0
        self.request_interval = 0.5
        self.max_backoff_time = 30
        self.request_timeout = 60
        self.Config = {}
        # 加载配置
        self._load_config()
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.total_files = len(image_files)
        self.file_queue = Queue()
        self.results = []
        self.workers = []
        self.signal_queue = Queue()
        self.signal_processor_running = True
        client_type = getattr(client, 'client_type', '未知')

        self.client_type = client_type

        # 创建共享客户端实例
        try:
            config = load_config()
            client_type = config.get('ocr_client', 'local')
            if client_type == 'ali':
                self.shared_client = AliClient()
            elif client_type == 'baidu':
                self.shared_client = BaiduClient()
            else:
                max_retries = self.client_config.get('max_retries', 3)
                self.shared_client = LocalClient(max_retries=max_retries, gpu=False)

        except (IOError, OSError) as e:
            error_msg = f"共享客户端初始化失败: {str(e)}"
            log_print(error_msg)
            self.error_occurred.emit(error_msg)
            raise

    def _load_config(self):
        """
        加载配置参数，设置线程池和请求限制等参数。可被外部调用以更新配置。
        """
        try:
            # 重新加载配置
            new_config = load_config()

            # 从配置中获取新参数值
            cpu_count = os.cpu_count() or 4
            default_worker_count = min(max(1, cpu_count // 8), 1)
            new_worker_count = new_config.get("CONCURRENCY", default_worker_count)
            new_max_requests_per_minute = new_config.get("MAX_REQUESTS_PER_MINUTE", 60)
            new_backoff_factor = new_config.get("BACKOFF_FACTOR", 2.0)
            new_request_interval = new_config.get("REQUEST_INTERVAL", 0.5)
            new_max_backoff_time = new_config.get("MAX_BACKOFF_TIME", 30)
            new_request_timeout = new_config.get("REQUEST_TIMEOUT", 60)

            # 检查配置是否有变化
            config_changed = False
            if new_worker_count != self.worker_count:
                self.worker_count = new_worker_count
                config_changed = True
            if new_max_requests_per_minute != self.max_requests_per_minute:
                self.max_requests_per_minute = new_max_requests_per_minute
                config_changed = True
            if new_backoff_factor != self.backoff_factor:
                self.backoff_factor = new_backoff_factor
                config_changed = True
            if new_request_interval != self.request_interval:
                self.request_interval = new_request_interval
                config_changed = True
            if new_max_backoff_time != self.max_backoff_time:
                self.max_backoff_time = new_max_backoff_time
                config_changed = True
            if new_request_timeout != self.request_timeout:
                self.request_timeout = new_request_timeout
                config_changed = True

            # 更新配置对象
            self.Config = new_config

            if config_changed:
                log("INFO", f"配置已更新: 工作线程数={self.worker_count}, 最大请求数/分钟={self.max_requests_per_minute}")
            else:
                pass
        except (FileNotFoundError, PermissionError, OSError) as e:
            self.max_requests_per_minute = 60
            cpu_count = os.cpu_count() or 4
            self.worker_count = min(max(1, cpu_count // 2), 8)
            self.backoff_factor = 2.0
            self.request_interval = 0.5
            self.max_backoff_time = 30
            self.request_timeout = 60
            error_msg = f"配置加载失败: {str(e)}"
            log("ERROR", error_msg)
            self.error_occurred.emit(error_msg)

    def run(self):
        try:
            if not self.image_files:
                log_print("没有待处理的图像文件")
                self.processing_finished.emit([])
                return

            self.stats_updated.emit(0, 0, 0)
            self.progress_updated.emit(0, "开始处理...")

            for file_path in self.image_files:
                self.file_queue.put(file_path)

            for i in range(self.worker_count):
                worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
                self.workers.append(worker)
                worker.start()

            signal_thread = threading.Thread(target=self._signal_processor, daemon=True)
            signal_thread.start()

            for worker in self.workers:
                worker.join()

            self.signal_queue.join()
            self.signal_processor_running = False
            signal_thread.join()

            self.processing_finished.emit(self.results)
            self.progress_updated.emit(100, "处理完成")
            log_print(
                f"处理完成，共 {self.processed_count} 个文件，成功 {self.success_count} 个，失败 {self.failed_count} 个")

        except (ValueError, RuntimeError) as e:
            error_msg = f"处理过程中发生致命错误: {str(e)}"
            log_print(error_msg)
            self.error_occurred.emit(error_msg)
            self.processing_finished.emit([])

    def _worker(self, worker_id):

        # 使用主线程创建的共享客户端实例
        client = self.shared_client


        while self.is_running or not self.file_queue.empty():
            try:
                file_path = self.file_queue.get(timeout=0.5)
            except Empty:
                break

            result = None
            try:
                if not self.is_running:
                    result = {
                        'filename': os.path.basename(file_path),
                        'success': False,
                        'error': '处理已取消'
                    }
                else:
                    result = self.rate_limited_process(file_path, client)
            except (requests.exceptions.RequestException, json.JSONDecodeError, RuntimeError) as e:
                error_msg = f"工作线程 {worker_id + 1} 处理文件时出错: {str(e)}"
                log_print(error_msg)
                result = {
                    'filename': os.path.basename(file_path),
                    'success': False,
                    'error': f'处理过程中发生异常: {str(e)}'
                }
                self.signal_queue.put(('error_occurred', error_msg))
            finally:
                if result is not None:
                    with self.lock:
                        self.processed_count += 1
                        self.results.append(result)

                        recognition = result.get('recognition') or result.get('result')

                        if result['success']:
                            with self.counter_lock:
                                self.success_count += 1
                            result['category_dir'] = self.copy_to_classified_folder(
                                file_path, recognition, self.dest_dir, self.is_move_mode)
                        else:
                            with self.counter_lock:
                                self.failed_count += 1
                            self.copy_to_classified_folder(file_path, None, self.dest_dir, self.is_move_mode)

                        self.signal_queue.put(('file_processed', result))
                        self.signal_queue.put(
                            ('stats_updated', self.processed_count, self.success_count, self.failed_count))

                        progress = int((self.processed_count / self.total_files) * 100)
                        self.signal_queue.put(
                            ('progress_updated', progress, f"已处理 {self.processed_count}/{self.total_files}"))

                self.file_queue.task_done()
        log_print(f"工作线程 {worker_id + 1} 已结束")

    def _signal_processor(self):
        while self.signal_processor_running or not self.signal_queue.empty():
            try:
                signal = self.signal_queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                signal_name = signal[0]
                args = signal[1:]

                if signal_name == 'file_processed':
                    self.file_processed.emit(args[0])
                elif signal_name == 'stats_updated':
                    self.stats_updated.emit(args[0], args[1], args[2])
                elif signal_name == 'progress_updated':
                    self.progress_updated.emit(args[0], args[1])
                elif signal_name == 'error_occurred':
                    self.error_occurred.emit(args[0])
            except (TypeError, AttributeError, ValueError) as e:
                log_print(f"处理信号时出错: {str(e)}")
            finally:
                self.signal_queue.task_done()

    def rate_limited_process(self, file_path, client):
        """
        带速率限制的图像处理方法

        参数:
            file_path: 图像文件路径

        返回:
            dict: 处理结果
        """
        if not self.is_running:
            return {'filename': os.path.basename(file_path), 'success': False, 'error': '处理已取消'}

        try:
            self._check_rate_limit()

            if not self.is_running:
                raise RuntimeError("处理已取消")

            return self.process_image_file(file_path, client)
        except (RuntimeError, ValueError, IOError) as e:
            error_msg = f"速率限制处理失败: {str(e)}"
            log("ERROR", error_msg)
            return {'filename': os.path.basename(file_path), 'success': False, 'error': error_msg}

    def _check_rate_limit(self):
        """
        检查请求速率限制，确保不超过每分钟最大请求数
        """
        with self.lock:
            now = datetime.now()
            # 每分钟重置计数器
            if now - self.window_start > timedelta(minutes=1):
                self.requests_counter = 0
                self.window_start = now

            # 如果超过限制，等待直到可以继续
            if self.requests_counter >= self.max_requests_per_minute:
                wait_time = (self.window_start + timedelta(minutes=1) - now).total_seconds() + 0.1
                warning_msg = f"请求频率过高，已达到每分钟{self.max_requests_per_minute}次的限制，需等待{wait_time:.2f}秒"
                log("WARNING", warning_msg)
                self.rate_limit_warning.emit(warning_msg)
                log_print(warning_msg)

                # 等待期间定期检查是否需要停止
                start_wait = time.time()
                while time.time() - start_wait < wait_time and self.is_running:
                    time.sleep(0.5)

                if not self.is_running:
                    raise RuntimeError("处理已取消")

                # 重置计数器
                self.requests_counter = 0
                self.window_start = now

            # 增加计数器
            self.requests_counter += 1

            # 确保请求间隔
            if self.request_interval > 0:
                time.sleep(self.request_interval)

    def stop(self):
        """
        停止处理线程
        """
        log("INFO", "正在停止处理线程")
        log_print("正在停止处理线程")

        with self.lock:
            if not self.is_running:
                log("INFO", "处理线程已处于停止状态")
                return
            self.is_running = False

        # 清空任务队列
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except Empty:
                break
            self.file_queue.task_done()

        # 等待工作线程结束，最多等待10秒
        start_time = time.time()
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
                if worker.is_alive():
                    log("WARNING", "工作线程未正常结束，已超时")
                    log_print("工作线程未正常结束，已超时")

        # 停止信号处理器
        self.signal_processor_running = False

        # 发出停止信号
        self.processing_stopped.emit()
        log("INFO", "处理线程已停止")
        log_print("处理线程已停止")

    def process_image_file(self, local_file_path, client):
        """
        处理单个图像文件

        参数:
            local_file_path: 本地图像文件路径

        返回:
            dict: 包含处理结果的字典
        """
        filename = os.path.basename(local_file_path)
        log("INFO", f"开始处理图像文件: {filename}")
        log_print(f"开始处理图像文件: {filename}")

        try:
            # 检查文件是否存在
            if not os.path.exists(local_file_path):
                error_msg = f"文件不存在: {local_file_path}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            # 所有模式均使用本地文件直接识别，不进行OSS上传
            log_print(f"使用本地文件处理: {filename}")

            # 读取图像文件内容作为bytes
            with open(local_file_path, 'rb') as f:
                image_source = f.read()

            # 调用OCR识别
            try:
                result = client.recognize(image_source, is_url=False)
            except Exception as e:
                error_msg = f"OCR识别失败: {str(e)}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            # 验证识别结果
            if result is None:
                log("WARNING", f"未识别到有效结果: {filename}")
                return {'filename': filename, 'success': False, 'error': '未识别到有效结果'}
            if not isinstance(result, str):
                log("ERROR", f"OCR返回非字符串结果: {type(result).__name__}")
                return {'filename': filename, 'success': False, 'error': 'OCR识别结果格式错误'}

            max_attempts = 1 if self.Config and self.Config.get("MODE_INDEX") == MODE_LOCAL else (
                self.Config.get("RETRY_TIMES") if self.Config else 3)
            ocr_result = None  # 初始化ocr_result变量
            for attempt in range(max_attempts):
                if attempt > 0:
                    backoff_time = min(self.backoff_factor ** attempt, self.max_backoff_time)
                    log_print(f"第 {attempt + 1} 次尝试，等待 {backoff_time:.2f} 秒后重试")
                    time.sleep(backoff_time)

                try:
                    # 对于本地文件，is_url始终为False
                    is_url = False
                    # 再次检查image_source是否为bytes类型
                    if not isinstance(image_source, bytes):
                        error_msg = f"image_source必须是bytes类型，但得到的是{type(image_source)}类型"
                        log("ERROR", error_msg)
                        log_print(f"[ERROR] {error_msg}")
                        return {'filename': filename, 'success': False, 'error': error_msg}
                    ocr_result = client.recognize(image_source, is_url=is_url)
                    log_print(f"OCR识别结果: {ocr_result}")

                    time.sleep(self.request_interval)

                    if ocr_result:
                        result_value = ocr_result
                        log("INFO", f"OCR识别成功: {filename}, 结果: {result_value}")
                        log_print(f"OCR识别成功: {filename}, 结果: {result_value}")

                        result = {
                            'filename': filename,
                            'success': True,
                            'result': result_value,
                            'recognition': result_value
                        }
                        return result
                    else:
                        error_msg = '未识别到有效结果'
                        log("WARNING",
                            f"OCR识别失败 (尝试 {attempt + 1}/{max_attempts}): {filename}, 错误: {error_msg}")
                        log_print(f"OCR识别失败 (尝试 {attempt + 1}/{max_attempts}): {filename}, 错误: {error_msg}")
                        if attempt == max_attempts - 1:
                            log("ERROR", f"文件 {filename} 识别失败: {error_msg}")
                            log_print(f"文件 {filename} 识别失败: {error_msg}")
                            return {'filename': filename, 'success': False, 'error': error_msg}

                except requests.exceptions.RequestException as e:
                    error_msg = f'网络请求异常: {str(e)}'
                    log("ERROR", f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, {error_msg}")
                    log_print(f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, 错误: {error_msg}")
                    if attempt == max_attempts - 1:
                        return {'filename': filename, 'success': False, 'error': error_msg}
                except json.JSONDecodeError as e:
                    error_msg = f'JSON解析异常: {str(e)}'
                    log("ERROR", f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, {error_msg}")
                    log_print(f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, 错误: {error_msg}")
                    if attempt == max_attempts - 1:
                        return {'filename': filename, 'success': False, 'error': error_msg}
                except (IOError, OSError) as e:
                    error_msg = f'识别异常: {str(e)}'
                    log("ERROR", f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, {error_msg}")
                    log_print(f"OCR识别异常 (尝试 {attempt + 1}/{max_attempts}): {filename}, 错误: {error_msg}")
                    if attempt == max_attempts - 1:
                        return {'filename': filename, 'success': False, 'error': error_msg}
                finally:
                    if hasattr(client, 'cleanup') and callable(client.cleanup):
                        try:
                            client.cleanup()
                            import gc
                            gc.collect()
                        except (IOError, OSError) as e:
                            log_print(f"客户端资源清理失败: {str(e)}")

            return {'filename': filename, 'success': False, 'error': '达到最大重试次数'}
        except (RuntimeError, TypeError, OSError) as e:
            error_msg = f'处理图像文件时发生致命错误: {str(e)}'
            log("ERROR", error_msg)
            log_print(error_msg)
            return {'filename': filename, 'success': False, 'error': error_msg}

    def copy_to_classified_folder(self, local_file_path, recognition, output_dir, is_move=False):
        """
        将处理后的文件复制或移动到分类文件夹

        参数:
            local_file_path: 源文件路径
            recognition: 识别结果（用于创建分类文件夹）
            output_dir: 目标文件夹
            is_move: 是否为移动模式

        返回:
            str: 分类文件夹名称或None（出错时）
        """
        filename = os.path.basename(local_file_path)

        if recognition:
            category = recognition.replace('\n', ' ').replace('【', '[').replace('】', ']')
            invalid_chars = '\\/:*?"<>|'
            for char in invalid_chars:
                category = category.replace(char, '-')
            max_length = 100
            if len(category) > max_length:
                category = category[:max_length] + '...'
            if '未识别到有效内容' in category:
                category = '未识别到有效内容'
        else:
            # 只有识别失败时才使用"识别失败"分类
            category = "识别失败"

        category_dir = os.path.join(output_dir, category)
        # 只有实际需要时才创建目录
        if not os.path.exists(category_dir):
            try:
                os.makedirs(category_dir, exist_ok=True)
            except OSError as e:
                error_msg = f"创建目录失败: {str(e)}"
                log("ERROR", error_msg)
                log_print(error_msg)
                self.signal_queue.put(('error_occurred', error_msg))
                return None

        dest_path = os.path.join(category_dir, filename)
        counter = 1

        while os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            dest_path = os.path.join(category_dir, f"{name}_{counter}{ext}")
            counter += 1

        try:
            if is_move:
                try:
                    with self.file_lock:
                        shutil.move(local_file_path, dest_path)
                        log("INFO", f"已移动文件: {filename} -> {category}")
                        log_print(f"已移动文件: {filename} -> {category}")
                except PermissionError:
                    error_msg = f"移动文件时权限不足: {filename}"
                    log("ERROR", error_msg)
                    log_print(error_msg)
                    self.signal_queue.put(('error_occurred', error_msg))
                    return None
                except Exception as e:
                    error_msg = f"移动文件时出错: {str(e)}"
                    log("ERROR", error_msg)
                    log_print(error_msg)
                    self.signal_queue.put(('error_occurred', error_msg))
                    return None
            else:
                try:
                    shutil.copy2(local_file_path, dest_path)
                    log("INFO", f"已复制文件: {filename} -> {category}")
                    log_print(f"已复制文件: {filename} -> {category}")
                except PermissionError:
                    error_msg = f"复制文件时权限不足: {filename}"
                    log("ERROR", error_msg)
                    log_print(error_msg)
                    self.signal_queue.put(('error_occurred', error_msg))
                    return None
                except Exception as e:
                    error_msg = f"复制文件时出错: {str(e)}"
                    log("ERROR", error_msg)
                    log_print(error_msg)
                    self.signal_queue.put(('error_occurred', error_msg))
                    return None

            return category
        except Exception as e:
            error_msg = f"处理文件时发生未知错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(error_msg)
            self.signal_queue.put(('error_occurred', error_msg))
            return None