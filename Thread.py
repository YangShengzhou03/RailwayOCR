import os
import time
import threading
import shutil
import json
import re
from datetime import datetime, timedelta
from queue import Queue, Empty

import oss2
from PyQt6 import QtCore

from utils import load_config, log, save_summary  # 假设log在utils中定义


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
        self.is_running = True  # 控制线程运行状态
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()  # 线程同步锁
        self.logger = self.parent().logger if hasattr(self.parent(), 'logger') else print
        self._load_config()
        self.requests_counter = 0
        self.window_start = datetime.now()
        self.total_files = len(image_files)
        self.file_queue = Queue()  # 任务队列
        self.results = []  # 处理结果
        self.workers = []  # 工作线程列表
        self.signal_queue = Queue()  # 信号队列（确保主线程发射信号）
        self.signal_processor_running = True  # 独立控制信号处理器运行状态

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

            # 初始化任务队列
            for file_path in self.image_files:
                self.file_queue.put(file_path)

            # 创建并启动工作线程
            for i in range(self.worker_count):
                worker = threading.Thread(target=self._worker, args=(i,), daemon=True)
                self.workers.append(worker)
                worker.start()
                self.logger(f"工作线程 {i + 1} 已启动")

            # 创建信号处理线程（独立控制运行状态）
            signal_thread = threading.Thread(target=self._signal_processor, daemon=True)
            signal_thread.start()

            # 等待所有工作线程完成（即使调用stop()，也会等待当前处理的文件完成）
            for worker in self.workers:
                worker.join()

            # 等待信号队列中的所有信号处理完毕后，再停止信号处理器
            self.signal_queue.join()  # 阻塞直到所有信号被处理
            self.signal_processor_running = False  # 停止信号处理器
            signal_thread.join()

            # 处理完成
            if self.results:
                save_summary(self.results)
            self.processing_finished.emit(self.results)
            self.progress_updated.emit(100, "处理完成")
            self.logger("处理全部完成")

        except Exception as e:
            error_msg = f"处理过程中发生致命错误: {str(e)}"
            self.logger(error_msg)
            self.error_occurred.emit(error_msg)
            self.processing_finished.emit(results)

    def _worker(self, worker_id):
        """工作线程函数，处理文件队列中的任务"""
        self.logger(f"工作线程 {worker_id + 1} 开始处理任务")

        while self.is_running or not self.file_queue.empty():  # 即使is_running=False，也要处理已取出的任务
            try:
                # 获取任务，设置超时以避免永久阻塞
                file_path = self.file_queue.get(timeout=0.5)
            except Empty:
                break  # 队列为空，退出循环

            try:
                # 检查是否已停止（允许正在处理的文件完成，但不再处理新任务）
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

                    # 将信号放入队列（无论是否停止，都发送进度更新）
                    self.signal_queue.put(('file_processed', result))
                    self.signal_queue.put(
                        ('stats_updated', self.processed_count, self.success_count, self.failed_count))

                    progress = int((self.processed_count / self.total_files) * 100)
                    self.signal_queue.put(
                        ('progress_updated', progress, f"已处理 {self.processed_count}/{self.total_files}"))

            except Exception as e:
                error_msg = f"工作线程 {worker_id + 1} 处理文件时出错: {str(e)}"
                self.logger(error_msg)
                self.signal_queue.put(('error_occurred', error_msg))
            finally:
                self.file_queue.task_done()

        self.logger(f"工作线程 {worker_id + 1} 已完成所有任务")

    def _signal_processor(self):
        """信号处理线程，确保所有信号在主线程中发射（即使停止后也处理剩余信号）"""
        while self.signal_processor_running or not self.signal_queue.empty():  # 处理完剩余信号再退出
            try:
                # 获取信号，设置超时以避免永久阻塞
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
                self.logger(f"信号处理错误: {str(e)}")
            finally:
                self.signal_queue.task_done()

    def _create_directories(self):
        """安全创建输出目录"""
        try:
            self.create_output_directories(self.dest_dir)
            self.logger(f"输出目录创建成功: {self.dest_dir}")
        except Exception as e:
            error_msg = f"创建输出目录失败: {str(e)}"
            self.logger(error_msg)
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
                self.logger(f"请求频率限制，等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
                self.requests_counter = 0
                self.window_start = now

            self.requests_counter += 1

    def stop(self):
        with self.lock:
            self.is_running = False  # 标记为停止，不再处理新任务
        self.logger("正在停止处理线程...")

        # 清空未处理的任务队列（保留正在处理的任务）
        while not self.file_queue.empty():
            try:
                self.file_queue.get_nowait()
            except Empty:
                continue
            self.file_queue.task_done()

        self.processing_stopped.emit()

    def upload_and_get_signed_url(self, local_file, oss_path):
        filename = os.path.basename(local_file)
        log("INFO", f"文件 {filename} 取出成功。")
        auth = oss2.Auth(self.Config["ACCESS_KEY_ID"], self.Config["ACCESS_KEY_SECRET"])
        bucket = oss2.Bucket(auth, self.Config["ENDPOINT"], self.Config["BUCKET_NAME"])
        if not os.path.exists(local_file):
            error_msg = f"文件不存在: {local_file}"
            log("ERROR", error_msg)
            return {'success': False, 'error': error_msg}
        result = bucket.put_object_from_file(oss_path, local_file)
        if result.status == 200:
            signed_url = bucket.sign_url('GET', oss_path, self.Config["EXPIRES_IN"])
            expire_time = (datetime.now() + timedelta(seconds=self.Config["EXPIRES_IN"])).strftime("%m-%d %H:%M:%S")
            return {
                'success': True,
                'signed_url': signed_url,
                'expire_time': expire_time
            }
        error_msg = f"OSS处理失败，HTTP状态码: {result.status}"
        log("ERROR", error_msg)
        return {'success': False, 'error': error_msg}

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
        log("WARNING", f"正在识别文件: {filename}")
        for attempt in range(self.Config["RETRY_TIMES"]):
            ocr_result = client.run_workflow(
                workflow_id=self.Config["WORKFLOW_ID"],
                parameters={
                    "prompt": self.Config["PROMPT"],
                    "image": upload_result['signed_url']
                }
            )
            if ocr_result['success']:
                recognition = self.parse_ocr_result(ocr_result)
                status = {
                    'filename': filename,
                    'success': bool(recognition),
                    'recognition': recognition,
                    'oss_path': oss_path,
                    'signed_url': upload_result['signed_url']
                }
                log("DEBUG" if recognition else "WARNING",
                    f"反馈识别结果: {filename} → {recognition}" if recognition else f"未识别到有效标签: {filename}")
                return status
            time.sleep(1)
        error_msg = ocr_result.get('error_msg', '未知识别错误') if ocr_result else '未获取到识别结果'
        log("ERROR", f"Ai识别失败: {filename}，原因: {error_msg}")
        return {'filename': filename, 'success': False, 'error': error_msg}

    def create_output_directories(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "识别失败"), exist_ok=True)

    def copy_to_classified_folder(self, local_file_path, recognition, output_dir, is_move=False):
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
            log("INFO", f"文件已{'移动' if is_move else '复制'}: {filename} → {category_dir}")
            return category_dir
        except Exception as e:
            log("ERROR", f"文件操作失败: {filename}, 错误: {str(e)}")
            return None
