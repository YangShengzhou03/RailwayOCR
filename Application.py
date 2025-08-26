import sys
import time

import bcrypt
import keyring
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from MainWindow import MainWindow
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


def center_window(window):
    qr = window.frameGeometry()
    cp = QtWidgets.QApplication.primaryScreen().availableGeometry().center()
    qr.moveCenter(cp)
    window.move(qr.topLeft())


def main():
    server = QLocalServer()
    socket_name = "LeafView_Railway_Server_Socket"

    client_socket = QLocalSocket()
    client_socket.connectToServer(socket_name)

    try:
        if client_socket.waitForConnected(500):
            client_socket.write(b"bring_to_front")
            client_socket.waitForBytesWritten()
            log("INFO", "程序已在运行，正在切换到前台窗口")
            return 1
    finally:
        client_socket.disconnectFromServer()

    QLocalServer.removeServer(socket_name)
    if not server.listen(socket_name):
        log("ERROR", "程序启动失败，可能已有实例在运行")
        log_print(f"[本地服务] 服务器启动失败: {server.errorString()}")
        return 1

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
            result = verify_password(password)
            dialog.password_edit.clear()
            password_bytes = bytearray(password.encode('utf-8'))
            for i in range(len(password_bytes)):
                password_bytes[i] = 0
            del password_bytes
            if result:
                log("INFO", "密码验证成功")
                break
            else:
                attempts += 1
                remaining = max_attempts - attempts
                delay = 2 **attempts
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

    center_window(window)

    window.show()
    exit_code = app.exec()

    server.close()
    QLocalServer.removeServer(socket_name)

    return exit_code


def handle_incoming_connection(server):
    socket = server.nextPendingConnection()

    try:
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
    except Exception as e:
        log("ERROR", f"处理连接时出错: {str(e)}")
    finally:
        socket.disconnectFromServer()
        socket.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ImportError) as e:
        sys.__stderr__.write(f"Fatal error: {str(e)}\n")
        sys.__stderr__.write(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)
