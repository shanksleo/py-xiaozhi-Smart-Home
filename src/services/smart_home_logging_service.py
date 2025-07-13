#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Home 消息日志上报服务

负责处理 smart_home 类型的 WebSocket 消息，并将相关信息上报到日志接口。
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional

# 配置参数（文件顶部）
REQUEST_TIMEOUT_SECONDS = 10 # 请求超时时间（秒）
LOG_LEVEL = "INFO"           # 日志级别
ENABLE_ASYNC_LOGGING = True  # 是否启用异步日志
FUNCTION_NAME = "智能家居控制" # 功能名称
DEFAULT_STATUS = "received"   # 默认状态
DEFAULT_RESULT_MESSAGE = "消息接收成功"  # 默认结果消息

# 导入处理
try:
    from src.ha.ha_data_post_service import HomeAssistantRegistrationAPI
except ImportError:
    try:
        from ha.ha_data_post_service import HomeAssistantRegistrationAPI
    except ImportError:
        # 创建模拟类用于测试
        class HomeAssistantRegistrationAPI:
            def log_action(self, *args, **kwargs):
                print(f"模拟日志上报: args={args}, kwargs={kwargs}")
                return {"code": 0, "msg": "success"}

try:
    from src.utils.device_fingerprint import DeviceFingerprint
except ImportError:
    try:
        from utils.device_fingerprint import DeviceFingerprint
    except ImportError:
        # 创建模拟类用于测试
        class DeviceFingerprint:
            @staticmethod
            def get_instance():
                return DeviceFingerprint()
            
            def get_mac_address(self):
                return "06:5e:0f:cc:bc:51"

try:
    from src.utils.logging_config import get_logger
except ImportError:
    try:
        from utils.logging_config import get_logger
    except ImportError:
        import logging
        def get_logger(name):
            return logging.getLogger(name)

# 获取日志记录器
logger = get_logger(__name__)


