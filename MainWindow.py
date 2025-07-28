import os
import sys
import time
from datetime import timedelta

import requests
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QApplication, QMainWindow,
                             QMessageBox, QFileDialog)

import utils
from Thread import ProcessingThread
from Ui_MainWindow import Ui_MainWindow
from utils import log, save_summary, get_resource_path


class CozeClient:

    def __init__(self, api_key, base_url="https://api.coze.cn/v1", timeout=30,
                 max_retries=3, backoff_factor=1.0, proxies=None):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.proxies = proxies
        self.session = self._create_session(max_retries, backoff_factor)

    def _create_session(self, max_retries, backoff_factor):
        session = requests.Session()
        retry_strategy = requests.adapters.Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        return session

    def run_workflow(self, workflow_id, parameters=None, bot_id=None, is_async=False):
        api_url = f"{self.base_url}/workflow/run"
        payload = {"workflow_id": workflow_id, "is_async": is_async}

        if parameters:
            payload["parameters"] = parameters
        if bot_id:
            payload["bot_id"] = bot_id

        try:
            response = self.session.post(
                api_url,
                json=payload,
                timeout=self.timeout,
                proxies=self.proxies
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                return {
                    "success": True,
                    "data": result.get("data"),
                    "debug_url": result.get("debug_url"),
                    "execute_id": result.get("execute_id"),
                    "usage": result.get("usage")
                }
            else:
                return {
                    "success": False,
                    "error_code": result.get("code"),
                    "error_msg": result.get("msg"),
                    "logid": result.get("detail", {}).get("logid")
                }

        except Exception as e:
            return {"success": False, "error_msg": f"请求异常: {str(e)}"}


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.source_dir = ""
        self.dest_dir = ""
        self.is_move_mode = False
        self.processing_thread = None
        self.image_files = []
        self.processing = False
        self.processing_start_time = 0

        self.dragging = False
        self.drag_position = QtCore.QPoint()

        utils.main_window = self
        self.config = utils.load_config()
        self._init_ui_components()
        self.setup_connections()

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("LeafView-RailwayOCR")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))

        log("INFO", "LeafView-RailwayOCR 启动成功.")

    def _init_ui_components(self):
        self.total_files_label.setText("0")
        self.processed_label.setText("0")
        self.success_label.setText("0")
        self.failed_label.setText("0")

        self.copy_radio.setChecked(True)
        self.move_radio.setChecked(False)
        self.pushButton_start.setText("开始分类")

        self.textEdit_log.setReadOnly(True)

    def setup_connections(self):
        self.pushButton_src_folder.clicked.connect(self.browse_source_directory)
        self.pushButton_dst_folder.clicked.connect(self.browse_dest_directory)

        self.pushButton_start.clicked.connect(self.toggle_processing)
        self.copy_radio.toggled.connect(self.toggle_move_mode)
        self.move_radio.toggled.connect(self.toggle_move_mode)

        self.toolButton_close.clicked.connect(self.close_application)
        self.toolButton_mini.clicked.connect(self.minimize_window)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def browse_source_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择源文件夹")

        if directory:
            self.source_dir = directory
            self.lineEdit_src_folder.setText(directory)
            log("INFO", f"已选择源文件夹: {directory}")

            if not self.check_directory_conflict():
                self.load_images()

    def browse_dest_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择目标文件夹")

        if directory:
            self.dest_dir = directory
            self.lineEdit_dst_folder.setText(directory)
            log("INFO", f"已选择目标文件夹: {directory}")
            self.check_directory_conflict()

    def load_images(self):
        self.image_files = []

        if not self.source_dir or not os.path.exists(self.source_dir):
            log("WARNING", "源文件夹不存在或未设置")
            return

        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.config["ALLOWED_EXTENSIONS"]):
                    file_path = os.path.join(root, file)
                    self.image_files.append(file_path)

        total_count = len(self.image_files)
        self.total_files_label.setText(str(total_count))
        log("INFO", f"扫描完成，发现 {total_count} 个图像文件")

    def toggle_move_mode(self):
        self.is_move_mode = self.move_radio.isChecked()
        mode = "移动" if self.is_move_mode else "复制"
        log("INFO", f"操作模式切换为: {mode}")

    def check_directory_conflict(self):
        if not (self.source_dir and self.dest_dir):
            return False

        try:
            source_abs = os.path.abspath(self.source_dir)
            dest_abs = os.path.abspath(self.dest_dir)

            if dest_abs == source_abs or os.path.commonpath([source_abs, dest_abs]) == source_abs:
                log("ERROR", "文件夹冲突: 目标文件夹不能是源文件夹或其子文件夹")
                QMessageBox.warning(
                    self, "文件夹冲突",
                    "目标文件夹不能是源文件夹或其子文件夹！这可能导致文件覆盖或其他意外行为。"
                )

                self.source_dir = ""
                self.dest_dir = ""
                self.lineEdit_src_folder.setText("待处理文件夹（默认包含子文件夹）")
                self.lineEdit_dst_folder.setText("存放分类后的结果")
                self.image_files = []
                self.total_files_label.setText("0")
                return True

        except Exception as e:
            log("ERROR", f"文件夹检查出错: {str(e)}")

        return False

    def toggle_processing(self):
        if self.processing:
            self.stop_processing()
        else:
            self.start_processing()

    def start_processing(self):
        if not self._validate_processing_conditions():
            return

        total_files = len(self.image_files)
        mode = "移动" if self.is_move_mode else "复制"
        reply = QMessageBox.question(
            self, "确认处理",
            f"即将{mode} {total_files} 个图像文件到分类文件夹。\n是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            log("INFO", "用户取消处理操作")
            return

        self.processing_start_time = time.time()

        log("WARNING", "开始文件处理流程")
        self.processing = True
        self.pushButton_start.setText("停止分类")
        self.progressBar.setValue(0)

        try:
            client = CozeClient(api_key=self.config["COZE_API_KEY"])
            self.processing_thread = ProcessingThread(
                client, self.image_files, self.dest_dir, self.is_move_mode
            )
            self.processing_thread.file_processed.connect(self.on_file_processed)
            self.processing_thread.processing_finished.connect(self.on_processing_finished)
            self.processing_thread.stats_updated.connect(self.update_stats)
            self.processing_thread.progress_updated.connect(self.update_progress)

            self.processing_thread.start()
            log("INFO", "图像识别线程启动")

        except Exception as e:
            log("ERROR", f"启动处理线程失败: {str(e)}")
            self.processing = False
            self.pushButton_start.setText("开始分类")

    def _validate_processing_conditions(self):
        if not self.lineEdit_src_folder.text().strip():
            log("WARNING", "未选择源文件夹")
            QMessageBox.warning(self, "参数缺失", "请先选择源文件夹")
            return False

        if not self.lineEdit_dst_folder.text().strip():
            log("WARNING", "未选择目标文件夹")
            QMessageBox.warning(self, "参数缺失", "请先选择目标文件夹")
            return False

        if not self.image_files:
            log("WARNING", "源文件夹中没有图像文件")
            QMessageBox.warning(self, "文件缺失", "源文件夹中未发现任何图像文件")
            return False

        return True

    def stop_processing(self):
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止处理吗? 当前进度将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            log("INFO", "用户请求停止处理")
            self.pushButton_start.setEnabled(False)
            self.processing = False
            self.pushButton_start.setText("等待停止")
            if self.processing_thread:
                self.processing_thread.stop()
                log("INFO", "处理线程已停止")

    def update_progress(self, value, message):
        self.progressBar.setValue(value)
        print(message)

    def on_file_processed(self, result):
        status = "成功" if result['success'] else "失败"
        details = result.get('recognition', '未识别') if result['success'] else result.get('error', '未知错误')

        if not result['success']:
            log("ERROR", f"{result['filename']} - {status}: {details}")

    def update_stats(self, processed, success, failed):
        self.processed_label.setText(str(processed))
        self.success_label.setText(str(success))
        self.failed_label.setText(str(failed))

    def on_processing_finished(self, results):
        self.processing = False
        self.pushButton_start.setText("开始分类")

        processing_end_time = time.time()
        total_seconds = int(processing_end_time - self.processing_start_time)
        total_time = str(timedelta(seconds=total_seconds))

        total_count = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_count - success_count
        success_rate = f"{(success_count / total_count * 100) if total_count > 0 else 0:.2f}%"

        log("INFO", "=" * 50)
        log("INFO", f"处理完成 | 总耗时: {total_time}")
        log("INFO", f"总文件数: {total_count} | 成功: {success_count} | 失败: {failed_count}")
        log("INFO", f"识别率: {success_rate}")
        log("INFO", "=" * 50)

        if total_count > 0:
            result_message = (
                f"LeafView-RailWayORC 处理完成!\n\n"
                f"总文件数: {total_count}\n"
                f"成功识别: {success_count}\n"
                f"识别失败: {failed_count}\n"
                f"识别率: {success_rate}\n"
                f"总共耗时: {total_time}"
            )
            QMessageBox.information(self, "处理完成", result_message)

        self.pushButton_start.setEnabled(True)
        self.pushButton_start.setText("开始分类")

        save_summary(results, self.dest_dir)

    def minimize_window(self):
        log("INFO", "窗口最小化")
        self.showMinimized()

    def close_application(self):
        if self.processing:
            reply = QMessageBox.question(
                self, "确认关闭",
                "当前正在处理文件，关闭将终止处理过程。\n确定要关闭吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            if self.processing_thread:
                self.processing_thread.stop()
                log("INFO", "处理线程已终止")

        log("INFO", "应用程序即将关闭")
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
