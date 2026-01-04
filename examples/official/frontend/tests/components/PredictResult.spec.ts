/**
 * PredictResult 组件测试
 * 测试预测结果组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import PredictResult from '@/components/PredictResult.vue'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import request from '@/utils/request'

describe('PredictResult', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(PredictResult)
      expect(wrapper.find('.predict-result').exists()).toBe(true)
    })

    it('should display header', () => {
      const wrapper = mount(PredictResult)
      const header = wrapper.find('h2')
      expect(header.text()).toBe('预测结果')
    })

    it('should render filter controls', () => {
      const wrapper = mount(PredictResult)
      const datePicker = wrapper.findComponent('el-date-picker-stub')
      const select = wrapper.findComponent('el-select-stub')

      expect(datePicker.exists()).toBe(true)
      expect(select.exists()).toBe(true)
    })

    it('should render predictions table', () => {
      const wrapper = mount(PredictResult)
      const table = wrapper.findComponent('el-table-stub')

      expect(table.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load predictions on mount', async () => {
      const mockPredictions = [
        {
          date: '2025-01-04',
          code: 'sh600000',
          name: '浦发银行',
          score: 0.85,
          rank: 1,
          is_held: false
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPredictions)

      const wrapper = mount(PredictResult)
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/predict/results', expect.any(Object))
    })
  })

  describe('Filter Functionality', () => {
    it('should filter predictions by date', async () => {
      const wrapper = mount(PredictResult)
      await wrapper.setData({ filterDate: '2025-01-04' })

      await wrapper.vm.loadPredictions()

      expect(request.get).toHaveBeenCalledWith('/api/predict/results', expect.objectContaining({
        params: expect.objectContaining({
          date: '2025-01-04'
        })
      }))
    })

    it('should filter by type: held', async () => {
      const wrapper = mount(PredictResult)
      await wrapper.setData({ filterType: 'held' })

      await wrapper.vm.loadPredictions()

      expect(request.get).toHaveBeenCalledWith('/api/predict/results', expect.objectContaining({
        params: expect.objectContaining({
          filter_type: 'held'
        })
      }))
    })

    it('should filter by type: not_held', async () => {
      const wrapper = mount(PredictResult)
      await wrapper.setData({ filterType: 'not_held' })

      await wrapper.vm.loadPredictions()

      expect(request.get).toHaveBeenCalledWith('/api/predict/results', expect.objectContaining({
        params: expect.objectContaining({
          filter_type: 'not_held'
        })
      }))
    })

    it('should show all predictions by default', async () => {
      const wrapper = mount(PredictResult)
      await wrapper.setData({ filterType: 'all' })

      await wrapper.vm.loadPredictions()

      expect(request.get).toHaveBeenCalledWith('/api/predict/results', expect.objectContaining({
        params: expect.objectContaining({
          filter_type: 'all'
        })
      }))
    })
  })

  describe('Predict Functionality', () => {
    it('should create predict task', async () => {
      vi.mocked(request.post).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(PredictResult)
      await wrapper.vm.handlePredict()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/predict/')
      expect(ElMessage.success).toHaveBeenCalledWith('预测任务已创建')
    })

    it('should send predict date if specified', async () => {
      vi.mocked(request.post).mockResolvedValue({})

      const wrapper = mount(PredictResult)
      await wrapper.setData({ filterDate: '2025-01-05' })

      await wrapper.vm.handlePredict()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/predict/', expect.objectContaining({
        predict_date: '2025-01-05'
      }))
    })

    it('should handle predict error', async () => {
      vi.mocked(request.post).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(PredictResult)
      await wrapper.vm.handlePredict()
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('创建预测任务失败')
    })
  })

  describe('Score Display', () => {
    it('should color high scores green', async () => {
      const mockPredictions = [
        {
          date: '2025-01-04',
          code: 'sh600000',
          name: '浦发银行',
          score: 0.85,
          rank: 1,
          is_held: false
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPredictions)

      const wrapper = mount(PredictResult)
      await wrapper.vm.$nextTick()

      const predictions = wrapper.vm.predictions
      expect(predictions[0].score).toBeGreaterThan(0.5)
    })

    it('should color low scores red', async () => {
      const mockPredictions = [
        {
          date: '2025-01-04',
          code: 'sh600000',
          name: '浦发银行',
          score: 0.35,
          rank: 10,
          is_held: false
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockPredictions)

      const wrapper = mount(PredictResult)
      await wrapper.vm.$nextTick()

      const predictions = wrapper.vm.predictions
      expect(predictions[0].score).toBeLessThan(0.5)
    })
  })

  describe('Loading State', () => {
    it('should show loading state', async () => {
      vi.mocked(request.get).mockImplementation(() => new Promise(() => {}))

      const wrapper = mount(PredictResult)
      await wrapper.vm.loadPredictions()

      expect(wrapper.vm.loading).toBe(true)
    })
  })
})
