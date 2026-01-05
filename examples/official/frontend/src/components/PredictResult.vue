<template>
  <div class="predict-result">
    <el-card shadow="hover">
      <div class="header">
        <h2>预测结果</h2>
        <el-button type="primary" icon="el-icon-video-play" @click="handlePredict">
          执行预测
        </el-button>
      </div>

      <el-divider></el-divider>

      <!-- 日期信息展示 -->
      <div class="prediction-info" v-if="predictDate || dataDate">
        <el-tag v-if="predictDate" type="info" effect="plain">
          <i class="el-icon-date"></i>
          预测日期: {{ predictDate }}
        </el-tag>
        <el-tag v-if="dataDate" type="success" effect="plain">
          <i class="el-icon-date"></i>
          数据日期: {{ dataDate }}
        </el-tag>
      </div>

      <!-- 日期选择对话框 -->
      <el-dialog v-model="showDateDialog" title="选择预测日期" width="400px">
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          :default-value="new Date()"
          style="width: 100%"
        ></el-date-picker>
        <template #footer>
          <el-button @click="showDateDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmPredict">确认预测</el-button>
        </template>
      </el-dialog>

      <!-- 筛选条件 -->
      <div class="filters">
        <el-date-picker
          v-model="filterDate"
          type="date"
          placeholder="选择预测日期"
          value-format="YYYY-MM-DD"
        ></el-date-picker>

        <el-select v-model="filterType" placeholder="筛选类型">
          <el-option label="全部" value="all"></el-option>
          <el-option label="仅持仓" value="held"></el-option>
          <el-option label="仅非持仓" value="not_held"></el-option>
        </el-select>

        <el-button icon="el-icon-search" @click="loadPredictions">查询</el-button>
      </div>

      <!-- 预测结果表格 -->
      <el-table
        :data="predictions"
        v-loading="loading"
        style="width: 100%; margin-top: 20px"
      >
        <el-table-column prop="date" label="预测日期" width="120"></el-table-column>

        <el-table-column prop="code" label="股票代码" width="120"></el-table-column>

        <el-table-column prop="name" label="股票名称" width="150"></el-table-column>

        <el-table-column prop="score" label="预测得分" width="100" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.score >= 0.5 ? '#67c23a' : '#f56c6c' }">
              {{ row.score?.toFixed(4) || '0.0000' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="rank" label="排名" width="80" sortable></el-table-column>

        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_held ? 'success' : 'info'" size="small">
              {{ row.is_held ? '持仓' : '非持仓' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

export default {
  name: 'PredictResult',
  setup() {
    const predictions = ref([])
    const loading = ref(false)
    const filterDate = ref('')
    const filterType = ref('all')
    const predictDate = ref('')
    const dataDate = ref('')
    const showDateDialog = ref(false)
    const selectedDate = ref('')

    const loadPredictions = async () => {
      loading.value = true
      try {
        const data = await request.get('/api/predict/results', {
          params: {
            date: filterDate.value,
            filter_type: filterType.value,
            limit: 100
          }
        })
        predictions.value = data

        // 获取预测日期和数据日期
        if (data.length > 0) {
          predictDate.value = data[0].date || ''
          dataDate.value = data[0].data_date || ''
        } else {
          predictDate.value = ''
          dataDate.value = ''
        }
      } catch (error) {
        ElMessage.error('加载预测结果失败')
        predictDate.value = ''
        dataDate.value = ''
      } finally {
        loading.value = false
      }
    }

    const handlePredict = async () => {
      // 打开日期选择对话框，默认使用当前日期
      selectedDate.value = new Date().toISOString().split('T')[0]
      showDateDialog.value = true
    }

    const confirmPredict = async () => {
      if (!selectedDate.value) {
        ElMessage.warning('请选择预测日期')
        return
      }

      try {
        await request.post('/api/predict/', null, {
          params: { predict_date: selectedDate.value }
        })
        ElMessage.success('预测任务已创建')
        showDateDialog.value = false

        // 自动加载新的预测结果
        filterDate.value = selectedDate.value
        await loadPredictions()
      } catch (error) {
        ElMessage.error('创建预测任务失败')
      }
    }

    onMounted(() => {
      loadPredictions()
    })

    return {
      predictions,
      loading,
      filterDate,
      filterType,
      predictDate,
      dataDate,
      showDateDialog,
      selectedDate,
      loadPredictions,
      handlePredict,
      confirmPredict
    }
  }
}
</script>

<style scoped>
.predict-result {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prediction-info {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
