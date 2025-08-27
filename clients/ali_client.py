"""阿里云OCR客户端实现

提供阿里云OCR服务的客户端封装，支持图片识别和结果提取功能"""
import base64
import json
import os
import re
import ssl
import threading

from typing import Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import requests

from utils import load_config, log
from .base_client import BaseClient


class AliClient(BaseClient):
    """阿里云OCR客户端类

    继承自BaseClient，实现阿里云OCR服务的具体功能
    """
    client_type: str = "ali"
    def __init__(self):
        """初始化阿里云OCR客户端"""
        self.request_url = "https://gjbsb.market.alicloudapi.com/ocrservice/advanced"
        self.config = load_config()
        self.appcode = self.config.get("ALI_APPCODE", "")
        self.context = ssl._create_unverified_context()
        self.pattern = re.compile(self.config.get("RE", r'.*'))
        self.client_type = 'ali'
        self.api_lock = threading.Lock()

    def get_img(self, img_file):
        """获取图片数据，支持本地文件路径或URL

        Args:
            img_file: 图片文件路径或URL

        Returns:
            str: 图片的base64编码字符串或URL字符串
        """
        if img_file.startswith("http"):
            return img_file

        with open(os.path.expanduser(img_file), 'rb') as f:
            data = f.read()
        try:
            return str(base64.b64encode(data), 'utf-8')
        except TypeError:
            return base64.b64encode(data)

    def posturl(self, headers, body):
        """发送POST请求到阿里云OCR API

        Args:
            headers: 请求头信息
            body: 请求体数据

        Returns:
            str: API响应内容
        """
        try:
            params = json.dumps(body).encode(encoding='UTF8')
            req = Request(self.request_url, params, headers)
            with self.api_lock:
                with urlopen(req, context=self.context, timeout=30) as r:
                    return r.read().decode("utf8")
        except HTTPError as e:
            error_msg = f"HTTP错误: {e.code}, 详情: {e.read().decode('utf8')}"
            log("错误", f"识别服务请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except URLError as e:
            error_msg = f"URL错误: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except requests.exceptions.RequestException as e:
            error_msg = f"未知错误: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})
        except TimeoutError as e:
            error_msg = f"请求超时: {str(e)}"
            log("ERROR", f"API请求失败: {error_msg}")
            return json.dumps({"error": error_msg})

    def extract_matches(self, response_text):
        """从API响应中提取匹配的文本结果

        Args:
            response_text: API响应文本

        Returns:
            str: 匹配的文本结果，未找到时返回None
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            truncated_text = response_text[:100] if len(response_text) > 100 else response_text
            log("ERROR", f"响应解析失败: {str(e)}, 响应文本: {truncated_text}")
            return None

        words_info = data.get("prism_wordsInfo", [])
        for item in words_info:
            word = item.get("word", "").strip()
            if self.pattern.fullmatch(word):
                return word.upper()
        return None

    def recognize(self, image_source: Union[str, bytes], is_url: bool = False) -> Optional[str]:
        """识别图片中的文本内容

        Args:
            image_source: 图片源，可以是文件路径、字节数据或URL
            is_url: 是否为URL标识

        Returns:
            str: 识别结果文本，识别失败时返回None
        """
        self.validate_image_source(image_source, is_url)
        params = None
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
            if is_url:
                img_url = image_source
                params.update({'url': img_url})
            else:
                img_base64 = str(base64.b64encode(image_source), 'utf-8')
                params.update({'img': img_base64})

            headers = {
                'Authorization': f'APPCODE {self.appcode}',
                'Content-Type': 'application/json; charset=UTF-8'
            }

            response = self.posturl(headers, params)
            result = self.extract_matches(response)
            return self.process_recognition_result(result, image_source, is_url)
        except (ValueError, IOError, requests.exceptions.RequestException) as e:
            error_msg = f"识别过程中发生错误: {str(e)}"
            log("ERROR", error_msg)
            return None
    