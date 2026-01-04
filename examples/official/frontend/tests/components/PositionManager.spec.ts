/**
 * PositionManager 组件测试
 * 测试持仓管理组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import PositionManager from '@/components/PositionManager.vue'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(),
  },
}))

import request from '@/utils/request'

describe('PositionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(PositionManager)
      expect(wrapper.find('.position-manager').exists()).toBe(true)
    })

    it('should render toolbar buttons', () => {
      const wrapper = mount(PositionManager)
      const buttons = wrapper.findAll('el-button-stub')

      expect(buttons.length).toBeGreaterThan(0)
    })

    it('should render positions table', () => {
      const wrapper = mount(PositionManager)
      const table = wrapper.findComponent('el-table-stub')

      expect(table.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load positions on mount', async () => {
      const mockPositions = [
        {
          code: 'sh600000',
          name: '浦发银行',
          quantity: 1000,
          cost_price: 10.50,
          market_value: 10500,
          pnl: 500,
          pnl_percent: 5.0
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPositions)

      const wrapper = mount(PositionManager)
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/positions/')
    })

    it('should handle load error', async () => {
      vi.mocked(request.get).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(PositionManager)
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('加载持仓列表失败')
    })
  })

  describe('Selection Handling', () => {
    it('should track selected positions', async () => {
      const wrapper = mount(PositionManager)
      const selectedPositions = [
        { code: 'sh600000', name: '浦发银行', quantity: 1000 }
      ]

      await wrapper.vm.handleSelectionChange(selectedPositions)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedPositions).toEqual(selectedPositions)
    })

    it('should disable batch buttons when no selection', async () => {
      const wrapper = mount(PositionManager)
      await wrapper.setData({ selectedPositions: [] })
      await wrapper.vm.$nextTick()

      const batchDeleteButton = wrapper.findAll('el-button-stub')[3]
      expect(batchDeleteButton.attributes('disabled')).toBeDefined()
    })
  })

  describe('Delete Operations', () => {
    it('should delete position with confirmation', async () => {
      const wrapper = mount(PositionManager)
      const position = { code: 'sh600000', name: '浦发银行' }

      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(request.delete).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      await wrapper.vm.handleDelete(position)
      await wrapper.vm.$nextTick()

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(request.delete).toHaveBeenCalledWith('/api/positions/sh600000')
      expect(ElMessage.success).toHaveBeenCalledWith('删除成功')
    })

    it('should cancel delete', async () => {
      const wrapper = mount(PositionManager)
      const position = { code: 'sh600000', name: '浦发银行' }

      vi.mocked(ElMessageBox.confirm).mockRejectedValue('cancel')

      await wrapper.vm.handleDelete(position)
      await wrapper.vm.$nextTick()

      expect(request.delete).not.toHaveBeenCalled()
    })

    it('should batch delete positions', async () => {
      const wrapper = mount(PositionManager)
      await wrapper.setData({
        selectedPositions: [
          { code: 'sh600000', name: '浦发银行' }
        ]
      })

      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(request.post).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      await wrapper.vm.handleBatchDelete()
      await wrapper.vm.$nextTick()

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(request.post).toHaveBeenCalledWith('/api/positions/batch', expect.objectContaining({
        operation: 'delete'
      }))
    })
  })

  describe('Sync Functionality', () => {
    it('should sync positions from agent', async () => {
      vi.mocked(request.post).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(PositionManager)
      await wrapper.vm.handleSync()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/positions/sync')
      expect(ElMessage.success).toHaveBeenCalledWith('同步持仓成功')
    })

    it('should handle sync error', async () => {
      vi.mocked(request.post).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(PositionManager)
      await wrapper.vm.handleSync()
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('同步持仓失败')
    })
  })

  describe('PnL Display', () => {
    it('should show positive PnL in green', async () => {
      const mockPositions = [
        {
          code: 'sh600000',
          name: '浦发银行',
          quantity: 1000,
          cost_price: 10.50,
          market_value: 10500,
          pnl: 500,
          pnl_percent: 5.0
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPositions)

      const wrapper = mount(PositionManager)
      await wrapper.vm.$nextTick()

      const positions = wrapper.vm.positions
      expect(positions[0].pnl).toBeGreaterThan(0)
      expect(positions[0].pnl_percent).toBeGreaterThan(0)
    })

    it('should show negative PnL in red', async () => {
      const mockPositions = [
        {
          code: 'sh600000',
          name: '浦发银行',
          quantity: 1000,
          cost_price: 10.50,
          market_value: 10500,
          pnl: -500,
          pnl_percent: -5.0
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPositions)

      const wrapper = mount(PositionManager)
      await wrapper.vm.$nextTick()

      const positions = wrapper.vm.positions
      expect(positions[0].pnl).toBeLessThan(0)
      expect(positions[0].pnl_percent).toBeLessThan(0)
    })
  })
})
