#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Home 日志上报功能验证脚本

不依赖外部测试框架，直接验证核心功能实现。
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# 验证配置参数（文件顶部）
TEST_MODE = "all"            # 测试模式：all, unit, integration
GENERATE_REPORT = True       # 是否生成验证报告
REPORT_FORMAT = "console"    # 报告格式：console, json
VERBOSE_OUTPUT = True        # 是否显示详细输出
MAX_TEST_TIME = 30           # 最大测试时间（秒）
TEST_MESSAGE_COUNT = 5       # 测试消息数量

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class SmartHomeLoggingVerifier:
    """
    Smart Home 日志上报功能验证器
    """
    
    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": [],
            "details": []
        }
        self.start_time = time.time()
    
    def log_result(self, test_name: str, success: bool, message: str = "", details: dict = None):
        """记录测试结果"""
        self.results["total_tests"] += 1
        
        if success:
            self.results["passed_tests"] += 1
            status = "✓ PASS"
        else:
            self.results["failed_tests"] += 1
            status = "✗ FAIL"
            self.results["errors"].append(f"{test_name}: {message}")
        
        result_detail = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        }
        
        self.results["details"].append(result_detail)
        
        if VERBOSE_OUTPUT:
            print(f"{status} {test_name}")
            if message:
                print(f"    {message}")
            if details and VERBOSE_OUTPUT:
                for key, value in details.items():
                    print(f"    {key}: {value}")
    
    def verify_imports(self):
        """验证模块导入"""
        print("\n" + "=" * 60)
        print("1. 模块导入验证")
        print("=" * 60)
        
        # 验证核心模块导入
        try:
            from src.services.smart_home_logging_service import SmartHomeLoggingService, get_smart_home_logging_service
            self.log_result("导入SmartHomeLoggingService", True, "核心服务类导入成功")
        except Exception as e:
            self.log_result("导入SmartHomeLoggingService", False, f"导入失败: {e}")
            return False
        
        try:
            from src.protocols.websocket_protocol import WebsocketProtocol
            self.log_result("导入WebsocketProtocol", True, "WebSocket协议类导入成功")
        except Exception as e:
            self.log_result("导入WebsocketProtocol", False, f"导入失败: {e}")
        
        try:
            from src.ha.ha_data_post_service import HomeAssistantRegistrationAPI
            self.log_result("导入HomeAssistantRegistrationAPI", True, "日志上报API导入成功")
        except Exception as e:
            self.log_result("导入HomeAssistantRegistrationAPI", False, f"导入失败: {e}")
        
        return True
    
    def verify_service_initialization(self):
        """验证服务初始化"""
        print("\n" + "=" * 60)
        print("2. 服务初始化验证")
        print("=" * 60)
        
        try:
            from src.services.smart_home_logging_service import get_smart_home_logging_service
            
            # 测试单例模式
            service1 = get_smart_home_logging_service()
            service2 = get_smart_home_logging_service()
            
            if service1 is service2:
                self.log_result("单例模式验证", True, "服务实例单例模式正常")
            else:
                self.log_result("单例模式验证", False, "服务实例不是单例")
            
            # 验证服务属性
            if hasattr(service1, 'mac_address') and service1.mac_address:
                self.log_result("MAC地址获取", True, f"MAC地址: {service1.mac_address}")
            else:
                self.log_result("MAC地址获取", False, "MAC地址获取失败")
            
            if hasattr(service1, 'ha_api') and service1.ha_api:
                self.log_result("HA API初始化", True, "HomeAssistant API初始化成功")
            else:
                self.log_result("HA API初始化", False, "HomeAssistant API初始化失败")
            
            return service1
            
        except Exception as e:
            self.log_result("服务初始化", False, f"初始化异常: {e}")
            return None
    
    def verify_message_parsing(self, service):
        """验证消息解析功能"""
        print("\n" + "=" * 60)
        print("3. 消息解析验证")
        print("=" * 60)
        
        if not service:
            self.log_result("消息解析验证", False, "服务实例不可用")
            return
        
        # 测试正常消息
        valid_message = {
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
        }
        
        try:
            parsed_data = service._parse_message(valid_message)
            if parsed_data and parsed_data.get("ha_domain") == "light":
                self.log_result("正常消息解析", True, "消息解析成功", {
                    "domain": parsed_data.get("ha_domain"),
                    "service": parsed_data.get("ha_service"),
                    "entity_id": parsed_data.get("entity_id")
                })
            else:
                self.log_result("正常消息解析", False, "消息解析结果异常")
        except Exception as e:
            self.log_result("正常消息解析", False, f"解析异常: {e}")
        
        # 测试异常消息
        invalid_messages = [
            {"type": "other"},  # 错误类型
            {"type": "smart_home"},  # 缺少payload
            {"type": "smart_home", "payload": {"ha_domain": "light"}},  # 缺少service
        ]
        
        for i, msg in enumerate(invalid_messages, 1):
            try:
                parsed_data = service._parse_message(msg)
                if parsed_data is None:
                    self.log_result(f"异常消息处理{i}", True, "正确拒绝无效消息")
                else:
                    self.log_result(f"异常消息处理{i}", False, "应该拒绝无效消息")
            except Exception as e:
                self.log_result(f"异常消息处理{i}", False, f"处理异常: {e}")
    
    def verify_log_data_building(self, service):
        """验证日志数据构建"""
        print("\n" + "=" * 60)
        print("4. 日志数据构建验证")
        print("=" * 60)
        
        if not service:
            self.log_result("日志数据构建验证", False, "服务实例不可用")
            return
        
        try:
            parsed_data = {
                "session_id": "test-session",
                "ha_domain": "light",
                "ha_service": "turn_on",
                "arguments": {"entity_id": "light.test"},
                "entity_id": "light.test"
            }
            
            start_time = time.time()
            log_data = service._build_log_data(parsed_data, start_time)
            
            # 验证必要字段
            required_fields = [
                "mac_address", "ha_entity_id", "function_name",
                "ha_domain", "ha_service", "arguments",
                "status", "result_message", "execution_duration_ms"
            ]
            
            missing_fields = [field for field in required_fields if field not in log_data]
            
            if not missing_fields:
                self.log_result("日志数据字段完整性", True, "所有必要字段都存在", {
                    "字段数量": len(log_data),
                    "MAC地址": log_data.get("mac_address"),
                    "实体ID": log_data.get("ha_entity_id"),
                    "域": log_data.get("ha_domain"),
                    "服务": log_data.get("ha_service")
                })
            else:
                self.log_result("日志数据字段完整性", False, f"缺少字段: {missing_fields}")
            
            # 验证数据类型
            if isinstance(log_data.get("execution_duration_ms"), int):
                self.log_result("执行时间类型", True, "执行时间为整数类型")
            else:
                self.log_result("执行时间类型", False, "执行时间类型错误")
            
            # 验证JSON序列化
            try:
                json.loads(log_data.get("arguments", "{}"))
                self.log_result("参数JSON格式", True, "参数正确序列化为JSON")
            except:
                self.log_result("参数JSON格式", False, "参数JSON格式错误")
                
        except Exception as e:
            self.log_result("日志数据构建", False, f"构建异常: {e}")
    
    async def verify_async_logging(self, service):
        """验证异步日志功能"""
        print("\n" + "=" * 60)
        print("5. 异步日志功能验证")
        print("=" * 60)
        
        if not service:
            self.log_result("异步日志功能验证", False, "服务实例不可用")
            return
        
        test_message = {
            "session_id": "async-test-001",
            "type": "smart_home",
            "payload": {
                "ha_domain": "light",
                "ha_service": "turn_on",
                "arguments": {
                    "entity_id": "light.async_test"
                }
            }
        }
        
        try:
            start_time = time.time()
            result = await service.log_smart_home_message(test_message)
            duration = int((time.time() - start_time) * 1000)
            
            if isinstance(result, bool):
                self.log_result("异步日志调用", True, f"调用完成，耗时: {duration}ms", {
                    "返回值类型": type(result).__name__,
                    "返回值": result,
                    "耗时": f"{duration}ms"
                })
            else:
                self.log_result("异步日志调用", False, "返回值类型错误")
                
        except Exception as e:
            self.log_result("异步日志调用", False, f"调用异常: {e}")
    
    async def verify_performance(self, service):
        """验证性能"""
        print("\n" + "=" * 60)
        print("6. 性能验证")
        print("=" * 60)
        
        if not service:
            self.log_result("性能验证", False, "服务实例不可用")
            return
        
        test_messages = []
        for i in range(TEST_MESSAGE_COUNT):
            test_messages.append({
                "session_id": f"perf-test-{i:03d}",
                "type": "smart_home",
                "payload": {
                    "ha_domain": "light",
                    "ha_service": "turn_on",
                    "arguments": {
                        "entity_id": f"light.perf_test_{i}"
                    }
                }
            })
        
        try:
            # 串行测试
            start_time = time.time()
            serial_results = []
            for msg in test_messages:
                result = await service.log_smart_home_message(msg)
                serial_results.append(result)
            serial_time = time.time() - start_time
            
            # 并行测试
            start_time = time.time()
            tasks = [service.log_smart_home_message(msg) for msg in test_messages]
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            parallel_time = time.time() - start_time
            
            # 统计结果
            serial_success = sum(1 for r in serial_results if r is True)
            parallel_success = sum(1 for r in parallel_results if r is True)
            
            self.log_result("串行性能测试", True, f"{TEST_MESSAGE_COUNT}条消息串行处理", {
                "成功数量": f"{serial_success}/{TEST_MESSAGE_COUNT}",
                "总耗时": f"{int(serial_time * 1000)}ms",
                "平均耗时": f"{int(serial_time * 1000 / TEST_MESSAGE_COUNT)}ms/条"
            })
            
            self.log_result("并行性能测试", True, f"{TEST_MESSAGE_COUNT}条消息并行处理", {
                "成功数量": f"{parallel_success}/{TEST_MESSAGE_COUNT}",
                "总耗时": f"{int(parallel_time * 1000)}ms",
                "平均耗时": f"{int(parallel_time * 1000 / TEST_MESSAGE_COUNT)}ms/条",
                "性能提升": f"{serial_time / parallel_time:.2f}x" if parallel_time > 0 else "N/A"
            })
            
        except Exception as e:
            self.log_result("性能测试", False, f"测试异常: {e}")
    
    def generate_report(self):
        """生成验证报告"""
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("验证报告")
        print("=" * 60)
        
        print(f"总测试数量: {self.results['total_tests']}")
        print(f"通过测试: {self.results['passed_tests']}")
        print(f"失败测试: {self.results['failed_tests']}")
        print(f"成功率: {self.results['passed_tests'] / max(self.results['total_tests'], 1) * 100:.1f}%")
        print(f"总耗时: {int(total_time * 1000)}ms")
        
        if self.results['errors']:
            print("\n错误详情:")
            for error in self.results['errors']:
                print(f"  ✗ {error}")
        
        # 生成JSON报告
        if GENERATE_REPORT and REPORT_FORMAT == "json":
            report_file = project_root / "smart_home_logging_verification_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": {
                        "total_tests": self.results['total_tests'],
                        "passed_tests": self.results['passed_tests'],
                        "failed_tests": self.results['failed_tests'],
                        "success_rate": self.results['passed_tests'] / max(self.results['total_tests'], 1) * 100,
                        "total_time_ms": int(total_time * 1000)
                    },
                    "details": self.results['details'],
                    "errors": self.results['errors']
                }, f, ensure_ascii=False, indent=2)
            print(f"\nJSON报告已生成: {report_file}")
        
        return self.results['failed_tests'] == 0


