#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频扬声器验证测试模块
Audio Speaker Verification Test Module

本测试模块提供了完整的音频扬声器功能验证测试套件，包括：
1. 音频设备检测和验证
2. 音频信号生成测试（正弦波、白噪声、频率扫描、多音调）
3. 音频文件操作测试（保存、加载、清理）
4. 音频播放功能测试
5. 交互式扬声器验证测试

使用方法：
1. 直接运行测试：python test_audio_speaker_verification.py
2. 运行特定测试：python -m unittest test_audio_speaker_verification.TestAudioSpeakerVerification.test_sine_wave_generation
3. 详细输出：python test_audio_speaker_verification.py -v
4. 生成测试报告：python test_audio_speaker_verification.py --report

测试配置：
- 所有测试参数在文件顶部的配置区域定义
- 支持通过环境变量覆盖默认配置
- 测试文件自动在tests目录下创建和清理

依赖要求：
- numpy: 音频数据处理
- sounddevice: 音频设备操作
- wave: WAV文件处理
- unittest: 测试框架

注意事项：
- 测试需要系统有可用的音频输出设备
- 交互式测试需要用户手动确认音频播放效果
- 测试过程中会产生临时音频文件，测试结束后自动清理
"""

import os
import sys
import unittest
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import wave
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("错误：sounddevice库未安装，请运行: pip install sounddevice")
    sys.exit(1)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试配置参数 - 可通过环境变量覆盖
TEST_CONFIG = {
    'SAMPLE_RATE': int(os.getenv('TEST_SAMPLE_RATE', '44100')),
    'CHANNELS': int(os.getenv('TEST_CHANNELS', '1')),
    'DURATION': float(os.getenv('TEST_DURATION', '2.0')),
    'AMPLITUDE': float(os.getenv('TEST_AMPLITUDE', '0.3')),
    'TEST_FREQUENCIES': [440.0, 880.0, 1320.0],  # A4, A5, E6
    'SWEEP_START_FREQ': 200.0,
    'SWEEP_END_FREQ': 2000.0,
    'TEST_AUDIO_DIR': Path(__file__).parent / 'audio_test_files',
    'PLAY_BUFFER_SIZE': 1024,
    'INTERACTIVE_TIMEOUT': 30.0,  # 交互式测试超时时间（秒）
    'DEVICE_DETECTION_RETRY': 3,  # 设备检测重试次数
    'PLAYBACK_WAIT_TIME': 0.5,   # 播放等待时间（秒）
}


class AudioGenerator:
    """音频信号生成器"""
    
    def __init__(self, sample_rate: int = TEST_CONFIG['SAMPLE_RATE']):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(f"{__name__}.AudioGenerator")
        self.logger.info(f"初始化音频生成器，采样率: {sample_rate}Hz")
    
    def generate_sine_wave(self, frequency: float, duration: float, 
                          amplitude: float = TEST_CONFIG['AMPLITUDE']) -> np.ndarray:
        """生成正弦波信号"""
        self.logger.debug(f"生成正弦波: 频率={frequency}Hz, 时长={duration}s, 幅度={amplitude}")
        
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        self.logger.info(f"成功生成正弦波信号，样本数: {len(wave_data)}")
        return wave_data.astype(np.float32)
    
    def generate_white_noise(self, duration: float, 
                           amplitude: float = TEST_CONFIG['AMPLITUDE']) -> np.ndarray:
        """生成白噪声信号"""
        self.logger.debug(f"生成白噪声: 时长={duration}s, 幅度={amplitude}")
        
        samples = int(self.sample_rate * duration)
        noise_data = amplitude * np.random.normal(0, 1, samples)
        
        self.logger.info(f"成功生成白噪声信号，样本数: {len(noise_data)}")
        return noise_data.astype(np.float32)
    
    def generate_frequency_sweep(self, start_freq: float, end_freq: float, 
                               duration: float, 
                               amplitude: float = TEST_CONFIG['AMPLITUDE']) -> np.ndarray:
        """生成频率扫描信号（线性扫频）"""
        self.logger.debug(f"生成频率扫描: {start_freq}Hz -> {end_freq}Hz, 时长={duration}s")
        
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # 线性频率扫描
        freq_sweep = np.linspace(start_freq, end_freq, samples)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate
        sweep_data = amplitude * np.sin(phase)
        
        self.logger.info(f"成功生成频率扫描信号，样本数: {len(sweep_data)}")
        return sweep_data.astype(np.float32)
    
    def generate_multi_tone(self, frequencies: List[float], duration: float,
                          amplitude: float = TEST_CONFIG['AMPLITUDE']) -> np.ndarray:
        """生成多音调混合信号"""
        self.logger.debug(f"生成多音调信号: 频率={frequencies}Hz, 时长={duration}s")
        
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        
        # 混合多个频率
        mixed_signal = np.zeros(samples)
        for freq in frequencies:
            mixed_signal += np.sin(2 * np.pi * freq * t)
        
        # 归一化幅度
        mixed_signal = amplitude * mixed_signal / len(frequencies)
        
        self.logger.info(f"成功生成多音调信号，频率数: {len(frequencies)}, 样本数: {len(mixed_signal)}")
        return mixed_signal.astype(np.float32)


class AudioFileManager:
    """音频文件管理器"""
    
    def __init__(self, base_dir: Path = TEST_CONFIG['TEST_AUDIO_DIR']):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(f"{__name__}.AudioFileManager")
        
        # 确保目录存在
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"初始化音频文件管理器，基础目录: {self.base_dir}")
    
    def save_audio_to_wav(self, audio_data: np.ndarray, filename: str, 
                         sample_rate: int = TEST_CONFIG['SAMPLE_RATE']) -> Path:
        """保存音频数据到WAV文件"""
        file_path = self.base_dir / filename
        self.logger.debug(f"保存音频到文件: {file_path}")
        
        try:
            # 确保音频数据在有效范围内
            audio_data = np.clip(audio_data, -1.0, 1.0)
            
            # 转换为16位整数
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(str(file_path), 'wb') as wav_file:
                wav_file.setnchannels(TEST_CONFIG['CHANNELS'])
                wav_file.setsampwidth(2)  # 16位 = 2字节
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            self.logger.info(f"成功保存音频文件: {file_path}, 大小: {file_path.stat().st_size} bytes")
            return file_path
            
        except Exception as e:
            self.logger.error(f"保存音频文件失败: {e}")
            raise
    
    def load_audio_from_wav(self, file_path: Path) -> Tuple[np.ndarray, int]:
        """从WAV文件加载音频数据"""
        self.logger.debug(f"加载音频文件: {file_path}")
        
        try:
            with wave.open(str(file_path), 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                
                # 转换为numpy数组
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # 转换为浮点数并归一化
                audio_data = audio_data.astype(np.float32) / 32767.0
                
                # 如果是立体声，转换为单声道
                if channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)
            
            self.logger.info(f"成功加载音频文件: {file_path}, 样本数: {len(audio_data)}, 采样率: {sample_rate}Hz")
            return audio_data, sample_rate
            
        except Exception as e:
            self.logger.error(f"加载音频文件失败: {e}")
            raise
    
    def cleanup_test_files(self) -> None:
        """清理测试文件"""
        self.logger.info(f"清理测试文件目录: {self.base_dir}")
        
        try:
            if self.base_dir.exists():
                for file_path in self.base_dir.glob('*.wav'):
                    file_path.unlink()
                    self.logger.debug(f"删除文件: {file_path}")
                
                # 如果目录为空，删除目录
                if not any(self.base_dir.iterdir()):
                    self.base_dir.rmdir()
                    self.logger.info(f"删除空目录: {self.base_dir}")
            
        except Exception as e:
            self.logger.warning(f"清理测试文件时出现警告: {e}")


class AudioPlayer:
    """音频播放器"""
    
    def __init__(self, device_id: Optional[int] = None):
        self.device_id = device_id
        self.logger = logging.getLogger(f"{__name__}.AudioPlayer")
        self.logger.info(f"初始化音频播放器，设备ID: {device_id}")
    
    def get_available_output_devices(self) -> List[Dict[str, Any]]:
        """获取可用的音频输出设备"""
        self.logger.debug("检测可用的音频输出设备")
        
        try:
            devices = sd.query_devices()
            output_devices = []
            
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    device_info = {
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_output_channels'],
                        'sample_rate': device['default_samplerate'],
                        'hostapi': device['hostapi']
                    }
                    output_devices.append(device_info)
                    self.logger.debug(f"发现输出设备: {device_info}")
            
            self.logger.info(f"检测到 {len(output_devices)} 个音频输出设备")
            return output_devices
            
        except Exception as e:
            self.logger.error(f"检测音频设备失败: {e}")
            return []
    
    def play_audio_data(self, audio_data: np.ndarray, 
                       sample_rate: int = TEST_CONFIG['SAMPLE_RATE'],
                       blocking: bool = True) -> bool:
        """播放音频数据"""
        self.logger.debug(f"播放音频数据，样本数: {len(audio_data)}, 采样率: {sample_rate}Hz")
        
        try:
            # 确保音频数据格式正确
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 确保音频数据在有效范围内
            audio_data = np.clip(audio_data, -1.0, 1.0)
            
            # 播放音频
            sd.play(audio_data, samplerate=sample_rate, device=self.device_id, blocking=blocking)
            
            if blocking:
                self.logger.info("音频播放完成")
            else:
                self.logger.info("音频播放已启动（非阻塞模式）")
            
            return True
            
        except Exception as e:
            self.logger.error(f"播放音频失败: {e}")
            return False
    
    def play_audio_file(self, file_path: Path, blocking: bool = True) -> bool:
        """播放音频文件"""
        self.logger.debug(f"播放音频文件: {file_path}")
        
        try:
            file_manager = AudioFileManager()
            audio_data, sample_rate = file_manager.load_audio_from_wav(file_path)
            return self.play_audio_data(audio_data, sample_rate, blocking)
            
        except Exception as e:
            self.logger.error(f"播放音频文件失败: {e}")
            return False
    
    def stop_playback(self) -> None:
        """停止音频播放"""
        try:
            sd.stop()
            self.logger.info("音频播放已停止")
        except Exception as e:
            self.logger.warning(f"停止音频播放时出现警告: {e}")


class TestAudioSpeakerVerification(unittest.TestCase):
    """音频扬声器验证测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_audio_speaker.log')
            ]
        )
        
        cls.logger = logging.getLogger(f"{__name__}.TestAudioSpeakerVerification")
        cls.logger.info("开始音频扬声器验证测试")
        
        # 初始化组件
        cls.generator = AudioGenerator()
        cls.file_manager = AudioFileManager()
        cls.player = AudioPlayer()
        
        # 测试数据存储
        cls.test_files = []
        cls.test_results = {}
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.logger.info("清理测试环境")
        
        # 停止任何正在播放的音频
        cls.player.stop_playback()
        
        # 清理测试文件
        cls.file_manager.cleanup_test_files()
        
        # 输出测试结果摘要
        cls.logger.info("测试结果摘要:")
        for test_name, result in cls.test_results.items():
            cls.logger.info(f"  {test_name}: {'通过' if result else '失败'}")
    
    def test_audio_device_detection(self):
        """测试音频设备检测"""
        self.logger.info("测试音频设备检测")
        
        devices = self.player.get_available_output_devices()
        
        # 验证至少有一个输出设备
        self.assertGreater(len(devices), 0, "未检测到音频输出设备")
        
        # 验证设备信息完整性
        for device in devices:
            self.assertIn('id', device)
            self.assertIn('name', device)
            self.assertIn('channels', device)
            self.assertIn('sample_rate', device)
            self.assertGreater(device['channels'], 0)
            self.assertGreater(device['sample_rate'], 0)
        
        self.test_results['device_detection'] = True
        self.logger.info(f"设备检测测试通过，发现 {len(devices)} 个输出设备")
    
    def test_sine_wave_generation(self):
        """测试正弦波生成"""
        self.logger.info("测试正弦波生成")
        
        frequency = 440.0  # A4音符
        duration = 1.0
        
        audio_data = self.generator.generate_sine_wave(frequency, duration)
        
        # 验证音频数据
        expected_samples = int(TEST_CONFIG['SAMPLE_RATE'] * duration)
        self.assertEqual(len(audio_data), expected_samples)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertTrue(np.all(np.abs(audio_data) <= 1.0))
        
        # 保存测试文件
        file_path = self.file_manager.save_audio_to_wav(audio_data, 'test_sine_wave.wav')
        self.test_files.append(file_path)
        
        self.test_results['sine_wave_generation'] = True
        self.logger.info("正弦波生成测试通过")
    
    def test_white_noise_generation(self):
        """测试白噪声生成"""
        self.logger.info("测试白噪声生成")
        
        duration = 1.0
        audio_data = self.generator.generate_white_noise(duration)
        
        # 验证音频数据
        expected_samples = int(TEST_CONFIG['SAMPLE_RATE'] * duration)
        self.assertEqual(len(audio_data), expected_samples)
        self.assertEqual(audio_data.dtype, np.float32)
        
        # 验证噪声特性（标准差应该接近幅度值）
        std_dev = np.std(audio_data)
        self.assertGreater(std_dev, TEST_CONFIG['AMPLITUDE'] * 0.8)
        self.assertLess(std_dev, TEST_CONFIG['AMPLITUDE'] * 1.2)
        
        # 保存测试文件
        file_path = self.file_manager.save_audio_to_wav(audio_data, 'test_white_noise.wav')
        self.test_files.append(file_path)
        
        self.test_results['white_noise_generation'] = True
        self.logger.info("白噪声生成测试通过")
    
    def test_frequency_sweep_generation(self):
        """测试频率扫描生成"""
        self.logger.info("测试频率扫描生成")
        
        start_freq = TEST_CONFIG['SWEEP_START_FREQ']
        end_freq = TEST_CONFIG['SWEEP_END_FREQ']
        duration = 2.0
        
        audio_data = self.generator.generate_frequency_sweep(start_freq, end_freq, duration)
        
        # 验证音频数据
        expected_samples = int(TEST_CONFIG['SAMPLE_RATE'] * duration)
        self.assertEqual(len(audio_data), expected_samples)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertTrue(np.all(np.abs(audio_data) <= 1.0))
        
        # 保存测试文件
        file_path = self.file_manager.save_audio_to_wav(audio_data, 'test_frequency_sweep.wav')
        self.test_files.append(file_path)
        
        self.test_results['frequency_sweep_generation'] = True
        self.logger.info("频率扫描生成测试通过")
    
    def test_multi_tone_generation(self):
        """测试多音调生成"""
        self.logger.info("测试多音调生成")
        
        frequencies = TEST_CONFIG['TEST_FREQUENCIES']
        duration = 1.5
        
        audio_data = self.generator.generate_multi_tone(frequencies, duration)
        
        # 验证音频数据
        expected_samples = int(TEST_CONFIG['SAMPLE_RATE'] * duration)
        self.assertEqual(len(audio_data), expected_samples)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertTrue(np.all(np.abs(audio_data) <= 1.0))
        
        # 保存测试文件
        file_path = self.file_manager.save_audio_to_wav(audio_data, 'test_multi_tone.wav')
        self.test_files.append(file_path)
        
        self.test_results['multi_tone_generation'] = True
        self.logger.info("多音调生成测试通过")
    
    def test_audio_file_operations(self):
        """测试音频文件操作"""
        self.logger.info("测试音频文件操作")
        
        # 生成测试音频
        original_data = self.generator.generate_sine_wave(880.0, 1.0)
        
        # 保存文件
        file_path = self.file_manager.save_audio_to_wav(original_data, 'test_file_ops.wav')
        self.assertTrue(file_path.exists())
        
        # 加载文件
        loaded_data, sample_rate = self.file_manager.load_audio_from_wav(file_path)
        
        # 验证数据一致性
        self.assertEqual(sample_rate, TEST_CONFIG['SAMPLE_RATE'])
        self.assertEqual(len(loaded_data), len(original_data))
        
        # 验证数据相似性（考虑量化误差）
        correlation = np.corrcoef(original_data, loaded_data)[0, 1]
        self.assertGreater(correlation, 0.99)
        
        self.test_results['file_operations'] = True
        self.logger.info("音频文件操作测试通过")
    
    def test_audio_playback_basic(self):
        """测试基础音频播放功能"""
        self.logger.info("测试基础音频播放功能")
        
        # 生成短音频用于测试
        test_audio = self.generator.generate_sine_wave(440.0, 0.5)  # 0.5秒测试音频
        
        # 测试播放功能（非阻塞模式，避免测试卡住）
        success = self.player.play_audio_data(test_audio, blocking=False)
        self.assertTrue(success, "音频播放启动失败")
        
        # 等待一小段时间
        time.sleep(TEST_CONFIG['PLAYBACK_WAIT_TIME'])
        
        # 停止播放
        self.player.stop_playback()
        
        self.test_results['basic_playback'] = True
        self.logger.info("基础音频播放测试通过")
    
    def test_interactive_speaker_verification(self):
        """交互式扬声器验证测试（可选）"""
        # 检查是否在交互环境中
        if not sys.stdin.isatty():
            self.skipTest("非交互环境，跳过交互式测试")
        
        self.logger.info("开始交互式扬声器验证测试")
        
        try:
            # 播放测试音频
            test_audio = self.generator.generate_sine_wave(440.0, 2.0)
            
            print("\n=== 交互式扬声器验证 ===")
            print("即将播放测试音频（440Hz正弦波，2秒）...")
            print("请确保扬声器音量适中")
            
            input("按回车键开始播放...")
            
            success = self.player.play_audio_data(test_audio, blocking=True)
            self.assertTrue(success, "测试音频播放失败")
            
            # 用户确认
            response = input("\n您是否听到了测试音频？(y/n): ").strip().lower()
            
            if response in ['y', 'yes', '是', 'Y']:
                self.test_results['interactive_verification'] = True
                self.logger.info("交互式扬声器验证通过")
            else:
                self.test_results['interactive_verification'] = False
                self.logger.warning("用户报告未听到音频")
                self.fail("用户确认未听到测试音频")
                
        except KeyboardInterrupt:
            self.skipTest("用户中断了交互式测试")
        except Exception as e:
            self.logger.error(f"交互式测试失败: {e}")
            self.fail(f"交互式测试出现错误: {e}")


