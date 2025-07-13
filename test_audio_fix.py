#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频设备修复测试脚本
用于验证音频设备初始化修复是否有效
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logging_config import setup_logging
from src.audio_codecs.audio_codec import AudioCodec

async def test_audio_initialization():
    """
    测试音频设备初始化
    """
    print("=== 音频设备初始化测试 ===")
    print()
    
    try:
        # 初始化日志
        setup_logging()
        
        # 创建音频编解码器实例
        audio_codec = AudioCodec()
        
        print("正在初始化音频设备...")
        await audio_codec.initialize()
        
        print("✅ 音频设备初始化成功！")
        print(f"输入采样率: {audio_codec.device_input_sample_rate}Hz")
        print(f"输出采样率: {audio_codec.device_output_sample_rate}Hz")
        
        # 清理资源
        await audio_codec.close()
        print("✅ 音频资源清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 音频设备初始化失败: {e}")
        return False

def main():
    """
    主函数
    """
    try:
        success = asyncio.run(test_audio_initialization())
        if success:
            print("\n🎉 测试通过！音频设备修复成功。")
            sys.exit(0)
        else:
            print("\n💥 测试失败！请检查音频设备配置。")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()