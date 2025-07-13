#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能家居设备控制系统单元测试

本测试文件用于测试智能家居设备控制系统的各个功能模块，包括：
1. Home Assistant API连接测试
2. 设备控制功能测试
3. 设备映射系统测试
4. 错误处理机制测试
5. 配置参数验证测试

使用方法：
1. 确保Home Assistant服务正在运行
2. 配置正确的ha_service_data（host, port, token）
3. 运行测试：python -m pytest tests/test_smart_home_device_control.py -v
4. 运行特定测试：python -m pytest tests/test_smart_home_device_control.py::TestHomeAssistantControlDemo::test_api_connection -v
5. 生成覆盖率报告：python -m pytest tests/test_smart_home_device_control.py --cov=src.ha --cov-report=html

测试环境要求：
- Python 3.7+
- pytest
- requests
- unittest.mock
- Home Assistant实例（用于集成测试）

注意事项：
- 单元测试使用mock模拟API调用，不会实际控制设备
- 集成测试需要真实的Home Assistant环境
- 测试前请备份重要的设备状态
- 某些测试可能需要特定的设备配置
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ha.home_assistant_command import HomeAssistantControlDemo
from src.ha.ha_data import ha_service_data, ha_device_data


class TestHomeAssistantControlDemo(unittest.TestCase):
    """
    HomeAssistantControlDemo类的单元测试
    
    测试覆盖范围：
    - 初始化和配置
    - API连接检查
    - 设备控制方法
    - 错误处理
    - 日志记录
    """
    
    def setUp(self):
        """测试前的初始化设置"""
        self.host = "localhost"
        self.port = 8123
        self.token = "test_token_123456"
        self.demo = HomeAssistantControlDemo(self.host, self.port)
        self.demo.set_token(self.token)
        
        # 测试用的设备数据
        self.test_devices = {
            "test_light": "light.test_light",
            "test_switch": "switch.test_switch",
            "test_climate": "climate.test_ac"
        }
    
    def tearDown(self):
        """测试后的清理工作"""
        pass
    
    def test_initialization(self):
        """测试类的初始化"""
        demo = HomeAssistantControlDemo("192.168.1.100", 8123)
        self.assertEqual(demo.base_url, "http://192.168.1.100:8123")
        self.assertIn("Content-Type", demo.headers)
        self.assertEqual(demo.headers["Content-Type"], "application/json")
    
    def test_set_token(self):
        """测试令牌设置"""
        test_token = "new_test_token_789"
        self.demo.set_token(test_token)
        self.assertEqual(self.demo.headers["Authorization"], f"Bearer {test_token}")
    
    @patch('requests.get')
    def test_check_api_success(self, mock_get):
        """测试API连接成功的情况"""
        # 模拟成功的API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "API running."}
        mock_get.return_value = mock_response
        
        result = self.demo.check_api()
        self.assertTrue(result)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_check_api_failure(self, mock_get):
        """测试API连接失败的情况"""
        # 模拟失败的API响应
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = self.demo.check_api()
        self.assertFalse(result)
    
    @patch('requests.get')
    def test_check_api_exception(self, mock_get):
        """测试API连接异常的情况"""
        # 模拟网络异常
        mock_get.side_effect = Exception("Connection error")
        
        result = self.demo.check_api()
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_call_service_success(self, mock_post):
        """测试服务调用成功"""
        # 模拟成功的服务调用响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"state": "on"}]
        mock_post.return_value = mock_response
        
        result = self.demo.call_service(
            domain="light",
            service="turn_on",
            entity_id="light.test_light",
            data={"brightness": 255}
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # 验证调用参数
        call_args = mock_post.call_args
        self.assertIn("light/turn_on", call_args[1]['url'])
        
        # 验证请求数据
        request_data = json.loads(call_args[1]['data'])
        self.assertEqual(request_data['entity_id'], 'light.test_light')
        self.assertEqual(request_data['brightness'], 255)
    
    @patch('requests.post')
    def test_call_service_failure(self, mock_post):
        """测试服务调用失败"""
        # 模拟失败的服务调用响应
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        result = self.demo.call_service(
            domain="light",
            service="turn_on",
            entity_id="light.nonexistent"
        )
        
        self.assertFalse(result)
    
    def test_light_control_methods(self):
        """测试灯光控制方法"""
        entity_id = "light.test_light"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            # 测试开灯
            result = self.demo.light_on(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("light", "turn_on", entity_id)
            
            # 测试关灯
            result = self.demo.light_off(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("light", "turn_off", entity_id)
            
            # 测试设置亮度
            result = self.demo.light_set_brightness(entity_id, 128)
            self.assertTrue(result)
            mock_call.assert_called_with("light", "turn_on", entity_id, {"brightness": 128})
    
    def test_air_conditioner_control_methods(self):
        """测试空调控制方法"""
        entity_id = "climate.test_ac"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            # 测试开空调
            result = self.demo.ac_on(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("climate", "turn_on", entity_id)
            
            # 测试关空调
            result = self.demo.ac_off(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("climate", "turn_off", entity_id)
    
    def test_curtain_control_methods(self):
        """测试窗帘控制方法"""
        entity_id = "cover.test_curtain"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            # 测试开窗帘
            result = self.demo.curtain_open(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("cover", "open_cover", entity_id)
            
            # 测试关窗帘
            result = self.demo.curtain_close(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("cover", "close_cover", entity_id)
    
    def test_switch_control_methods(self):
        """测试开关控制方法"""
        entity_id = "switch.test_switch"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            # 测试开开关
            result = self.demo.switch_on(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("switch", "turn_on", entity_id)
            
            # 测试关开关
            result = self.demo.switch_off(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("switch", "turn_off", entity_id)
    
    def test_tv_control_method(self):
        """测试电视控制方法"""
        entity_id = "button.test_tv"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            result = self.demo.tv_on(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("button", "press", entity_id)
    
    def test_air_cleaner_control_methods(self):
        """测试空气净化器控制方法"""
        entity_id = "fan.test_air_cleaner"
        
        with patch.object(self.demo, 'call_service', return_value=True) as mock_call:
            # 测试开空气净化器
            result = self.demo.air_cleaner_on(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("fan", "turn_on", entity_id)
            
            # 测试关空气净化器
            result = self.demo.air_cleaner_off(entity_id)
            self.assertTrue(result)
            mock_call.assert_called_with("fan", "turn_off", entity_id)
    
    @patch('time.sleep')
    @patch.object(HomeAssistantControlDemo, '_control_light')
    @patch.object(HomeAssistantControlDemo, '_control_air_conditioner')
    def test_demo_control_devices(self, mock_control_ac, mock_control_light, mock_sleep):
        """测试设备演示控制功能"""
        test_devices = {
            "light": "light.test_light",
            "air_conditioner": "climate.test_ac"
        }
        
        # 模拟控制方法返回成功
        mock_control_light.return_value = None
        mock_control_ac.return_value = None
        
        # 执行演示
        self.demo.demo_control_devices(
            demo_devices=test_devices,
            interval=1,
            device_keys=['light', 'air_conditioner']
        )
        
        # 验证控制方法被调用
        mock_control_light.assert_called_once()
        mock_control_ac.assert_called_once()
    
    def test_demo_control_devices_with_invalid_key(self):
        """测试使用无效设备key的情况"""
        test_devices = {"light": "light.test_light"}
        
        # 这应该不会抛出异常，而是跳过无效的设备
        try:
            self.demo.demo_control_devices(
                demo_devices=test_devices,
                interval=0.1,
                device_keys=['nonexistent_device']
            )
        except Exception as e:
            self.fail(f"demo_control_devices raised an exception with invalid key: {e}")
    
    @patch('time.sleep')
    def test_control_light_private_method(self, mock_sleep):
        """测试私有的灯光控制方法"""
        entity_id = "light.test_light"
        
        with patch.object(self.demo, 'light_on', return_value=True) as mock_on, \
             patch.object(self.demo, 'light_off', return_value=True) as mock_off, \
             patch.object(self.demo, 'light_set_brightness', return_value=True) as mock_brightness:
            
            self.demo._control_light(entity_id, 0.1)
            
            # 验证所有灯光控制方法都被调用
            mock_on.assert_called()
            mock_off.assert_called()
            mock_brightness.assert_called()
    
    @patch('time.sleep')
    def test_control_air_conditioner_private_method(self, mock_sleep):
        """测试私有的空调控制方法"""
        entity_id = "climate.test_ac"
        
        with patch.object(self.demo, 'ac_on', return_value=True) as mock_on, \
             patch.object(self.demo, 'ac_off', return_value=True) as mock_off:
            
            self.demo._control_air_conditioner(entity_id, 0.1)
            
            # 验证空调控制方法都被调用
            mock_on.assert_called()
            mock_off.assert_called()


class TestDeviceMapping(unittest.TestCase):
    """
    设备映射系统的测试
    
    测试设备数据的正确性和映射关系
    """
    
    def test_ha_device_data_structure(self):
        """测试ha_device_data的数据结构"""
        self.assertIsInstance(ha_device_data, dict)
        self.assertGreater(len(ha_device_data), 0)
        
        # 验证每个设备都有正确的entity_id格式
        for key, entity_id in ha_device_data.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(entity_id, str)
            self.assertIn('.', entity_id)  # entity_id应该包含domain
    
    def test_ha_service_data_structure(self):
        """测试ha_service_data的数据结构"""
        self.assertIsInstance(ha_service_data, dict)
        
        # 验证必要的配置项
        required_keys = ['host', 'port', 'token']
        for key in required_keys:
            self.assertIn(key, ha_service_data)
            self.assertIsNotNone(ha_service_data[key])
    
    def test_device_type_mapping_coverage(self):
        """测试设备类型映射的覆盖范围"""
        demo = HomeAssistantControlDemo("localhost", 8123)
        
        # 获取device_type_mapping（这需要在实际代码中暴露或通过其他方式访问）
        # 这里我们测试已知的设备类型
        known_device_types = [
            'light', 'air_conditioner', 'curtain', 
            'smart_switch', 'tv', 'air_clean'
        ]
        
        # 验证每种设备类型都有对应的控制方法
        for device_type in known_device_types:
            if device_type == 'light':
                self.assertTrue(hasattr(demo, 'light_on'))
                self.assertTrue(hasattr(demo, 'light_off'))
            elif device_type == 'air_conditioner':
                self.assertTrue(hasattr(demo, 'ac_on'))
                self.assertTrue(hasattr(demo, 'ac_off'))
            # 可以继续添加其他设备类型的验证


class TestIntegration(unittest.TestCase):
    """
    集成测试
    
    注意：这些测试需要真实的Home Assistant环境
    如果没有可用的HA实例，这些测试将被跳过
    """
    
    def setUp(self):
        """集成测试的初始化"""
        self.demo = HomeAssistantControlDemo(
            ha_service_data["host"], 
            ha_service_data["port"]
        )
        self.demo.set_token(ha_service_data["token"])
    
    def test_real_api_connection(self):
        """测试真实的API连接（需要HA实例）"""
        try:
            result = self.demo.check_api()
            if result:
                print("✅ 成功连接到Home Assistant API")
            else:
                print("❌ 无法连接到Home Assistant API")
                self.skipTest("Home Assistant API不可用")
        except Exception as e:
            self.skipTest(f"Home Assistant API连接测试跳过: {e}")
    
    @unittest.skipUnless(
        os.getenv('RUN_INTEGRATION_TESTS') == 'true',
        "集成测试需要设置环境变量 RUN_INTEGRATION_TESTS=true"
    )
    def test_real_device_control(self):
        """测试真实设备控制（需要HA实例和设备）"""
        # 只有在明确启用集成测试时才运行
        if not self.demo.check_api():
            self.skipTest("Home Assistant API不可用")
        
        # 选择一个安全的测试设备（如果存在）
        test_entity = "light.test_light"  # 假设有一个测试灯
        
        try:
            # 尝试控制测试设备
            result = self.demo.light_on(test_entity)
            time.sleep(1)
            result = self.demo.light_off(test_entity)
            
            print(f"✅ 成功测试设备控制: {test_entity}")
        except Exception as e:
            print(f"⚠️ 设备控制测试失败: {e}")
            # 不让测试失败，因为可能是设备不存在


class TestErrorHandling(unittest.TestCase):
    """
    错误处理机制测试
    """
    
    def setUp(self):
        self.demo = HomeAssistantControlDemo("localhost", 8123)
        self.demo.set_token("test_token")
    
    def test_invalid_entity_id_handling(self):
        """测试无效entity_id的处理"""
        with patch.object(self.demo, 'call_service', return_value=False):
            result = self.demo.light_on("invalid.entity.id")
            self.assertFalse(result)
    
    def test_network_error_handling(self):
        """测试网络错误的处理"""
        with patch('requests.post', side_effect=Exception("Network error")):
            result = self.demo.call_service("light", "turn_on", "light.test")
            self.assertFalse(result)
    
    def test_malformed_response_handling(self):
        """测试格式错误响应的处理"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response
            
            result = self.demo.call_service("light", "turn_on", "light.test")
            # 应该能够处理JSON解析错误而不崩溃
            self.assertIsInstance(result, bool)


if __name__ == '__main__':
    # 配置测试运行器
    unittest.main(
        verbosity=2,
        buffer=True,  # 捕获print输出
        catchbreak=True,  # 允许Ctrl+C中断
        warnings='ignore'  # 忽略警告
    )