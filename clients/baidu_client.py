"""百度OCR客户端实现

提供百度OCR服务的客户端封装，支持图片识别和结果提取功能
"""
import base64
import json
import re
import ssl
import threading
import urllib.parse
from typing import Optional, Union
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import requests

from utils import load_config, log, log_print
from .base_client import BaseClient


class BaiduClient(BaseClient):
    """百度OCR客户端类
    
    继承自BaseClient，实现百度OCR服务的具体功能
    """
    client_type: str = "baidu"

    def __init__(self):
        self.api_lock = threading.Lock()
        self.request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        self.config = load_config()
        self.api_key = self.config.get("BAIDU_API_KEY", "")
        self.secret_key = self.config.get("BAIDU_SECRET_KEY", "")
        self.access_token = ""
        self.context = ssl._create_unverified_context()

    def get_access_token(self):
        """获取百度OCR访问令牌
        
        通过API密钥和密钥获取访问令牌，用于后续OCR请求认证
        
        Returns:
            str: 访问令牌字符串，如果获取失败则返回空字符串
        """
        if not self.access_token:
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            try:
                with self.api_lock:
                    response = requests.post(token_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token", "")
                else:
                    error_msg = f"获取token失败: {response.status_code} - {response.text}"
                    raise requests.exceptions.HTTPError(error_msg)
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                log("ERROR", "百度OCR认证失败，请检查API密钥")
                log_print(f"[百度认证] 获取access_token失败: {str(e)} "
                         f"(API_KEY:{self.api_key[:4]}****)")
        return self.access_token

    def posturl(self, headers, body):
        """发送POST请求到百度OCR API
        
        Args:
            headers: 请求头信息
            body: 请求体内容
            
        Returns:
            str: API响应内容
        """
        try:
            req_url = f"{self.request_url}?access_token={self.access_token}"
            req = Request(req_url, body.encode("utf-8"), headers)
            with urlopen(req, context=self.context) as r:
                return r.read().decode("utf8")
        except HTTPError as e:
            return json.dumps({"error": f"HTTP错误: {e.code}", "details": e.read().decode("utf8")})

    def extract_matches(self, texts, pattern: re.Pattern):
        """从API响应中提取匹配结果
        
        Args:
            texts: API响应文本
            pattern: 正则表达式模式对象
            
        Returns:
            Optional[str]: 匹配到的文本内容，如果没有匹配则返回None
        """
        try:
            data = json.loads(texts)
        except json.JSONDecodeError:
            return None

        words_result = data.get("words_result", [])
        for item in words_result:
            word = item.get("words", "").strip()
            if pattern.fullmatch(word):
                return word.upper()
        return None

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        """识别图像中的文本内容
        
        Args:
            image_source: 图像源，可以是文件路径、字节数据或URL
            is_url: 是否为URL图像源
            
        Returns:
            Optional[str]: 识别到的文本内容，识别失败返回None
        """
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
                response = requests.get(image_source, timeout=10)
                image_data = response.content
                img_base64 = str(base64.b64encode(image_data), 'utf-8')
            else:
                img_base64 = str(base64.b64encode(image_source), 'utf-8')

            body = urllib.parse.urlencode({"image": img_base64})
            response = self.posturl(headers, body)
            pattern = re.compile(self.config.get("RE", r'.*'))
            result = self.extract_matches(response, pattern)
            return self.process_recognition_result(result, image_source, is_url)
        except (requests.exceptions.RequestException, IOError, ValueError) as e:
            log("ERROR", f"图像识别请求失败: {str(e)}")
            return None
