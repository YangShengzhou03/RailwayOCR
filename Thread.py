import json
import os
import re
import shutil
import threading
import time
from datetime import datetime, timedelta
from queue import Queue, Empty

import oss2
from PyQt6 import QtCore

from utils import load_config, save_summary, log


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
        self.lock = threading.Lock()
        self.logger = self.parent().logger if hasattr(self.parent(), 'logger') else print
        self._load_config()
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.total_files = len(image_files)
        self.file_queue = Queue()
        self.results = []
        self.workers = []
        self.signal_queue = Queue()
        self.signal_processor_running = True

    def _load_config(self):
        try:
            self.Config = load_config()
            self.max_requests_per_minute = self.Config.get("MAX_REQUESTS_PER_MINUTE", 60)
            self.worker_count = self.Config.get("CONCURRENCY", 4)
        except Exception as e:
            self.max_requests_per_minute = 60
            self.worker_count = 4
            self.error_occurred.emit(f"配置加载失败: {str(e)}")

    def run(self):
        results = []
        total_files = self.total_files

        try:
            if total_files == 0:
                self.processing_finished.emit(results)
                return

            self._create_directories()
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

            if self.results:
                save_summary(self.results)
            self.processing_finished.emit(self.results)
            self.progress_updated.emit(100, "处理完成")

        except Exception as e:
            error_msg = f"处理过程中发生致命错误: {str(e)}"
            self.error_occurred.emit(error_msg)
            self.processing_finished.emit(results)

    def _worker(self, worker_id):
        while self.is_running or not self.file_queue.empty():
            try:
                file_path = self.file_queue.get(timeout=0.5)
            except Empty:
                break

            try:
                if not self.is_running:
                    result = {
                        'filename': os.path.basename(file_path),
                        'success': False,
                        'error': '处理已取消'
                    }
                else:
                    result = self.rate_limited_process(file_path, self.client)

                with self.lock:
                    self.processed_count += 1
                    self.results.append(result)

                    if result['success']:
                        self.success_count += 1
                        result['category_dir'] = self.copy_to_classified_folder(
                            file_path, result['recognition'], self.dest_dir, self.is_move_mode)
                    else:
                        self.failed_count += 1
                        self.copy_to_classified_folder(file_path, None, self.dest_dir, self.is_move_mode)

                    self.signal_queue.put(('file_processed', result))
                    self.signal_queue.put(
                        ('stats_updated', self.processed_count, self.success_count, self.failed_count))

                    progress = int((self.processed_count / self.total_files) * 100)
                    self.signal_queue.put(
                        ('progress_updated', progress, f"已处理 {self.processed_count}/{self.total_files}"))

            except Exception as e:
                self.signal_queue.put(('error_occurred', f"工作线程 {worker_id + 1} 处理文件时出错: {str(e)}"))
            finally:
                self.file_queue.task_done()

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
            except Exception as e:
                pass
            finally:
                self.signal_queue.task_done()

    def _create_directories(self):
        try:
            self.create_output_directories(self.dest_dir)
        except Exception as e:
            error_msg = f"创建输出目录失败: {str(e)}"
            self.error_occurred.emit(error_msg)
            raise

    def rate_limited_process(self, file_path, client):
        if not self.is_running:
            return {'filename': os.path.basename(file_path), 'success': False, 'error': '处理已取消'}

        self._check_rate_limit()

        if not self.is_running:
            raise RuntimeError("处理已取消")

        return self.process_image_file(file_path, client)

    def _check_rate_limit(self):
        with self.lock:
            now = datetime.now()
            if now - self.window_start > timedelta(minutes=1):
                self.requests_counter = 0
                self.window_start = now

            if self.requests_counter >= self.max_requests_per_minute:
                wait_time = (self.window_start + timedelta(minutes=1) - now).total_seconds() + 0.1
                self.rate_limit_warning.emit(f"请求频率限制，等待 {wait_time:.1f} 秒")
                log("WARNING", f"请求频率限制，等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
                self.requests_counter = 0
                self.window_start = now

            self.requests_counter += 1

    def stop(self):
        with self.lock:
            self.is_running = False

        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except Empty:
                continue
            self.file_queue.task_done()

        self.processing_stopped.emit()

    def upload_and_get_signed_url(self, local_file, oss_path):
        filename = os.path.basename(local_file)
        auth = oss2.Auth(self.Config["ACCESS_KEY_ID"], self.Config["ACCESS_KEY_SECRET"])
        bucket = oss2.Bucket(auth, self.Config["ENDPOINT"], self.Config["BUCKET_NAME"])
        if not os.path.exists(local_file):
            return {'success': False, 'error': f"文件不存在: {local_file}"}
        result = bucket.put_object_from_file(oss_path, local_file)
        if result.status == 200:
            signed_url = bucket.sign_url('GET', oss_path, self.Config["EXPIRES_IN"])
            return {
                'success': True,
                'signed_url': signed_url,
                'expire_time': (datetime.now() + timedelta(seconds=self.Config["EXPIRES_IN"])).strftime(
                    "%m-%d %H:%M:%S")
            }
        return {'success': False, 'error': f"OSS处理失败，HTTP状态码: {result.status}"}

    def is_image_file(self, filename):
        return os.path.splitext(filename)[1].lower() in self.Config["ALLOWED_EXTENSIONS"]

    def parse_ocr_result(self, ocr_data):
        if not ocr_data.get('success'):
            return None
        data = ocr_data.get('data', '')
        try:
            text = data.get('msg', '') if isinstance(data, dict) else json.loads(data).get('msg', '')
        except (json.JSONDecodeError, TypeError):
            text = str(data)
        match = re.search(self.Config["RE"], text)
        return match.group(0).upper() if match else None

    def process_image_file(self, local_file_path, client):
        filename = os.path.basename(local_file_path)
        oss_path = f"RailwayOCR/images/{datetime.now().strftime('%Y%m%d')}/{filename}"
        upload_result = self.upload_and_get_signed_url(local_file_path, oss_path)
        if not upload_result['success']:
            return {'filename': filename, 'success': False, 'error': upload_result['error']}
        for attempt in range(self.Config["RETRY_TIMES"]):
            ocr_result = client.run_workflow(
                workflow_id=self.Config["WORKFLOW_ID"],
                parameters={
                    "prompt": self.Config["PROMPT"],
                    "image": upload_result['signed_url']
                }
            )
            print(ocr_result)
            if ocr_result['success']:
                recognition = self.parse_ocr_result(ocr_result)
                status = {
                    'filename': filename,
                    'success': bool(recognition),
                    'recognition': recognition,
                    'oss_path': oss_path,
                    'signed_url': upload_result['signed_url']
                }
                return status
            time.sleep(1)
        error_msg = ocr_result.get('error_msg', '未知识别错误') if ocr_result else '未获取到识别结果'
        return {'filename': filename, 'success': False, 'error': error_msg}

    def create_output_directories(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "识别失败"), exist_ok=True)

    def copy_to_classified_folder(self, local_file_path, recognition, output_dir, is_move=False):
        log("DEBUG", f"{local_file_path} 识别为 {recognition}")
        filename = os.path.basename(local_file_path)
        category = ''.join(c for c in recognition if c.isalnum() or c in "-_.() ") if recognition else "识别失败"
        category_dir = os.path.join(output_dir, category or "其他")
        os.makedirs(category_dir, exist_ok=True)
        dest_path = os.path.join(category_dir, filename)
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(filename)
            dest_path = os.path.join(category_dir, f"{name}_{counter}{ext}")
            counter += 1
        try:
            (shutil.move if is_move else shutil.copy2)(local_file_path, dest_path)
            return category_dir
        except Exception as e:
            return None
