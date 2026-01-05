<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`预测结果 - ${record?.data_date || ''}`"
    width="90%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="result-dialog">
      <div class="filter-bar">
        <span class="filter-label">持仓筛选：</span>
        <el-radio-group v-model="filterType" @change="handleFilterChange">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="held">仅持仓</el-radio-button>
          <el-radio-button value="not_held">仅非持仓</el-radio-button>
        </el-radio-group>
      </div>

      <el-table
        :data="filteredResults"
        v-loading="loading"
        style="width: 100%"
        :default-sort="{ prop: 'row_number', order: 'ascending' }"
      >
        <el-table-column
          prop="row_number"
          label="行号"
          width="80"
          sortable
        />

        <el-table-column
          prop="stock_code"
          label="股票代码"
          width="120"
          sortable
        />

        <el-table-column
          prop="stock_name"
          label="股票名称"
          width="150"
          sortable
        />

        <el-table-column
          prop="prediction_score"
          label="预测分数"
          width="120"
          sortable
        >
          <template #default="{ row }">
            <span :class="getScoreClass(row.prediction_score)">
              {{ formatScore(row.prediction_score) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="是否持仓"
          width="100"
        >
          <template #default="{ row }">
            <el-tag :type="row.is_held ? 'success' : 'info'" size="small">
              {{ row.is_held ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getPredictionResult } from '@/api/prediction'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  record: {
    type: Object,
    default: null
  }
})

const emit = defineEmits('update:visible')

const loading = ref(false)
const filterType = ref('all')
const results = ref([])

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const filteredResults = computed(() => {
  if (filterType.value === 'all') {
    return results.value
  } else if (filterType.value === 'held') {
    return results.value.filter(r => r.is_held)
  } else if (filterType.value === 'not_held') {
    return results.value.filter(r => !r.is_held)
  }
  return results.value
})

const loadResults = async () => {
  if (!props.record?.id) return

  loading.value = true
  try {
    const data = await getPredictionResult(props.record.id)
    results.value = (data || []).map((item, index) => ({
      row_number: index + 1,
      stock_code: item.stock_code,
      stock_name: item.stock_name,
      prediction_score: item.prediction_score,
      is_held: item.is_held
    }))
  } catch (error) {
    ElMessage.error('加载预测结果失败')
    console.error('Load results error:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  // 筛选逻辑通过 computed 自动处理
}

const handleClose = () => {
  dialogVisible.value = false
  results.value = []
  filterType.value = 'all'
}

const getScoreClass = (score) => {
  return score >= 0.5 ? 'score-high' : 'score-low'
}

const formatScore = (score) => {
  return (score || 0).toFixed(4)
}

watch(() => props.visible, (newVal) => {
  if (newVal && props.record) {
    loadResults()
  }
})

watch(() => props.record, (newVal) => {
  if (newVal && props.visible) {
    loadResults()
  }
})
</script>

<style scoped>
.result-dialog {
  max-height: 60vh;
  overflow-y: auto;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  margin-right: 12px;
}

.score-high {
  color: #67c23a;
  font-weight: 600;
}

.score-low {
  color: #f56c6c;
  font-weight: 600;
}
</style>
