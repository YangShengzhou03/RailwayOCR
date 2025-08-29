"""
多线程图像处理模块

该模块提供ProcessingThread类，用于多线程处理OCR图像识别任务，
支持速率限制、重试机制和线程安全的文件操作。
"""

import gc
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from queue import Queue, Empty
        

import requests
from PyQt6 import QtCore

from utils import load_config, log_print, log, MODE_LOCAL


class ProcessingThread(QtCore.QThread):
    """
    多线程图像处理类
    
    负责管理OCR图像处理的多线程任务，包括速率限制、重试机制
    和线程安全的文件复制/移动操作。
    """
    file_processed = QtCore.pyqtSignal(dict)
    processing_finished = QtCore.pyqtSignal(list)
    processing_stopped = QtCore.pyqtSignal()
    stats_updated = QtCore.pyqtSignal(int, int, int)
    rate_limit_warning = QtCore.pyqtSignal(str)
    progress_updated = QtCore.pyqtSignal(int, str)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, client, image_files, dest_dir, is_move_mode, parent=None):
        """
        初始化处理线程
        
        Args:
            client: OCR客户端实例
            image_files: 要处理的图像文件列表
            dest_dir: 目标目录
            is_move_mode: 是否为移动模式
            parent: 父对象
        """
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
        
        # 直接使用传入的client参数，不再重新创建客户端实例
        self.shared_client = client
        self.client_type = getattr(client, 'client_type', 'unknown')
        
        if self.client_type == 'local' or self.client_type == 'paddle':
            self.worker_count = 1
        else:
            if cpu_count <= 4:
                self.worker_count = 1
            else:
                self.worker_count = min(max(2, cpu_count // 4), 4)
        
        self.last_progress_update_time = 0
        self.progress_update_interval = 0.5
        self.max_requests_per_minute = 60
        self.backoff_factor = 2.0
        self.request_interval = 0.5
        self.max_backoff_time = 30
        self.request_timeout = 60
        self.config = {}
        self._load_config()
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.total_files = len(image_files)
        self.file_queue = Queue()
        self.results = []
        self.workers = []
        self.signal_queue = Queue()
        self.signal_processor_running = True
        self.signal_processor_thread = None
        
        log_print(f"[线程初始化] 使用{self.client_type} OCR客户端")

    def _load_config(self):
        """加载并应用配置文件设置"""
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
            if self.client_type == 'local' or self.client_type == 'paddle':
                if self.worker_count != 1:
                    self.worker_count = 1
                    config_changed = True
            elif new_worker_count != self.worker_count:
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
            self.config = new_config
            if config_changed:
                log("WARNING",
                    f"配置: 工作线程数={self.worker_count}, 请求限制={self.max_requests_per_minute}次/分钟")
        except (FileNotFoundError, PermissionError, OSError) as e:
            self.max_requests_per_minute = 60
            cpu_count = os.cpu_count() or 4
            self.worker_count = min(max(1, cpu_count // 2), 8)
            self.backoff_factor = 2.0
            self.request_interval = 0.5
            self.max_backoff_time = 30
            self.request_timeout = 60
            error_msg = f"配置加载失败: {str(e)}"
            log("ERROR", f"配置文件加载失败: {str(e)}, 使用默认设置")
            self.error_occurred.emit(error_msg)

    def run(self):
        try:
            if not self.image_files:
                log("INFO", "没有需要处理的图像文件")
                self.processing_finished.emit([])
                return

            self.stats_updated.emit(0,0,0)
            self.progress_updated.emit(0, "开始处理...")

            for file_path in self.image_files:
                self.file_queue.put(file_path)

            for i in range(self.worker_count):
                worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
                self.workers.append(worker)
                worker.start()

            self.signal_processor_thread = threading.Thread(target=self._signal_processor, daemon=True)
            self.signal_processor_thread.start()

            for worker in self.workers:
                worker.join()

            self.signal_queue.join()
            self.signal_processor_running = False
            if self.signal_processor_thread.is_alive():
                self.signal_processor_thread.join(1.0)

            self.processing_finished.emit(self.results)
            self.progress_updated.emit(100, "处理完成")
            log("INFO",
                f"处理完成: 共{self.processed_count}个文件，成功{self.success_count}个，失败{self.failed_count}个")
            log_print(
                f"[处理统计] 总文件:{self.processed_count}, 成功:{self.success_count}, 失败:{self.failed_count}")

        except (ValueError, RuntimeError) as e:
            error_msg = f"处理过程中发生致命错误: {str(e)}"
            log_print(f"[工作线程] 处理文件出错: {str(e)}")
            self.error_occurred.emit(error_msg)
            self.processing_finished.emit([])
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        self.is_running = False

        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=1.0)

        self.signal_processor_running = False
        if self.signal_processor_thread and self.signal_processor_thread.is_alive():
            self.signal_processor_thread.join(timeout=1.0)

    def _worker(self, worker_id):
        """工作线程处理函数，从文件队列中获取并处理文件"""
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
                            self.copy_to_classified_folder(
                                file_path, recognition, self.dest_dir, self.is_move_mode)
                        else:
                            with self.counter_lock:
                                self.failed_count += 1
                            self.copy_to_classified_folder(file_path, '识别失败', self.dest_dir, self.is_move_mode)

                        self.signal_queue.put(('file_processed', result))
                        self.signal_queue.put(
                            ('stats_updated', self.processed_count, self.success_count, self.failed_count))

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
        """信号处理器线程函数，处理来自工作线程的信号"""
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
                elif signal_name == 'stop_signal':
                    break
                else:
                    log_print(f"未知信号类型: {signal_name}")
            except (TypeError, AttributeError, ValueError) as e:
                log_print(f"处理信号时出错: {str(e)}")
            finally:
                self.signal_queue.task_done()

    def rate_limited_process(self, file_path, client):
        """
        带速率限制的文件处理函数
        
        Args:
            file_path: 要处理的文件路径
            client: OCR客户端实例
            
        Returns:
            dict: 处理结果字典
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
        """检查并实施速率限制"""
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

                remaining_wait = wait_time
                while remaining_wait > 0 and self.is_running:
                    sleep_duration = min(0.5, remaining_wait)
                    time.sleep(sleep_duration)
                    remaining_wait -= sleep_duration

                if not self.is_running:
                    raise RuntimeError("处理已取消")

                self.requests_counter = 0
                self.window_start = now

            self.requests_counter += 1

            if self.request_interval > 0:
                time.sleep(self.request_interval)

    def stop(self):
        """停止线程，支持超时处理和资源清理"""
        with self.lock:
            if not self.is_running:
                return
            self.is_running = False

        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
                self.file_queue.task_done()
            except Empty:
                break

        self.signal_processor_running = False
        self.signal_queue.put(('stop_signal',))

        # 设置超时时间，避免线程无法正常终止
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5.0)  # 5秒超时
                if worker.is_alive():
                    log("WARNING", f"工作线程未能正常退出，正在强制清理")
                    # 这里不直接使用terminate()，因为可能造成资源泄漏
                    # 而是通过设置更强的停止信号
                    self._force_stop = True
                    
                    # 再次尝试优雅终止
                    worker.join(timeout=2.0)
                    
                    if worker.is_alive():
                        log("ERROR", f"工作线程最终无法终止，可能需要重启程序")

        if self.signal_processor_thread and self.signal_processor_thread.is_alive():
            self.signal_processor_thread.join(timeout=5.0)
            if self.signal_processor_thread.is_alive():
                log("WARNING", "信号处理器线程未能正常退出，正在强制清理")
                self._force_stop = True
                self.signal_processor_thread.join(timeout=2.0)
                if self.signal_processor_thread.is_alive():
                    log("ERROR", "信号处理器线程最终无法终止，可能需要重启程序")

        self.processing_stopped.emit()
        log("INFO", "处理线程已成功停止")
        log_print("处理线程已成功停止")

        if self.client_type != 'local' and hasattr(self.shared_client, 'cleanup') and callable(self.shared_client.cleanup):
            try:
                self.shared_client.cleanup()
                gc.collect()
            except (RuntimeError, OSError) as e:
                log_print(f"客户端资源清理失败: {str(e)}")

        # 清理资源
        self._cleanup_resources()
        self.workers = []
        self.signal_processor_thread = None
    
    def _cleanup_resources(self):
        """清理线程使用的资源"""
        try:
            # 清空信号队列
            while not self.signal_queue.empty():
                try:
                    self.signal_queue.get_nowait()
                except:
                    break
            
            # 清空工作队列
            while not self.work_queue.empty():
                try:
                    self.work_queue.get_nowait()
                except:
                    break
            
            # 清理文件锁相关资源
            if hasattr(self, 'file_lock') and self.file_lock:
                try:
                    self.file_lock.release()
                except:
                    pass
            
            # 清理OCR客户端资源
            if hasattr(self, 'clients') and self.clients:
                for client in self.clients:
                    try:
                        if hasattr(client, 'close') and callable(client.close):
                            client.close()
                    except Exception as e:
                        log("WARNING", f"客户端资源清理失败: {str(e)}")
            
            log("INFO", "线程资源清理完成")
            
        except Exception as e:
            log("ERROR", f"资源清理过程中发生错误: {str(e)}")

    def process_image_file(self, local_file_path, client):
        """
        处理单个图像文件，包含重试逻辑
        
        Args:
            local_file_path: 图像文件路径
            client: OCR客户端实例
            
        Returns:
            dict: 处理结果字典
        """
        filename = os.path.basename(local_file_path)
        try:
            if not os.path.exists(local_file_path):
                error_msg = f"文件不存在: {local_file_path}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            with open(local_file_path, 'rb') as f:
                image_source = f.read()

            try:
                result = client.recognize(image_source, is_url=False)
            except (RuntimeError, OSError, ConnectionError) as e:
                error_msg = f"OCR识别失败: {str(e)}"
                log("ERROR", error_msg)
                return {'filename': filename, 'success': False, 'error': error_msg}

            if result is None:
                log("WARNING", f"未识别到有效结果: {filename}")
                return {'filename': filename, 'success': False, 'error': '未识别到有效结果'}
            if not isinstance(result, str):
                log("ERROR", f"OCR返回非字符串结果: {type(result).__name__}")
                return {'filename': filename, 'success': False, 'error': 'OCR识别结果格式错误'}

            max_attempts = 1 if self.config and self.config.get("MODE_INDEX") == MODE_LOCAL else (
                self.config.get("RETRY_TIMES") if self.config else 3)
            for attempt in range(max_attempts):
                if attempt > 0:
                    backoff_time = min(self.backoff_factor ** attempt, self.max_backoff_time)
                    log_print(f"第 {attempt + 1} 次尝试，等待 {backoff_time:.2f} 秒后重试")
                    time.sleep(backoff_time)

                try:
                    is_url = False
                    ocr_result = client.recognize(image_source, is_url=is_url)

                    time.sleep(self.request_interval)

                    if ocr_result:
                        result_value = ocr_result
                        log("DEBUG", f"{self.client_type} OCR识别成功: {filename}, 结果: {result_value}")
                        log_print(f"OCR识别成功: {filename}, 结果: {result_value}")

                        result = {
                            'filename': filename,
                            'success': True,
                            'result': result_value,
                            'recognition': result_value
                        }
                        return result
                    
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
                    pass

            return {'filename': filename, 'success': False, 'error': '达到最大重试次数'}
        except (RuntimeError, TypeError, OSError) as e:
            error_msg = f'处理图像文件时发生致命错误: {str(e)}'
            log("ERROR", error_msg)
            log_print(error_msg)
            return {'filename': filename, 'success': False, 'error': error_msg}

    def copy_to_classified_folder(self, local_file_path, recognition, output_dir, is_move=False):
        """
        将文件复制或移动到分类文件夹，使用文件锁确保线程安全，包含重试机制和错误处理
        
        Args:
            local_file_path: 源文件路径
            recognition: 识别结果（用于创建目标子文件夹）
            output_dir: 输出目录
            is_move: 是否为移动操作（True=移动，False=复制）
        """

        # 使用文件锁确保同一文件的并发操作安全
        with self.file_lock:
            max_retries = 3
            retry_delay = 1.0  # 初始重试延迟1秒
            
            for attempt in range(max_retries):
                try:
                    if not os.path.exists(local_file_path):
                        log("ERROR", f"源文件不存在: {local_file_path}")
                        return
                    
                    # 清理识别结果，创建有效的文件夹名称
                    safe_recognition = self._sanitize_folder_name(recognition)
                    
                    # 创建目标子文件夹
                    target_subdir = os.path.join(output_dir, safe_recognition)
                    os.makedirs(target_subdir, exist_ok=True)
                    
                    # 构建目标文件路径
                    filename = os.path.basename(local_file_path)
                    target_path = os.path.join(target_subdir, filename)
                    
                    # 处理文件名冲突
                    counter = 1
                    base_name, ext = os.path.splitext(filename)
                    while os.path.exists(target_path):
                        target_path = os.path.join(target_subdir, f"{base_name}_{counter}{ext}")
                        counter += 1
                    
                    # 执行文件操作
                    if is_move:
                        # 移动操作：使用临时文件确保原子性
                        temp_path = target_path + '.tmp'
                        try:
                            shutil.copy2(local_file_path, temp_path)
                            
                            # 验证复制文件的完整性
                            if os.path.getsize(temp_path) == os.path.getsize(local_file_path):
                                os.rename(temp_path, target_path)
                                if os.path.exists(target_path):
                                    os.remove(local_file_path)
                                    log("INFO", f"文件移动成功: {filename} -> {safe_recognition}")
                                    return
                                else:
                                    raise Exception("文件重命名失败")
                            else:
                                # 文件大小不匹配，删除临时文件
                                os.remove(temp_path)
                                raise Exception("文件复制后大小不匹配")
                                
                        except (OSError, PermissionError, shutil.Error) as move_error:
                            log("ERROR", f"文件移动失败: {filename}, 错误: {str(move_error)}")
                            # 清理临时文件
                            try:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                            except:
                                pass
                            
                            if attempt == max_retries - 1:
                                # 最后一次尝试失败，回退到复制+删除方式
                                try:
                                    shutil.copy2(local_file_path, target_path)
                                    if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(local_file_path):
                                        os.remove(local_file_path)
                                        log("INFO", f"文件移动成功(回退方式): {filename} -> {safe_recognition}")
                                        return
                                    else:
                                        log("ERROR", f"文件移动回退失败: {filename}")
                                        if os.path.exists(target_path):
                                            os.remove(target_path)
                                except (OSError, PermissionError, shutil.Error) as fallback_error:
                                    log("ERROR", f"文件移动回退操作失败: {filename}, 错误: {str(fallback_error)}")
                    else:
                        # 复制操作：使用临时文件确保原子性
                        temp_path = target_path + '.tmp'
                        try:
                            shutil.copy2(local_file_path, temp_path)
                            
                            # 验证复制文件的完整性
                            if os.path.getsize(temp_path) == os.path.getsize(local_file_path):
                                os.rename(temp_path, target_path)
                                if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(local_file_path):
                                    log("INFO", f"文件复制成功: {filename} -> {safe_recognition}")
                                    return
                                else:
                                    raise Exception("文件重命名失败")
                            else:
                                # 文件大小不匹配，删除临时文件
                                os.remove(temp_path)
                                raise Exception("文件复制后大小不匹配")
                                
                        except (OSError, PermissionError, shutil.Error) as copy_error:
                            log("ERROR", f"文件复制失败: {filename}, 错误: {str(copy_error)}")
                            # 清理临时文件
                            try:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                            except:
                                pass
                            
                            if attempt == max_retries - 1:
                                log("ERROR", f"文件复制最终失败: {filename}")
                                if os.path.exists(target_path):
                                    os.remove(target_path)
                    
                    # 如果操作成功，跳出重试循环
                    break
                    
                except (OSError, PermissionError, shutil.Error) as e:
                    if attempt < max_retries - 1:
                        log("WARNING", f"文件操作失败 (尝试 {attempt + 1}/{max_retries}): {filename}, 错误: {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        log("ERROR", f"文件操作最终失败: {filename}, 错误: {str(e)}")
                        # 清理可能残留的临时文件
                        try:
                            if 'temp_path' in locals() and os.path.exists(temp_path):
                                os.remove(temp_path)
                        except:
                            pass
    
    def _sanitize_folder_name(self, name):
        """清理文件夹名称，移除非法字符"""
        if not name or not isinstance(name, str):
            return "未知分类"
        
        # 移除非法文件名字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 移除首尾空格和点
        name = name.strip().strip('.')
        
        # 限制长度
        if len(name) > 100:
            name = name[:100]
        
        # 如果名称为空，使用默认名称
        if not name:
            name = "未知分类"
            
        return name


