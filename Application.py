import sys
import time
import traceback

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from main_window import MainWindow
from security import PasswordDialog, verify_password, has_password
from utils import get_resource_path, log_print


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
            return 1
    except Exception:
        pass

    client_socket.disconnectFromServer()

    QLocalServer.removeServer(socket_name)
    if not server.listen(socket_name):
        log_print(f"[Application] 服务器启动失败: {server.errorString()}")
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
                return 1

            password = dialog.get_password()
            result = verify_password(password)
            dialog.password_edit.clear()
            password_bytes = bytearray(password.encode('utf-8'))
            for i in range(len(password_bytes)):
                password_bytes[i] = 0
            del password_bytes
            if result:
                break
            attempts += 1
            remaining = max_attempts - attempts
            delay = 2 ** attempts
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
                for widget in enumerate(QtWidgets.QApplication.topLevelWidgets()):
                    if isinstance(widget[1], QtWidgets.QMainWindow) and widget[1].windowTitle() == "LeafView Railway":
                        widget[1].setWindowState(
                            widget[1].windowState() &
                            ~QtCore.Qt.WindowState.WindowMinimized |
                            QtCore.Qt.WindowState.WindowActive
                        )
                        widget[1].activateWindow()
                        widget[1].raise_()
                        widget[1].setStyleSheet("")
                        QtCore.QTimer.singleShot(300, lambda w=widget[1]: w.setStyleSheet(""))
                        break
    except (OSError, RuntimeError) as e:
        pass
    finally:
        socket.disconnectFromServer()
        socket.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        sys.__stderr__.write(f"Unexpected fatal error: {str(e)}")
        sys.__stderr__.write(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        sys.exit(1)