class SmartHomeLoggingService:
    """
    Smart Home 消息日志上报服务类
    
    负责处理 smart_home 类型的消息，提取关键信息并上报到日志接口。
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化服务"""
        if self._initialized:
            return
            
        self._initialized = True
        self.ha_api = HomeAssistantRegistrationAPI()
        self.device_fingerprint = DeviceFingerprint.get_instance()
        self.mac_address = None
        
        # 获取设备MAC地址
        try:
            self.mac_address = self.device_fingerprint.get_mac_address()
            logger.info(f"[SmartHomeLogging] 获取设备MAC地址: {self.mac_address}")
        except Exception as e:
            logger.error(f"[SmartHomeLogging] 获取MAC地址失败: {e}")
            self.mac_address = "unknown"
    
    async def log_smart_home_message(self, message_data: Dict[str, Any]) -> bool:
        """
        异步记录 smart_home 消息日志
        
        Args:
            message_data: smart_home 消息数据
            
        Returns:
            bool: 是否成功记录日志
        """
        start_time = time.time()
        
        try:
            logger.info(f"[SmartHomeLogging] 开始处理消息: {json.dumps(message_data, ensure_ascii=False)}")
            
            # 解析消息数据
            parsed_data = self._parse_message(message_data)
            if not parsed_data:
                logger.warning(f"[SmartHomeLogging] 消息解析失败，跳过日志上报")
                return False
            
            # 构建日志数据
            log_data = self._build_log_data(parsed_data, start_time)
            logger.info(f"[SmartHomeLogging] 构建日志数据: {json.dumps(log_data, ensure_ascii=False)}")
            
            # 上报日志（单次上报）
            success = await self._upload_log_once(log_data)
            
            execution_time = int((time.time() - start_time) * 1000)
            if success:
                logger.info(f"[SmartHomeLogging] 日志上报成功，耗时: {execution_time}ms")
            else:
                logger.error(f"[SmartHomeLogging] 日志上报失败，耗时: {execution_time}ms")
            
            return success
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"[SmartHomeLogging] 处理消息异常: {e}，耗时: {execution_time}ms")
            return False
    
    def _parse_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析 smart_home 消息
        
        Args:
            message_data: 原始消息数据
            
        Returns:
            解析后的数据，如果解析失败返回 None
        """
        try:
            # 检查消息类型
            if message_data.get("type") != "smart_home":
                logger.warning(f"[SmartHomeLogging] 非smart_home消息类型: {message_data.get('type')}")
                return None
            
            # 检查payload
            payload = message_data.get("payload")
            if not payload or not isinstance(payload, dict):
                logger.warning(f"[SmartHomeLogging] payload格式错误: {payload}")
                return None
            
            # 提取关键信息
            ha_domain = payload.get("ha_domain")
            ha_service = payload.get("ha_service")
            arguments = payload.get("arguments", {})
            session_id = message_data.get("session_id", "")
            
            if not ha_domain or not ha_service:
                logger.warning(f"[SmartHomeLogging] 缺少必要字段: ha_domain={ha_domain}, ha_service={ha_service}")
                return None
            
            # 提取entity_id
            entity_id = arguments.get("entity_id", "")
            
            parsed_data = {
                "session_id": session_id,
                "ha_domain": ha_domain,
                "ha_service": ha_service,
                "arguments": arguments,
                "entity_id": entity_id
            }
            
            logger.debug(f"[SmartHomeLogging] 消息解析成功: {json.dumps(parsed_data, ensure_ascii=False)}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"[SmartHomeLogging] 消息解析异常: {e}")
            return None
    
    def _build_log_data(self, parsed_data: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """
        构建日志数据
        
        Args:
            parsed_data: 解析后的消息数据
            start_time: 开始处理时间
            
        Returns:
            构建的日志数据
        """
        execution_duration_ms = int((time.time() - start_time) * 1000)
        
        log_data = {
            "mac_address": self.mac_address,
            "ha_entity_id": parsed_data["entity_id"],
            "function_name": FUNCTION_NAME,
            "ha_domain": parsed_data["ha_domain"],
            "ha_service": parsed_data["ha_service"],
            "arguments": json.dumps(parsed_data["arguments"], ensure_ascii=False),
            "status": DEFAULT_STATUS,
            "result_message": DEFAULT_RESULT_MESSAGE,
            "execution_duration_ms": execution_duration_ms
        }
        
        return log_data
    
    async def _upload_log_once(self, log_data: Dict[str, Any]) -> bool:
        """
        单次日志上报（无重试机制）
        
        Args:
            log_data: 日志数据
            
        Returns:
            bool: 是否上报成功
        """
        try:
            logger.info(f"[SmartHomeLogging] 开始上报日志: {json.dumps(log_data, ensure_ascii=False)}")
            
            # 调用日志上报接口
            result = self.ha_api.log_action(
                mac_address=log_data["mac_address"],
                ha_entity_id=log_data["ha_entity_id"],
                function_name=log_data["function_name"],
                ha_domain=log_data["ha_domain"],
                ha_service=log_data["ha_service"],
                arguments=log_data["arguments"],
                status=log_data["status"],
                result_message=log_data["result_message"],
                execution_duration_ms=log_data["execution_duration_ms"]
            )
            
            if result is not None:
                logger.info(f"[SmartHomeLogging] 日志上报成功: {result}")
                return True
            else:
                logger.warning(f"[SmartHomeLogging] 日志上报返回空结果")
                return False
                
        except Exception as e:
            logger.error(f"[SmartHomeLogging] 日志上报异常: {e}")
            return False


# 全局服务实例
_service_instance = None


def get_smart_home_logging_service() -> SmartHomeLoggingService:
    """
    获取 SmartHomeLoggingService 单例实例
    
    Returns:
        SmartHomeLoggingService: 服务实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SmartHomeLoggingService()
    return _service_instance


