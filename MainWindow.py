import os
import sys
import time
from datetime import timedelta

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QFileDialog)

import utils
from Client import LocalClient, AliClient, DouyinClient, BaiduClient
from Setting import SettingWindow
from Thread import ProcessingThread
from Ui_MainWindow import Ui_MainWindow
from utils import save_summary, get_resource_path, log


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

        log("INFO", "LeafView-RailwayOCR 启动成功")

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

        self.toolButton_setting.clicked.connect(self.open_setting)
        self.toolButton_close.clicked.connect(self.close_application)
        self.toolButton_mini.clicked.connect(self.minimize_window)

    def open_setting(self):
        self.setting_window = SettingWindow()
        self.setting_window.show()
        log("INFO", "打开设置窗口")

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

        try:
            for root, _, files in os.walk(self.source_dir):
                for file in files:
                    try:
                        if any(file.lower().endswith(ext) for ext in self.config["ALLOWED_EXTENSIONS"]):
                            file_path = os.path.abspath(os.path.join(root, file))
                            self.image_files.append(file_path)
                    except Exception as e:
                        log("ERROR", f"处理文件 {file} 时出错: {str(e)}")
                        continue
        except PermissionError:
            log("ERROR", f"访问文件夹 {self.source_dir} 时权限不足")
            QMessageBox.warning(self, "权限错误", f"无法访问文件夹 {self.source_dir}，权限不足")
            return
        except Exception as e:
            log("ERROR", f"扫描文件夹时出错: {str(e)}")
            QMessageBox.warning(self, "扫描错误", f"扫描文件夹时出错: {str(e)}")
            return

        total_count = len(self.image_files)
        self.total_files_label.setText(str(total_count))
        log("INFO", f"扫描完成，发现 {total_count} 个图像文件")

    def toggle_move_mode(self):
        self.is_move_mode = self.move_radio.isChecked()

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
        """
        切换处理状态（开始/停止处理）
        """
        if self.processing:
            self.stop_processing()
        else:
            # 确保之前的线程已经终止
            if self.processing_thread and self.processing_thread.isRunning():
                log("WARNING", "存在正在运行的处理线程，尝试停止")
                self._safe_stop_thread()
            self.start_processing()

    def _safe_stop_thread(self):
        """
        安全地停止处理线程

        返回:
            bool: 线程是否成功终止
        """
        if not self.processing_thread or not self.processing_thread.isRunning():
            return True

        self.processing_thread.stop()
        # 等待线程终止，最多等待10秒
        start_time = time.time()
        while self.processing_thread.isRunning() and (time.time() - start_time) < 10:
            QApplication.processEvents()
            time.sleep(0.1)

        if self.processing_thread.isRunning():
            log("ERROR", "无法正常停止处理线程")
            # 尝试强制终止（不推荐，但在极端情况下可能必要）
            try:
                # 在线程对象上设置一个标志，通知线程必须立即终止
                self.processing_thread.is_running = False
                # 再次等待短暂时间
                time.sleep(0.5)
                if self.processing_thread.isRunning():
                    log("ERROR", "线程仍在运行，可能导致资源泄漏")
                    return False
            except Exception as e:
                log("ERROR", f"强制终止线程时出错: {str(e)}")
                return False
        else:
            log("INFO", "处理线程已成功终止")
            # 清理线程资源
            self.processing_thread = None
        return True

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

        log("WARNING", "开始文件处理流程")
        log("INFO", f"开始处理 {len(self.image_files)} 个图像文件")
        self.processing = True
        self.pushButton_start.setText("停止分类")
        self.progressBar.setValue(0)

        try:
            mode_index = self.config.get("MODE_INDEX", 0)

            if mode_index == 0:
                appcode = self.config.get("ALI_CODE")
                if not appcode:
                    QMessageBox.critical(self, "错误", "未配置阿里云AppCode")
                    log("ERROR", "未配置阿里云AppCode")
                    return
                client = AliClient(appcode=appcode)
                log("INFO", "使用阿里云OCR模式")
            elif mode_index == 1:
                try:
                    client = LocalClient(max_retries=5)
                    log("INFO", "使用本地OCR模式")
                except Exception as e:
                    error_msg = f"本地OCR模型加载失败: {str(e)}"
                    log("ERROR", error_msg)
                    QMessageBox.critical(self, "模型加载失败", f"无法加载OCR模型: {str(e)}\n请检查网络连接并重试。")
                    return
            elif mode_index == 2:
                api_key = self.config.get("DOUYIN_API_KEY")
                if not api_key:
                    QMessageBox.critical(self, "错误", "未配置抖音API Key")
                    log("ERROR", "未配置抖音API Key")
                    return
                timeout = self.config.get("REQUEST_TIMEOUT", 60)
                client = DouyinClient(
                    api_key=api_key,
                    timeout=timeout,
                    max_retries=self.config.get("RETRY_TIMES", 3),
                    backoff_factor=self.config.get("BACKOFF_FACTOR", 1.0)
                )
                log("INFO", "使用抖音云OCR模式")
            elif mode_index == 3:
                api_key = self.config.get("BAIDU_API_KEY")
                secret_key = self.config.get("BAIDU_SECRET_KEY")
                if not api_key or not secret_key:
                    QMessageBox.critical(self, "错误", "未配置百度云API Key或Secret Key")
                    log("ERROR", "未配置百度云API Key或Secret Key")
                    return
                client = BaiduClient(api_key=api_key, secret_key=secret_key)
                log("INFO", "使用百度云OCR模式")
            else:
                QMessageBox.critical(self, "错误", f"无效的模式索引: {mode_index}")
                log("ERROR", f"无效的模式索引: {mode_index}")
                return

            self.processing_thread = ProcessingThread(
                client, self.image_files, self.dest_dir, self.is_move_mode
            )
            self.processing_thread.processing_finished.connect(self.on_processing_finished)
            self.processing_thread.stats_updated.connect(self.on_stats_updated)
            self.processing_thread.progress_updated.connect(self.on_progress_updated)
            self.processing_thread.processing_stopped.connect(self.on_processing_stopped)
            self.processing_thread.error_occurred.connect(self.on_error_occurred)

            self.processing_thread.start()
            log("INFO", "正在处理图像，请耐心等待")

        except Exception as e:
            error_msg = f"启动处理线程失败: {str(e)}"
            log("ERROR", error_msg)
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

        if mode_index == 0 and not self.config.get("ALI_CODE"):
            log("WARNING", "未配置阿里云AppCode")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置阿里云AppCode")
            return False
        elif mode_index == 1:
            pass
        elif mode_index == 2 and not self.config.get("DOUYIN_API_KEY"):
            log("WARNING", "未配置抖音API Key")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置抖音API Key")
            return False
        elif mode_index == 3 and not (self.config.get("BAIDU_API_KEY") and self.config.get("BAIDU_SECRET_KEY")):
            log("WARNING", "未配置百度API Key或Secret Key")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置百度API Key和Secret Key")
            return False

        return True

    def stop_processing(self):
        """
        停止处理
        """
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止处理吗? 当前进度将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            log("WARNING", "用户请求停止处理")
            self.pushButton_start.setText("正在停止...")
            self.pushButton_start.setEnabled(False)
            self.processing = False

            if self.processing_thread and self.processing_thread.isRunning():
                # 安全停止线程
                success = self._safe_stop_thread()
                if not success:
                    log("ERROR", "停止处理线程失败")
                    QMessageBox.critical(self, "错误", "无法正常停止处理线程，可能导致资源泄漏")

            # 更新UI状态
            self.pushButton_start.setEnabled(True)
            self.pushButton_start.setText("开始分类")

    @QtCore.pyqtSlot(int, str)
    def on_progress_updated(self, value, message):
        try:
            self.progressBar.setValue(value)
        except Exception as e:
            log("ERROR", f"更新进度条失败: {str(e)}")

    @QtCore.pyqtSlot(int, int, int)
    def on_stats_updated(self, processed, success, failed):
        try:
            self.processed_label.setText(str(processed))
            self.success_label.setText(str(success))
            self.failed_label.setText(str(failed))
        except Exception as e:
            log("ERROR", f"更新统计信息失败: {str(e)}")

    @QtCore.pyqtSlot(list)
    def on_processing_finished(self, results):
        self.processing = False
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

        log("INFO", f"处理完成，总耗时: {total_time}")
        log("INFO", f"总文件数: {total_count}, 成功: {success_count}, 失败: {failed_count}, 识别率: {success_rate}")

        stats = save_summary(results)
        if stats:
            log("INFO", "统计信息已保存到summary文件夹")

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
        save_summary(results)

    @QtCore.pyqtSlot()
    def on_processing_stopped(self):
        """
        处理线程停止信号
        """
        try:
            log("INFO", "处理已停止")
            self.processing = False
            self.pushButton_start.setEnabled(True)
            self.pushButton_start.setText("开始分类")
            # 清理线程资源
            if self.processing_thread:
                self.processing_thread = None
        except Exception as e:
            log("ERROR", f"处理停止信号失败: {str(e)}")

    @QtCore.pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        try:
            log("ERROR", f"处理线程错误: {error_msg}")
            QMessageBox.critical(self, "处理错误", error_msg)
            self.processing = False
            self.pushButton_start.setEnabled(True)
            self.pushButton_start.setText("开始分类")
        except Exception as e:
            log("ERROR", f"处理错误信号失败: {str(e)}")

    def minimize_window(self):
        try:
            log("INFO", "窗口最小化")
            self.showMinimized()
        except Exception as e:
            log("ERROR", f"最小化窗口失败: {str(e)}")

    def close_application(self):
        try:
            if self.processing:
                reply = QMessageBox.question(
                    self, "确认关闭",
                    "当前正在处理文件，关闭将终止处理过程。\n确定要关闭吗?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return

                if self.processing_thread and self.processing_thread.isRunning():
                    log("WARNING", "应用程序关闭前停止处理线程")
                    self.processing_thread.stop()
                    import time
                    start_time = time.time()
                    while self.processing_thread.isRunning() and (time.time() - start_time) < 5:
                        QApplication.processEvents()
                        time.sleep(0.1)
                    if self.processing_thread.isRunning():
                        log("ERROR", "无法正常停止处理线程，强制退出")

            log("INFO", "应用程序即将关闭")
            QApplication.quit()
        except Exception as e:
            log("ERROR", f"关闭应用程序失败: {str(e)}")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        from utils import log

        log("ERROR", f"应用程序启动失败: {str(e)}")
        sys.exit(1)