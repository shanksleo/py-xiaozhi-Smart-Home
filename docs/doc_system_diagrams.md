# 智能家居设备控制系统架构图

本文档包含系统的各种架构图和流程图，帮助理解系统设计和数据流向。

## 1. 系统整体架构图

```mermaid
graph TB
    subgraph "用户层 User Layer"
        U[用户 User]
        CLI[命令行接口 CLI]
        CONFIG[配置参数 Config]
    end
    
    subgraph "应用层 Application Layer"
        MAIN[main函数]
        DEMO[HomeAssistantControlDemo类]
        MAPPER[设备映射器 Device Mapper]
    end
    
    subgraph "数据层 Data Layer"
        HADATA[ha_device_data]
        SERVICEDATA[ha_service_data]
        MAPPING[device_type_mapping]
    end
    
    subgraph "接口层 Interface Layer"
        RESTAPI[REST API Client]
        WEBSOCKET[WebSocket Client]
    end
    
    subgraph "Home Assistant 层"
        HACORE[Home Assistant Core]
        HAAPI[Home Assistant API]
    end
    
    subgraph "设备层 Device Layer"
        LIGHT[智能灯光]
        AC[空调设备]
        CURTAIN[智能窗帘]
        SWITCH[智能开关]
        TV[智能电视]
        FAN[空气净化器]
    end
    
    U --> CLI
    CLI --> MAIN
    CONFIG --> MAIN
    MAIN --> DEMO
    DEMO --> MAPPER
    MAPPER --> HADATA
    MAPPER --> SERVICEDATA
    MAPPER --> MAPPING
    DEMO --> RESTAPI
    DEMO --> WEBSOCKET
    RESTAPI --> HAAPI
    WEBSOCKET --> HAAPI
    HAAPI --> HACORE
    HACORE --> LIGHT
    HACORE --> AC
    HACORE --> CURTAIN
    HACORE --> SWITCH
    HACORE --> TV
    HACORE --> FAN
```

## 2. 设备控制流程图

```mermaid
flowchart TD
    START([开始]) --> INIT[初始化HomeAssistantControlDemo]
    INIT --> SETTOKEN[设置访问令牌]
    SETTOKEN --> CHECKAPI{检查API连接}
    
    CHECKAPI -->|成功| LOADDEVICES[加载设备数据]
    CHECKAPI -->|失败| ERROR1[显示连接错误]
    ERROR1 --> END1([结束])
    
    LOADDEVICES --> PARSECONFIG[解析配置参数]
    PARSECONFIG --> FILTERDEVICES{过滤设备列表}
    
    FILTERDEVICES -->|指定设备| SPECIFICDEVICES[使用指定设备]
    FILTERDEVICES -->|全部设备| ALLDEVICES[使用全部设备]
    
    SPECIFICDEVICES --> STARTDEMO[开始设备演示]
    ALLDEVICES --> STARTDEMO
    
    STARTDEMO --> LOOPDEVICES[遍历设备列表]
    LOOPDEVICES --> GETDEVICE[获取设备信息]
    GETDEVICE --> MAPTYPE[映射设备类型]
    
    MAPTYPE --> CHECKTYPE{设备类型判断}
    
    CHECKTYPE -->|light| CONTROLLIGHT[控制灯光设备]
    CHECKTYPE -->|air_conditioner| CONTROLAC[控制空调设备]
    CHECKTYPE -->|curtain| CONTROLCURTAIN[控制窗帘设备]
    CHECKTYPE -->|smart_switch| CONTROLSWITCH[控制智能开关]
    CHECKTYPE -->|tv| CONTROLTV[控制电视设备]
    CHECKTYPE -->|air_clean| CONTROLFAN[控制空气净化器]
    CHECKTYPE -->|unknown| SKIPDEVICE[跳过未知设备]
    
    CONTROLLIGHT --> CALLAPI1[调用Home Assistant API]
    CONTROLAC --> CALLAPI2[调用Home Assistant API]
    CONTROLCURTAIN --> CALLAPI3[调用Home Assistant API]
    CONTROLSWITCH --> CALLAPI4[调用Home Assistant API]
    CONTROLTV --> CALLAPI5[调用Home Assistant API]
    CONTROLFAN --> CALLAPI6[调用Home Assistant API]
    
    CALLAPI1 --> LOGRESULT1[记录操作结果]
    CALLAPI2 --> LOGRESULT2[记录操作结果]
    CALLAPI3 --> LOGRESULT3[记录操作结果]
    CALLAPI4 --> LOGRESULT4[记录操作结果]
    CALLAPI5 --> LOGRESULT5[记录操作结果]
    CALLAPI6 --> LOGRESULT6[记录操作结果]
    
    LOGRESULT1 --> WAIT1[等待间隔时间]
    LOGRESULT2 --> WAIT2[等待间隔时间]
    LOGRESULT3 --> WAIT3[等待间隔时间]
    LOGRESULT4 --> WAIT4[等待间隔时间]
    LOGRESULT5 --> WAIT5[等待间隔时间]
    LOGRESULT6 --> WAIT6[等待间隔时间]
    SKIPDEVICE --> NEXTDEVICE
    
    WAIT1 --> NEXTDEVICE{还有设备?}
    WAIT2 --> NEXTDEVICE
    WAIT3 --> NEXTDEVICE
    WAIT4 --> NEXTDEVICE
    WAIT5 --> NEXTDEVICE
    WAIT6 --> NEXTDEVICE
    
    NEXTDEVICE -->|是| LOOPDEVICES
    NEXTDEVICE -->|否| COMPLETE[演示完成]
    COMPLETE --> END2([结束])
```

