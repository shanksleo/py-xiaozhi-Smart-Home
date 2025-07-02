import logging

from src.ha.ha_data import ha_service_data, ha_device_data
from src.ha.home_assistant_command import HomeAssistantControlDemo



def parse_command_json(json_data):
    """
    解析智能家居命令的 JSON 数据并执行相应的设备控制
    
    参数:
        json_data (dict): 包含智能家居命令的 JSON 数据
        
    示例 JSON 格式:
    {
        'session_id': 'cbe64e3e-4975-4a2e-8a04-5a412bbbb38d', 
        'type': 'smart_home', 
        'payload': {
            'ha_domain': 'light', 
            'ha_service': 'turn_on', 
            'arguments': {
                'entity_id': 'light.ftd_cn_1123337548_ftdlmp_s_2_light'
            }
        }
    }
    """
    try:
        data_str = json_data
        logging.info(f"data = {data_str}")
        # 检查 JSON 数据的基本结构
        if not isinstance(json_data, dict):
            logging.error("JSON 数据格式错误，应为字典类型")
            return False
            
        # 检查必要字段
        if 'type' not in json_data or json_data['type'] != 'smart_home':
            cmd_type = json_data.get('type')
            logging.error(f"不支持的命令类型: {cmd_type}")
            return False
            
        if 'payload' not in json_data or not isinstance(json_data['payload'], dict):
            logging.error("缺少 payload 字段或格式错误")
            return False
            
        payload = json_data['payload']
        
        # 提取设备类型和命令
        ha_domain = payload.get('ha_domain')
        ha_service = payload.get('ha_service')
        arguments = payload.get('arguments', {})
        
        if not ha_domain or not ha_service:
            logging.error(f"缺少必要的字段: ha_domain={ha_domain}, ha_service={ha_service}")
            return False
        
        # 记录接收到的设备类型和服务
        domain = ha_domain
        service = ha_service
        args = arguments
        logging.info(f"接收到命令: 设备类型={domain}, 服务={service}, 参数={args}")
        
        # 将 ha_service 转换为设备命令格式
        command_map = {
            # 通用命令
            'turn_on': 'ON',
            'turn_off': 'OFF',
            
            # 空调特定命令 (climate domain)
            'fan_only': 'fan_only',
            'set_temperature': 'set_temp',
            'set_hvac_mode': 'set_mode',  # 设置空调模式
            'set_fan_mode': 'set_fan',    # 设置风扇模式
            
            # 窗帘特定命令 (cover domain)
            'open_cover': 'ON',     # 映射到窗帘的 ON 命令
            'close_cover': 'OFF',   # 映射到窗帘的 OFF 命令
            'stop_cover': 'STOP',   # 停止窗帘命令
            
            # 灯光特定命令 (light domain)
            'set_brightness': 'set_brightness',  # 设置亮度
            'set_color': 'set_color',           # 设置颜色
            
            # 电视特定命令
            'press': 'PRESS'              # 按下按钮
        }
        
        device_command = command_map.get(ha_service)
        if not device_command:
            service = ha_service
            logging.error(f"不支持的服务: {service}")
            return False
        
        # 创建 HomeAssistant API 实例并执行命令
        ha_command_api = HomeAssistantCommandAPI()
        ha_command_api.command_device(ha_domain, device_command, arguments)
        
        return True
    except Exception as e:
        error_msg = str(e)
        logging.error(f"解析命令时出错: {error_msg}")
        return False



