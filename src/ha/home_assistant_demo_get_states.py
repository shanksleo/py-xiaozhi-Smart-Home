import requests
import json
import asyncio
import websockets
import ssl

from src.ha.ha_data import ha_service_data

use_SSL = ha_service_data["use_ssl"]
protocol_suffix = 's' if use_SSL else ''

class HomeAssistantAPI:
    def __init__(self, host, port=ha_service_data["port"]):
        protocol_suffix_value = protocol_suffix
        self.base_url = f"http{protocol_suffix_value}://{host}:{port}"
        self.ws_url = f"ws{protocol_suffix_value}://{host}:{port}/api/websocket"
        self.access_token = None
        self.headers = {
            "Content-Type": "application/json",
        }

    def set_token(self, token):
        self.access_token = token
        self.headers["Authorization"] = f"Bearer {self.access_token}"
        print("令牌已设置！")

    def get_states(self):
        base_url = self.base_url
        url = f"{base_url}/api/states"
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
    host = "103.112.185.171"  # 或你的 HA 服务器地址
    port = 8123
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI1MDhmYTZiNjJlMjE0M2FjOGRiYjAxMzhhNTVkMzQ3YSIsImlhdCI6MTc0OTgyMTIwOSwiZXhwIjoyMDY1MTgxMjA5fQ.ypsnM4IMhY6b7nqPt4qf5uBwP9COxJDfiVjGfGiJb28"

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

        for state in states:
            entity_id = state['entity_id']
            state_value = state['state']
            print(f"{entity_id}: {state_value}")

        # 获取所有设备并保存 manufacturer 信息
        import asyncio
        import websockets
        import ssl
        protocol_suffix_value = protocol_suffix
        ws_url = f"ws{protocol_suffix_value}://{host}:{port}/api/websocket"
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
            device_manufacturer_map = {dev.get('id'): dev.get('manufacturer') for dev in devices}
            with open('device_manufacturer.json', 'w', encoding='utf-8') as f:
                json.dump(device_manufacturer_map, f, ensure_ascii=False, indent=2)
            print('已保存到 device_manufacturer.json')
