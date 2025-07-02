import requests
import json

from src.ha.ha_data import ha_service_data, xiao_zhi_server_data
from src.ha.ha_data_fecth_service import HaDataFetchService

use_SSL = xiao_zhi_server_data["use_ssl"]
protocol_suffix = 's' if use_SSL else ''

class HomeAssistantRegistrationAPI:
    def __init__(self, host=xiao_zhi_server_data["host"], port=xiao_zhi_server_data["port"]):
        self.base_url = f"http{protocol_suffix}://{host}:{port}"
        print(f"base_url = {self.base_url}")
        self.access_token = None
        token = xiao_zhi_server_data["token"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

    def register_home_and_devices(self, home_info, xiaozhi_device_info, ha_devices_info):
        """
        注册家庭及下属所有设备
        
        接口地址: /xiaozhi/smart-home/register
        请求方式: POST
        请求数据类型: application/json
        
        Args:
            home_info (dict): 家庭信息，包含name和mijiaAccount
            xiaozhi_device_info (dict): 小智设备信息，包含macAddress和friendlyName
            ha_devices_info (list): HA设备列表，每个设备包含haEntityId、friendlyName、manufacturer和model
            
        Returns:
            dict: 注册结果，包含homeId和defaultRoomId，如果失败则返回None
        """
        base_url = self.base_url
        url = f"{base_url}/xiaozhi/smart-home/register"
        
        # 构建请求数据
        request_data = {
            "home": home_info,
            "xiaozhiDevice": xiaozhi_device_info,
            "haDevices": ha_devices_info
        }
        
        try:
            # 打印请求详情
            print("\n请求URL:", url)
            print("请求头:", json.dumps(self.headers, ensure_ascii=False, indent=2))
            print("请求数据:", json.dumps(request_data, ensure_ascii=False, indent=2))
            
            response = requests.post(url, headers=self.headers, json=request_data)
            
            # 打印响应详情
            print("\n响应状态码:", response.status_code)
            print("响应头:", dict(response.headers))
            print("响应内容:", response.text)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print(f"注册成功！家庭ID: {result['data']['homeId']}, 默认房间ID: {result['data']['defaultRoomId']}")
                    return result['data']
                else:
                    print(f"注册失败: {result.get('msg')}")
                    return None
            else:
                print(f"注册请求失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"注册过程中发生错误: {str(e)}")
            return None
            
    def filter_devices_info(self, devices_info):
        """
        剔除设备信息中的onlineStatus参数
        
        Args:
            devices_info (list): 设备信息列表
            
        Returns:
            list: 处理后的设备信息列表，不包含onlineStatus参数
        """
        filtered_devices = []
        for device in devices_info:
            # 创建设备信息的副本，避免修改原始数据
            filtered_device = device.copy()
            # 如果存在onlineStatus字段，则移除
            if 'onlineStatus' in filtered_device:
                del filtered_device['onlineStatus']
            filtered_devices.append(filtered_device)
        return filtered_devices
    
    def update_devices(self, mac_address, ha_devices_info):
        """
        更新设备信息
        
        接口地址: /xiaozhi/smart-home/devices/update
        请求方式: POST
        请求数据类型: application/json
        
        Args:
            mac_address (str): 小智设备MAC地址
            ha_devices_info (list): HA设备信息列表
            
        Returns:
            dict: 更新结果，如果失败则返回None
        """
        base_url = self.base_url
        url = f"{base_url}/xiaozhi/smart-home/devices/state"
        
        try:
            # 打印请求详情
            print("\n请求URL:", url)
            print("请求头:", json.dumps(self.headers, ensure_ascii=False, indent=2))

            # 剔除设备信息中的onlineStatus参数
            filtered_devices = self.filter_devices_info(ha_devices_info)
            
            # 构建请求数据
            device_update_info = {
                "macAddress": mac_address,
                "devices": filtered_devices,
            }
            print("请求数据:", json.dumps(device_update_info, ensure_ascii=False, indent=2))

            response = requests.post(url, headers=self.headers, json=device_update_info)
            
            # 打印响应详情
            print("\n响应状态码:", response.status_code)
            print("响应头:", dict(response.headers))
            print("响应内容:", response.text)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print(f"设备更新成功！")
                    return result.get('data')
                else:
                    print(f"设备更新失败: {result.get('msg')}")
                    return None
            else:
                print(f"设备更新请求失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"设备更新过程中发生错误: {str(e)}")
            return None
            
    def log_action(self, mac_address, ha_entity_id, function_name, ha_domain, ha_service, arguments, status, result_message, execution_duration_ms):
        """
        记录设备操作日志
        
        接口地址: /xiaozhi/smart-home/action-logs
        请求方式: POST
        请求数据类型: application/json
        
        Args:
            mac_address (str): 小智设备MAC地址
            ha_entity_id (str): Home Assistant实体ID
            function_name (str): 功能名称
            ha_domain (str): Home Assistant域
            ha_service (str): Home Assistant服务
            arguments (str): 参数
            status (str): 状态
            result_message (str): 结果消息
            execution_duration_ms (int): 执行时长(毫秒)
            
        Returns:
            dict: 记录结果，如果失败则返回None
        """
        base_url = self.base_url
        url = f"{base_url}/xiaozhi/smart-home/action-logs"
        
        try:
            # 构建请求数据
            action_log_data = {
                "macAddress": mac_address,
                "haEntityId": ha_entity_id,
                "functionName": function_name,
                "haDomain": ha_domain,
                "haService": ha_service,
                "arguments": arguments,
                "status": status,
                "resultMessage": result_message,
                "executionDurationMs": execution_duration_ms
            }
            
            # 打印请求详情
            print("\n请求URL:", url)
            print("请求头:", json.dumps(self.headers, ensure_ascii=False, indent=2))
            print("请求数据:", json.dumps(action_log_data, ensure_ascii=False, indent=2))
            
            response = requests.post(url, headers=self.headers, json=action_log_data)
            
            # 打印响应详情
            print("\n响应状态码:", response.status_code)
            print("响应头:", dict(response.headers))
            print("响应内容:", response.text)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print(f"操作日志记录成功！")
                    return result.get('data')
                else:
                    print(f"操作日志记录失败: {result.get('msg')}")
                    return None
            else:
                print(f"操作日志记录请求失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"操作日志记录过程中发生错误: {str(e)}")
            return None


if __name__ == "__main__":
    # 导入所需模块
    from src.utils.device_fingerprint import get_device_fingerprint
    import sys
    import time
    
    # 创建API实例
    ha_api = HomeAssistantRegistrationAPI()
    
    # 获取命令行参数，决定测试哪个功能
    test_mode = "all"  # 默认测试所有功能
    if len(sys.argv) > 1:
        test_mode = sys.argv[1]
    
    # 获取设备MAC地址
    device_fingerprint = get_device_fingerprint()
    mac_address, mac_type = device_fingerprint.get_mac_address()
    print(f"MAC 地址: {mac_address}, 类型: {mac_type}")
    
    # 测试1: 设备更新功能
    if test_mode in ["update", "all"]:
        print("\n===== 测试设备更新功能 =====")
        
        # # 构建设备更新请求参数
        # device_update_info = {
        #     "macAddress": mac_address,
        #     "devices": [
        #         {
        #             "haEntityId": "light.ftd_cn_1123337548_ftdlmp_s_2_light",
        #             "friendlyName": "客厅灯",
        #             "manufacturer": "设备制造商",
        #             "model": "设备型号",
        #             "onlineStatus": True
        #         },
        #         {
        #             "haEntityId": "switch.smart_plug_1",
        #             "friendlyName": "卧室插座",
        #             "manufacturer": "智能家居公司",
        #             "model": "SP100",
        #             "onlineStatus": True
        #         }
        #     ]
        # }
        #
        # # 调用设备更新方法
        # update_result = ha_api.update_devices(mac_address,device_update_info)
        # print(f"设备更新结果: {update_result}")
    
    # 测试2: 家庭和设备注册功能
    if test_mode in ["register", "all"]:
        print("\n===== 测试家庭和设备注册功能 =====")
        
        # 示例数据
        home_info = {
            "name": "我的智能家庭",
            "mijiaAccount": "test@example.com"
        }
        
        xiaozhi_device_info = {
            "macAddress": mac_address,
            "friendlyName": "客厅小智",
            "board":"树莓派 5",
            "appVersion":"1.2"
        }
        
        ha_devices_info = [
            {
                "haEntityId": "light.ftd_cn_1123337548_ftdlmp_s_2_light",
                "friendlyName": "客厅灯",
                "manufacturer": "设备制造商",
                "model": "设备型号",
                "onlineStatus": True
            }
        ]
        
        # 使用HaDataFetchService获取实际设备数据
        ha = HaDataFetchService()
        ha.set_token()
        
        # 测试解析设备数据为注册格式
        # ha_devices_info = ha.parse_devices_for_registration()
        # home_info = ha.convert_home_data_to_home_info()
        
        # 调用注册方法
        # register_result = ha_api.register_home_and_devices(home_info, xiaozhi_device_info, ha_devices_info)
        # print(f"注册结果: {register_result}")
        
        # # 调用设备更新方法
        # update_result = ha_api.update_devices(mac_address, ha_devices_info)
        # print(f"更新结果: {update_result}")
    
    # 测试3: 操作日志记录功能
    if test_mode in ["log", "all"]:
        print("\n===== 测试操作日志记录功能 =====")
        
        # 模拟一个操作日志记录
        start_time = time.time()
        # 模拟操作执行时间
        time.sleep(0.5)  # 模拟操作耗时500毫秒
        execution_time = int((time.time() - start_time) * 1000)  # 转换为毫秒
        
        # 构建操作日志参数
        ha_entity_id = "light.living_room"
        function_name = "打开灯光"
        ha_domain = "light"
        ha_service = "turn_on"
        arguments = "{\"brightness\": 255}"
        status = "success"  # 或 "failed"
        result_message = "操作成功完成"
        
        # 调用操作日志记录方法
        log_result = ha_api.log_action(
            mac_address=mac_address,
            ha_entity_id=ha_entity_id,
            function_name=function_name,
            ha_domain=ha_domain,
            ha_service=ha_service,
            arguments=arguments,
            status=status,
            result_message=result_message,
            execution_duration_ms=execution_time
        )
        print(f"操作日志记录结果: {log_result}")
        
    print("\n测试完成！")
    print("使用方法: python -m src.ha.ha_data_post_service [register|update|log|all]")
    print("  register: 测试家庭和设备注册功能")
    print("  update: 测试设备更新功能")
    print("  log: 测试操作日志记录功能")
    print("  all: 测试所有功能(默认)")