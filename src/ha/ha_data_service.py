import asyncio

from src.ha.ha_data import ha_service_data
from src.ha.ha_data_fecth_all_devices_service import HomeAssistantModelAPI
from src.ha.ha_data_fecth_service import HaDataFetchService
from src.ha.ha_data_post_service import HomeAssistantRegistrationAPI
from src.utils.device_fingerprint import get_device_fingerprint


class HaDataService:

    async def send_ha_data(self):
        """
        异步方法：获取设备信息并发送到 Home Assistant
        
        获取设备指纹、MAC地址、设备信息，然后从 Home Assistant 获取设备数据，
        最后将所有信息注册到 Home Assistant
        
        Returns:
            dict: 注册结果
        """
        # 获取 DeviceFingerprint 实例
        device_fingerprint = get_device_fingerprint()

        # 获取 MAC 地址和网卡类型
        mac_address, mac_type = device_fingerprint.get_mac_address()
        mac_address_val = mac_address
        mac_type_val = mac_type
        print(f"MAC 地址: {mac_address_val}, 类型: {mac_type_val}")

        xiaozhi_device_info = {
            "macAddress": mac_address,
            "friendlyName": "客厅小智",
            "board":"树莓派 5",
            "appVersion":"1.2"
        }

        ha = HaDataFetchService()
        ha.set_token()

        # 测试解析设备数据为注册格式
        home_info = ha.convert_home_data_to_home_info()

        # 创建 HomeAssistantModelAPI 实例并设置 token
        ha_model = HomeAssistantModelAPI()
        ha_model.set_token(ha_service_data["token"])
        
        # 异步获取设备信息
        ha_devices_info = await ha_model.parse_devices_for_registration()

        # 数据请求
        ha_api = HomeAssistantRegistrationAPI()
        result = ha_api.register_home_and_devices(home_info, xiaozhi_device_info, ha_devices_info)
        return result


if __name__ == '__main__':
    # 使用异步方式运行 send_ha_data 方法
    asyncio.run(HaDataService().send_ha_data())