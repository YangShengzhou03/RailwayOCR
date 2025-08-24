import json
import os
import sys
import time
from datetime import datetime
import traceback
from functools import lru_cache

from PyQt6 import QtCore

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


def log_print(formatted_log):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] {formatted_log}"
    print(formatted_log)

    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 600 * 1024:
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                f.seek(0, 2)
                pos, lines = f.tell(), 0
                while pos > 0 and lines < MAX_LINES:
                    pos -= 1
                    f.seek(pos)
                    if f.read(1) == '\n':
                        lines += 1
                if pos > 0:
                    f.seek(pos + 1)
                    with open(LOG_PATH, 'w', encoding='utf-8') as f_write:
                        f_write.write(f.read())

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
        "DOUYIN_PROMPT": "请识别图像中的内容"
    }

    try:
        if not os.path.exists(file_path):
            log("DEBUG", f"配置文件不存在: {file_path}")
            log("DEBUG", "正在创建默认配置文件...")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            log("DEBUG", f"默认配置文件已创建: {file_path}")
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
    timestamp = time.strftime("%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{level}] {message}"
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
