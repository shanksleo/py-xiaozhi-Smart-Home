# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Home Assistant 设备控制演示
独立于主文件的设备控制演示模块
"""

import time
import json
import requests

from src.ha.ha_data import ha_service_data, ha_device_data

use_SSL = ha_service_data["use_ssl"]
protocol_suffix = 's' if use_SSL else ''


class HomeAssistantControlDemo:
    def __init__(self, host, port=ha_service_data["port"], token=None):
        """
        初始化设备控制演示

        参数:
            host: Home Assistant服务器地址
            port: Home Assistant服务器端口
            token: 长期访问令牌
        """
        protocol_suffix_value = protocol_suffix
        self.base_url = f"http{protocol_suffix_value}://{host}:{port}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}" if token else ""
        }

    def set_token(self, token):
        """设置访问令牌"""
        token_value = token
        self.headers["Authorization"] = f"Bearer {token_value}"
        print("令牌已设置！")

    def check_api(self):
        """检查API连接"""
        base_url = self.base_url
        url = f"{base_url}/api/"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                print("API连接正常！")
                return True
            else:
                status_code = response.status_code
                print(f"API检查失败: {status_code}")
                return False
        except Exception as e:
            error_msg = str(e)
            print(f"API检查错误: {error_msg}")
            return False

    def call_service(self, domain, service, entity_id=None, data=None):
        """调用HA服务"""
        base_url = self.base_url
        domain_val = domain
        service_val = service
        url = f"{base_url}/api/services/{domain_val}/{service_val}"
        service_data = data or {}

        if entity_id:
            service_data["entity_id"] = entity_id

        try:
            response = requests.post(url, headers=self.headers, json=service_data)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f"调用服务失败: {status_code} - {response_text}")
                return None
        except Exception as e:
            error_msg = str(e)
            print(f"调用服务错误: {error_msg}")
            return None

    # ----------- 设备控制方法 -----------

    def light_on(self, entity_id):
        """开灯"""
        return self.call_service("light", "turn_on", entity_id)

    def light_off(self, entity_id):
        """关灯"""
        return self.call_service("light", "turn_off", entity_id)
        
    def light_set_brightness(self, entity_id, brightness):
        """设置灯光亮度"""
        return self.call_service("light", "turn_on", entity_id, {"brightness": brightness})
        
    def light_set_color(self, entity_id, rgb_color):
        """设置灯光颜色"""
        return self.call_service("light", "turn_on", entity_id, {"rgb_color": rgb_color})

    def ac_on(self, entity_id):
        """开空调"""
        return self.call_service("climate", "turn_on", entity_id)

    def ac_off(self, entity_id):
        """关空调"""
        return self.call_service("climate", "turn_off", entity_id)

    def ac_set_temp(self, entity_id, temperature):
        """设置空调温度"""
        return self.call_service("climate", "set_temperature", entity_id, {"temperature": temperature})

    def ac_set_mode(self, entity_id, mode):
        """设置空调模式"""
        return self.call_service("climate", "set_hvac_mode", entity_id, {"hvac_mode": mode})
        
    def ac_set_fan_mode(self, entity_id, fan_mode):
        """设置空调风扇模式"""
        return self.call_service("climate", "set_fan_mode", entity_id, {"fan_mode": fan_mode})

    def curtain_open(self, entity_id):
        """打开窗帘"""
        return self.call_service("cover", "open_cover", entity_id)

    def curtain_close(self, entity_id):
        """关闭窗帘"""
        return self.call_service("cover", "close_cover", entity_id)

    def curtain_stop(self, entity_id):
        """停止窗帘"""
        return self.call_service("cover", "stop_cover", entity_id)

    def switch_on(self, entity_id):
        """开启开关"""
        return self.call_service("switch", "turn_on", entity_id)

    def switch_off(self, entity_id):
        """关闭开关"""
        return self.call_service("switch", "turn_off", entity_id)

    def tv_on(self,entity_id):
        #打开电视
        return self.call_service("button", "press", entity_id)

    def tv_off(self,entity_id):
        # 关闭电视
        return self.call_service("button", "press", entity_id)


    def air_cleaner_on(self, entity_id):
        """开启空气净化器"""
        logging.info(f"[HomeAssistantControlDemo] 开启空气净化器: {entity_id}")
        return self.call_service("fan", "turn_on", entity_id)

    def air_cleaner_off(self, entity_id):
        """关闭空气净化器"""
        logging.info(f"[HomeAssistantControlDemo] 关闭空气净化器: {entity_id}")
        return self.call_service("fan", "turn_off", entity_id)

    def demo_control_devices(self, demo_devices, interval=10, device_keys=None):
        """
        演示控制设备 - 支持通过设备key或完整设备字典进行控制

        参数:
            demo_devices: 设备字典 (key -> entity_id)
            interval: 操作间隔时间(秒)
            device_keys: 要测试的设备key列表，如果为None则测试所有设备
        """
        print("\n" + "=" * 50)
        print("智能家居设备控制演示")
        print("=" * 50)
        
        # 设备类型映射表
        device_type_mapping = {
            'light': {'domain': 'light', 'friendly_name': '灯光'},
            'air_conditioner': {'domain': 'climate', 'friendly_name': '空调'},
            'curtain': {'domain': 'cover', 'friendly_name': '窗帘'},
            'smart_switch': {'domain': 'switch', 'friendly_name': '智能开关'},
            'tv': {'domain': 'button', 'friendly_name': '电视'},
            'air_clean': {'domain': 'fan', 'friendly_name': '空气净化器'}
        }
        
        # 如果指定了device_keys，只测试指定的设备
        if device_keys:
            test_devices = {key: demo_devices[key] for key in device_keys if key in demo_devices}
            print(f"测试指定设备: {list(test_devices.keys())}")
        else:
            test_devices = demo_devices
            print(f"测试所有设备: {list(test_devices.keys())}")
        
        print(f"设备总数: {len(test_devices)}")
        print(f"操作间隔: {interval}秒")
        print("=" * 50)

        # 遍历设备进行控制演示
        for device_key, entity_id in test_devices.items():
            if not entity_id or "你的" in entity_id:
                print(f"\n⚠️  跳过设备 {device_key}: entity_id 未配置")
                continue
                
            device_info = device_type_mapping.get(device_key, {'domain': 'unknown', 'friendly_name': device_key})
            friendly_name = device_info['friendly_name']
            domain = device_info['domain']
            
            print(f"\n🏠 --- 控制 {friendly_name} ({device_key}) ---")
            print(f"📋 Entity ID: {entity_id}")
            print(f"🔧 Domain: {domain}")
            
            try:
                # 根据设备类型执行相应的控制逻辑
                if device_key == 'light':
                    self._control_light(entity_id, interval)
                elif device_key == 'air_conditioner':
                    self._control_air_conditioner(entity_id, interval)
                elif device_key == 'curtain':
                    self._control_curtain(entity_id, interval)
                elif device_key == 'smart_switch':
                    self._control_smart_switch(entity_id, interval)
                elif device_key == 'tv':
                    self._control_tv(entity_id, interval)
                elif device_key == 'air_clean':
                    self._control_air_cleaner(entity_id, interval)
                else:
                    print(f"⚠️  未知设备类型: {device_key}")
                    
            except Exception as e:
                print(f"❌ 控制设备 {friendly_name} 时发生错误: {str(e)}")
                
            print(f"✅ {friendly_name} 控制完成")

        print("\n" + "=" * 50)
        print("🎉 所有设备演示完成！")
        print("=" * 50)
        
    def _control_light(self, entity_id, interval):
        """控制灯光设备"""
        print("💡 开启灯光...")
        result = self.light_on(entity_id)
        if result:
            print("✅ 灯光已开启")
        time.sleep(interval // 2)
        
        print("🔆 设置亮度为150...")
        self.light_set_brightness(entity_id, 150)
        time.sleep(interval // 2)
        
        print("💡 关闭灯光...")
        result = self.light_off(entity_id)
        if result:
            print("✅ 灯光已关闭")
            
    def _control_air_conditioner(self, entity_id, interval):
        """控制空调设备"""
        print("❄️ 开启空调...")
        result = self.ac_on(entity_id)
        if result:
            print("✅ 空调已开启")
            
        print("🌪️ 设置为送风模式...")
        self.ac_set_mode(entity_id, "fan_only")
        
        print("🌡️ 设置温度为25度...")
        self.ac_set_temp(entity_id, 25)
        time.sleep(interval)
        
        print("❄️ 关闭空调...")
        result = self.ac_off(entity_id)
        if result:
            print("✅ 空调已关闭")
            
    def _control_curtain(self, entity_id, interval):
        """控制窗帘设备"""
        print("🪟 关闭窗帘...")
        result = self.curtain_close(entity_id)
        if result:
            print("✅ 窗帘已关闭")
        time.sleep(interval)
        
        print("🪟 打开窗帘...")
        result = self.curtain_open(entity_id)
        if result:
            print("✅ 窗帘已打开")
            
    def _control_smart_switch(self, entity_id, interval):
        """控制智能开关设备"""
        print("🔌 开启智能开关...")
        result = self.switch_on(entity_id)
        if result:
            print("✅ 智能开关已开启")
        time.sleep(interval)
        
        print("🔌 关闭智能开关...")
        result = self.switch_off(entity_id)
        if result:
            print("✅ 智能开关已关闭")
            
    def _control_tv(self, entity_id, interval):
        """控制电视设备"""
        print("📺 操作电视按钮...")
        result = self.tv_on(entity_id)
        if result:
            print("✅ 电视按钮操作完成")
        time.sleep(interval)
        
    def _control_air_cleaner(self, entity_id, interval):
        """控制空气净化器设备"""
        print("🌬️ 开启空气净化器...")
        result = self.air_cleaner_on(entity_id)
        if result:
            print("✅ 空气净化器已开启")
        time.sleep(interval)
        
        print("🌬️ 关闭空气净化器...")
        result = self.air_cleaner_off(entity_id)
        if result:
            print("✅ 空气净化器已关闭")


def main():
    """主函数 - 智能家居设备控制演示"""
    
    # ==================== 配置参数 ====================
    # 测试间隔时间(秒)
    TEST_INTERVAL = 5
    
    # 指定要测试的设备key列表，None表示测试所有设备
    # 可选值: ['light', 'air_conditioner', 'curtain', 'smart_switch', 'tv', 'air_clean']
    SPECIFIC_DEVICE_KEYS = None  # 例如: ['air_clean', 'light'] 只测试空气净化器和灯光
    
    # 是否启用详细日志
    VERBOSE_LOGGING = True
    
    # ==================== 系统配置 ====================
    server = ha_service_data["host"]
    port = ha_service_data["port"]
    token = ha_service_data["token"]
    
    # 使用统一的设备数据
    demo_devices = ha_device_data
    
    print("🏠 智能家居设备控制演示系统")
    print("=" * 60)
    print(f"🌐 服务器地址: {server}:{port}")
    print(f"📱 设备总数: {len(demo_devices)}")
    print(f"⏱️  测试间隔: {TEST_INTERVAL}秒")
    
    if SPECIFIC_DEVICE_KEYS:
        print(f"🎯 指定测试设备: {SPECIFIC_DEVICE_KEYS}")
    else:
        print("🎯 测试模式: 全部设备")
        
    print(f"📋 可用设备列表: {list(demo_devices.keys())}")
    print("=" * 60)
    
    if VERBOSE_LOGGING:
        print("📊 设备详细信息:")
        for key, entity_id in demo_devices.items():
            print(f"  • {key}: {entity_id}")
        print("=" * 60)

    # 创建演示实例
    print("🔧 初始化Home Assistant控制器...")
    demo = HomeAssistantControlDemo(server, port)
    demo.set_token(token)

    # 检查API连接
    print("🔍 检查API连接状态...")
    if not demo.check_api():
        print("❌ API连接失败，请检查以下项目:")
        print("   1. 网络连接是否正常")
        print("   2. Home Assistant服务是否运行")
        print("   3. 访问令牌是否有效")
        print(f"   4. 服务器地址是否正确: {server}:{port}")
        return

    print("✅ API连接成功，开始设备控制演示...")
    print("\n" + "🚀 " + "=" * 58)
    
    try:
        # 运行设备控制演示
        demo.demo_control_devices(
            demo_devices=demo_devices, 
            interval=TEST_INTERVAL,
            device_keys=SPECIFIC_DEVICE_KEYS
        )
        
        print("\n" + "=" * 60)
        print("🎉 演示程序执行完成！")
        print("💡 提示: 可以修改main()函数中的配置参数来自定义测试行为")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断演示程序")
        print("👋 程序已安全退出")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
        print("🔧 请检查设备配置和网络连接")


if __name__ == "__main__":
    main()

