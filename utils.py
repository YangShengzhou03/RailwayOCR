import json
import os
import sys
import time
from datetime import datetime
import traceback

main_window = None
LOG_PATH = '_internal/log'
MAX_LINES = 3000

LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

CURRENT_LOG_LEVEL = LOG_LEVELS["INFO"]


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


file_path = get_resource_path('resources/Config.json')

def set_log_level(level):
    global CURRENT_LOG_LEVEL
    if level in LOG_LEVELS:
        CURRENT_LOG_LEVEL = LOG_LEVELS[level]
        log_print(f"日志级别已设置为: {level}", level="INFO")
    else:
        log_print(f"无效的日志级别: {level}", level="ERROR")


def log_print(log_info, level="INFO"):
    if LOG_LEVELS.get(level, 20) < CURRENT_LOG_LEVEL:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] [{level}] {log_info}"
    print(formatted_log)

    def ensure_log_file_exists():
        try:
            directory = os.path.dirname(LOG_PATH)
            if not os.path.exists(directory):
                os.makedirs(directory)
            if not os.path.exists(LOG_PATH):
                with open(LOG_PATH, 'w', encoding='utf-8') as f:
                    f.write(f"# Log file created at {datetime.now()}\n")
        except Exception as e:
            print(f"创建日志文件失败: {str(e)}")

    def rotate_log_if_needed():
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if len(lines) > MAX_LINES:
                    with open(LOG_PATH, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-MAX_LINES:])
        except Exception as e:
            print(f"日志旋转失败: {str(e)}")

    try:
        ensure_log_file_exists()
        rotate_log_if_needed()
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{formatted_log}\n")

        if main_window and hasattr(main_window, 'textEdit_log'):
            colors = {
                "INFO": "#691bfd",
                "ERROR": "#FF0000",
                "WARNING": "#FFA500",
                "DEBUG": "#008000",
                "CRITICAL": "#8B0000"
            }
            color = colors.get(level, "#000000")
            ui_log = f'<span style="color:{color}">{formatted_log}</span>'
            main_window.textEdit_log.append(ui_log)
            main_window.textEdit_log.ensureCursorVisible()
    except Exception as e:
        print(f"写入日志文件失败: {str(e)}")
        print(traceback.format_exc())



def load_config():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log_print(f"配置文件不存在: {file_path}", level="ERROR")
        return {
            "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
            "SUMMARY_DIR": "summary",
            "DOUYIN_WORKFLOW_ID": "",
            "DOUYIN_PROMPT": "请识别图像中的内容",
            "LOG_LEVEL": "INFO"
        }
    except json.JSONDecodeError:
        log_print(f"配置文件格式错误: {file_path}", level="ERROR")
        return {
            "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
            "SUMMARY_DIR": "summary",
            "DOUYIN_WORKFLOW_ID": "",
            "DOUYIN_PROMPT": "请识别图像中的内容",
            "LOG_LEVEL": "INFO"
        }


Config = load_config()

set_log_level(Config.get("LOG_LEVEL", "INFO"))



def log(level, message):
    log_print(message, level=level)


def log_debug(message):
    log_print(message, level="DEBUG")


def log_info(message):
    log_print(message, level="INFO")


def log_warning(message):
    log_print(message, level="WARNING")


def log_error(message):
    log_print(message, level="ERROR")


def log_critical(message):
    log_print(message, level="CRITICAL")


def save_summary(results):
    try:
        os.makedirs(Config["SUMMARY_DIR"], exist_ok=True)

        stats_path = os.path.join(Config["SUMMARY_DIR"], "statistics.json")

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

    except PermissionError:
        print(f"错误：没有权限创建或写入文件，请检查目录权限")
        return None
    except FileNotFoundError as e:
        print(f"错误：找不到文件或目录 - {e}")
        return None
    except Exception as e:
        print(f"未知错误：{e}")
        return None
