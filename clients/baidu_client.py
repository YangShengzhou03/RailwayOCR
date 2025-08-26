import base64
import json
import os
import re
import ssl
import urllib.parse
import threading
import requests
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from typing import Optional, Union

from utils import load_config, log, log_print

from .base_client import BaseClient


class BaiduClient(BaseClient):
    client_type: str = "baidu"
    def __init__(self):
        self.api_lock = threading.Lock()  # API请求线程锁
        self.REQUEST_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        self.config = load_config()
        self.api_key = self.config.get("BAIDU_API_KEY", "")
        self.secret_key = self.config.get("BAIDU_SECRET_KEY", "")
        self.access_token = ""
        self.context = ssl._create_unverified_context()
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
                with self.api_lock:
                    response = requests.post(token_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token", "")
                else:
                    raise Exception(f"获取token失败: {response.text}")
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                log("ERROR", f"百度OCR认证失败，请检查API密钥")
                log_print(f"[百度认证] 获取access_token失败: {str(e)} (API_KEY:{self.api_key[:4]}****)")
        return self.access_token

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

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        self.validate_image_source(image_source, is_url)
        if not self.api_key or not self.secret_key:
            log("ERROR", "百度API密钥未设置，请在设置中配置")
            return None

        self.get_access_token()
        if not self.access_token:
            log("ERROR", "无法获取访问令牌，请检查网络连接或API密钥")
            return None

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            if is_url:
                # 对于URL，需要先下载图像再编码
                import requests
                response = requests.get(image_source, timeout=10)
                image_data = response.content
                img_base64 = str(base64.b64encode(image_data), 'utf-8')
            else:
                img_base64 = str(base64.b64encode(image_source), 'utf-8')

            body = urllib.parse.urlencode({"image": img_base64})
            response = self.posturl(headers, body)
            result = self.extract_matches(response)
            filename = self.get_image_filename(image_source, is_url)

            if result:
                log("INFO", f"识别成功: {result} (文件: {filename})")
                return result
            else:
                log("WARNING", f"未识别到有效内容 (文件: {filename})")
                return None
        except (requests.exceptions.RequestException, IOError, ValueError) as e:
            log("ERROR", f"图像识别请求失败: {str(e)}")
            log_print(f"[百度API] 识别请求异常: {str(e)} (文件: {filename})")
            return None
    