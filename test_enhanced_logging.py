#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的音频设备日志功能
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 首先设置日志
from src.utils.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

async def test_enhanced_audio_logging():
    """
    测试增强的音频设备日志功能
    """
    print("=" * 80)
    print(f"测试增强的音频设备日志功能 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # 导入AudioCodec
        from src.audio_codecs.audio_codec import AudioCodec
        
        logger.info("🚀 开始测试增强的音频设备日志功能")
        
        # 创建AudioCodec实例
        logger.info("创建AudioCodec实例...")
        audio_codec = AudioCodec()
        
        # 初始化音频设备（这里会输出详细的调试日志）
        logger.info("开始初始化音频设备（将输出详细的调试信息）...")
        await audio_codec.initialize()
        
        logger.info("✅ 音频设备初始化成功！")
        
        # 清理资源
        logger.info("清理音频资源...")
        await audio_codec.close()
        logger.info("✅ 资源清理完成")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成！请检查上面的详细日志输出")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中出现错误: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        print("\n" + "=" * 80)
        print("❌ 测试失败！请查看上面的错误信息")
        print("=" * 80)
        
        return False

def main():
    """
    主函数
    """
    print("增强的音频设备日志测试")
    print("此测试将展示详细的设备检测和初始化过程")
    print("注意：现在日志级别已设置为DEBUG，将显示更多详细信息\n")
    
    # 运行异步测试
    success = asyncio.run(test_enhanced_audio_logging())
    
    if success:
        print("\n🎉 测试成功！增强的日志功能正常工作")
        print("现在您可以运行 main.py 来查看详细的设备检测日志")
    else:
        print("\n💡 即使测试失败，您也应该能看到详细的错误日志")
        print("这些日志将帮助您诊断音频设备问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)