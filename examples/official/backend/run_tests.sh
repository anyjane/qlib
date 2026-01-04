#!/bin/bash

# 测试运行脚本
# 用于快速运行测试套件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi

    if ! python3 -c "import pytest" 2>/dev/null; then
        print_warn "pytest 未安装，正在安装..."
        pip install pytest pytest-asyncio pytest-cov pytest-mock
    fi

    print_info "依赖检查完成"
}

# 检查 MongoDB
check_mongodb() {
    print_info "检查 MongoDB 连接..."

    if ! command -v mongod &> /dev/null; then
        print_warn "MongoDB 未安装，测试可能失败"
        return
    fi

    # 尝试连接 MongoDB
    if python3 -c "from motor.motor_asyncio import AsyncIOMotorClient; client = AsyncIOMotorClient('mongodb://localhost:27017'); client.admin.command('ping')" 2>/dev/null; then
        print_info "MongoDB 连接正常"
    else
        print_warn "MongoDB 未运行或无法连接，测试可能失败"
    fi
}

# 运行所有测试
run_all_tests() {
    print_info "运行所有测试..."
    pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
}

# 运行特定模块测试
run_module_tests() {
    local module=$1
    print_info "运行 $module 模块测试..."
    pytest tests/test_${module}.py -v -m ${module}
}

# 运行快速测试（跳过慢速测试）
run_fast_tests() {
    print_info "运行快速测试（跳过慢速测试）..."
    pytest tests/ -v -m "not slow"
}

# 显示帮助信息
show_help() {
    echo "测试运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  all         运行所有测试（默认）"
    echo "  stock       运行 Stock 模块测试"
    echo "  data        运行 Data 模块测试"
    echo "  predict     运行 Predict 模块测试"
    echo "  position    运行 Position 模块测试"
    echo "  agent       运行 Agent 模块测试"
    echo "  log         运行 Log 模块测试"
    echo "  fast        运行快速测试（跳过慢速测试）"
    echo "  coverage    运行测试并生成覆盖率报告"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0              # 运行所有测试"
    echo "  $0 stock        # 运行 Stock 模块测试"
    echo "  $0 coverage     # 运行测试并生成覆盖率报告"
}

# 主函数
main() {
    cd "$(dirname "$0")"

    # 如果没有参数，显示帮助
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    # 检查依赖
    check_dependencies

    # 检查 MongoDB
    check_mongodb

    # 根据参数执行相应操作
    case $1 in
        all)
            run_all_tests
            ;;
        stock)
            run_module_tests "stock"
            ;;
        data)
            run_module_tests "data"
            ;;
        predict)
            run_module_tests "predict"
            ;;
        position)
            run_module_tests "position"
            ;;
        agent)
            run_module_tests "agent"
            ;;
        log)
            run_module_tests "log"
            ;;
        fast)
            run_fast_tests
            ;;
        coverage)
            print_info "运行测试并生成覆盖率报告..."
            pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml
            print_info "覆盖率报告已生成: htmlcov/index.html"
            ;;
        help)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac

    print_info "测试完成！"
}

# 执行主函数
main "$@"
