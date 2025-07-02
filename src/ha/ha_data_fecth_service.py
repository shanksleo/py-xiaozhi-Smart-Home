import requests
import json
import asyncio
import websockets
import ssl
import os

from src.ha.ha_data import ha_device_data, ha_service_data

use_SSL = ha_service_data['use_ssl']
protocol_suffix = 's' if use_SSL else ''


class HaDataFetchService:
    def __init__(self, host=ha_service_data['host'], port=ha_service_data['port']):
        protocol_suffix_value = protocol_suffix
        self.base_url = f'http{protocol_suffix_value}://{host}:{port}'
        base_url_val = self.base_url
        print(f'base_url = {base_url_val}')
        self.ws_url = f'ws{protocol_suffix_value}://{host}:{port}/api/websocket'
        self.access_token = None
        self.headers = {
            'Content-Type': 'application/json',
        }

    def set_token(self, token=ha_service_data['token']):
        self.access_token = token
        access_token_val = self.access_token
        self.headers['Authorization'] = f'Bearer {access_token_val}'
        print('令牌已设置！')

    def get_config_entries(self):
        """
        /api/config/config_entries/entry

        返回:
            list: 可用服务列表
        """
        base_url = self.base_url
        url = f'{base_url}/api/config/config_entries/entry'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取 entry 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取 entry 过程中发生错误: {error_msg}')
            return None

    def create_flow(self, handler):
        """
        新建一条 flow

        返回:
            flow: flow
        """
        base_url = self.base_url
        url = f'{base_url}/api/config/config_entries/options/flow'

        json = {
            'handler': handler,
            'show_advanced_options': False
        }
        try:
            response = requests.post(url, headers=self.headers, json=json)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取 flows 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取 flows 过程中发生错误: {error_msg}')
            return None

    def post_flow_step1(self, flow_id):
        flow_id_val = flow_id
        print(f'开始提交第一步 flow flow_id: {flow_id_val}')
        """
        提交第一步 flow
  
        返回:
            flow: 新建的 flow
        """
        base_url = self.base_url
        flow_id_val = flow_id
        url = f'{base_url}/api/config/config_entries/options/flow/{flow_id_val}'

        json = {
            'integration_language': 'zh-Hans',
            'update_user_info': False,
            'network_detect_config': False,
            'update_devices': True,
            'display_devices_changed_notify': [
                'add',
                'del',
                'offline'
            ],
            'update_lan_ctrl_config': False,
            'action_debug': False,
            'hide_non_standard_entities': False,
            'display_binary_mode': [
                'bool'
            ],
            'update_trans_rules': False
        }
        try:
            response = requests.post(url, headers=self.headers, json=json)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取 flows 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取 flows 过程中发生错误: {error_msg}')
            return None

    def post_flow_step2(self, flow_id, home_infos):
        flow_id_val = flow_id
        home_infos_val = home_infos
        print(f'开始提交第二步 flow flow_id: {flow_id_val}, home_infos: {home_infos_val}')

        base_url = self.base_url
        flow_id_val = flow_id
        url = f'{base_url}/api/config/config_entries/options/flow/{flow_id_val}'

        json = {
            'home_infos': home_infos,
            'devices_filter': False,
            'ctrl_mode': 'auto'
        }

        try:
            response = requests.post(url, headers=self.headers, json=json)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取 flows 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取 flows 过程中发生错误: {error_msg}')
            return None

    def post_flow_step3(self, flow_id):
        flow_id_val = flow_id
        print(f'开始提交第三步 flow flow_id: {flow_id_val}')
        base_url = self.base_url
        flow_id_val = flow_id
        url = f'{base_url}/api/config/config_entries/options/flow/{flow_id_val}'

        json = {
            'confirm': True
        }

        try:
            response = requests.post(url, headers=self.headers, json=json)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取 flows 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取 flows 过程中发生错误: {error_msg}')
            return None

    def delete_flow(self, flow_id):
        """
        删除指定的 flow

        参数:
            flow_id: 要删除的 flow ID

        返回:
            dict: 删除结果
        """
        base_url = self.base_url
        flow_id_val = flow_id
        url = f'{base_url}/api/config/config_entries/options/flow/{flow_id_val}'

        try:
            response = requests.delete(url, headers=self.headers)
            if response.status_code == 200:
                flow_id_val = flow_id
                print(f'成功删除 flow: {flow_id_val}')
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'删除 flow 失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'删除 flow 过程中发生错误: {error_msg}')
            return None

    def get_states(self, entity_id):
        base_url = self.base_url
        entity_id_val = entity_id
        url = f'{base_url}/api/states/{entity_id_val}'
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

    def get_all_states(self):
        """获取所有设备状态"""
        base_url = self.base_url
        url = f'{base_url}/api/states'
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                status_code = response.status_code
                response_text = response.text
                print(f'获取所有状态失败: {status_code} - {response_text}')
                return None
        except Exception as e:
            error_msg = str(e)
            print(f'获取所有状态过程中发生错误: {error_msg}')
            return None

    def parse_devices_for_registration(self, entity_ids=None):
        """将设备数据解析为注册所需的格式
        
        Args:
            entity_ids (list, optional): 要解析的实体ID列表。如果为None，则使用ha_device_data中的所有设备。
            
        Returns:
            list: 包含设备信息的列表，每个设备包含haEntityId、friendlyName、manufacturer和model
        """
        if entity_ids is None:
            entity_ids = list(ha_device_data.values())
        elif isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        # 加载设备制造商信息
        manufacturer_data = {}
        manufacturer_file = os.path.join(os.path.dirname(__file__), 'device_manufacturer.json')
        if os.path.exists(manufacturer_file):
            try:
                with open(manufacturer_file, 'r', encoding='utf-8') as f:
                    manufacturer_data = json.load(f)
            except Exception as e:
                error_msg = str(e)
                print(f'加载设备制造商信息失败: {error_msg}')

        ha_devices_info = []

        # 获取所有设备状态
        all_states = self.get_all_states()
        if not all_states:
            return ha_devices_info

        # 筛选出需要的设备并解析
        for state in all_states:
            if state.get('entity_id') in entity_ids:
                entity_id = state.get('entity_id')
                online_status = state.get('status') != 'unavailable'
                friendly_name = state.get('attributes', {}).get('friendly_name', entity_id)

                # 尝试获取设备ID和制造商信息
                device_id = state.get('context', {}).get('id', '')
                manufacturer = manufacturer_data.get(device_id, '设备制造商')

                # 尝试获取设备型号
                model = state.get('attributes', {}).get('model', '设备型号')

                ha_devices_info.append({
                    'haEntityId': entity_id,
                    'friendlyName': friendly_name,
                    'manufacturer': manufacturer if manufacturer else '设备制造商',
                    'model': model,
                    'onlineStatus': online_status

                })

        return ha_devices_info

    def get_home_infos(self):
        config_entries = self.get_config_entries()
        if not config_entries:
            print('无法获取配置条目')
            return None, None
        xiaomi_entry = next((item for item in config_entries if item['domain'] == 'xiaomi_home'), None)
        if not xiaomi_entry:
            print('未找到小米集成配置')
            return None, None
        flow = self.create_flow(xiaomi_entry.get('entry_id'))
        if not flow:
            print('创建flow失败')
            return None, None
        flow_id = flow.get('flow_id')
        if not flow_id:
            print('获取flow_id失败')
            return None, None
        step2_data = self.post_flow_step1(flow_id)
        if not step2_data:
            print('获取step2数据失败')
            return None, None
        options = None
        default = None
        for item in step2_data.get('data_schema', []):
            if item.get('name') == 'home_infos':
                options = item.get('options')
                default = item.get('default')
                break
        return options, default

    def convert_home_data_to_home_info(self, home_data = None):
        if not home_data:
            home_data,default_data = self.get_home_infos()

        """
        将家庭数据转换为home_info格式
        
        Args:
            home_data (dict): 家庭数据，格式如 {'220868661': '楠哥 [ 4 个设备  ]', '607001073747': 'shanks_的家 [ 22 个设备  ]'}
            
        Returns:
            dict: 转换后的home_info格式数据，包含name和mijiaAccount
        """
        if not home_data or not isinstance(home_data, dict) or len(home_data) == 0:
            print('家庭数据为空或格式不正确')
            return {
                'name': '我的智能家庭',
                'mijiaAccount': 'test@example.com'
            }

        try:
            # 获取第一个键值对
            first_key = next(iter(home_data))
            first_value = home_data[first_key]

            # 提取家庭名称，去除设备数量信息
            home_name = first_value.split('[')[0].strip() if '[' in first_value else first_value

            # 创建home_info对象
            home_info = {
                'name': home_name,
                'mijiaAccount': first_key  # 将键作为homeId
            }

            # 如果有设备数量信息，也可以提取出来
            # if '[' in first_value and ']' in first_value:
            #     devices_info = first_value.split('[')[1].split(']')[0].strip()
            #     if '个设备' in devices_info:
            #         try:
            #             device_count = int(devices_info.split('个')[0].strip())
            #             home_info['deviceCount'] = device_count
            #         except ValueError:
            #             pass

            return home_info
        except Exception as e:
            error_msg = str(e)
            print(f'转换数据格式时发生错误: {error_msg}')
            return {
                'name': '我的智能家庭',
                'mijiaAccount': 'test@example.com'
            }


if __name__ == "__main__":
    ha = HaDataFetchService()
    ha.set_token()

    # 测试解析设备数据为注册格式
    ha_devices_info = ha.parse_devices_for_registration()
    print('解析后的设备信息:')
    print(json.dumps(ha_devices_info, ensure_ascii=False, indent=4))

    home_info = ha.convert_home_data_to_home_info()
    home_info_val = home_info
    print(f'home_info = {home_info_val}')
    # 原始测试代码
    # for key, values in ha_device_data.items():
    #     print(f"{key} = {values}")
    #     states = ha.get_states(entity_id=values)
    #     print(f"{key}的状态:{states}")
