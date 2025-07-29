import json
import os

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication

from Ui_SettingWindow import Ui_SettingWindow
from utils import get_resource_path


class SettingWindow(QMainWindow, Ui_SettingWindow):
    CONFIG_FILE = "Config.json"  # 配置文件路径

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('RailwayOCR Setting')  # 统一窗口标题

        # 绑定控件事件
        self.pushButton_save.clicked.connect(self.save_config)
        self.pushButton_Password.clicked.connect(self.handle_password)
        self.toolButton_close.clicked.connect(self.close)  # 关闭窗口按钮

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))

        # 加载配置并填充界面
        self.load_and_populate_config()

    def load_and_populate_config(self):
        """加载配置文件并填充到界面控件"""
        try:
            # 读取配置文件
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                # 配置文件不存在时使用空字典
                config = {}
                QMessageBox.information(self, "提示", "首次启动，使用默认配置模板")

            # 填充界面控件（严格对应UI中的控件）
            self.lineEdit_ACCESS_KEY_ID.setText(config.get("ACCESS_KEY_ID", ""))
            self.lineEdit_ACCESS_KEY_SECRET.setText(config.get("ACCESS_KEY_SECRET", ""))
            self.lineEdit_ENDPOINT.setText(config.get("ENDPOINT", ""))
            self.lineEdit_BUCKET_NAME.setText(config.get("BUCKET_NAME", ""))
            self.lineEdit_COZE_API_KEY.setText(config.get("COZE_API_KEY", ""))
            self.lineEdit_WORKFLOW_ID.setText(config.get("WORKFLOW_ID", ""))

            # 数值控件设置（带默认值和范围限制）
            self.spinBox_CONCURRENCY.setValue(config.get("CONCURRENCY", 4))
            self.spinBox_RETRY_TIMES.setValue(config.get("RETRY_TIMES", 3))
            self.lineEdit_RE.setText(config.get("RE", r"^[A-K][1-7]$"))
            self.textEdit_PROMPT.setPlainText(config.get("PROMPT", ""))

        except Exception as e:
            QMessageBox.critical(self, "配置加载失败", f"读取配置时出错：{str(e)}")
            # 加载失败时填充默认值
            self._load_default_values()

    def _load_default_values(self):
        """配置加载失败时填充默认值"""
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
        """验证必填字段是否为空"""
        # 定义必填字段（标签文本 -> 控件）
        required_fields = [
            ("ACCESS_KEY_ID", self.lineEdit_ACCESS_KEY_ID),
            ("ACCESS_KEY_SECRET", self.lineEdit_ACCESS_KEY_SECRET),
            ("ENDPOINT", self.lineEdit_ENDPOINT),
            ("BUCKET_NAME", self.lineEdit_BUCKET_NAME),
            ("COZE_API_KEY", self.lineEdit_COZE_API_KEY),
            ("WORKFLOW_ID", self.lineEdit_WORKFLOW_ID),
            ("RE（正则表达式）", self.lineEdit_RE)
        ]

        # 检查空字段
        empty_fields = [label for label, widget in required_fields if not widget.text().strip()]
        if empty_fields:
            QMessageBox.warning(
                self, "输入不完整",
                "以下必填字段不能为空：\n" + "\n".join(empty_fields)
            )
            # 聚焦到第一个空字段
            if empty_fields:
                for label, widget in required_fields:
                    if not widget.text().strip():
                        widget.setFocus()
                        break
            return False
        return True

    def save_config(self):
        """保存配置到JSON文件"""
        # 验证必填字段
        if not self.validate_required_fields():
            return

        try:
            # 构建配置字典（严格对应UI控件和原始Config.json结构）
            config = {
                "ACCESS_KEY_ID": self.lineEdit_ACCESS_KEY_ID.text().strip(),
                "ACCESS_KEY_SECRET": self.lineEdit_ACCESS_KEY_SECRET.text().strip(),
                "ENDPOINT": self.lineEdit_ENDPOINT.text().strip(),
                "BUCKET_NAME": self.lineEdit_BUCKET_NAME.text().strip(),
                "EXPIRES_IN": 1800,  # 界面无此控件，保持默认值
                "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],  # 固定值
                "LOG_FILE": "ocr_processing.log",  # 界面无此控件，保持默认值
                "CONCURRENCY": self.spinBox_CONCURRENCY.value(),
                "RETRY_TIMES": self.spinBox_RETRY_TIMES.value(),
                "COZE_API_KEY": self.lineEdit_COZE_API_KEY.text().strip(),
                "WORKFLOW_ID": self.lineEdit_WORKFLOW_ID.text().strip(),
                "SUMMARY_DIR": "summary",  # 界面无此控件，保持默认值
                "MAX_REQUESTS_PER_MINUTE": 300,  # 界面无此控件，保持默认值
                "RATE_LIMIT_BUFFER": 0.9,  # 界面无此控件，保持默认值
                "OPTIMAL_RATE": 270,  # 界面无此控件，保持默认值
                "IMAGE_PROCESSING_TIMEOUT": 30,  # 界面无此控件，保持默认值
                "RE": self.lineEdit_RE.text().strip(),
                "PROMPT": self.textEdit_PROMPT.toPlainText().strip()
            }

            # 保存到文件
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "保存成功", "配置已成功保存")
            self.close()  # 保存后关闭窗口

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错：{str(e)}")

    def handle_password(self):
        """处理启动密码按钮点击事件"""
        QMessageBox.information(
            self, "启动密码",
            "启动密码功能说明：\n设置后，下次启动软件需输入密码验证。\n当前功能暂未启用。"
        )


if __name__ == "__main__":
    # 测试代码
    import sys

    app = QApplication(sys.argv)
    window = SettingWindow()
    window.show()
    sys.exit(app.exec())