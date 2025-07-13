# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Home Assistant 设备控制演示
独立于主文件的设备控制演示模块
"""

import time
import json
import requests

from src.ha.ha_data import ha_service_data

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
        return self.call_service("fan", "turn_on", entity_id)

    def air_cleaner_off(self, entity_id):
        """开启空气净化器"""
        return self.call_service("fan", "turn_off", entity_id)

    def demo_control_devices(self, demo_devices, interval=10):
        """
        演示控制设备

        参数:
            demo_devices: 设备字典
            interval: 操作间隔时间(秒)
        """
        print("\n" + "=" * 50)
        print("设备控制演示")
        print("=" * 50)

        print("请先填写上面的 entity_id，然后运行演示")
        print("示例格式：")
        print("- 灯: light.living_room_light")
        print("- 空调: climate.bedroom_ac")
        print("- 窗帘: cover.bedroom_curtain")
        print("- 智能开关: switch.speaker_power")

        # 演示控制（需要先填写 entity_id）
        for device_name, entity_id in demo_devices.items():
            if "你的" not in entity_id:  # 如果已经填写了真实的 entity_id
                device = device_name
                print(f"\n--- 控制 {device} ---")

                if device_name == "灯":
                    print("开灯...")
                    self.light_on(entity_id)
                    time.sleep(interval)
                    print("关灯...")
                    # self.light_off(entity_id)

                elif device_name == "空调":
                    print("开空调...")
                    self.ac_on(entity_id)
                    print("设置吹风模式...")
                    self.ac_set_mode(entity_id, "fan_only")
                    print("设置温度25度...")
                    self.ac_set_temp(entity_id, 25)
                    time.sleep(interval)
                    print("关空调...")
                    self.ac_off(entity_id)

                elif device_name == "窗帘":
                    print("关闭窗帘...")
                    self.curtain_close(entity_id)
                    time.sleep(interval)
                    print("打开窗帘...")
                    self.curtain_open(entity_id)

                elif device_name == "智能开关":
                    print("开启开关...")
                    self.switch_on(entity_id)
                    time.sleep(interval)
                    print("关闭开关...")
                    self.switch_off(entity_id)

                elif device_name == "tv_on":
                    entity = entity_id
                    print(f"开启开关...{entity}")
                    self.tv_on(entity_id)
                    # time.sleep(interval)
                    # print("关闭开关...")
                    # self.tv_off(entity_id)

                elif device_name == "tv_off":
                    print("关闭电视...")
                    self.tv_off(entity_id)



        print("\n演示完成！")


def main():
    """主函数"""
    # 配置信息
    server = ha_service_data["host"]
    port =  ha_service_data["port"]
    LONG_LIVED_TOKEN = ha_service_data["token"]
    # 请在这里填写你的设备 entity_id
    demo_devices = {
       "air_clean": "fan.fan.zhimi_cn_287827089_ma2_s_2_air_purifier",
        # "灯": "light.ftd_cn_1123337548_ftdlmp_s_2_light",
        # "tv_on": "button.xiaomi_cn_885441719_rmi1_turn_on_a_6_1",
        # "tv_off":"button.xiaomi_cn_885441719_rmi1_turn_off_a_7_1"
        # "空调": "climate.scdvb_cn_1102732000_acm",
        # "窗帘": "cover.xiaomi_cn_708478375_acn009_s_2_curtain",
        # "智能开关": "switch.090615_cn_792978759_akpro4_on_p_2_1"
    }

    print("Home Assistant 设备控制演示")
    server_val = server
    port_val = port
    print(f"服务器地址: {server_val}:{port_val}")
    print("=" * 50)

    # 创建演示实例
    demo = HomeAssistantControlDemo(server, port)
    demo.set_token(LONG_LIVED_TOKEN)

    # 检查连接
    if not demo.check_api():
        print("API连接失败，请检查网络和令牌")
        return

    # 运行演示
    demo.demo_control_devices(demo_devices, interval=10)


if __name__ == "__main__":
    main()

