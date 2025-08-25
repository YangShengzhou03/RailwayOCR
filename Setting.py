import json
import os
import re

import bcrypt
import keyring
from PyQt6 import QtGui
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, \
    QPushButton, QHBoxLayout, QWidget

from utils import MODE_ALI, MODE_BAIDU
from utils import get_resource_path, log, log_print
from Ui_SettingWindow import Ui_SettingWindow


class SettingWindow(QMainWindow, Ui_SettingWindow):
    def __init__(self):
        super().__init__()
        # 配置文件路径
        self.CONFIG_FILE = os.path.join(get_resource_path("_internal/Config.json"))
        self.REG_PATH = r"SOFTWARE\RailwayOCR"
        self.REG_PWD_KEY = "PasswordHash"
        self.setupUi(self)
        self.setWindowTitle('RailwayOCR Setting')
        self.pushButton_save.clicked.connect(self.save_config)
        self.pushButton_Password.clicked.connect(self.handle_password)
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))
        self.load_and_populate_config()



    def load_and_populate_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 验证配置
                self._validate_config(config)
            else:
                config = {}
                log("INFO", "配置文件不存在，使用默认配置")
                # 只在首次创建配置时显示提示
                if not os.path.exists(os.path.dirname(self.CONFIG_FILE)):
                    try:
                        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
                        log("INFO", f"创建配置目录: {os.path.dirname(self.CONFIG_FILE)}")
                    except (OSError, FileNotFoundError) as e:
                        log("ERROR", f"创建配置目录失败: {str(e)}")
                        QMessageBox.critical(self, "配置错误", f"创建配置目录失败: {str(e)}")
                QMessageBox.information(self, "提示", "首次启动，使用默认配置模板")
            self.lineEdit_BAIDU_API_KEY.setText(config.get("BAIDU_API_KEY", ""))
            self.lineEdit_BAIDU_SECRET_KEY.setText(config.get("BAIDU_SECRET_KEY", ""))
            self.lineEdit_ALI_APPCODE.setText(config.get("ALI_APPCODE", ""))
            # 兼容旧配置项CONCURRENT_NUM
            concurrency_value = config.get("CONCURRENCY", 4)
            self.spinBox_CONCURRENCY.setValue(concurrency_value)
            self.spinBox_RETRY_TIMES.setValue(config.get("RETRY_TIMES", 3))
            self.lineEdit_RE.setText(config.get("RE", r"^[A-K][1-7]$"))
            mode_index = config.get("MODE_INDEX", 0)
            if 0 <= mode_index < self.comboBox_mode.count():
                self.comboBox_mode.setCurrentIndex(mode_index)
        except json.JSONDecodeError:
            log("ERROR", f"配置文件格式错误: {self.CONFIG_FILE}")
            QMessageBox.critical(self, "配置加载失败", f"配置文件格式错误: {self.CONFIG_FILE}")
            self._load_default_values()
        except (IOError, OSError) as e:
            log("ERROR", f"配置加载失败: {str(e)}")
            QMessageBox.critical(self, "配置加载失败", f"读取配置时出错：{str(e)}")
            self._load_default_values()

    def _load_default_values(self):
        self.spinBox_CONCURRENCY.setValue(4)
        self.spinBox_RETRY_TIMES.setValue(3)
        self.lineEdit_RE.setText(r"^[A-K][1-7]$")
        self.comboBox_mode.setCurrentIndex(0)

    def validate_required_fields(self):
        """
        验证必填字段是否完整且有效

        返回:
            bool: 字段是否有效
        """
        mode_index = self.comboBox_mode.currentIndex()
        required_fields = [
            ("RE（正则表达式）", self.lineEdit_RE)
        ]

        if mode_index == MODE_ALI:
            # 阿里百炼服务
            required_fields.extend([
                ("ALI_APPCODE", self.lineEdit_ALI_APPCODE)
            ])
        elif mode_index == MODE_BAIDU:
            # 百度千帆服务
            required_fields.extend([
                ("BAIDU_API_KEY", self.lineEdit_BAIDU_API_KEY),
                ("BAIDU_SECRET_KEY", self.lineEdit_BAIDU_SECRET_KEY)
            ])
        # 模式1（本地模型）和模式2（抖音服务）不需要额外API密钥

        # 检查必填字段是否为空
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

        # 验证正则表达式
        try:
            re.compile(self.lineEdit_RE.text().strip())
        except re.error as e:
            QMessageBox.warning(
                self, "正则表达式错误",
                f"无效的正则表达式: {self.lineEdit_RE.text().strip()}\n{str(e)}"
            )
            self.lineEdit_RE.setFocus()
            return False

        # 验证并发数范围
        if self.spinBox_CONCURRENCY.value() <= 0 or self.spinBox_CONCURRENCY.value() > 32:
            QMessageBox.warning(
                self, "并发数范围错误",
                "并发数必须在1-32之间"
            )
            self.spinBox_CONCURRENCY.setFocus()
            return False

        # 验证重试次数范围
        if self.spinBox_RETRY_TIMES.value() < 3 or self.spinBox_RETRY_TIMES.value() > 30:
            QMessageBox.warning(
                self, "重试次数范围错误",
                "重试次数必须在3-30之间"
            )
            self.spinBox_RETRY_TIMES.setFocus()
            return False

        return True

    def _validate_config(self, config):
        # 验证正则表达式
        if "RE" in config:
            if not isinstance(config["RE"], str):
                raise ValueError("RE必须是字符串")
            try:
                re.compile(config["RE"])
            except re.error as e:
                raise ValueError(f"正则表达式无效: {config['RE']}\n{str(e)}")

        # 验证数值类型和范围
        if "CONCURRENCY" in config:
            if not isinstance(config["CONCURRENCY"], int):
                raise ValueError("CONCURRENCY必须是整数")
            if config["CONCURRENCY"] <= 0 or config["CONCURRENCY"] > 32:
                raise ValueError("CONCURRENCY必须在1-32之间")

        if "RETRY_TIMES" in config:
            if not isinstance(config["RETRY_TIMES"], int):
                raise ValueError("RETRY_TIMES必须是整数")
            if config["RETRY_TIMES"] < 0 or config["RETRY_TIMES"] > 30:
                raise ValueError("RETRY_TIMES必须在0-30之间")

        # 验证API密钥
        if "BAIDU_API_KEY" in config and not isinstance(config["BAIDU_API_KEY"], str):
            raise ValueError("BAIDU_API_KEY必须是字符串")

        if "BAIDU_SECRET_KEY" in config and not isinstance(config["BAIDU_SECRET_KEY"], str):
            raise ValueError("BAIDU_SECRET_KEY必须是字符串")

        if "ALI_APPCODE" in config and not isinstance(config["ALI_APPCODE"], str):
            raise ValueError("ALI_APPCODE必须是字符串")

        # 验证模式索引
        if "MODE_INDEX" in config:
            if not isinstance(config["MODE_INDEX"], int):
                raise ValueError("MODE_INDEX必须是整数")
            if config["MODE_INDEX"] < 0 or config["MODE_INDEX"] > MODE_BAIDU:
                raise ValueError("MODE_INDEX必须在0-3之间")

    def load_config(self):
        # 此方法已被 load_and_populate_config 替代，保留以确保兼容性
        self.load_and_populate_config()

    def save_config(self):
        try:
            # 验证输入字段
            if not self.validate_required_fields():
                return

            config = {
                'BAIDU_API_KEY': self.lineEdit_BAIDU_API_KEY.text(),
                'BAIDU_SECRET_KEY': self.lineEdit_BAIDU_SECRET_KEY.text(),
                'ALI_APPCODE': self.lineEdit_ALI_APPCODE.text(),
                'CONCURRENCY': self.spinBox_CONCURRENCY.value(),
                'RETRY_TIMES': self.spinBox_RETRY_TIMES.value(),
                'MODE_INDEX': self.comboBox_mode.currentIndex(),
                'RE': self.lineEdit_RE.text()
            }

            # 验证配置有效性
            self._validate_config(config)

            # 使用统一的配置文件路径
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, '提示', '设置已保存')
        except ValueError as ve:
            log("ERROR", f"配置验证失败: {str(ve)}")
            QMessageBox.warning(self, "配置无效", str(ve))
        except (IOError, PermissionError) as e:
            try:
                error_msg = f"保存配置失败: {str(e)}"
                log("ERROR", error_msg)
                QMessageBox.critical(self, "保存失败", error_msg)
            except Exception as log_err:
                # 日志和消息框同时失败的极端情况
                print(f"双重错误: {str(log_err)} - 原始错误: {str(e)}")

    def handle_password(self):
        """
        处理密码设置或修改
        """
        # 注意：此方法使用Windows特有的winreg模块，存在跨平台兼容性问题
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
                # 密码强度检查
                if new_pwd1.text() and not re.match(r'^(?=.*[A-Za-z])(?=.*\d).{4,}$', new_pwd1.text()):
                    QMessageBox.warning(
                        self, "密码强度不足",
                        "密码应至少包含字母和数字，长度至少4个字符"
                    )
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
                # 密码强度检查
                if new_pwd1.text() and not re.match(r'^(?=.*[A-Za-z])(?=.*\d).{4,}$', new_pwd1.text()):
                    QMessageBox.warning(
                        self, "密码强度不足",
                        "密码应至少包含字母和数字，长度至少4个字符"
                    )
                    return
                if self._save_password(new_pwd1.text()):
                    msg = "密码已设置" if new_pwd1.text() else "未设置密码"
                    QMessageBox.information(self, "成功", msg)
                else:
                    QMessageBox.critical(self, "失败", "密码设置失败")

    def _has_password(self):
        """检查系统凭据管理器中是否存储了密码"""
        try:
            password = keyring.get_password("RailwayOCR", "admin")
            return password is not None and password != ""
        except keyring.errors.KeyringError as e:
            log("ERROR", f"检查密码时出错: {str(e)}")
            return False

    def _verify_password(self, password):
        """使用系统凭据管理器验证密码"""
        try:
            stored_value = keyring.get_password("RailwayOCR", "admin")
            if not stored_value:
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
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        except keyring.errors.KeyringError as e:
            log("ERROR", f"验证密码时出错: {str(e)}")
            return False

    def showEvent(self, event):
        self.load_and_populate_config()
        super().showEvent(event)

    def _save_password(self, password):
        """将密码安全存储到系统凭据管理器"""
        try:
            if password:
                # 生成盐值并使用bcrypt哈希密码
                salt = bcrypt.gensalt(12)
                password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
                # 存储盐值和哈希值（盐值16字节+哈希值32字节，HEX编码）
                stored_value = f"{salt.hex()}:{password_hash.hex()}"
                
                # 使用keyring存储到系统凭据管理器
                keyring.set_password("RailwayOCR", "admin", stored_value)
                log_print("密码已成功保存到系统凭据管理器")
            else:
                # 删除密码
                try:
                    keyring.delete_password("RailwayOCR", "admin")
                    log_print("密码已从系统凭据管理器中删除")
                except keyring.errors.PasswordDeleteError:
                    log_print("尝试删除不存在的密码")
                    pass
            return True
        except keyring.errors.PasswordSetError as e:
            log_print(f"保存密码失败: {str(e)}")
            QMessageBox.critical(None, "密码保存错误", f"无法保存密码到系统凭据管理器: {str(e)}")
            return False
        except keyring.errors.KeyringError as e:
            error_msg = f"密码操作失败: {str(e)}"
            log_print(error_msg)
            QMessageBox.critical(None, "密码错误", error_msg)
            return False


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = SettingWindow()
    window.show()
    sys.exit(app.exec())
