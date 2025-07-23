import asyncio
import time
import wave
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
import opuslib
import sounddevice as sd
import soxr

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """
    音频编解码器类.
    """

    def __init__(self):
        self.opus_encoder = None
        self.opus_decoder = None

        # 设备默认采样率
        self.device_input_sample_rate = None
        self.device_output_sample_rate = None

        # 重采样器
        self.input_resampler = None
        self.output_resampler = None

        # 使用deque替代list，提升性能
        self._resample_input_buffer = deque()

        # 缓存计算结果
        self._device_input_frame_size = None
        self._device_output_frame_size = None

        # 异步队列
        max_queue_size = int(10 * 1000 / AudioConfig.FRAME_DURATION)
        self.audio_decode_queue = asyncio.Queue(maxsize=max_queue_size)

        # 状态管理
        self._is_closing = False
        self._is_input_paused = False

        # SoundDevice流对象
        self.input_stream = None
        self.output_stream = None

        # 音频缓冲区
        self._input_buffer = asyncio.Queue(maxsize=300)
        self._output_buffer = asyncio.Queue(maxsize=200)

        # 专门为唤醒词检测器提供的缓冲区（不受暂停影响）
        self._wake_word_buffer = asyncio.Queue(maxsize=100)

    async def initialize(self):
        """
        初始化音频设备和编解码器.
        """
        try:
            # 查询所有可用设备
            sd.wait()
            devices = sd.query_devices()
            logger.info(f"检测到 {len(devices)} 个音频设备")
            
            # 输出所有设备的详细信息
            logger.debug("=== 音频设备详细信息 ===")
            for i, device in enumerate(devices):
                logger.debug(f"设备 {i}: {device['name']}")
                logger.debug(f"  - 输入通道: {device['max_input_channels']}")
                logger.debug(f"  - 输出通道: {device['max_output_channels']}")
                logger.debug(f"  - 默认采样率: {device['default_samplerate']}")
                logger.debug(f"  - 主机API: {device['hostapi']}")
                logger.debug(f"  - 设备类型: {'输入' if device['max_input_channels'] > 0 else ''}{'输出' if device['max_output_channels'] > 0 else ''}")
            logger.debug("=== 设备信息结束 ===")

            # 查找可用的输入和输出设备
            input_device = None
            output_device = None
            input_candidates = []
            output_candidates = []
            
            # 优先选择支持16kHz采样率的设备，如果没有则选择sysdefault
            preferred_output_device = None
            preferred_input_device = 'UACDemo'
            sysdefault_device = None
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_candidates.append((i, device['name'], device['max_input_channels']))
                    # 新增：检查设备名称是否包含首选前缀
                    if preferred_input_device in device['name']:
                        input_device = i
                        logger.info(f"选择首选输入设备 {i}: {device['name']} (通道数: {device['max_input_channels']})")
                    # 修改：仅在input_device未设置时才执行原有逻辑
                    elif input_device is None:
                        input_device = i
                        logger.info(f"选择输入设备 {i}: {device['name']} (通道数: {device['max_input_channels']})")
                if device['max_output_channels'] > 0:
                    output_candidates.append((i, device['name'], device['max_output_channels']))
                    # 检查是否是sysdefault设备（通常支持更多采样率）
                    if 'sysdefault' in device['name'].lower():
                        sysdefault_device = i
                        logger.debug(f"发现sysdefault设备: {i}")
                    if output_device is None:
                        output_device = i
                        logger.info(f"选择输出设备 {i}: {device['name']} (通道数: {device['max_output_channels']})")
            
            # 如果找到了sysdefault设备，优先使用它作为输出设备
            if sysdefault_device is not None:
                output_device = sysdefault_device
                logger.info(f"🔄 切换到sysdefault输出设备 {output_device}: {devices[output_device]['name']} (支持更多采样率)")
            
            # 输出候选设备信息
            logger.debug(f"可用输入设备候选: {input_candidates}")
            logger.debug(f"可用输出设备候选: {output_candidates}")
            
            if input_device is None:
                logger.error(f"未找到可用的音频输入设备！总设备数: {len(devices)}, 输入候选: {input_candidates}")
                raise RuntimeError("未找到可用的音频输入设备（麦克风）")
            if output_device is None:
                logger.error(f"未找到可用的音频输出设备！总设备数: {len(devices)}, 输出候选: {output_candidates}")
                raise RuntimeError("未找到可用的音频输出设备（扬声器）")
            
            # 设置默认设备
            logger.debug(f"准备设置默认设备: 输入={input_device}, 输出={output_device}")
            sd.default.device = [input_device, output_device]
            logger.info(f"✅ 成功设置默认设备: 输入={input_device}, 输出={output_device}")
            
            # 获取设备默认采样率
            logger.debug(f"查询输入设备 {input_device} 的详细信息...")
            input_device_info = sd.query_devices(input_device)
            logger.debug(f"输入设备信息: {input_device_info}")
            
            logger.debug(f"查询输出设备 {output_device} 的详细信息...")
            output_device_info = sd.query_devices(output_device)
            logger.debug(f"输出设备信息: {output_device_info}")

            self.device_input_sample_rate = int(input_device_info["default_samplerate"])
            self.device_output_sample_rate = int(
                output_device_info["default_samplerate"]
            )
            
            # 验证输出设备是否支持项目所需的采样率
            logger.debug("验证输出设备采样率兼容性...")
            supported_output_rates = self._test_device_sample_rates(output_device, is_output=True)
            logger.debug(f"输出设备支持的采样率: {supported_output_rates}")
            
            # 如果设备不支持16kHz，但支持其他采样率，选择最接近的
            if AudioConfig.OUTPUT_SAMPLE_RATE not in supported_output_rates:
                if self.device_output_sample_rate in supported_output_rates:
                    logger.info(f"⚠️ 输出设备不支持{AudioConfig.OUTPUT_SAMPLE_RATE}Hz，使用设备默认采样率{self.device_output_sample_rate}Hz")
                else:
                    # 选择最接近的支持采样率
                    closest_rate = min(supported_output_rates, key=lambda x: abs(x - AudioConfig.OUTPUT_SAMPLE_RATE))
                    self.device_output_sample_rate = closest_rate
                    logger.info(f"⚠️ 输出设备不支持{AudioConfig.OUTPUT_SAMPLE_RATE}Hz，使用最接近的支持采样率{closest_rate}Hz")
            else:
                logger.info(f"✅ 输出设备支持目标采样率{AudioConfig.OUTPUT_SAMPLE_RATE}Hz")

            # 缓存帧大小计算结果
            frame_duration_sec = AudioConfig.FRAME_DURATION / 1000
            self._device_input_frame_size = int(
                self.device_input_sample_rate * frame_duration_sec
            )
            self._device_output_frame_size = int(
                self.device_output_sample_rate * frame_duration_sec
            )

            logger.info(f"📊 设备输入采样率: {self.device_input_sample_rate}Hz")
            logger.info(f"📊 设备输出采样率: {self.device_output_sample_rate}Hz")
            logger.debug(f"计算的输入帧大小: {self._device_input_frame_size}")
            logger.debug(f"计算的输出帧大小: {self._device_output_frame_size}")

            # 创建重采样器
            logger.debug("开始创建重采样器...")
            await self._create_resamplers()
            logger.debug("✅ 重采样器创建完成")

            # 设置SoundDevice使用设备默认采样率
            logger.debug("配置SoundDevice默认参数...")
            sd.default.samplerate = None  # 让设备使用默认采样率
            sd.default.channels = AudioConfig.CHANNELS
            sd.default.dtype = np.int16
            logger.debug(f"SoundDevice配置: channels={AudioConfig.CHANNELS}, dtype=int16")

            # 初始化流
            logger.debug("开始创建音频流...")
            await self._create_streams()
            logger.debug("✅ 音频流创建完成")

            # 编解码器初始化 - 客户端-服务器架构
            # 编码器：16kHz发送给服务器
            # 解码器：24kHz从服务器接收
            logger.debug("开始初始化Opus编解码器...")
            logger.debug(f"编码器配置: {AudioConfig.INPUT_SAMPLE_RATE}Hz, {AudioConfig.CHANNELS}通道")
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,  # 16kHz
                AudioConfig.CHANNELS,
                opuslib.APPLICATION_AUDIO,
            )
            logger.debug(f"解码器配置: {AudioConfig.OUTPUT_SAMPLE_RATE}Hz, {AudioConfig.CHANNELS}通道")
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS  # 24kHz
            )
            logger.debug("✅ Opus编解码器初始化完成")

            logger.info("🎉 音频设备和编解码器初始化成功")
        except Exception as e:
            logger.error(f"❌ 初始化音频设备失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            await self.close()
            raise

    def _test_device_sample_rates(self, device_id, is_output=True):
        """
        测试设备支持的采样率。
        
        Args:
            device_id: 设备ID
            is_output: 是否为输出设备
            
        Returns:
            list: 支持的采样率列表
        """
        test_rates = [8000, 16000, 22050, 24000, 44100, 48000]
        supported_rates = []
        
        for rate in test_rates:
            try:
                if is_output:
                    # 测试输出流
                    test_stream = sd.OutputStream(
                        device=device_id,
                        samplerate=rate,
                        channels=AudioConfig.CHANNELS,
                        dtype='int16',
                        blocksize=1024,
                        latency='low'
                    )
                else:
                    # 测试输入流
                    test_stream = sd.InputStream(
                        device=device_id,
                        samplerate=rate,
                        channels=AudioConfig.CHANNELS,
                        dtype='int16',
                        blocksize=1024,
                        latency='low'
                    )
                
                # 如果能成功创建流，说明支持该采样率
                test_stream.close()
                supported_rates.append(rate)
                logger.debug(f"✅ 设备{device_id}支持采样率{rate}Hz")
                
            except Exception as e:
                logger.debug(f"❌ 设备{device_id}不支持采样率{rate}Hz: {e}")
                continue
                
        return supported_rates

    async def _create_resamplers(self):
        """
        创建重采样器.
        """
        logger.debug(f"检查是否需要输入重采样: 设备采样率={self.device_input_sample_rate}Hz, 目标采样率={AudioConfig.INPUT_SAMPLE_RATE}Hz")
        if self.device_input_sample_rate != AudioConfig.INPUT_SAMPLE_RATE:
            logger.debug("需要创建输入重采样器")
            self.input_resampler = soxr.ResampleStream(
                self.device_input_sample_rate,
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(
                f"🔄 创建输入重采样器: {self.device_input_sample_rate}Hz -> "
                f"{AudioConfig.INPUT_SAMPLE_RATE}Hz"
            )
        else:
            logger.debug("✅ 输入采样率匹配，无需重采样")

        # 输出重采样器：从Opus解码的24kHz重采样到设备采样率
        logger.debug(f"检查是否需要输出重采样: Opus输出={AudioConfig.OUTPUT_SAMPLE_RATE}Hz, 设备采样率={self.device_output_sample_rate}Hz")
        if self.device_output_sample_rate != AudioConfig.OUTPUT_SAMPLE_RATE:
            logger.debug("需要创建输出重采样器")
            self.output_resampler = soxr.ResampleStream(
                AudioConfig.OUTPUT_SAMPLE_RATE,  # Opus输出24kHz
                self.device_output_sample_rate,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(
                f"🔄 创建输出重采样器: {AudioConfig.OUTPUT_SAMPLE_RATE}Hz -> "
                f"{self.device_output_sample_rate}Hz"
            )
        else:
            logger.debug("✅ 输出采样率匹配，无需重采样")

    async def _create_streams(self):
        """
        创建输入和输出流.
        """
        try:
            # 创建输入流（录音）
            logger.debug("创建输入流...")
            logger.debug(f"输入流参数: samplerate={self.device_input_sample_rate}, channels={AudioConfig.CHANNELS}, blocksize={self._device_input_frame_size}")
            self.input_stream = sd.InputStream(
                samplerate=self.device_input_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=self._device_input_frame_size,
                callback=self._input_callback,
                finished_callback=self._input_finished_callback,
                latency="low",
            )
            logger.debug("✅ 输入流创建成功")

            # 创建输出流（播放）
            logger.debug("创建输出流...")
            logger.debug(f"输出流参数: samplerate={self.device_output_sample_rate}, channels={AudioConfig.CHANNELS}, blocksize={self._device_output_frame_size}")
            self.output_stream = sd.OutputStream(
                samplerate=self.device_output_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=self._device_output_frame_size,
                callback=self._output_callback,
                finished_callback=self._output_finished_callback,
                latency="low",
            )
            logger.debug("✅ 输出流创建成功")

            # 启动流
            logger.debug("启动输入流...")
            self.input_stream.start()
            logger.debug("✅ 输入流启动成功")
            
            logger.debug("启动输出流...")
            self.output_stream.start()
            logger.debug("✅ 输出流启动成功")
            
            logger.info("🎵 所有音频流已成功创建并启动")

        except Exception as e:
            logger.error(f"❌ 创建音频流失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise

    def _input_callback(self, indata, frames, time_info, status):
        """
        输入流回调函数.
        """
        if status and "overflow" not in str(status).lower():
            logger.warning(f"输入流状态: {status}")

        if self._is_closing:
            return

        try:
            audio_data = indata.copy().flatten()

            # 如果需要重采样，先进行重采样
            if self.input_resampler is not None:
                audio_data = self._process_input_resampling(audio_data)
                if audio_data is None:
                    return

            # 使用统一的队列操作方法
            self._put_audio_data_safe(self._wake_word_buffer, audio_data)

            # 只有在未暂停时才填充正常的输入缓冲区
            if not self._is_input_paused:
                self._put_audio_data_safe(self._input_buffer, audio_data)

        except Exception as e:
            logger.error(f"输入回调错误: {e}")

    def _process_input_resampling(self, audio_data):
        """
        处理输入重采样.
        """
        try:
            resampled_data = self.input_resampler.resample_chunk(audio_data, last=False)
            if len(resampled_data) > 0:
                # 添加重采样数据到缓冲区
                self._resample_input_buffer.extend(resampled_data.astype(np.int16))

            # 检查缓冲区是否有足够的数据组成完整帧
            expected_frame_size = AudioConfig.INPUT_FRAME_SIZE
            if len(self._resample_input_buffer) < expected_frame_size:
                return None  # 数据不足，等待更多数据

            # 取出一帧数据
            frame_data = []
            for _ in range(expected_frame_size):
                frame_data.append(self._resample_input_buffer.popleft())

            return np.array(frame_data, dtype=np.int16)

        except Exception as e:
            logger.error(f"输入重采样失败: {e}")
            return None

    def _put_audio_data_safe(self, queue, audio_data):
        """
        安全地将音频数据放入队列.
        """
        try:
            queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            # 移除最旧的数据
            try:
                queue.get_nowait()
                queue.put_nowait(audio_data)
            except asyncio.QueueEmpty:
                queue.put_nowait(audio_data)

    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        输出流回调函数.
        """
        if status:
            if "underflow" not in str(status).lower():
                logger.warning(f"输出流状态: {status}")

        try:
            try:
                audio_data = self._output_buffer.get_nowait()

                # 如果需要重采样到设备采样率
                if self.output_resampler is not None and len(audio_data) > 0:
                    audio_data = self._process_output_resampling(audio_data)
                    if audio_data is None:
                        outdata.fill(0)
                        return

                if len(audio_data) >= frames:
                    outdata[:] = audio_data[:frames].reshape(-1, 1)
                else:
                    outdata[: len(audio_data)] = audio_data.reshape(-1, 1)
                    outdata[len(audio_data) :] = 0

            except asyncio.QueueEmpty:
                outdata.fill(0)

        except Exception as e:
            logger.error(f"输出回调错误: {e}")
            outdata.fill(0)

    def _process_output_resampling(self, audio_data):
        """
        处理输出重采样.
        """
        try:
            resampled_data = self.output_resampler.resample_chunk(
                audio_data, last=False
            )
            if len(resampled_data) > 0:
                return resampled_data.astype(np.int16)
            else:
                return None
        except Exception as e:
            logger.error(f"输出重采样失败: {e}")
            return None

    def _input_finished_callback(self):
        """
        输入流结束回调.
        """
        logger.info("输入流已结束")

    def _output_finished_callback(self):
        """
        输出流结束回调.
        """
        logger.info("输出流已结束")

    async def reinitialize_stream(self, is_input=True):
        """
        重新初始化流.
        """
        if self._is_closing:
            return False if is_input else None

        try:
            if is_input:
                logger.info(f"重新初始化输入流前 - 当前流状态: {self.input_stream.active if self.input_stream else 'None'}")
                logger.info(f"输入缓冲区大小: {self._input_buffer.qsize()}")
                logger.info(f"输入暂停状态: {self._is_input_paused}")
                
                # 重建输入流
                if self.input_stream:
                    logger.info("停止并关闭现有输入流")
                    self.input_stream.stop()
                    self.input_stream.close()

                logger.info(f"创建新的输入流 - 采样率: {self.device_input_sample_rate}, 帧大小: {self._device_input_frame_size}")
                self.input_stream = sd.InputStream(
                    samplerate=self.device_input_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=self._device_input_frame_size,
                    callback=self._input_callback,
                    finished_callback=self._input_finished_callback,
                    latency="low",
                )
                self.input_stream.start()
                logger.info(f"输入流重新初始化完成 - 新流状态: {self.input_stream.active}")
                return True
            else:
                # 重建输出流
                if self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()

                self.output_stream = sd.OutputStream(
                    samplerate=self.device_output_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=self._device_output_frame_size,
                    callback=self._output_callback,
                    finished_callback=self._output_finished_callback,
                    latency="low",
                )
                self.output_stream.start()
                logger.info("输出流重新初始化成功")
                return None
        except Exception as e:
            stream_type = "输入" if is_input else "输出"
            logger.error(f"{stream_type}流重建失败: {e}")
            if is_input:
                return False
            else:
                raise

    async def pause_input(self):
        """
        暂停音频输入.
        """
        logger.info(f"暂停音频输入前 - 输入流状态: {self.input_stream.active if self.input_stream else 'None'}")
        logger.info(f"输入缓冲区大小: {self._input_buffer.qsize()}")
        logger.info(f"唤醒词缓冲区大小: {self._wake_word_buffer.qsize()}")
        
        self._is_input_paused = True
        # 暂停输入的同时清空输入缓冲区
        self._clear_queue(self._input_buffer)
        logger.info("音频输入已暂停并清空缓冲区")
        
        logger.info(f"暂停音频输入后 - 输入流状态: {self.input_stream.active if self.input_stream else 'None'}")
        logger.info(f"清空后输入缓冲区大小: {self._input_buffer.qsize()}")

    async def resume_input(self):
        """
        恢复音频输入.
        """
        logger.info(f"恢复音频输入前 - 输入流状态: {self.input_stream.active if self.input_stream else 'None'}")
        logger.info(f"输入暂停状态: {self._is_input_paused}")
        logger.info(f"输入缓冲区大小: {self._input_buffer.qsize()}")
        
        self._is_input_paused = False
        logger.info("音频输入已恢复")
        
        logger.info(f"恢复音频输入后 - 输入流状态: {self.input_stream.active if self.input_stream else 'None'}")
        logger.info(f"输入暂停状态: {self._is_input_paused}")

    def is_input_paused(self):
        """
        检查输入是否已暂停.
        """
        return self._is_input_paused

    def _clear_queue(self, queue):
        """
        清空队列的辅助方法.
        """
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def read_audio(self) -> Optional[bytes]:
        """
        读取音频数据并编码.
        """
        if self.is_input_paused():
            logger.debug("音频输入已暂停，跳过读取")
            return None

        try:
            # 直接处理单帧数据，避免浪费
            try:
                audio_data = self._input_buffer.get_nowait()
                # logger.debug(f"成功从输入缓冲区读取音频数据，缓冲区剩余: {self._input_buffer.qsize()}")

                # 严格验证数据长度
                if len(audio_data) != AudioConfig.INPUT_FRAME_SIZE:
                    expected = AudioConfig.INPUT_FRAME_SIZE
                    actual = len(audio_data)
                    logger.warning(f"音频数据长度异常: {actual}, 期望: {expected}")
                    return None

                # 转换为bytes并编码
                pcm_data = audio_data.astype(np.int16).tobytes()
                encoded_data = self.opus_encoder.encode(pcm_data, AudioConfig.INPUT_FRAME_SIZE)
                # logger.debug(f"音频编码成功，编码后大小: {len(encoded_data)} bytes")
                return encoded_data

            except asyncio.QueueEmpty:
                # logger.debug("输入缓冲区为空，无音频数据可读取")
                return None

        except Exception as e:
            logger.error(f"音频读取失败: {e}")

        return None

    async def play_audio(self):
        """
        播放音频（处理解码队列中的数据）
        """
        try:
            if self.audio_decode_queue.empty():
                return

            processed_count = 0
            max_process_per_call = 3

            while (
                not self.audio_decode_queue.empty()
                and processed_count < max_process_per_call
            ):
                try:
                    opus_data = self.audio_decode_queue.get_nowait()

                    try:
                        # Opus解码输出24kHz
                        pcm_data = self.opus_decoder.decode(
                            opus_data, AudioConfig.OUTPUT_FRAME_SIZE
                        )

                        audio_array = np.frombuffer(pcm_data, dtype=np.int16)

                        self._put_audio_data_safe(self._output_buffer, audio_array)

                    except opuslib.OpusError as e:
                        logger.warning(f"音频解码失败，丢弃此帧: {e}")
                    except Exception as e:
                        logger.warning(f"音频处理失败，丢弃此帧: {e}")

                    processed_count += 1

                except asyncio.QueueEmpty:
                    break

        except Exception as e:
            logger.error(f"播放音频时发生未预期错误: {e}")

    async def write_audio(self, opus_data: bytes):
        """
        将Opus数据写入播放队列.
        """
        self._put_audio_data_safe(self.audio_decode_queue, opus_data)

    async def wait_for_audio_complete(self, timeout=5.0):
        """
        等待音频播放完成.
        """
        start = time.time()
        while not self.audio_decode_queue.empty() and time.time() - start < timeout:
            await asyncio.sleep(0.1)

        if not self.audio_decode_queue.empty():
            remaining = self.audio_decode_queue.qsize()
            logger.warning(f"音频播放超时，剩余队列: {remaining} 帧")

    async def clear_audio_queue(self):
        """
        清空音频队列.
        """
        logger.info("开始清空音频队列")
        cleared_count = 0
        queue_sizes = {}

        # 清空所有队列
        queues_to_clear = [
            ("audio_decode_queue", self.audio_decode_queue),
            ("input_buffer", self._input_buffer),
            ("output_buffer", self._output_buffer),
            ("wake_word_buffer", self._wake_word_buffer),
        ]

        for queue_name, queue in queues_to_clear:
            initial_size = queue.qsize()
            queue_sizes[queue_name] = initial_size
            queue_cleared = 0
            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue_cleared += 1
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break
            logger.info(f"清空{queue_name}: {queue_cleared}帧 (原大小: {initial_size})")

        # 清空重采样缓冲区
        resample_buffer_size = 0
        if self._resample_input_buffer:
            resample_buffer_size = len(self._resample_input_buffer)
            cleared_count += resample_buffer_size
            self._resample_input_buffer.clear()
            logger.info(f"清空重采样缓冲区: {resample_buffer_size}帧")

        # 额外等待一小段时间，确保正在处理的音频数据完成
        await asyncio.sleep(0.01)

        # 再次清空可能新产生的数据
        extra_cleared = 0
        for queue_name, queue in [("input_buffer", self._input_buffer), ("wake_word_buffer", self._wake_word_buffer)]:
            extra_count = 0
            while not queue.empty():
                try:
                    queue.get_nowait()
                    extra_count += 1
                    extra_cleared += 1
                except asyncio.QueueEmpty:
                    break
            if extra_count > 0:
                logger.info(f"二次清空{queue_name}: {extra_count}帧")

        cleared_count += extra_cleared

        logger.info(f"音频队列清空完成，总共丢弃 {cleared_count} 帧音频数据")
        logger.info(f"清空前队列状态: {queue_sizes}")
        logger.info(f"清空后队列状态: input_buffer={self._input_buffer.qsize()}, wake_word_buffer={self._wake_word_buffer.qsize()}")

    async def start_streams(self):
        """
        启动音频流.
        """
        try:
            if self.input_stream and not self.input_stream.active:
                try:
                    self.input_stream.start()
                except Exception as e:
                    logger.warning(f"启动输入流时出错: {e}")
                    await self.reinitialize_stream(is_input=True)

            if self.output_stream and not self.output_stream.active:
                try:
                    self.output_stream.start()
                except Exception as e:
                    logger.warning(f"启动输出流时出错: {e}")
                    await self.reinitialize_stream(is_input=False)

            logger.info("音频流已启动")
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")

    async def stop_streams(self):
        """
        停止音频流.
        """
        try:
            if self.input_stream and self.input_stream.active:
                self.input_stream.stop()
        except Exception as e:
            logger.warning(f"停止输入流失败: {e}")

        try:
            if self.output_stream and self.output_stream.active:
                self.output_stream.stop()
        except Exception as e:
            logger.warning(f"停止输出流失败: {e}")

    async def _cleanup_resampler(self, resampler, name):
        """
        清理重采样器的辅助方法.
        """
        if resampler:
            try:
                # 让重采样器处理完剩余数据
                if hasattr(resampler, "resample_chunk"):
                    empty_array = np.array([], dtype=np.int16)
                    resampler.resample_chunk(empty_array, last=True)
            except Exception as e:
                logger.warning(f"清理{name}重采样器失败: {e}")

    async def play_wav_file_nonblocking(self, file_path: str):
        """
        非阻塞播放 WAV 文件.
        
        Args:
            file_path: WAV 文件路径
        """
        def audio_file_worker():
            try:
                logger.info(f"开始播放音频文件: {file_path}")
                
                # 检查文件是否存在
                audio_file = Path(file_path)
                if not audio_file.exists():
                    logger.error(f"音频文件不存在: {file_path}")
                    return
                
                # 加载 WAV 文件
                audio_data, sample_rate = self._load_wav_file(file_path)
                if audio_data is None:
                    return
                
                # 重采样到输出设备采样率
                if sample_rate != self.device_output_sample_rate:
                    logger.info(f"重采样音频: {sample_rate}Hz -> {self.device_output_sample_rate}Hz")
                    audio_data = self._resample_audio_data(audio_data, sample_rate, self.device_output_sample_rate)
                
                # 分块播放音频数据
                chunk_size = self._device_output_frame_size
                for i in range(0, len(audio_data), chunk_size):
                    if self._is_closing:
                        break
                    
                    chunk = audio_data[i:i + chunk_size]
                    if len(chunk) < chunk_size:
                        # 填充最后一块
                        padded_chunk = np.zeros(chunk_size, dtype=np.int16)
                        padded_chunk[:len(chunk)] = chunk
                        chunk = padded_chunk
                    
                    # 将音频数据放入输出缓冲区
                    self._put_audio_data_safe(self._output_buffer, chunk)
                    
                    # 控制播放速度
                    time.sleep(AudioConfig.FRAME_DURATION / 1000.0)
                
                logger.info(f"音频文件播放完成: {file_path}")
                
            except Exception as e:
                logger.error(f"播放音频文件失败: {e}")
        
        # 在新线程中播放音频
        # import threading
        # thread = threading.Thread(target=audio_file_worker, daemon=True)
        # thread.start()
        # thread.join()

        audio_file_worker()

    def _load_wav_file(self, file_path: str):
        """
        加载 WAV 文件.
        
        Args:
            file_path: WAV 文件路径
            
        Returns:
            (audio_data, sample_rate) 或 (None, None) 如果失败
        """
        try:
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                
                # 转换为numpy数组
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # 如果是多声道，转换为单声道
                if channels > 1:
                    audio_data = audio_data.reshape(-1, channels)
                    audio_data = audio_data[:, 0]  # 取第一个声道
                
                logger.info(f"加载音频文件成功: {file_path}, 采样率: {sample_rate}Hz, 声道数: {channels}, 长度: {len(audio_data)} 样本")
                return audio_data, sample_rate
                
        except Exception as e:
            logger.error(f"加载WAV文件失败 {file_path}: {e}")
            return None, None
    
    def _resample_audio_data(self, audio_data: np.ndarray, input_rate: int, output_rate: int) -> np.ndarray:
        """
        重采样音频数据.
        
        Args:
            audio_data: 输入音频数据
            input_rate: 输入采样率
            output_rate: 输出采样率
            
        Returns:
            重采样后的音频数据
        """
        try:
            # 使用 soxr 进行高质量重采样
            resampler = soxr.ResampleStream(
                input_rate, output_rate, 1, dtype=np.int16
            )
            resampled_data = resampler.resample_chunk(audio_data, last=True)
            return resampled_data.astype(np.int16)
            
        except Exception as e:
            logger.error(f"音频重采样失败: {e}")
            return audio_data

    async def close(self):
        """
        关闭音频编解码器.
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("开始关闭音频编解码器...")

        try:
            # 清空队列
            await self.clear_audio_queue()

            # 关闭流
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输入流失败: {e}")
                finally:
                    self.input_stream = None

            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输出流失败: {e}")
                finally:
                    self.output_stream = None

            # 清理重采样器
            await self._cleanup_resampler(self.input_resampler, "输入")
            await self._cleanup_resampler(self.output_resampler, "输出")

            self.input_resampler = None
            self.output_resampler = None

            # 清理重采样缓冲区
            self._resample_input_buffer.clear()

            # 清理编解码器
            self.opus_encoder = None
            self.opus_decoder = None

            logger.info("音频资源已完全释放")
        except Exception as e:
            logger.error(f"关闭音频编解码器过程中发生错误: {e}")

    def __del__(self):
        """
        析构函数.
        """
        if not self._is_closing:
            # 在析构函数中不能使用asyncio.create_task，改为记录警告
            logger.warning("AudioCodec对象被销毁但未正确关闭，请确保调用close()方法")
