import json
import os
import winreg
import hashlib
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, \
    QPushButton, QHBoxLayout, QWidget

from Ui_SettingWindow import Ui_SettingWindow
from utils import get_resource_path


class SettingWindow(QMainWindow, Ui_SettingWindow):
    CONFIG_FILE = get_resource_path("resources/Config.json")
    REG_PATH = r"SOFTWARE\RailwayOCR"
    REG_PWD_KEY = "PasswordHash"

    def __init__(self):
        super().__init__()
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
            else:
                config = {}
                QMessageBox.information(self, "提示", "首次启动，使用默认配置模板")
            self.lineEdit_ACCESS_KEY_ID.setText(config.get("ACCESS_KEY_ID", ""))
            self.lineEdit_ACCESS_KEY_SECRET.setText(config.get("ACCESS_KEY_SECRET", ""))
            self.lineEdit_ENDPOINT.setText(config.get("ENDPOINT", ""))
            self.lineEdit_BUCKET_NAME.setText(config.get("BUCKET_NAME", ""))
            self.lineEdit_COZE_API_KEY.setText(config.get("COZE_API_KEY", ""))
            self.lineEdit_WORKFLOW_ID.setText(config.get("WORKFLOW_ID", ""))
            self.spinBox_CONCURRENCY.setValue(config.get("CONCURRENCY", 4))
            self.spinBox_RETRY_TIMES.setValue(config.get("RETRY_TIMES", 3))
            self.lineEdit_RE.setText(config.get("RE", r"^[A-K][1-7]$"))
            self.textEdit_PROMPT.setPlainText(config.get("PROMPT", ""))
        except Exception as e:
            QMessageBox.critical(self, "配置加载失败", f"读取配置时出错：{str(e)}")
            self._load_default_values()

    def _load_default_values(self):
        self.lineEdit_ACCESS_KEY_ID.setText("")
        self.lineEdit_ACCESS_KEY_SECRET.setText("")
        self.lineEdit_ENDPOINT.setText("oss-cn-hangzhou.aliyuncs.com")
        self.lineEdit_BUCKET_NAME.setText("")
        self.lineEdit_COZE_API_KEY.setText("")
        self.lineEdit_WORKFLOW_ID.setText("")
        self.spinBox_CONCURRENCY.setValue(4)
        self.spinBox_RETRY_TIMES.setValue(3)
        self.lineEdit_RE.setText(r"^[A-K][1-7]$")
        self.textEdit_PROMPT.setPlainText("请识别图像中卡片上的红色标签，格式为A-K+1-7（如A1），直接返回结果或'识别失败'")

    def validate_required_fields(self):
        required_fields = [
            ("ACCESS_KEY_ID", self.lineEdit_ACCESS_KEY_ID),
            ("ACCESS_KEY_SECRET", self.lineEdit_ACCESS_KEY_SECRET),
            ("ENDPOINT", self.lineEdit_ENDPOINT),
            ("BUCKET_NAME", self.lineEdit_BUCKET_NAME),
            ("COZE_API_KEY", self.lineEdit_COZE_API_KEY),
            ("WORKFLOW_ID", self.lineEdit_WORKFLOW_ID),
            ("RE（正则表达式）", self.lineEdit_RE)
        ]
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
        return True

    def save_config(self):
        if not self.validate_required_fields():
            return
        try:
            config = {
                "ACCESS_KEY_ID": self.lineEdit_ACCESS_KEY_ID.text().strip(),
                "ACCESS_KEY_SECRET": self.lineEdit_ACCESS_KEY_SECRET.text().strip(),
                "ENDPOINT": self.lineEdit_ENDPOINT.text().strip(),
                "BUCKET_NAME": self.lineEdit_BUCKET_NAME.text().strip(),
                "EXPIRES_IN": 1800,
                "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
                "LOG_FILE": "ocr_processing.log",
                "CONCURRENCY": self.spinBox_CONCURRENCY.value(),
                "RETRY_TIMES": self.spinBox_RETRY_TIMES.value(),
                "COZE_API_KEY": self.lineEdit_COZE_API_KEY.text().strip(),
                "WORKFLOW_ID": self.lineEdit_WORKFLOW_ID.text().strip(),
                "SUMMARY_DIR": "summary",
                "MAX_REQUESTS_PER_MINUTE": 300,
                "RATE_LIMIT_BUFFER": 0.9,
                "OPTIMAL_RATE": 270,
                "IMAGE_PROCESSING_TIMEOUT": 30,
                "RE": self.lineEdit_RE.text().strip(),
                "PROMPT": self.textEdit_PROMPT.toPlainText().strip()
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "保存成功", "配置已成功保存")
            self.close()
        except Exception as e:
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
            if not password:
                try:
                    winreg.DeleteValue(key, self.REG_PWD_KEY)
                except FileNotFoundError:
                    pass
            else:
                pwd_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
                winreg.SetValueEx(key, self.REG_PWD_KEY, 0, winreg.REG_SZ, pwd_hash)
            winreg.CloseKey(key)
            return True
        except OSError:
            return False


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = SettingWindow()
    window.show()
    sys.exit(app.exec())