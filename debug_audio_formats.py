#!/usr/bin/env python3
"""
音频设备格式检测脚本
用于诊断 PortAudioError -9994 (Sample format not supported) 问题
"""

import sounddevice as sd
import numpy as np
from typing import List, Dict, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_device_formats(device_id: int, device_info: Dict[str, Any], is_input: bool = True) -> Dict[str, Any]:
    """
    测试指定设备支持的音频格式
    
    Args:
        device_id: 设备ID
        device_info: 设备信息
        is_input: 是否为输入设备
    
    Returns:
        支持的格式信息
    """
    device_name = device_info['name']
    default_samplerate = int(device_info['default_samplerate'])
    max_channels = device_info['max_input_channels'] if is_input else device_info['max_output_channels']
    
    logger.info(f"\n{'='*60}")
    logger.info(f"测试设备: {device_name} (ID: {device_id})")
    logger.info(f"设备类型: {'输入' if is_input else '输出'}")
    logger.info(f"默认采样率: {default_samplerate}Hz")
    logger.info(f"最大通道数: {max_channels}")
    logger.info(f"{'='*60}")
    
    # 测试的数据类型
    dtypes_to_test = [
        ('int8', np.int8),
        ('uint8', np.uint8), 
        ('int16', np.int16),
        ('int24', 'int24'),  # 特殊处理
        ('int32', np.int32),
        ('float32', np.float32),
        ('float64', np.float64)
    ]
    
    # 测试的采样率
    samplerates_to_test = [8000, 16000, 22050, 44100, 48000, 96000]
    
    # 测试的通道数
    channels_to_test = [1, 2] if max_channels >= 2 else [1]
    
    results = {
        'device_id': device_id,
        'device_name': device_name,
        'is_input': is_input,
        'default_samplerate': default_samplerate,
        'max_channels': max_channels,
        'supported_formats': [],
        'failed_formats': []
    }
    
    # 测试每种格式组合
    for dtype_name, dtype in dtypes_to_test:
        for samplerate in samplerates_to_test:
            for channels in channels_to_test:
                try:
                    # 使用check_input_settings或check_output_settings进行快速检查
                    if is_input:
                        sd.check_input_settings(
                            device=device_id,
                            channels=channels,
                            dtype=dtype,
                            samplerate=samplerate
                        )
                    else:
                        sd.check_output_settings(
                            device=device_id,
                            channels=channels,
                            dtype=dtype,
                            samplerate=samplerate
                        )
                    
                    # 如果检查通过，记录为支持的格式
                    format_info = {
                        'dtype': dtype_name,
                        'samplerate': samplerate,
                        'channels': channels,
                        'status': 'supported'
                    }
                    results['supported_formats'].append(format_info)
                    logger.info(f"✅ 支持: {dtype_name}, {samplerate}Hz, {channels}ch")
                    
                except Exception as e:
                    # 记录失败的格式
                    format_info = {
                        'dtype': dtype_name,
                        'samplerate': samplerate,
                        'channels': channels,
                        'status': 'failed',
                        'error': str(e)
                    }
                    results['failed_formats'].append(format_info)
                    logger.debug(f"❌ 不支持: {dtype_name}, {samplerate}Hz, {channels}ch - {e}")
    
    return results

def test_stream_creation(device_id: int, device_info: Dict[str, Any], is_input: bool = True):
    """
    测试实际的流创建（更严格的测试）
    """
    device_name = device_info['name']
    default_samplerate = int(device_info['default_samplerate'])
    
    logger.info(f"\n测试实际流创建: {device_name}")
    
    # 测试常用的格式组合
    test_configs = [
        {'dtype': np.int16, 'samplerate': default_samplerate, 'channels': 1},
        {'dtype': np.float32, 'samplerate': default_samplerate, 'channels': 1},
        {'dtype': np.int16, 'samplerate': 44100, 'channels': 1},
        {'dtype': np.float32, 'samplerate': 44100, 'channels': 1},
    ]
    
    for config in test_configs:
        try:
            if is_input:
                stream = sd.InputStream(
                    device=device_id,
                    channels=config['channels'],
                    samplerate=config['samplerate'],
                    dtype=config['dtype'],
                    blocksize=1024
                )
            else:
                stream = sd.OutputStream(
                    device=device_id,
                    channels=config['channels'],
                    samplerate=config['samplerate'],
                    dtype=config['dtype'],
                    blocksize=1024
                )
            
            # 尝试启动流
            stream.start()
            logger.info(f"✅ 流创建成功: {config}")
            stream.stop()
            stream.close()
            
        except Exception as e:
            logger.error(f"❌ 流创建失败: {config} - {e}")
            if "PaErrorCode -9994" in str(e):
                logger.error(f"🔍 发现-9994错误！配置: {config}")

def main():
    """
    主函数：检测所有音频设备的格式支持情况
    """
    logger.info("开始音频设备格式检测...")
    
    try:
        # 获取所有设备
        devices = sd.query_devices()
        logger.info(f"检测到 {len(devices)} 个音频设备")
        
        # 输出设备列表
        logger.info("\n设备列表:")
        for i, device in enumerate(devices):
            logger.info(f"  {i}: {device['name']} - 输入:{device['max_input_channels']} 输出:{device['max_output_channels']}")
        
        all_results = []
        
        # 测试每个设备
        for i, device in enumerate(devices):
            # 测试输入设备
            if device['max_input_channels'] > 0:
                try:
                    result = test_device_formats(i, device, is_input=True)
                    all_results.append(result)
                    test_stream_creation(i, device, is_input=True)
                except Exception as e:
                    logger.error(f"测试输入设备 {i} 失败: {e}")
            
            # 测试输出设备
            if device['max_output_channels'] > 0:
                try:
                    result = test_device_formats(i, device, is_input=False)
                    all_results.append(result)
                    test_stream_creation(i, device, is_input=False)
                except Exception as e:
                    logger.error(f"测试输出设备 {i} 失败: {e}")
        
        # 输出总结
        logger.info("\n" + "="*80)
        logger.info("检测总结:")
        logger.info("="*80)
        
        for result in all_results:
            device_type = "输入" if result['is_input'] else "输出"
            supported_count = len(result['supported_formats'])
            failed_count = len(result['failed_formats'])
            
            logger.info(f"\n设备: {result['device_name']} ({device_type})")
            logger.info(f"  支持的格式: {supported_count} 个")
            logger.info(f"  不支持的格式: {failed_count} 个")
            
            # 显示一些支持的格式示例
            if supported_count > 0:
                logger.info("  支持的格式示例:")
                for fmt in result['supported_formats'][:5]:  # 只显示前5个
                    logger.info(f"    - {fmt['dtype']}, {fmt['samplerate']}Hz, {fmt['channels']}ch")
                if supported_count > 5:
                    logger.info(f"    ... 还有 {supported_count - 5} 个")
        
        logger.info("\n检测完成！")
        
    except Exception as e:
        logger.error(f"检测过程中发生错误: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")

if __name__ == "__main__":
    main()