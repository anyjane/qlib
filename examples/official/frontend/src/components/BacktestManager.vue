<template>
  <div class="backtest-manager">
    <el-card shadow="hover">
      <div class="header">
        <h2>量化回测</h2>
        <el-button-group>
          <el-button type="primary" icon="el-icon-video-play" @click="showConfigDialog = true">
            创建回测
          </el-button>
          <el-button type="success" icon="el-icon-setting" @click="goToConfig">
            参数配置
          </el-button>
        </el-button-group>
      </div>

      <el-divider></el-divider>

      <!-- 回测配置对话框 -->
      <el-dialog v-model="showConfigDialog" title="创建回测任务" width="500px">
        <el-form :model="config" label-width="100px">
          <el-form-item label="市场">
            <el-select v-model="config.market" placeholder="选择市场" style="width: 100%">
              <el-option 
                v-for="m in markets" 
                :key="m.id" 
                :label="m.name" 
                :value="m.id"
              >
                <span>{{ m.name }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 10px">{{ m.description }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="训练开始">
            <el-date-picker
              v-model="config.train_start"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            ></el-date-picker>
          </el-form-item>
          
          <el-form-item label="训练结束">
            <el-date-picker
              v-model="config.train_end"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            ></el-date-picker>
          </el-form-item>
          
          <el-form-item label="回测开始">
            <el-date-picker
              v-model="config.test_start"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            ></el-date-picker>
          </el-form-item>
          
          <el-form-item label="回测结束">
            <el-date-picker
              v-model="config.test_end"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            ></el-date-picker>
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="showConfigDialog = false">取消</el-button>
          <el-button type="primary" @click="createBacktest" :loading="creating">创建</el-button>
        </template>
      </el-dialog>

      <!-- 回测任务列表 -->
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="任务ID" width="280">
          <template #default="{ row }">
            <span style="font-family: monospace; font-size: 12px">{{ row.id }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="market" label="市场" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.market }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="train_period" label="训练周期" width="200"></el-table-column>
        
        <el-table-column prop="test_period" label="回测周期" width="200"></el-table-column>
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewResults(row)"
              :disabled="row.status !== 'completed'"
            >
              查看结果
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteTask(row)"
              :disabled="row.status === 'running'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 结果对话框 -->
      <el-dialog v-model="showResultDialog" title="回测结果" width="600px">
        <div v-if="currentResults" class="results-container">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="年化收益率（无成本）">
              <span :class="getValueClass(currentResults.annual_return_no_cost)">
                {{ formatPercent(currentResults.annual_return_no_cost) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="夏普比率（无成本）">
              {{ formatNumber(currentResults.sharpe_ratio_no_cost) }}
            </el-descriptions-item>
            <el-descriptions-item label="年化收益率（含成本）">
              <span :class="getValueClass(currentResults.annual_return_with_cost)">
                {{ formatPercent(currentResults.annual_return_with_cost) }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="夏普比率（含成本）">
              {{ formatNumber(currentResults.sharpe_ratio_with_cost) }}
            </el-descriptions-item>
            <el-descriptions-item label="最大回撤（无成本）">
              <span class="negative">{{ formatPercent(currentResults.max_drawdown_no_cost) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="最大回撤（含成本）">
              <span class="negative">{{ formatPercent(currentResults.max_drawdown_with_cost) }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div v-else class="no-results">
          <el-empty description="暂无结果"></el-empty>
        </div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'

const router = useRouter()

export default {
  name: 'BacktestManager',
  setup() {
    const tasks = ref([])
    const markets = ref([])
    const loading = ref(false)
    const creating = ref(false)
    const showConfigDialog = ref(false)
    const showResultDialog = ref(false)
    const currentResults = ref(null)
    
    const config = ref({
      market: 'all',
      train_start: '2024-01-01',
      train_end: '2024-12-31',
      test_start: '2025-01-01',
      test_end: '2025-06-30'
    })

    const loadMarkets = async () => {
      try {
        const data = await request.get('/api/backtest/markets')
        markets.value = data.markets || []
      } catch (error) {
        console.error('Failed to load markets:', error)
      }
    }

    const loadTasks = async () => {
      loading.value = true
      try {
        const data = await request.get('/api/backtest/tasks')
        tasks.value = data || []
      } catch (error) {
        ElMessage.error('加载回测任务失败')
      } finally {
        loading.value = false
      }
    }

    const createBacktest = async () => {
      creating.value = true
      try {
        await request.post('/api/backtest/', config.value)
        ElMessage.success('回测任务已创建')
        showConfigDialog.value = false
        await loadTasks()
      } catch (error) {
        ElMessage.error('创建回测任务失败')
      } finally {
        creating.value = false
      }
    }

    const viewResults = async (task) => {
      try {
        const data = await request.get(`/api/backtest/tasks/${task.id}/results`)
        currentResults.value = data
        showResultDialog.value = true
      } catch (error) {
        ElMessage.error('获取回测结果失败')
      }
    }

    const deleteTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要删除该回测任务吗？', '确认删除')
        await request.delete(`/api/backtest/tasks/${task.id}`)
        ElMessage.success('删除成功')
        await loadTasks()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    const goToConfig = () => {
      router.push('/backtest/config')
    }

    const getStatusType = (status) => {
      const types = {
        pending: 'info',
        running: 'warning',
        completed: 'success',
        failed: 'danger'
      }
      return types[status] || 'info'
    }

    const getStatusText = (status) => {
      const texts = {
        pending: '等待中',
        running: '运行中',
        completed: '已完成',
        failed: '失败'
      }
      return texts[status] || status
    }

    const getValueClass = (value) => {
      if (value === null || value === undefined) return ''
      return value >= 0 ? 'positive' : 'negative'
    }

    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-'
      return (value * 100).toFixed(2) + '%'
    }

    const formatNumber = (value) => {
      if (value === null || value === undefined) return '-'
      return value.toFixed(4)
    }

    onMounted(() => {
      loadMarkets()
      loadTasks()
    })

    return {
      tasks,
      markets,
      loading,
      creating,
      config,
      showConfigDialog,
      showResultDialog,
      currentResults,
      createBacktest,
      viewResults,
      deleteTask,
      goToConfig,
      getStatusType,
      getStatusText,
      getValueClass,
      formatPercent,
      formatNumber
    }
  }
}
</script>

<style scoped>
.backtest-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.results-container {
  padding: 10px 0;
}

.positive {
  color: #67c23a;
  font-weight: bold;
}

.negative {
  color: #f56c6c;
  font-weight: bold;
}

.no-results {
  padding: 40px 0;
}
</style>
