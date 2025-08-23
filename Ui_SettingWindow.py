from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_SettingWindow(object):
    def setupUi(self, SettingWindow):
        SettingWindow.setObjectName("SettingWindow")
        SettingWindow.resize(800, 495)
        self.centralwidget = QtWidgets.QWidget(parent=SettingWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.main_frame = QtWidgets.QFrame(parent=self.centralwidget)
        self.main_frame.setStyleSheet("QFrame{\n"
"background-color: rgb(240, 249, 254);\n"
"border:0px solid red;\n"
"border-radius:18px\n"
"}")
        self.main_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.main_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.main_frame.setObjectName("main_frame")
        self.horizontalLayout_18 = QtWidgets.QHBoxLayout(self.main_frame)
        self.horizontalLayout_18.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_18.setSpacing(12)
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(12, 12, 12, 12)
        self.verticalLayout_2.setSpacing(16)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(18)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.toolButton_close = QtWidgets.QToolButton(parent=self.main_frame)
        self.toolButton_close.setStyleSheet("QToolButton {\n"
"    background: transparent;\n"
"    border: none;\n"
"    padding: 0;\n"
"    spacing: 4px;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QToolButton:hover {\n"
"    background-color: rgb(255, 255, 255);\n"
"    border-radius: 9px;\n"
"}\n"
"\n"
"QToolButton:pressed {\n"
"    background-color: rgba(150, 150, 150, 80);\n"
"}\n"
"\n"
"QToolButton:disabled {\n"
"    color: #999999;\n"
"    opacity: 0.7;\n"
"}\n"
"\n"
"QToolButton::menu-indicator {\n"
"    image: none;\n"
"    subcontrol-position: right center;\n"
"    subcontrol-origin: padding;\n"
"    width: 8px;\n"
"    height: 8px;\n"
"}")
        self.toolButton_close.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("resources/img/窗口控制/窗口控制-关闭.svg"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.toolButton_close.setIcon(icon)
        self.toolButton_close.setIconSize(QtCore.QSize(24, 24))
        self.toolButton_close.setObjectName("toolButton_close")
        self.horizontalLayout.addWidget(self.toolButton_close)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(12)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.label_2 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_9.addWidget(self.label_2)
        self.lineEdit_ACCESS_KEY_ID = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_ACCESS_KEY_ID.setFont(font)
        self.lineEdit_ACCESS_KEY_ID.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_ACCESS_KEY_ID.setObjectName("lineEdit_ACCESS_KEY_ID")
        self.horizontalLayout_9.addWidget(self.lineEdit_ACCESS_KEY_ID)
        self.horizontalLayout_2.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_3.addWidget(self.label_3)
        self.lineEdit_ACCESS_KEY_SECRET = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_ACCESS_KEY_SECRET.setFont(font)
        self.lineEdit_ACCESS_KEY_SECRET.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_ACCESS_KEY_SECRET.setObjectName("lineEdit_ACCESS_KEY_SECRET")
        self.horizontalLayout_3.addWidget(self.lineEdit_ACCESS_KEY_SECRET)
        self.horizontalLayout_2.addLayout(self.horizontalLayout_3)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setSpacing(12)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.label_4 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_10.addWidget(self.label_4)
        self.lineEdit_ENDPOINT = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_ENDPOINT.setFont(font)
        self.lineEdit_ENDPOINT.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_ENDPOINT.setObjectName("lineEdit_ENDPOINT")
        self.horizontalLayout_10.addWidget(self.lineEdit_ENDPOINT)
        self.horizontalLayout_4.addLayout(self.horizontalLayout_10)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_5 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_5.addWidget(self.label_5)
        self.lineEdit_BUCKET_NAME = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_BUCKET_NAME.setFont(font)
        self.lineEdit_BUCKET_NAME.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_BUCKET_NAME.setObjectName("lineEdit_BUCKET_NAME")
        self.horizontalLayout_5.addWidget(self.lineEdit_BUCKET_NAME)
        self.horizontalLayout_4.addLayout(self.horizontalLayout_5)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setSpacing(12)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        self.label_9 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.horizontalLayout_12.addWidget(self.label_9)
        self.lineEdit_DOUYIN_API_KEY = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_DOUYIN_API_KEY.setFont(font)
        self.lineEdit_DOUYIN_API_KEY.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_DOUYIN_API_KEY.setObjectName("lineEdit_DOUYIN_API_KEY")
        self.horizontalLayout_12.addWidget(self.lineEdit_DOUYIN_API_KEY)
        self.horizontalLayout_11.addLayout(self.horizontalLayout_12)
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.label_10 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_10.setFont(font)
        self.label_10.setObjectName("label_10")
        self.horizontalLayout_13.addWidget(self.label_10)
        self.lineEdit_ALI_CODE = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_ALI_CODE.setFont(font)
        self.lineEdit_ALI_CODE.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_ALI_CODE.setObjectName("lineEdit_ALI_CODE")
        self.horizontalLayout_13.addWidget(self.lineEdit_ALI_CODE)
        self.horizontalLayout_11.addLayout(self.horizontalLayout_13)
        self.verticalLayout_2.addLayout(self.horizontalLayout_11)
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout_6.setSpacing(12)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_7 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_7.setFont(font)
        self.label_7.setObjectName("label_7")
        self.horizontalLayout_7.addWidget(self.label_7)
        self.spinBox_CONCURRENCY = QtWidgets.QSpinBox(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.spinBox_CONCURRENCY.setFont(font)
        self.spinBox_CONCURRENCY.setStyleSheet("QSpinBox {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 4px;\n"
"    padding: 2px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QSpinBox:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"}\n"
"\n"
"QSpinBox:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QSpinBox:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}\n"
"\n"
"QSpinBox::up-button, QSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    width: 16px;\n"
"    height: 8px;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"QSpinBox::up-button:hover, QSpinBox::down-button:hover {\n"
"    background-color: rgba(30, 131, 255, 0.1);\n"
"}\n"
"\n"
"QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {\n"
"    background-color: rgba(30, 131, 255, 0.2);\n"
"}\n"
"\n"
"QSpinBox:disabled::up-button, QSpinBox:disabled::down-button {\n"
"    background-color: transparent;\n"
"}")
        self.spinBox_CONCURRENCY.setMinimum(1)
        self.spinBox_CONCURRENCY.setMaximum(32)
        self.spinBox_CONCURRENCY.setObjectName("spinBox_CONCURRENCY")
        self.horizontalLayout_7.addWidget(self.spinBox_CONCURRENCY)
        self.horizontalLayout_6.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_14 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_14.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.label_6 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_6.setFont(font)
        self.label_6.setObjectName("label_6")
        self.horizontalLayout_14.addWidget(self.label_6)
        self.spinBox_RETRY_TIMES = QtWidgets.QSpinBox(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.spinBox_RETRY_TIMES.setFont(font)
        self.spinBox_RETRY_TIMES.setStyleSheet("QSpinBox {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 4px;\n"
"    padding: 2px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QSpinBox:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"}\n"
"\n"
"QSpinBox:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QSpinBox:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}\n"
"\n"
"QSpinBox::up-button, QSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    width: 16px;\n"
"    height: 8px;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"QSpinBox::up-button:hover, QSpinBox::down-button:hover {\n"
"    background-color: rgba(30, 131, 255, 0.1);\n"
"}\n"
"\n"
"QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {\n"
"    background-color: rgba(30, 131, 255, 0.2);\n"
"}\n"
"\n"
"QSpinBox:disabled::up-button, QSpinBox:disabled::down-button {\n"
"    background-color: transparent;\n"
"}")
        self.spinBox_RETRY_TIMES.setMinimum(3)
        self.spinBox_RETRY_TIMES.setMaximum(30)
        self.spinBox_RETRY_TIMES.setSingleStep(1)
        self.spinBox_RETRY_TIMES.setProperty("value", 3)
        self.spinBox_RETRY_TIMES.setObjectName("spinBox_RETRY_TIMES")
        self.horizontalLayout_14.addWidget(self.spinBox_RETRY_TIMES)
        self.horizontalLayout_6.addLayout(self.horizontalLayout_14)
        self.horizontalLayout_16 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_16.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout_16.setSpacing(0)
        self.horizontalLayout_16.setObjectName("horizontalLayout_16")
        self.label_11 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_11.setFont(font)
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_16.addWidget(self.label_11)
        self.comboBox_mode = QtWidgets.QComboBox(parent=self.main_frame)
        self.comboBox_mode.setStyleSheet("QComboBox {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 4px;\n"
"    padding: 2px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"}\n"
"\n"
"QComboBox:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 1px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QComboBox:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}\n"
"\n"
"/* 下拉按钮样式 */\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    width: 16px;\n"
"    height: 100%;\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* 下拉箭头样式 */\n"
"QComboBox::down-arrow {\n"
"    image: url(:/icons/down_arrow.png); /* 可替换为实际箭头图标 */\n"
"    width: 8px;\n"
"    height: 8px;\n"
"}\n"
"\n"
"QComboBox::drop-down:hover {\n"
"    background-color: rgba(30, 131, 255, 0.1);\n"
"}\n"
"\n"
"QComboBox::drop-down:pressed {\n"
"    background-color: rgba(30, 131, 255, 0.2);\n"
"}\n"
"\n"
"QComboBox:disabled::drop-down {\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* 下拉列表样式 */\n"
"QComboBox QAbstractItemView {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 4px;\n"
"    background-color: white;\n"
"    selection-background-color: rgba(30, 131, 255, 0.2);\n"
"    selection-color: black;\n"
"}")
        self.comboBox_mode.setObjectName("comboBox_mode")
        self.comboBox_mode.addItem("")
        self.comboBox_mode.addItem("")
        self.comboBox_mode.addItem("")
        self.comboBox_mode.addItem("")
        self.horizontalLayout_16.addWidget(self.comboBox_mode)
        self.horizontalLayout_6.addLayout(self.horizontalLayout_16)
        self.verticalLayout_2.addLayout(self.horizontalLayout_6)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.label_8 = QtWidgets.QLabel(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout_8.addWidget(self.label_8)
        self.lineEdit_RE = QtWidgets.QLineEdit(parent=self.main_frame)
        font = QtGui.QFont()
        font.setPointSize(-1)
        self.lineEdit_RE.setFont(font)
        self.lineEdit_RE.setStyleSheet("QLineEdit {\n"
"    border: 1px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 5px;\n"
"    background-color: white;\n"
"    color: black;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    padding: 4px;\n"
"    background-color: #f8faff;\n"
"}\n"
"\n"
"QLineEdit:disabled {\n"
"    border: 1px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.lineEdit_RE.setObjectName("lineEdit_RE")
        self.horizontalLayout_8.addWidget(self.lineEdit_RE)
        self.pushButton_Password = QtWidgets.QPushButton(parent=self.main_frame)
        self.pushButton_Password.setStyleSheet("QPushButton {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 6px 16px;\n"
"    background-color: white;\n"
"    color: rgb(30, 131, 255);\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgba(30, 131, 255, 0.1);\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgba(30, 131, 255, 0.3);\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    border: 2px solid #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.pushButton_Password.setObjectName("pushButton_Password")
        self.horizontalLayout_8.addWidget(self.pushButton_Password)
        self.verticalLayout_2.addLayout(self.horizontalLayout_8)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_2.addLayout(self.verticalLayout_3)
        self.horizontalLayout_15 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_15.addItem(spacerItem)
        self.pushButton_save = QtWidgets.QPushButton(parent=self.main_frame)
        self.pushButton_save.setStyleSheet("QPushButton {\n"
"    border: 2px solid rgb(30, 131, 255);\n"
"    border-radius: 6px;\n"
"    padding: 6px 16px;\n"
"    background-color: rgb(30, 131, 255);\n"
"    color: white;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(30, 131, 255);\n"
"    border-color: rgb(30, 131, 255);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(20, 107, 214);\n"
"    border-color: rgb(20, 107, 214);\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    border-color: #cccccc;\n"
"    background-color: #f0f0f0;\n"
"    color: #999999;\n"
"}")
        self.pushButton_save.setObjectName("pushButton_save")
        self.horizontalLayout_15.addWidget(self.pushButton_save)
        self.verticalLayout_2.addLayout(self.horizontalLayout_15)
        self.horizontalLayout_18.addLayout(self.verticalLayout_2)
        self.verticalLayout.addWidget(self.main_frame)
        SettingWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(SettingWindow)
        QtCore.QMetaObject.connectSlotsByName(SettingWindow)

    def retranslateUi(self, SettingWindow):
        _translate = QtCore.QCoreApplication.translate
        SettingWindow.setWindowTitle(_translate("SettingWindow", "MainWindow"))
        self.label.setText(_translate("SettingWindow", "RailwayOCR Setting"))
        self.label_2.setText(_translate("SettingWindow", "ACCESS_KEY_ID："))
        self.lineEdit_ACCESS_KEY_ID.setPlaceholderText(_translate("SettingWindow", "OSS服务公钥"))
        self.label_3.setText(_translate("SettingWindow", "ACCESS_KEY_SECRET："))
        self.lineEdit_ACCESS_KEY_SECRET.setPlaceholderText(_translate("SettingWindow", "OSS服务私钥"))
        self.label_4.setText(_translate("SettingWindow", "ENDPOINT："))
        self.lineEdit_ENDPOINT.setPlaceholderText(_translate("SettingWindow", "服务器地址"))
        self.label_5.setText(_translate("SettingWindow", "BUCKET_NAME："))
        self.lineEdit_BUCKET_NAME.setPlaceholderText(_translate("SettingWindow", "存储桶名称"))
        self.label_9.setText(_translate("SettingWindow", "DOUYIN_KEY："))
        self.lineEdit_DOUYIN_API_KEY.setPlaceholderText(_translate("SettingWindow", "抖音服务密钥"))
        self.label_10.setText(_translate("SettingWindow", "ALI_KEY："))
        self.lineEdit_ALI_CODE.setPlaceholderText(_translate("SettingWindow", "阿里服务code"))
        self.label_7.setText(_translate("SettingWindow", "多线程并发数："))
        self.label_6.setText(_translate("SettingWindow", "出错重试次数："))
        self.label_11.setText(_translate("SettingWindow", "识别模式："))
        self.comboBox_mode.setItemText(0, _translate("SettingWindow", "阿里服务"))
        self.comboBox_mode.setItemText(1, _translate("SettingWindow", "本地模型"))
        self.comboBox_mode.setItemText(2, _translate("SettingWindow", "抖音服务"))
        self.comboBox_mode.setItemText(3, _translate("SettingWindow", "百度服务"))
        self.label_8.setText(_translate("SettingWindow", "RE（Ai 识别结果校验）："))
        self.lineEdit_RE.setPlaceholderText(_translate("SettingWindow", "输入正则表达式"))
        self.pushButton_Password.setText(_translate("SettingWindow", "启动密码"))
        self.pushButton_save.setText(_translate("SettingWindow", "保存设置"))
