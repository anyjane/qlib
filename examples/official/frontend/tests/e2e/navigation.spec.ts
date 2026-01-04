/**
 * Navigation E2E 测试
 * 测试应用的导航和整体流程
 */
import { test, expect } from '@playwright/test'

test.describe('Application Navigation', () => {
  test('should load home page', async ({ page }) => {
    await page.goto('/')

    // 验证页面标题
    await expect(page.locator('h1')).toHaveText('量化投资管理系统')
  })

  test('should display sidebar menu', async ({ page }) => {
    await page.goto('/')

    // 验证侧边栏存在
    const aside = page.locator('.el-aside')
    await expect(aside).toBeVisible()

    // 验证所有菜单项
    const menuItems = page.locator('.el-menu-item')
    const count = await menuItems.count()
    expect(count).toBe(6)
  })

  test('should navigate between pages', async ({ page }) => {
    await page.goto('/')

    // 点击股票管理
    await page.click('text=代码管理')
    await page.waitForURL('**/stocks')
    await expect(page.locator('h2')).toHaveText('股票管理')

    // 点击数据管理
    await page.click('text=数据管理')
    await page.waitForURL('**/data')
    await expect(page.locator('h2')).toHaveText('数据管理')

    // 点击预测结果
    await page.click('text=预测结果')
    await page.waitForURL('**/predict')
    await expect(page.locator('h2')).toHaveText('预测结果')

    // 点击持仓管理
    await page.click('text=持仓管理')
    await page.waitForURL('**/positions')
    await expect(page.locator('h2')).toHaveText('持仓管理')

    // 点击代理管理
    await page.click('text=代理管理')
    await page.waitForURL('**/agent')
    await expect(page.locator('h2')).toHaveText('代理管理')

    // 点击日志管理
    await page.click('text=日志管理')
    await page.waitForURL('**/logs')
    await expect(page.locator('h2')).toHaveText('日志管理')
  })

  test('should highlight active menu item', async ({ page }) => {
    await page.goto('/stocks')

    // 验证股票管理菜单项被激活
    const activeMenuItem = page.locator('.el-menu-item.is-active')
    await expect(activeMenuItem).toHaveText('代码管理')
  })

  test('should maintain navigation state', async ({ page }) => {
    await page.goto('/stocks')

    // 刷新页面
    await page.reload()

    // 验证仍然在股票管理页面
    await expect(page).toHaveURL('**/stocks')
    await expect(page.locator('h2')).toHaveText('股票管理')
  })

  test('should handle browser back button', async ({ page }) => {
    await page.goto('/stocks')

    // 导航到数据管理
    await page.click('text=数据管理')
    await page.waitForURL('**/data')

    // 点击浏览器后退按钮
    await page.goBack()

    // 验证返回到股票管理
    await expect(page).toHaveURL('**/stocks')
  })
})

test.describe('Application Responsiveness', () => {
  test('should be responsive on mobile', async ({ page, viewport }) => {
    await viewport.setSize(375, 667)
    await page.goto('/')

    // 验证页面正常显示
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('.el-aside')).toBeVisible()
  })

  test('should be responsive on tablet', async ({ page, viewport }) => {
    await viewport.setSize(768, 1024)
    await page.goto('/')

    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('.el-aside')).toBeVisible()
  })

  test('should be responsive on desktop', async ({ page, viewport }) => {
    await viewport.setSize(1920, 1080)
    await page.goto('/')

    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('.el-aside')).toBeVisible()
  })
})
