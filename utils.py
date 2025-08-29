import json
import os
import sys
import time
from datetime import datetime
from functools import lru_cache, wraps

from PyQt6.QtWidgets import QMessageBox

MODE_LOCAL = 0
MODE_PADDLE = 1
MODE_BAIDU = 2
MODE_ALI = 3

MAIN_WINDOW = None
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_internal', 'log')
MAX_LINES = 3000
_LOG_FILE_HANDLE = None


def exception_handler(max_retries=1, retry_delay=1.0, log_level="ERROR"):
    """
    统一异常处理装饰器
    :param max_retries: 最大重试次数
    :param retry_delay: 重试延迟时间（秒）
    :param log_level: 日志级别
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries:
                        log_print(f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}", "WARNING")
                        time.sleep(retry_delay * (2 ** attempt))  # 指数退避
                    else:
                        log_print(f"函数 {func.__name__} 最终执行失败: {str(e)}", log_level)
                        # 根据异常类型决定是否重新抛出
                        if isinstance(e, (KeyboardInterrupt, SystemExit)):
                            raise
                        # 对于文件操作和网络相关的异常，通常不重新抛出以避免程序崩溃
                        elif isinstance(e, (FileNotFoundError, PermissionError, ConnectionError)):
                            return None
                        else:
                            # 对于其他未知异常，可以选择重新抛出或返回None
                            return None
            return None
        return wrapper
    return decorator


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


def log_print(message, level='INFO'):
    """打印日志并记录到文件

    Args:
        message (str): 日志消息
        level (str): 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    global _LOG_COUNTER
    
    # 根据配置过滤日志级别
    config_level = getattr(logging, Config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    message_level = getattr(logging, level.upper(), logging.INFO)
    
    if message_level < config_level:
        return  # 低于配置级别的日志不输出
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = f"[{timestamp}] [{level}] {message}"
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
            _LOG_COUNTER += 1
            # 优化：每10条日志flush一次，降低磁盘IO
            if _LOG_COUNTER % _LOG_FLUSH_INTERVAL == 0:
                log_handle.flush()
    except (OSError, IOError) as e:
        pass


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
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
            except IOError as e:
                QMessageBox.critical(None, "配置错误", f"创建默认配置文件失败: {str(e)}")
            return default_config

        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            default_config.update(config_data)
            return default_config
    except json.JSONDecodeError:
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
