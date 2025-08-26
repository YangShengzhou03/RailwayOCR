import base64
import json
import os
import re
import ssl
import threading
from asyncio import timeout
from typing import Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import requests

from utils import load_config, log
from .base_client import BaseClient


class AliClient(BaseClient):
    client_type: str = "ali"
    def __init__(self):
        self.REQUEST_URL = "https://gjbsb.market.alicloudapi.com/ocrservice/advanced"
        self.config = load_config()
        self.appcode = self.config.get("ALI_APPCODE", "")
        self.context = ssl._create_unverified_context()
        self.pattern = re.compile(self.config.get("RE", r'^[A-Za-z][0-9]$'))
        self.client_type = 'ali'
        self.api_lock = threading.Lock()  # API请求线程锁

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
            with self.api_lock:
                r = urlopen(req, context=self.context, timeout=30)
            return r.read().decode("utf8")
        except HTTPError as e:
            error_msg = f"HTTP错误: {e.code}, 详情: {e.read().decode('utf8')}"
            log("错误", f"识别服务请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except URLError as e:
            error_msg = f"URL错误: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except timeout as e:
            error_msg = f"请求超时: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except requests.exceptions.RequestException as e:
            error_msg = f"未知错误: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})

    def extract_matches(self, response_text):
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            log("ERROR", f"响应解析失败: {str(e)}, 响应文本: {response_text[:100] if len(response_text) > 100 else response_text}")
            return None

        words_info = data.get("prism_wordsInfo", [])
        for item in words_info:
            word = item.get("word", "").strip()
            if self.pattern.fullmatch(word):
                return word.upper()
        return None

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        self.validate_image_source(image_source, is_url)
        params = None
        # 检查AppCode是否提供
        if not self.appcode:
            log("ERROR", "未提供AppCode, 无法调用API")
            return None

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

        try:
            # Get image data
            if is_url:
                img_url = image_source
                params.update({'url': img_url})
            else:
                img_base64 = str(base64.b64encode(image_source), 'utf-8')
                params.update({'img': img_base64})

            # Prepare headers
            headers = {
                'Authorization': f'APPCODE {self.appcode}',
                'Content-Type': 'application/json; charset=UTF-8'
            }

            # Send request
            response = self.posturl(headers, params)

            # Parse response and extract matches
            result = self.extract_matches(response)
            filename = self.get_image_filename(image_source, is_url)

            if result:
                log("INFO", f"识别成功: {result} (文件: {filename})")
                return result
            else:
                log("WARNING", f"未识别到有效内容 (文件: {filename})")
                return None
        except (ValueError, IOError, requests.exceptions.RequestException) as e:
            error_msg = f"识别过程中发生错误: {str(e)}"
            log("ERROR", error_msg)
            return None