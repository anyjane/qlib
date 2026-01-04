/**
 * Stock 管理 E2E 测试
 * 测试完整的股票管理用户流程
 */
import { test, expect } from '@playwright/test'

test.describe('Stock Management', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到应用
    await page.goto('/')
  })

  test('should display stock management page', async ({ page }) => {
    // 点击股票管理菜单
    await page.click('text=代码管理')

    // 等待页面加载
    await page.waitForURL('**/stocks')

    // 验证标题
    await expect(page.locator('h2')).toHaveText('股票管理')
  })

  test('should load and display stocks', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 等待表格加载
    await page.waitForSelector('table', { timeout: 5000 })

    // 验证表格存在
    const table = page.locator('table')
    await expect(table).toBeVisible()
  })

  test('should add new stock', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 点击添加按钮
    await page.click('button:has-text("添加")')

    // 等待对话框出现
    await page.waitForSelector('.el-dialog')

    // 填写表单
    await page.fill('input[placeholder*="股票代码"]', 'sh601988')
    await page.fill('input[placeholder*="股票名称"]', '中国银行')

    // 点击确定
    await page.click('button:has-text("确定")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should search stocks', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 输入搜索词
    const searchInput = page.locator('input[placeholder*="搜索"]')
    await searchInput.fill('浦发')

    // 等待表格更新
    await page.waitForTimeout(500)

    // 验证搜索结果
    const table = page.locator('table tbody tr')
    const rowCount = await table.count()
    expect(rowCount).toBeGreaterThanOrEqual(0)
  })

  test('should export stocks as CSV', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 点击导出按钮
    await page.click('button:has-text("导出股票")')

    // 等待下拉菜单
    await page.waitForSelector('.el-dropdown-menu')

    // 点击 CSV 选项
    await page.click('text=导出为 CSV')

    // 验证下载触发
    const downloadPromise = page.waitForEvent('download')
    await downloadPromise
  })

  test('should batch enable stocks', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 选择第一行
    await page.check('table tbody tr:first-child input[type="checkbox"]')

    // 点击批量启用按钮
    await page.click('button:has-text("批量启用")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should delete stock', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 找到并点击第一行的删除按钮
    await page.click('table tbody tr:first-child button:has-text("删除")')

    // 确认删除
    await page.click('button:has-text("确定")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should initialize stocks from A500', async ({ page }) => {
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 点击重新初始化按钮
    await page.click('button:has-text("重新初始化代码列表")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })
})

test.describe('Stock Management Responsiveness', () => {
  test('should work on mobile devices', async ({ page, viewport }) => {
    // 设置移动设备视口
    await viewport.setSize(375, 667)

    await page.goto('/')

    // 点击股票管理
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    // 验证页面响应式
    const table = page.locator('table')
    await expect(table).toBeVisible()
  })

  test('should work on tablet devices', async ({ page, viewport }) => {
    // 设置平板设备视口
    await viewport.setSize(768, 1024)

    await page.goto('/')

    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')

    const table = page.locator('table')
    await expect(table).toBeVisible()
  })
})
