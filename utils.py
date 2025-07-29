import json
import os
import sys
import time
from datetime import datetime

main_window = None


def load_config(file_path='Config.json'):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


Config = load_config()


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path).replace(os.sep, '/')


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
    os.makedirs(Config["SUMMARY_DIR"], exist_ok=True)
    summary_path = os.path.join(Config["SUMMARY_DIR"], "summary.json")
    stats_path = os.path.join(Config["SUMMARY_DIR"], "statistics.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    total = len(results)
    success_count = sum(1 for r in results if r['success'])
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