## 3. API调用时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant M as main函数
    participant D as HomeAssistantControlDemo
    participant API as Home Assistant API
    participant DEV as 智能设备
    
    Note over U,DEV: 系统初始化阶段
    U->>M: 启动程序
    M->>M: 加载配置参数
    Note right of M: TEST_INTERVAL=5<br/>SPECIFIC_DEVICE_KEYS=None<br/>VERBOSE_LOGGING=True
    
    M->>M: 导入设备数据
    Note right of M: 从ha_device_data加载设备列表
    
    M->>D: 创建控制器实例
    Note right of D: HomeAssistantControlDemo(host, port)
    
    M->>D: set_token(token)
    D->>D: 设置认证头
    
    Note over U,DEV: API连接检查阶段
    M->>D: check_api()
    D->>API: GET /api/
    API-->>D: {"message": "API running."}
    D-->>M: True
    
    Note over U,DEV: 设备控制演示阶段
    M->>D: demo_control_devices(devices, interval, keys)
    
    loop 遍历每个设备
        D->>D: 解析设备类型
        Note right of D: 根据device_type_mapping<br/>确定设备类型和控制方法
        
        alt 灯光设备
            D->>D: _control_light(entity_id, interval)
            D->>API: POST /api/services/light/turn_on
            Note right of API: {"entity_id": "light.xxx"}
            API->>DEV: 发送开灯指令
            DEV-->>API: 执行成功
            API-->>D: 200 OK
            D->>D: 记录成功日志
            
            Note over D: 等待间隔时间
            
            D->>API: POST /api/services/light/turn_off
            API->>DEV: 发送关灯指令
            DEV-->>API: 执行成功
            API-->>D: 200 OK
            D->>D: 记录成功日志
            
        else 空调设备
            D->>D: _control_air_conditioner(entity_id, interval)
            D->>API: POST /api/services/climate/turn_on
            API->>DEV: 发送开空调指令
            DEV-->>API: 执行成功
            API-->>D: 200 OK
            
            D->>API: POST /api/services/climate/turn_off
            API->>DEV: 发送关空调指令
            DEV-->>API: 执行成功
            API-->>D: 200 OK
            
        else 其他设备类型
            Note right of D: 类似的控制流程
        end
        
        D->>D: 等待TEST_INTERVAL秒
    end
    
    D-->>M: 演示完成
    M-->>U: 显示完成信息
