#!/usr/bin/env python3
"""
音频设备诊断脚本（无numpy依赖版本）
用于检查音频设备支持的格式，特别是针对 PortAudioError -9994 错误的诊断
"""

import sounddevice as sd
from typing import List, Dict, Any


def check_device_formats(device_id: int, device_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    检查指定设备支持的音频格式
    
    Args:
        device_id: 设备ID
        device_info: 设备信息
        
    Returns:
        Dict: 包含支持格式的字典
    """
    result = {
        'device_id': device_id,
        'device_name': device_info['name'],
        'supported_input_formats': [],
        'supported_output_formats': [],
        'supported_sample_rates': [],
        'errors': []
    }
    
    # 测试的数据类型
    test_dtypes = ['int16', 'int32', 'float32', 'int8', 'uint8']
    
    # 测试的采样率
    test_sample_rates = [8000, 16000, 22050, 24000, 44100, 48000]
    
    # 测试输入格式（如果设备支持输入）
    if device_info['max_input_channels'] > 0:
        print(f"\n测试输入设备 {device_id}: {device_info['name']}")
        for dtype in test_dtypes:
            try:
                # 尝试创建输入流
                with sd.InputStream(
                    device=device_id,
                    channels=1,
                    dtype=dtype,
                    samplerate=int(device_info['default_samplerate']),
                    blocksize=1024
                ):
                    result['supported_input_formats'].append(dtype)
                    print(f"  ✅ 支持输入格式: {dtype}")
            except Exception as e:
                print(f"  ❌ 不支持输入格式 {dtype}: {e}")
                result['errors'].append(f"Input {dtype}: {str(e)}")
    
    # 测试输出格式（如果设备支持输出）
    if device_info['max_output_channels'] > 0:
        print(f"\n测试输出设备 {device_id}: {device_info['name']}")
        for dtype in test_dtypes:
            try:
                # 尝试创建输出流
                with sd.OutputStream(
                    device=device_id,
                    channels=1,
                    dtype=dtype,
                    samplerate=int(device_info['default_samplerate']),
                    blocksize=1024
                ):
                    result['supported_output_formats'].append(dtype)
                    print(f"  ✅ 支持输出格式: {dtype}")
            except Exception as e:
                print(f"  ❌ 不支持输出格式 {dtype}: {e}")
                result['errors'].append(f"Output {dtype}: {str(e)}")
    
    # 测试采样率（使用支持的格式）
    if result['supported_input_formats'] or result['supported_output_formats']:
        print(f"\n测试采样率支持 - 设备 {device_id}")
        test_dtype = 'float32'  # 使用通常支持的格式
        
        for sample_rate in test_sample_rates:
            try:
                if device_info['max_input_channels'] > 0:
                    with sd.InputStream(
                        device=device_id,
                        channels=1,
                        dtype=test_dtype,
                        samplerate=sample_rate,
                        blocksize=1024
                    ):
                        result['supported_sample_rates'].append(sample_rate)
                        print(f"  ✅ 支持采样率: {sample_rate}Hz")
                elif device_info['max_output_channels'] > 0:
                    with sd.OutputStream(
                        device=device_id,
                        channels=1,
                        dtype=test_dtype,
                        samplerate=sample_rate,
                        blocksize=1024
                    ):
                        result['supported_sample_rates'].append(sample_rate)
                        print(f"  ✅ 支持采样率: {sample_rate}Hz")
            except Exception as e:
                print(f"  ❌ 不支持采样率 {sample_rate}Hz: {e}")
    
    return result


def test_specific_configuration():
    """
    测试项目中使用的具体配置
    """
    print("\n" + "="*60)
    print("测试项目特定配置")
    print("="*60)
    
    try:
        devices = sd.query_devices()
        
        # 查找输入和输出设备
        input_device = None
        output_device = None
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 and input_device is None:
                input_device = i
            if device['max_output_channels'] > 0 and output_device is None:
                output_device = i
        
        if input_device is not None:
            input_info = sd.query_devices(input_device)
            print(f"\n测试输入设备配置: {input_info['name']}")
            print(f"默认采样率: {input_info['default_samplerate']}Hz")
            
            # 测试项目使用的配置
            try:
                frame_duration = 20  # 项目默认值
                device_sample_rate = int(input_info['default_samplerate'])
                frame_size = int(device_sample_rate * (frame_duration / 1000))
                
                print(f"计算的帧大小: {frame_size}")
                
                with sd.InputStream(
                    device=input_device,
                    channels=1,
                    dtype='int16',
                    samplerate=device_sample_rate,
                    blocksize=frame_size,
                    latency='low'
                ):
                    print("✅ 项目输入配置测试成功")
            except Exception as e:
                print(f"❌ 项目输入配置测试失败: {e}")
                print(f"错误类型: {type(e).__name__}")
        
        if output_device is not None:
            output_info = sd.query_devices(output_device)
            print(f"\n测试输出设备配置: {output_info['name']}")
            print(f"默认采样率: {output_info['default_samplerate']}Hz")
            
            # 测试项目使用的配置
            try:
                frame_duration = 20  # 项目默认值
                device_sample_rate = int(output_info['default_samplerate'])
                frame_size = int(device_sample_rate * (frame_duration / 1000))
                
                print(f"计算的帧大小: {frame_size}")
                
                with sd.OutputStream(
                    device=output_device,
                    channels=1,
                    dtype='int16',
                    samplerate=device_sample_rate,
                    blocksize=frame_size,
                    latency='low'
                ):
                    print("✅ 项目输出配置测试成功")
            except Exception as e:
                print(f"❌ 项目输出配置测试失败: {e}")
                print(f"错误类型: {type(e).__name__}")
                
                # 尝试不同的配置
                print("\n尝试替代配置...")
                
                # 尝试 float32 格式
                try:
                    with sd.OutputStream(
                        device=output_device,
                        channels=1,
                        dtype='float32',
                        samplerate=device_sample_rate,
                        blocksize=frame_size,
                        latency='low'
                    ):
                        print("✅ float32 格式测试成功")
                except Exception as e2:
                    print(f"❌ float32 格式也失败: {e2}")
                
                # 尝试不同的延迟设置
                try:
                    with sd.OutputStream(
                        device=output_device,
                        channels=1,
                        dtype='int16',
                        samplerate=device_sample_rate,
                        blocksize=frame_size,
                        latency='high'
                    ):
                        print("✅ 高延迟设置测试成功")
                except Exception as e3:
                    print(f"❌ 高延迟设置也失败: {e3}")
                
                # 尝试默认blocksize
                try:
                    with sd.OutputStream(
                        device=output_device,
                        channels=1,
                        dtype='int16',
                        samplerate=device_sample_rate,
                        latency='low'
                    ):
                        print("✅ 默认blocksize测试成功")
                except Exception as e4:
                    print(f"❌ 默认blocksize也失败: {e4}")
                
                # 尝试更大的blocksize
                try:
                    larger_frame_size = frame_size * 2
                    with sd.OutputStream(
                        device=output_device,
                        channels=1,
                        dtype='int16',
                        samplerate=device_sample_rate,
                        blocksize=larger_frame_size,
                        latency='low'
                    ):
                        print(f"✅ 更大blocksize({larger_frame_size})测试成功")
                except Exception as e5:
                    print(f"❌ 更大blocksize也失败: {e5}")
    
    except Exception as e:
        print(f"配置测试出错: {e}")


def check_host_apis():
    """
    检查主机API信息
    """
    print("\n" + "="*60)
    print("主机API信息")
    print("="*60)
    
    try:
        host_apis = sd.query_hostapis()
        for i, api in enumerate(host_apis):
            print(f"\nAPI {i}: {api['name']}")
            print(f"  默认输入设备: {api['default_input_device']}")
            print(f"  默认输出设备: {api['default_output_device']}")
            print(f"  设备数量: {len(api['devices'])}")
    except Exception as e:
        print(f"查询主机API失败: {e}")


def main():
    """
    主函数
    """
    print("音频设备诊断工具（无numpy版本）")
    print("="*60)
    
    try:
        # 获取所有设备
        devices = sd.query_devices()
        print(f"检测到 {len(devices)} 个音频设备\n")
        
        # 显示所有设备信息
        print("设备列表:")
        for i, device in enumerate(devices):
            print(f"  {i}: {device['name']}")
            print(f"     输入通道: {device['max_input_channels']}, 输出通道: {device['max_output_channels']}")
            print(f"     默认采样率: {device['default_samplerate']}Hz")
            print(f"     主机API: {device['hostapi']}")
        
        # 检查主机API
        check_host_apis()
        
        # 检查每个设备的格式支持
        results = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0 or device['max_output_channels'] > 0:
                result = check_device_formats(i, device)
                results.append(result)
        
        # 测试项目特定配置
        test_specific_configuration()
        
        # 输出总结
        print("\n" + "="*60)
        print("诊断总结")
        print("="*60)
        
        for result in results:
            print(f"\n设备 {result['device_id']}: {result['device_name']}")
            if result['supported_input_formats']:
                print(f"  支持的输入格式: {result['supported_input_formats']}")
            if result['supported_output_formats']:
                print(f"  支持的输出格式: {result['supported_output_formats']}")
            if result['supported_sample_rates']:
                print(f"  支持的采样率: {result['supported_sample_rates']}")
            if result['errors']:
                print(f"  错误: {len(result['errors'])} 个")
                for error in result['errors'][:3]:  # 只显示前3个错误
                    print(f"    - {error}")
    
    except Exception as e:
        print(f"诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()