def generate_test_audio_files() -> List[Path]:
    """生成所有测试音频文件"""
    logger = logging.getLogger(f"{__name__}.generate_test_audio_files")
    logger.info("生成测试音频文件")
    
    generator = AudioGenerator()
    file_manager = AudioFileManager()
    generated_files = []
    
    try:
        # 1. 正弦波测试音频
        sine_wave = generator.generate_sine_wave(440.0, TEST_CONFIG['DURATION'])
        file_path = file_manager.save_audio_to_wav(sine_wave, 'test_sine_440hz.wav')
        generated_files.append(file_path)
        
        # 2. 白噪声测试音频
        white_noise = generator.generate_white_noise(TEST_CONFIG['DURATION'])
        file_path = file_manager.save_audio_to_wav(white_noise, 'test_white_noise.wav')
        generated_files.append(file_path)
        
        # 3. 频率扫描测试音频
        freq_sweep = generator.generate_frequency_sweep(
            TEST_CONFIG['SWEEP_START_FREQ'], 
            TEST_CONFIG['SWEEP_END_FREQ'], 
            TEST_CONFIG['DURATION']
        )
        file_path = file_manager.save_audio_to_wav(freq_sweep, 'test_frequency_sweep.wav')
        generated_files.append(file_path)
        
        # 4. 多音调测试音频
        multi_tone = generator.generate_multi_tone(
            TEST_CONFIG['TEST_FREQUENCIES'], 
            TEST_CONFIG['DURATION']
        )
        file_path = file_manager.save_audio_to_wav(multi_tone, 'test_multi_tone.wav')
        generated_files.append(file_path)
        
        logger.info(f"成功生成 {len(generated_files)} 个测试音频文件")
        return generated_files
        
    except Exception as e:
        logger.error(f"生成测试音频文件失败: {e}")
        raise