```

## 4. 设备映射系统类图

```mermaid
classDiagram
    class HomeAssistantControlDemo {
        -base_url: str
        -headers: dict
        +__init__(host: str, port: int)
        +set_token(token: str): void
        +check_api(): bool
        +call_service(domain: str, service: str, entity_id: str, data: dict): bool
        +demo_control_devices(demo_devices: dict, interval: int, device_keys: list): void
        +light_on(entity_id: str): bool
        +light_off(entity_id: str): bool
        +light_set_brightness(entity_id: str, brightness: int): bool
        +ac_on(entity_id: str): bool
        +ac_off(entity_id: str): bool
        +curtain_open(entity_id: str): bool
        +curtain_close(entity_id: str): bool
        +switch_on(entity_id: str): bool
        +switch_off(entity_id: str): bool
        +tv_on(entity_id: str): bool
        +air_cleaner_on(entity_id: str): bool
        +air_cleaner_off(entity_id: str): bool
        -_control_light(entity_id: str, interval: int): void
        -_control_air_conditioner(entity_id: str, interval: int): void
        -_control_curtain(entity_id: str, interval: int): void
        -_control_smart_switch(entity_id: str, interval: int): void
        -_control_tv(entity_id: str, interval: int): void
        -_control_air_cleaner(entity_id: str, interval: int): void
    }
    
    class DeviceDataManager {
        <<static>>
        +ha_device_data: dict
        +ha_service_data: dict
        +get_device_by_key(key: str): str
        +get_all_devices(): dict
        +validate_device_data(): bool
    }
    
    class DeviceTypeMapper {
        <<static>>
        +device_type_mapping: dict
        +get_device_info(device_type: str): dict
        +get_domain(device_type: str): str
        +get_friendly_name(device_type: str): str
        +is_supported_type(device_type: str): bool
    }
    
    class ConfigManager {
        <<static>>
        +TEST_INTERVAL: int
        +SPECIFIC_DEVICE_KEYS: list
        +VERBOSE_LOGGING: bool
        +validate_config(): bool
        +get_filtered_devices(all_devices: dict): dict
    }
    
    class APIClient {
        -session: requests.Session
        +get(url: str): Response
        +post(url: str, data: dict): Response
        +handle_response(response: Response): bool
        +handle_error(error: Exception): void
    }
    
    HomeAssistantControlDemo --> DeviceDataManager : uses
    HomeAssistantControlDemo --> DeviceTypeMapper : uses
    HomeAssistantControlDemo --> ConfigManager : uses
    HomeAssistantControlDemo --> APIClient : uses
    
    DeviceDataManager --> DeviceTypeMapper : validates with
    ConfigManager --> DeviceDataManager : filters
