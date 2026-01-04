#!/bin/bash

# 测试运行脚本
# 用于快速运行前端测试套件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_section() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# 检查依赖
check_dependencies() {
    print_section "检查依赖"

    if ! command -v npm &> /dev/null; then
        print_error "npm 未安装"
        exit 1
    fi

    if ! npm list vitest &> /dev/null 2>&1; then
        print_warn "Vitest 未安装，正在安装..."
        npm install --save-dev vitest @vitest/ui @vitest/coverage-v8 @vue/test-utils jsdom
    fi

    if ! npm list @playwright/test &> /dev/null 2>&1; then
        print_warn "Playwright 未安装，正在安装..."
        npm install --save-dev @playwright/test
        npx playwright install
    fi

    print_info "依赖检查完成"
}

# 运行单元测试和组件测试
run_unit_tests() {
    print_section "运行单元测试和组件测试"

    if [ "$1" == "ui" ]; then
        print_info "启动 Vitest UI 模式..."
        npm run test:ui
    elif [ "$1" == "coverage" ]; then
        print_info "运行测试并生成覆盖率报告..."
        npm run test:coverage
        print_info "覆盖率报告已生成: coverage/index.html"
    else
        print_info "运行所有单元测试和组件测试..."
        npm test:run
    fi
}

# 运行 E2E 测试
run_e2e_tests() {
    print_section "运行 E2E 测试"

    if [ "$1" == "ui" ]; then
        print_info "启动 Playwright UI 模式..."
        npm run test:e2e:ui
    elif [ "$1" == "debug" ]; then
        print_info "启动 Playwright 调试模式..."
        npm run test:e2e:debug
    else
        print_info "运行所有 E2E 测试..."
        npm run test:e2e
    fi
}

# 运行所有测试
run_all_tests() {
    print_section "运行所有测试"

    print_info "运行单元测试和组件测试..."
    npm test:run

    print_info "运行 E2E 测试..."
    npm run test:e2e
}

# 显示帮助信息
show_help() {
    echo "测试运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  unit                 运行单元测试和组件测试（默认）"
    echo "  unit:ui             运行单元测试 UI 模式"
    echo "  unit:coverage       运行单元测试并生成覆盖率报告"
    echo "  e2e                 运行 E2E 测试"
    echo "  e2e:ui             运行 E2E 测试 UI 模式"
    echo "  e2e:debug           运行 E2E 测试调试模式"
    echo "  all                  运行所有测试"
    echo "  help                 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                  # 运行单元测试"
    echo "  $0 unit:coverage    # 运行测试并生成覆盖率"
    echo "  $0 e2e               # 运行 E2E 测试"
    echo "  $0 all               # 运行所有测试"
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

    # 根据参数执行相应操作
    case $1 in
        unit)
            run_unit_tests
            ;;
        unit:ui)
            run_unit_tests ui
            ;;
        unit:coverage)
            run_unit_tests coverage
            ;;
        e2e)
            run_e2e_tests
            ;;
        e2e:ui)
            run_e2e_tests ui
            ;;
        e2e:debug)
            run_e2e_tests debug
            ;;
        all)
            run_all_tests
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
