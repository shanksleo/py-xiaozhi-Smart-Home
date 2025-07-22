#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARM版本Ubuntu音频播放兼容性测试模块
ARM Ubuntu Audio Playback Compatibility Test Module

本测试模块专门用于验证在ARM版本Ubuntu系统上的音频播放功能兼容性，包括：
1. 验证wakeup_words.wav音频文件播放功能
2. 验证start_online.wav音频文件播放功能
3. 检测系统音频播放器可用性
4. 验证sounddevice库在ARM Ubuntu上的兼容性

使用方法：
1. 直接运行测试：python test_audio_playback_arm_ubuntu.py
2. 详细输出：python test_audio_playback_arm_ubuntu.py -v

注意事项：
- 本测试专为ARM版本Ubuntu系统设计
- 测试会检查音频文件是否存在
- 测试会验证系统音频播放器的可用性
- 测试过程中会输出详细的诊断信息
"""

import os
import sys
import unittest
import logging
import time
import platform
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from src.utils.logging_config import get_logger
from src.utils.common_utils import play_audio_file_nonblocking


class TestAudioPlaybackARMUbuntu(unittest.TestCase):
    """ARM Ubuntu音频播放兼容性测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_audio_playback_arm_ubuntu.log')
            ]
        )
        
        cls.logger = get_logger(f"{__name__}.TestAudioPlaybackARMUbuntu")
        cls.logger.info("开始ARM Ubuntu音频播放兼容性测试")
        
        # 系统信息检测
        cls._log_system_info()
        
        # 音频文件路径
        cls.project_root = Path(__file__).parent.parent
        cls.assets_audio_dir = cls.project_root / "assets" / "audio"
        cls.wakeup_audio_path = cls.assets_audio_dir / "wakeup_words.wav"
        cls.online_audio_path = cls.assets_audio_dir / "start_online.wav"
        
        # 测试结果存储
        cls.test_results = {}
    
    @classmethod
    def _log_system_info(cls):
        """记录系统信息"""
        logger = get_logger(f"{__name__}.SystemInfo")
        
        logger.info(f"操作系统: {platform.system()}")
        logger.info(f"系统版本: {platform.release()}")
        logger.info(f"处理器架构: {platform.machine()}")
        logger.info(f"Python版本: {platform.python_version()}")
        
        # 检查是否为ARM架构
        machine = platform.machine().lower()
        is_arm = any(arch in machine for arch in ['arm', 'aarch64'])
        logger.info(f"ARM架构检测: {'是' if is_arm else '否'} (架构: {machine})")
        
        # 检查是否为Ubuntu系统
        is_ubuntu = False
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                is_ubuntu = 'ubuntu' in content.lower()
                logger.info(f"Ubuntu系统检测: {'是' if is_ubuntu else '否'}")
                if is_ubuntu:
                    for line in content.split('\n'):
                        if line.startswith('VERSION='):
                            version = line.split('=')[1].strip('"')
                            logger.info(f"Ubuntu版本: {version}")
                            break
        except Exception as e:
            logger.warning(f"无法读取系统版本信息: {e}")
    
    def test_audio_files_existence(self):
        """测试音频文件是否存在"""
        self.logger.info("测试音频文件存在性")
        
        # 检查wakeup_words.wav
        self.assertTrue(self.wakeup_audio_path.exists(), 
                       f"唤醒音频文件不存在: {self.wakeup_audio_path}")
        self.logger.info(f"唤醒音频文件存在: {self.wakeup_audio_path}")
        self.logger.info(f"文件大小: {self.wakeup_audio_path.stat().st_size} bytes")
        
        # 检查start_online.wav
        self.assertTrue(self.online_audio_path.exists(), 
                       f"上线音频文件不存在: {self.online_audio_path}")
        self.logger.info(f"上线音频文件存在: {self.online_audio_path}")
        self.logger.info(f"文件大小: {self.online_audio_path.stat().st_size} bytes")
        
        self.test_results['audio_files_existence'] = True
        self.logger.info("音频文件存在性测试通过")
    
    def test_system_audio_players_availability(self):
        """测试系统音频播放器可用性"""
        self.logger.info("测试系统音频播放器可用性")
        
        available_players = []
        
        # 根据操作系统检查相应的音频播放器
        if platform.system() == "Linux":
            # Linux系统检查
            if shutil.which("aplay"):
                available_players.append("aplay")
                self.logger.info("检测到aplay播放器 (ALSA)")
            
            if shutil.which("paplay"):
                available_players.append("paplay")
                self.logger.info("检测到paplay播放器 (PulseAudio)")
                
        elif platform.system() == "Darwin":  # macOS
            if shutil.which("afplay"):
                available_players.append("afplay")
                self.logger.info("检测到afplay播放器 (macOS)")
                
        elif platform.system() == "Windows":
            # Windows系统有内置的winsound模块
            try:
                import winsound
                available_players.append("winsound")
                self.logger.info("检测到winsound播放器 (Windows)")
            except ImportError:
                pass
        
        # 检查其他跨平台播放器
        other_players = ["mpg123", "sox", "ffplay"]
        for player in other_players:
            if shutil.which(player):
                available_players.append(player)
                self.logger.info(f"检测到{player}播放器")
        
        # 检查sounddevice是否可用作为音频输出方案
        sounddevice_available = False
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            output_devices = [d for d in devices if d['max_output_channels'] > 0]
            if output_devices:
                sounddevice_available = True
                self.logger.info("sounddevice库可用，可作为音频输出方案")
        except (ImportError, Exception):
            pass
        
        self.logger.info(f"可用音频播放器: {available_players}")
        
        # 如果有系统播放器或sounddevice可用，则测试通过
        if len(available_players) > 0 or sounddevice_available:
            self.test_results['system_players'] = available_players
            if sounddevice_available:
                self.test_results['sounddevice_fallback'] = True
            self.logger.info("系统音频播放器可用性测试通过")
        else:
            self.fail("未检测到任何可用的系统音频播放器或sounddevice库")
    
    def test_sounddevice_compatibility(self):
        """测试sounddevice库兼容性"""
        self.logger.info("测试sounddevice库兼容性")
        
        try:
            import sounddevice as sd
            self.logger.info("sounddevice库导入成功")
            
            # 检查音频设备
            devices = sd.query_devices()
            self.logger.info(f"检测到 {len(devices)} 个音频设备")
            
            # 查找输出设备
            output_devices = []
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    output_devices.append({
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_output_channels'],
                        'sample_rate': device['default_samplerate']
                    })
                    self.logger.info(f"输出设备 {i}: {device['name']}, "
                                   f"声道: {device['max_output_channels']}, "
                                   f"采样率: {device['default_samplerate']}Hz")
            
            self.assertGreater(len(output_devices), 0, "未检测到音频输出设备")
            self.test_results['sounddevice_devices'] = output_devices
            self.logger.info("sounddevice库兼容性测试通过")
            
        except ImportError as e:
            self.logger.error(f"sounddevice库导入失败: {e}")
            self.test_results['sounddevice_available'] = False
            self.skipTest("sounddevice库不可用，跳过相关测试")
        except Exception as e:
            self.logger.error(f"sounddevice库测试失败: {e}")
            self.test_results['sounddevice_error'] = str(e)
            raise
    
    def test_wakeup_audio_playback(self):
        """测试唤醒音频播放功能"""
        self.logger.info("测试唤醒音频播放功能")
        
        # 模拟application.py中的唤醒音频播放逻辑
        try:
            # 获取音频文件的绝对路径（模拟application.py中的逻辑）
            wakeup_audio_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "assets", "audio", "wakeup_words.wav"
            )
            
            self.logger.info(f"播放唤醒回复音频: {wakeup_audio_path}")
            
            # 验证路径正确性
            self.assertTrue(os.path.exists(wakeup_audio_path), 
                           f"音频文件路径不存在: {wakeup_audio_path}")
            
            # 调用播放函数
            play_audio_file_nonblocking(wakeup_audio_path)
            
            # 等待播放开始
            time.sleep(1.0)
            
            self.test_results['wakeup_audio_playback'] = True
            self.logger.info("唤醒音频播放功能测试通过")
            
        except Exception as e:
            self.logger.error(f"唤醒音频播放测试失败: {e}")
            self.test_results['wakeup_audio_error'] = str(e)
            raise
    
    def test_online_audio_playback(self):
        """测试上线音频播放功能"""
        self.logger.info("测试上线音频播放功能")
        
        # 模拟application.py中的上线音频播放逻辑
        try:
            # 获取音频文件的绝对路径（模拟application.py中的逻辑）
            online_audio_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "assets", "audio", "start_online.wav"
            )
            
            self.logger.info(f"播放唤醒回复音频: {online_audio_path}")
            
            # 验证路径正确性
            self.assertTrue(os.path.exists(online_audio_path), 
                           f"音频文件路径不存在: {online_audio_path}")
            
            # 调用播放函数
            play_audio_file_nonblocking(online_audio_path)
            
            # 等待播放开始
            time.sleep(1.0)
            
            self.test_results['online_audio_playback'] = True
            self.logger.info("上线音频播放功能测试通过")
            
        except Exception as e:
            self.logger.error(f"上线音频播放测试失败: {e}")
            self.test_results['online_audio_error'] = str(e)
            raise
    
    def test_audio_playback_comprehensive(self):
        """综合音频播放测试"""
        self.logger.info("开始综合音频播放测试")
        
        try:
            # 连续播放两个音频文件，测试系统稳定性
            self.logger.info("连续播放测试开始")
            
            # 播放唤醒音频
            wakeup_path = str(self.wakeup_audio_path)
            self.logger.info(f"播放唤醒音频: {wakeup_path}")
            play_audio_file_nonblocking(wakeup_path)
            time.sleep(2.0)  # 等待播放完成
            
            # 播放上线音频
            online_path = str(self.online_audio_path)
            self.logger.info(f"播放上线音频: {online_path}")
            play_audio_file_nonblocking(online_path)
            time.sleep(2.0)  # 等待播放完成
            
            self.test_results['comprehensive_playback'] = True
            self.logger.info("综合音频播放测试通过")
            
        except Exception as e:
            self.logger.error(f"综合音频播放测试失败: {e}")
            self.test_results['comprehensive_error'] = str(e)
            raise
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.logger.info("ARM Ubuntu音频播放兼容性测试完成")
        
        # 输出测试结果摘要
        cls.logger.info("=== 测试结果摘要 ===")
        for test_name, result in cls.test_results.items():
            if isinstance(result, bool):
                status = "通过" if result else "失败"
                cls.logger.info(f"  {test_name}: {status}")
            elif isinstance(result, list):
                cls.logger.info(f"  {test_name}: {len(result)} 项")
            else:
                cls.logger.info(f"  {test_name}: {result}")
        
        # 输出ARM Ubuntu兼容性建议
        cls._output_compatibility_recommendations()
    
    @classmethod
    def _output_compatibility_recommendations(cls):
        """输出ARM Ubuntu兼容性建议"""
        cls.logger.info("=== ARM Ubuntu兼容性建议 ===")
        
        # 检查系统播放器
        if 'system_players' in cls.test_results:
            players = cls.test_results['system_players']
            if 'aplay' in players:
                cls.logger.info("✓ 推荐使用aplay作为主要音频播放器 (ALSA支持)")
            if 'paplay' in players:
                cls.logger.info("✓ 可使用paplay作为备用音频播放器 (PulseAudio支持)")
        
        # sounddevice兼容性建议
        if 'sounddevice_devices' in cls.test_results:
            devices = cls.test_results['sounddevice_devices']
            cls.logger.info(f"✓ sounddevice库在ARM Ubuntu上工作正常，检测到 {len(devices)} 个输出设备")
        elif 'sounddevice_available' in cls.test_results and not cls.test_results['sounddevice_available']:
            cls.logger.warning("⚠ sounddevice库不可用，建议安装: pip install sounddevice")
        
        # 通用建议
        cls.logger.info("=== 通用建议 ===")
        cls.logger.info("1. 确保系统已安装ALSA或PulseAudio音频系统")
        cls.logger.info("2. 检查音频设备权限，确保用户在audio组中")
        cls.logger.info("3. 如果sounddevice不可用，系统会自动回退到系统播放器")
        cls.logger.info("4. 建议在ARM Ubuntu上优先使用aplay播放器")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ARM Ubuntu音频播放兼容性测试程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python test_audio_playback_arm_ubuntu.py           # 运行所有测试
  python test_audio_playback_arm_ubuntu.py -v       # 详细输出
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = get_logger(__name__)
    
    try:
        print("\n=== ARM Ubuntu音频播放兼容性测试 ===")
        print(f"系统: {platform.system()} {platform.release()}")
        print(f"架构: {platform.machine()}")
        print("\n开始测试...")
        
        # 运行unittest
        test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAudioPlaybackARMUbuntu)
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(test_suite)
        
        return 0 if result.wasSuccessful() else 1
        
    except KeyboardInterrupt:
        logger.info("用户中断了程序")
        return 1
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())