```

## 5. 错误处理流程图

```mermaid
flowchart TD
    START([开始操作]) --> TRYCALL[尝试API调用]
    TRYCALL --> CHECKRESP{检查响应状态}
    
    CHECKRESP -->|200 OK| SUCCESS[操作成功]
    CHECKRESP -->|401 Unauthorized| AUTH_ERROR[认证错误]
    CHECKRESP -->|404 Not Found| NOT_FOUND[设备不存在]
    CHECKRESP -->|500 Server Error| SERVER_ERROR[服务器错误]
    CHECKRESP -->|其他错误| OTHER_ERROR[其他HTTP错误]
    
    SUCCESS --> LOG_SUCCESS[记录成功日志]
    LOG_SUCCESS --> RETURN_TRUE[返回True]
    
    AUTH_ERROR --> LOG_AUTH[记录认证错误]
    LOG_AUTH --> SUGGEST_TOKEN[建议检查令牌]
    SUGGEST_TOKEN --> RETURN_FALSE1[返回False]
    
    NOT_FOUND --> LOG_NOT_FOUND[记录设备未找到]
    LOG_NOT_FOUND --> SUGGEST_ENTITY[建议检查entity_id]
    SUGGEST_ENTITY --> RETURN_FALSE2[返回False]
    
    SERVER_ERROR --> LOG_SERVER[记录服务器错误]
    LOG_SERVER --> SUGGEST_HA[建议检查HA状态]
    SUGGEST_HA --> RETURN_FALSE3[返回False]
    
    OTHER_ERROR --> LOG_OTHER[记录其他错误]
    LOG_OTHER --> RETURN_FALSE4[返回False]
    
    TRYCALL -->|网络异常| NETWORK_ERROR[网络连接错误]
    TRYCALL -->|超时| TIMEOUT_ERROR[请求超时]
    TRYCALL -->|JSON解析错误| JSON_ERROR[响应格式错误]
    
    NETWORK_ERROR --> LOG_NETWORK[记录网络错误]
    LOG_NETWORK --> SUGGEST_NETWORK[建议检查网络连接]
    SUGGEST_NETWORK --> RETURN_FALSE5[返回False]
    
    TIMEOUT_ERROR --> LOG_TIMEOUT[记录超时错误]
    LOG_TIMEOUT --> SUGGEST_TIMEOUT[建议增加超时时间]
    SUGGEST_TIMEOUT --> RETURN_FALSE6[返回False]
    
    JSON_ERROR --> LOG_JSON[记录JSON错误]
    LOG_JSON --> SUGGEST_JSON[建议检查API版本]
    SUGGEST_JSON --> RETURN_FALSE7[返回False]
    
    RETURN_TRUE --> END1([结束])
    RETURN_FALSE1 --> END2([结束])
    RETURN_FALSE2 --> END3([结束])
    RETURN_FALSE3 --> END4([结束])
    RETURN_FALSE4 --> END5([结束])
    RETURN_FALSE5 --> END6([结束])
    RETURN_FALSE6 --> END7([结束])
    RETURN_FALSE7 --> END8([结束])
```

## 6. 数据流向图

```mermaid
graph LR
    subgraph "配置数据 Configuration Data"
        CONFIG_FILE[配置文件]
        TEST_PARAMS[测试参数]
        DEVICE_KEYS[设备键列表]
    end
    
    subgraph "设备数据 Device Data"
        HA_DEVICE_DATA[ha_device_data]
        HA_SERVICE_DATA[ha_service_data]
        DEVICE_MAPPING[device_type_mapping]
    end
    
    subgraph "运行时数据 Runtime Data"
        FILTERED_DEVICES[过滤后的设备]
        CURRENT_DEVICE[当前设备]
        DEVICE_TYPE[设备类型]
        ENTITY_ID[实体ID]
    end
    
    subgraph "API数据 API Data"
        REQUEST_PAYLOAD[请求载荷]
        RESPONSE_DATA[响应数据]
        ERROR_INFO[错误信息]
    end
    
    subgraph "日志数据 Log Data"
        SUCCESS_LOG[成功日志]
        ERROR_LOG[错误日志]
        DEBUG_LOG[调试日志]
    end
    
    CONFIG_FILE --> TEST_PARAMS
    TEST_PARAMS --> DEVICE_KEYS
    
    HA_DEVICE_DATA --> FILTERED_DEVICES
    DEVICE_KEYS --> FILTERED_DEVICES
    
    FILTERED_DEVICES --> CURRENT_DEVICE
    CURRENT_DEVICE --> DEVICE_TYPE
    DEVICE_MAPPING --> DEVICE_TYPE
    CURRENT_DEVICE --> ENTITY_ID
    
    DEVICE_TYPE --> REQUEST_PAYLOAD
    ENTITY_ID --> REQUEST_PAYLOAD
    HA_SERVICE_DATA --> REQUEST_PAYLOAD
    
    REQUEST_PAYLOAD --> RESPONSE_DATA
    REQUEST_PAYLOAD --> ERROR_INFO
    
    RESPONSE_DATA --> SUCCESS_LOG
    ERROR_INFO --> ERROR_LOG
    CURRENT_DEVICE --> DEBUG_LOG
    
    SUCCESS_LOG --> CONSOLE_OUTPUT[控制台输出]
    ERROR_LOG --> CONSOLE_OUTPUT
    DEBUG_LOG --> CONSOLE_OUTPUT