def play_test_audio_files(device_id: Optional[int] = None) -> bool:
    """播放所有测试音频文件"""
    logger = logging.getLogger(f"{__name__}.play_test_audio_files")
    logger.info("播放测试音频文件")
    
    player = AudioPlayer(device_id)
    file_manager = AudioFileManager()
    
    try:
        # 检查测试文件是否存在
        test_files = list(TEST_CONFIG['TEST_AUDIO_DIR'].glob('*.wav'))
        if not test_files:
            logger.warning("未找到测试音频文件，先生成文件")
            test_files = generate_test_audio_files()
        
        logger.info(f"找到 {len(test_files)} 个测试音频文件")
        
        for i, file_path in enumerate(test_files, 1):
            logger.info(f"播放文件 {i}/{len(test_files)}: {file_path.name}")
            
            success = player.play_audio_file(file_path, blocking=True)
            if not success:
                logger.error(f"播放文件失败: {file_path}")
                return False
            
            # 文件间短暂停顿
            time.sleep(0.5)
        
        logger.info("所有测试音频文件播放完成")
        return True
        
    except Exception as e:
        logger.error(f"播放测试音频文件失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='音频扬声器验证测试程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python test_audio_speaker_verification.py                    # 运行所有测试
  python test_audio_speaker_verification.py --generate-only   # 仅生成音频文件
  python test_audio_speaker_verification.py --play-only       # 仅播放音频文件
  python test_audio_speaker_verification.py --list-devices    # 列出音频设备
  python test_audio_speaker_verification.py --cleanup         # 清理测试文件
  python test_audio_speaker_verification.py -v               # 详细输出
        """
    )
    
    parser.add_argument('--generate-only', action='store_true',
                       help='仅生成测试音频文件，不运行测试')
    parser.add_argument('--play-only', action='store_true',
                       help='仅播放测试音频文件，不运行测试')
    parser.add_argument('--list-devices', action='store_true',
                       help='列出可用的音频设备')
    parser.add_argument('--cleanup', action='store_true',
                       help='清理测试文件')
    parser.add_argument('--device-id', type=int,
                       help='指定音频输出设备ID')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='详细输出')
    parser.add_argument('--report', action='store_true',
                       help='生成测试报告')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        if args.list_devices:
            # 列出音频设备
            player = AudioPlayer()
            devices = player.get_available_output_devices()
            
            print("\n=== 可用音频输出设备 ===")
            for device in devices:
                print(f"ID: {device['id']}, 名称: {device['name']}, "
                      f"声道: {device['channels']}, 采样率: {device['sample_rate']}Hz")
            
            return 0
        
        elif args.cleanup:
            # 清理测试文件
            file_manager = AudioFileManager()
            file_manager.cleanup_test_files()
            print("测试文件清理完成")
            return 0
        
        elif args.generate_only:
            # 仅生成音频文件
            files = generate_test_audio_files()
            print(f"\n成功生成 {len(files)} 个测试音频文件:")
            for file_path in files:
                print(f"  {file_path}")
            return 0
        
        elif args.play_only:
            # 仅播放音频文件
            success = play_test_audio_files(args.device_id)
            return 0 if success else 1
        
        else:
            # 运行完整测试套件
            print("\n=== 音频扬声器验证测试 ===")
            print(f"测试配置: 采样率={TEST_CONFIG['SAMPLE_RATE']}Hz, "
                  f"声道={TEST_CONFIG['CHANNELS']}, 时长={TEST_CONFIG['DURATION']}s")
            
            # 运行unittest
            test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAudioSpeakerVerification)
            
            if args.report:
                # 生成详细报告
                import io
                test_output = io.StringIO()
                runner = unittest.TextTestRunner(stream=test_output, verbosity=2)
                result = runner.run(test_suite)
                
                # 保存报告
                report_path = Path('test_audio_speaker_report.txt')
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(test_output.getvalue())
                
                print(f"\n测试报告已保存到: {report_path}")
            else:
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