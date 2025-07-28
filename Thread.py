import concurrent.futures
import os
import time
from functools import partial
from datetime import datetime, timedelta

from PyQt6 import QtCore
from utils import create_output_directories, process_image_file, copy_to_classified_folder, save_summary, load_config


class ProcessingThread(QtCore.QThread):
    file_processed = QtCore.pyqtSignal(dict)
    processing_finished = QtCore.pyqtSignal(list)
    processing_stopped = QtCore.pyqtSignal()
    stats_updated = QtCore.pyqtSignal(int, int, int)
    rate_limit_warning = QtCore.pyqtSignal(str)
    progress_updated = QtCore.pyqtSignal(int, str)

    def __init__(self, client, image_files, dest_dir, is_move_mode, parent=None):
        super().__init__(parent)
        self.client = client
        self.Config = load_config()
        self.image_files = image_files
        self.dest_dir = dest_dir
        self.is_move_mode = is_move_mode
        self.is_running = True
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.max_requests_per_minute = self.Config["MAX_REQUESTS_PER_MINUTE"]
        self.worker_count = self.Config["CONCURRENCY"]
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.futures = []
        self.total_files = len(image_files)

    def run(self):
        results = []
        total_files = self.total_files
        if total_files == 0:
            self.processing_finished.emit(results)
            return

        create_output_directories(self.dest_dir)
        self.stats_updated.emit(0, 0, 0)
        self.progress_updated.emit(0, "开始处理...")

        process_func = partial(self.rate_limited_process, client=self.client)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.worker_count) as executor:
            self.futures = [executor.submit(process_func, file_path) for file_path in self.image_files]

            for i, future in enumerate(concurrent.futures.as_completed(self.futures)):
                if not self.is_running:
                    for f in self.futures:
                        f.cancel()
                    executor.shutdown(wait=True)
                    break

                file_path = self.image_files[i]
                filename = os.path.basename(file_path)

                try:
                    result = future.result()
                except Exception as e:
                    result = {'filename': filename, 'success': False, 'error': str(e)}

                results.append(result)
                self.file_processed.emit(result)
                self.processed_count += 1

                if result['success']:
                    self.success_count += 1
                    result['category_dir'] = copy_to_classified_folder(
                        file_path, result['recognition'], self.dest_dir, self.is_move_mode)
                else:
                    self.failed_count += 1
                    copy_to_classified_folder(file_path, None, self.dest_dir, self.is_move_mode)

                self.stats_updated.emit(self.processed_count, self.success_count, self.failed_count)

                progress = int((self.processed_count / total_files) * 100)
                self.progress_updated.emit(progress, f"已处理 {self.processed_count}/{total_files}")

        if results:
            save_summary(results, self.dest_dir)
        self.processing_finished.emit(results)
        self.progress_updated.emit(100, "处理完成")

    def rate_limited_process(self, file_path, client):
        if not self.is_running:
            return {'filename': os.path.basename(file_path), 'success': False, 'error': '处理已取消'}
        self._check_rate_limit()
        return process_image_file(file_path, client)

    def _check_rate_limit(self):
        now = datetime.now()
        if now - self.window_start > timedelta(minutes=1):
            self.requests_counter = 0
            self.window_start = now

        if self.requests_counter >= self.max_requests_per_minute:
            wait_time = (self.window_start + timedelta(minutes=1) - now).total_seconds() + 0.1
            self.rate_limit_warning.emit(f"请求频率限制，等待 {wait_time:.1f} 秒")
            time.sleep(wait_time)
            self.requests_counter = 0
            self.window_start = now

        self.requests_counter += 1

    def stop(self):
        self.is_running = False
        for future in self.futures:
            future.cancel()
        self.processing_stopped.emit()
