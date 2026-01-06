<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`${stockName} (${stockCode}) - 历史记录`"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-loading="loading" class="history-content">
      <el-empty v-if="!loading && (!historyData || historyData.length === 0)" description="暂无历史数据" />

      <el-table
        v-else
        :data="displayData"
        stripe
        border
        style="width: 100%"
        :default-sort="{ prop: 'date', order: 'descending' }"
      >
        <el-table-column
          prop="date"
          label="日期"
          width="120"
          sortable
        />
        <el-table-column
          prop="open"
          label="开盘价"
          width="100"
          sortable
          align="right"
        >
          <template #default="{ row }">
            <span :style="getColorStyle(row.change, 0)">{{ formatPrice(row.open) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="close"
          label="收盘价"
          width="100"
          sortable
          align="right"
        >
          <template #default="{ row }">
            <span :style="getColorStyle(row.change, 0)">{{ formatPrice(row.close) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="high"
          label="最高价"
          width="100"
          sortable
          align="right"
        >
          <template #default="{ row }">
            <span class="text-red-600">{{ formatPrice(row.high) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="low"
          label="最低价"
          width="100"
          sortable
          align="right"
        >
          <template #default="{ row }">
            <span class="text-green-600">{{ formatPrice(row.low) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="volume"
          label="成交量"
          width="120"
          sortable
          align="right"
        >
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="change"
          label="涨跌幅"
          width="100"
          sortable
          align="right"
        >
          <template #default="{ row }">
            <span :style="getColorStyle(row.change, 0)">{{ formatPercent(row.change) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import request from '../utils/request'

export default {
  name: 'HistoryDialog',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    stockCode: {
      type: String,
      default: ''
    },
    stockName: {
      type: String,
      default: ''
    }
  },
  emits: ['update:visible'],
  setup(props, { emit }) {
    const loading = ref(false)
    const historyData = ref([])

    const dialogVisible = computed({
      get: () => props.visible,
      set: (val) => emit('update:visible', val)
    })

    // 最多显示20条记录
    const displayData = computed(() => {
      if (!historyData.value || historyData.value.length === 0) {
        return []
      }
      // 按日期降序排列，取前20条
      const sorted = [...historyData.value].sort((a, b) => {
        return new Date(b.date) - new Date(a.date)
      })
      return sorted.slice(0, 20)
    })

    // 格式化价格
    const formatPrice = (value) => {
      if (value === null || value === undefined) return '-'
      return Number(value).toFixed(2)
    }

    // 格式化成交量
    const formatVolume = (value) => {
      if (value === null || value === undefined) return '-'
      const v = Number(value)
      if (v >= 100000000) {
        return (v / 100000000).toFixed(2) + '亿'
      } else if (v >= 10000) {
        return (v / 10000).toFixed(2) + '万'
      }
      return v.toFixed(0)
    }

    // 格式化百分比
    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-'
      return (Number(value) * 100).toFixed(2) + '%'
    }

    // 获取颜色样式
    const getColorStyle = (change, threshold = 0) => {
      if (change === null || change === undefined) return {}
      const val = Number(change)
      if (val > threshold) {
        return { color: '#F44336' } // 红色
      } else if (val < threshold) {
        return { color: '#4CAF50' } // 绿色
      }
      return { color: '#666666' }
    }

    // 加载历史数据
    const loadHistoryData = async () => {
      if (!props.stockCode) {
        historyData.value = []
        return
      }

      loading.value = true
      try {
        const response = await request.get(`/api/stocks/${props.stockCode}/history`)
        historyData.value = response || []
      } catch (error) {
        console.error('Failed to load history data:', error)
        historyData.value = []
      } finally {
        loading.value = false
      }
    }

    // 关闭弹窗
    const handleClose = () => {
      dialogVisible.value = false
      historyData.value = []
    }

    // 监听弹窗显示状态
    watch(() => props.visible, (newVal) => {
      if (newVal) {
        loadHistoryData()
      }
    })

    return {
      loading,
      historyData,
      dialogVisible,
      displayData,
      formatPrice,
      formatVolume,
      formatPercent,
      getColorStyle,
      handleClose
    }
  }
}
</script>

<style scoped>
.history-content {
  min-height: 400px;
}

.text-red-600 {
  color: #F44336;
}

.text-green-600 {
  color: #4CAF50;
}
</style>
