/**
 * LogManager 组件测试
 * 测试日志管理组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import LogManager from '@/components/LogManager.vue'

// Mock request
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
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

describe('LogManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(LogManager)
      expect(wrapper.find('.log-manager').exists()).toBe(true)
    })

    it('should display header', () => {
      const wrapper = mount(LogManager)
      const header = wrapper.find('h2')
      expect(header.text()).toBe('日志管理')
    })

    it('should render logs table', () => {
      const wrapper = mount(LogManager)
      const table = wrapper.findComponent('el-table-stub')

      expect(table.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load logs on mount', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date()
        },
        {
          filename: 'error.log',
          size: 2048,
          modified: new Date()
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockLogs)

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/logs/')
      expect(wrapper.vm.logs).toEqual(mockLogs)
    })

    it('should handle load error', async () => {
      vi.mocked(request.get).mockRejectedValue(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('加载日志列表失败')
    })
  })

  describe('Size Formatting', () => {
    it('should format bytes correctly', () => {
      const wrapper = mount(LogManager)

      expect(wrapper.vm.formatSize(0)).toBe('0 B')
      expect(wrapper.vm.formatSize(1024)).toBe('1.00 KB')
      expect(wrapper.vm.formatSize(1048576)).toBe('1.00 MB')
      expect(wrapper.vm.formatSize(1073741824)).toBe('1.00 GB')
    })

    it('should handle edge cases', () => {
      const wrapper = mount(LogManager)

      expect(wrapper.vm.formatSize(500)).toBe('0.49 KB')
      expect(wrapper.vm.formatSize(1500)).toBe('1.46 KB')
    })
  })

  describe('Date Formatting', () => {
    it('should format date correctly', () => {
      const wrapper = mount(LogManager)
      const date = new Date('2025-01-04T10:30:00')

      const formattedDate = wrapper.vm.formatDate(date)

      expect(typeof formattedDate).toBe('string')
      expect(formattedDate).toContain('2025')
    })
  })

  describe('Download Functionality', () => {
    it('should download log file', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date()
        }
      ]

      const mockBlob = new Blob(['test content'], { type: 'text/plain' })
      vi.mocked(request.get).mockResolvedValue(mockBlob)

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      // Mock URL and link
      const mockURL = { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }
      vi.stubGlobal('URL', mockURL)

      const mockCreateElement = vi.fn(() => ({
        href: '',
        download: '',
        click: vi.fn()
      }))
      vi.stubGlobal('document', { createElement: mockCreateElement })

      await wrapper.vm.handleDownload('app.log')
      await wrapper.vm.$nextTick()

      expect(request.get).toHaveBeenCalledWith('/api/logs/download/app.log', {
        responseType: 'blob'
      })
    })

    it('should handle download error', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date()
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockLogs)
      vi.mocked(request.get).mockRejectedValueOnce(new Error('Failed'))
      vi.mocked(ElMessage.error).mockReturnValue({})

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      await wrapper.vm.handleDownload('app.log')
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('下载失败')
    })
  })

  describe('Table Display', () => {
    it('should display log filename', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date()
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockLogs)

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      const logs = wrapper.vm.logs
      expect(logs[0].filename).toBe('app.log')
    })

    it('should display formatted size', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date()
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockLogs)

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formatSize(1024)).toContain('KB')
    })

    it('should display formatted date', async () => {
      const mockLogs = [
        {
          filename: 'app.log',
          size: 1024,
          modified: new Date('2025-01-04')
        }
      ]

      vi.mocked(request.get).mockResolvedValue(mockLogs)

      const wrapper = mount(LogManager)
      await wrapper.vm.$nextTick()

      const formattedDate = wrapper.vm.formatDate(mockLogs[0].modified)
      expect(typeof formattedDate).toBe('string')
    })
  })
})
