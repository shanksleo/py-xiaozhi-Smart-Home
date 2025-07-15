import asyncio
import json
import ssl

import websockets

from src.constants.constants import AudioConfig
from src.ha.ha_command_service import parse_command_json
from src.protocols.protocol import Protocol
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

# 导入日志服务
try:
    from src.services.smart_home_logging_service import get_smart_home_logging_service
except ImportError:
    try:
        from services.smart_home_logging_service import get_smart_home_logging_service
    except ImportError:
        # 创建模拟函数用于测试
        def get_smart_home_logging_service():
            class MockLoggingService:
                async def log_smart_home_message(self, data):
                    print(f"模拟日志上报: {data}")
                    return True
            return MockLoggingService()

ssl_context = ssl._create_unverified_context()

logger = get_logger(__name__)


class WebsocketProtocol(Protocol):
    def __init__(self):
        super().__init__()
        # 获取配置管理器实例
        self.config = ConfigManager.get_instance()
        self.websocket = None
        self.connected = False
        self.hello_received = None  # 初始化时先设为 None
        self.WEBSOCKET_URL = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL"
        )
        access_token = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN"
        )
        device_id = self.config.get_config("SYSTEM_OPTIONS.DEVICE_ID")
        client_id = self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID")

        self.HEADERS = {
            "Authorization": f"Bearer {access_token}",
            "Protocol-Version": "1",
            "Device-Id": device_id,  # 获取设备MAC地址
            "Client-Id": client_id,
        }

    async def connect(self) -> bool:
        """
        连接到WebSocket服务器.
        """
        try:
            # 在连接时创建 Event，确保在正确的事件循环中
            self.hello_received = asyncio.Event()

            # 判断是否应该使用 SSL
            current_ssl_context = None
            if self.WEBSOCKET_URL.startswith("wss://"):
                current_ssl_context = ssl_context

            # 建立WebSocket连接 (兼容不同Python版本的写法)
            try:
                # 新的写法 (在Python 3.11+版本中)
                self.websocket = await websockets.connect(
                    uri=self.WEBSOCKET_URL,
                    ssl=current_ssl_context,
                    additional_headers=self.HEADERS,
                )
            except TypeError:
                # 旧的写法 (在较早的Python版本中)
                self.websocket = await websockets.connect(
                    self.WEBSOCKET_URL,
                    ssl=current_ssl_context,
                    extra_headers=self.HEADERS,
                )

            # 启动消息处理循环
            asyncio.create_task(self._message_handler())

            # 发送客户端hello消息
            hello_message = {
                "type": "hello",
                "version": 1,
                "features": {
                    "mcp": True,
                },
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": AudioConfig.INPUT_SAMPLE_RATE,
                    "channels": AudioConfig.CHANNELS,
                    "frame_duration": AudioConfig.FRAME_DURATION,
                },
            }
            await self.send_text(json.dumps(hello_message))

            # 等待服务器hello响应
            try:
                await asyncio.wait_for(self.hello_received.wait(), timeout=10.0)
                self.connected = True
                logger.info("已连接到WebSocket服务器")
                return True
            except asyncio.TimeoutError:
                logger.error("等待服务器hello响应超时")
                if self._on_network_error:
                    self._on_network_error("等待响应超时")
                return False

        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            if self._on_network_error:
                self._on_network_error(f"无法连接服务: {str(e)}")
            return False

    async def delayed_close_audio_channel(self):
        logger.info("准备在10秒后关闭音频通道")
        await asyncio.sleep(10)  # 延迟10秒
        await self.close_audio_channel()
        logger.info("音频通道已关闭")
    async def _message_handler(self):
        """
        处理接收到的WebSocket消息.
        """
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        if msg_type == "hello":
                            # 处理服务器 hello 消息
                            await self._handle_server_hello(data)
                        elif msg_type == "smart_home":
                            # 异步记录日志（不阻塞主流程）
                            asyncio.create_task(self._log_smart_home_message(data))
                            
                            parse_command_json(data)
                            logger.info(f"smart_home data = {data}")
                            # 收到 smart_home 消息后主动断开 websocket 连接
                            logger.info("收到 smart_home 消息，10s主动断开 websocket 连接")
                            asyncio.create_task(self.delayed_close_audio_channel())
                        else:
                            if self._on_incoming_json:
                                self._on_incoming_json(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"无效的JSON消息: {message}, 错误: {e}")
                elif self._on_incoming_audio:  # 使用 elif 更清晰
                    self._on_incoming_audio(message)

        except websockets.ConnectionClosed:
            logger.info("WebSocket连接已关闭")
            self.connected = False
            if self._on_audio_channel_closed:
                # 使用 schedule 确保回调在主线程中执行
                await self._on_audio_channel_closed()
        except Exception as e:
            logger.error(f"消息处理错误: {e}")
            self.connected = False
            if self._on_network_error:
                # 使用 schedule 确保错误处理在主线程中执行
                self._on_network_error(f"连接错误: {str(e)}")

    async def send_audio(self, data: bytes):
        """
        发送音频数据.
        """
        if not self.is_audio_channel_opened():  # 使用已有的 is_connected 方法
            return

        try:
            await self.websocket.send(data)
        except Exception as e:
            if self._on_network_error:
                self._on_network_error(f"发送音频数据失败: {str(e)}")

    async def send_text(self, message: str):
        """
        发送文本消息.
        """
        if self.websocket:
            try:
                await self.websocket.send(message)
            except Exception as e:
                logger.error(f"发送文本消息失败: {e}")
                await self.close_audio_channel()
                if self._on_network_error:
                    self._on_network_error("客户端已关闭")

    def is_audio_channel_opened(self) -> bool:
        """
        检查音频通道是否打开.
        """
        return self.websocket is not None and self.connected

    async def open_audio_channel(self) -> bool:
        """建立 WebSocket 连接.

        如果尚未连接,则创建新的 WebSocket 连接
        Returns:
            bool: 连接是否成功
        """
        logger.info(f"开始打开音频通道 - 当前连接状态: {self.connected}, WebSocket对象: {self.websocket is not None}")
        if not self.connected:
            result = await self.connect()
            logger.info(f"音频通道连接结果: {result}")
            return result
        logger.info("音频通道已经打开")
        return True

    async def _handle_server_hello(self, data: dict):
        """
        处理服务器的 hello 消息.
        """
        try:
            # 验证传输方式
            transport = data.get("transport")
            if not transport or transport != "websocket":
                logger.error(f"不支持的传输方式: {transport}")
                return
            print("服务链接返回初始化配置", data)

            # 设置 hello 接收事件
            self.hello_received.set()

            # 通知音频通道已打开
            if self._on_audio_channel_opened:
                await self._on_audio_channel_opened()

            logger.info("成功处理服务器 hello 消息")

        except Exception as e:
            logger.error(f"处理服务器 hello 消息时出错: {e}")
            if self._on_network_error:
                self._on_network_error(f"处理服务器响应失败: {str(e)}")

    async def _log_smart_home_message(self, data: dict):
        """
        异步记录智能家居消息日志
        
        Args:
            data: smart_home 消息数据
        """
        try:
            logger.info(f"[WebSocket] 开始记录smart_home消息日志")
            
            # 获取日志服务实例
            logging_service = get_smart_home_logging_service()
            
            # 异步上报日志
            success = await logging_service.log_smart_home_message(data)
            
            if success:
                logger.info(f"[WebSocket] smart_home消息日志上报成功")
            else:
                logger.warning(f"[WebSocket] smart_home消息日志上报失败")
                
        except Exception as e:
            logger.error(f"[WebSocket] smart_home消息日志上报异常: {e}")

    async def close_audio_channel(self):
        """
        关闭音频通道.
        """
        logger.info(f"开始关闭音频通道 - 当前连接状态: {self.connected}, WebSocket对象: {self.websocket is not None}")
        if self.websocket:
            try:
                await self.websocket.close()
                self.websocket = None
                self.connected = False
                logger.info("音频通道已关闭")
                if self._on_audio_channel_closed:
                    await self._on_audio_channel_closed()
            except Exception as e:
                logger.error(f"关闭WebSocket连接失败: {e}")
