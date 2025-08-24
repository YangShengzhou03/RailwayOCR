import base64
import json
import os
import re
import ssl
import time
import urllib.parse
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import easyocr
import numpy as np
import requests
from PIL import Image
import multiprocessing

from utils import load_config, log_print, log


class AliClient:
    def __init__(self, appcode=None):
        self.REQUEST_URL = "https://gjbsb.market.alicloudapi.com/ocrservice/advanced"
        self.appcode = appcode
        self.context = ssl._create_unverified_context()
        self.config = load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'ali'

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
    def __init__(self, max_retries=3, gpu=False):
        self.config = load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-K][1-7]$'))
        self.client_type = 'local'
        self.reader = None
        self.max_retries = max_retries
        self.gpu = gpu
        self._reader_lock = multiprocessing.Lock()

        cpu_count = multiprocessing.cpu_count()
        max_threads_limit = max(1, cpu_count // 4)
        json_threads = self.config.get("CONCURRENCY", 1)
        self.max_threads = min(json_threads, max_threads_limit)
        log_print(f"[DEBUG] CPU核心数: {cpu_count}, 最大限制线程数: {max_threads_limit}, JSON配置线程数: {json_threads}, 最终设置线程数: {self.max_threads}")

        self._initialize_reader()

    def _initialize_reader(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                log_print(f"[DEBUG] 正在尝试加载OCR模型 (尝试 {retry_count + 1}/{self.max_retries})...")
                with self._reader_lock:
                    self.reader = easyocr.Reader(['en'], gpu=self.gpu)
                log("INFO", "OCR模型加载成功")
                return
            except Exception as e:
                error_msg = f"模型加载失败: {str(e)}"
                log("ERROR", error_msg)
                log_print(f"[ERROR] {error_msg}")
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = min(2 ** retry_count, 10)
                    log_print(f"[DEBUG] {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    log("ERROR", f"达到最大重试次数 ({self.max_retries})，无法加载OCR模型")
                    raise RuntimeError(f"无法加载OCR模型，错误: {str(e)}")

    def get_img(self, img_file):
        return img_file

    def optimized_preprocess(self, img_path, max_size=800):
        try:
            image = Image.open(img_path)

            if not self.gpu and max(image.size) > max_size:
                scale = max_size / max(image.size)
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                log_print(f"[DEBUG] 图像已缩放至: {new_size}")
            elif self.gpu:
                log_print(f"[DEBUG] 使用GPU加速，不缩放图像")

            gray_image = image.convert('L')
            result = np.array(gray_image)
            image.close()
            return result
        except Exception as e:
            error_msg = f"图像预处理错误: {str(e)}"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            return None

    def extract_matches(self, texts):
        for text in texts:
            if self.pattern.fullmatch(text.strip()):
                return text.strip().upper()
        return None

    def recognize(self, img_file, params=None):
        start_time = time.time()
        processed_image = self.optimized_preprocess(img_file)

        if processed_image is not None:
            try:
                with self._reader_lock:
                    result = self.reader.readtext(processed_image, detail=0)
                matched_result = self.extract_matches(result)
                raw_result = json.dumps({"texts": result})
                processing_time = time.time() - start_time

                log_print(f"[DEBUG] 本地OCR识别完成，耗时: {processing_time:.2f}秒")

                if matched_result:
                    log("INFO", f"识别成功: {matched_result}")
                    log_print(f"[INFO] 识别成功: {matched_result}")
                    return {"success": True, "result": matched_result, "raw": raw_result,
                            "processing_time": processing_time}
                else:
                    log("WARNING", "未识别到匹配模式")
                    log_print("[WARNING] 未识别到匹配模式")
                    return {"success": False, "error": "未识别到匹配模式", "raw": raw_result,
                            "processing_time": processing_time}
            except Exception as e:
                error_msg = f"OCR识别异常: {str(e)}"
                log("ERROR", error_msg)
                log_print(f"[ERROR] {error_msg}")
                return {"success": False, "error": error_msg, "raw": str(e)}
            finally:
                del processed_image  # 显式释放内存
        else:
            log("ERROR", "图像预处理失败")
            log_print("[ERROR] 图像预处理失败")
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
        self.config = load_config()
        self.workflow_id = self.config.get("DOUYIN_WORKFLOW_ID", "7514709270924361743")
        self.prompt = self.config.get("DOUYIN_PROMPT", "识别图像中【纯白色小卡片】上的红色目标文字...")

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
                error_code = result.get("code")
                error_msg = result.get("msg", "工作流运行失败")
                log("ERROR", f"工作流运行失败: 错误码 {error_code}, 错误信息: {error_msg}")
                log_print(f"[ERROR] 工作流运行失败: 错误码 {error_code}, 错误信息: {error_msg}")
                return {
                    "success": False,
                    "error_code": error_code,
                    "error_msg": error_msg,
                    "logid": result.get("detail", {}).get("logid")
                }

        except requests.exceptions.Timeout:
            log("ERROR", f"请求超时: {self.timeout}秒")
            log_print(f"[ERROR] 请求超时: {self.timeout}秒")
            return {"success": False, "error_msg": f"请求超时: {self.timeout}秒"}
        except requests.exceptions.ConnectionError:
            log("ERROR", "网络连接错误")
            log_print("[ERROR] 网络连接错误")
            return {"success": False, "error_msg": "网络连接错误"}
        except requests.exceptions.HTTPError as e:
            log("ERROR", f"HTTP错误: {e.response.status_code}, {e.response.text}")
            log_print(f"[ERROR] HTTP错误: {e.response.status_code}, {e.response.text}")
            return {"success": False, "error_msg": f"HTTP错误: {e.response.status_code}"}
        except Exception as e:
            log("ERROR", f"请求异常: {str(e)}")
            log_print(f"[ERROR] 请求异常: {str(e)}")
            return {"success": False, "error_msg": f"请求异常: {str(e)}"}
        finally:
            session.close()

    def recognize(self, img_file, params=None):
        retry_count = 0
        max_retries = self.max_retries
        backoff_factor = self.backoff_factor
        request_timeout = self.timeout

        if params and isinstance(params, dict):
            request_timeout = params.get('timeout', self.timeout)

        if not self.api_key:
            error_msg = "未提供抖音API Key"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg, "raw": ""}

        if not self.workflow_id:
            error_msg = "缺少必要配置参数: DOUYIN_WORKFLOW_ID"
            log("ERROR", error_msg)
            log_print(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg, "raw": ""}

        default_params = {
            "prompt": self.prompt,
            "image": img_file
        }

        if params:
            default_params.update(params)

        while retry_count <= max_retries:
            if retry_count > 0:
                sleep_time = backoff_factor * (2 ** (retry_count - 1))
                log_print(f"[DEBUG] 请求失败，{sleep_time:.2f}秒后重试... (重试 {retry_count}/{max_retries})")
                time.sleep(sleep_time)

            try:
                result = self.run_workflow(
                    workflow_id=self.workflow_id,
                    parameters=default_params,
                    bot_id=None,
                    is_async=False,
                )

                log_print(f"[DEBUG] 请求结果: {result}")

                parsed_result = self.parse_ocr_result(result)
                log("INFO", f"工作流处理结果: {parsed_result}")
                log_print(f"[INFO] 工作流处理结果: {parsed_result}")

                execute_id = result.get('execute_id')

                if not result['success']:
                    error_code = result.get('error_code')
                    error_msg = result.get('error_msg', '工作流运行失败')

                    if error_code == 4024 and retry_count < max_retries:
                        retry_count += 1
                        log_print(f"[DEBUG] 请求频率过高(错误码4024)，正在进行第{retry_count}次重试...")
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
                if retry_count < max_retries:
                    retry_count += 1
                    log_print(f"[DEBUG] 请求异常: {str(e)}，正在进行第{retry_count}次重试...")
                    continue
                error_msg = f'识别过程异常: {str(e)}'
                log_print(error_msg)
                return {'success': False, 'error': error_msg, 'raw': str(e)}

        error_msg = f'达到最大重试次数({max_retries})，请求失败'
        log_print(error_msg)
        return {'success': False, 'error': error_msg, 'raw': ''}

    def parse_ocr_result(self, ocr_data):
        if not ocr_data.get('success'):
            return f"处理失败: {ocr_data.get('error_msg', '未知错误')}"

        data = ocr_data.get('data', '')
        try:
            if isinstance(data, dict):
                text = data.get('msg', str(data))
            else:
                json_data = json.loads(data)
                text = json_data.get('msg', str(data))
        except (json.JSONDecodeError, TypeError):
            text = str(data)

        pattern = re.compile(r'^[A-K][1-7]$')
        if pattern.match(text.strip()):
            return text.strip().upper()
        elif text.strip() == "识别失败":
            return text.strip()
        else:
            return f"未识别到有效内容: {text}" if text else "未识别到有效内容"


class BaiduClient:
    def __init__(self, api_key=None, secret_key=None):
        self.REQUEST_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = ''
        self.context = ssl._create_unverified_context()
        self.config = load_config()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'baidu'

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
                log("ERROR", f"获取百度access_token失败: {str(e)}")
                log_print(f"[ERROR] 获取百度access_token失败: {str(e)}")
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
