import concurrent.futures
import os
import time
from functools import partial
from datetime import datetime, timedelta
from threading import Lock

from PyQt6 import QtCore
from utils import create_output_directories, process_image_file, copy_to_classified_folder, save_summary, load_config


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
        self.client = client
        self.image_files = image_files
        self.dest_dir = dest_dir
        self.is_move_mode = is_move_mode
        self.is_running = True
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.lock = Lock()  # 用于线程同步
        self.logger = self.parent().logger if hasattr(self.parent(), 'logger') else print
        self._load_config()
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.futures = []
        self.total_files = len(image_files)

    def _load_config(self):
        """安全加载配置并设置默认值"""
        try:
            self.Config = load_config()
            self.max_requests_per_minute = self.Config.get("MAX_REQUESTS_PER_MINUTE", 60)
            self.worker_count = self.Config.get("CONCURRENCY", 4)
            self.logger(f"配置加载成功: 并发数={self.worker_count}, 请求限制={self.max_requests_per_minute}/分钟")
        except Exception as e:
            self.logger(f"配置加载失败: {str(e)}")
            self.max_requests_per_minute = 60
            self.worker_count = 4
            self.error_occurred.emit(f"配置加载失败: {str(e)}")

    def run(self):
        results = []
        total_files = self.total_files

        try:
            self.logger(f"开始处理 {total_files} 个文件")

            if total_files == 0:
                self.processing_finished.emit(results)
                return

            self._create_directories()
            self.stats_updated.emit(0, 0, 0)
            self.progress_updated.emit(0, "开始处理...")

            process_func = partial(self.rate_limited_process, client=self.client)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.worker_count) as executor:
                self.logger(f"创建线程池，工作线程数: {self.worker_count}")

                # 创建future到文件路径的映射
                future_to_file = {executor.submit(process_func, file_path): file_path
                                  for file_path in self.image_files}
                self.futures = list(future_to_file.keys())

                # 按完成顺序处理结果
                for future in concurrent.futures.as_completed(self.futures):
                    if not self.is_running:
                        self.logger("处理被用户取消")
                        for f in self.futures:
                            f.cancel()
                        executor.shutdown(wait=True)
                        break

                    file_path = future_to_file[future]
                    filename = os.path.basename(file_path)

                    try:
                        result = future.result()
                    except Exception as e:
                        error_msg = f"处理文件 {filename} 时出错: {str(e)}"
                        self.logger(error_msg)
                        result = {'filename': filename, 'success': False, 'error': error_msg}

                    results.append(result)
                    self.file_processed.emit(result)

                    with self.lock:
                        self.processed_count += 1

                    if result['success']:
                        with self.lock:
                            self.success_count += 1
                        result['category_dir'] = copy_to_classified_folder(
                            file_path, result['recognition'], self.dest_dir, self.is_move_mode)
                    else:
                        with self.lock:
                            self.failed_count += 1
                        copy_to_classified_folder(file_path, None, self.dest_dir, self.is_move_mode)

                    self.stats_updated.emit(self.processed_count, self.success_count, self.failed_count)

                    progress = int((self.processed_count / total_files) * 100)
                    self.progress_updated.emit(progress, f"已处理 {self.processed_count}/{total_files}")

            if results:
                save_summary(results, self.dest_dir)
            self.processing_finished.emit(results)
            self.progress_updated.emit(100, "处理完成")
            self.logger("处理全部完成")

        except Exception as e:
            error_msg = f"处理过程中发生致命错误: {str(e)}"
            self.logger(error_msg)
            self.error_occurred.emit(error_msg)
            self.processing_finished.emit(results)  # 确保主线程知道处理已结束

    def _create_directories(self):
        """安全创建输出目录"""
        try:
            create_output_directories(self.dest_dir)
            self.logger(f"输出目录创建成功: {self.dest_dir}")
        except Exception as e:
            error_msg = f"创建输出目录失败: {str(e)}"
            self.logger(error_msg)
            self.error_occurred.emit(error_msg)
            raise

    def rate_limited_process(self, file_path, client):
        if not self.is_running:
            return {'filename': os.path.basename(file_path), 'success': False, 'error': '处理已取消'}

        # 检查是否需要停止
        if not self.is_running:
            raise RuntimeError("处理已取消")

        self._check_rate_limit()

        # 再次检查是否需要停止
        if not self.is_running:
            raise RuntimeError("处理已取消")

        return process_image_file(file_path, client)

    def _check_rate_limit(self):
        with self.lock:  # 保护计数器更新
            now = datetime.now()
            if now - self.window_start > timedelta(minutes=1):
                self.requests_counter = 0
                self.window_start = now

            if self.requests_counter >= self.max_requests_per_minute:
                wait_time = (self.window_start + timedelta(minutes=1) - now).total_seconds() + 0.1
                self.rate_limit_warning.emit(f"请求频率限制，等待 {wait_time:.1f} 秒")
                self.logger(f"请求频率限制，等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
                self.requests_counter = 0
                self.window_start = now

            self.requests_counter += 1

    def stop(self):
        with self.lock:
            self.is_running = False
        self.logger("正在停止处理线程...")

        # 尝试取消所有未完成的任务
        for future in self.futures:
            future.cancel()

        self.processing_stopped.emit()