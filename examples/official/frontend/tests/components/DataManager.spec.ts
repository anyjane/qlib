/**
 * DataManager 组件测试
 * 测试数据管理组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import DataManager from '@/components/DataManager.vue'

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

describe('DataManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(DataManager)
      expect(wrapper.find('.data-manager').exists()).toBe(true)
    })

    it('should display header', () => {
      const wrapper = mount(DataManager)
      const header = wrapper.find('h2')
      expect(header.text()).toBe('数据管理')
    })

    it('should render download button', () => {
      const wrapper = mount(DataManager)
      const button = wrapper.findAll('el-button-stub')[0]
      expect(button.exists()).toBe(true)
    })

    it('should render update button', () => {
      const wrapper = mount(DataManager)
      const button = wrapper.findAll('el-button-stub')[1]
      expect(button.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load latest date on mount', async () => {
      const mockResponse = { latest_date: '2025-01-04' }
      vi.mocked(request.get).mockResolvedValue(mockResponse)

      const wrapper = mount(DataManager)
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/data/latest_date')
      expect(wrapper.vm.latestDate).toBe('2025-01-04')
    })

    it('should handle load error', async () => {
      vi.mocked(request.get).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(DataManager)
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('获取数据日期失败')
    })
  })

  describe('Download Functionality', () => {
    it('should create download task', async () => {
      vi.mocked(request.post).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(DataManager)
      await wrapper.vm.handleDownload()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/data/download', {
        start_date: '2015-01-01',
        end_date: null
      })
      expect(ElMessage.success).toHaveBeenCalledWith('下载任务已创建')
    })

    it('should handle download error', async () => {
      vi.mocked(request.post).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(DataManager)
      await wrapper.vm.handleDownload()
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('创建下载任务失败')
    })
  })

  describe('Update Functionality', () => {
    it('should create update task', async () => {
      vi.mocked(request.post).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(DataManager)
      await wrapper.vm.handleUpdate()
      await wrapper.vm.$nextTick()

      expect(request.post).toHaveBeenCalledWith('/api/data/update')
      expect(ElMessage.success).toHaveBeenCalledWith('更新任务已创建')
    })

    it('should handle update error', async () => {
      vi.mocked(request.post).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(DataManager)
      await wrapper.vm.handleUpdate()
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('创建更新任务失败')
    })
  })

  describe('Display', () => {
    it('should show latest date when available', async () => {
      const mockResponse = { latest_date: '2025-01-04' }
      vi.mocked(request.get).mockResolvedValue(mockResponse)

      const wrapper = mount(DataManager)
      await wrapper.vm.$nextTick()

      const dateElement = wrapper.find('strong')
      expect(dateElement.text()).toContain('2025-01-04')
    })

    it('should show "暂无数据" when no latest date', async () => {
      const mockResponse = { latest_date: null }
      vi.mocked(request.get).mockResolvedValue(mockResponse)

      const wrapper = mount(DataManager)
      await wrapper.vm.$nextTick()

      const dateElement = wrapper.find('strong')
      expect(dateElement.text()).toContain('暂无数据')
    })
  })
})
