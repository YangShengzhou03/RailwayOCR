import sys
import traceback

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from MainWindow import MainWindow


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
