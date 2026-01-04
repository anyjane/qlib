# Official Frontend Tests

这是 official 前端项目的完整测试套件文档。

## 测试概述

本测试套件包含三种类型的测试：

1. **单元测试** - 测试工具函数和 API 模块
2. **组件测试** - 测试 Vue 组件的渲染和交互
3. **端到端测试** - 测试完整的用户操作流程

## 目录结构

```
tests/
├── __init__.py
├── unit/                          # 单元测试
│   ├── __init__.py
│   ├── request.spec.ts              # Axios 拦截器测试
│   ├── stock.spec.ts                # Stock API 测试
│   └── agent.spec.ts               # Agent API 测试
├── components/                     # 组件测试
│   ├── __init__.py
│   ├── StockManager.spec.ts         # 股票管理组件测试
│   ├── DataManager.spec.ts          # 数据管理组件测试
│   ├── PredictResult.spec.ts       # 预测结果组件测试
│   ├── PositionManager.spec.ts      # 持仓管理组件测试
│   ├── AgentManager.spec.ts         # 代理管理组件测试
│   └── LogManager.spec.ts          # 日志管理组件测试
├── e2e/                          # 端到端测试
│   ├── __init__.py
│   ├── stock-management.spec.ts      # 股票管理 E2E 测试
│   ├── data-management.spec.ts       # 数据管理 E2E 测试
│   ├── agent-management.spec.ts      # 代理管理 E2E 测试
│   └── navigation.spec.ts           # 导航 E2E 测试
└── README.md                      # 本文档
```

## 安装依赖

### 完整安装

```bash
cd examples/official/frontend
npm install
```

### 仅安装测试依赖

```bash
npm install --save-dev \
  vitest@^1.1.0 \
  @vitest/ui@^1.1.0 \
  @vitest/coverage-v8@^1.1.0 \
  @vue/test-utils@^2.4.3 \
  jsdom@^23.0.1 \
  @playwright/test@^1.40.1 \
  happy-dom@^12.10.3
```

## 运行测试

### 单元测试和组件测试

```bash
# 运行所有测试
npm test

# 监听模式
npm test:ui

# 运行一次并退出
npm test:run

# 生成覆盖率报告
npm run test:coverage
```

### E2E 测试

```bash
# 运行 E2E 测试
npm run test:e2e

# UI 模式
npm run test:e2e:ui

# 调试模式
npm run test:e2e:debug
```

## 测试配置

### Vitest 配置

配置文件：`vitest.config.ts`

```typescript
{
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      statements: 80,
      branches: 80,
      functions: 80,
      lines: 80
    }
  }
}
```

### Playwright 配置

配置文件：`playwright.config.ts`

```typescript
{
  testDir: './tests/e2e',
  fullyParallel: true,
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173'
  }
}
```

## 测试覆盖率

### 查看覆盖率报告

```bash
# 生成覆盖率报告
npm run test:coverage

# 查看 HTML 报告
open coverage/index.html
```

### 覆盖率目标

- **语句覆盖率**: ≥80%
- **分支覆盖率**: ≥80%
- **函数覆盖率**: ≥80%
- **行覆盖率**: ≥80%

## 测试分类

### 单元测试

测试纯函数和模块：

- `request.spec.ts` - Axios 拦截器和错误处理
- `stock.spec.ts` - Stock API 函数
- `agent.spec.ts` - Agent API 函数

### 组件测试

测试 Vue 组件的渲染、交互和状态管理：

- `StockManager.spec.ts` - 股票管理组件
- `DataManager.spec.ts` - 数据管理组件
- `PredictResult.spec.ts` - 预测结果组件
- `PositionManager.spec.ts` - 持仓管理组件
- `AgentManager.spec.ts` - 代理管理组件
- `LogManager.spec.ts` - 日志管理组件

### E2E 测试

测试完整的用户操作流程：

- `stock-management.spec.ts` - 股票管理流程
- `data-management.spec.ts` - 数据管理流程
- `agent-management.spec.ts` - 代理管理流程
- `navigation.spec.ts` - 应用导航流程

## 编写测试指南

### 单元测试示例

```typescript
import { describe, it, expect } from 'vitest'
import { myFunction } from '@/utils/myUtils'

describe('myFunction', () => {
  it('should return expected result', () => {
    const result = myFunction('input')
    expect(result).toBe('expected')
  })
})
```

### 组件测试示例

```typescript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  it('should render correctly', () => {
    const wrapper = mount(MyComponent)
    expect(wrapper.find('.my-component').exists()).toBe(true)
  })
})
```

### E2E 测试示例

```typescript
import { test, expect } from '@playwright/test'

test('should complete user flow', async ({ page }) => {
  await page.goto('/')
  await page.click('button')
  await expect(page.locator('.result')).toBeVisible()
})
```

## 故障排查

### 测试失败

1. 查看详细的错误信息
   ```bash
   npm test --reporter=verbose
   ```

2. 运行单个测试文件
   ```bash
   npm test StockManager.spec.ts
   ```

3. 使用 UI 模式调试
   ```bash
   npm run test:ui
   ```

### E2E 测试失败

1. 使用调试模式
   ```bash
   npm run test:e2e:debug
   ```

2. 查看 Playwright 报告
   ```bash
   npx playwright show-report
   ```

3. 检查浏览器控制台错误

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run unit tests
        run: npm run test:coverage
      - name: Run E2E tests
        run: npm run test:e2e
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage/lcov.info
```

## 最佳实践

1. **测试隔离**: 每个测试应该独立运行，不依赖其他测试
2. **描述性名称**: 测试名称应该清楚地描述被测试的功能
3. **AAA 模式**: Arrange（准备）→ Act（执行）→ Assert（断言）
4. **Mock 外部依赖**: 使用 vi.mock 模拟外部 API 调用
5. **清理副作用**: 使用 afterEach 清理副作用（如定时器）
6. **覆盖边界条件**: 测试正常情况、边界情况和错误情况
7. **使用快照**: 对于复杂组件，使用快照测试

## 持续改进

- 定期检查测试覆盖率
- 识别未覆盖的代码区域
- 添加新功能的测试
- 重构和优化现有测试

## 许可证

本测试套件遵循与主项目相同的许可证。
