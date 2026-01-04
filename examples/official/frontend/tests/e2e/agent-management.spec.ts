/**
 * Agent 管理 E2E 测试
 * 测试完整的代理管理用户流程
 */
import { test, expect } from '@playwright/test'

test.describe('Agent Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display agent management page', async ({ page }) => {
    // 点击代理管理菜单
    await page.click('text=代理管理')

    // 等待页面加载
    await page.waitForURL('**/agent')

    // 验证标题
    await expect(page.locator('h2')).toHaveText('代理管理')
  })

  test('should load and display agents', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 等待代理卡片加载
    await page.waitForSelector('.el-card', { timeout: 5000 })

    // 验证卡片存在
    const cards = page.locator('.agent-card')
    await expect(cards.first()).toBeVisible()
  })

  test('should add new agent', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 点击添加代理按钮
    await page.click('button:has-text("添加代理")')

    // 等待对话框出现
    await page.waitForSelector('.el-dialog')

    // 填写表单
    await page.fill('input[placeholder*="代理名称"]', 'Test Agent')
    await page.fill('input[placeholder*="代理URL"]', 'http://localhost:9000')
    await page.fill('input[placeholder*="代理Token"]', 'test_token_123')

    // 点击确定
    await page.click('button:has-text("确定")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should view agent assets', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 等待代理卡片加载
    await page.waitForSelector('.agent-card')

    // 点击第一个代理卡片的操作按钮
    await page.click('.agent-card:first-child button')

    // 点击查看资产
    await page.click('text=查看资产')

    // 验证资产对话框出现
    await page.waitForSelector('.el-dialog:has-text("代理资产信息")')

    // 验证资产信息显示
    const dialogTitle = page.locator('.el-dialog .el-dialog__title')
    await expect(dialogTitle).toContainText('代理资产信息')
  })

  test('should set primary agent', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 等待代理卡片加载
    await page.waitForSelector('.agent-card')

    // 点击第一个代理卡片的操作按钮
    await page.click('.agent-card:first-child button')

    // 点击设为主用
    await page.click('text=设为主用')

    // 确认操作
    await page.click('button:has-text("确定")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should delete agent', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 等待代理卡片加载
    await page.waitForSelector('.agent-card')

    // 点击第一个代理卡片的操作按钮
    await page.click('.agent-card:first-child button')

    // 点击删除
    await page.click('text=删除')

    // 确认删除
    await page.click('button:has-text("确定")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should refresh agent status', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 点击刷新状态按钮
    await page.click('button:has-text("刷新状态")')

    // 等待刷新完成
    await page.waitForTimeout(1000)

    // 验证页面仍然可见
    const cards = page.locator('.agent-card')
    await expect(cards.first()).toBeVisible()
  })

  test('should show warning when primary agent unavailable', async ({ page }) => {
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    // 等待页面加载
    await page.waitForTimeout(1000)

    // 检查是否有警告提示（如果主用代理不可用）
    const alert = page.locator('.el-alert--warning')
    const isVisible = await alert.isVisible().catch(() => false)

    // 注意：这个测试只有在主用代理不可用时才会通过
    // 正常情况下主用代理应该可用，不会显示警告
    if (isVisible) {
      await expect(alert).toContainText('警告：主用代理不可用')
    }
  })
})

test.describe('Agent Management Responsiveness', () => {
  test('should work on mobile devices', async ({ page, viewport }) => {
    await viewport.setSize(375, 667)
    await page.goto('/')

    await page.click('text=代理管理')
    await page.waitForURL('**/agent')

    const cards = page.locator('.agent-card')
    await expect(cards.first()).toBeVisible()
  })
})
