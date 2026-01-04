import request from '../utils/request'

// Stock APIs
export const stockApi = {
  // 获取股票列表
  getStocks(params) {
    return request.get('/api/stocks/', { params })
  },

  // 导出股票列表
  exportStocks(format = 'csv') {
    return request.get('/api/stocks/export', {
      params: { format },
      responseType: 'blob'
    })
  },

  // 导入股票列表
  importStocks(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/api/stocks/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 重新初始化股票列表
  initializeStocks() {
    return request.post('/api/stocks/initialize')
  },

  // 添加股票
  createStock(data) {
    return request.post('/api/stocks/', data)
  },

  // 删除股票
  deleteStock(code) {
    return request.delete(`/api/stocks/${code}`)
  },

  // 更新股票
  updateStock(code, data) {
    return request.put(`/api/stocks/${code}`, data)
  },

  // 启用/禁用股票
  enableStock(code, enabled) {
    return request.put(`/api/stocks/${code}/enable`, null, {
      params: { enabled }
    })
  },

  // 批量操作
  batchOperation(operation, codes) {
    return request.post('/api/stocks/batch', { codes }, {
      params: { operation }
    })
  }
}
