#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARM Ubuntu音频播放诊断工具

专门用于诊断ARM Ubuntu系统上音频播放无声音的问题
包括系统音频配置检查、设备状态检查、权限检查等
"""

import os
import sys
import subprocess
import platform
import logging
import time
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_system_info():
    """检查系统基本信息"""
    logger.info("=== 系统信息检查 ===")
    logger.info(f"操作系统: {platform.system()}")
    logger.info(f"系统版本: {platform.release()}")
    logger.info(f"处理器架构: {platform.machine()}")
    logger.info(f"Python版本: {platform.python_version()}")
    
    # 检查是否为ARM Ubuntu
    machine = platform.machine().lower()
    is_arm = any(arch in machine for arch in ['arm', 'aarch64', 'armv7l'])
    logger.info(f"ARM架构: {'是' if is_arm else '否'}")
    
    try:
        with open('/etc/os-release', 'r') as f:
            content = f.read()
            if 'ubuntu' in content.lower():
                logger.info("Ubuntu系统: 是")
                for line in content.split('\n'):
                    if line.startswith('VERSION='):
                        version = line.split('=')[1].strip('"')
                        logger.info(f"Ubuntu版本: {version}")
                        break
            else:
                logger.info("Ubuntu系统: 否")
    except Exception as e:
        logger.warning(f"无法读取系统版本信息: {e}")

def check_audio_devices():
    """检查音频设备"""
    logger.info("\n=== 音频设备检查 ===")
    
    # 检查ALSA设备
    try:
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("ALSA音频设备列表:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
        else:
            logger.error(f"aplay -l 失败: {result.stderr}")
    except Exception as e:
        logger.error(f"检查ALSA设备失败: {e}")
    
    # 检查PulseAudio设备
    try:
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("\nPulseAudio输出设备列表:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
        else:
            logger.warning(f"pactl list sinks 失败: {result.stderr}")
    except Exception as e:
        logger.warning(f"检查PulseAudio设备失败: {e}")
    
    # 检查音频设备文件
    audio_devices = ['/dev/snd/', '/dev/dsp', '/dev/audio']
    for device in audio_devices:
        if os.path.exists(device):
            logger.info(f"音频设备存在: {device}")
            if device == '/dev/snd/':
                try:
                    snd_files = os.listdir(device)
                    logger.info(f"  /dev/snd/ 内容: {snd_files}")
                except Exception as e:
                    logger.warning(f"  无法读取 /dev/snd/ 内容: {e}")
        else:
            logger.warning(f"音频设备不存在: {device}")

def check_audio_permissions():
    """检查音频权限"""
    logger.info("\n=== 音频权限检查 ===")
    
    # 检查用户组
    try:
        import grp
        import pwd
        
        username = pwd.getpwuid(os.getuid()).pw_name
        logger.info(f"当前用户: {username}")
        
        # 检查audio组
        try:
            audio_group = grp.getgrnam('audio')
            if username in audio_group.gr_mem:
                logger.info("✓ 用户在audio组中")
            else:
                logger.warning("⚠ 用户不在audio组中")
                logger.info("建议执行: sudo usermod -a -G audio $USER")
        except KeyError:
            logger.warning("audio组不存在")
        
        # 检查pulse-access组
        try:
            pulse_group = grp.getgrnam('pulse-access')
            if username in pulse_group.gr_mem:
                logger.info("✓ 用户在pulse-access组中")
            else:
                logger.warning("⚠ 用户不在pulse-access组中")
        except KeyError:
            logger.info("pulse-access组不存在（正常）")
            
    except Exception as e:
        logger.error(f"检查用户组失败: {e}")
    
    # 检查音频设备权限
    audio_device_paths = ['/dev/snd/controlC0', '/dev/snd/pcmC0D0p']
    for device_path in audio_device_paths:
        if os.path.exists(device_path):
            try:
                stat_info = os.stat(device_path)
                logger.info(f"{device_path} 权限: {oct(stat_info.st_mode)[-3:]}")
                
                # 检查是否可读写
                if os.access(device_path, os.R_OK | os.W_OK):
                    logger.info(f"✓ {device_path} 可读写")
                else:
                    logger.warning(f"⚠ {device_path} 无法读写")
            except Exception as e:
                logger.warning(f"检查 {device_path} 权限失败: {e}")

def check_audio_services():
    """检查音频服务状态"""
    logger.info("\n=== 音频服务检查 ===")
    
    # 检查PulseAudio服务
    try:
        result = subprocess.run(['pulseaudio', '--check'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✓ PulseAudio服务正在运行")
        else:
            logger.warning("⚠ PulseAudio服务未运行")
            logger.info("尝试启动PulseAudio: pulseaudio --start")
    except Exception as e:
        logger.warning(f"检查PulseAudio服务失败: {e}")
    
    # 检查ALSA状态
    try:
        result = subprocess.run(['amixer'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✓ ALSA混音器可用")
            # 检查音量设置
            if 'Master' in result.stdout:
                logger.info("检测到Master音量控制")
            if '[off]' in result.stdout:
                logger.warning("⚠ 检测到静音设置")
                logger.info("建议执行: amixer sset Master unmute")
        else:
            logger.warning(f"ALSA混音器不可用: {result.stderr}")
    except Exception as e:
        logger.warning(f"检查ALSA状态失败: {e}")

def test_audio_playback():
    """测试音频播放"""
    logger.info("\n=== 音频播放测试 ===")
    
    # 查找测试音频文件
    project_root = Path(__file__).parent
    test_audio = project_root / "assets" / "audio" / "wakeup_words.wav"
    
    if not test_audio.exists():
        logger.error(f"测试音频文件不存在: {test_audio}")
        return
    
    logger.info(f"使用测试文件: {test_audio}")
    
    # 测试不同的播放器
    players_to_test = [
        ('aplay', ['aplay', str(test_audio)]),
        ('aplay -D default', ['aplay', '-D', 'default', str(test_audio)]),
        ('aplay -D hw:0,0', ['aplay', '-D', 'hw:0,0', str(test_audio)]),
        ('paplay', ['paplay', str(test_audio)]),
        ('ffplay', ['ffplay', '-nodisp', '-autoexit', str(test_audio)])
    ]
    
    for player_name, command in players_to_test:
        if subprocess.run(['which', command[0]], capture_output=True).returncode == 0:
            logger.info(f"\n测试 {player_name}:")
            try:
                logger.info(f"执行命令: {' '.join(command)}")
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"✓ {player_name} 执行成功")
                else:
                    logger.warning(f"⚠ {player_name} 执行失败:")
                    logger.warning(f"  错误输出: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.info(f"✓ {player_name} 正在播放（超时正常）")
            except Exception as e:
                logger.error(f"✗ {player_name} 测试失败: {e}")
        else:
            logger.info(f"跳过 {player_name}（未安装）")

def check_volume_settings():
    """检查音量设置"""
    logger.info("\n=== 音量设置检查 ===")
    
    # 检查ALSA音量
    try:
        result = subprocess.run(['amixer', 'get', 'Master'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("Master音量设置:")
            for line in result.stdout.split('\n'):
                if 'Playback' in line or '[' in line:
                    logger.info(f"  {line.strip()}")
        else:
            logger.warning("无法获取Master音量设置")
    except Exception as e:
        logger.warning(f"检查ALSA音量失败: {e}")
    
    # 检查PulseAudio音量
    try:
        result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("\nPulseAudio音量设置:")
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if 'Volume:' in line:
                    logger.info(f"  {line.strip()}")
                elif 'Mute:' in line:
                    logger.info(f"  {line.strip()}")
        else:
            logger.warning("无法获取PulseAudio音量设置")
    except Exception as e:
        logger.warning(f"检查PulseAudio音量失败: {e}")

def provide_solutions():
    """提供解决方案"""
    logger.info("\n=== 解决方案建议 ===")
    
    solutions = [
        "1. 检查硬件连接:",
        "   - 确保音响/耳机正确连接",
        "   - 检查音响/耳机是否开启",
        "   - 尝试不同的音频输出设备",
        "",
        "2. 权限设置:",
        "   sudo usermod -a -G audio $USER",
        "   # 然后重新登录或重启",
        "",
        "3. 音量设置:",
        "   amixer sset Master unmute",
        "   amixer sset Master 80%",
        "   pactl set-sink-volume @DEFAULT_SINK@ 80%",
        "   pactl set-sink-mute @DEFAULT_SINK@ false",
        "",
        "4. 服务重启:",
        "   pulseaudio --kill",
        "   pulseaudio --start",
        "   # 或者",
        "   sudo systemctl restart alsa-state",
        "",
        "5. 安装缺失组件:",
        "   sudo apt-get update",
        "   sudo apt-get install alsa-utils pulseaudio pulseaudio-utils",
        "   sudo apt-get install linux-modules-extra-$(uname -r)",
        "",
        "6. 测试特定设备:",
        "   aplay -D hw:0,0 /path/to/audio/file.wav",
        "   aplay -D default /path/to/audio/file.wav",
        "",
        "7. 检查内核模块:",
        "   lsmod | grep snd",
        "   sudo modprobe snd-bcm2835  # 对于树莓派",
    ]
    
    for solution in solutions:
        logger.info(solution)

def main():
    """主函数"""
    logger.info("ARM Ubuntu音频播放诊断工具启动")
    logger.info("=" * 50)
    
    try:
        check_system_info()
        check_audio_devices()
        check_audio_permissions()
        check_audio_services()
        check_volume_settings()
        test_audio_playback()
        provide_solutions()
        
        logger.info("\n=== 诊断完成 ===")
        logger.info("请根据上述检查结果和建议解决方案进行调试")
        
    except KeyboardInterrupt:
        logger.info("\n用户中断了诊断程序")
    except Exception as e:
        logger.error(f"诊断程序执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()