import bcrypt
import keyring
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon
from utils import get_resource_path, log, log_print


class PasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("请输入密码")
        self.setWindowIcon(QIcon(get_resource_path("resources/img/icon.ico")))
        self.setFixedSize(350, 180)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f7;
                border-radius: 8px;
            }
            QLabel {
                color: #333333;
                font-size: 18px;
                font-family: "Microsoft YaHei UI";
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007aff;
                outline: none;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#okButton {
                background-color: #007aff;
                color: white;
                border: none;
            }
            QPushButton#okButton:hover {
                background-color: #0066cc;
            }
            QPushButton#cancelButton {
                background-color: #f5f5f7;
                color: #333333;
                border: 1px solid #d1d1d6;
            }
            QPushButton#cancelButton:hover {
                background-color: #ebebef;
            }
        """)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        title_label = QtWidgets.QLabel("请输入启动密码", self)
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        self.password_edit = QtWidgets.QLineEdit(self)
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("输入密码")
        self.password_edit.setMinimumHeight(36)
        main_layout.addWidget(self.password_edit)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)

        self.cancel_button = QtWidgets.QPushButton("取消", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setMinimumHeight(34)

        self.ok_button = QtWidgets.QPushButton("确定", self)
        self.ok_button.setObjectName("okButton")
        self.ok_button.setMinimumHeight(34)
        self.ok_button.setDefault(True)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        main_layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.password_edit.returnPressed.connect(self.accept)

        self.password_edit.setFocus()

    def get_password(self):
        return self.password_edit.text()


def verify_password(password):
    try:
        stored_value = keyring.get_password("RailwayOCR", "admin")
        if not stored_value:
            log("ERROR", "未设置启动密码")
            log_print("[安全模块] 密钥环中未找到存储的密码哈希")
            return False

        if ':' not in stored_value:
            log("ERROR", "密码格式错误")
            log_print("[安全模块] 存储格式应为'salt:hash'，实际为:{stored_value}")
            return False
        salt_hex, hash_hex = stored_value.split(':', 1)

        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)

        result = bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        if not result:
            log("WARNING", "密码不正确，请重试")
        return result
    except (keyring.errors.KeyringError, ValueError, TypeError) as e:
        log("ERROR", "密码验证失败")
        log_print(f"[安全模块] 验证异常: {str(e)} (类型:{type(e).__name__})")
        return False


def has_password():
    try:
        stored_value = keyring.get_password("RailwayOCR", "admin")
        return bool(stored_value)
    except (keyring.errors.KeyringError, OSError) as e:
        log_print(f"[安全模块] 密码检查异常: {str(e)} (类型:{type(e).__name__})")
        return False


def save_password(password):
    try:
        # 生成salt并哈希密码
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # 将salt和hash以十六进制格式存储
        stored_value = f"{salt.hex()}:{password_hash.hex()}"
        keyring.set_password("RailwayOCR", "admin", stored_value)
        log("INFO", "密码设置成功")
        log_print("[安全模块] 密码已成功设置并存储到密钥环")
        return True
    except (keyring.errors.KeyringError, ValueError, TypeError) as e:
        log("ERROR", "密码设置失败")
        log_print(f"[安全模块] 设置密码异常: {str(e)} (类型:{type(e).__name__})")
        return False


def delete_password():
    try:
        keyring.delete_password("RailwayOCR", "admin")
        log("INFO", "密码已删除")
        log_print("[安全模块] 密码已从密钥环中删除")
        return True
    except (keyring.errors.KeyringError, ValueError, TypeError) as e:
        log("ERROR", "密码删除失败")
        log_print(f"[安全模块] 删除密码异常: {str(e)} (类型:{type(e).__name__})")
        return False