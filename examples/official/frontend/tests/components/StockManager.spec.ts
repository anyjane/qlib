/**
 * StockManager 组件测试
 * 测试股票管理组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import StockManager from '@/components/StockManager.vue'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(),
  },
}))

import request from '@/utils/request'

describe('StockManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(StockManager)
      expect(wrapper.find('.stock-manager').exists()).toBe(true)
    })

    it('should display toolbar buttons', () => {
      const wrapper = mount(StockManager)
      const buttons = wrapper.findAll('el-button-stub')

      expect(buttons.length).toBeGreaterThan(0)
    })

    it('should render search input', () => {
      const wrapper = mount(StockManager)
      const searchInput = wrapper.findComponent('el-input-stub')

      expect(searchInput.exists()).toBe(true)
    })

    it('should render stock table', () => {
      const wrapper = mount(StockManager)
      const table = wrapper.findComponent('el-table-stub')

      expect(table.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load stocks on mount', async () => {
      const mockStocks = [
        {
          code: 'sh600000',
          name: '浦发银行',
          enabled: true,
          is_a500: true,
          created_at: new Date(),
          updated_at: new Date()
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockStocks)

      const wrapper = mount(StockManager)
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/stocks/')
    })
  })

  describe('Filter Functionality', () => {
    it('should filter stocks by code', async () => {
      const mockStocks = [
        { code: 'sh600000', name: '浦发银行', enabled: true },
        { code: 'sz000001', name: '平安银行', enabled: true },
      ]

      vi.mocked(request.get).mockResolvedValue(mockStocks)

      const wrapper = mount(StockManager)
      await wrapper.vm.$nextTick()

      // 设置搜索查询
      await wrapper.setData({ searchQuery: 'sh600000' })
      await wrapper.vm.$nextTick()

      const filteredStocks = wrapper.vm.filteredStocks
      expect(filteredStocks.length).toBe(1)
      expect(filteredStocks[0].code).toBe('sh600000')
    })

    it('should filter stocks by name', async () => {
      const mockStocks = [
        { code: 'sh600000', name: '浦发银行', enabled: true },
        { code: 'sz000001', name: '平安银行', enabled: true },
      ]

      vi.mocked(request.get).mockResolvedValue(mockStocks)

      const wrapper = mount(StockManager)
      await wrapper.vm.$nextTick()

      await wrapper.setData({ searchQuery: '浦发' })
      await wrapper.vm.$nextTick()

      const filteredStocks = wrapper.vm.filteredStocks
      expect(filteredStocks.length).toBe(1)
      expect(filteredStocks[0].name).toContain('浦发')
    })
  })

  describe('Table Selection', () => {
    it('should track selected stocks', async () => {
      const mockStocks = [
        { code: 'sh600000', name: '浦发银行', enabled: true },
      ]

      vi.mocked(request.get).mockResolvedValue(mockStocks)

      const wrapper = mount(StockManager)
      await wrapper.vm.$nextTick()

      const selectedStocks = [{ code: 'sh600000', name: '浦发银行' }]
      await wrapper.vm.handleSelectionChange(selectedStocks)

      expect(wrapper.vm.selectedStocks).toEqual(selectedStocks)
    })

    it('should disable batch buttons when no selection', async () => {
      const wrapper = mount(StockManager)

      await wrapper.setData({ selectedStocks: [] })
      await wrapper.vm.$nextTick()

      const batchDeleteButton = wrapper.findAll('el-button-stub')[3]
      expect(batchDeleteButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('Batch Operations', () => {
    it('should call batch enable', async () => {
      const wrapper = mount(StockManager)
      const codes = ['sh600000', 'sh600036']

      vi.mocked(request.post).mockResolvedValue({ modified_count: 2 })
      vi.mocked(ElMessage.success).mockReturnValue({})

      await wrapper.vm.handleBatchEnable(true)
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/stocks/batch', expect.objectContaining({
        codes: expect.any(Array)
      }))
    })

    it('should call batch delete', async () => {
      const wrapper = mount(StockManager)
      await wrapper.setData({ selectedStocks: [{ code: 'sh600000' }] })

      vi.mocked(request.post).mockResolvedValue({ modified_count: 1 })
      vi.mocked(ElMessage.success).mockReturnValue({})

      await wrapper.vm.handleBatchDelete()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalled()
    })
  })

  describe('Stock Operations', () => {
    it('should add stock successfully', async () => {
      const wrapper = mount(StockManager)
      const newStock = {
        code: 'sh601988',
        name: '中国银行',
        is_a500: false
      }

      vi.mocked(request.post).mockResolvedValue(newStock)
      vi.mocked(ElMessage.success).mockReturnValue({})

      await wrapper.vm.createStock(newStock)
      await wrapper.vm.$nextTick()

      expect(ElMessage.success).toHaveBeenCalledWith('添加成功')
    })

    it('should delete stock with confirmation', async () => {
      const wrapper = mount(StockManager)
      const stock = { code: 'sh600000', name: '浦发银行' }

      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(request.delete).mockResolvedValue({})

      await wrapper.vm.handleDelete(stock)
      await wrapper.vm.$nextTick()

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(request.delete).toHaveBeenCalledWith('/api/stocks/sh600000')
    })
  })

  describe('Export Functionality', () => {
    it('should export stocks as CSV', async () => {
      const wrapper = mount(StockManager)
      const mockBlob = new Blob(['test'], { type: 'text/csv' })

      vi.mocked(request.get).mockResolvedValue(mockBlob)

      await wrapper.vm.handleExport('csv')
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/stocks/export', {
        params: { format: 'csv' },
        responseType: 'blob'
      })
    })

    it('should export stocks as Excel', async () => {
      const wrapper = mount(StockManager)
      const mockBlob = new Blob(['test'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })

      vi.mocked(request.get).mockResolvedValue(mockBlob)

      await wrapper.vm.handleExport('excel')
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/stocks/export', {
        params: { format: 'excel' },
        responseType: 'blob'
      })
    })
  })

  describe('Error Handling', () => {
    it('should show error message when load fails', async () => {
      vi.mocked(request.get).mockRejectedValue(new Error('Network error'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(StockManager)
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalled()
    })
  })
})
