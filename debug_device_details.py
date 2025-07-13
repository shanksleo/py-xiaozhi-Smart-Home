#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频设备详细调试脚本
用于分析设备检测不一致的问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import sounddevice as sd
    import json
    from datetime import datetime
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保已安装 sounddevice")
    sys.exit(1)

def analyze_audio_devices():
    """
    详细分析音频设备状态
    """
    print("=" * 80)
    print(f"音频设备详细分析 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 获取所有设备
        devices = sd.query_devices()
        print(f"\n总设备数量: {len(devices)}")
        
        # 获取默认设备信息
        try:
            default_input = sd.default.device[0] if sd.default.device[0] is not None else "未设置"
            default_output = sd.default.device[1] if sd.default.device[1] is not None else "未设置"
            print(f"当前默认输入设备: {default_input}")
            print(f"当前默认输出设备: {default_output}")
        except Exception as e:
            print(f"获取默认设备失败: {e}")
        
        print("\n" + "-" * 80)
        print("设备详细信息:")
        print("-" * 80)
        
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(devices):
            print(f"\n设备 {i}:")
            print(f"  名称: {device['name']}")
            print(f"  输入通道数: {device['max_input_channels']}")
            print(f"  输出通道数: {device['max_output_channels']}")
            print(f"  默认采样率: {device['default_samplerate']}")
            print(f"  主机API: {device['hostapi']}")
            
            # 检查设备是否可用
            is_input_available = device['max_input_channels'] > 0
            is_output_available = device['max_output_channels'] > 0
            
            print(f"  可作为输入设备: {'是' if is_input_available else '否'}")
            print(f"  可作为输出设备: {'是' if is_output_available else '否'}")
            
            if is_input_available:
                input_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'samplerate': device['default_samplerate']
                })
            
            if is_output_available:
                output_devices.append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_output_channels'],
                    'samplerate': device['default_samplerate']
                })
            
            # 尝试测试设备是否真正可用
            try:
                if is_input_available:
                    # 尝试查询输入设备详细信息
                    input_info = sd.query_devices(i, 'input')
                    print(f"  输入设备查询: 成功")
                if is_output_available:
                    # 尝试查询输出设备详细信息
                    output_info = sd.query_devices(i, 'output')
                    print(f"  输出设备查询: 成功")
            except Exception as e:
                print(f"  设备查询失败: {e}")
        
        print("\n" + "=" * 80)
        print("设备分类汇总:")
        print("=" * 80)
        
        print(f"\n可用输入设备数量: {len(input_devices)}")
        for device in input_devices:
            print(f"  - 设备{device['index']}: {device['name']} ({device['channels']}通道, {device['samplerate']}Hz)")
        
        print(f"\n可用输出设备数量: {len(output_devices)}")
        for device in output_devices:
            print(f"  - 设备{device['index']}: {device['name']} ({device['channels']}通道, {device['samplerate']}Hz)")
        
        # 模拟 audio_codec.py 的设备选择逻辑
        print("\n" + "=" * 80)
        print("模拟 AudioCodec 设备选择逻辑:")
        print("=" * 80)
        
        input_device = None
        output_device = None
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 and input_device is None:
                input_device = i
                print(f"选择输入设备 {i}: {device['name']}")
            if device['max_output_channels'] > 0 and output_device is None:
                output_device = i
                print(f"选择输出设备 {i}: {device['name']}")
        
        if input_device is None:
            print("❌ 未找到可用的音频输入设备（麦克风）")
        if output_device is None:
            print("❌ 未找到可用的音频输出设备（扬声器）")
        
        if input_device is not None and output_device is not None:
            print(f"✅ 设备选择成功: 输入={input_device}, 输出={output_device}")
        
        # 获取主机API信息
        print("\n" + "=" * 80)
        print("主机API信息:")
        print("=" * 80)
        
        try:
            hostapis = sd.query_hostapis()
            for i, api in enumerate(hostapis):
                print(f"API {i}: {api['name']} (设备数: {api['device_count']})")
        except Exception as e:
            print(f"获取主机API信息失败: {e}")
        
        return {
            'total_devices': len(devices),
            'input_devices': len(input_devices),
            'output_devices': len(output_devices),
            'selected_input': input_device,
            'selected_output': output_device,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """
    主函数
    """
    result = analyze_audio_devices()
    
    if result:
        print("\n" + "=" * 80)
        print("分析结果摘要:")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n分析完成。")

if __name__ == "__main__":
    main()