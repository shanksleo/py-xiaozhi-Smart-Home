#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频扬声器验证测试系统

本测试文件用于验证音频扬声器功能，包括：
1. 音频信号生成（正弦波、白噪声、扫频等）
2. 音频播放测试
3. 音频设备检测和验证
4. 音频质量评估
5. 多种音频格式支持

技术方案对比：
- SoundDevice: 现代化、跨平台、低延迟，项目主要使用
- PyAudio: 传统、稳定但API较老
- Pygame: 游戏导向，功能有限
- Wave + 系统播放器: 简单但依赖系统

使用方法：
1. 基础测试：python -m pytest tests/test_audio_speaker_verification.py -v
2. 完整测试：python tests/test_audio_speaker_verification.py
3. 指定设备测试：python tests/test_audio_speaker_verification.py --device-id 1
4. 生成测试音频：python tests/test_audio_speaker_verification.py --generate-only
5. 播放测试音频：python tests/test_audio_speaker_verification.py --play-only

测试环境要求：
- Python 3.7+
- sounddevice >= 0.4.4
- numpy >= 1.26.4
- pytest（用于单元测试）
- 可用的音频输出设备

注意事项：
- 测试前请确保音量适中，避免损伤听力
- 某些测试需要人工确认音频播放效果
- 在无头环境下会跳过需要用户交互的测试
- 测试音频文件会保存在tests目录下
"""

import unittest
import sys
import os
import argparse
import time
import wave
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import numpy as np
    import sounddevice as sd
except ImportError as e:
    print(f"缺少必要依赖: {e}")
    print("请运行: pip install numpy sounddevice")
    sys.exit(1)

from src.utils.logging_config import setup_logging, get_logger
from src.constants.constants import AudioConfig
from src.audio_codecs.audio_codec import AudioCodec

# 测试配置参数
class TestConfig:
    """测试配置类"""
    
    # 音频生成参数
    SAMPLE_RATE = 44100  # 标准CD质量采样率
    CHANNELS = 1  # 单声道
    DURATION = 2.0  # 测试音频时长（秒）
    AMPLITUDE = 0.3  # 音频幅度（0-1）
    
    # 测试频率
    TEST_FREQUENCIES = [440, 880, 1000, 2000]  # Hz
    SWEEP_START_FREQ = 200  # 扫频起始频率
    SWEEP_END_FREQ = 8000   # 扫频结束频率
    
    # 文件路径
    TEST_AUDIO_DIR = Path(__file__).parent / "audio_test_files"
    
    # 播放参数
    PLAY_BUFFER_SIZE = 1024
    PLAY_TIMEOUT = 10.0  # 播放超时时间


class AudioGenerator:
    """音频信号生成器"""
    
    def __init__(self, sample_rate: int = TestConfig.SAMPLE_RATE):
        self.sample_rate = sample_rate
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)

    def generate_sine_wave(self, frequency: float, duration: float, 
                          amplitude: float = TestConfig.AMPLITUDE) -> np.ndarray:
        """生成正弦波信号
        
        Args:
            frequency: 频率（Hz）
            duration: 时长（秒）
            amplitude: 幅度（0-1）
            
        Returns:
            numpy数组形式的音频数据
        """
        print(f"生成正弦波: {frequency}Hz, {duration}s, 幅度{amplitude}")
        
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 添加淡入淡出效果，避免爆音
        fade_samples = int(0.01 * self.sample_rate)  # 10ms淡入淡出
        if len(wave_data) > 2 * fade_samples:
            # 淡入
            wave_data[:fade_samples] *= np.linspace(0, 1, fade_samples)
            # 淡出
            wave_data[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
        return wave_data.astype(np.float32)
    
    def generate_white_noise(self, duration: float, 
                           amplitude: float = TestConfig.AMPLITUDE * 0.5) -> np.ndarray:
        """生成白噪声信号
        
        Args:
            duration: 时长（秒）
            amplitude: 幅度（0-1）
            
        Returns:
            numpy数组形式的音频数据
        """
        print(f"生成白噪声: {duration}s, 幅度{amplitude}")
        
        samples = int(self.sample_rate * duration)
        noise_data = amplitude * np.random.normal(0, 1, samples)
        
        return noise_data.astype(np.float32)
    
    def generate_frequency_sweep(self, start_freq: float, end_freq: float, 
                               duration: float, amplitude: float = TestConfig.AMPLITUDE) -> np.ndarray:
        """生成扫频信号
        
        Args:
            start_freq: 起始频率（Hz）
            end_freq: 结束频率（Hz）
            duration: 时长（秒）
            amplitude: 幅度（0-1）
            
        Returns:
            numpy数组形式的音频数据
        """
        print(f"生成扫频信号: {start_freq}-{end_freq}Hz, {duration}s")
        
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        # 线性扫频
        instantaneous_freq = start_freq + (end_freq - start_freq) * t / duration
        # 计算相位
        phase = 2 * np.pi * np.cumsum(instantaneous_freq) / self.sample_rate
        sweep_data = amplitude * np.sin(phase)
        
        return sweep_data.astype(np.float32)
    
    def generate_multi_tone(self, frequencies: List[float], duration: float,
                          amplitude: float = TestConfig.AMPLITUDE) -> np.ndarray:
        """生成多音调信号
        
        Args:
            frequencies: 频率列表（Hz）
            duration: 时长（秒）
            amplitude: 幅度（0-1）
            
        Returns:
            numpy数组形式的音频数据
        """
        print(f"生成多音调信号: {frequencies}Hz, {duration}s")
        
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        multi_tone_data = np.zeros_like(t)
        
        # 叠加多个频率
        for freq in frequencies:
            multi_tone_data += np.sin(2 * np.pi * freq * t)
        
        # 归一化幅度
        multi_tone_data = amplitude * multi_tone_data / len(frequencies)
        
        return multi_tone_data.astype(np.float32)


class AudioFileManager:
    """音频文件管理器"""
    
    def __init__(self, base_dir: Path = TestConfig.TEST_AUDIO_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)

    def save_audio_to_wav(self, audio_data: np.ndarray, filename: str, 
                         sample_rate: int = TestConfig.SAMPLE_RATE) -> Path:
        """保存音频数据到WAV文件
        
        Args:
            audio_data: 音频数据
            filename: 文件名
            sample_rate: 采样率
            
        Returns:
            保存的文件路径
        """
        file_path = self.base_dir / f"{filename}.wav"
        
        print(f"保存音频文件: {file_path}")
        
        # 转换为16位整数格式
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        with wave.open(str(file_path), 'wb') as wav_file:
            wav_file.setnchannels(TestConfig.CHANNELS)
            wav_file.setsampwidth(2)  # 16位 = 2字节
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
            
        print(f"音频文件保存成功: {file_path}, 大小: {file_path.stat().st_size} bytes")
        return file_path
    
    def load_audio_from_wav(self, file_path: Path) -> Tuple[np.ndarray, int]:
        """从WAV文件加载音频数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            (音频数据, 采样率)
        """
        print(f"加载音频文件: {file_path}")
        
        with wave.open(str(file_path), 'rb') as wav_file:
            frames = wav_file.readframes(-1)
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            
            # 转换为numpy数组
            audio_data = np.frombuffer(frames, dtype=np.int16)
            if channels > 1:
                audio_data = audio_data.reshape(-1, channels)
                audio_data = audio_data[:, 0]  # 取第一个声道
                
            # 转换为float32格式
            audio_data = audio_data.astype(np.float32) / 32767.0
            
        print(f"音频加载成功: 采样率{sample_rate}Hz, 长度{len(audio_data)}样本")
        return audio_data, sample_rate
    
    def cleanup_test_files(self):
        """清理测试文件"""
        print(f"清理测试文件目录: {self.base_dir}")
        
        for file_path in self.base_dir.glob("*.wav"):
            try:
                file_path.unlink()
                print(f"删除文件: {file_path}")
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")


class AudioPlayer:
    """音频播放器"""
    
    def __init__(self, device_id: Optional[int] = None):
        self.device_id = device_id
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
        
    def get_available_output_devices(self) -> List[Dict[str, Any]]:
        """获取可用的输出设备列表
        
        Returns:
            设备信息列表
        """
        devices = []
        
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_output_channels'] > 0:
                    devices.append({
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_output_channels'],
                        'sample_rate': device['default_samplerate']
                    })
                    
        except Exception as e:
            print(f"获取音频设备失败: {e}")
            
        return devices
    
    def play_audio_data(self, audio_data: np.ndarray, sample_rate: int, 
                       blocking: bool = True) -> bool:
        """播放音频数据
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            blocking: 是否阻塞播放
            
        Returns:
            播放是否成功
        """
        try:
            print(f"开始播放音频: 采样率{sample_rate}Hz, 长度{len(audio_data)}样本")
            
            # 确保音频数据格式正确
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                
            # 播放音频
            sd.play(audio_data, samplerate=sample_rate, device=self.device_id, blocking=blocking)
            
            if blocking:
                print("音频播放完成")
            else:
                print("音频播放已开始（非阻塞模式）")
                
            return True
            
        except Exception as e:
            print(f"音频播放失败: {e}")
            return False
    
    def play_audio_file(self, file_path: Path, blocking: bool = True) -> bool:
        """播放音频文件
        
        Args:
            file_path: 音频文件路径
            blocking: 是否阻塞播放
            
        Returns:
            播放是否成功
        """
        try:
            file_manager = AudioFileManager()
            audio_data, sample_rate = file_manager.load_audio_from_wav(file_path)
            return self.play_audio_data(audio_data, sample_rate, blocking)
            
        except Exception as e:
            print(f"播放音频文件失败 {file_path}: {e}")
            return False
    
    def stop_playback(self):
        """停止播放"""
        try:
            sd.stop()
            print("音频播放已停止")
        except Exception as e:
            print(f"停止播放时出错: {e}")


class TestAudioSpeakerVerification(unittest.TestCase):
    """音频扬声器验证测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        setup_logging()
        cls.logger = get_logger(cls.__name__)
        cls.generator = AudioGenerator()
        cls.file_manager = AudioFileManager()
        cls.player = AudioPlayer()
        
        print("=== 音频扬声器验证测试开始 ===")
        
        # 检查音频设备
        devices = cls.player.get_available_output_devices()
        print(f"检测到 {len(devices)} 个输出设备")
        for device in devices:
            print(f"  设备 {device['id']}: {device['name']} ({device['channels']}声道)")
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        print("=== 音频扬声器验证测试结束 ===")
        
        # 可选：清理测试文件（保留用于手动验证）
        # cls.file_manager.cleanup_test_files()
    
    def test_audio_device_detection(self):
        """测试音频设备检测"""
        print("测试音频设备检测")
        
        devices = self.player.get_available_output_devices()
        self.assertGreater(len(devices), 0, "未检测到可用的音频输出设备")
        
        for device in devices:
            self.assertIn('id', device)
            self.assertIn('name', device)
            self.assertGreater(device['channels'], 0)
            self.assertGreater(device['sample_rate'], 0)
    
    def test_sine_wave_generation(self):
        """测试正弦波生成"""
        print("测试正弦波生成")
        
        for freq in TestConfig.TEST_FREQUENCIES:
            with self.subTest(frequency=freq):
                audio_data = self.generator.generate_sine_wave(freq, 1.0)
                
                self.assertIsInstance(audio_data, np.ndarray)
                self.assertEqual(audio_data.dtype, np.float32)
                self.assertGreater(len(audio_data), 0)
                
                # 检查幅度范围
                self.assertLessEqual(np.max(np.abs(audio_data)), 1.0)
                
                # 保存测试文件
                filename = f"test_sine_{freq}hz"
                file_path = self.file_manager.save_audio_to_wav(audio_data, filename)
                self.assertTrue(file_path.exists())
    
    def test_white_noise_generation(self):
        """测试白噪声生成"""
        print("测试白噪声生成")
        
        audio_data = self.generator.generate_white_noise(1.0)
        
        self.assertIsInstance(audio_data, np.ndarray)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertGreater(len(audio_data), 0)
        
        # 保存测试文件
        filename = "test_white_noise"
        file_path = self.file_manager.save_audio_to_wav(audio_data, filename)
        self.assertTrue(file_path.exists())
    
    def test_frequency_sweep_generation(self):
        """测试扫频信号生成"""
        print("测试扫频信号生成")
        
        audio_data = self.generator.generate_frequency_sweep(
            TestConfig.SWEEP_START_FREQ, 
            TestConfig.SWEEP_END_FREQ, 
            TestConfig.DURATION
        )
        
        self.assertIsInstance(audio_data, np.ndarray)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertGreater(len(audio_data), 0)
        
        # 保存测试文件
        filename = f"test_sweep_{TestConfig.SWEEP_START_FREQ}-{TestConfig.SWEEP_END_FREQ}hz"
        file_path = self.file_manager.save_audio_to_wav(audio_data, filename)
        self.assertTrue(file_path.exists())
    
    def test_multi_tone_generation(self):
        """测试多音调信号生成"""
        print("测试多音调信号生成")
        
        audio_data = self.generator.generate_multi_tone(
            TestConfig.TEST_FREQUENCIES[:2], 
            TestConfig.DURATION
        )
        
        self.assertIsInstance(audio_data, np.ndarray)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertGreater(len(audio_data), 0)
        
        # 保存测试文件
        filename = "test_multi_tone"
        file_path = self.file_manager.save_audio_to_wav(audio_data, filename)
        self.assertTrue(file_path.exists())
    
    def test_audio_file_operations(self):
        """测试音频文件操作"""
        print("测试音频文件操作")
        
        # 生成测试音频
        original_data = self.generator.generate_sine_wave(1000, 0.5)
        
        # 保存文件
        filename = "test_file_operations"
        file_path = self.file_manager.save_audio_to_wav(original_data, filename)
        self.assertTrue(file_path.exists())
        
        # 加载文件
        loaded_data, sample_rate = self.file_manager.load_audio_from_wav(file_path)
        
        self.assertEqual(sample_rate, TestConfig.SAMPLE_RATE)
        self.assertIsInstance(loaded_data, np.ndarray)
        self.assertEqual(loaded_data.dtype, np.float32)
        
        # 验证数据一致性（允许小的精度误差）
        np.testing.assert_allclose(original_data, loaded_data, rtol=1e-3)
    
    def test_audio_playback_basic(self):
        """测试基础音频播放功能"""
        print("测试基础音频播放功能")
        
        # 生成短音频
        audio_data = self.generator.generate_sine_wave(1000, 0.2)  # 200ms
        
        # 测试播放（非阻塞）
        success = self.player.play_audio_data(audio_data, TestConfig.SAMPLE_RATE, blocking=False)
        self.assertTrue(success, "音频播放失败")
        
        # 等待播放完成
        time.sleep(0.3)
        
        # 停止播放
        self.player.stop_playback()
    
    @unittest.skipIf(os.getenv('CI') or not sys.stdin.isatty(), "跳过交互式测试")
    def test_interactive_speaker_verification(self):
        """交互式扬声器验证测试"""
        print("开始交互式扬声器验证测试")
        
        test_cases = [
            ("440Hz正弦波", lambda: self.generator.generate_sine_wave(440, 2.0)),
            ("1000Hz正弦波", lambda: self.generator.generate_sine_wave(1000, 2.0)),
            ("白噪声", lambda: self.generator.generate_white_noise(2.0)),
            ("扫频信号", lambda: self.generator.generate_frequency_sweep(200, 4000, 3.0))
        ]
        
        print("\n=== 交互式扬声器验证测试 ===")
        print("请确保音量适中，准备听取测试音频...")
        
        for test_name, audio_generator in test_cases:
            print(f"\n播放: {test_name}")
            input("按回车键开始播放...")
            
            try:
                audio_data = audio_generator()
                success = self.player.play_audio_data(audio_data, TestConfig.SAMPLE_RATE, blocking=True)
                
                if success:
                    response = input("是否听到音频？(y/n): ").lower().strip()
                    self.assertIn(response, ['y', 'yes', '是'], f"{test_name} 播放验证失败")
                else:
                    self.fail(f"{test_name} 播放失败")
                    
            except Exception as e:
                self.fail(f"{test_name} 测试异常: {e}")
        
        print("\n✅ 交互式扬声器验证测试完成")


