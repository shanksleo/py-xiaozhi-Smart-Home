import requests
import json
import asyncio
import websockets
import ssl

from src.ha.ha_data import ha_service_data

use_SSL = False
protocol_suffix = 's' if use_SSL else ''

class HomeAssistantAPI:
    def __init__(self, host, port=ha_service_data["port"]):
        self.base_url = f"http{protocol_suffix}://{host}:{port}"
        self.ws_url = f"ws{protocol_suffix}://{host}:{port}/api/websocket"
        self.access_token = None
        self.headers = {
            "Content-Type": "application/json",
        }

    def set_token(self, token):
        self.access_token = token
        self.headers["Authorization"] = f"Bearer {self.access_token}"
        print("令牌已设置！")

    def get_states(self):
        url = f"{self.base_url}/api/states"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取状态失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取状态过程中发生错误: {str(e)}")
            return None

if __name__ == "__main__":
    # 替换为你的 Home Assistant 地址和 token
    host = ha_service_data["host"]
    port = 8123

    # 长期访问令牌
    # 可以在 Home Assistant 的个人资料页面生成
    # 路径: 个人资料 > 长期访问令牌 > 创建令牌
    token = ha_service_data["token"]

    ha = HomeAssistantAPI(host, port)
    ha.set_token(token)
    states = ha.get_states()
    if states:
        with open('0618_states.json', 'w', encoding='utf-8') as f:
            json.dump(states, f, ensure_ascii=False, indent=2)
        print('已保存到 0618_states.json')

        # 按 domain 分类
        domain_dict = {}
        for state in states:
            entity_id = state.get('entity_id', '')
            if '.' in entity_id:
                domain = entity_id.split('.', 1)[0]
                domain_dict.setdefault(domain, []).append(state)
        with open('0618_states_domain.json', 'w', encoding='utf-8') as f:
            json.dump(domain_dict, f, ensure_ascii=False, indent=2)
        print('已保存到 0618_states_domain.json')

        # 获取所有设备并保存 manufacturer 和 model 信息
        import asyncio
        import websockets
        import ssl
        ws_url = f"ws{protocol_suffix}://{host}:{port}/api/websocket"
        ssl_context = ssl._create_unverified_context() if use_SSL else None
        async def inner():
            async with websockets.connect(ws_url, ssl=ssl_context) as ws:
                await ws.recv()  # welcome
                await ws.send(json.dumps({
                    "type": "auth",
                    "access_token": token
                }))
                await ws.recv()  # auth_ok
                await ws.send(json.dumps({
                    "id": 1,
                    "type": "config/device_registry/list"
                }))
                while True:
                    resp = await ws.recv()
                    data = json.loads(resp)
                    if data.get("id") == 1 and data.get("type") == "result":
                        return data.get("result", [])
        devices = asyncio.run(inner())
        if devices:
            with open('0618_devices.json', 'w', encoding='utf-8') as f:
                json.dump(devices, f, ensure_ascii=False, indent=2)
            print('已保存到 0618_devices.json')

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

            # 保存新 states 文件
            with open('0618_states_with_manufacturer.json', 'w', encoding='utf-8') as f:
                json.dump(states, f, ensure_ascii=False, indent=2)
            print('已保存到 0618_states_with_manufacturer.json')

