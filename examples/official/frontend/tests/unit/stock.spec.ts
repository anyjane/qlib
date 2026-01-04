/**
 * stock API 模块单元测试
 * 测试股票相关的 API 调用函数
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { stockApi } from '@/api/stock'

// Mock request 模块
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}))

import request from '@/utils/request'

describe('stockApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getStocks', () => {
    it('should call GET /api/stocks/ with params', () => {
      const params = { enabled_only: true }
      stockApi.getStocks(params)

      expect(request.get).toHaveBeenCalledWith('/api/stocks/', { params })
    })

    it('should call GET /api/stocks/ without params', () => {
      stockApi.getStocks()

      expect(request.get).toHaveBeenCalledWith('/api/stocks/', {})
    })
  })

  describe('exportStocks', () => {
    it('should call GET /api/stocks/export with CSV format', () => {
      stockApi.exportStocks('csv')

      expect(request.get).toHaveBeenCalledWith('/api/stocks/export', {
        params: { format: 'csv' },
        responseType: 'blob'
      })
    })

    it('should call GET /api/stocks/export with Excel format', () => {
      stockApi.exportStocks('excel')

      expect(request.get).toHaveBeenCalledWith('/api/stocks/export', {
        params: { format: 'excel' },
        responseType: 'blob'
      })
    })

    it('should default to CSV format if no format provided', () => {
      stockApi.exportStocks()

      expect(request.get).toHaveBeenCalledWith('/api/stocks/export', {
        params: { format: 'csv' },
        responseType: 'blob'
      })
    })
  })

  describe('importStocks', () => {
    it('should call POST /api/stocks/import with FormData', () => {
      const mockFile = new File(['test'], 'test.csv')
      stockApi.importStocks(mockFile)

      expect(request.post).toHaveBeenCalledWith(
        '/api/stocks/import',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )
    })
  })

  describe('initializeStocks', () => {
    it('should call POST /api/stocks/initialize', () => {
      stockApi.initializeStocks()

      expect(request.post).toHaveBeenCalledWith('/api/stocks/initialize')
    })
  })

  describe('createStock', () => {
    it('should call POST /api/stocks/ with stock data', () => {
      const stockData = {
        code: 'sh600000',
        name: '浦发银行',
        is_a500: false
      }
      stockApi.createStock(stockData)

      expect(request.post).toHaveBeenCalledWith('/api/stocks/', stockData)
    })
  })

  describe('deleteStock', () => {
    it('should call DELETE /api/stocks/{code}', () => {
      const code = 'sh600000'
      stockApi.deleteStock(code)

      expect(request.delete).toHaveBeenCalledWith(`/api/stocks/${code}`)
    })
  })

  describe('updateStock', () => {
    it('should call PUT /api/stocks/{code} with update data', () => {
      const code = 'sh600000'
      const updateData = { name: '浦发银行（更新）' }
      stockApi.updateStock(code, updateData)

      expect(request.put).toHaveBeenCalledWith(`/api/stocks/${code}`, updateData)
    })
  })

  describe('enableStock', () => {
    it('should call PUT /api/stocks/{code}/enable with enabled=true', () => {
      const code = 'sh600000'
      stockApi.enableStock(code, true)

      expect(request.put).toHaveBeenCalledWith(
        `/api/stocks/${code}/enable`,
        null,
        { params: { enabled: true } }
      )
    })

    it('should call PUT /api/stocks/{code}/enable with enabled=false', () => {
      const code = 'sh600000'
      stockApi.enableStock(code, false)

      expect(request.put).toHaveBeenCalledWith(
        `/api/stocks/${code}/enable`,
        null,
        { params: { enabled: false } }
      )
    })
  })

  describe('batchOperation', () => {
    it('should call POST /api/stocks/batch with operation and codes', () => {
      const operation = 'enable'
      const codes = ['sh600000', 'sh600036']
      stockApi.batchOperation(operation, codes)

      expect(request.post).toHaveBeenCalledWith('/api/stocks/batch', { codes }, {
        params: { operation }
      })
    })

    it('should handle delete operation', () => {
      const codes = ['sh600000']
      stockApi.batchOperation('delete', codes)

      expect(request.post).toHaveBeenCalledWith('/api/stocks/batch', { codes }, {
        params: { operation: 'delete' }
      })
    })

    it('should handle disable operation', () => {
      const codes = ['sh600000']
      stockApi.batchOperation('disable', codes)

      expect(request.post).toHaveBeenCalledWith('/api/stocks/batch', { codes }, {
        params: { operation: 'disable' }
      })
    })
  })
})
