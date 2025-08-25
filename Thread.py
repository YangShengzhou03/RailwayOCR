import json
import os
import shutil
import threading
import time
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
        self.counter_lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.lock = threading.Lock()
        self.results_lock = threading.Lock()
        cpu_count = os.cpu_count() or 4
        # 优化：根据CPU核心数动态调整工作线程数
        if cpu_count <= 4:
            self.worker_count = 1
        else:
            self.worker_count = min(max(2, cpu_count // 4), 4)
        # 添加进度更新时间阈值，避免频繁更新UI
        self.last_progress_update_time = 0
        self.progress_update_interval = 0.5  # 秒
        self.max_requests_per_minute = 60
        self.backoff_factor = 2.0
        self.request_interval = 0.5
        self.max_backoff_time = 30
        self.request_timeout = 60
        self.Config = {}
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
        try:
            new_config = load_config()

            cpu_count = os.cpu_count() or 4
            default_worker_count = min(max(1, cpu_count // 8), 1)
            new_worker_count = new_config.get("CONCURRENCY", default_worker_count)
            new_max_requests_per_minute = new_config.get("MAX_REQUESTS_PER_MINUTE", 60)
            new_backoff_factor = new_config.get("BACKOFF_FACTOR", 2.0)
            new_request_interval = new_config.get("REQUEST_INTERVAL", 0.5)
            new_max_backoff_time = new_config.get("MAX_BACKOFF_TIME", 30)
            new_request_timeout = new_config.get("REQUEST_TIMEOUT", 60)

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

            self.Config = new_config

            if config_changed:
                log("INFO",
                    f"配置已更新: 工作线程数={self.worker_count}, 最大请求数/分钟={self.max_requests_per_minute}")
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
            except (requests.exceptions.RequestException, json.JSONDecodeError, RuntimeError, OSError) as e:
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
                        with self.results_lock:
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

                        # 优化：限制进度更新频率，避免UI卡顿
                        current_time = time.time()
                        if current_time - self.last_progress_update_time >= self.progress_update_interval:
                            progress = int((self.processed_count / self.total_files) * 100)
                            self.signal_queue.put(
                                ('progress_updated', progress, f"已处理 {self.processed_count}/{self.total_files}")
                            )
                            self.last_progress_update_time = current_time

                self.file_queue.task_done()
        log_print(f"工作线程 {worker_id + 1} 已结束")

    def _signal_processor(self):
        while self.signal_processor_running or not self.signal_queue.empty():
            try:
                signal = self.signal_queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                if not isinstance(signal, tuple) or len(signal) < 1:
                    log_print("收到无效信号格式")
                    continue

                signal_name = signal[0]
                args = signal[1:]

                if signal_name == 'file_processed':
                    if len(args) >= 1 and isinstance(args[0], dict):
                        self.file_processed.emit(args[0])
                    else:
                        log_print("file_processed信号参数错误")
                elif signal_name == 'stats_updated':
                    if len(args) >= 3 and all(isinstance(arg, int) for arg in args[:3]):
                        self.stats_updated.emit(args[0], args[1], args[2])
                    else:
                        log_print("stats_updated信号参数错误")
                elif signal_name == 'progress_updated':
                    if len(args) >= 2 and isinstance(args[0], int) and isinstance(args[1], str):
                        self.progress_updated.emit(args[0], args[1])
                    else:
                        log_print("progress_updated信号参数错误")
                elif signal_name == 'error_occurred':
                    if len(args) >= 1 and isinstance(args[0], str):
                        self.error_occurred.emit(args[0])
                    else:
                        log_print("error_occurred信号参数错误")
                else:
                    log_print(f"未知信号类型: {signal_name}")
            except (TypeError, AttributeError, ValueError) as e:
                log_print(f"处理信号时出错: {str(e)}")
            finally:
                self.signal_queue.task_done()

    def rate_limited_process(self, file_path, client):
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
        with self.lock:
            now = datetime.now()
            if now - self.window_start > timedelta(minutes=1):
                self.requests_counter = 0
                self.window_start = now

            if self.requests_counter >= self.max_requests_per_minute:
                wait_time = (self.window_start + timedelta(minutes=1) - now).total_seconds() + 0.1
                warning_msg = f"请求频率过高，已达到每分钟{self.max_requests_per_minute}次的限制，需等待{wait_time:.2f}秒"
                log("WARNING", warning_msg)
                self.rate_limit_warning.emit(warning_msg)
                log_print(warning_msg)

                start_wait = time.time()
                remaining_wait = wait_time
                # 优化：动态调整sleep时长，避免过长等待
                while remaining_wait > 0 and self.is_running:
                    # 每次最多等待0.5秒，以便及时响应停止信号
                    sleep_duration = min(0.5, remaining_wait)
                    time.sleep(sleep_duration)
                    remaining_wait -= sleep_duration

                if not self.is_running:
                    raise RuntimeError("处理已取消")

                self.requests_counter = 0
                self.window_start = now

            self.requests_counter += 1

            # 优化：精准控制请求间隔
            if self.request_interval > 0:
                time.sleep(self.request_interval)

    def stop(self):
        log("INFO", "正在停止处理线程")
        log_print("正在停止处理线程")

        with self.lock:
            if not self.is_running:
                log("INFO", "处理线程已处于停止状态")
                return
            self.is_running = False

        # 优化：快速清空任务队列，避免线程等待
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
                self.file_queue.task_done()
            except Empty:
                break

        # 优化：不等待工作线程，让它们自然结束
        # 因为我们已经设置了is_running = False，工作线程会在下次检查时退出

        # 优化：立即停止信号处理器
        self.signal_processor_running = False
        # 向信号队列中添加一个空信号，以唤醒阻塞的signal_processor
        self.signal_queue.put(('stop_signal',))

        # 立即发出停止信号，不等待线程完全结束
        self.processing_stopped.emit()
        log("INFO", "处理线程已请求停止")
        log_print("处理线程已请求停止")

        # 优化：清理资源
        if hasattr(self.shared_client, 'cleanup') and callable(self.shared_client.cleanup):
            try:
                self.shared_client.cleanup()
                import gc
                gc.collect()
            except Exception as e:
                log_print(f"客户端资源清理失败: {str(e)}")

    def process_image_file(self, local_file_path, client):
        filename = os.path.basename(local_file_path)
        log("INFO", f"开始处理图像文件: {filename}")
        log_print(f"开始处理图像文件: {filename}")

        try:
            if not os.path.exists(local_file_path):
                error_msg = f"文件不存在: {local_file_path}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            log_print(f"使用本地文件处理: {filename}")

            with open(local_file_path, 'rb') as f:
                image_source = f.read()

            try:
                result = client.recognize(image_source, is_url=False)
            except Exception as e:
                error_msg = f"OCR识别失败: {str(e)}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            if result is None:
                log("WARNING", f"未识别到有效结果: {filename}")
                return {'filename': filename, 'success': False, 'error': '未识别到有效结果'}
            if not isinstance(result, str):
                log("ERROR", f"OCR返回非字符串结果: {type(result).__name__}")
                return {'filename': filename, 'success': False, 'error': 'OCR识别结果格式错误'}

            max_attempts = 1 if self.Config and self.Config.get("MODE_INDEX") == MODE_LOCAL else (
                self.Config.get("RETRY_TIMES") if self.Config else 3)
            ocr_result = None
            for attempt in range(max_attempts):
                if attempt > 0:
                    backoff_time = min(self.backoff_factor ** attempt, self.max_backoff_time)
                    log_print(f"第 {attempt + 1} 次尝试，等待 {backoff_time:.2f} 秒后重试")
                    time.sleep(backoff_time)

                try:
                    is_url = False
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
            category = "识别失败"

        category_dir = os.path.join(output_dir, category)
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

        # 检查目标文件是否已存在且与源文件相同
        skip_copy = False
        if os.path.exists(dest_path):
            src_stat = os.stat(local_file_path)
            dest_stat = os.stat(dest_path)
            # 如果文件大小和修改时间相同，则认为文件内容相同
            if src_stat.st_size == dest_stat.st_size and abs(src_stat.st_mtime - dest_stat.st_mtime) < 1:
                skip_copy = True
                log("INFO", f"文件已存在且相同，跳过复制/移动: {filename}")
                log_print(f"文件已存在且相同，跳过复制/移动: {filename}")
        
        # 如果文件已存在但不相同，则生成新文件名
        while os.path.exists(dest_path) and not skip_copy:
            name, ext = os.path.splitext(filename)
            dest_path = os.path.join(category_dir, f"{name}_{counter}{ext}")
            counter += 1

        try:
            if skip_copy:
                    # 文件已存在且相同，直接返回分类目录
                    return category
                
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
                except shutil.Error as e:
                    error_msg = f"移动文件失败: {str(e)}"
                    log("ERROR", error_msg)
                    log_print(f"[ERROR] 文件已被占用或路径无效: {filename}")
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
                except shutil.Error as e:
                    error_msg = f"复制文件失败: {str(e)}"
                    log("ERROR", error_msg)
                    log_print(f"[ERROR] 文件已被占用或路径无效: {filename}")
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
