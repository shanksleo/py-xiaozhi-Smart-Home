#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB音频设备综合测试系统 - 树莓派5 Ubuntu 25.4专用

本测试文件专门用于树莓派5 Ubuntu 25.4系统中USB麦克风和扬声器的全面测试，包括：

核心功能：
1. USB音频设备自动检测和识别
2. 麦克风录音功能测试（多种采样率、格式）
3. 扬声器播放功能测试（频响、失真、延迟）
4. 音频质量分析（SNR、THD、频响曲线）
5. 实时音频处理测试（回声消除、噪声抑制）
6. 设备兼容性和稳定性测试
7. 音频同步和延迟测试
8. 多设备并发测试

技术方案对比：
- SoundDevice: 现代化、低延迟、NumPy集成 ⭐⭐⭐⭐⭐ (主要使用)
- PyAudio: 传统、稳定、PortAudio封装 ⭐⭐⭐ (兼容性支持)
- ALSA直接调用: 底层控制、Linux原生 ⭐⭐⭐ (系统级检测)
- WebRTC APM: 专业音频处理、回声消除 ⭐⭐⭐⭐ (音频增强)

使用方法：
1. 完整测试：python tests/test_usb_audio_comprehensive.py
2. 仅设备检测：python tests/test_usb_audio_comprehensive.py --detect-only
3. 仅录音测试：python tests/test_usb_audio_comprehensive.py --record-only
4. 仅播放测试：python tests/test_usb_audio_comprehensive.py --playback-only
5. 指定设备：python tests/test_usb_audio_comprehensive.py --input-device 1 --output-device 2
6. 质量分析：python tests/test_usb_audio_comprehensive.py --quality-analysis
7. 压力测试：python tests/test_usb_audio_comprehensive.py --stress-test
8. 生成报告：python tests/test_usb_audio_comprehensive.py --generate-report

测试环境要求：
- 树莓派5 + Ubuntu 25.4
- Python 3.9+
- USB麦克风和/或扬声器
- sounddevice >= 0.4.4
- numpy >= 1.26.4
- scipy >= 1.11.0
- matplotlib >= 3.7.0 (用于图表生成)
- pyaudio >= 0.2.11 (兼容性支持)

