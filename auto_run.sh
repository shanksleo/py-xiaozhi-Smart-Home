#!/bin/bash

# py-xiaozhi Smart Home 自动启动脚本
# 优化版本 - 基于用户系统环境配置

# ==================== 系统环境配置 ====================
# Conda 环境路径
CONDA_PATH="/home/tianjiao/miniconda3/condabin/conda"
# Python 解释器路径
PYTHON_PATH="/usr/bin/python3"
# 项目路径
PROJECT_DIR="/home/tianjiao/originXiaoZhi/py-xiaozhi-Smart-Home"
# Conda 环境名称
CONDA_ENV_NAME="py-xiaozhi"

# ==================== 启动参数配置 ====================
RUN_MODE="cli"                    # 运行模式: gui 或 cli
PROTOCOL="websocket"              # 通信协议: mqtt 或 websocket
SKIP_ACTIVATION="false"           # 是否跳过激活: true 或 false

# ==================== 函数定义 ====================

# 输出带时间戳的日志信息
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

# 输出错误信息并退出
log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
    exit 1
}

# 检查文件或目录是否存在
check_path() {
    local path="$1"
    local type="$2"  # file 或 directory
    
    if [ "$type" = "file" ]; then
        if [ ! -f "$path" ]; then
            log_error "文件不存在: $path"
        fi
    elif [ "$type" = "directory" ]; then
        if [ ! -d "$path" ]; then
            log_error "目录不存在: $path"
        fi
    fi
    
    log_info "✅ 路径检查通过: $path"
}

# 检查系统环境
check_environment() {
    log_info "🔍 开始检查系统环境..."
    
    # 检查 Conda 路径
    check_path "$CONDA_PATH" "file"
    
    # 检查 Python 路径
    check_path "$PYTHON_PATH" "file"
    
    # 检查项目目录
    check_path "$PROJECT_DIR" "directory"
    
    # 检查 main.py 文件
    check_path "$PROJECT_DIR/main.py" "file"
    
    log_info "✅ 系统环境检查完成"
}

# 激活 Conda 环境
activate_conda_env() {
    log_info "🔧 激活 Conda 环境: $CONDA_ENV_NAME"
    
    # 使用指定路径的 conda 命令激活环境
    eval "$($CONDA_PATH shell.bash hook)"
    
    # 激活指定环境
    if ! $CONDA_PATH activate "$CONDA_ENV_NAME"; then
        log_error "无法激活 Conda 环境: $CONDA_ENV_NAME"
    fi
    
    # 验证环境是否正确激活
    if [ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV_NAME" ]; then
        log_error "Conda 环境激活验证失败，当前环境: $CONDA_DEFAULT_ENV，期望环境: $CONDA_ENV_NAME"
    fi
    
    log_info "✅ Conda 环境激活成功: $CONDA_DEFAULT_ENV"
}

# 启动应用程序
start_application() {
    log_info "🚀 启动 py-xiaozhi Smart Home 应用..."
    
    # 切换到项目目录
    if ! cd "$PROJECT_DIR"; then
        log_error "无法切换到项目目录: $PROJECT_DIR"
    fi
    
    # 构建启动命令参数
    local cmd_args="--mode $RUN_MODE --protocol $PROTOCOL"
    if [ "$SKIP_ACTIVATION" = "true" ]; then
        cmd_args="$cmd_args --skip-activation"
    fi
    
    log_info "启动参数: $cmd_args"
    log_info "使用 Python 解释器: $PYTHON_PATH"
    
    # 启动应用
    if ! "$PYTHON_PATH" main.py $cmd_args; then
        log_error "应用启动失败"
    fi
}

# 主函数
main() {
    log_info "🎯 py-xiaozhi Smart Home 自动启动脚本开始执行"
    echo "==========================================="
    
    # 检查系统环境
    check_environment
    
    echo "==========================================="
    
    # 激活 Conda 环境
    activate_conda_env
    
    echo "==========================================="
    
    # 启动应用
    start_application
    
    log_info "🎉 py-xiaozhi Smart Home 启动完成！"
}

# ==================== 脚本执行 ====================

# 设置错误时退出
set -e

# 执行主函数
main "$@"