```

## 7. 系统状态图

```mermaid
stateDiagram-v2
    [*] --> 初始化
    
    初始化 --> 配置加载
    配置加载 --> API连接检查
    
    API连接检查 --> API连接成功 : 连接成功
    API连接检查 --> API连接失败 : 连接失败
    
    API连接失败 --> 错误处理
    错误处理 --> [*]
    
    API连接成功 --> 设备列表加载
    设备列表加载 --> 设备过滤
    
    设备过滤 --> 设备演示循环 : 有设备需要测试
    设备过滤 --> 演示完成 : 无设备需要测试
    
    设备演示循环 --> 设备类型识别
    设备类型识别 --> 设备控制执行
    
    设备控制执行 --> 控制成功 : API调用成功
    设备控制执行 --> 控制失败 : API调用失败
    
    控制成功 --> 等待间隔
    控制失败 --> 错误记录
    错误记录 --> 等待间隔
    
    等待间隔 --> 下一设备检查
    
    下一设备检查 --> 设备演示循环 : 还有设备
    下一设备检查 --> 演示完成 : 无更多设备
    
    演示完成 --> [*]
    
    note right of API连接检查
        检查Home Assistant
        API的可用性和认证
    end note
    
    note right of 设备控制执行
        根据设备类型调用
        相应的控制方法
    end note
    
    note right of 等待间隔
        等待TEST_INTERVAL
        秒后继续下一个操作
    end note
```

## 8. 部署架构图

```mermaid
graph TB
    subgraph "开发环境 Development Environment"
        DEV_MACHINE[开发机器]
        IDE[集成开发环境]
        GIT[Git仓库]
    end
    
    subgraph "测试环境 Test Environment"
        TEST_HA[测试Home Assistant]
        TEST_DEVICES[测试设备]
        PYTEST[单元测试]
    end
    
    subgraph "生产环境 Production Environment"
        PROD_HA[生产Home Assistant]
        REAL_DEVICES[真实设备]
        MONITORING[监控系统]
    end
    
    subgraph "网络层 Network Layer"
        WIFI[WiFi网络]
        ZIGBEE[Zigbee网络]
        ZWAVE[Z-Wave网络]
    end
    
    DEV_MACHINE --> IDE
    IDE --> GIT
    GIT --> TEST_HA
    
    TEST_HA --> TEST_DEVICES
    PYTEST --> TEST_HA
    
    GIT --> PROD_HA
    PROD_HA --> REAL_DEVICES
    PROD_HA --> MONITORING
    
    TEST_DEVICES --> WIFI
    REAL_DEVICES --> WIFI
    REAL_DEVICES --> ZIGBEE
    REAL_DEVICES --> ZWAVE
    
    WIFI --> TEST_HA
    WIFI --> PROD_HA
    ZIGBEE --> PROD_HA
    ZWAVE --> PROD_HA
```

---

**说明：**
- 所有图表使用Mermaid语法，可以在支持Mermaid的Markdown查看器中渲染
- 图表中包含了类名和方法名，便于快速定位代码
- 时序图详细展示了API调用的完整流程
- 错误处理流程图涵盖了各种异常情况的处理方式
- 状态图展示了系统的完整生命周期