class HomeAssistantCommandAPI:
    def __init__(self, host=ha_service_data["host"], port=ha_service_data["port"]):
        self.demo = HomeAssistantControlDemo(host, port)
        self.demo.set_token(ha_service_data["token"])

    def command_device(self,device_type,device_command,params = {}):
        # 检查连接
        if not self.demo.check_api():
            print("API连接失败，请检查网络和令牌")
            return

        # 优先使用用户提供的实体 ID
        entity_id = params.get('entity_id')
        
        # 如果用户没有提供实体 ID，则使用预定义的实体 ID
        if not entity_id:
            if device_type not in ha_device_data.keys():
                dev_type = device_type
                logging.error(f"device_type = {dev_type} not in ha_device_data")
                return
            entity_id = ha_device_data.get(device_type)
        if device_type == "light":
            if device_command == "ON":
                print("打开灯...")
                self.demo.light_on(entity_id)
            elif device_command == "OFF":
                print("关闭灯...")
                self.demo.light_off(entity_id)
            elif device_command == "set_brightness":
                # 从参数中获取亮度值，范围1-255
                brightness = params.get('brightness', 255)
                brightness_val = brightness
                print(f"设置灯光亮度为{brightness_val}...")
                if hasattr(self.demo, 'light_set_brightness'):
                    self.demo.light_set_brightness(entity_id, brightness)
                else:
                    # 如果没有专门的亮度设置方法，可以通过 turn_on 命令附带亮度参数实现
                    self.demo.call_service("light", "turn_on", entity_id, {"brightness": brightness})
            elif device_command == "set_color":
                # 从参数中获取颜色值
                rgb_color = params.get('rgb_color', [255, 255, 255])
                color_val = rgb_color
                print(f"设置灯光颜色为{color_val}...")
                if hasattr(self.demo, 'light_set_color'):
                    self.demo.light_set_color(entity_id, rgb_color)
                else:
                    # 如果没有专门的颜色设置方法，可以通过 turn_on 命令附带颜色参数实现
                    self.demo.call_service("light", "turn_on", entity_id, {"rgb_color": rgb_color})


        elif device_type == "air_conditioner" or device_type == "climate":
            if device_command == "ON":
                print("打开空调...")
                self.demo.ac_on(entity_id)
            elif device_command == "OFF":
                print("关闭空调...")
                self.demo.ac_off(entity_id)
            elif device_command == "fan_only":
                print("设置空调为送风模式...")
                self.demo.ac_set_mode(entity_id, "fan_only")
            elif device_command == "set_temp":
                # 从参数中获取温度值，默认为25度
                temperature = params.get('temperature', 25)
                temp_val = temperature
                print(f"设置空调温度为{temp_val}度...")
                self.demo.ac_set_temp(entity_id, temperature)
            elif device_command == "set_mode":
                # 从参数中获取模式值
                mode = params.get('hvac_mode', 'auto')
                mode_val = mode
                print(f"设置空调模式为{mode_val}...")
                self.demo.ac_set_mode(entity_id, mode)
            elif device_command == "set_fan":
                # 从参数中获取风扇模式
                fan_mode = params.get('fan_mode', 'auto')
                fan_mode_val = fan_mode
                print(f"设置空调风扇模式为{fan_mode_val}...")
                if hasattr(self.demo, 'ac_set_fan_mode'):
                    self.demo.ac_set_fan_mode(entity_id, fan_mode)
                else:
                    logging.warning("ac_set_fan_mode 方法不存在，无法设置风扇模式")

        elif device_type == "curtain" or device_type == "cover":
            if device_command == "ON":
                print("打开窗帘...")
                self.demo.curtain_open(entity_id)
            elif device_command == "OFF":
                print("关闭窗帘...")
                self.demo.curtain_close(entity_id)
            elif device_command == "STOP":
                print("停止窗帘...")
                self.demo.curtain_stop(entity_id)
        elif device_type=="tv":
            if device_command == "ON":
                print("开启电视...")
                self.demo.tv_on(entity_id)
            elif device_command == "OFF":
                print("尝试关闭电视...")
                # 注意：button 实体类型不支持 turn_off 服务
                # 此处调用 tv_off 方法会尝试使用 media_player 服务
                self.demo.tv_off(entity_id)
            elif device_command == "PRESS":
                # 直接按下按钮
                print("按下电视按钮...")
                self.demo.tv_on(entity_id)

        elif device_type == "smart_switch":
            if device_command == "ON":
                print("开启开关...")
                self.demo.switch_on(entity_id)
            elif device_command == "OFF":
                print("关闭开关...")
                self.demo.switch_off(entity_id)


if __name__ == "__main__":
    # 示例1：解析命令JSON
    command_json = {
        "session_id": "ce37d536-205a-4451-b4da-da50ae180305",
        "type": "smart_home",
        "payload": {
            "ha_domain": "light",
            "ha_service": "turn_on",
            "arguments": {}
        }
    }
    
    result = parse_command_json(command_json)
    result_val = result
    print(f"命令执行结果: {result_val}")
    
    # 示例2：使用自定义实体ID
    command_json = {
        "session_id": "ce37d536-205a-4451-b4da-da50ae180305",
        "type": "smart_home",
        "payload": {
            "ha_domain": "light",
            "ha_service": "turn_off",
            "arguments": {
                "entity_id": "light.custom_light"
            }
        }
    }
    
    result = parse_command_json(command_json)
    result_val = result
    print(f"命令执行结果: {result_val}")
    
    # 示例3：控制窗帘
    command_json = {
        "session_id": "ce37d536-205a-4451-b4da-da50ae180305",
        "type": "smart_home",
        "payload": {
            "ha_domain": "cover",
            "ha_service": "open_cover",
            "arguments": {}
        }
    }
    
    result = parse_command_json(command_json)
    result_val = result
    print(f"命令执行结果: {result_val}")
    
    # 示例4：控制空调（使用climate领域）
    command_json = {
        "session_id": "ce37d536-205a-4451-b4da-da50ae180305",
        "type": "smart_home",
        "payload": {
            "ha_domain": "climate",
            "ha_service": "turn_on",
            "arguments": {
                "entity_id": "climate.scdvb_cn_1102732000_acm"
            }
        }
    }
    
    result = parse_command_json(command_json)
    result_val = result
    print(f"命令执行结果: {result_val}")
    
    # 示例5：使用button实体控制电视（按下按钮）
    command_json = {
        "session_id": "ce37d536-205a-4451-b4da-da50ae180305",
        "type": "smart_home",
        "payload": {
            "ha_domain": "button",
            "ha_service": "press",
            "arguments": {
                "entity_id": "button.tv_power"
            }
        }
    }
    
    result = parse_command_json(command_json)
    result_val = result
    print(f"命令执行结果: {result_val}")