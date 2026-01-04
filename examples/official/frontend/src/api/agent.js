import request from '../utils/request'

// Agent APIs
export const agentApi = {
  // 获取所有代理配置
  getAgentConfigs() {
    return request.get('/api/agent/config')
  },

  // 获取指定代理配置
  getAgentConfig(agentId) {
    return request.get(`/api/agent/config/${agentId}`)
  },

  // 创建代理配置
  createAgentConfig(data) {
    return request.post('/api/agent/config', data)
  },

  // 更新代理配置
  updateAgentConfig(agentId, data) {
    return request.put(`/api/agent/config/${agentId}`, data)
  },

  // 删除代理配置
  deleteAgentConfig(agentId) {
    return request.delete(`/api/agent/config/${agentId}`)
  },

  // 设置主用代理
  setPrimaryAgent(agentId) {
    return request.put(`/api/agent/config/${agentId}/primary`)
  },

  // 获取当前主用代理
  getPrimaryAgent() {
    return request.get('/api/agent/primary')
  },

  // 获取所有代理状态
  getAgentsStatus() {
    return request.get('/api/agent/status')
  },

  // 获取代理资产信息
  getAgentAssetInfo(agentId) {
    return request.get(`/api/agent/asset/${agentId}`)
  },

  // 提交交易订单
  submitOrders(action, stocks) {
    return request.post('/api/agent/orders', { stocks }, {
      params: { action }
    })
  },

  // 查询代理订单
  getAgentOrders(orderId = null, limit = 100) {
    return request.get('/api/agent/orders', {
      params: { order_id: orderId, limit }
    })
  },

  // 查询代理持仓
  getAgentPositions(agentId) {
    return request.get(`/api/agent/positions/${agentId}`)
  },

  // 心跳检测
  heartbeatAgent(agentId) {
    return request.post(`/api/agent/heartbeat/${agentId}`)
  }
}
