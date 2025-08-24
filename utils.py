import json
import os
import sys
import time
from datetime import datetime
import traceback
from functools import lru_cache

from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox

main_window = None
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_internal', 'log')
MAX_LINES = 3000
_log_file_handle = None


@lru_cache(maxsize=128)
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


file_path = get_resource_path('resources/Config.json')


def _init_log_system():
    try:
        directory = os.path.dirname(LOG_PATH)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.write(f"# Log file created at {datetime.now()}\n")
    except Exception as e:
        print(f"[ERROR] 初始化日志系统失败: {str(e)}")


_init_log_system()


def _get_log_file_handle():
    global _log_file_handle
    if _log_file_handle is None or _log_file_handle.closed:
        try:
            _log_file_handle = open(LOG_PATH, 'a', encoding='utf-8')
        except Exception as e:
            log("DEBUG", f"获取日志文件句柄失败: {str(e)}")
            return None
    return _log_file_handle


def close_log_file():
    """
    关闭日志文件句柄
    """
    global _log_file_handle
    if _log_file_handle and not _log_file_handle.closed:
        try:
            _log_file_handle.close()
            _log_file_handle = None
            log("DEBUG", "日志文件已关闭")
        except Exception as e:
            print(f"[ERROR] 关闭日志文件失败: {str(e)}")


def log_print(formatted_log):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] {formatted_log}"
    print(formatted_log)

    try:
        # 日志轮转
        log_rotation_size = Config.get("LOG_ROTATION_SIZE", 5 * 1024 * 1024)
        log_backup_count = Config.get("LOG_BACKUP_COUNT", 3)

        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > log_rotation_size:
            # 执行日志轮转
            for i in range(log_backup_count - 1, 0, -1):
                backup_path = f"{LOG_PATH}.{i}"
                prev_backup_path = f"{LOG_PATH}.{i-1}"
                if os.path.exists(prev_backup_path):
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(prev_backup_path, backup_path)
            # 重命名当前日志文件为 .1
            backup_path = f"{LOG_PATH}.1"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(LOG_PATH, backup_path)
            # 创建新的日志文件
            with open(LOG_PATH, 'w', encoding='utf-8') as f:
                f.write(f"# Log file created at {datetime.now()}\n")

        log_handle = _get_log_file_handle()
        if log_handle:
            log_handle.write(f"{formatted_log}\n")
            log_handle.flush()

        if main_window and hasattr(main_window, 'textEdit_log') and main_window.textEdit_log:
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(
                main_window.textEdit_log,
                "append",
                Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, formatted_log)
            )
            QMetaObject.invokeMethod(
                main_window.textEdit_log,
                "ensureCursorVisible",
                Qt.ConnectionType.QueuedConnection
            )
    except Exception as e:
        log("DEBUG", f"写入日志文件失败: {str(e)}")
        log("DEBUG", f"详细错误信息: {traceback.format_exc()}")


@lru_cache(maxsize=1)
def load_config():
    default_config = {
        "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
        "SUMMARY_DIR": "summary",
        "DOUYIN_WORKFLOW_ID": "",
        "DOUYIN_PROMPT": "请识别图像中的内容",
        "LOG_LEVEL": "INFO",  # 日志级别: DEBUG, INFO, WARNING, ERROR
        "LOG_ROTATION_SIZE": 5 * 1024 * 1024,  # 5MB
        "LOG_BACKUP_COUNT": 3  # 保留的备份文件数
    }

    try:
        if not os.path.exists(file_path):
            log("DEBUG", f"配置文件不存在: {file_path}")
            log("DEBUG", "正在创建默认配置文件...")
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                log("DEBUG", f"默认配置文件已创建: {file_path}")
            except Exception as e:
                log("ERROR", f"创建默认配置文件失败: {str(e)}")
                QMessageBox.critical(None, "配置错误", f"创建默认配置文件失败: {str(e)}")
            return default_config

        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            default_config.update(config_data)
            return default_config
    except json.JSONDecodeError:
        log("DEBUG", f"配置文件格式错误: {file_path}")
        log("DEBUG", "使用默认配置...")
        return default_config
    except Exception as e:
        log("DEBUG", f"加载配置文件时发生错误: {str(e)}")
        return default_config


Config = load_config()


def log(level, message):
    # 检查日志级别
    log_levels = {"DEBUG": 1, "INFO": 2, "WARNING": 3, "ERROR": 4}
    current_level = log_levels.get(Config.get("LOG_LEVEL", "INFO"), 2)
    message_level = log_levels.get(level, 2)

    if message_level < current_level:
        return

    timestamp = time.strftime("%m-%d %H:%M:%S")
    colors = {
        "INFO": "#691bfd",
        "ERROR": "#FF0000",
        "WARNING": "#FFA500",
        "DEBUG": "#008000"
    }
    color = colors.get(level, "#000000")
    formatted_message = f'<span style="color:{color}">[{timestamp}] [{level}] {message}</span>'
    if main_window and hasattr(main_window, 'textEdit_log') and main_window.textEdit_log:
        from PyQt6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            main_window.textEdit_log,
            "append",
            Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, formatted_message)
        )
        QMetaObject.invokeMethod(
            main_window.textEdit_log,
            "ensureCursorVisible",
            Qt.ConnectionType.QueuedConnection
        )


def save_summary(results):
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
        log("DEBUG", f"统计信息已保存到: {stats_path}")
        return stats
    except Exception as e:
        log("DEBUG", f"保存统计信息时发生错误: {str(e)}")
        return None
