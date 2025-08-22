import json
import os
import sys
import time
from datetime import datetime

main_window = None
LOG_PATH = '_internal/log'
MAX_LINES = 3000


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


file_path = get_resource_path('resources/Config.json')

def log_print(log_info):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {log_info}")

    def ensure_log_file_exists():
        """内部函数：确保日志文件存在，不存在则创建"""
        try:
            directory = os.path.dirname(LOG_PATH)
            if not os.path.exists(directory):
                os.makedirs(directory)
            if not os.path.exists(LOG_PATH):
                with open(LOG_PATH, 'w', encoding='utf-8') as f:
                    f.write("# Log file created at {}\n".format(datetime.now()))
        except Exception:
            pass

    def rotate_log_if_needed():
        """内部函数：检查日志行数，超过限制则进行旋转"""
        try:
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > MAX_LINES:
                with open(LOG_PATH, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-MAX_LINES:])
        except Exception:
            pass

    try:
        ensure_log_file_exists()
        rotate_log_if_needed()
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {log_info}\n")
    except Exception:
        pass



def load_config():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log("ERROR", f"配置文件不存在: {file_path}")
        # 返回默认配置
        return {
            "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
            "SUMMARY_DIR": "summary"
        }
    except json.JSONDecodeError:
        log("ERROR", f"配置文件格式错误: {file_path}")
        return {
            "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
            "SUMMARY_DIR": "summary"
        }


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
    if main_window and hasattr(main_window, 'textEdit_log'):
        main_window.textEdit_log.append(formatted_message)
        main_window.textEdit_log.ensureCursorVisible()


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
