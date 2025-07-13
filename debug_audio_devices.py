#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频设备调试脚本
用于检测当前系统的音频设备状态
"""

import sounddevice as sd
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_audio_devices():
    """
    调试音频设备状态
    """
    print("=== 音频设备调试信息 ===")
    print()
    
    try:
        # 获取所有设备
        devices = sd.query_devices()
        print(f"总共找到 {len(devices)} 个音频设备:")
        print()
        
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(devices):
            print(f"设备 {i}: {device['name']}")
            print(f"  - 输入通道: {device['max_input_channels']}")
            print(f"  - 输出通道: {device['max_output_channels']}")
            print(f"  - 默认采样率: {device['default_samplerate']}")
            print(f"  - 主机API: {device['hostapi']}")
            print()
            
            if device['max_input_channels'] > 0:
                input_devices.append((i, device['name']))
            if device['max_output_channels'] > 0:
                output_devices.append((i, device['name']))
        
        print(f"可用输入设备 ({len(input_devices)} 个):")
        for idx, name in input_devices:
            print(f"  - 设备 {idx}: {name}")
        print()
        
        print(f"可用输出设备 ({len(output_devices)} 个):")
        for idx, name in output_devices:
            print(f"  - 设备 {idx}: {name}")
        print()
        
        # 检查默认设备
        try:
            default_input = sd.default.device[0] if sd.default.device else None
            default_output = sd.default.device[1] if sd.default.device else None
            print(f"当前默认输入设备: {default_input}")
            print(f"当前默认输出设备: {default_output}")
        except Exception as e:
            print(f"获取默认设备失败: {e}")
        
        print()
        print("=== 设备选择逻辑测试 ===")
        
        # 模拟audio_codec.py中的设备选择逻辑
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
            print("✅ 音频设备选择成功")
        
    except Exception as e:
        print(f"❌ 音频设备检测失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_audio_devices()