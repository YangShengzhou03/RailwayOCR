import json
import os
import sys
import time
import re
from datetime import datetime
import traceback

main_window = None
# 使用绝对路径存储日志文件
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_internal', 'log')
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
    """获取资源文件的绝对路径，兼容开发环境和打包环境"""
    try:
        # 打包环境下的路径
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下的路径
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


file_path = get_resource_path('resources/Config.json')

def set_log_level(level):
    global CURRENT_LOG_LEVEL
    if level in LOG_LEVELS:
        CURRENT_LOG_LEVEL = LOG_LEVELS[level]
        log_print(f"[INFO] 日志级别已设置为: {level}")
    else:
        log_print(f"[ERROR] 无效的日志级别: {level}")


def log_print(formatted_log):
    """打印日志到控制台、文件和UI界面"""
    # 提取日志级别
    level_match = re.match(r'\[(\w+)\]', formatted_log)
    if level_match:
        level = level_match.group(1)
        if LOG_LEVELS.get(level, 20) < CURRENT_LOG_LEVEL:
            return
    else:
        # 如果没有指定级别，默认为INFO
        level = "INFO"
        formatted_log = f"[INFO] {formatted_log}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] {formatted_log}"
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
            log_error(f"创建日志文件失败: {str(e)}")

    def rotate_log_if_needed():
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if len(lines) > MAX_LINES:
                    with open(LOG_PATH, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-MAX_LINES:])
        except Exception as e:
            log_error(f"日志旋转失败: {str(e)}")

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
        log_error(f"写入日志文件失败: {str(e)}")
        log_error(f"详细错误信息: {traceback.format_exc()}")



def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    default_config = {
        "ALLOWED_EXTENSIONS": [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
        "SUMMARY_DIR": "summary",
        "DOUYIN_WORKFLOW_ID": "",
        "DOUYIN_PROMPT": "请识别图像中的内容",
        "LOG_LEVEL": "INFO"
    }

    try:
        if not os.path.exists(file_path):
            log_warning(f"配置文件不存在: {file_path}")
            log_info("正在创建默认配置文件...")
            # 确保配置文件目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # 创建默认配置文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            log_info(f"默认配置文件已创建: {file_path}")
            return default_config

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        log_error(f"配置文件格式错误: {file_path}")
        log_info("使用默认配置...")
        return default_config
    except Exception as e:
        log_error(f"加载配置文件时发生错误: {str(e)}")
        log_info("使用默认配置...")
        return default_config


Config = load_config()

set_log_level(Config.get("LOG_LEVEL", "INFO"))



def log(level, message):
    log_print(f"[{level}] {message}")


def log_debug(message):
    log_print(f"[DEBUG] {message}")


def log_info(message):
    log_print(f"[INFO] {message}")


def log_warning(message):
    log_print(f"[WARNING] {message}")


def log_error(message):
    log_print(f"[ERROR] {message}")


def log_critical(message):
    log_print(f"[CRITICAL] {message}")


def save_summary(results):
    """保存处理结果统计信息"""
    try:
        # 确保摘要目录存在
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

        log_info(f"统计信息已保存到: {stats_path}")
        return stats

    except PermissionError:
        log_error(f"没有权限创建或写入文件，请检查目录权限: {summary_dir}")
        return None
    except FileNotFoundError as e:
        log_error(f"找不到文件或目录: {e}")
        return None
    except Exception as e:
        log_error(f"保存统计信息时发生错误: {str(e)}")
        return None
