/**
 * Data 管理 E2E 测试
 * 测试完整的数据管理用户流程
 */
import { test, expect } from '@playwright/test'

test.describe('Data Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display data management page', async ({ page }) => {
    // 点击数据管理菜单
    await page.click('text=数据管理')

    // 等待页面加载
    await page.waitForURL('**/data')

    // 验证标题
    await expect(page.locator('h2')).toHaveText('数据管理')
  })

  test('should display latest data date', async ({ page }) => {
    await page.click('text=数据管理')
    await page.waitForURL('**/data')

    // 等待数据加载
    await page.waitForTimeout(1000)

    // 验证最新数据日期显示
    const dateElement = page.locator('strong:has-text("最新数据日期")')
    await expect(dateElement).toBeVisible()
  })

  test('should download data', async ({ page }) => {
    await page.click('text=数据管理')
    await page.waitForURL('**/data')

    // 点击下载数据按钮
    await page.click('button:has-text("下载数据")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should update data', async ({ page }) => {
    await page.click('text=数据管理')
    await page.waitForURL('**/data')

    // 点击增量更新按钮
    await page.click('button:has-text("增量更新")')

    // 等待成功消息
    await page.waitForSelector('.el-message--success', { timeout: 5000 })
  })

  test('should show correct information', async ({ page }) => {
    await page.click('text=数据管理')
    await page.waitForURL('**/data')

    // 验证说明文本
    const info = page.locator('p:has-text("从腾讯财经 API 下载数据")')
    await expect(info).toBeVisible()
  })
})
