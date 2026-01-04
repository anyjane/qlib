/**
 * agent API 模块单元测试
 * 测试代理相关的 API 调用函数
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { agentApi } from '@/api/agent'

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

describe('agentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAgentConfigs', () => {
    it('should call GET /api/agent/config', () => {
      agentApi.getAgentConfigs()

      expect(request.get).toHaveBeenCalledWith('/api/agent/config')
    })
  })

  describe('getAgentConfig', () => {
    it('should call GET /api/agent/config/{agentId}', () => {
      const agentId = 'agent_001'
      agentApi.getAgentConfig(agentId)

      expect(request.get).toHaveBeenCalledWith(`/api/agent/config/${agentId}`)
    })
  })

  describe('createAgentConfig', () => {
    it('should call POST /api/agent/config with agent data', () => {
      const agentData = {
        agent_url: 'http://localhost:9000',
        agent_token: 'test_token',
        agent_name: 'Test Agent'
      }
      agentApi.createAgentConfig(agentData)

      expect(request.post).toHaveBeenCalledWith('/api/agent/config', agentData)
    })
  })

  describe('updateAgentConfig', () => {
    it('should call PUT /api/agent/config/{agentId} with update data', () => {
      const agentId = 'agent_001'
      const updateData = { agent_name: 'Updated Agent' }
      agentApi.updateAgentConfig(agentId, updateData)

      expect(request.put).toHaveBeenCalledWith(`/api/agent/config/${agentId}`, updateData)
    })
  })

  describe('deleteAgentConfig', () => {
    it('should call DELETE /api/agent/config/{agentId}', () => {
      const agentId = 'agent_001'
      agentApi.deleteAgentConfig(agentId)

      expect(request.delete).toHaveBeenCalledWith(`/api/agent/config/${agentId}`)
    })
  })

  describe('setPrimaryAgent', () => {
    it('should call PUT /api/agent/config/{agentId}/primary', () => {
      const agentId = 'agent_001'
      agentApi.setPrimaryAgent(agentId)

      expect(request.put).toHaveBeenCalledWith(`/api/agent/config/${agentId}/primary`)
    })
  })

  describe('getPrimaryAgent', () => {
    it('should call GET /api/agent/primary', () => {
      agentApi.getPrimaryAgent()

      expect(request.get).toHaveBeenCalledWith('/api/agent/primary')
    })
  })

  describe('getAgentsStatus', () => {
    it('should call GET /api/agent/status', () => {
      agentApi.getAgentsStatus()

      expect(request.get).toHaveBeenCalledWith('/api/agent/status')
    })
  })

  describe('getAgentAssetInfo', () => {
    it('should call GET /api/agent/asset/{agentId}', () => {
      const agentId = 'agent_001'
      agentApi.getAgentAssetInfo(agentId)

      expect(request.get).toHaveBeenCalledWith(`/api/agent/asset/${agentId}`)
    })
  })

  describe('submitOrders', () => {
    it('should call POST /api/agent/orders with action and stocks', () => {
      const action = 'buy'
      const stocks = [
        { code: 'sh600000', quantity: 100, price: 10.50 }
      ]
      agentApi.submitOrders(action, stocks)

      expect(request.post).toHaveBeenCalledWith('/api/agent/orders', { stocks }, {
        params: { action }
      })
    })

    it('should handle sell action', () => {
      const stocks = [{ code: 'sh600000', quantity: 100, price: 10.50 }]
      agentApi.submitOrders('sell', stocks)

      expect(request.post).toHaveBeenCalledWith('/api/agent/orders', { stocks }, {
        params: { action: 'sell' }
      })
    })

    it('should handle cancel action', () => {
      const orders = [{ order_id: 'order_001' }]
      agentApi.submitOrders('cancel', orders)

      expect(request.post).toHaveBeenCalledWith('/api/agent/orders', { stocks: orders }, {
        params: { action: 'cancel' }
      })
    })
  })

  describe('getAgentOrders', () => {
    it('should call GET /api/agent/orders with default params', () => {
      agentApi.getAgentOrders()

      expect(request.get).toHaveBeenCalledWith('/api/agent/orders', {
        params: { order_id: null, limit: 100 }
      })
    })

    it('should call GET /api/agent/orders with custom params', () => {
      const orderId = 'order_001'
      const limit = 50
      agentApi.getAgentOrders(orderId, limit)

      expect(request.get).toHaveBeenCalledWith('/api/agent/orders', {
        params: { order_id: orderId, limit }
      })
    })

    it('should call GET /api/agent/orders with orderId only', () => {
      agentApi.getAgentOrders('order_001')

      expect(request.get).toHaveBeenCalledWith('/api/agent/orders', {
        params: { order_id: 'order_001', limit: 100 }
      })
    })
  })

  describe('getAgentPositions', () => {
    it('should call GET /api/agent/positions/{agentId}', () => {
      const agentId = 'agent_001'
      agentApi.getAgentPositions(agentId)

      expect(request.get).toHaveBeenCalledWith(`/api/agent/positions/${agentId}`)
    })
  })

  describe('heartbeatAgent', () => {
    it('should call POST /api/agent/heartbeat/{agentId}', () => {
      const agentId = 'agent_001'
      agentApi.heartbeatAgent(agentId)

      expect(request.post).toHaveBeenCalledWith(`/api/agent/heartbeat/${agentId}`)
    })
  })
})
