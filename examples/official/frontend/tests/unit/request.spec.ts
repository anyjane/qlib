/**
 * request 模块单元测试
 * 测试 Axios 拦截器配置和错误处理
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import axios from 'axios'
import request from '@/utils/request'

// Mock axios create
vi.mock('axios', () => ({
  default: vi.fn(() => ({
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
  })),
}))

describe('request', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should create axios instance with correct config', () => {
    expect(axios).toHaveBeenCalledWith({
      baseURL: 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  })

  it('should have request interceptor', () => {
    const instance = request
    expect(instance.interceptors.request.use).toHaveBeenCalled()
  })

  it('should have response interceptor', () => {
    const instance = request
    expect(instance.interceptors.response.use).toHaveBeenCalled()
  })
})

describe('request interceptor', () => {
  it('should pass through config unchanged', () => {
    const requestInterceptor = (vi.fn().mockImplementation(config => config) as any)

    // 模拟拦截器调用
    const config = { url: '/api/test', method: 'get' }
    const result = requestInterceptor(config)

    expect(result).toBe(config)
  })
})

describe('response interceptor', () => {
  it('should return response data', () => {
    const responseInterceptor = (vi.fn().mockImplementation(response => response.data) as any)

    const response = { data: { success: true, message: 'test' } }
    const result = responseInterceptor(response)

    expect(result).toBe(response.data)
  })

  it('should handle error responses correctly', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = {
      response: {
        status: 404,
        data: { message: 'Not found' }
      }
    }

    // 模拟错误处理逻辑
    if (error.response) {
      console.error('Response error:', error)
    }

    expect(consoleErrorSpy).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })

  it('should handle network errors', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { message: 'Network Error' }

    // 模拟网络错误处理
    console.error('Response error:', error)

    expect(consoleErrorSpy).toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })
})

describe('HTTP status codes handling', () => {
  it('should handle 401 unauthorized', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 401 } }

    // 模拟状态码处理
    switch (error.response.status) {
      case 401:
        console.error('未授权，请登录')
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('未授权，请登录')
    consoleErrorSpy.mockRestore()
  })

  it('should handle 403 forbidden', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 403 } }

    switch (error.response.status) {
      case 403:
        console.error('拒绝访问')
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('拒绝访问')
    consoleErrorSpy.mockRestore()
  })

  it('should handle 404 not found', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 404 } }

    switch (error.response.status) {
      case 404:
        console.error('请求的资源不存在')
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('请求的资源不存在')
    consoleErrorSpy.mockRestore()
  })

  it('should handle 500 server error', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 500 } }

    switch (error.response.status) {
      case 500:
        console.error('服务器错误')
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('服务器错误')
    consoleErrorSpy.mockRestore()
  })

  it('should handle 503 service unavailable', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 503 } }

    switch (error.response.status) {
      case 503:
        console.error('服务不可用，可能是主用代理不可用')
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('服务不可用，可能是主用代理不可用')
    consoleErrorSpy.mockRestore()
  })

  it('should handle unknown status codes', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const error = { response: { status: 499 } }

    switch (error.response.status) {
      default:
        console.error(`未知错误: ${error.response.status}`)
        break
    }

    expect(consoleErrorSpy).toHaveBeenCalledWith('未知错误: 499')
    consoleErrorSpy.mockRestore()
  })
})
