# home-assistant restapi 文档
# https://developers.home-assistant.io/docs/api/rest/
# 服务器地址：http://103.112.185.171:8123/
# 长期访问令牌：eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI1MDhmYTZiNjJlMjE0M2FjOGRiYjAxMzhhNTVkMzQ3YSIsImlhdCI6MTc0OTgyMTIwOSwiZXhwIjoyMDY1MTgxMjA5fQ.ypsnM4IMhY6b7nqPt4qf5uBwP9COxJDfiVjGfGiJb28
#
# 注意：此演示程序需要一个有效的长期访问令牌（Long-Lived Access Token）
# 获取方法：在Home Assistant Web界面 -> 个人资料 -> 长期访问令牌 -> 创建令牌
# 请将获取的令牌替换下方的LONG_LIVED_TOKEN变量值

import requests

from src.ha.ha_data import ha_service_data

use_SSL = False
protocol_suffix = 's' if use_SSL else ''

class HomeAssistantAPI:
  def __init__(self, host, port=ha_service_data["port"]):
    """
    初始化Home Assistant API客户端

    参数:
        host: Home Assistant服务器地址
        port: Home Assistant服务器端口，默认为8123
    """
    self.base_url = f"http{protocol_suffix}://{host}:{port}"
    self.access_token = None
    self.headers = {
      "Content-Type": "application/json",
    }

  def set_token(self, token):
    """
    直接设置访问令牌（如果已经有长期访问令牌）

    参数:
        token: 长期访问令牌
    """
    self.access_token = token
    self.headers["Authorization"] = f"Bearer {self.access_token}"
    print("令牌已设置！")

  def check_api(self):
    """
    检查API是否正常运行

    返回:
        bool: API是否正常运行
    """
    base_url = self.base_url
    url = f"{base_url}/api/"
    try:
      response = requests.get(url, headers=self.headers)
      if response.status_code == 200:
        print("API正常运行！")
        return True
      else:
        print(f"API检查失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
      print(f"API检查过程中发生错误: {str(e)}")
      return False

  def get_config(self):
    """
    获取Home Assistant配置信息

    返回:
        dict: 配置信息
    """
    base_url = self.base_url
    url = f"{base_url}/api/config"
    try:
      response = requests.get(url, headers=self.headers)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取配置失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取配置过程中发生错误: {str(e)}")
      return None

  def get_services(self):
    """
    获取可用服务列表

    返回:
        list: 可用服务列表
    """
    base_url = self.base_url
    url = f"{base_url}/api/services"
    try:
      response = requests.get(url, headers=self.headers)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取服务列表失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取服务列表过程中发生错误: {str(e)}")
      return None

  def get_config_entries(self):
    """
    /api/config/config_entries/entry

    返回:
        list: 可用服务列表
    """
    base_url = self.base_url
    url = f"{base_url}/api/config/config_entries/entry"
    try:
      response = requests.get(url, headers=self.headers)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取 entry 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取 entry 过程中发生错误: {str(e)}")
      return None

  def create_flow(self, handler):
    """
    新建一条 flow

    返回:
        flow: flow
    """
    base_url = self.base_url
    url = f"{base_url}/api/config/config_entries/options/flow"

    json = {
      "handler": handler,
      "show_advanced_options": False
    }
    try:
      response = requests.post(url, headers=self.headers, json=json)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取 flows 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取 flows 过程中发生错误: {str(e)}")
      return None

  def post_flow_step1(self, flow_id):
    print(f"开始提交第一步 flow flow_id: {flow_id}")
    """
    提交第一步 flow

    返回:
        flow: 新建的 flow
    """
    base_url = self.base_url
    url = f"{base_url}/api/config/config_entries/options/flow/{flow_id}"

    json = {
      "integration_language": "zh-Hans",
      "update_user_info": False,
      "network_detect_config": False,
      "update_devices": True,
      "display_devices_changed_notify": [
        "add",
        "del",
        "offline"
      ],
      "update_lan_ctrl_config": False,
      "action_debug": False,
      "hide_non_standard_entities": False,
      "display_binary_mode": [
        "bool"
      ],
      "update_trans_rules": False
    }
    try:
      response = requests.post(url, headers=self.headers, json=json)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取 flows 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取 flows 过程中发生错误: {str(e)}")
      return None

  def post_flow_step2(self, flow_id, home_infos):
    print(f"开始提交第二步 flow flow_id: {flow_id}, home_infos: {home_infos}")

    base_url = self.base_url
    url = f"{base_url}/api/config/config_entries/options/flow/{flow_id}"

    json = {
      "home_infos": home_infos,
      "devices_filter": False,
      "ctrl_mode": "auto"
    }

    try:
      response = requests.post(url, headers=self.headers, json=json)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取 flows 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取 flows 过程中发生错误: {str(e)}")
      return None

  def post_flow_step3(self, flow_id):
    print(f"开始提交第三步 flow flow_id: {flow_id}")
    base_url = self.base_url
    url = f"{base_url}/api/config/config_entries/options/flow/{flow_id}"

    json = {
      "confirm": True
    }

    try:
      response = requests.post(url, headers=self.headers, json=json)
      if response.status_code == 200:
        return response.json()
      else:
        print(f"获取 flows 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"获取 flows 过程中发生错误: {str(e)}")
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
    url = f"{base_url}/api/config/config_entries/options/flow/{flow_id}"
    
    try:
      response = requests.delete(url, headers=self.headers)
      if response.status_code == 200:
        print(f"成功删除 flow: {flow_id}")
        return response.json()
      else:
        print(f"删除 flow 失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
      print(f"删除 flow 过程中发生错误: {str(e)}")
      return None

  def get_home_infos(self):
    config_entries = self.get_config_entries()
    if not config_entries:
      print("无法获取配置条目")
      return None, None
    xiaomi_entry = next((item for item in config_entries if item['domain'] == 'xiaomi_home'), None)
    if not xiaomi_entry:
      print("未找到小米集成配置")
      return None, None
    flow = self.create_flow(xiaomi_entry.get('entry_id'))
    if not flow:
      print("创建flow失败")
      return None, None
    flow_id = flow.get('flow_id')
    if not flow_id:
      print("获取flow_id失败")
      return None, None
    step2_data = self.post_flow_step1(flow_id)
    if not step2_data:
      print("获取step2数据失败")
      return None, None
    options = None
    default = None
    for item in step2_data.get('data_schema', []):
      if item.get('name') == 'home_infos':
        options = item.get('options')
        default = item.get('default')
        break
    return options, default

def find_xiaomi_integration(data):
  """查找 domain 为 'xiaomi_home' 的集成配置"""
  # 使用 next 函数获取第一个匹配项，若不存在则返回 None
  return next((item for item in data if item['domain'] == 'xiaomi_home'), None)



def demo():
  """
  演示如何使用 Home Assistant API
  """
  # 服务器地址
  server = ha_service_data["host"]
  port = 8123

  # 长期访问令牌
  # 可以在 Home Assistant 的个人资料页面生成
  # 路径: 个人资料 > 长期访问令牌 > 创建令牌
  LONG_LIVED_TOKEN = ha_service_data["token"]

  print("Home Assistant REST API 演示程序")
  print(f"服务器地址: {server}:{port}")
  print("-----------------------------------")


  # 创建API客户端
  ha_api = HomeAssistantAPI(server, port)
  # 设置长期访问令牌
  print("设置长期访问令牌...")
  ha_api.set_token(LONG_LIVED_TOKEN)

  # 检查API连接
  if not ha_api.check_api():
    print("API连接失败，请检查网络和令牌")
    return

  options, default = ha_api.get_home_infos()
  print("home_infos options:", options)
  print("home_infos default:", default)

  return

if __name__ == "__main__":
  print("\n开始演示...\n")

  demo()
