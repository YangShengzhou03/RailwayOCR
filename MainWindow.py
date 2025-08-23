import base64
import json
import os
import re
import ssl
import sys
import time
import requests
import urllib.parse
from datetime import timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import easyocr
import numpy as np
from PIL import Image

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QFileDialog)

import utils
from Setting import SettingWindow
from Thread import ProcessingThread
from Ui_MainWindow import Ui_MainWindow
from utils import log, save_summary, get_resource_path, log_print


class AliClient:
    def __init__(self, appcode=None):
        self.REQUEST_URL = "https://gjbsb.market.alicloudapi.com/ocrservice/advanced"
        self.appcode = appcode
        self.context = ssl._create_unverified_context()
        self.config = utils.load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'ali'  # 添加客户端类型标识

    def get_img(self, img_file):
        if img_file.startswith("http"):
            return img_file
        else:
            with open(os.path.expanduser(img_file), 'rb') as f:
                data = f.read()
        try:
            return str(base64.b64encode(data), 'utf-8')
        except TypeError:
            return base64.b64encode(data)

    def posturl(self, headers, body):
        try:
            params = json.dumps(body).encode(encoding='UTF8')
            req = Request(self.REQUEST_URL, params, headers)
            r = urlopen(req, context=self.context)
            return r.read().decode("utf8")
        except HTTPError as e:
            return json.dumps({"error": f"HTTP错误: {e.code}", "details": e.read().decode("utf8")})

    def extract_matches(self, response_text):
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return None

        words_info = data.get("prism_wordsInfo", [])
        for item in words_info:
            word = item.get("word", "").strip()
            if self.pattern.fullmatch(word):
                return word.upper()
        return None

    def recognize(self, img_file, params=None):
        if not self.appcode:
            return {"success": False, "error": "未提供AppCode"}

        if params is None:
            params = {
                "prob": False,
                "charInfo": False,
                "rotate": False,
                "table": False,
                "sortPage": False,
                "noStamp": False,
                "figure": False,
                "row": False,
                "paragraph": False,
                "oricoord": False
            }

        img = self.get_img(img_file)
        if img.startswith('http'):
            params.update({'url': img})
        else:
            params.update({'img': img})

        headers = {
            'Authorization': f'APPCODE {self.appcode}',
            'Content-Type': 'application/json; charset=UTF-8'
        }

        response = self.posturl(headers, params)
        result = self.extract_matches(response)

        if result:
            return {"success": True, "result": result, "raw": response}
        else:
            return {"success": False, "error": "未识别到匹配模式", "raw": response}


