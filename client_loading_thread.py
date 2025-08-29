"""
异步客户端加载线程模块

该模块提供异步加载OCR客户端的功能，避免在应用程序启动时阻塞UI线程。
"""

import traceback
from PyQt6.QtCore import QThread, pyqtSignal
from clients import AliClient, BaiduClient, LocalClient
from clients.paddle_client import PaddleClient
from utils import MODE_ALI, MODE_LOCAL, MODE_BAIDU, MODE_PADDLE, log


class ClientLoadingThread(QThread):
    """
    异步加载OCR客户端的线程类
    
    该类在后台线程中初始化OCR客户端，避免阻塞主线程，提升用户体验。
    
    信号:
        client_loaded: 客户端加载成功时发出，携带客户端实例
        loading_error: 加载失败时发出，携带错误信息
    """
    
    client_loaded = pyqtSignal(object)  # 成功加载的客户端
    loading_error = pyqtSignal(str)   # 错误信息
    
    def __init__(self, config):
        """
        初始化客户端加载线程
        
        Args:
            config: 应用程序配置字典
        """
        super().__init__()
        self.config = config
        self.client = None
        
    def run(self):
        """
        线程主函数，执行客户端加载操作
        
        根据配置选择合适的OCR客户端并初始化，完成后通过信号通知主线程。
        """
        try:
            mode_index = self.config.get("MODE_INDEX", 0)
            
            if mode_index == MODE_ALI:
                self._load_ali_client()
            elif mode_index == MODE_BAIDU:
                self._load_baidu_client()
            elif mode_index == MODE_PADDLE:
                self._load_paddle_client()
            else:
                self._load_local_client()
                
            if self.client:
                log("INFO", f"OCR客户端加载成功: {type(self.client).__name__}")
                self.client_loaded.emit(self.client)
            else:
                raise ValueError("客户端初始化失败")
                
        except Exception as e:
            error_msg = f"客户端加载失败: {str(e)}"
            log("ERROR", error_msg)
            log("DEBUG", f"详细错误信息: {traceback.format_exc()}")
            self.loading_error.emit(str(e))
    
    def _load_ali_client(self):
        """加载阿里云OCR客户端"""
        try:
            appcode = self.config.get("ALI_APPCODE", "")
            if not appcode:
                log("WARNING", "未配置阿里云AppCode，使用本地客户端")
                self._load_local_client()
                return
            self.client = AliClient()
        except Exception as e:
            log("ERROR", f"阿里云客户端加载失败: {str(e)}")
            self._load_local_client()
    
    def _load_baidu_client(self):
        """加载百度云OCR客户端"""
        try:
            api_key = self.config.get("BAIDU_API_KEY")
            secret_key = self.config.get("BAIDU_SECRET_KEY")
            if not api_key or not secret_key:
                log("WARNING", "未配置百度API Key或Secret Key，使用本地客户端")
                self._load_local_client()
                return
            self.client = BaiduClient()
        except Exception as e:
            log("ERROR", f"百度云客户端加载失败: {str(e)}")
            self._load_local_client()
    
    def _load_paddle_client(self):
        """加载飞桨OCR客户端"""
        try:
            self.client = PaddleClient(max_retries=1)
            log("INFO", "飞桨OCR客户端初始化成功")
        except Exception as e:
            log("ERROR", f"飞桨OCR客户端加载失败: {str(e)}")
            self._load_local_client()
    
    def _load_local_client(self):
        """加载本地OCR客户端"""
        try:
            self.client = LocalClient(max_retries=1)
            log("INFO", "本地OCR客户端初始化成功")
        except Exception as e:
            log("ERROR", f"本地客户端加载失败: {str(e)}")
            raise