if __name__ == '__main__':
    """
    测试脚本
    """
    import sys
    
    # 测试配置参数（文件顶部）
    TEST_MODE = "all"            # 测试模式：all, unit, integration
    GENERATE_REPORT = True       # 是否生成测试报告
    REPORT_FORMAT = "console"    # 报告格式：console, json, html
    VERBOSE_OUTPUT = True        # 是否显示详细输出
    
    async def test_service():
        """测试服务功能"""
        print("=" * 60)
        print("Smart Home 日志上报服务测试")
        print("=" * 60)
        
        # 创建服务实例
        service = get_smart_home_logging_service()
        print(f"✓ 服务实例创建成功: {service}")
        print(f"✓ 设备MAC地址: {service.mac_address}")
        
        # 测试数据
        test_messages = [
            {
                "session_id": "test-session-001",
                "type": "smart_home",
                "payload": {
                    "ha_domain": "light",
                    "ha_service": "turn_on",
                    "arguments": {
                        "entity_id": "light.living_room",
                        "brightness": 255
                    }
                }
            },
            {
                "session_id": "test-session-002",
                "type": "smart_home",
                "payload": {
                    "ha_domain": "climate",
                    "ha_service": "set_temperature",
                    "arguments": {
                        "entity_id": "climate.living_room",
                        "temperature": 25
                    }
                }
            },
            {
                "session_id": "test-session-003",
                "type": "smart_home",
                "payload": {
                    "ha_domain": "cover",
                    "ha_service": "open_cover",
                    "arguments": {
                        "entity_id": "cover.bedroom_curtain"
                    }
                }
            }
        ]
        
        # 测试正常消息处理
        print("\n" + "-" * 40)
        print("测试正常消息处理")
        print("-" * 40)
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n测试消息 {i}:")
            print(f"Domain: {message['payload']['ha_domain']}")
            print(f"Service: {message['payload']['ha_service']}")
            print(f"Entity: {message['payload']['arguments'].get('entity_id')}")
            
            start_time = time.time()
            success = await service.log_smart_home_message(message)
            duration = int((time.time() - start_time) * 1000)
            
            if success:
                print(f"✓ 处理成功，耗时: {duration}ms")
            else:
                print(f"✗ 处理失败，耗时: {duration}ms")
        
        # 测试异常情况
        print("\n" + "-" * 40)
        print("测试异常情况处理")
        print("-" * 40)
        
        error_messages = [
            {"type": "other", "payload": {}},  # 错误的消息类型
            {"type": "smart_home"},  # 缺少payload
            {"type": "smart_home", "payload": {"ha_domain": "light"}},  # 缺少ha_service
            {"type": "smart_home", "payload": {"ha_service": "turn_on"}},  # 缺少ha_domain
        ]
        
        for i, message in enumerate(error_messages, 1):
            print(f"\n异常测试 {i}: {json.dumps(message, ensure_ascii=False)}")
            success = await service.log_smart_home_message(message)
            if not success:
                print(f"✓ 正确处理异常情况")
            else:
                print(f"✗ 异常处理有误")
        
        # 性能测试
        print("\n" + "-" * 40)
        print("性能测试")
        print("-" * 40)
        
        test_count = 10
        start_time = time.time()
        
        tasks = []
        for i in range(test_count):
            task = service.log_smart_home_message(test_messages[0])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r is True)
        avg_time = (total_time / test_count) * 1000
        
        print(f"并发处理 {test_count} 条消息:")
        print(f"✓ 成功: {success_count}/{test_count}")
        print(f"✓ 总耗时: {int(total_time * 1000)}ms")
        print(f"✓ 平均耗时: {int(avg_time)}ms/条")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
    
    # 运行测试
    if len(sys.argv) > 1:
        TEST_MODE = sys.argv[1]
    
    print(f"测试模式: {TEST_MODE}")
    print(f"配置参数:")
    print(f"  REQUEST_TIMEOUT_SECONDS: {REQUEST_TIMEOUT_SECONDS}")
    print(f"  ENABLE_ASYNC_LOGGING: {ENABLE_ASYNC_LOGGING}")
    print(f"  FUNCTION_NAME: {FUNCTION_NAME}")
    
    # 运行异步测试
    asyncio.run(test_service())