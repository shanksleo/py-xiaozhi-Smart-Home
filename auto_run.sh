#!/bin/bash
# -*- coding: utf-8 -*-
"""
开机启动脚本 - py-xiaozhi Smart Home 自动启动服务

功能说明:
1. 自动切换到项目目录
2. 激活conda环境
3. 启动智能家居服务
4. 输出带日期的日志文件
5. 错误处理和重试机制

使用方法:
1. 给脚本添加执行权限: chmod +x auto_run.sh
2. 直接运行: ./auto_run.sh
3. 或添加到系统启动项

配置参数 (可在脚本顶部修改):
"""

# ==================== 配置参数 ====================
# 项目路径配置
PROJECT_BASE_DIR="originXiaoZhi"                    # 项目基础目录
PROJECT_NAME="py-xiaozhi-Smart-Home"                # 项目名称
CONDA_ENV_NAME="py-xiaozhi"                         # conda环境名称

# 启动参数配置
RUN_MODE="cli"                                      # 运行模式: gui 或 cli
PROTOCOL="websocket"                                # 通信协议: mqtt 或 websocket
SKIP_ACTIVATION="false"                             # 是否跳过激活: true 或 false

# 日志配置
LOG_DIR="logs"                                      # 日志目录
LOG_LEVEL="INFO"                                    # 日志级别: DEBUG, INFO, WARNING, ERROR
MAX_RETRIES=3                                       # 最大重试次数
RETRY_DELAY=5                                        # 重试间隔(秒)

# 系统配置
TIMEOUT=30                                          # 启动超时时间(秒)
HEALTH_CHECK_INTERVAL=60                            # 健康检查间隔(秒)

# ==================== 脚本开始 ====================

# 颜色输出定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取当前时间戳
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# 获取日期字符串(用于日志文件名)
get_date_string() {
    date '+%Y%m%d'
}

# 日志输出函数
log_info() {
    echo -e "${GREEN}[$(get_timestamp)] [INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(get_timestamp)] [WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(get_timestamp)] [ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_debug() {
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo -e "${CYAN}[$(get_timestamp)] [DEBUG]${NC} $1" | tee -a "$LOG_FILE"
    fi
}

# 打印分隔线
print_separator() {
    echo -e "${BLUE}$(printf '=%.0s' {1..60})${NC}" | tee -a "$LOG_FILE"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请确保已正确安装"
        return 1
    fi
    return 0
}

# 检查conda环境
check_conda_env() {
    log_debug "检查conda环境: $CONDA_ENV_NAME"
    if ! conda env list | grep -q "^$CONDA_ENV_NAME "; then
        log_error "Conda环境 '$CONDA_ENV_NAME' 不存在"
        log_info "可用的conda环境:"
        conda env list | tee -a "$LOG_FILE"
        return 1
    fi
    log_info "✅ Conda环境 '$CONDA_ENV_NAME' 检查通过"
    return 0
}

# 检查项目目录
check_project_dir() {
    log_debug "检查项目目录: $PROJECT_DIR"
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        return 1
    fi
    
    if [ ! -f "$PROJECT_DIR/main.py" ]; then
        log_error "main.py文件不存在: $PROJECT_DIR/main.py"
        return 1
    fi
    
    log_info "✅ 项目目录检查通过: $PROJECT_DIR"
    return 0
}

# 初始化环境
init_environment() {
    log_info "🚀 开始初始化py-xiaozhi Smart Home启动环境"
    print_separator
    
    # 检查必要命令
    log_info "检查系统依赖..."
    check_command "conda" || exit 1
    check_command "python3" || exit 1
    
    # 设置项目路径
    if [ -z "$HOME" ]; then
        log_error "无法获取用户主目录"
        exit 1
    fi
    
    PROJECT_DIR="$HOME/$PROJECT_BASE_DIR/$PROJECT_NAME"
    log_info "项目路径: $PROJECT_DIR"
    
    # 检查项目目录
    check_project_dir || exit 1
    
    # 创建日志目录
    LOG_DIR_FULL="$PROJECT_DIR/$LOG_DIR"
    mkdir -p "$LOG_DIR_FULL"
    
    # 设置日志文件路径(包含日期)
    DATE_STR=$(get_date_string)
    LOG_FILE="$LOG_DIR_FULL/auto_run_${DATE_STR}.log"
    
    log_info "日志文件: $LOG_FILE"
    
    # 检查conda环境
    check_conda_env || exit 1
    
    log_info "✅ 环境初始化完成"
    print_separator
}

