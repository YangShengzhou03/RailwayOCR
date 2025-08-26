import json
import os
import re

from PyQt6 import QtGui
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication

import utils
from Ui_SettingWindow import Ui_SettingWindow
from security import save_password, delete_password
from utils import MODE_ALI, MODE_BAIDU
from utils import get_resource_path, log, log_print, load_config


class SettingWindow(QMainWindow, Ui_SettingWindow):
    """设置窗口类，用于配置应用程序参数和密码管理。

    提供界面用于配置API密钥、并发数、重试次数、正则表达式等参数，
    并支持密码设置功能。
    """
    def __init__(self):
        super().__init__()
        self.config_file = os.path.join(get_resource_path("_internal/Config.json"))
        self.reg_path = r"SOFTWARE\RailwayOCR"
        self.reg_pwd_key = "PasswordHash"
        self.setupUi(self)
        self.setWindowTitle('RailwayOCR Setting')
        self.pushButton_save.clicked.connect(self.save_config)
        self.pushButton_Password.clicked.connect(self.handle_password)
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.load_and_populate_config()

    def load_and_populate_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._validate_config(config)
            else:
                config = {}
                log("INFO", "未找到配置文件，已自动创建默认配置")
                if not os.path.exists(os.path.dirname(self.config_file)):
                    try:
                        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                        log("INFO", "已创建配置文件夹: " + os.path.basename(os.path.dirname(self.config_file)))
                    except (OSError, FileNotFoundError) as e:
                        log("ERROR", f"无法创建配置文件夹: {str(e)}")
                        QMessageBox.critical(self, "配置错误", f"创建配置目录失败: {str(e)}")
                QMessageBox.information(self, "提示", "首次启动，使用默认配置模板")
            self.lineEdit_BAIDU_API_KEY.setText(config.get("BAIDU_API_KEY", ""))
            self.lineEdit_BAIDU_SECRET_KEY.setText(config.get("BAIDU_SECRET_KEY", ""))
            self.lineEdit_ALI_APPCODE.setText(config.get("ALI_APPCODE", ""))
            concurrency_value = config.get("CONCURRENCY", 4)
            self.spinBox_CONCURRENCY.setValue(concurrency_value)
            self.spinBox_RETRY_TIMES.setValue(config.get("RETRY_TIMES", 3))
            self.lineEdit_RE.setText(config.get("RE", r"^[A-K][1-7]$"))
            mode_index = config.get("MODE_INDEX", 0)
            if 0 <= mode_index < self.comboBox_mode.count():
                self.comboBox_mode.setCurrentIndex(mode_index)
        except json.JSONDecodeError:
            log("ERROR", f"配置文件格式有误，请检查JSON语法")
            self._load_default_values()
        except (IOError, OSError) as e:
            log("ERROR", f"读取配置时出错: {str(e)}")
            QMessageBox.critical(self, "配置加载失败", f"读取配置时出错：{str(e)}")
            self._load_default_values()

    def _load_default_values(self):
        """加载默认配置值到UI控件."""
        self.spinBox_CONCURRENCY.setValue(4)
        self.spinBox_RETRY_TIMES.setValue(3)
        self.lineEdit_RE.setText(r".*")
        self.comboBox_mode.setCurrentIndex(0)

    def validate_required_fields(self):
        """验证必填字段是否符合要求。

        检查当前选择的模式下所需的API密钥、正则表达式格式、并发数和重试次数范围是否有效。

        Returns:
            bool: 所有验证通过返回True，否则返回False并显示错误提示
        """
        mode_index = self.comboBox_mode.currentIndex()
        required_fields = [
            ("RE（正则表达式）", self.lineEdit_RE)
        ]

        if mode_index == MODE_ALI:
            required_fields.extend([
                ("ALI_APPCODE", self.lineEdit_ALI_APPCODE)
            ])
        elif mode_index == MODE_BAIDU:
            required_fields.extend([
                ("BAIDU_API_KEY", self.lineEdit_BAIDU_API_KEY),
                ("BAIDU_SECRET_KEY", self.lineEdit_BAIDU_SECRET_KEY)
            ])

        empty_fields = [label for label, widget in required_fields if not widget.text().strip()]
        if empty_fields:
            QMessageBox.warning(
                self, "输入不完整",
                "以下必填字段不能为空：\n" + "\n".join(empty_fields)
            )
            if empty_fields:
                for label, widget in required_fields:
                    if not widget.text().strip():
                        widget.setFocus()
                        break
            return False

        # 移除不必要的else语句
        try:
            re.compile(self.lineEdit_RE.text().strip())
        except re.error as e:
            QMessageBox.warning(
                self, "正则表达式错误",
                f"无效的正则表达式: {self.lineEdit_RE.text().strip()}\n{str(e)}"
            )
            self.lineEdit_RE.setFocus()
            return False

        if self.spinBox_CONCURRENCY.value() <= 0 or self.spinBox_CONCURRENCY.value() > 32:
            QMessageBox.warning(
                self, "并发数范围错误",
                "并发数必须在1-32之间"
            )
            self.spinBox_CONCURRENCY.setFocus()
            return False

        if self.spinBox_RETRY_TIMES.value() < 3 or self.spinBox_RETRY_TIMES.value() > 30:
            QMessageBox.warning(
                self, "重试次数范围错误",
                "重试次数必须在3-30之间"
            )
            self.spinBox_RETRY_TIMES.setFocus()
            return False

        return True

    def _validate_config(self, config):
        """验证配置字典的数据类型和取值范围。

        Args:
            config (dict): 配置字典

        Raises:
            ValueError: 当配置项不符合要求时抛出
        """
        if "RE" in config:
            if not isinstance(config["RE"], str):
                raise ValueError("RE必须是字符串")
            try:
                re.compile(config["RE"])
            except re.error as e:
                raise ValueError(f"正则表达式无效: {config['RE']}\n{str(e)}") from e

        if "CONCURRENCY" in config:
            if not isinstance(config["CONCURRENCY"], int):
                raise ValueError("CONCURRENCY必须是整数")
            if config["CONCURRENCY"] <= 0 or config["CONCURRENCY"] > 32:
                raise ValueError("CONCURRENCY必须在1-32之间")

        if "RETRY_TIMES" in config:
            if not isinstance(config["RETRY_TIMES"], int):
                raise ValueError("RETRY_TIMES必须是整数")
            if config["RETRY_TIMES"] < 0 or config["RETRY_TIMES"] > 30:
                raise ValueError("RETRY_TIMES必须在0-30之间")

        if "BAIDU_API_KEY" in config and not isinstance(config["BAIDU_API_KEY"], str):
            raise ValueError("BAIDU_API_KEY必须是字符串")

        if "BAIDU_SECRET_KEY" in config and not isinstance(config["BAIDU_SECRET_KEY"], str):
            raise ValueError("BAIDU_SECRET_KEY必须是字符串")

        if "ALI_APPCODE" in config and not isinstance(config["ALI_APPCODE"], str):
            raise ValueError("ALI_APPCODE必须是字符串")

        if "MODE_INDEX" in config:
            if not isinstance(config["MODE_INDEX"], int):
                raise ValueError("MODE_INDEX必须是整数")
            if config["MODE_INDEX"] < 0 or config["MODE_INDEX"] > MODE_BAIDU:
                raise ValueError("MODE_INDEX必须在0-3之间")

    def load_config(self):
        """加载配置文件并更新UI控件。"""
        self.load_and_populate_config()

    def save_config(self):
        """保存当前UI配置到文件并应用更改"""
        try:
            if not self.validate_required_fields():
                return

            config = {
                'BAIDU_API_KEY': self.lineEdit_BAIDU_API_KEY.text(),
                'BAIDU_SECRET_KEY': self.lineEdit_BAIDU_SECRET_KEY.text(),
                'ALI_APPCODE': self.lineEdit_ALI_APPCODE.text(),
                'CONCURRENCY': self.spinBox_CONCURRENCY.value(),
                'RETRY_TIMES': self.spinBox_RETRY_TIMES.value(),
                'RE': self.lineEdit_RE.text(),
                'MODE_INDEX': self.comboBox_mode.currentIndex()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            load_config.cache_clear()
            # 移除未使用变量 new_config
            if hasattr(utils.main_window, 'on_config_updated'):
                utils.main_window.on_config_updated()

            QMessageBox.information(self, "保存成功", "配置已成功保存！")
            log("INFO", "设置已保存并生效")
            self.close()

        except (IOError, OSError, PermissionError) as e:
            # 调整异常捕获顺序，具体异常在前
            log("ERROR", f"保存设置失败: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错：{str(e)}窗口将保持打开，您可以重试操作。")
        except ValueError as ve:
            log("ERROR", f"配置验证失败: {str(ve)}")
            QMessageBox.warning(self, "配置无效", str(ve))

    def show_event(self, event):
        """窗口显示事件处理，加载最新配置"""
        self.load_and_populate_config()
        super().showEvent(event)

    def _save_password(self, password):
        try:
            if password:
                return save_password(password)
            else:
                return delete_password()
        except (OSError, RuntimeError) as e:
            log_print(f"保存密码失败: {str(e)}")
            QMessageBox.critical(None, "密码保存错误", f"无法保存密码到系统凭据管理器: {str(e)}")
            return False

    def handle_password(self):
        """处理密码设置按钮点击事件，打开密码对话框并保存或删除密码"""


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = SettingWindow()
    window.show()
    sys.exit(app.exec())