def generate_test_audio_files():
    """生成所有测试音频文件"""
    setup_logging()
    logger = get_logger("AudioFileGenerator")
    print("开始生成测试音频文件")
    
    generator = AudioGenerator()
    file_manager = AudioFileManager()
    
    # 生成各种测试音频
    test_audio_configs = [
        ("sine_440hz", lambda: generator.generate_sine_wave(440, 3.0)),
        ("sine_1000hz", lambda: generator.generate_sine_wave(1000, 3.0)),
        ("sine_2000hz", lambda: generator.generate_sine_wave(2000, 3.0)),
        ("white_noise", lambda: generator.generate_white_noise(3.0)),
        ("frequency_sweep", lambda: generator.generate_frequency_sweep(200, 8000, 5.0)),
        ("multi_tone", lambda: generator.generate_multi_tone([440, 880, 1320], 3.0)),
        ("low_frequency", lambda: generator.generate_sine_wave(100, 3.0)),
        ("high_frequency", lambda: generator.generate_sine_wave(8000, 3.0))
    ]
    
    generated_files = []
    
    for filename, audio_generator in test_audio_configs:
        try:
            print(f"生成音频文件: {filename}")
            audio_data = audio_generator()
            file_path = file_manager.save_audio_to_wav(audio_data, filename)
            generated_files.append(file_path)
            print(f"✅ 生成成功: {file_path}")
            
        except Exception as e:
            print(f"❌ 生成失败 {filename}: {e}")
    
    print(f"音频文件生成完成，共生成 {len(generated_files)} 个文件")
    print(f"文件保存位置: {TestConfig.TEST_AUDIO_DIR}")
    
    return generated_files