# 激活conda环境并启动应用
start_application() {
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        log_info "🎯 尝试启动应用 (第 $((retry_count + 1)) 次)"
        
        # 切换到项目目录
        log_info "切换到项目目录: $PROJECT_DIR"
        cd "$PROJECT_DIR" || {
            log_error "无法切换到项目目录: $PROJECT_DIR"
            return 1
        }
        
        # 构建启动命令
        local cmd_args="--mode $RUN_MODE --protocol $PROTOCOL"
        if [ "$SKIP_ACTIVATION" = "true" ]; then
            cmd_args="$cmd_args --skip-activation"
        fi
        
        log_info "启动参数: $cmd_args"
        log_info "激活conda环境并启动应用..."
        
        # 激活conda环境并启动应用
        # 使用timeout命令防止启动卡死
        if timeout $TIMEOUT bash -c "
            source \$(conda info --base)/etc/profile.d/conda.sh && \
            conda activate $CONDA_ENV_NAME && \
            log_info '✅ Conda环境激活成功: $CONDA_ENV_NAME' && \
            log_info '🚀 启动py-xiaozhi Smart Home服务...' && \
            python3 main.py $cmd_args
        " 2>&1 | tee -a "$LOG_FILE"; then
            log_info "✅ 应用启动成功"
            return 0
        else
            local exit_code=$?
            log_error "应用启动失败，退出码: $exit_code"
            
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $MAX_RETRIES ]; then
                log_warn "等待 $RETRY_DELAY 秒后重试..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    log_error "❌ 应用启动失败，已达到最大重试次数: $MAX_RETRIES"
    return 1
}

# 健康检查函数
health_check() {
    log_info "🔍 开始健康检查..."
    
    # 检查进程是否存在
    if pgrep -f "python3 main.py" > /dev/null; then
        log_info "✅ 应用进程运行正常"
        return 0
    else
        log_warn "⚠️ 应用进程未找到"
        return 1
    fi
}

# 清理函数
cleanup() {
    log_info "🧹 执行清理操作..."
    
    # 终止相关进程
    pkill -f "python3 main.py" 2>/dev/null || true
    
    log_info "清理完成"
}

# 信号处理
trap cleanup EXIT INT TERM

# 主函数
main() {
    # 初始化环境
    init_environment
    
    # 启动应用
    if start_application; then
        log_info "🎉 py-xiaozhi Smart Home 启动成功！"
        
        # 如果是CLI模式，进行健康检查
        if [ "$RUN_MODE" = "cli" ]; then
            log_info "进入健康检查模式，每 $HEALTH_CHECK_INTERVAL 秒检查一次"
            while true; do
                sleep $HEALTH_CHECK_INTERVAL
                if ! health_check; then
                    log_warn "健康检查失败，尝试重启应用"
                    start_application
                fi
            done
        fi
    else
        log_error "💥 py-xiaozhi Smart Home 启动失败！"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "py-xiaozhi Smart Home 自动启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -v, --version  显示版本信息"
    echo "  -d, --debug    启用调试模式"
    echo ""
    echo "配置参数 (在脚本顶部修改):"
    echo "  PROJECT_BASE_DIR: $PROJECT_BASE_DIR"
    echo "  PROJECT_NAME: $PROJECT_NAME"
    echo "  CONDA_ENV_NAME: $CONDA_ENV_NAME"
    echo "  RUN_MODE: $RUN_MODE"
    echo "  PROTOCOL: $PROTOCOL"
    echo ""
}

# 显示版本信息
show_version() {
    echo "py-xiaozhi Smart Home Auto Run Script v1.0.0"
    echo "Copyright (c) 2024 py-xiaozhi Team"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            show_version
            exit 0
            ;;
        -d|--debug)
            LOG_LEVEL="DEBUG"
            shift
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行主函数
main "$@"