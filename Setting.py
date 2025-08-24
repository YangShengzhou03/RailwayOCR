import json
import os
import winreg
import hashlib
import re
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, \
    QPushButton, QHBoxLayout, QWidget

from Ui_SettingWindow import Ui_SettingWindow
from utils import get_resource_path, log, log_print


class SettingWindow(QMainWindow, Ui_SettingWindow):
    def __init__(self):
        super().__init__()
        # 配置文件路径
        self.CONFIG_FILE = os.path.join(get_resource_path(), "resources", "Config.json")
        self.REG_PATH = r"SOFTWARE\RailwayOCR"
        self.REG_PWD_KEY = "PasswordHash"
        self.setupUi(self)
        self.setWindowTitle('RailwayOCR Setting')
        self.pushButton_save.clicked.connect(self.save_config)
        self.pushButton_Password.clicked.connect(self.handle_password)
        self.toolButton_close.clicked.connect(self.close)
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.load_and_populate_config()



    def load_and_populate_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 验证配置
                self._validate_config(config)
            else:
                config = {}
                log("INFO", "配置文件不存在，使用默认配置")
                # 只在首次创建配置时显示提示
                if not os.path.exists(os.path.dirname(self.CONFIG_FILE)):
                    try:
                        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
                        log("INFO", f"创建配置目录: {os.path.dirname(self.CONFIG_FILE)}")
                    except Exception as e:
                        log("ERROR", f"创建配置目录失败: {str(e)}")
                        QMessageBox.critical(self, "配置错误", f"创建配置目录失败: {str(e)}")
                QMessageBox.information(self, "提示", "首次启动，使用默认配置模板")
            self.lineEdit_ACCESS_KEY_ID.setText(config.get("ACCESS_KEY_ID", ""))
            self.lineEdit_ACCESS_KEY_SECRET.setText(config.get("ACCESS_KEY_SECRET", ""))
            self.lineEdit_ENDPOINT.setText(config.get("ENDPOINT", "oss-cn-hangzhou.aliyuncs.com"))
            self.lineEdit_BUCKET_NAME.setText(config.get("BUCKET_NAME", ""))
            self.lineEdit_DOUYIN_API_KEY.setText(config.get("DOUYIN_API_KEY", ""))
            self.lineEdit_ALI_CODE.setText(config.get("ALI_CODE", ""))
            self.spinBox_CONCURRENCY.setValue(config.get("CONCURRENCY", 4))
            self.spinBox_RETRY_TIMES.setValue(config.get("RETRY_TIMES", 3))
            self.lineEdit_RE.setText(config.get("RE", r"^[A-K][1-7]$"))
            mode_index = config.get("MODE_INDEX", 0)
            if 0 <= mode_index < self.comboBox_mode.count():
                self.comboBox_mode.setCurrentIndex(mode_index)
        except json.JSONDecodeError:
            log("ERROR", f"配置文件格式错误: {self.CONFIG_FILE}")
            QMessageBox.critical(self, "配置加载失败", f"配置文件格式错误: {self.CONFIG_FILE}")
            self._load_default_values()
        except Exception as e:
            log("ERROR", f"配置加载失败: {str(e)}")
            QMessageBox.critical(self, "配置加载失败", f"读取配置时出错：{str(e)}")
            self._load_default_values()

    def _load_default_values(self):
        self.lineEdit_ACCESS_KEY_ID.setText("")
        self.lineEdit_ACCESS_KEY_SECRET.setText("")
        self.lineEdit_ENDPOINT.setText("oss-cn-hangzhou.aliyuncs.com")
        self.lineEdit_BUCKET_NAME.setText("")
        self.lineEdit_DOUYIN_API_KEY.setText("")
        self.lineEdit_ALI_CODE.setText("")
        self.spinBox_CONCURRENCY.setValue(4)
        self.spinBox_RETRY_TIMES.setValue(3)
        self.lineEdit_RE.setText(r"^[A-K][1-7]$")
        self.comboBox_mode.setCurrentIndex(0)

    def validate_required_fields(self):
        mode_index = self.comboBox_mode.currentIndex()
        required_fields = [
            ("RE（正则表达式）", self.lineEdit_RE)
        ]

        if mode_index == 0:
            required_fields.extend([
                ("ALI_CODE", self.lineEdit_ALI_CODE),
                ("ACCESS_KEY_ID", self.lineEdit_ACCESS_KEY_ID),
                ("ACCESS_KEY_SECRET", self.lineEdit_ACCESS_KEY_SECRET),
                ("ENDPOINT", self.lineEdit_ENDPOINT),
                ("BUCKET_NAME", self.lineEdit_BUCKET_NAME)
            ])
        elif mode_index == 2:
            required_fields.extend([
                ("DOUYIN_API_KEY", self.lineEdit_DOUYIN_API_KEY)
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

        # 验证正则表达式
        try:
            re.compile(self.lineEdit_RE.text().strip())
        except re.error:
            QMessageBox.warning(
                self, "正则表达式错误",
                f"无效的正则表达式: {self.lineEdit_RE.text().strip()}\n{str(e)}"
            )
            self.lineEdit_RE.setFocus()
            return False

        return True

    def _validate_config(self, config):
        """
        验证配置的有效性
        """
        # 验证API密钥格式
        if "ACCESS_KEY_ID" in config and not isinstance(config["ACCESS_KEY_ID"], str):
            raise ValueError("ACCESS_KEY_ID必须是字符串")

        if "ACCESS_KEY_SECRET" in config and not isinstance(config["ACCESS_KEY_SECRET"], str):
            raise ValueError("ACCESS_KEY_SECRET必须是字符串")

        if "DOUYIN_API_KEY" in config and not isinstance(config["DOUYIN_API_KEY"], str):
            raise ValueError("DOUYIN_API_KEY必须是字符串")

        # 验证正则表达式
        if "RE" in config:
            try:
                re.compile(config["RE"])
            except re.error as e:
                raise ValueError(f"正则表达式无效: {config['RE']}\n{str(e)}")

        # 验证数值类型
        if "CONCURRENCY" in config and not isinstance(config["CONCURRENCY"], int):
            raise ValueError("CONCURRENCY必须是整数")

        if "RETRY_TIMES" in config and not isinstance(config["RETRY_TIMES"], int):
            raise ValueError("RETRY_TIMES必须是整数")

        # 验证目录路径
        if "SUMMARY_DIR" in config and not isinstance(config["SUMMARY_DIR"], str):
            raise ValueError("SUMMARY_DIR必须是字符串")

    def save_config(self):
        if not self.validate_required_fields():
            return
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            config.update({
                "ACCESS_KEY_ID": self.lineEdit_ACCESS_KEY_ID.text().strip(),
                "ACCESS_KEY_SECRET": self.lineEdit_ACCESS_KEY_SECRET.text().strip(),
                "ENDPOINT": self.lineEdit_ENDPOINT.text().strip(),
                "BUCKET_NAME": self.lineEdit_BUCKET_NAME.text().strip(),
                "CONCURRENCY": self.spinBox_CONCURRENCY.value(),
                "RETRY_TIMES": self.spinBox_RETRY_TIMES.value(),
                "DOUYIN_API_KEY": self.lineEdit_DOUYIN_API_KEY.text().strip(),
                "ALI_CODE": self.lineEdit_ALI_CODE.text().strip(),
                "RE": self.lineEdit_RE.text().strip(),
                "MODE_INDEX": self.comboBox_mode.currentIndex()
            })

            required_defaults = {
                "EXPIRES_IN": 1800,
                "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
                "LOG_FILE": "ocr_processing.log",
                "SUMMARY_DIR": "summary",
                "MAX_REQUESTS_PER_MINUTE": 300,
                "RATE_LIMIT_BUFFER": 0.9,
                "OPTIMAL_RATE": 270,
                "IMAGE_PROCESSING_TIMEOUT": 30
            }
            for key, value in required_defaults.items():
                if key not in config:
                    config[key] = value

            # 验证配置
            self._validate_config(config)

            # 确保目录存在
            try:
                os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
            except Exception as e:
                log("ERROR", f"创建配置目录失败: {str(e)}")
                QMessageBox.critical(self, "保存失败", f"创建配置目录失败: {str(e)}")
                return

            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            log("INFO", f"配置已保存到 {self.CONFIG_FILE}")
            QMessageBox.information(self, "保存成功", "配置已成功保存")
            self.close()
        except json.JSONDecodeError:
            log("ERROR", f"配置数据格式错误")
            QMessageBox.critical(self, "保存失败", "配置数据格式错误")
        except Exception as e:
            log("ERROR", f"保存配置失败: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错：{str(e)}")

    def handle_password(self):
        has_pwd = self._has_password()
        if has_pwd:
            dialog = QDialog(self)
            dialog.setWindowTitle("修改密码")
            dialog.setMinimumWidth(300)
            layout = QVBoxLayout(dialog)

            layout.addWidget(QLabel("请输入当前密码进行验证"))
            current_pwd = QLineEdit()
            current_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(QLabel("当前密码:"))
            layout.addWidget(current_pwd)

            layout.addWidget(QLabel("请设置新密码（为空则取消密码）"))
            new_pwd1 = QLineEdit()
            new_pwd1.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(QLabel("新密码:"))
            layout.addWidget(new_pwd1)

            new_pwd2 = QLineEdit()
            new_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(QLabel("确认新密码:"))
            layout.addWidget(new_pwd2)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            confirm_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addWidget(btn_widget)

            confirm_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if not self._verify_password(current_pwd.text()):
                    QMessageBox.warning(self, "验证失败", "当前密码不正确")
                    return
                if new_pwd1.text() != new_pwd2.text():
                    QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
                    return
                if new_pwd1.text() and len(new_pwd1.text()) < 4:
                    QMessageBox.warning(self, "密码过短", "密码长度至少4个字符")
                    return
                if self._save_password(new_pwd1.text()):
                    msg = "密码已取消" if not new_pwd1.text() else "密码已更新"
                    QMessageBox.information(self, "成功", msg)
                else:
                    QMessageBox.critical(self, "失败", "密码修改失败")
        else:
            dialog = QDialog(self)
            dialog.setWindowTitle("设置密码")
            dialog.setMinimumWidth(300)
            layout = QVBoxLayout(dialog)

            layout.addWidget(QLabel("请设置启动密码（为空则不设置）"))
            new_pwd1 = QLineEdit()
            new_pwd1.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(QLabel("密码:"))
            layout.addWidget(new_pwd1)

            new_pwd2 = QLineEdit()
            new_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addWidget(QLabel("确认密码:"))
            layout.addWidget(new_pwd2)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            confirm_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            btn_layout.addWidget(confirm_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addWidget(btn_widget)

            confirm_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                if new_pwd1.text() != new_pwd2.text():
                    QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
                    return
                if new_pwd1.text() and len(new_pwd1.text()) < 4:
                    QMessageBox.warning(self, "密码过短", "密码长度至少4个字符")
                    return
                if self._save_password(new_pwd1.text()):
                    msg = "密码已设置" if new_pwd1.text() else "未设置密码"
                    QMessageBox.information(self, "成功", msg)
                else:
                    QMessageBox.critical(self, "失败", "密码设置失败")

    def _has_password(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            winreg.QueryValueEx(key, self.REG_PWD_KEY)
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False

    def _verify_password(self, password):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            stored_hash, _ = winreg.QueryValueEx(key, self.REG_PWD_KEY)
            winreg.CloseKey(key)
            input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return input_hash == stored_hash
        except (FileNotFoundError, OSError):
            return False

    def _save_password(self, password):
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            if password:
                password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
                winreg.SetValueEx(key, self.REG_PWD_KEY, 0, winreg.REG_SZ, password_hash)
            else:
                try:
                    winreg.DeleteValue(key, self.REG_PWD_KEY)
                except FileNotFoundError:
                    pass  # 如果值不存在，忽略错误
            winreg.CloseKey(key)
            return True
        except Exception as e:
            log_print(f"保存密码失败: {str(e)}")
            return False


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = SettingWindow()
    window.show()
    sys.exit(app.exec())
