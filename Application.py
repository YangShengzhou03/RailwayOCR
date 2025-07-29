import sys
import traceback
import winreg
import hashlib

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from MainWindow import MainWindow


class PasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("请输入密码")
        self.setFixedSize(300, 150)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("请输入启动密码：", self)
        layout.addWidget(label)

        self.password_edit = QtWidgets.QLineEdit(self)
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        button_layout = QtWidgets.QHBoxLayout()
        self.ok_button = QtWidgets.QPushButton("确定", self)
        self.cancel_button = QtWidgets.QPushButton("取消", self)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.password_edit.returnPressed.connect(self.accept)

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

    if has_password():
        dialog = PasswordDialog()
        while True:
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return 1

            password = dialog.get_password()
            if verify_password(password):
                break
            else:
                QtWidgets.QMessageBox.warning(None, "密码错误", "输入的密码不正确，请重试")

    window = MainWindow()
    window.setWindowTitle("LeafView Railway")

    if hasattr(window, 'centerOnScreen'):
        window.centerOnScreen()

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
                    if widget.windowState() & QtCore.Qt.WindowState.WindowMinimized:
                        widget.setWindowState(
                            widget.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
                    widget.activateWindow()
                    widget.raise_()
                    break

    socket.disconnectFromServer()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        sys.__stderr__.write(f"Fatal error: {str(e)}\n")
        sys.__stderr__.write(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)