def play_test_audio_files(device_id: Optional[int] = None):
    """播放所有测试音频文件"""
    setup_logging()
    logger = get_logger("AudioFilePlayer")
    print("开始播放测试音频文件")
    
    player = AudioPlayer(device_id)
    
    # 检查设备
    devices = player.get_available_output_devices()
    if not devices:
        print("未找到可用的音频输出设备")
        return False
    
    if device_id is not None:
        print(f"使用指定设备 ID: {device_id}")
    else:
        print("使用默认音频设备")
    
    # 查找测试音频文件
    audio_files = list(TestConfig.TEST_AUDIO_DIR.glob("*.wav"))
    if not audio_files:
        logger.warning("未找到测试音频文件，正在生成...")
        generate_test_audio_files()
        audio_files = list(TestConfig.TEST_AUDIO_DIR.glob("*.wav"))
    
    if not audio_files:
        print("无法生成或找到测试音频文件")
        return False
    
    print(f"找到 {len(audio_files)} 个测试音频文件")
    
    # 播放每个文件
    for i, file_path in enumerate(sorted(audio_files), 1):
        print(f"[{i}/{len(audio_files)}] 播放: {file_path.name}")
        
        try:
            success = player.play_audio_file(file_path, blocking=True)
            if success:
                print(f"✅ 播放完成: {file_path.name}")
            else:
                print(f"❌ 播放失败: {file_path.name}")
                
            # 文件间间隔
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("播放被用户中断")
            player.stop_playback()
            break
        except Exception as e:
            print(f"播放文件时出错 {file_path.name}: {e}")
    
    print("测试音频播放完成")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="音频扬声器验证测试系统")
    parser.add_argument("--device-id", type=int, help="指定音频输出设备ID")
    parser.add_argument("--generate-only", action="store_true", help="仅生成测试音频文件")
    parser.add_argument("--play-only", action="store_true", help="仅播放测试音频文件")
    parser.add_argument("--list-devices", action="store_true", help="列出可用音频设备")
    parser.add_argument("--cleanup", action="store_true", help="清理测试文件")
    
    args = parser.parse_args()
    
    # 初始化日志
    
    try:
        if args.list_devices:
            # 列出设备
            player = AudioPlayer()
            devices = player.get_available_output_devices()
            print("\n=== 可用音频输出设备 ===")
            for device in devices:
                print(f"设备 {device['id']}: {device['name']} ({device['channels']}声道, {device['sample_rate']}Hz)")
            return
        
        if args.cleanup:
            # 清理测试文件
            file_manager = AudioFileManager()
            file_manager.cleanup_test_files()
            print("测试文件清理完成")
            return
        
        if args.generate_only:
            # 仅生成音频文件
            files = generate_test_audio_files()
            print(f"\n生成了 {len(files)} 个测试音频文件")
            print(f"文件位置: {TestConfig.TEST_AUDIO_DIR}")
            return
        
        if args.play_only:
            # 仅播放音频文件
            success = play_test_audio_files(args.device_id)
            if not success:
                sys.exit(1)
            return
        
        # 运行完整测试
        print("\n=== 音频扬声器验证测试系统 ===")
        print("正在运行完整测试套件...")
        
        # 生成测试音频
        print("生成测试音频文件")
        generate_test_audio_files()
        
        # 运行单元测试
        print("运行单元测试")
        unittest.main(argv=[''], exit=False, verbosity=2)
        
        # 播放测试音频
        print("播放测试音频")
        play_test_audio_files(args.device_id)
        
        print("\n✅ 音频扬声器验证测试完成")
        print(f"测试音频文件保存在: {TestConfig.TEST_AUDIO_DIR}")
        
    except KeyboardInterrupt:
        print("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试过程中发生错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()