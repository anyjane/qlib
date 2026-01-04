<template>
  <div class="agent-manager">
    <!-- 代理状态警告 -->
    <el-alert
      v-if="!primaryAgent || primaryAgent.status !== 'active'"
      title="警告：主用代理不可用"
      type="warning"
      description="所有交易操作将受到影响，请尽快修复主用代理或切换到可用代理"
      show-icon
      :closable="false"
      style="margin-bottom: 20px"
    >
    </el-alert>

    <el-card shadow="hover">
      <!-- 工具栏 -->
      <div class="toolbar">
        <el-button type="primary" icon="el-icon-plus" @click="handleAdd">
          添加代理
        </el-button>

        <el-button
          type="success"
          icon="el-icon-refresh"
          @click="loadAgentsStatus"
        >
          刷新状态
        </el-button>

        <span style="margin-left: 20px; color: #909399">
          心跳检测间隔：30秒
        </span>
      </div>

      <!-- 代理列表 -->
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="8" v-for="agent in agents" :key="agent.agent_id">
          <el-card class="agent-card" shadow="hover">
            <div slot="header" class="card-header">
              <span class="agent-name">
                {{ agent.agent_name }}
                <el-tag v-if="agent.is_primary" type="success" size="small" style="margin-left: 10px">
                  主用
                </el-tag>
              </span>

              <div class="header-actions">
                <el-button
                  size="small"
                  :type="agent.status === 'active' ? 'success' : 'danger'"
                  circle
                >
                  <i class="el-icon-video-camera-solid" v-if="agent.status === 'active'"></i>
                  <i class="el-icon-video-camera" v-else></i>
                </el-button>

                <el-dropdown @command="(cmd) => handleCardAction(cmd, agent)">
                  <el-button size="small" circle icon="el-icon-more"></el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="view">
                        <i class="el-icon-view"></i>
                        查看资产
                      </el-dropdown-item>
                      <el-dropdown-item command="edit">
                        <i class="el-icon-edit"></i>
                        编辑
                      </el-dropdown-item>
                      <el-dropdown-item command="setPrimary" v-if="!agent.is_primary">
                        <i class="el-icon-star-on"></i>
                        设为主用
                      </el-dropdown-item>
                      <el-dropdown-item command="delete">
                        <i class="el-icon-delete"></i>
                        删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>

            <div class="agent-info">
              <p><strong>代理ID：</strong>{{ agent.agent_id }}</p>
              <p><strong>URL：</strong>{{ agent.agent_url }}</p>
              <p><strong>状态：</strong>
                <el-tag :type="agent.status === 'active' ? 'success' : 'danger'" size="small">
                  {{ agent.status === 'active' ? '可用' : '不可用' }}
                </el-tag>
              </p>
              <p v-if="agent.last_heartbeat">
                <strong>最后心跳：</strong>{{ formatDate(agent.last_heartbeat) }}
              </p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 资产信息对话框 -->
    <el-dialog
      v-model="assetDialogVisible"
      title="代理资产信息"
      width="800px"
      v-loading="assetLoading"
    >
      <el-descriptions :column="2" border>
        <el-descriptions-item label="账号ID">
          {{ assetInfo.account_id || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="总资产">
          <span style="font-weight: bold; color: #409eff">
            ¥{{ assetInfo.total_assets?.toFixed(2) || '0.00' }}
          </span>
        </el-descriptions-item>

        <el-descriptions-item label="可用资金">
          <span style="font-weight: bold; color: #67c23a">
            ¥{{ assetInfo.available_cash?.toFixed(2) || '0.00' }}
          </span>
        </el-descriptions-item>

        <el-descriptions-item label="市值">
          ¥{{ assetInfo.market_value?.toFixed(2) || '0.00' }}
        </el-descriptions-item>

        <el-descriptions-item label="更新时间" :span="2">
          {{ formatDate(assetInfo.updated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 持仓列表 -->
      <div style="margin-top: 20px">
        <h3>持仓列表</h3>
        <el-table :data="assetInfo.positions" style="width: 100%">
          <el-table-column prop="code" label="股票代码" width="120"></el-table-column>

          <el-table-column prop="name" label="股票名称" width="150"></el-table-column>

          <el-table-column prop="quantity" label="持仓数量" width="100">
            <template #default="{ row }">
              {{ row.quantity?.toFixed(0) || '0' }}
            </template>
          </el-table-column>

          <el-table-column prop="cost_price" label="成本价" width="100">
            <template #default="{ row }">
              ¥{{ row.cost_price?.toFixed(2) || '0.00' }}
            </template>
          </el-table-column>

          <el-table-column prop="market_value" label="市值" width="120">
            <template #default="{ row }">
              ¥{{ row.market_value?.toFixed(2) || '0.00' }}
            </template>
          </el-table-column>

          <el-table-column prop="pnl" label="盈亏" width="100">
            <template #default="{ row }">
              <span :style="{ color: row.pnl >= 0 ? '#67c23a' : '#f56c6c' }">
                ¥{{ row.pnl?.toFixed(2) || '0.00' }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="pnl_percent" label="盈亏%" width="100">
            <template #default="{ row }">
              <span :style="{ color: row.pnl_percent >= 0 ? '#67c23a' : '#f56c6c' }">
                {{ row.pnl_percent?.toFixed(2) || '0.00' }}%
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="assetDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑代理对话框 -->
    <el-dialog
      v-model="agentDialogVisible"
      :title="isEditMode ? '编辑代理' : '添加代理'"
      width="500px"
    >
      <el-form :model="agentForm" label-width="100px">
        <el-form-item label="代理名称" required>
          <el-input v-model="agentForm.agent_name" placeholder="例如：主用代理"></el-input>
        </el-form-item>

        <el-form-item label="代理URL" required>
          <el-input
            v-model="agentForm.agent_url"
            placeholder="例如：http://localhost:9000"
          ></el-input>
        </el-form-item>

        <el-form-item label="代理Token" required>
          <el-input
            v-model="agentForm.agent_token"
            type="password"
            placeholder="请输入代理Token"
            show-password
          ></el-input>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="agentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAgent">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi } from '../api/agent'

export default {
  name: 'AgentManager',
  setup() {
    const agents = ref([])
    const primaryAgent = ref(null)
    const loading = ref(false)
    const heartbeatTimer = ref(null)

    // 对话框状态
    const assetDialogVisible = ref(false)
    const agentDialogVisible = ref(false)
    const assetLoading = ref(false)

    // 资产信息
    const assetInfo = ref({
      account_id: '',
      total_assets: 0,
      available_cash: 0,
      market_value: 0,
      positions: [],
      updated_at: null
    })

    // 代理表单
    const isEditMode = ref(false)
    const currentAgentId = ref(null)
    const agentForm = ref({
      agent_name: '',
      agent_url: '',
      agent_token: ''
    })

    // 加载代理状态
    const loadAgentsStatus = async () => {
      loading.value = true
      try {
        const data = await agentApi.getAgentsStatus()
        agents.value = data

        // 获取主用代理
        const primary = await agentApi.getPrimaryAgent()
        primaryAgent.value = primary
      } catch (error) {
        ElMessage.error('加载代理状态失败')
      } finally {
        loading.value = false
      }
    }

    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN')
    }

    // 卡片操作
    const handleCardAction = async (command, agent) => {
      switch (command) {
        case 'view':
          handleViewAsset(agent)
          break
        case 'edit':
          handleEdit(agent)
          break
        case 'setPrimary':
          handleSetPrimary(agent)
          break
        case 'delete':
          handleDelete(agent)
          break
      }
    }

    // 查看资产
    const handleViewAsset = async (agent) => {
      assetLoading.value = true
      assetDialogVisible.value = true

      try {
        const data = await agentApi.getAgentAssetInfo(agent.agent_id)
        assetInfo.value = data
      } catch (error) {
        ElMessage.error('获取资产信息失败')
        assetDialogVisible.value = false
      } finally {
        assetLoading.value = false
      }
    }

    // 添加代理
    const handleAdd = () => {
      isEditMode.value = false
      currentAgentId.value = null
      agentForm.value = {
        agent_name: '',
        agent_url: '',
        agent_token: ''
      }
      agentDialogVisible.value = true
    }

    // 编辑代理
    const handleEdit = (agent) => {
      isEditMode.value = true
      currentAgentId.value = agent.agent_id
      agentForm.value = {
        agent_name: agent.agent_name,
        agent_url: agent.agent_url,
        agent_token: agent.agent_token
      }
      agentDialogVisible.value = true
    }

    // 设置主用代理
    const handleSetPrimary = async (agent) => {
      try {
        await ElMessageBox.confirm(
          `确定要将 ${agent.agent_name} 设置为主用代理吗？`,
          '确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await agentApi.setPrimaryAgent(agent.agent_id)
        ElMessage.success('设置主用代理成功')
        loadAgentsStatus()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('设置主用代理失败')
        }
      }
    }

    // 删除代理
    const handleDelete = async (agent) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除代理 ${agent.agent_name} 吗？`,
          '警告',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await agentApi.deleteAgentConfig(agent.agent_id)
        ElMessage.success('删除代理成功')
        loadAgentsStatus()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除代理失败')
        }
      }
    }

    // 确认添加/编辑代理
    const confirmAgent = async () => {
      if (!agentForm.value.agent_name || !agentForm.value.agent_url || !agentForm.value.agent_token) {
        ElMessage.warning('请填写完整信息')
        return
      }

      loading.value = true
      try {
        if (isEditMode.value) {
          await agentApi.updateAgentConfig(currentAgentId.value, agentForm.value)
          ElMessage.success('更新代理成功')
        } else {
          await agentApi.createAgentConfig(agentForm.value)
          ElMessage.success('添加代理成功')
        }

        agentDialogVisible.value = false
        loadAgentsStatus()
      } catch (error) {
        ElMessage.error(isEditMode.value ? '更新代理失败' : '添加代理失败')
      } finally {
        loading.value = false
      }
    }

    // 心跳检测
    const startHeartbeat = () => {
      heartbeatTimer.value = setInterval(() => {
        loadAgentsStatus()
      }, 30000) // 每30秒检测一次
    }

    const stopHeartbeat = () => {
      if (heartbeatTimer.value) {
        clearInterval(heartbeatTimer.value)
      }
    }

    // 生命周期
    onMounted(() => {
      loadAgentsStatus()
      startHeartbeat()
    })

    onUnmounted(() => {
      stopHeartbeat()
    })

    return {
      agents,
      primaryAgent,
      loading,
      assetDialogVisible,
      agentDialogVisible,
      assetLoading,
      assetInfo,
      isEditMode,
      agentForm,
      loadAgentsStatus,
      formatDate,
      handleCardAction,
      handleAdd,
      confirmAgent
    }
  }
}
</script>

<style scoped>
.agent-manager {
  padding: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-card {
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.agent-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-name {
  font-size: 16px;
  font-weight: bold;
}

.header-actions {
  display: flex;
  gap: 5px;
}

.agent-info p {
  margin: 8px 0;
  color: #606266;
}

.agent-info strong {
  color: #303133;
}
</style>
