"""
RailwayOCR主窗口模块

该模块负责应用程序的主界面管理，包括：
- 文件选择和目录管理
- OCR客户端初始化和配置
- 图像处理线程控制
- 用户界面交互处理
- 异常处理和资源清理
"""

import os
import sys
import time
from datetime import timedelta

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QFileDialog)

import utils
from Setting import SettingWindow
from Thread import ProcessingThread
from Ui_MainWindow import Ui_MainWindow
from clients import AliClient, BaiduClient, LocalClient
from utils import MODE_ALI, MODE_LOCAL, MODE_BAIDU, get_resource_path, log, load_config


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    主窗口类，负责管理OCR应用程序的主界面和核心功能
    
    属性:
        client: OCR客户端实例，用于文本识别
        source_dir: 源文件夹路径
        dest_dir: 目标文件夹路径
        processing: 处理状态标志
        processing_thread: 处理线程实例
        config: 应用程序配置
    """
    
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.source_dir = ""
        self.dest_dir = ""

        self.processing = False
        self.processing_start_time = 0
        self.processing_thread = None
        self.image_files = []

        self.is_move_mode = False
        self.dragging = False
        self.drag_position = QtCore.QPoint()
        self.setting_window = None
        self.client = None

        utils.MAIN_WINDOW = self
        self.config = load_config()
        self._initialize_ocr_client()

        self._init_ui_components()
        self._setup_connections()

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("LeafView-RailwayOCR")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))

    def _init_ui_components(self):
        """初始化用户界面组件的初始状态"""
        self.total_files_label.setText("0")
        self.processed_label.setText("0")
        self.success_label.setText("0")
        self.failed_label.setText("0")

        self.copy_radio.setChecked(True)
        self.move_radio.setChecked(False)
        self.pushButton_start.setText("开始分类")

        self.textEdit_log.setReadOnly(True)

    def _initialize_ocr_client(self):
        """初始化OCR客户端实例，根据配置选择不同的OCR服务提供商"""
        mode_index = self.config.get("MODE_INDEX", 0)
        try:
            if mode_index == MODE_ALI:
                self.client = AliClient()
                log("WARNING", "已切换至阿里云OCR服务")
            elif mode_index == MODE_BAIDU:
                self.client = BaiduClient()
                log("WARNING", "已切换至百度OCR服务")
            else:
                self.client = LocalClient(max_retries=1)
                log("WARNING", "已切换至本地OCR引擎")
        except (ConnectionError, ValueError, OSError) as e:
            log("ERROR", f"OCR服务启动失败: {str(e)}")
            self.client = LocalClient(max_retries=1)

    def _setup_connections(self):
        """设置UI组件的事件信号连接"""
        self.pushButton_src_folder.clicked.connect(self.browse_source_directory)
        self.pushButton_dst_folder.clicked.connect(self.browse_dest_directory)

        self.pushButton_start.clicked.connect(self.toggle_processing)
        self.copy_radio.toggled.connect(self._toggle_move_mode)
        self.move_radio.toggled.connect(self._toggle_move_mode)

        self.toolButton_setting.clicked.connect(self.open_setting)
        self.toolButton_close.clicked.connect(self.close_application)
        self.toolButton_mini.clicked.connect(self.minimize_window)

    def open_setting(self):
        """打开设置窗口"""
        self.setting_window = SettingWindow()
        self.setting_window.show()

    def mousePressEvent(self, event):
        """处理鼠标按下事件，支持窗口拖动"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，实现窗口拖动功能"""
        if self.dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件，结束窗口拖动"""
        self.dragging = False

    def browse_source_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择源文件夹")

        if directory:
            self.source_dir = directory
            self.lineEdit_src_folder.setText(directory)
            log("INFO", f"待分类文件夹已选择: {os.path.basename(directory)}")

            if not self._check_directory_conflict():
                self._load_images()

    def browse_dest_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if directory:
            self.dest_dir = directory
            self.lineEdit_dst_folder.setText(directory)
            log("INFO", f"目标文件夹已选择: {os.path.basename(directory)}")
            self._check_directory_conflict()

    def _load_images(self):
        self.image_files = []
        if not self.source_dir or not os.path.exists(self.source_dir):
            log("ERROR", "源文件夹不存在或未设置")
            return

        try:
            for root, _, files in os.walk(self.source_dir):
                for file in files:
                    try:
                        if any(file.lower().endswith(ext) for ext in self.config["ALLOWED_EXTENSIONS"]):
                            file_path = os.path.abspath(os.path.join(root, file))
                            self.image_files.append(file_path)
                    except (FileNotFoundError, PermissionError, OSError) as e:
                        log("ERROR", f"处理文件 {file} 时出错: {str(e)}")
                        continue
        except PermissionError:
            log("ERROR", f"访问文件夹 {self.source_dir} 时权限不足")
            return
        except (ValueError, TypeError) as e:
            log("ERROR", f"扫描文件夹时出错: {str(e)}")
            return

        total_count = len(self.image_files)
        self.total_files_label.setText(str(total_count))
        log("DEBUG", f"扫描完成，发现 {total_count} 个图像文件")

    def _toggle_move_mode(self):
        self.is_move_mode = self.move_radio.isChecked()

    def _check_directory_conflict(self):
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

        except (RuntimeError, ConnectionError) as e:
            log("ERROR", f"文件夹检查出错: {str(e)}")

        return False

    def toggle_processing(self):
        if self.processing:
            self.stop_processing()
            return
        if self.processing_thread and self.processing_thread.isRunning():
            log("WARNING", "存在正在运行的处理线程，尝试停止")
            self._safe_stop_thread()
        self.start_processing()

    def _safe_stop_thread(self):
        if not self.processing_thread or not self.processing_thread.isRunning():
            return True

        try:
            self.processing_thread.stop()
            if self.processing_thread.wait(2000):
                log("INFO", "处理线程已成功停止")
                return True
            else:
                log("WARNING", "处理线程未能正常终止，强制终止")
                self.processing_thread.terminate()
                return False
        except Exception as e:
            log("ERROR", f"停止线程时发生错误: {str(e)}")
            return False

    def start_processing(self):
        if not self._validate_processing_conditions():
            return

        total_files = len(self.image_files)
        mode = "移动" if self.is_move_mode else "复制"
        reply = QMessageBox.question(
            self, "确认处理",
            f"即将识别分类 {total_files} 个图像并 {mode} 。\n是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            log("INFO", "用户取消处理操作")
            return

        self.processing_start_time = time.time()
        self.processing = True
        self.pushButton_start.setText("停止分类")
        self.progressBar.setValue(0)

        try:
            mode_index = self.config.get("MODE_INDEX", 0)

            if mode_index == MODE_ALI:
                print("阿里云")
                appcode = self.config.get("ALI_APPCODE", "")
                if not appcode:
                    log("ERROR", "未配置阿里云AppCode")
                    return
                if not hasattr(self.client, 'client_type') or self.client.client_type != 'ali':
                    self.client = AliClient()
                client = self.client
            elif mode_index == MODE_LOCAL:
                print("本地")
                if not hasattr(self.client, 'client_type') or self.client.client_type != 'local':
                    self.client = LocalClient(max_retries=1)
                client = self.client
            elif mode_index == MODE_BAIDU:
                print("百度")
                api_key = self.config.get("BAIDU_API_KEY")
                secret_key = self.config.get("BAIDU_SECRET_KEY")
                if not api_key or not secret_key:
                    log("ERROR", "未配置百度云API Key或Secret Key")
                    return
                if not hasattr(self.client, 'client_type') or self.client.client_type != 'baidu':
                    self.client = BaiduClient()
                client = self.client
            else:
                log("ERROR", f"无效的模式索引: {mode_index}")
                return

            if not hasattr(client, 'recognize') or not callable(client.recognize):
                raise ValueError("OCR客户端必须实现recognize方法")

            self.processing_thread = ProcessingThread(
                client, self.image_files, self.dest_dir, self.is_move_mode
            )
            from PyQt6.QtCore import Qt
            self.processing_thread.processing_finished.connect(self.on_processing_finished,
                                                               Qt.ConnectionType.QueuedConnection)
            self.processing_thread.stats_updated.connect(self.on_stats_updated, Qt.ConnectionType.QueuedConnection)
            self.processing_thread.progress_updated.connect(self.on_progress_updated,
                                                            Qt.ConnectionType.QueuedConnection)
            self.processing_thread.processing_stopped.connect(self.on_processing_stopped,
                                                              Qt.ConnectionType.QueuedConnection)
            self.processing_thread.error_occurred.connect(self.on_error_occurred, Qt.ConnectionType.QueuedConnection)
            self.processing_thread.finished.connect(self._cleanup_thread)

            self.processing_thread.start()
            log("INFO", "正在处理图像，请耐心等待")

        except Exception as e:
            error_msg = f"启动处理线程失败: {str(e)}"
            log("ERROR", error_msg)
            QMessageBox.critical(self, "线程启动失败", error_msg)
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

        mode_index = self.config.get("MODE_INDEX", 0)

        if mode_index == MODE_ALI and not self.config.get("ALI_APPCODE"):
            log("WARNING", "未配置阿里云AppCode")
            return False
        if mode_index == MODE_BAIDU and not (
                self.config.get("BAIDU_API_KEY") and self.config.get("BAIDU_SECRET_KEY")):
            log("WARNING", "未配置百度API Key或Secret Key")
            return False
        return True

    def stop_processing(self):
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止处理吗? 当前进度将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            log("WARNING", "用户请求停止处理")
            self.pushButton_start.setText("正在刹停")
            self.pushButton_start.setEnabled(False)
            self.processing = False

            if self.processing_thread and self.processing_thread.isRunning():
                self._safe_stop_thread()
                QtCore.QTimer.singleShot(100, self._update_ui_after_stop)
            else:
                QtCore.QTimer.singleShot(100, self._update_ui_after_stop)

    def _update_ui_after_stop(self):
        self.pushButton_start.setEnabled(True)
        self.pushButton_start.setText("开始分类")

    @QtCore.pyqtSlot(int, str)
    def on_progress_updated(self, value, message):
        """处理进度更新信号，更新进度条显示"""
        try:
            self.progressBar.setValue(value)
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"更新进度条失败: {str(e)}")

    @QtCore.pyqtSlot(int, int, int)
    def on_stats_updated(self, processed, success, failed):
        """处理统计信息更新信号，更新处理结果统计"""
        try:
            self.processed_label.setText(str(processed))
            self.success_label.setText(str(success))
            self.failed_label.setText(str(failed))
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"更新统计信息失败: {str(e)}")

    @QtCore.pyqtSlot(list)
    def on_processing_finished(self, results):
        """处理完成信号，显示最终处理结果统计"""
        self.processing = False
        processing_end_time = time.time()
        total_seconds = int(processing_end_time - self.processing_start_time)
        total_time = str(timedelta(seconds=total_seconds))

        total_count = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_count - success_count
        success_rate = f"{(success_count / total_count * 100) if total_count > 0 else 0:.2f}%"

        log("DEBUG", "=" * 50)
        log("DEBUG", f"处理完成，总耗时: {total_time}")
        log("DEBUG", f"总文件数: {total_count}, 成功: {success_count}, 失败: {failed_count}, 识别率: {success_rate}")
        log("DEBUG", "=" * 50)

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

    @QtCore.pyqtSlot()
    def on_processing_stopped(self):
        """处理停止信号，清理处理状态"""
        try:
            log("INFO", "处理已停止")
            self.processing = False
            QtCore.QTimer.singleShot(0, self._update_ui_after_stop)
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"处理停止信号失败: {str(e)}")

    @QtCore.pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        """处理错误信号，显示错误信息并重置界面"""
        try:
            log("ERROR", f"处理线程错误: {error_msg}")
            QMessageBox.critical(self, "处理错误", error_msg)
            self.processing = False
            self.pushButton_start.setEnabled(True)
            self.pushButton_start.setText("开始分类")
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"处理错误信号失败: {str(e)}")

    def on_config_updated(self):
        """配置更新时的回调方法，重新加载配置并重新初始化OCR客户端"""
        try:
            self.config = load_config()
            self._initialize_ocr_client()
            log("INFO", "配置已更新，OCR客户端已重新初始化")
        except Exception as e:
            log("ERROR", f"配置更新失败: {str(e)}")

    def _cleanup_thread(self):
        """清理处理线程和OCR资源"""
        if self.processing_thread:
            if hasattr(self.client, 'cleanup') and hasattr(self.client,
                                                           'client_type') and self.client.client_type == 'local':
                try:
                    self.client.cleanup()
                except (RuntimeError, ValueError, TypeError) as e:
                    log("ERROR", f"清理本地OCR资源失败: {str(e)}")
            self.processing_thread.deleteLater()
            self.processing_thread = None

    def minimize_window(self):
        """最小化应用程序窗口"""
        try:
            self.showMinimized()
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"最小化窗口失败: {str(e)}")

    def close_application(self):
        """关闭应用程序，清理资源并安全退出"""
        try:
            if self.processing:
                reply = QMessageBox.question(
                    self, "确认关闭",
                    "当前正在处理文件, 关闭将终止处理过程。\n确定要关闭吗?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return

                if self.processing_thread and self.processing_thread.isRunning():
                    log("WARNING", "应用程序关闭前停止处理线程")
                    self.processing_thread.stop()
                    start_time = time.time()
                    while self.processing_thread.isRunning() and (time.time() - start_time) < 5:
                        QApplication.processEvents()
                        time.sleep(0.1)
                    if self.processing_thread.isRunning():
                        log("ERROR", "无法正常停止处理线程，强制退出")

            if hasattr(self.client, 'cleanup') and hasattr(self.client,
                                                           'client_type') and self.client.client_type == 'local':
                try:
                    self.client.cleanup()
                    log("INFO", "本地OCR资源已在应用程序关闭前释放")
                except (RuntimeError, ValueError, TypeError) as e:
                    log("ERROR", f"清理本地OCR资源失败: {str(e)}")

            log("INFO", "应用程序即将关闭")
            QApplication.quit()
        except (RuntimeError, ValueError, TypeError) as e:
            log("ERROR", f"关闭应用程序失败: {str(e)}")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        log("ERROR", f"应用程序启动失败: {str(e)}")
        sys.exit(1)
