/**
 * AgentManager 组件测试
 * 测试代理管理组件的渲染和交互
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import AgentManager from '@/components/AgentManager.vue'
import { agentApi } from '@/api/agent'

// Mock API
vi.mock('@/api/agent', () => ({
  agentApi: {
    getAgentsStatus: vi.fn(),
    getPrimaryAgent: vi.fn(),
    getAgentAssetInfo: vi.fn(),
    setPrimaryAgent: vi.fn(),
    deleteAgentConfig: vi.fn(),
    createAgentConfig: vi.fn(),
    updateAgentConfig: vi.fn(),
  },
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(),
  },
}))

describe('AgentManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render correctly', () => {
      const wrapper = mount(AgentManager)
      expect(wrapper.find('.agent-manager').exists()).toBe(true)
    })

    it('should display toolbar buttons', () => {
      const wrapper = mount(AgentManager)
      const buttons = wrapper.findAll('el-button-stub')

      expect(buttons.length).toBeGreaterThan(0)
    })

    it('should render agent cards container', () => {
      const wrapper = mount(AgentManager)
      const row = wrapper.findComponent('el-row-stub')

      expect(row.exists()).toBe(true)
    })
  })

  describe('Data Loading', () => {
    it('should load agents status on mount', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          agent_url: 'http://localhost:9000',
          agent_token: 'test_token',
          is_primary: true,
          status: 'active',
          last_heartbeat: new Date(),
          created_at: new Date(),
          updated_at: new Date()
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      expect(agentApi.getAgentsStatus).toHaveBeenCalled()
      expect(agentApi.getPrimaryAgent).toHaveBeenCalled()
    })

    it('should show alert when primary agent unavailable', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          agent_url: 'http://localhost:9000',
          is_primary: true,
          status: 'unavailable'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      const alert = wrapper.findComponent('el-alert-stub')
      expect(alert.exists()).toBe(true)
    })
  })

  describe('Card Display', () => {
    it('should display agent information', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          agent_url: 'http://localhost:9000',
          is_primary: true,
          status: 'active'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      const agents = wrapper.vm.agents
      expect(agents[0].agent_name).toBe('Primary Agent')
      expect(agents[0].agent_url).toBe('http://localhost:9000')
    })

    it('should show primary badge for primary agent', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          is_primary: true,
          status: 'active'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      const agents = wrapper.vm.agents
      expect(agents[0].is_primary).toBe(true)
    })
  })

  describe('View Asset', () => {
    it('should load agent asset info', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          is_primary: true,
          status: 'active'
        }
      ]

      const mockAssetInfo = {
        account_id: '12345',
        total_assets: 100000,
        available_cash: 50000,
        market_value: 50000,
        positions: []
      }

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])
      vi.mocked(agentApi.getAgentAssetInfo).mockResolvedValue(mockAssetInfo)

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      await wrapper.vm.handleViewAsset(mockAgents[0])
      await wrapper.vm.$nextTick()

      expect(agentApi.getAgentAssetInfo).toHaveBeenCalledWith('agent_001')
      expect(wrapper.vm.assetDialogVisible).toBe(true)
    })
  })

  describe('Set Primary', () => {
    it('should set primary agent with confirmation', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          is_primary: false,
          status: 'active'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(agentApi.setPrimaryAgent).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      await wrapper.vm.handleSetPrimary(mockAgents[0])
      await wrapper.vm.$nextTick()

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(agentApi.setPrimaryAgent).toHaveBeenCalledWith('agent_001')
    })
  })

  describe('Delete Agent', () => {
    it('should delete agent with confirmation', async () => {
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          is_primary: false,
          status: 'active'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm')
      vi.mocked(agentApi.deleteAgentConfig).mockResolvedValue({})
      vi.mocked(ElMessage.success).mockReturnValue({})

      const wrapper = mount(AgentManager)
      await wrapper.vm.$nextTick()

      await wrapper.vm.handleDelete(mockAgents[0])
      await wrapper.vm.$nextTick()

      expect(ElMessageBox.confirm).toHaveBeenCalled()
      expect(agentApi.deleteAgentConfig).toHaveBeenCalledWith('agent_001')
    })
  })

  describe('Heartbeat', () => {
    it('should start heartbeat on mount', () => {
      const setIntervalSpy = vi.spyOn(global, 'setInterval')
      const mockAgents = [
        {
          agent_id: 'agent_001',
          agent_name: 'Primary Agent',
          is_primary: true,
          status: 'active'
        }
      ]

      vi.mocked(agentApi.getAgentsStatus).mockResolvedValue(mockAgents)
      vi.mocked(agentApi.getPrimaryAgent).mockResolvedValue(mockAgents[0])

      mount(AgentManager)

      expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 30000)
      setIntervalSpy.mockRestore()
    })
  })
})
