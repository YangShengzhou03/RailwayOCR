import json
import os
import sys
import time
from datetime import datetime
import traceback
from functools import lru_cache

from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox

MODE_LOCAL = 0
MODE_BAIDU = 1
MODE_ALI = 2

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


file_path = get_resource_path('_internal/Config.json')


def _init_log_system():
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
    global _log_file_handle
    if _log_file_handle is None or _log_file_handle.closed:
        try:
            _log_file_handle = open(LOG_PATH, 'a', encoding='utf-8')
        except (IOError, OSError) as e:
            log("ERROR", f"无法打开日志文件: {str(e)}")
            return None
    return _log_file_handle


def close_log_file():
    global _log_file_handle
    if _log_file_handle and not _log_file_handle.closed:
        try:
            _log_file_handle.close()
            _log_file_handle = None
            
        except (OSError, IOError) as e:
            print(f"[ERROR] 关闭日志文件失败: {str(e)}")


# 添加日志计数器，用于控制flush频率
_log_counter = 0
_LOG_FLUSH_INTERVAL = 10  # 每10条日志flush一次

def log_print(debug_message):
    global _log_counter
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] [DEBUG] {debug_message}"
    print(formatted_log)

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
            _log_counter += 1
            # 优化：每10条日志flush一次，降低磁盘IO
            if _log_counter % _LOG_FLUSH_INTERVAL == 0:
                log_handle.flush()

        if main_window and hasattr(main_window, 'textEdit_log') and main_window.textEdit_log:
            from PyQt6.QtCore import QMetaObject, Qt, QCoreApplication
            if QCoreApplication.instance().thread() != main_window.thread():
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
            else:
                main_window.textEdit_log.append(formatted_log)
                main_window.textEdit_log.ensureCursorVisible()
    except (OSError, IOError) as e:
        log("ERROR", f"写入日志时出错: {str(e)}")


@lru_cache(maxsize=1)
def load_config():
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
    except (IOError, ValueError) as e:
        return default_config


Config = load_config()


def log(level, message):
    # 用户可见日志：使用通俗语言，仅显示关键操作和错误
    if level == "DEBUG":
        return  # 用户日志不显示DEBUG级别
    allowed_levels = {"ERROR", "INFO", "WARNING"}
    allowed_levels = {"ERROR", "DEBUG", "INFO", "WARNING"}
    if level not in allowed_levels:
        print(f"错误：不支持的日志级别 '{level}'，必须是 ERROR、DEBUG、INFO 或 WARNING")
        return
    print(f"{level} {message}")
    timestamp = time.strftime("%m-%d %H:%M:%S")
    colors = {
        "INFO": "#691bfd",
        "ERROR": "#FF0000",
        "WARNING": "#FFA500",
        "DEBUG": "#3232CD"
    }
    color = colors[level]
    # 使用更友好的用户语言
    user_friendly_levels = {"ERROR": "错误", "INFO": "信息", "WARNING": "警告"}
    friendly_level = user_friendly_levels.get(level, level)
    formatted_message = f'<span style="color:{color}">[{timestamp}] [{friendly_level}] {message}</span>'
    if main_window and hasattr(main_window, 'textEdit_log'):
        main_window.textEdit_log.append(formatted_message)
        main_window.textEdit_log.ensureCursorVisible()


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
        
        return stats
    except (IOError, json.JSONEncodeError) as e:
        log("DEBUG", f"保存统计信息时发生错误: {str(e)}")
        return None
