#!/bin/bash

# py-xiaozhi Smart Home 自动启动脚本
# 简化版本 - 直接使用 Conda 环境中的 Python

# ==================== 系统环境配置 ====================
# Conda 环境中的 Python 解释器路径（直接使用，无需激活）
PYTHON_PATH="/home/tianjiao/miniconda3/envs/py-xiaozhi/bin/python3"
# 项目路径
PROJECT_DIR="/home/tianjiao/originXiaoZhi/py-xiaozhi-Smart-Home"

# ==================== 启动参数配置 ====================
RUN_MODE="cli"                    # 运行模式: gui 或 cli
PROTOCOL="websocket"              # 通信协议: mqtt 或 websocket
SKIP_ACTIVATION="false"           # 是否跳过激活: true 或 false

echo whoami
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
    
    # 检查 Python 路径
    check_path "$PYTHON_PATH" "file"
    
    # 检查项目目录
    check_path "$PROJECT_DIR" "directory"
    
    # 检查 main.py 文件
    check_path "$PROJECT_DIR/main.py" "file"
    
    log_info "✅ 系统环境检查完成"
}

# 验证 Python 环境
verify_python_env() {
    log_info "🔧 验证 Python 环境..."
    
    # 检查 Python 版本
    local python_version
    python_version=$("$PYTHON_PATH" --version 2>&1)
    log_info "Python 版本: $python_version"
    
    # 检查是否在正确的 Conda 环境中
    local conda_env
    conda_env=$("$PYTHON_PATH" -c "import sys; print(sys.prefix)" 2>/dev/null)
    if [[ "$conda_env" == *"py-xiaozhi"* ]]; then
        log_info "✅ 确认使用 py-xiaozhi 环境: $conda_env"
    else
        log_info "⚠️ Python 环境路径: $conda_env"
    fi
    
    # 测试基本 Python 功能
    if "$PYTHON_PATH" -c "import sys; print('Python 环境正常')" 2>/dev/null; then
        log_info "✅ Python 环境验证成功"
    else
        log_error "Python 环境验证失败"
    fi
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
    log_info "工作目录: $(pwd)"
    
    # 启动应用
    log_info "正在启动应用程序..."
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
    
    # 验证 Python 环境
    verify_python_env
    
    echo "==========================================="
    
    # 启动应用
    start_application
    
    log_info "🎉 py-xiaozhi Smart Home 启动完成！"
}

# ==================== 脚本执行 ====================

# 执行主函数
main "$@"