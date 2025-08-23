import hashlib
import sys
import traceback
import winreg

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from MainWindow import MainWindow
from utils import get_resource_path


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
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\RailwayOCR")
        stored_hash, _ = winreg.QueryValueEx(key, "PasswordHash")
        winreg.CloseKey(key)

        input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return input_hash == stored_hash
    except (FileNotFoundError, OSError):
        return False


def has_password():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\RailwayOCR")
        winreg.QueryValueEx(key, "PasswordHash")
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def main():
    server = QLocalServer()
    socket_name = "LeafView_Railway_Server_Socket"

    client_socket = QLocalSocket()
    client_socket.connectToServer(socket_name)

    if client_socket.waitForConnected(500):
        client_socket.write(b"bring_to_front")
        client_socket.waitForBytesWritten()
        client_socket.disconnectFromServer()
        return 1

    QLocalServer.removeServer(socket_name)
    if not server.listen(socket_name):
        return 1

    server.newConnection.connect(lambda: handle_incoming_connection(server))

    shared_memory = QtCore.QSharedMemory("LeafView_Railway_Server")
    if shared_memory.attach():
        return 1

    if not shared_memory.create(1):
        return 1

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
        while True:
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return 1

            password = dialog.get_password()
            if verify_password(password):
                break
            else:
                msg_box = QtWidgets.QMessageBox(
                    QtWidgets.QMessageBox.Icon.Warning,
                    "密码错误",
                    "输入的密码不正确，请重试",
                    parent=None
                )
                msg_box.setStyleSheet("""
                    QPushButton {
                        min-width: 80px;
                    }
                """)
                msg_box.exec()

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
    shared_memory.detach()

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
    except Exception as e:
        sys.__stderr__.write(f"Fatal error: {str(e)}\n")
        sys.__stderr__.write(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)