class LocalClient:
    def __init__(self, max_retries=3):
        self.config = utils.load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'local'  # 添加客户端类型标识
        self.reader = None
        self.max_retries = max_retries
        self._initialize_reader()

    def _initialize_reader(self):
        import time
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                log_print(f"正在尝试加载OCR模型 (尝试 {retry_count + 1}/{self.max_retries})...")
                self.reader = easyocr.Reader(['en'], gpu=False)
                log_print("OCR模型加载成功")
                return
            except Exception as e:
                error_msg = f"模型加载失败: {str(e)}"
                log_print(error_msg)
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = min(2 ** retry_count, 10)  # 指数退避，最大10秒
                    log_print(f"{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    log_print(f"达到最大重试次数 ({self.max_retries})，无法加载OCR模型")
                    # 仍然抛出异常，让调用者知道初始化失败
                    raise RuntimeError(f"无法加载OCR模型，错误: {str(e)}")

    def get_img(self, img_file):
        return img_file  # 本地识别直接使用文件路径

    def optimized_preprocess(self, img_path, max_size=800):
        try:
            image = Image.open(img_path)

            if max(image.size) > max_size:
                scale = max_size / max(image.size)
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            gray_image = image.convert('L')
            return np.array(gray_image)
        except Exception as e:
            log_print(f"图像预处理错误: {str(e)}")
            return None

    def extract_matches(self, texts):
        for text in texts:
            if self.pattern.fullmatch(text.strip()):
                return text.strip().upper()
        return None

    def recognize(self, img_file, params=None):
        processed_image = self.optimized_preprocess(img_file)

        if processed_image is not None:
            result = self.reader.readtext(processed_image, detail=0)
            matched_result = self.extract_matches(result)
            raw_result = json.dumps({"texts": result})

            if matched_result:
                return {"success": True, "result": matched_result, "raw": raw_result}
            else:
                return {"success": False, "error": "未识别到匹配模式", "raw": raw_result}
        else:
            return {"success": False, "error": "图像预处理失败", "raw": "{}"}


class DouyinClient:
    def __init__(self, api_key, base_url="https://api.coze.cn/v1", timeout=30, max_retries=3, backoff_factor=1.0,
                 proxies=None):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.proxies = proxies
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.client_type = "抖音服务"

    def _create_session(self):
        session = requests.Session()
        retry_strategy = requests.adapters.Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        return session

    def run_workflow(self, workflow_id, parameters=None, bot_id=None, is_async=False):
        api_url = f"{self.base_url}/workflow/run"
        payload = {"workflow_id": workflow_id, "is_async": is_async}

        if parameters:
            payload["parameters"] = parameters
        if bot_id:
            payload["bot_id"] = bot_id

        session = self._create_session()
        try:
            response = session.post(
                api_url,
                json=payload,
                timeout=self.timeout,
                proxies=self.proxies
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                return {
                    "success": True,
                    "data": result.get("data"),
                    "debug_url": result.get("debug_url"),
                    "execute_id": result.get("execute_id"),
                    "usage": result.get("usage")
                }
            else:
                return {
                    "success": False,
                    "error_code": result.get("code"),
                    "error_msg": result.get("msg"),
                    "logid": result.get("detail", {}).get("logid")
                }

        except Exception as e:
            return {"success": False, "error_msg": f"请求异常: {str(e)}"}
        finally:
            session.close()

    def recognize(self, img_file, params=None):
        """统一接口：处理图像识别，兼容本地文件路径和URL"""
        # 处理参数，设置超时
        retry_count = 0
        max_retries = self.max_retries
        backoff_factor = self.backoff_factor

        while retry_count <= max_retries:
            # 计算退避时间
            if retry_count > 0:
                sleep_time = backoff_factor * (2 ** (retry_count - 1))
                log_print(f"请求失败，{sleep_time:.2f}秒后重试...")
                time.sleep(sleep_time)

            try:
        request_timeout = self.timeout
        if params and isinstance(params, dict):
            request_timeout = params.get('timeout', self.timeout)

        if not self.api_key:
            return {"success": False, "error": "未提供抖音API Key", "raw": ""}

        # 从配置中获取workflow_id
        workflow_id = "7514709270924361743"
        if not workflow_id:
            return {"success": False, "error": "缺少必要配置参数: DOUYIN_WORKFLOW_ID", "raw": ""}

        # 准备参数，支持本地文件路径和URL
        image_url = img_file

        parameters = {
            "prompt": "识别图像中【纯白色小卡片】上的红色目标文字：  1. 卡片特征：纯白色背景（无其他颜色或图案），尺寸较小（通常占图像面积5%-20%），可能倾斜/部分边缘轻微遮挡（遮挡不超过20%），表面有黑色手写数字（与目标无关，可忽略）。 2. 目标文字要求：   - 颜色：正红色（RGB参考值255,0,0，非暗红/粉红）；   - 字体：无衬线大写字母（如Arial、Helvetica风格，无装饰性笔画）；   - 格式：严格为1个大写字母（A-K，仅A至K）直接衔接1个数字（1-7，仅1至7），无空格/符号/多余字符。 3. 输出规则：仅输出符合上述全部条件的标签（如：B3）；若未识别到或存在多个符合项，输出“识别失败”。无需任何额外说明。",
            "image": image_url
        }

        if params:
            parameters.update(params)

                # 运行工作流
                result = self.run_workflow(
                    workflow_id=workflow_id,
                    parameters=parameters,
                    bot_id=None,
                    is_async=False,  # 修改为同步执行以便获取结果
                )

                log_print(f"请求结果: {result}")

                # 解析并打印结果
                parsed_result = self.parse_ocr_result(result)
                log_print(f"工作流处理结果: {parsed_result}")

                # 即使没有execute_id也继续，因为有些API响应可能不包含它
                execute_id = result.get('execute_id')
                
                if not result['success']:
                    error_code = result.get('error_code')
                    error_msg = result.get('error_msg', '工作流运行失败')
                     
                    # 对错误码4024(请求频率过高)进行重试
                    if error_code == 4024 and retry_count < max_retries:
                        retry_count += 1
                        log_print(f"请求频率过高(错误码4024)，正在进行第{retry_count}次重试...")
                        continue
                     
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_code': error_code,
                        'raw': str(result)
                    }

                return {
                    'success': True,
                    'result': parsed_result,
                    'execute_id': execute_id,
                    'raw': str(result)
                }

            except Exception as e:
                # 网络异常也可以重试
                if retry_count < max_retries:
                    retry_count += 1
                    log_print(f"请求异常: {str(e)}，正在进行第{retry_count}次重试...")
                    continue
                error_msg = f'识别过程异常: {str(e)}'
                log_print(error_msg)
                return {'success': False, 'error': error_msg, 'raw': str(e)}

        # 达到最大重试次数
        return {'success': False, 'error': f'达到最大重试次数({max_retries})，请求失败', 'raw': ''}

    def parse_ocr_result(self, ocr_data):
        if not ocr_data.get('success'):
            return f"处理失败: {ocr_data.get('error_msg', '未知错误')}"

        data = ocr_data.get('data', '')
        try:
            # 尝试解析数据
            if isinstance(data, dict):
                text = data.get('msg', str(data))
            else:
                # 尝试将字符串解析为JSON
                json_data = json.loads(data)
                text = json_data.get('msg', str(data))
        except (json.JSONDecodeError, TypeError):
            text = str(data)

        # 应用正则表达式验证结果格式
        pattern = re.compile(".*")
        if pattern.match(text):
            return text.upper()
        else:
            return text if text else "未识别到有效内容"


class BaiduClient:
    def __init__(self, api_key=None, secret_key=None):
        self.REQUEST_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = ''
        self.context = ssl._create_unverified_context()
        self.config = utils.load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'baidu'  # 添加客户端类型标识

    def get_access_token(self):
        if not self.access_token:
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            try:
                req = Request(f"{token_url}?{urllib.parse.urlencode(params)}")
                r = urlopen(req, context=self.context)
                data = json.loads(r.read().decode("utf8"))
                self.access_token = data.get("access_token", "")
            except Exception as e:
                log_print(f"获取百度access_token失败: {str(e)}")
        return self.access_token

    def get_img(self, img_file):
        with open(os.path.expanduser(img_file), 'rb') as f:
            data = f.read()
        return str(base64.b64encode(data), 'utf-8')

    def posturl(self, headers, body):
        try:
            req = Request(self.REQUEST_URL + "?access_token=" + self.access_token, body.encode("utf-8"), headers)
            r = urlopen(req, context=self.context)
            return r.read().decode("utf8")
        except HTTPError as e:
            return json.dumps({"error": f"HTTP错误: {e.code}", "details": e.read().decode("utf8")})

    def extract_matches(self, response_text):
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return None

        words_result = data.get("words_result", [])
        for item in words_result:
            word = item.get("words", "").strip()
            if self.pattern.fullmatch(word):
                return word.upper()
        return None

    def recognize(self, img_file, params=None):
        if not self.api_key or not self.secret_key:
            return {"success": False, "error": "未提供百度API Key或Secret Key"}

        self.get_access_token()
        if not self.access_token:
            return {"success": False, "error": "获取百度access_token失败"}

        img = self.get_img(img_file)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        body = f"image={urllib.parse.quote(img)}"
        if params:
            body += "&" + urllib.parse.urlencode(params)

        response = self.posturl(headers, body)
        result = self.extract_matches(response)

        if result:
            return {"success": True, "result": result, "raw": response}
        else:
            return {"success": False, "error": "未识别到匹配模式", "raw": response}


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.source_dir = ""
        self.dest_dir = ""
        self.is_move_mode = False
        self.processing_thread = None
        self.image_files = []
        self.processing = False
        self.processing_start_time = 0

        self.dragging = False
        self.drag_position = QtCore.QPoint()

        utils.main_window = self
        self.config = utils.load_config()
        self._init_ui_components()
        self.setup_connections()

        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("LeafView-RailwayOCR")
        self.setWindowIcon(QtGui.QIcon(get_resource_path('resources/img/icon.ico')))

        log("INFO", "LeafView-RailwayOCR 启动成功.")

    def _init_ui_components(self):
        self.total_files_label.setText("0")
        self.processed_label.setText("0")
        self.success_label.setText("0")
        self.failed_label.setText("0")

        self.copy_radio.setChecked(True)
        self.move_radio.setChecked(False)
        self.pushButton_start.setText("开始分类")

        self.textEdit_log.setReadOnly(True)

    def setup_connections(self):
        self.pushButton_src_folder.clicked.connect(self.browse_source_directory)
        self.pushButton_dst_folder.clicked.connect(self.browse_dest_directory)

        self.pushButton_start.clicked.connect(self.toggle_processing)
        self.copy_radio.toggled.connect(self.toggle_move_mode)
        self.move_radio.toggled.connect(self.toggle_move_mode)

        self.toolButton_setting.clicked.connect(self.open_setting)
        self.toolButton_close.clicked.connect(self.close_application)
        self.toolButton_mini.clicked.connect(self.minimize_window)

    def open_setting(self):
        self.setting_window = SettingWindow()
        self.setting_window.show()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def browse_source_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择源文件夹")

        if directory:
            self.source_dir = directory
            self.lineEdit_src_folder.setText(directory)
            log("INFO", f"已选择源文件夹: {directory}")

            if not self.check_directory_conflict():
                self.load_images()

    def browse_dest_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择目标文件夹")

        if directory:
            self.dest_dir = directory
            self.lineEdit_dst_folder.setText(directory)
            log("INFO", f"已选择目标文件夹: {directory}")
            self.check_directory_conflict()

    def load_images(self):
        self.image_files = []

        if not self.source_dir or not os.path.exists(self.source_dir):
            log("WARNING", "源文件夹不存在或未设置")
            return

        for root, _, files in os.walk(self.source_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.config["ALLOWED_EXTENSIONS"]):
                    file_path = os.path.join(root, file)
                    self.image_files.append(file_path)

        total_count = len(self.image_files)
        self.total_files_label.setText(str(total_count))
        log("INFO", f"扫描完成，发现 {total_count} 个图像文件")

    def toggle_move_mode(self):
        self.is_move_mode = self.move_radio.isChecked()

    def check_directory_conflict(self):
        if not (self.source_dir and self.dest_dir):
            return False

        try:
            source_abs = os.path.abspath(self.source_dir)
            dest_abs = os.path.abspath(self.dest_dir)

            if dest_abs == source_abs or os.path.commonpath([source_abs, dest_abs]) == source_abs:
                log("ERROR", "文件夹冲突: 目标文件夹不能是源文件夹或其子文件夹")
                QMessageBox.warning(
                    self, "文件夹冲突",
                    "目标文件夹不能是源文件夹或其子文件夹！这可能导致文件覆盖或其他意外行为。"
                )

                self.source_dir = ""
                self.dest_dir = ""
                self.lineEdit_src_folder.setText("待处理文件夹（默认包含子文件夹）")
                self.lineEdit_dst_folder.setText("存放分类后的结果")
                self.image_files = []
                self.total_files_label.setText("0")
                return True

        except Exception as e:
            log("ERROR", f"文件夹检查出错: {str(e)}")

        return False

    def toggle_processing(self):
        if self.processing:
            self.stop_processing()
        else:
            self.start_processing()

    def start_processing(self):
        if not self._validate_processing_conditions():
            return

        total_files = len(self.image_files)
        mode = "移动" if self.is_move_mode else "复制"
        reply = QMessageBox.question(
            self, "确认处理",
            f"即将识别分类 {total_files} 个图像并 {mode} 。\n是否继续?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            log("INFO", "用户取消处理操作")
            log_print("用户取消处理操作")
            return

        self.processing_start_time = time.time()

        log("WARNING", "开始文件处理流程")
        log_print(f"开始处理 {len(self.image_files)} 个图像文件")
        self.processing = True
        self.pushButton_start.setText("停止分类")
        self.progressBar.setValue(0)

        try:
            mode_index = self.config.get("MODE_INDEX", 0)

            # 根据模式索引创建对应的客户端
            if mode_index == 0:
                # 阿里云模式
                appcode = self.config.get("ALI_CODE")
                if not appcode:
                    QMessageBox.critical(self, "错误", "未配置阿里云AppCode")
                    log("ERROR", "未配置阿里云AppCode")
                    return
                client = AliClient(appcode=appcode)
                log("INFO", "使用阿里云OCR模式")
            elif mode_index == 1:
                # 本地模式
                try:
                    client = LocalClient(max_retries=5)
                    log("INFO", "使用本地OCR模式")
                except Exception as e:
                    error_msg = f"本地OCR模型加载失败: {str(e)}"
                    log("ERROR", error_msg)
                    QMessageBox.critical(self, "模型加载失败", f"无法加载OCR模型: {str(e)}\n请检查网络连接并重试。")
                    return
            elif mode_index == 2:
                # 抖音云模式
                api_key = self.config.get("DOUYIN_API_KEY")
                if not api_key:
                    QMessageBox.critical(self, "错误", "未配置抖音API Key")
                    log("ERROR", "未配置抖音API Key")
                    return
                # 从配置获取超时参数
                timeout = self.config.get("REQUEST_TIMEOUT", 60)
                client = DouyinClient(
                    api_key=api_key,
                    timeout=timeout,
                    max_retries=self.config.get("RETRY_TIMES", 3),
                    backoff_factor=self.config.get("BACKOFF_FACTOR", 1.0)
                )
                log("INFO", "使用抖音云OCR模式")
            elif mode_index == 3:
                # 百度云模式
                api_key = self.config.get("BAIDU_API_KEY")
                secret_key = self.config.get("BAIDU_SECRET_KEY")
                if not api_key or not secret_key:
                    QMessageBox.critical(self, "错误", "未配置百度云API Key或Secret Key")
                    log("ERROR", "未配置百度云API Key或Secret Key")
                    return
                client = BaiduClient(api_key=api_key, secret_key=secret_key)
                log("INFO", "使用百度云OCR模式")
            else:
                QMessageBox.critical(self, "错误", f"无效的模式索引: {mode_index}")
                log("ERROR", f"无效的模式索引: {mode_index}")
                return

            # 创建处理线程
            self.processing_thread = ProcessingThread(
                client, self.image_files, self.dest_dir, self.is_move_mode
            )
            self.processing_thread.processing_finished.connect(self.on_processing_finished)
            self.processing_thread.stats_updated.connect(self.on_stats_updated)
            self.processing_thread.progress_updated.connect(self.on_progress_updated)
            self.processing_thread.processing_stopped.connect(self.on_processing_stopped)
            self.processing_thread.error_occurred.connect(self.on_error_occurred)

            self.processing_thread.start()
            log("INFO", "正在连接到OSS和图像识别服务器，请耐心等待")

        except Exception as e:
            error_msg = f"启动处理线程失败: {str(e)}"
            log("ERROR", error_msg)
            log_print(error_msg)
            self.processing = False
            self.pushButton_start.setText("开始分类")

    def _validate_processing_conditions(self):
        if not self.lineEdit_src_folder.text().strip():
            log("WARNING", "未选择源文件夹")
            QMessageBox.warning(self, "参数缺失", "请先选择源文件夹")
            return False

        if not self.lineEdit_dst_folder.text().strip():
            log("WARNING", "未选择目标文件夹")
            QMessageBox.warning(self, "参数缺失", "请先选择目标文件夹")
            return False

        if not self.image_files:
            log("WARNING", "源文件夹中没有图像文件")
            QMessageBox.warning(self, "文件缺失", "源文件夹中未发现任何图像文件")
            return False

        mode_index = self.config.get("MODE_INDEX", 0)

        if mode_index == 0 and not self.config.get("ALI_CODE"):
            log("WARNING", "未配置阿里云AppCode")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置阿里云AppCode")
            return False
        elif mode_index == 1:
            # 本地模式不需要API密钥
            pass
        elif mode_index == 2 and not self.config.get("DOUYIN_API_KEY"):
            log("WARNING", "未配置抖音API Key")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置抖音API Key")
            return False
        elif mode_index == 3 and not (self.config.get("BAIDU_API_KEY") and self.config.get("BAIDU_SECRET_KEY")):
            log("WARNING", "未配置百度API Key或Secret Key")
            QMessageBox.warning(self, "配置缺失", "请先在设置中配置百度API Key和Secret Key")
            return False

        return True

    def stop_processing(self):
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止处理吗? 当前进度将会丢失。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            log("WARNING", "用户请求停止处理")
            self.pushButton_start.setText("正在刹停")
            self.pushButton_start.setEnabled(False)
            self.processing = False

            if self.processing_thread and self.processing_thread.isRunning():
                self.processing_thread.stop()

    @QtCore.pyqtSlot(int, str)
    def on_progress_updated(self, value, message):
        self.progressBar.setValue(value)

    @QtCore.pyqtSlot(int, int, int)
    def on_stats_updated(self, processed, success, failed):
        self.processed_label.setText(str(processed))
        self.success_label.setText(str(success))
        self.failed_label.setText(str(failed))

    @QtCore.pyqtSlot(list)
    def on_processing_finished(self, results):
        self.processing = False
        processing_end_time = time.time()
        total_seconds = int(processing_end_time - self.processing_start_time)
        total_time = str(timedelta(seconds=total_seconds))

        total_count = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total_count - success_count
        success_rate = f"{(success_count / total_count * 100) if total_count > 0 else 0:.2f}%"

        log("INFO", "=" * 50)
        log("INFO", f"处理完成 | 总耗时: {total_time}")
        log("INFO", f"总文件数: {total_count} | 成功: {success_count} | 失败: {failed_count}")
        log("INFO", f"识别率: {success_rate}")
        log("INFO", "=" * 50)

        log_print(f"处理完成，总耗时: {total_time}")
        log_print(f"总文件数: {total_count}, 成功: {success_count}, 失败: {failed_count}, 识别率: {success_rate}")

        stats = save_summary(results)
        if stats:
            log_print(f"统计信息已保存到summary文件夹")

        if total_count > 0:
            result_message = (
                f"LeafView-RailWayORC 处理完成!\n\n"
                f"总文件数: {total_count}\n"
                f"成功识别: {success_count}\n"
                f"识别失败: {failed_count}\n"
                f"识别率: {success_rate}\n"
                f"总共耗时: {total_time}"
            )
            QMessageBox.information(self, "处理完成", result_message)
        self.pushButton_start.setEnabled(True)
        self.pushButton_start.setText("开始分类")
        save_summary(results)

    @QtCore.pyqtSlot()
    def on_processing_stopped(self):
        log("INFO", "处理已停止")
        self.processing = False

    @QtCore.pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        log("ERROR", f"处理线程错误: {error_msg}")
        QMessageBox.critical(self, "处理错误", error_msg)
        self.processing = False

    def minimize_window(self):
        log("INFO", "窗口最小化")
        self.showMinimized()

    def close_application(self):
        if self.processing:
            reply = QMessageBox.question(
                self, "确认关闭",
                "当前正在处理文件，关闭将终止处理过程。\n确定要关闭吗?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            if self.processing_thread:
                self.processing_thread.stop()

        log("INFO", "应用程序即将关闭")
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