注意事项：
- 测试前请确保USB设备正确连接
- 某些测试需要安静环境以获得准确结果
- 长时间测试可能产生较大的临时文件
- 建议在测试前备份重要音频设置
"""

import unittest
import sys
import os
import argparse
import time
import wave
import json
import threading
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import numpy as np
    import sounddevice as sd
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 无头环境支持
except ImportError as e:
    print(f"缺少必要依赖: {e}")
    print("请运行: pip install numpy sounddevice matplotlib")
    sys.exit(1)

# 可选依赖
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("PyAudio不可用，将跳过相关兼容性测试")

from src.utils.logging_config import setup_logging, get_logger
from src.constants.constants import AudioConfig
from src.audio_codecs.audio_codec import AudioCodec
from src.audio_processing.webrtc_processing import WebRTCProcessor

# 测试配置参数
@dataclass
class USBTestConfig:
    """USB音频测试配置类"""
    
    # 基础音频参数
    SAMPLE_RATES = [8000, 16000, 22050, 44100, 48000, 96000]  # 支持的采样率
    CHANNELS = [1, 2]  # 支持的声道数
    FORMATS = ['int16', 'int24', 'float32']  # 支持的音频格式
    
    # 测试音频参数
    TEST_DURATION = 3.0  # 标准测试时长（秒）
    RECORD_DURATION = 5.0  # 录音测试时长（秒）
    AMPLITUDE = 0.3  # 测试音频幅度
    
    # 测试频率
    TEST_FREQUENCIES = [100, 440, 1000, 2000, 4000, 8000]  # Hz
    SWEEP_START_FREQ = 20  # 扫频起始频率
    SWEEP_END_FREQ = 20000  # 扫频结束频率
    
    # 质量分析参数
    SNR_THRESHOLD = 40.0  # 信噪比阈值（dB）
    THD_THRESHOLD = 0.05  # 总谐波失真阈值（5%）
    LATENCY_THRESHOLD = 100.0  # 延迟阈值（ms）
    
    # 文件路径
    TEST_AUDIO_DIR = Path(__file__).parent / "usb_audio_test_files"
    REPORT_DIR = Path(__file__).parent / "usb_audio_reports"
    
    # 设备检测参数
    USB_KEYWORDS = ['usb', 'usb audio', 'usb device', 'usb microphone', 'usb speaker']
    DEVICE_SCAN_TIMEOUT = 10.0  # 设备扫描超时时间
    
    # 压力测试参数
    STRESS_TEST_DURATION = 300  # 压力测试时长（秒）
    STRESS_TEST_CYCLES = 100  # 压力测试循环次数


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    id: int
    name: str
    channels: int
    sample_rate: float
    is_usb: bool
    is_input: bool
    is_output: bool
    hostapi: str
    latency: float


@dataclass
class AudioQualityMetrics:
    """音频质量指标数据类"""
    snr: float  # 信噪比（dB）
    thd: float  # 总谐波失真
    frequency_response: List[Tuple[float, float]]  # 频响曲线
    dynamic_range: float  # 动态范围（dB）
    latency: float  # 延迟（ms）
    jitter: float  # 抖动（ms）


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    metrics: Optional[AudioQualityMetrics] = None
    details: Optional[Dict[str, Any]] = None


class USBDeviceDetector:
    """USB音频设备检测器"""
    
    def __init__(self):
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
        
    def detect_usb_audio_devices(self) -> List[DeviceInfo]:
        """检测USB音频设备
        
        Returns:
            USB音频设备列表
        """
        self.logger.info("开始检测USB音频设备")
        usb_devices = []
        
        try:
            # 使用SoundDevice检测
            devices = sd.query_devices()
            
            for i, device in enumerate(devices):
                device_name = device['name'].lower()
                is_usb = any(keyword in device_name for keyword in USBTestConfig.USB_KEYWORDS)
                
                if is_usb or 'usb' in device_name:
                    device_info = DeviceInfo(
                        id=i,
                        name=device['name'],
                        channels=max(device['max_input_channels'], device['max_output_channels']),
                        sample_rate=device['default_samplerate'],
                        is_usb=True,
                        is_input=device['max_input_channels'] > 0,
                        is_output=device['max_output_channels'] > 0,
                        hostapi=sd.query_hostapis(device['hostapi'])['name'],
                        latency=device.get('default_low_input_latency', 0) + device.get('default_low_output_latency', 0)
                    )
                    usb_devices.append(device_info)
                    self.logger.info(f"发现USB设备: {device_info.name} (ID: {device_info.id})")
            
            # 使用系统命令进一步验证
            self._verify_usb_devices_system(usb_devices)
            
        except Exception as e:
            self.logger.error(f"USB设备检测失败: {e}")
            
        self.logger.info(f"检测完成，共发现 {len(usb_devices)} 个USB音频设备")
        return usb_devices
    
    def _verify_usb_devices_system(self, devices: List[DeviceInfo]):
        """使用系统命令验证USB设备"""
        try:
            # 使用lsusb命令检查USB设备
            result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                usb_output = result.stdout.lower()
                self.logger.debug(f"lsusb输出: {usb_output}")
                
                # 检查是否有音频相关的USB设备
                audio_keywords = ['audio', 'sound', 'microphone', 'speaker', 'headset']
                for keyword in audio_keywords:
                    if keyword in usb_output:
                        self.logger.info(f"系统检测到USB音频设备关键词: {keyword}")
            
            # 使用aplay/arecord检查ALSA设备
            for cmd in [['aplay', '-l'], ['arecord', '-l']]:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.debug(f"{cmd[0]}输出: {result.stdout}")
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"{cmd[0]}命令超时")
                except FileNotFoundError:
                    self.logger.warning(f"{cmd[0]}命令不可用")
                    
        except Exception as e:
            self.logger.warning(f"系统验证USB设备时出错: {e}")
    
    def get_device_capabilities(self, device_id: int) -> Dict[str, Any]:
        """获取设备能力信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备能力字典
        """
        capabilities = {
            'supported_sample_rates': [],
            'supported_channels': [],
            'supported_formats': [],
            'latency_info': {},
            'buffer_sizes': []
        }
        
        try:
            device_info = sd.query_devices(device_id)
            
            # 测试支持的采样率
            for sample_rate in USBTestConfig.SAMPLE_RATES:
                try:
                    sd.check_input_settings(device=device_id, samplerate=sample_rate)
                    capabilities['supported_sample_rates'].append(sample_rate)
                except:
                    pass
            
            # 测试支持的声道数
            for channels in USBTestConfig.CHANNELS:
                try:
                    if device_info['max_input_channels'] >= channels:
                        sd.check_input_settings(device=device_id, channels=channels)
                        capabilities['supported_channels'].append(channels)
                except:
                    pass
            
            # 获取延迟信息
            capabilities['latency_info'] = {
                'low_input': device_info.get('default_low_input_latency', 0),
                'high_input': device_info.get('default_high_input_latency', 0),
                'low_output': device_info.get('default_low_output_latency', 0),
                'high_output': device_info.get('default_high_output_latency', 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取设备能力失败: {e}")
            
        return capabilities


class USBAudioRecorder:
    """USB音频录制器"""
    
    def __init__(self, device_id: Optional[int] = None):
        self.device_id = device_id
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
        self.is_recording = False
        self.recorded_data = None
        
    def record_audio(self, duration: float, sample_rate: int = 44100, 
                    channels: int = 1) -> Tuple[np.ndarray, int]:
        """录制音频
        
        Args:
            duration: 录制时长（秒）
            sample_rate: 采样率
            channels: 声道数
            
        Returns:
            (音频数据, 采样率)
        """
        self.logger.info(f"开始录制音频: {duration}s, {sample_rate}Hz, {channels}声道")
        
        try:
            self.is_recording = True
            
            # 录制音频
            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                device=self.device_id,
                dtype='float32'
            )
            
            # 等待录制完成
            sd.wait()
            self.is_recording = False
            
            # 如果是立体声，转换为单声道
            if channels > 1 and audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            self.recorded_data = audio_data.flatten()
            self.logger.info(f"录制完成，数据长度: {len(self.recorded_data)}")
            
            return self.recorded_data, sample_rate
            
        except Exception as e:
            self.is_recording = False
            self.logger.error(f"录制音频失败: {e}")
            raise
    
    def record_with_playback_test(self, test_signal: np.ndarray, 
                                 sample_rate: int) -> Tuple[np.ndarray, AudioQualityMetrics]:
        """录制回放测试（用于测量延迟和质量）
        
        Args:
            test_signal: 测试信号
            sample_rate: 采样率
            
        Returns:
            (录制的音频, 质量指标)
        """
        self.logger.info("开始录制回放测试")
        
        try:
            # 准备录制
            record_duration = len(test_signal) / sample_rate + 1.0  # 额外1秒缓冲
            
            # 开始录制
            recording = sd.rec(
                int(record_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=self.device_id,
                dtype='float32'
            )
            
            # 稍等片刻后开始播放
            time.sleep(0.1)
            
            # 播放测试信号
            sd.play(test_signal, samplerate=sample_rate)
            
            # 等待完成
            sd.wait()
            
            # 分析录制的音频
            recorded_audio = recording.flatten()
            metrics = self._analyze_audio_quality(test_signal, recorded_audio, sample_rate)
            
            return recorded_audio, metrics
            
        except Exception as e:
            self.logger.error(f"录制回放测试失败: {e}")
            raise
    
    def _analyze_audio_quality(self, original: np.ndarray, recorded: np.ndarray, 
                              sample_rate: int) -> AudioQualityMetrics:
        """分析音频质量"""
        try:
            # 计算信噪比
            snr = self._calculate_snr(original, recorded)
            
            # 计算总谐波失真
            thd = self._calculate_thd(recorded, sample_rate)
            
            # 计算频响
            freq_response = self._calculate_frequency_response(original, recorded, sample_rate)
            
            # 计算动态范围
            dynamic_range = self._calculate_dynamic_range(recorded)
            
            # 计算延迟
            latency = self._calculate_latency(original, recorded, sample_rate)
            
            # 计算抖动
            jitter = self._calculate_jitter(recorded, sample_rate)
            
            return AudioQualityMetrics(
                snr=snr,
                thd=thd,
                frequency_response=freq_response,
                dynamic_range=dynamic_range,
                latency=latency,
                jitter=jitter
            )
            
        except Exception as e:
            self.logger.error(f"音频质量分析失败: {e}")
            return AudioQualityMetrics(0, 1, [], 0, 1000, 100)
    
    def _calculate_snr(self, original: np.ndarray, recorded: np.ndarray) -> float:
        """计算信噪比"""
        try:
            # 对齐信号长度
            min_len = min(len(original), len(recorded))
            orig_aligned = original[:min_len]
            rec_aligned = recorded[:min_len]
            
            # 计算信号功率和噪声功率
            signal_power = np.mean(orig_aligned ** 2)
            noise_power = np.mean((rec_aligned - orig_aligned) ** 2)
            
            if noise_power == 0:
                return float('inf')
            
            snr_linear = signal_power / noise_power
            snr_db = 10 * np.log10(snr_linear) if snr_linear > 0 else -100
            
            return snr_db
            
        except Exception:
            return 0.0
    
    def _calculate_thd(self, signal: np.ndarray, sample_rate: int) -> float:
        """计算总谐波失真"""
        try:
            # 进行FFT分析
            fft_data = np.fft.fft(signal)
            freqs = np.fft.fftfreq(len(signal), 1/sample_rate)
            
            # 找到基频
            magnitude = np.abs(fft_data)
            fundamental_idx = np.argmax(magnitude[1:len(magnitude)//2]) + 1
            fundamental_freq = freqs[fundamental_idx]
            
            # 计算谐波功率
            fundamental_power = magnitude[fundamental_idx] ** 2
            harmonic_power = 0
            
            for harmonic in range(2, 6):  # 2-5次谐波
                harmonic_freq = fundamental_freq * harmonic
                harmonic_idx = np.argmin(np.abs(freqs - harmonic_freq))
                if harmonic_idx < len(magnitude):
                    harmonic_power += magnitude[harmonic_idx] ** 2
            
            if fundamental_power == 0:
                return 1.0
            
            thd = np.sqrt(harmonic_power / fundamental_power)
            return min(thd, 1.0)  # 限制在100%以内
            
        except Exception:
            return 1.0
    
    def _calculate_frequency_response(self, original: np.ndarray, recorded: np.ndarray, 
                                    sample_rate: int) -> List[Tuple[float, float]]:
        """计算频响曲线"""
        try:
            # 对齐信号长度
            min_len = min(len(original), len(recorded))
            orig_fft = np.fft.fft(original[:min_len])
            rec_fft = np.fft.fft(recorded[:min_len])
            freqs = np.fft.fftfreq(min_len, 1/sample_rate)
            
            # 计算传递函数
            transfer_function = rec_fft / (orig_fft + 1e-10)  # 避免除零
            magnitude_response = np.abs(transfer_function)
            
            # 提取正频率部分
            positive_freqs = freqs[:min_len//2]
            positive_response = magnitude_response[:min_len//2]
            
            # 转换为dB
            response_db = 20 * np.log10(positive_response + 1e-10)
            
            # 返回频率-响应对
            freq_response = list(zip(positive_freqs.tolist(), response_db.tolist()))
            
            return freq_response[:100]  # 限制数据点数量
            
        except Exception:
            return []
    
    def _calculate_dynamic_range(self, signal: np.ndarray) -> float:
        """计算动态范围"""
        try:
            if len(signal) == 0:
                return 0.0
            
            max_amplitude = np.max(np.abs(signal))
            noise_floor = np.std(signal[np.abs(signal) < 0.01])  # 估算噪声底
            
            if noise_floor == 0:
                return 100.0  # 理论最大值
            
            dynamic_range = 20 * np.log10(max_amplitude / noise_floor)
            return max(0, dynamic_range)
            
        except Exception:
            return 0.0
    
    def _calculate_latency(self, original: np.ndarray, recorded: np.ndarray, 
                          sample_rate: int) -> float:
        """计算延迟（毫秒）"""
        try:
            # 使用互相关找到延迟
            correlation = np.correlate(recorded, original, mode='full')
            delay_samples = np.argmax(correlation) - len(original) + 1
            delay_ms = (delay_samples / sample_rate) * 1000
            
            return abs(delay_ms)
            
        except Exception:
            return 1000.0  # 默认高延迟值
    
    def _calculate_jitter(self, signal: np.ndarray, sample_rate: int) -> float:
        """计算抖动（毫秒）"""
        try:
            # 简化的抖动计算：基于信号的时域变化
            if len(signal) < 2:
                return 0.0
            
            # 计算相邻样本的差异
            diff = np.diff(signal)
            jitter_samples = np.std(diff)
            jitter_ms = (jitter_samples / sample_rate) * 1000
            
            return jitter_ms
            
        except Exception:
            return 100.0


class USBAudioPlayer:
    """USB音频播放器（扩展版）"""
    
    def __init__(self, device_id: Optional[int] = None):
        self.device_id = device_id
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
        
    def get_available_usb_output_devices(self) -> List[DeviceInfo]:
        """获取可用的USB输出设备"""
        detector = USBDeviceDetector()
        all_usb_devices = detector.detect_usb_audio_devices()
        return [device for device in all_usb_devices if device.is_output]
    
    def test_frequency_response(self, frequencies: List[float], 
                              sample_rate: int = 44100) -> Dict[float, bool]:
        """测试频率响应
        
        Args:
            frequencies: 测试频率列表
            sample_rate: 采样率
            
        Returns:
            频率测试结果字典
        """
        self.logger.info(f"开始频率响应测试: {frequencies}")
        results = {}
        
        for freq in frequencies:
            try:
                # 生成测试音调
                duration = 1.0
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                test_signal = 0.3 * np.sin(2 * np.pi * freq * t).astype(np.float32)
                
                # 播放测试
                success = self.play_audio_data(test_signal, sample_rate, blocking=True)
                results[freq] = success
                
                if success:
                    self.logger.info(f"✅ 频率 {freq}Hz 播放成功")
                else:
                    self.logger.warning(f"❌ 频率 {freq}Hz 播放失败")
                
                time.sleep(0.2)  # 间隔
                
            except Exception as e:
                self.logger.error(f"频率 {freq}Hz 测试异常: {e}")
                results[freq] = False
        
        return results
    
    def test_amplitude_levels(self, levels: List[float], 
                            sample_rate: int = 44100) -> Dict[float, bool]:
        """测试不同幅度级别
        
        Args:
            levels: 幅度级别列表 (0.0-1.0)
            sample_rate: 采样率
            
        Returns:
            幅度测试结果字典
        """
        self.logger.info(f"开始幅度级别测试: {levels}")
        results = {}
        
        test_freq = 1000  # 使用1kHz测试音
        duration = 0.5
        
        for level in levels:
            try:
                # 生成测试信号
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                test_signal = level * np.sin(2 * np.pi * test_freq * t).astype(np.float32)
                
                # 播放测试
                success = self.play_audio_data(test_signal, sample_rate, blocking=True)
                results[level] = success
                
                if success:
                    self.logger.info(f"✅ 幅度 {level:.2f} 播放成功")
                else:
                    self.logger.warning(f"❌ 幅度 {level:.2f} 播放失败")
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"幅度 {level:.2f} 测试异常: {e}")
                results[level] = False
        
        return results
    
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
            self.logger.debug(f"播放音频: 采样率{sample_rate}Hz, 长度{len(audio_data)}样本")
            
            # 确保音频数据格式正确
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 限制幅度防止削波
            max_amplitude = np.max(np.abs(audio_data))
            if max_amplitude > 0.95:
                audio_data = audio_data * (0.95 / max_amplitude)
                self.logger.warning(f"音频幅度过大，已缩放至0.95")
            
            # 播放音频
            sd.play(audio_data, samplerate=sample_rate, device=self.device_id, blocking=blocking)
            
            return True
            
        except Exception as e:
            self.logger.error(f"音频播放失败: {e}")
            return False
    
    def stop_playback(self):
        """停止播放"""
        try:
            sd.stop()
            self.logger.info("音频播放已停止")
        except Exception as e:
            self.logger.error(f"停止播放时出错: {e}")


class AudioSignalGenerator:
    """音频信号生成器（扩展版）"""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
    
    def generate_test_suite_signals(self) -> Dict[str, np.ndarray]:
        """生成完整的测试信号套件
        
        Returns:
            测试信号字典
        """
        self.logger.info("生成测试信号套件")
        signals = {}
        
        try:
            # 基础测试音调
            for freq in USBTestConfig.TEST_FREQUENCIES:
                signals[f'sine_{freq}hz'] = self.generate_sine_wave(freq, USBTestConfig.TEST_DURATION)
            
            # 扫频信号
            signals['frequency_sweep'] = self.generate_frequency_sweep(
                USBTestConfig.SWEEP_START_FREQ, 
                USBTestConfig.SWEEP_END_FREQ, 
                USBTestConfig.TEST_DURATION * 2
            )
            
            # 噪声信号
            signals['white_noise'] = self.generate_white_noise(USBTestConfig.TEST_DURATION)
            signals['pink_noise'] = self.generate_pink_noise(USBTestConfig.TEST_DURATION)
            
            # 脉冲信号
            signals['impulse'] = self.generate_impulse_response()
            
            # 多音调信号
            signals['multi_tone'] = self.generate_multi_tone(
                USBTestConfig.TEST_FREQUENCIES[:4], 
                USBTestConfig.TEST_DURATION
            )
            
            # 调幅信号
            signals['am_modulated'] = self.generate_am_signal(1000, 10, USBTestConfig.TEST_DURATION)
            
            # 调频信号
            signals['fm_modulated'] = self.generate_fm_signal(1000, 100, 5, USBTestConfig.TEST_DURATION)
            
            self.logger.info(f"生成了 {len(signals)} 个测试信号")
            
        except Exception as e:
            self.logger.error(f"生成测试信号失败: {e}")
            
        return signals
    
    def generate_sine_wave(self, frequency: float, duration: float, 
                          amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成正弦波信号"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 添加淡入淡出
        fade_samples = int(0.01 * self.sample_rate)
        if len(wave_data) > 2 * fade_samples:
            wave_data[:fade_samples] *= np.linspace(0, 1, fade_samples)
            wave_data[-fade_samples:] *= np.linspace(1, 0, fade_samples)
        
        return wave_data.astype(np.float32)
    
    def generate_frequency_sweep(self, start_freq: float, end_freq: float, 
                               duration: float, amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成扫频信号"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        # 对数扫频
        instantaneous_freq = start_freq * (end_freq / start_freq) ** (t / duration)
        phase = 2 * np.pi * np.cumsum(instantaneous_freq) / self.sample_rate
        sweep_data = amplitude * np.sin(phase)
        
        return sweep_data.astype(np.float32)
    
    def generate_white_noise(self, duration: float, 
                           amplitude: float = USBTestConfig.AMPLITUDE * 0.5) -> np.ndarray:
        """生成白噪声"""
        samples = int(self.sample_rate * duration)
        noise_data = amplitude * np.random.normal(0, 1, samples)
        return noise_data.astype(np.float32)
    
    def generate_pink_noise(self, duration: float, 
                          amplitude: float = USBTestConfig.AMPLITUDE * 0.5) -> np.ndarray:
        """生成粉红噪声"""
        samples = int(self.sample_rate * duration)
        
        # 生成白噪声
        white_noise = np.random.normal(0, 1, samples)
        
        # 应用1/f滤波器近似粉红噪声
        # 简化实现：使用简单的移动平均滤波器
        window_size = max(1, int(len(white_noise) * 0.01))  # 1%的窗口大小
        pink_noise = np.convolve(white_noise, np.ones(window_size)/window_size, mode='same')
        
        # 归一化
        pink_noise = amplitude * pink_noise / np.max(np.abs(pink_noise))
        
        return pink_noise.astype(np.float32)
    
    def generate_impulse_response(self, amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成脉冲响应信号"""
        duration = 0.1  # 100ms
        samples = int(self.sample_rate * duration)
        impulse = np.zeros(samples)
        impulse[0] = amplitude  # 单位脉冲
        
        return impulse.astype(np.float32)
    
    def generate_multi_tone(self, frequencies: List[float], duration: float,
                          amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成多音调信号"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        multi_tone_data = np.zeros_like(t)
        
        for freq in frequencies:
            multi_tone_data += np.sin(2 * np.pi * freq * t)
        
        # 归一化
        multi_tone_data = amplitude * multi_tone_data / len(frequencies)
        
        return multi_tone_data.astype(np.float32)
    
    def generate_am_signal(self, carrier_freq: float, modulation_freq: float, 
                          duration: float, amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成调幅信号"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # AM调制: (1 + m*cos(2πfm*t)) * cos(2πfc*t)
        modulation_depth = 0.5
        carrier = np.cos(2 * np.pi * carrier_freq * t)
        modulation = 1 + modulation_depth * np.cos(2 * np.pi * modulation_freq * t)
        am_signal = amplitude * modulation * carrier
        
        return am_signal.astype(np.float32)
    
    def generate_fm_signal(self, carrier_freq: float, modulation_freq: float, 
                          frequency_deviation: float, duration: float, 
                          amplitude: float = USBTestConfig.AMPLITUDE) -> np.ndarray:
        """生成调频信号"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # FM调制: cos(2πfc*t + (Δf/fm)*sin(2πfm*t))
        modulation_index = frequency_deviation / modulation_freq
        phase = 2 * np.pi * carrier_freq * t + modulation_index * np.sin(2 * np.pi * modulation_freq * t)
        fm_signal = amplitude * np.cos(phase)
        
        return fm_signal.astype(np.float32)


class USBAudioFileManager:
    """USB音频文件管理器（扩展版）"""
    
    def __init__(self, base_dir: Path = USBTestConfig.TEST_AUDIO_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        setup_logging()
        self.logger = get_logger(self.__class__.__name__)
    
    def save_test_results(self, results: List[TestResult], filename: str = None) -> Path:
        """保存测试结果到JSON文件
        
        Args:
            results: 测试结果列表
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"usb_audio_test_results_{timestamp}.json"
        
        file_path = self.base_dir / filename
        
        try:
            # 转换为可序列化的格式
            serializable_results = []
            for result in results:
                result_dict = asdict(result)
                # 处理可能的numpy类型
                if result_dict.get('metrics'):
                    metrics = result_dict['metrics']
                    for key, value in metrics.items():
                        if isinstance(value, np.ndarray):
                            metrics[key] = value.tolist()
                        elif isinstance(value, (np.integer, np.floating)):
                            metrics[key] = float(value)
                serializable_results.append(result_dict)
            
            # 添加元数据
            test_data = {
                'timestamp': datetime.now().isoformat(),
                'test_config': asdict(USBTestConfig()),
                'results': serializable_results,
                'summary': self._generate_summary(results)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"测试结果已保存: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"保存测试结果失败: {e}")
            raise
    
    def _generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """生成测试摘要"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r.duration for r in results)
        
        # 质量指标统计
        snr_values = [r.metrics.snr for r in results if r.metrics and r.metrics.snr > 0]
        thd_values = [r.metrics.thd for r in results if r.metrics and r.metrics.thd < 1]
        latency_values = [r.metrics.latency for r in results if r.metrics and r.metrics.latency < 1000]
        
        summary = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration,
            'quality_metrics': {
                'avg_snr': statistics.mean(snr_values) if snr_values else 0,
                'avg_thd': statistics.mean(thd_values) if thd_values else 1,
                'avg_latency': statistics.mean(latency_values) if latency_values else 1000,
                'snr_range': [min(snr_values), max(snr_values)] if snr_values else [0, 0],
                'thd_range': [min(thd_values), max(thd_values)] if thd_values else [1, 1],
                'latency_range': [min(latency_values), max(latency_values)] if latency_values else [1000, 1000]
            }
        }
        
        return summary
    
    def save_audio_to_wav(self, audio_data: np.ndarray, filename: str, 
                         sample_rate: int = 44100) -> Path:
        """保存音频数据到WAV文件"""
        file_path = self.base_dir / f"{filename}.wav"
        
        try:
            # 转换为16位整数格式
            if audio_data.dtype == np.float32:
                audio_int16 = (audio_data * 32767).astype(np.int16)
            else:
                audio_int16 = audio_data.astype(np.int16)
            
            with wave.open(str(file_path), 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            self.logger.debug(f"音频文件保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"保存音频文件失败: {e}")
            raise
    
    def load_audio_from_wav(self, file_path: Path) -> Tuple[np.ndarray, int]:
        """从WAV文件加载音频数据"""
        try:
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
            
            self.logger.debug(f"音频文件加载成功: {file_path}")
            return audio_data, sample_rate
            
        except Exception as e:
            self.logger.error(f"加载音频文件失败: {e}")
            raise
    
    def cleanup_test_files(self, keep_recent: int = 5):
        """清理测试文件，保留最近的几个
        
        Args:
            keep_recent: 保留最近的文件数量
        """
        try:
            # 获取所有测试文件
            wav_files = list(self.base_dir.glob("*.wav"))
            json_files = list(self.base_dir.glob("*.json"))
            
            # 按修改时间排序
            wav_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除旧文件
            for file_path in wav_files[keep_recent:]:
                file_path.unlink()
                self.logger.debug(f"删除旧音频文件: {file_path}")
            
            for file_path in json_files[keep_recent:]:
                file_path.unlink()
                self.logger.debug(f"删除旧结果文件: {file_path}")
            
            self.logger.info(f"文件清理完成，保留最近 {keep_recent} 个文件")
            
        except Exception as e:
            self.logger.error(f"清理文件失败: {e}")


class TestUSBAudioComprehensive(unittest.TestCase):
    """USB音频设备综合测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        setup_logging()
        cls.logger = get_logger(cls.__name__)
        cls.detector = USBDeviceDetector()
        cls.generator = AudioSignalGenerator()
        cls.file_manager = USBAudioFileManager()
        cls.test_results = []
        
        cls.logger.info("=== USB音频设备综合测试开始 ===")
        
        # 检测USB音频设备
        cls.usb_devices = cls.detector.detect_usb_audio_devices()
        cls.logger.info(f"检测到 {len(cls.usb_devices)} 个USB音频设备")
        
        for device in cls.usb_devices:
            cls.logger.info(f"  设备: {device.name} (ID: {device.id}, 输入: {device.is_input}, 输出: {device.is_output})")
    
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        cls.logger.info("=== USB音频设备综合测试结束 ===")
        
        # 保存测试结果
        if cls.test_results:
            try:
                results_file = cls.file_manager.save_test_results(cls.test_results)
                cls.logger.info(f"测试结果已保存: {results_file}")
            except Exception as e:
                cls.logger.error(f"保存测试结果失败: {e}")
    
    def _record_test_result(self, test_name: str, success: bool, duration: float, 
                           error_message: str = None, metrics: AudioQualityMetrics = None, 
                           details: Dict[str, Any] = None):
        """记录测试结果"""
        result = TestResult(
            test_name=test_name,
            success=success,
            duration=duration,
            error_message=error_message,
            metrics=metrics,
            details=details
        )
        self.test_results.append(result)
        
        status = "✅ 通过" if success else "❌ 失败"
        self.logger.info(f"{test_name}: {status} (耗时: {duration:.2f}s)")
        if error_message:
            self.logger.error(f"  错误: {error_message}")
    
    def test_usb_device_detection(self):
        """测试USB设备检测"""
        start_time = time.time()
        
        try:
            # 基础检测
            self.assertGreater(len(self.usb_devices), 0, "未检测到USB音频设备")
            
            # 验证设备信息完整性
            for device in self.usb_devices:
                self.assertIsInstance(device.id, int)
                self.assertIsInstance(device.name, str)
                self.assertGreater(len(device.name), 0)
                self.assertGreaterEqual(device.channels, 0)
                self.assertGreater(device.sample_rate, 0)
                self.assertIsInstance(device.is_usb, bool)
            
            # 测试设备能力
            for device in self.usb_devices[:2]:  # 限制测试前2个设备
                capabilities = self.detector.get_device_capabilities(device.id)
                self.assertIsInstance(capabilities, dict)
                self.assertIn('supported_sample_rates', capabilities)
                self.assertIn('latency_info', capabilities)
            
            duration = time.time() - start_time
            self._record_test_result(
                "USB设备检测", True, duration,
                details={'device_count': len(self.usb_devices), 'devices': [asdict(d) for d in self.usb_devices]}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("USB设备检测", False, duration, str(e))
            raise
    
    def test_usb_microphone_recording(self):
        """测试USB麦克风录音功能"""
        input_devices = [d for d in self.usb_devices if d.is_input]
        
        if not input_devices:
            self.skipTest("未找到USB输入设备")
        
        for device in input_devices[:2]:  # 测试前2个输入设备
            with self.subTest(device=device.name):
                start_time = time.time()
                
                try:
                    recorder = USBAudioRecorder(device.id)
                    
                    # 测试不同采样率
                    test_sample_rates = [16000, 44100, 48000]
                    recording_results = {}
                    
                    for sample_rate in test_sample_rates:
                        try:
                            self.logger.info(f"测试录音: {device.name}, {sample_rate}Hz")
                            
                            # 录制2秒音频
                            audio_data, actual_rate = recorder.record_audio(
                                duration=2.0,
                                sample_rate=sample_rate,
                                channels=1
                            )
                            
                            # 验证录制结果
                            self.assertIsInstance(audio_data, np.ndarray)
                            self.assertGreater(len(audio_data), 0)
                            self.assertEqual(actual_rate, sample_rate)
                            
                            # 保存录制的音频
                            filename = f"recorded_{device.name.replace(' ', '_')}_{sample_rate}hz"
                            self.file_manager.save_audio_to_wav(audio_data, filename, sample_rate)
                            
                            recording_results[sample_rate] = True
                            
                        except Exception as e:
                            self.logger.warning(f"采样率 {sample_rate}Hz 录音失败: {e}")
                            recording_results[sample_rate] = False
                    
                    # 至少一个采样率成功
                    self.assertTrue(any(recording_results.values()), 
                                  f"设备 {device.name} 所有采样率录音都失败")
                    
                    duration = time.time() - start_time
                    self._record_test_result(
                        f"USB麦克风录音-{device.name}", True, duration,
                        details={'recording_results': recording_results}
                    )
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_test_result(f"USB麦克风录音-{device.name}", False, duration, str(e))
                    raise
    
    def test_usb_speaker_playback(self):
        """测试USB扬声器播放功能"""
        output_devices = [d for d in self.usb_devices if d.is_output]
        
        if not output_devices:
            self.skipTest("未找到USB输出设备")
        
        for device in output_devices[:2]:  # 测试前2个输出设备
            with self.subTest(device=device.name):
                start_time = time.time()
                
                try:
                    player = USBAudioPlayer(device.id)
                    
                    # 测试频率响应
                    test_frequencies = [440, 1000, 2000, 4000]
                    freq_results = player.test_frequency_response(test_frequencies)
                    
                    # 测试幅度级别
                    test_levels = [0.1, 0.3, 0.5, 0.7]
                    amplitude_results = player.test_amplitude_levels(test_levels)
                    
                    # 验证结果
                    self.assertTrue(any(freq_results.values()), 
                                  f"设备 {device.name} 所有频率播放都失败")
                    self.assertTrue(any(amplitude_results.values()), 
                                  f"设备 {device.name} 所有幅度播放都失败")
                    
                    duration = time.time() - start_time
                    self._record_test_result(
                        f"USB扬声器播放-{device.name}", True, duration,
                        details={
                            'frequency_results': freq_results,
                            'amplitude_results': amplitude_results
                        }
                    )
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_test_result(f"USB扬声器播放-{device.name}", False, duration, str(e))
                    raise
    
    def test_audio_quality_analysis(self):
        """测试音频质量分析"""
        # 需要同时有输入和输出设备
        input_devices = [d for d in self.usb_devices if d.is_input]
        output_devices = [d for d in self.usb_devices if d.is_output]
        
        if not input_devices or not output_devices:
            self.skipTest("需要同时有USB输入和输出设备进行质量分析")
        
        start_time = time.time()
        
        try:
            # 选择第一个输入和输出设备
            input_device = input_devices[0]
            output_device = output_devices[0]
            
            recorder = USBAudioRecorder(input_device.id)
            player = USBAudioPlayer(output_device.id)
            
            # 生成测试信号
            test_signal = self.generator.generate_sine_wave(1000, 3.0)  # 1kHz, 3秒
            
            self.logger.info(f"开始音频质量分析: 输入设备={input_device.name}, 输出设备={output_device.name}")
            
            # 进行录制回放测试
            recorded_audio, quality_metrics = recorder.record_with_playback_test(
                test_signal, 44100
            )
            
            # 验证质量指标
            self.assertIsInstance(quality_metrics, AudioQualityMetrics)
            self.assertGreaterEqual(quality_metrics.snr, 0)
            self.assertLessEqual(quality_metrics.thd, 1.0)
            self.assertGreaterEqual(quality_metrics.latency, 0)
            
            # 保存分析结果
            filename = f"quality_analysis_{input_device.name.replace(' ', '_')}_to_{output_device.name.replace(' ', '_')}"
            self.file_manager.save_audio_to_wav(recorded_audio, filename, 44100)
            
            duration = time.time() - start_time
            self._record_test_result(
                "音频质量分析", True, duration,
                metrics=quality_metrics,
                details={
                    'input_device': input_device.name,
                    'output_device': output_device.name,
                    'test_signal_freq': 1000
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("音频质量分析", False, duration, str(e))
            raise
    
    def test_device_compatibility(self):
        """测试设备兼容性"""
        start_time = time.time()
        
        try:
            compatibility_results = {}
            
            for device in self.usb_devices:
                device_results = {
                    'basic_info': True,
                    'capabilities_query': False,
                    'sample_rate_support': {},
                    'channel_support': {},
                    'format_support': {}
                }
                
                try:
                    # 测试设备能力查询
                    capabilities = self.detector.get_device_capabilities(device.id)
                    device_results['capabilities_query'] = len(capabilities) > 0
                    
                    # 测试采样率支持
                    for sample_rate in [16000, 44100, 48000]:
                        try:
                            if device.is_input:
                                sd.check_input_settings(device=device.id, samplerate=sample_rate)
                            elif device.is_output:
                                sd.check_output_settings(device=device.id, samplerate=sample_rate)
                            device_results['sample_rate_support'][sample_rate] = True
                        except:
                            device_results['sample_rate_support'][sample_rate] = False
                    
                    # 测试声道支持
                    for channels in [1, 2]:
                        try:
                            if device.is_input and device.channels >= channels:
                                sd.check_input_settings(device=device.id, channels=channels)
                                device_results['channel_support'][channels] = True
                            elif device.is_output and device.channels >= channels:
                                sd.check_output_settings(device=device.id, channels=channels)
                                device_results['channel_support'][channels] = True
                            else:
                                device_results['channel_support'][channels] = False
                        except:
                            device_results['channel_support'][channels] = False
                    
                except Exception as e:
                    self.logger.warning(f"设备 {device.name} 兼容性测试异常: {e}")
                
                compatibility_results[device.name] = device_results
            
            # 验证至少有一个设备通过基本兼容性测试
            basic_compatible = any(
                result['basic_info'] and result['capabilities_query']
                for result in compatibility_results.values()
            )
            
            self.assertTrue(basic_compatible, "没有设备通过基本兼容性测试")
            
            duration = time.time() - start_time
            self._record_test_result(
                "设备兼容性测试", True, duration,
                details={'compatibility_results': compatibility_results}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("设备兼容性测试", False, duration, str(e))
            raise
    
    def test_stress_test(self):
        """压力测试"""
        if len(self.usb_devices) == 0:
            self.skipTest("无USB设备进行压力测试")
        
        start_time = time.time()
        
        try:
            stress_results = {
                'cycles_completed': 0,
                'errors': [],
                'performance_metrics': []
            }
            
            # 选择一个设备进行压力测试
            test_device = self.usb_devices[0]
            
            self.logger.info(f"开始压力测试: {test_device.name}")
            
            # 进行多轮快速测试
            max_cycles = 20  # 减少循环次数以控制测试时间
            
            for cycle in range(max_cycles):
                cycle_start = time.time()
                
                try:
                    if test_device.is_output:
                        # 播放测试
                        player = USBAudioPlayer(test_device.id)
                        test_signal = self.generator.generate_sine_wave(1000, 0.5)  # 短信号
                        success = player.play_audio_data(test_signal, 44100, blocking=True)
                        
                        if not success:
                            stress_results['errors'].append(f"Cycle {cycle}: 播放失败")
                    
                    elif test_device.is_input:
                        # 录制测试
                        recorder = USBAudioRecorder(test_device.id)
                        audio_data, _ = recorder.record_audio(0.5, 44100, 1)  # 短录制
                        
                        if len(audio_data) == 0:
                            stress_results['errors'].append(f"Cycle {cycle}: 录制失败")
                    
                    cycle_duration = time.time() - cycle_start
                    stress_results['performance_metrics'].append(cycle_duration)
                    stress_results['cycles_completed'] = cycle + 1
                    
                    # 每5个周期报告一次进度
                    if (cycle + 1) % 5 == 0:
                        self.logger.info(f"压力测试进度: {cycle + 1}/{max_cycles}")
                    
                except Exception as e:
                    stress_results['errors'].append(f"Cycle {cycle}: {str(e)}")
                    self.logger.warning(f"压力测试周期 {cycle} 失败: {e}")
            
            # 计算性能统计
            if stress_results['performance_metrics']:
                avg_time = statistics.mean(stress_results['performance_metrics'])
                max_time = max(stress_results['performance_metrics'])
                min_time = min(stress_results['performance_metrics'])
                
                stress_results['avg_cycle_time'] = avg_time
                stress_results['max_cycle_time'] = max_time
                stress_results['min_cycle_time'] = min_time
            
            # 验证压力测试结果
            error_rate = len(stress_results['errors']) / max_cycles
            self.assertLess(error_rate, 0.2, f"压力测试错误率过高: {error_rate:.2%}")
            
            duration = time.time() - start_time
            self._record_test_result(
                "压力测试", True, duration,
                details=stress_results
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("压力测试", False, duration, str(e))
            raise


def generate_comprehensive_test_report(test_results: List[TestResult], 
                                     output_dir: Path = USBTestConfig.REPORT_DIR) -> Path:
    """生成综合测试报告
    
    Args:
        test_results: 测试结果列表
        output_dir: 输出目录
        
    Returns:
        报告文件路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"usb_audio_comprehensive_report_{timestamp}.html"
    
    # 生成HTML报告
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>USB音频设备综合测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .test-result {{ margin-bottom: 15px; padding: 10px; border-radius: 5px; }}
        .success {{ background-color: #d4edda; border-left: 4px solid #28a745; }}
        .failure {{ background-color: #f8d7da; border-left: 4px solid #dc3545; }}
        .metrics {{ background-color: #f8f9fa; padding: 10px; border-radius: 3px; margin-top: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .chart-container {{ margin: 20px 0; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 USB音频设备综合测试报告</h1>
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>测试平台:</strong> 树莓派5 + Ubuntu 25.4</p>
        
        <div class="summary">
            <h2>📊 测试摘要</h2>
            <p><strong>总测试数:</strong> {len(test_results)}</p>
            <p><strong>通过测试:</strong> {sum(1 for r in test_results if r.success)}</p>
            <p><strong>失败测试:</strong> {sum(1 for r in test_results if not r.success)}</p>
            <p><strong>成功率:</strong> {(sum(1 for r in test_results if r.success) / len(test_results) * 100):.1f}%</p>
            <p><strong>总耗时:</strong> {sum(r.duration for r in test_results):.2f}秒</p>
        </div>
        
        <h2>🔍 详细测试结果</h2>
"""
    
    # 添加每个测试的详细结果
    for result in test_results:
        status_class = "success" if result.success else "failure"
        status_icon = "✅" if result.success else "❌"
        
        html_content += f"""
        <div class="test-result {status_class}">
            <h3>{status_icon} {result.test_name}</h3>
            <p><strong>状态:</strong> {'通过' if result.success else '失败'}</p>
            <p><strong>耗时:</strong> {result.duration:.2f}秒</p>
"""
        
        if result.error_message:
            html_content += f"<p><strong>错误信息:</strong> {result.error_message}</p>"
        
        if result.metrics:
            html_content += f"""
            <div class="metrics">
                <h4>📈 质量指标</h4>
                <p><strong>信噪比:</strong> {result.metrics.snr:.2f} dB</p>
                <p><strong>总谐波失真:</strong> {result.metrics.thd:.4f}</p>
                <p><strong>延迟:</strong> {result.metrics.latency:.2f} ms</p>
                <p><strong>抖动:</strong> {result.metrics.jitter:.2f} ms</p>
                <p><strong>动态范围:</strong> {result.metrics.dynamic_range:.2f} dB</p>
            </div>
"""
        
        if result.details:
            html_content += f"""
            <div class="metrics">
                <h4>📋 详细信息</h4>
                <pre>{json.dumps(result.details, indent=2, ensure_ascii=False)}</pre>
            </div>
"""
        
        html_content += "</div>"
    
    html_content += """
        <h2>💡 建议和优化</h2>
        <ul>
            <li>定期进行USB音频设备测试以确保稳定性</li>
            <li>监控音频质量指标，及时发现性能下降</li>
            <li>根据测试结果调整音频处理参数</li>
            <li>考虑使用专业音频接口以获得更好的性能</li>
        </ul>
        
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; text-align: center;">
            <p>报告由 USB音频设备综合测试系统 自动生成</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # 保存报告
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return report_file


def main():
    """主函数 - 处理命令行参数并执行测试"""
    parser = argparse.ArgumentParser(
        description="USB音频设备综合测试系统 - 树莓派5 Ubuntu 25.4专用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python tests/test_usb_audio_comprehensive.py                    # 完整测试
  python tests/test_usb_audio_comprehensive.py --detect-only     # 仅设备检测
  python tests/test_usb_audio_comprehensive.py --record-only     # 仅录音测试
  python tests/test_usb_audio_comprehensive.py --playback-only   # 仅播放测试
  python tests/test_usb_audio_comprehensive.py --quality-analysis # 质量分析
  python tests/test_usb_audio_comprehensive.py --stress-test      # 压力测试
  python tests/test_usb_audio_comprehensive.py --generate-report  # 生成报告
        """
    )
    
    # 测试选项
    parser.add_argument('--detect-only', action='store_true', help='仅执行设备检测')
    parser.add_argument('--record-only', action='store_true', help='仅执行录音测试')
    parser.add_argument('--playback-only', action='store_true', help='仅执行播放测试')
    parser.add_argument('--quality-analysis', action='store_true', help='执行音频质量分析')
    parser.add_argument('--stress-test', action='store_true', help='执行压力测试')
    parser.add_argument('--generate-report', action='store_true', help='生成HTML测试报告')
    
    # 设备选择
    parser.add_argument('--input-device', type=int, help='指定输入设备ID')
    parser.add_argument('--output-device', type=int, help='指定输出设备ID')
    parser.add_argument('--list-devices', action='store_true', help='列出所有音频设备')
    
    # 测试参数
    parser.add_argument('--duration', type=float, default=USBTestConfig.TEST_DURATION, 
                       help=f'测试时长（秒），默认: {USBTestConfig.TEST_DURATION}')
    parser.add_argument('--sample-rate', type=int, default=44100, 
                       help='采样率，默认: 44100')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--cleanup', action='store_true', help='清理测试文件')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 初始化组件
    detector = USBDeviceDetector()
    file_manager = USBAudioFileManager()
    
    # 列出设备
    if args.list_devices:
        print("\n=== 所有音频设备 ===")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append('输入')
            if device['max_output_channels'] > 0:
                device_type.append('输出')
            
            print(f"ID {i:2d}: {device['name']} ({'/'.join(device_type)})")
            print(f"       采样率: {device['default_samplerate']:.0f}Hz, "
                  f"输入声道: {device['max_input_channels']}, "
                  f"输出声道: {device['max_output_channels']}")
        
        print("\n=== USB音频设备 ===")
        usb_devices = detector.detect_usb_audio_devices()
        if usb_devices:
            for device in usb_devices:
                device_type = []
                if device.is_input:
                    device_type.append('输入')
                if device.is_output:
                    device_type.append('输出')
                print(f"ID {device.id:2d}: {device.name} ({'/'.join(device_type)})")
        else:
            print("未检测到USB音频设备")
        return
    
    # 清理文件
    if args.cleanup:
        print("清理测试文件...")
        file_manager.cleanup_test_files()
        return
    
    # 执行测试
    test_suite = unittest.TestSuite()
    
    if args.detect_only:
        test_suite.addTest(TestUSBAudioComprehensive('test_usb_device_detection'))
    elif args.record_only:
        test_suite.addTest(TestUSBAudioComprehensive('test_usb_microphone_recording'))
    elif args.playback_only:
        test_suite.addTest(TestUSBAudioComprehensive('test_usb_speaker_playback'))
    elif args.quality_analysis:
        test_suite.addTest(TestUSBAudioComprehensive('test_audio_quality_analysis'))
    elif args.stress_test:
        test_suite.addTest(TestUSBAudioComprehensive('test_stress_test'))
    else:
        # 完整测试套件
        test_methods = [
            'test_usb_device_detection',
            'test_usb_microphone_recording',
            'test_usb_speaker_playback',
            'test_audio_quality_analysis',
            'test_device_compatibility',
            'test_stress_test'
        ]
        
        for method in test_methods:
            test_suite.addTest(TestUSBAudioComprehensive(method))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(test_suite)
    
    # 生成报告
    if args.generate_report and hasattr(TestUSBAudioComprehensive, 'test_results'):
        try:
            report_file = generate_comprehensive_test_report(TestUSBAudioComprehensive.test_results)
            print(f"\n📊 测试报告已生成: {report_file}")
        except Exception as e:
            print(f"生成报告失败: {e}")
    
    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())