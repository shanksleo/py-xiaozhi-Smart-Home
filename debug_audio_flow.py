#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频流状态调试脚本
用于测试和验证唤醒词检测后的音频流状态管理
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_audio_flow.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_audio_flow():
    """
    测试音频流状态管理
    """
    try:
        logger.info("开始音频流状态测试")
        
        # 导入必要的模块
        from src.audio_codecs.audio_codec import AudioCodec
        from src.audio_processing.wake_word_detect import WakeWordDetector
        from src.protocols.websocket_protocol import WebsocketProtocol
        
        # 初始化音频编解码器
        logger.info("初始化音频编解码器")
        audio_codec = AudioCodec()
        await audio_codec.initialize()
        
        # 初始化唤醒词检测器
        logger.info("初始化唤醒词检测器")
        wake_word_detector = WakeWordDetector()
        
        # 初始化WebSocket协议
        logger.info("初始化WebSocket协议")
        protocol = WebsocketProtocol()
        
        # 模拟唤醒词检测流程
        logger.info("=== 开始模拟唤醒词检测流程 ===")
        
        # 1. 启动唤醒词检测器
        logger.info("步骤1: 启动唤醒词检测器")
        await wake_word_detector.start(audio_codec)
        await asyncio.sleep(1)
        
        # 2. 模拟检测到唤醒词
        logger.info("步骤2: 模拟检测到唤醒词")
        await wake_word_detector.pause()
        
        # 3. 暂停音频输入
        logger.info("步骤3: 暂停音频输入")
        await audio_codec.pause_input()
        
        # 4. 打开WebSocket音频通道
        logger.info("步骤4: 尝试打开WebSocket音频通道")
        # 注意：这里可能会失败，因为没有真实的服务器连接
        try:
            await protocol.open_audio_channel()
        except Exception as e:
            logger.warning(f"WebSocket连接失败（预期）: {e}")
        
        # 5. 清空音频缓冲区
        logger.info("步骤5: 清空音频缓冲区")
        await audio_codec.clear_audio_queue()
        
        # 6. 重新初始化输入流
        logger.info("步骤6: 重新初始化输入流")
        await audio_codec.reinitialize_stream(is_input=True)
        
        # 7. 恢复音频输入
        logger.info("步骤7: 恢复音频输入")
        await audio_codec.resume_input()
        
        # 8. 测试音频读取
        logger.info("步骤8: 测试音频读取")
        for i in range(5):
            audio_data = await audio_codec.read_audio()
            if audio_data:
                logger.info(f"成功读取音频数据 {i+1}/5: {len(audio_data)} bytes")
            else:
                logger.warning(f"音频读取失败 {i+1}/5")
            await asyncio.sleep(0.1)
        
        # 9. 停止检测器
        logger.info("步骤9: 停止唤醒词检测器")
        await wake_word_detector.stop()
        
        logger.info("=== 音频流状态测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
    
    finally:
        # 清理资源
        try:
            if 'audio_codec' in locals():
                await audio_codec.stop_streams()
            if 'protocol' in locals():
                await protocol.close_audio_channel()
        except Exception as e:
            logger.error(f"清理资源时发生错误: {e}")

async def main():
    """
    主函数
    """
    logger.info("启动音频流调试脚本")
    
    try:
        await test_audio_flow()
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    
    logger.info("调试脚本结束")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())