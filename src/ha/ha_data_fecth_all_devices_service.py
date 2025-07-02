import requests
import json
import asyncio
import websockets
import ssl
import os

from src.ha.ha_data import ha_service_data, ha_device_data

use_SSL = ha_service_data['use_ssl']
protocol_suffix = 's' if use_SSL else ''


class HomeAssistantModelAPI:
    def __init__(self, host=ha_service_data['host'], port=ha_service_data['port']):
        protocol_suffix_value = protocol_suffix
        self.base_url = f'http{protocol_suffix_value}://{host}:{port}'
        self.ws_url = f'ws{protocol_suffix_value}://{host}:{port}/api/websocket'
        self.access_token = None
        self.headers = {
            'Content-Type': 'application/json',
        }

    def set_token(self, token):
        self.access_token = token
        access_token_val = self.access_token
        self.headers['Authorization'] = f'Bearer {access_token_val}'
        print('令牌已设置！')
        return self

    def get_states(self):
        base_url = self.base_url
        url = f'{base_url}/api/states'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取状态失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取状态过程中发生错误: {error_msg}')
            return None

    async def get_all_states_with_model_manufacturer(self):
        """
        异步方法：获取所有设备状态并添加制造商和型号信息
        
        通过 WebSocket 连接获取设备注册信息，然后将制造商和型号信息添加到设备状态中
        
        Returns:
            list: 包含制造商和型号信息的设备状态列表
        """
        states = self.get_states()
        # 获取所有设备并保存 manufacturer 和 model 信息
        protocol_suffix_value = protocol_suffix
        host_val = ha_service_data['host']
        port_val = ha_service_data['port']
        ws_url = f"ws{protocol_suffix_value}://{host_val}:{port_val}/api/websocket"
        ssl_context = ssl._create_unverified_context() if use_SSL else None

        # 定义内部异步函数获取设备注册信息
        async with websockets.connect(ws_url, ssl=ssl_context) as ws:
            await ws.recv()  # welcome
            await ws.send(json.dumps({
                'type': 'auth',
                'access_token': ha_service_data['token']
            }))
            await ws.recv()  # auth_ok
            await ws.send(json.dumps({
                'id': 1,
                'type': 'config/device_registry/list'
            }))
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get('id') == 1 and data.get('type') == 'result':
                    devices = data.get('result', [])
                    break

        if devices and states:
            # 简化 identifiers 匹配逻辑：只要 identifiers 的第二项包含在 entity_id 里就判为匹配
            for state in states:
                entity_id = state.get('entity_id', '')
                matched = None
                for dev in devices:
                    identifiers = dev.get('identifiers', [])
                    for ident in identifiers:
                        if isinstance(ident, list) and len(ident) > 1:
                            if str(ident[1]) in entity_id:
                                matched = {
                                    'manufacturer': dev.get('manufacturer'),
                                    'model': dev.get('model')
                                }
                                break
                    if matched:
                        break
                if matched:
                    state['manufacturer'] = matched['manufacturer']
                    state['model'] = matched['model']
                else:
                    state['manufacturer'] = None
                    state['model'] = None
            return states
        return states

    async def parse_devices_for_registration(self, entity_ids=None):
        """
        异步方法：将设备数据解析为注册所需的格式
        
        使用已获取的带有制造商和型号信息的设备状态，筛选并格式化为注册所需的格式
        
        Args:
            entity_ids (list, optional): 要解析的实体ID列表。如果为None，则使用ha_device_data中的所有设备。
            
        Returns:
            list: 包含设备信息的列表，每个设备包含haEntityId、friendlyName、manufacturer、model和onlineStatus
        """
        if entity_ids is None:
            entity_ids = list(ha_device_data.values())
        elif isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        
        ha_devices_info = []
        
        # 获取所有设备状态（带有manufacturer和model信息）
        all_states = await self.get_all_states_with_model_manufacturer()
        if not all_states:
            return ha_devices_info
        
        # 筛选出需要的设备并解析
        for state in all_states:
            if state.get('entity_id') in entity_ids:
                entity_id = state.get('entity_id')
                online_status = state.get('state') != 'unavailable'
                friendly_name = state.get('attributes', {}).get('friendly_name', entity_id)
                
                # 使用已获取的manufacturer和model信息
                manufacturer = state.get('manufacturer', '设备制造商')
                model = state.get('model', '设备型号')
                
                ha_devices_info.append({
                    'haEntityId': entity_id,
                    'friendlyName': friendly_name,
                    'manufacturer': manufacturer if manufacturer else '设备制造商',
                    'model': model if model else '设备型号',
                    'onlineStatus': online_status
                })
        
        return ha_devices_info


if __name__ == "__main__":
    # 替换为你的 Home Assistant 地址和 token
    host = ha_service_data['host']
    port = ha_service_data['port']

    # 长期访问令牌
    # 可以在 Home Assistant 的个人资料页面生成
    # 路径: 个人资料 > 长期访问令牌 > 创建令牌
    token = ha_service_data['token']

    ha = HomeAssistantModelAPI(host, port)
    ha.set_token(token)
    
    # 使用异步方式运行 parse_devices_for_registration 方法
    async def main():
        devices_info = await ha.parse_devices_for_registration()
        print(json.dumps(devices_info, ensure_ascii=False, indent=2))
    
    asyncio.run(main())