async def main():
    """主函数"""
    print("Smart Home 日志上报功能验证")
    print(f"验证模式: {TEST_MODE}")
    print(f"项目根目录: {project_root}")
    print(f"配置参数:")
    print(f"  TEST_MESSAGE_COUNT: {TEST_MESSAGE_COUNT}")
    print(f"  MAX_TEST_TIME: {MAX_TEST_TIME}s")
    print(f"  VERBOSE_OUTPUT: {VERBOSE_OUTPUT}")
    print(f"  GENERATE_REPORT: {GENERATE_REPORT}")
    print(f"  注意: 已移除重试机制，仅进行单次日志上报")
    
    verifier = SmartHomeLoggingVerifier()
    
    try:
        # 1. 验证导入
        if not verifier.verify_imports():
            print("\n❌ 核心模块导入失败，无法继续验证")
            return False
        
        # 2. 验证服务初始化
        service = verifier.verify_service_initialization()
        
        # 3. 验证消息解析
        verifier.verify_message_parsing(service)
        
        # 4. 验证日志数据构建
        verifier.verify_log_data_building(service)
        
        # 5. 验证异步日志功能
        await verifier.verify_async_logging(service)
        
        # 6. 验证性能
        await verifier.verify_performance(service)
        
    except Exception as e:
        print(f"\n❌ 验证过程中发生异常: {e}")
        return False
    
    finally:
        # 生成报告
        success = verifier.generate_report()
        
        if success:
            print("\n✅ 所有验证通过！")
        else:
            print("\n❌ 部分验证失败！")
        
        return success


if __name__ == '__main__':
    # 解析命令行参数
    if len(sys.argv) > 1:
        TEST_MODE = sys.argv[1]
    
    # 运行验证
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n验证失败: {e}")
        sys.exit(1)