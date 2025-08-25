import sys
import time
import traceback
import winreg

import bcrypt
import keyring
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from MainWindow import MainWindow
from utils import get_resource_path, log


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
    """
    使用系统凭据管理器验证密码
    :param password: 输入的密码
    :return: 验证是否通过
    """
    try:
        stored_value = keyring.get_password("RailwayOCR", "admin")
        if not stored_value:
            log("ERROR", "未找到存储的密码")
            return False

        # 解析盐值和哈希值
        if ':' not in stored_value:
            log("ERROR", "密码存储格式无效")
            return False
        salt_hex, hash_hex = stored_value.split(':', 1)

        # 转换为字节
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)

        # 使用bcrypt验证密码
        result = bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        if not result:
            log("WARNING", "密码验证失败")
        return result
    except (keyring.errors.KeyringError, ValueError, TypeError) as e:
        log("ERROR", f"密码验证时出错: {str(e)}")
        return False


def has_password():
    """
    检查是否已设置密码
    :return: 是否已设置密码
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\RailwayOCR")
        winreg.QueryValueEx(key, "PasswordHash")
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError) as e:
        log("DEBUG", f"检查密码时出错: {str(e)}")
        return False


def main():
    """
    应用程序主函数
    :return: 退出代码
    """
    # 单实例运行检查
    server = QLocalServer()
    socket_name = "LeafView_Railway_Server_Socket"

    # 尝试连接到已有的服务器
    client_socket = QLocalSocket()
    client_socket.connectToServer(socket_name)

    if client_socket.waitForConnected(500):
        # 如果连接成功，通知已有实例将窗口带到前台
        client_socket.write(b"bring_to_front")
        client_socket.waitForBytesWritten()
        client_socket.disconnectFromServer()
        log("INFO", "应用程序已在运行，切换到前台")
        return 1

    # 移除可能残留的服务器
    QLocalServer.removeServer(socket_name)
    if not server.listen(socket_name):
        log("ERROR", f"无法启动本地服务器: {server.errorString()}")
        return 1

    # 处理新连接
    server.newConnection.connect(lambda: handle_incoming_connection(server))

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("LeafView Railway")
    app.setOrganizationName("LeafView")

    font = QFont()
    font.setFamily("Segoe UI, Microsoft YaHei, sans-serif")
    app.setFont(font)

    app.setStyleSheet("""
        QMessageBox {
            background-color: #f5f5f7;
            border-radius: 8px;
        }
        QMessageBox QLabel {
            color: #333333;
            font-size: 14px;
        }
        QMessageBox QPushButton {
            padding: 6px 16px;
            border-radius: 6px;
            background-color: #007aff;
            color: white;
            border: none;
            font-size: 13px;
        }
        QMessageBox QPushButton:hover {
            background-color: #0066cc;
        }
    """)

    if has_password():
        dialog = PasswordDialog()
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                log("INFO", "用户取消密码输入")
                return 1

            password = dialog.get_password()
            # 安全验证密码
            result = verify_password(password)
            # 清除内存中的密码
            dialog.password_edit.clear()
            password = ' ' * len(password)
            if result:
                log("INFO", "密码验证成功")
                break
            else:
                attempts += 1
                remaining = max_attempts - attempts
                delay = 2 **attempts  # 指数递增延迟：1s, 2s, 4s
                time.sleep(delay)
                msg_box = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Icon.Warning,
                    "密码错误",
                    f"输入的密码不正确，还剩{remaining}次机会，将延迟{delay}秒",
                    parent=None
                )
                msg_box.setStyleSheet("""
                    QPushButton {
                        min-width: 80px;
                    }
                """)
                msg_box.exec()

        if attempts >= max_attempts:
            log("ERROR", "密码验证失败次数过多")
            msg_box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Critical,
                "验证失败",
                "密码错误次数过多，程序将退出",
                parent=None
            )
            msg_box.exec()
            return 1

    window = MainWindow()
    window.setWindowIcon(QIcon(get_resource_path("resources/img/icon.ico")))

    if hasattr(window, 'centerOnScreen'):
        window.centerOnScreen()
    else:
        qr = window.frameGeometry()
        cp = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    window.show()
    exit_code = app.exec()

    server.close()
    QLocalServer.removeServer(socket_name)

    return exit_code


def handle_incoming_connection(server):
    socket = server.nextPendingConnection()

    if socket.waitForReadyRead(1000):
        message = socket.readAll().data().decode('utf-8')
        if message == "bring_to_front":
            for widget in QtWidgets.QApplication.topLevelWidgets():
                if isinstance(widget, QtWidgets.QMainWindow) and widget.windowTitle() == "LeafView Railway":
                    widget.setWindowState(
                        widget.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
                    widget.activateWindow()
                    widget.raise_()
                    widget.setStyleSheet("""
                        QMainWindow {
                            border: 1px solid #007aff;
                        }
                    """)
                    QtCore.QTimer.singleShot(300, lambda: widget.setStyleSheet(""))
                    break

    socket.disconnectFromServer()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ImportError) as e:
        sys.__stderr__.write(f"Fatal error: {str(e)}\n")
        sys.__stderr__.write(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)
