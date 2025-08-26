"""
工具函数模块，包含日志系统、配置管理、文件处理等通用功能。
"""
import json
import os
import sys
import time
from datetime import datetime

from functools import lru_cache

from PyQt6 import QtCore

from PyQt6.QtWidgets import QMessageBox

MODE_LOCAL = 0
MODE_BAIDU = 1
MODE_ALI = 2

MAIN_WINDOW = None
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_internal', 'log')
MAX_LINES = 3000
_LOG_FILE_HANDLE = None


@lru_cache(maxsize=128)
def get_resource_path(relative_path):
    """获取资源文件的绝对路径

    Args:
        relative_path (str): 资源文件的相对路径

    Returns:
        str: 资源文件的绝对路径，兼容PyInstaller打包环境
    """
    try:
        # pylint: disable=protected-access,no-member
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


file_path = get_resource_path('_internal/Config.json')


def _init_log_system():
    """初始化日志系统

    创建日志目录和初始日志文件，若不存在则自动创建
    """
    try:
        directory = os.path.dirname(LOG_PATH)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.write(f"# Log file created at {datetime.now()}\n")
    except (OSError, FileNotFoundError) as e:
        print(f"[ERROR] 初始化日志系统失败: {str(e)}")


_init_log_system()


def _get_log_file_handle():
    """获取日志文件句柄

    若句柄未初始化或已关闭，则重新打开日志文件
    返回日志文件句柄，失败时返回None
    """
    global _LOG_FILE_HANDLE
    if _LOG_FILE_HANDLE is None or _LOG_FILE_HANDLE.closed:
        try:
            # pylint: disable=R1732
            _LOG_FILE_HANDLE = open(LOG_PATH, 'a', encoding='utf-8')
        except (IOError, OSError) as e:
            log("ERROR", f"无法打开日志文件: {str(e)}")
            return None
    return None


def close_log_file():
    """关闭日志文件句柄

    安全关闭当前打开的日志文件，释放资源
    """
    global _LOG_FILE_HANDLE
    if _LOG_FILE_HANDLE and not _LOG_FILE_HANDLE.closed:
        try:
            _LOG_FILE_HANDLE.close()
            _LOG_FILE_HANDLE = None

        except (OSError, IOError) as e:
            print(f"[ERROR] 关闭日志文件失败: {str(e)}")


# 添加日志计数器，用于控制flush频率
_LOG_COUNTER = 0
_LOG_FLUSH_INTERVAL = 10  # 每10条日志flush一次


def log_print(debug_message):
    """打印调试日志并写入文件

    Args:
        debug_message (str): 调试信息内容
    """
    global _LOG_COUNTER
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] [DEBUG] {debug_message}"

    try:
        log_rotation_size = Config.get("LOG_ROTATION_SIZE", 5 * 1024 * 1024)
        log_backup_count = Config.get("LOG_BACKUP_COUNT", 3)

        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > log_rotation_size:
            for i in range(log_backup_count - 1, 0, -1):
                backup_path = f"{LOG_PATH}.{i}"
                prev_backup_path = f"{LOG_PATH}.{i - 1}"
                if os.path.exists(prev_backup_path):
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(prev_backup_path, backup_path)
            backup_path = f"{LOG_PATH}.1"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(LOG_PATH, backup_path)
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.write(f"# Log file created at {datetime.now()}\n")

        log_handle = _get_log_file_handle()
        if log_handle:
            log_handle.write(f"{formatted_log}\n")
            _LOG_COUNTER += 1
            # 优化：每10条日志flush一次，降低磁盘IO
            if _LOG_COUNTER % _LOG_FLUSH_INTERVAL == 0:
                log_handle.flush()

        if MAIN_WINDOW and hasattr(MAIN_WINDOW, 'textEdit_log') and MAIN_WINDOW.textEdit_log:
            # pylint: disable=import-outside-toplevel
            from PyQt6.QtCore import QMetaObject, Qt, QCoreApplication
            if QCoreApplication.instance().thread() != MAIN_WINDOW.thread():
                QMetaObject.invokeMethod(
                    MAIN_WINDOW.textEdit_log,
                    "append",
                    Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, formatted_log)
                )
                QMetaObject.invokeMethod(
                    MAIN_WINDOW.textEdit_log,
                    "ensureCursorVisible",
                    Qt.ConnectionType.QueuedConnection
                )
            else:
                MAIN_WINDOW.textEdit_log.append(formatted_log)
                MAIN_WINDOW.textEdit_log.ensureCursorVisible()
                MAIN_WINDOW.textEdit_log.append(formatted_log)
                MAIN_WINDOW.textEdit_log.ensureCursorVisible()
    except (OSError, IOError) as e:
        log("ERROR", f"写入日志时出错: {str(e)}")


@lru_cache(maxsize=1)
def load_config():
    """加载应用配置

    如果配置文件不存在则创建默认配置，支持JSON格式解析
    返回合并后的配置字典
    """
    default_config = {
        "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
        "SUMMARY_DIR": "summary",
        "DOUYIN_WORKFLOW_ID": "",
        "DOUYIN_PROMPT": "请识别图像中的内容",
        "LOG_LEVEL": "INFO",
        "LOG_ROTATION_SIZE": 5 * 1024 * 1024,
        "LOG_BACKUP_COUNT": 3
    }

    try:
        if not os.path.exists(file_path):
            log("INFO", "配置文件不存在，正在创建默认设置...")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                log("INFO", "默认配置文件创建成功")
            except IOError as e:
                log("ERROR", f"创建默认配置文件失败: {str(e)}")
                QMessageBox.critical(None, "配置错误", f"创建默认配置文件失败: {str(e)}")
            return default_config

        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            default_config.update(config_data)
            return default_config
    except json.JSONDecodeError:
        log("WARNING", "配置文件格式错误，将使用默认设置")
        return default_config
    except (IOError, ValueError):
        return default_config


Config = load_config()


def log(level, message):
    timestamp = time.strftime("%m-%d %H:%M:%S")
    colors = {
        "INFO": "#691bfd",
        "ERROR": "#FF0000",
        "WARNING": "#FFA500",
        "DEBUG": "#008000"
    }
    color = colors.get(level, "#000000")
    formatted_message = f'<span style="color:{color}">[{timestamp}] [{level}] {message}</span>'
    MAIN_WINDOW.textEdit_log.append(formatted_message)
    MAIN_WINDOW.textEdit_log.ensureCursorVisible()


def save_summary(results):
    """保存识别结果统计信息

    Args:
        results (list): OCR识别结果列表，每个元素为包含识别状态的字典

    Returns:
        dict: 包含处理时间、总文件数、成功/失败数量及识别成功率的统计字典
    """
    try:
        summary_dir = Config["SUMMARY_DIR"]
        os.makedirs(summary_dir, exist_ok=True)
        stats_path = os.path.join(summary_dir, "statistics.json")
        total = len(results)
        success_count = sum(1 for r in results if r.get('success', False))
        stats = {
            "处理时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "总文件数": total,
            "成功识别": success_count,
            "识别失败": total - success_count,
            "识别成功率": f"{success_count / total * 100:.2f}%" if total > 0 else "0.00%"
        }
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return stats
    except (IOError, json.JSONDecodeError) as e:
        log("DEBUG", f"保存统计信息时发生错误: {str(e)}")
        return None
