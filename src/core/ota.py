import asyncio
import json
import logging
import socket

import aiohttp
import requests

from src.constants.system import SystemConstants
from src.utils.config_manager import ConfigManager
from src.utils.device_fingerprint import DeviceFingerprint
from src.utils.logging_config import get_logger
from src.ha.ha_data_service import HaDataService
from src.ha.ha_data_post_service import HomeAssistantRegistrationAPI
from src.ha.ha_data_fecth_all_devices_service import HomeAssistantModelAPI
from src.ha.ha_data import ha_service_data

class Ota:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = ConfigManager.get_instance()
        self.device_fingerprint = DeviceFingerprint.get_instance()
        self.mac_addr = None
        self.ota_version_url = None
        self.local_ip = None
        self.system_info = None
        self._update_task = None  # 添加任务引用

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    await instance.init()
                    cls._instance = instance
        return cls._instance

    async def init(self):
        """
        初始化OTA实例.
        """
        self.local_ip = await self.get_local_ip()
        # 从配置中获取设备ID（MAC地址）
        self.mac_addr = self.config.get_config("SYSTEM_OPTIONS.DEVICE_ID")
        # 获取OTA URL
        self.ota_version_url = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL"
        )

    async def get_local_ip(self):
        """
        异步获取本机IP地址.
        """
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._sync_get_ip)
        except Exception as e:
            self.logger.error(f"获取本机 IP 失败：{e}")
            return "127.0.0.1"

    def _sync_get_ip(self):
        """
        同步获取IP地址.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    def build_payload(self):
        """
        构建OTA请求的payload.
        """
        # 从efuse.json获取hmac_key作为elf_sha256
        hmac_key = self.device_fingerprint.get_hmac_key()
        elf_sha256 = hmac_key if hmac_key else "unknown"

        return {
            "application": {
                "version": SystemConstants.APP_VERSION,
                "elf_sha256": elf_sha256,
            },
            "board": {
                "type": SystemConstants.BOARD_TYPE,
                "name": SystemConstants.APP_NAME,
                "ip": self.local_ip,
                "mac": self.mac_addr,
            },
        }

    def build_headers(self):
        """
        构建OTA请求的headers.
        """
        app_version = SystemConstants.APP_VERSION
        board_type = SystemConstants.BOARD_TYPE
        app_name = SystemConstants.APP_NAME

        return {
            "Activation-Version": app_version,
            "Device-Id": self.mac_addr,
            "Client-Id": self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID"),
            "Content-Type": "application/json",
            "User-Agent": f"{board_type}/{app_name}-{app_version}",
            "Accept-Language": "zh-CN",
        }

    async def get_ota_config(self):
        # self.mac_addr = "06:5e:0f:cc:bc:51"
        # self.ota_version_url = "http://134.209.77.247:8002/xiaozhi/ota/"
        """
        获取OTA服务器的配置信息（MQTT、WebSocket等）
        """
        if not self.mac_addr:
            self.logger.error("设备ID(MAC地址)未配置")
            raise ValueError("设备ID未配置")

        if not self.ota_version_url:
            self.logger.error("OTA URL未配置")
            raise ValueError("OTA URL未配置")

        headers = self.build_headers()
        payload = self.build_payload()

        # 添加请求日志
        self.logger.info(f"发送OTA请求到: {self.ota_version_url}")
        self.logger.info(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
        self.logger.info(f"请求数据: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        # 获取应用信息
        app_name = "xiaozhi"
        app_version = "1.6.0"  # 从payload中获取
        board_type = "lc-esp32-s3"  # 立创ESP32-S3开发板
        # 设置请求头
        headers = {
            "Activation-Version": app_version,
            "Device-Id": self.mac_addr,
            "Client-Id": self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID"),
            "Content-Type": "application/json",
            "User-Agent": f"{board_type}/{app_name}-{app_version}",
            "Accept-Language": "zh-CN",  # 添加语言标识，与C++版本保持一致
        }

        # 构建设备信息payload
        payload = {
            "version": 2,
            "flash_size": 16777216,  # 闪存大小 (16MB)
            "psram_size": 8388608,  # 8MB PSRAM
            "minimum_free_heap_size": 7265024,  # 最小可用堆内存
            "mac_address": self.mac_addr,  # 设备MAC地址
            "uuid": self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID"),
            "chip_model_name": "esp32s3",  # 芯片型号
            "chip_info": {
                "model": 9,  # ESP32-S3
                "cores": 2,
                "revision": 0,  # 芯片版本修订
                "features": 20,  # WiFi + BLE + PSRAM
            },
            "application": {
                "name": "xiaozhi",
                "version": "1.6.0",
                "compile_time": "2025-4-16T12:00:00Z",
                "idf_version": "v5.3.2",
            },
            "partition_table": [
                {
                    "label": "nvs",
                    "type": 1,
                    "subtype": 2,
                    "address": 36864,
                    "size": 24576,
                },
                {
                    "label": "otadata",
                    "type": 1,
                    "subtype": 0,
                    "address": 61440,
                    "size": 8192,
                },
                {
                    "label": "app0",
                    "type": 0,
                    "subtype": 0,
                    "address": 65536,
                    "size": 1966080,
                },
                {
                    "label": "app1",
                    "type": 0,
                    "subtype": 0,
                    "address": 2031616,
                    "size": 1966080,
                },
                {
                    "label": "spiffs",
                    "type": 1,
                    "subtype": 130,
                    "address": 3997696,
                    "size": 1966080,
                },
            ],
            "ota": {"label": "app0"},
            "board": {
                "type": "lc-esp32-s3",
                "name": "立创ESP32-S3开发板",
                "features": ["wifi", "ble", "psram", "octal_flash"],
                "ip": self.local_ip,
                "mac": self.mac_addr,
            },
        }
        self.logger.info(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
        self.logger.info(f"请求body: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        try:

            # 发送请求到OTA服务器
            response = requests.post(
                self.ota_version_url,
                headers=headers,
                json=payload,
                timeout=10,  # 设置超时时间，防止请求卡死
                proxies={"http": None, "https": None},  # 禁用代理
            )
            self.logger.info(f"OTA服务器返回状态: {response.status_code}")
            self.logger.info(f"OTA服务器返回数据: {response.text}")
            # 检查HTTP状态码
            if response.status_code != 200:
                self.logger.error(f"OTA服务器错误: HTTP {response.status_code}")
                raise ValueError(f"OTA服务器返回错误状态码: {response.status_code}")

            # 解析JSON数据
            response_data = response.json()
            self.logger.debug(f"OTA 接口数据返回 {response_data}")
            # 调试信息：打印完整的OTA响应
            self.logger.debug(
                f"OTA服务器返回数据: "
                f"{json.dumps(response_data, indent=4, ensure_ascii=False)}"
            )

            print(json.dumps(response_data, indent=4, ensure_ascii=False))

            return response_data
        except asyncio.TimeoutError:
            self.logger.error("OTA请求超时，请检查网络或服务器状态")
            raise ValueError("OTA请求超时！请稍后重试。")
    
        except aiohttp.ClientError as e:
            self.logger.error(f"OTA请求失败: {e}")
            raise ValueError("无法连接到OTA服务器，请检查网络连接！")

    async def update_mqtt_config(self, response_data):
        """
        更新MQTT配置信息.
        """
        if "mqtt" in response_data:
            self.logger.info("发现MQTT配置信息")
            mqtt_info = response_data["mqtt"]
            if mqtt_info:
                # 更新配置
                success = self.config.update_config(
                    "SYSTEM_OPTIONS.NETWORK.MQTT_INFO", mqtt_info
                )
                if success:
                    self.logger.info("MQTT配置已更新")
                    return mqtt_info
                else:
                    self.logger.error("MQTT配置更新失败")
            else:
                self.logger.warning("MQTT配置为空")
        else:
            self.logger.info("未发现MQTT配置信息")

        return None

    async def update_websocket_config(self, response_data):
        """
        更新WebSocket配置信息.
        """
        if "websocket" in response_data:
            self.logger.info("发现WebSocket配置信息")
            websocket_info = response_data["websocket"]

            # 更新WebSocket URL
            if "url" in websocket_info:
                self.config.update_config(
                    "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", websocket_info["url"]
                )
                self.logger.info(f"WebSocket URL已更新: {websocket_info['url']}")

            # 更新WebSocket Token
            token_value = websocket_info.get("token", "test-token") or "test-token"
            self.config.update_config(
                "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN", token_value
            )
            self.logger.info("WebSocket Token已更新")

            return websocket_info
        else:
            self.logger.info("未发现WebSocket配置信息")

        return None

    async def _periodic_device_update(self):
        """
        每15分钟执行一次设备更新的后台任务
        首次启动后，第一次更新在15分钟后执行
        """
        while True:
            try:
                self.logger.info("设备更新计划在15分钟后执行")
                await asyncio.sleep(15 * 60)  # 等待15分钟
                
                # 执行设备更新逻辑
                self.logger.info("开始执行计划的设备更新")
                await self._execute_device_update()
                
            except Exception as e:
                self.logger.error(f"定时设备更新失败: {e}")

    async def _execute_device_update(self):
        """
        执行设备更新的核心逻辑
        """
        try:
            # 获取MAC地址
            mac_address = self.device_fingerprint.get_mac_address()
            
            # 获取设备信息
            ha_model = HomeAssistantModelAPI()
            ha_model.set_token(ha_service_data["token"])
            device_update_info = await ha_model.parse_devices_for_registration()
            
            # 调用设备更新方法
            ha_api = HomeAssistantRegistrationAPI()
            update_result = ha_api.update_devices(mac_address, device_update_info)
            self.logger.info(f"设备更新结果: {update_result}")
            
        except Exception as e:
            self.logger.error(f"执行设备更新失败: {e}")
            raise

    async def initialize_custom_register(self):
        """
        初始化自定义设备注册信息（优化后的方法）
        """
        try:
            self.logger.info("开始初始化自定义设备注册信息")
            
            # 发送HA数据
            await HaDataService().send_ha_data()
            
            # 首次启动不执行设备更新，只启动定时任务
            # 启动定时更新任务（如果还没有启动）
            if self._update_task is None or self._update_task.done():
                self._update_task = asyncio.create_task(self._periodic_device_update())
                self.logger.info("已启动设备定时更新任务（每15分钟执行一次）")
            
            self.logger.info("自定义设备注册信息初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化自定义设备注册信息失败: {e}")
            raise

    async def _get_custom_register(self):
        self.logger.info("开始获取自定义设备注册信息")
        await HaDataService().send_ha_data()
        # 首次启动不执行设备更新，只启动定时任务
        # 启动定时更新任务（如果还没有启动）
        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._periodic_device_update())
            self.logger.info("已启动设备定时更新任务（每15分钟执行一次）")


    async def fetch_and_update_config(self):
        """
        获取并更新所有配置信息.
        """
        try:
            # 注册设备信息
            await self._get_custom_register()

            # 获取OTA配置
            response_data = await self.get_ota_config()

            # 更新MQTT配置
            mqtt_config = await self.update_mqtt_config(response_data)

            # 更新WebSocket配置
            websocket_config = await self.update_websocket_config(response_data)

            # 返回完整的响应数据，供激活流程使用
            return {
                "response_data": response_data,
                "mqtt_config": mqtt_config,
                "websocket_config": websocket_config,
            }

        except Exception as e:
            self.logger.error(f"获取并更新配置失败: {e}")
            raise
