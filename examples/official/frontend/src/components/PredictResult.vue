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
      } catch (error) {
        ElMessage.error('加载预测结果失败')
      } finally {
        loading.value = false
      }
    }

    const handlePredict = async () => {
      try {
        await request.post('/api/predict/', {
          predict_date: filterDate.value
        })
        ElMessage.success('预测任务已创建')
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
      loadPredictions,
      handlePredict
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

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
