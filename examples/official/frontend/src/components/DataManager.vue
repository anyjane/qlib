<template>
  <div class="data-manager">
    <!-- 顶部工具栏 -->
    <el-card shadow="hover" class="toolbar-card">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索股票代码或名称..."
            clearable
            @clear="searchKeyword = ''"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="16" class="text-right">
          <el-button type="primary" @click="handleRefresh" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 批量操作栏 -->
    <el-card v-if="selectedStocks.length > 0" shadow="hover" class="batch-toolbar">
      <el-space>
        <span class="selection-info">
          已选择 <strong>{{ selectedStocks.length }}</strong> 只股票
        </span>
        <el-button type="primary" @click="handleBatchDownload">
          <el-icon><Download /></el-icon> 下载数据
        </el-button>
        <el-button type="success" @click="handleBatchUpdate">
          <el-icon><Refresh /></el-icon> 增量更新
        </el-button>
        <el-button type="danger" @click="handleBatchDelete">
          <el-icon><Delete /></el-icon> 删除数据
        </el-button>
        <el-button @click="handleSelectAll">全选</el-button>
        <el-button @click="handleClearSelection">清空</el-button>
      </el-space>
    </el-card>

    <!-- 股票数据表格 -->
    <el-card shadow="hover" class="table-card">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="filteredStocks"
        @selection-change="handleSelectionChange"
        @select="handleSelect"
        @row-dblclick="handleRowDblClick"
        stripe
        height="calc(100vh - 300px)"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column
          prop="code"
          label="股票代码"
          width="120"
          sortable
          :sort-method="(a, b) => sortByField(a, b, 'code')"
        />
        <el-table-column
          prop="name"
          label="股票名称"
          width="150"
          sortable
          :sort-method="(a, b) => sortByField(a, b, 'name')"
        />
        <el-table-column
          label="数据状态"
          width="120"
          sortable
          :sort-method="(a, b) => sortByStatus(a, b)"
        >
          <template #default="{ row }">
            <el-tag :type="row.has_data ? 'success' : 'info'">
              {{ row.has_data ? '已有数据' : '无数据' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="data_start_date"
          label="数据开始日期"
          width="140"
          sortable
          :sort-method="(a, b) => sortByDate(a, b, 'data_start_date')"
        />
        <el-table-column
          prop="data_end_date"
          label="数据结束日期"
          width="140"
          sortable
          :sort-method="(a, b) => sortByDate(a, b, 'data_end_date')"
        />
        <el-table-column
          prop="data_count"
          label="数据量"
          width="100"
          sortable
          :sort-method="(a, b) => sortByField(a, b, 'data_count', true)"
        />
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button
              v-if="!row.has_data"
              type="primary"
              size="small"
              @click="handleDownloadStock(row.code)"
            >
              下载数据
            </el-button>
            <el-button
              v-else
              type="success"
              size="small"
              @click="handleUpdateStock(row.code)"
            >
              增量更新
            </el-button>
            <el-button
              v-if="row.has_data"
              type="danger"
              size="small"
              @click="handleDeleteStock(row.code)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务监控面板 -->
    <TaskMonitor />

    <!-- 历史记录弹窗 -->
    <HistoryDialog
      v-model:visible="historyDialogVisible"
      :stock-code="selectedStockForHistory.code"
      :stock-name="selectedStockForHistory.name"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Download, Delete } from '@element-plus/icons-vue'
import request from '../utils/request'
import wsClient from '../utils/websocket'
import TaskMonitor from './TaskMonitor.vue'
import HistoryDialog from './HistoryDialog.vue'

export default {
  name: 'DataManager',
  components: {
    TaskMonitor,
    HistoryDialog,
    Search,
    Refresh,
    Download,
    Delete
  },
  setup() {
    const searchKeyword = ref('')
    const stocks = ref([])
    const selectedStocks = ref([])
    const loading = ref(false)
    const tableRef = ref(null)
    const lastClickedIndex = ref(-1)
    const historyDialogVisible = ref(false)
    const selectedStockForHistory = ref({ code: '', name: '' })

    // 过滤后的股票列表
    const filteredStocks = computed(() => {
      if (!searchKeyword.value) return stocks.value
      const keyword = searchKeyword.value.toLowerCase()
      return stocks.value.filter(stock =>
        stock.code.toLowerCase().includes(keyword) ||
        stock.name.toLowerCase().includes(keyword)
      )
    })

    // 加载股票数据状态
    const loadStocksData = async () => {
      loading.value = true
      try {
        stocks.value = await request.get('/api/data/stocks/status')
      } catch (error) {
        ElMessage.error('加载数据失败')
        console.error(error)
      } finally {
        loading.value = false
      }
    }

    // 刷新
    const handleRefresh = () => {
      loadStocksData()
    }

    // 选择变化
    const handleSelectionChange = (selection) => {
      selectedStocks.value = selection
    }

    // 跟踪 Shift 键状态
    const isShiftPressed = ref(false)
    
    const handleKeyDown = (e) => {
      if (e.key === 'Shift') {
        isShiftPressed.value = true
      }
    }
    
    const handleKeyUp = (e) => {
      if (e.key === 'Shift') {
        isShiftPressed.value = false
      }
    }

    // 单个行选择事件（checkbox 点击时触发）
    const handleSelect = (selection, row) => {
      const currentIndex = filteredStocks.value.findIndex(s => s.code === row.code)
      
      // 检查这一行是否被选中（在新 selection 中）
      const isSelected = selection.some(s => s.code === row.code)
      
      if (isShiftPressed.value && lastClickedIndex.value >= 0 && currentIndex !== lastClickedIndex.value && isSelected) {
        // Shift+Click: 选择从上次点击到当前行的范围
        const startIndex = Math.min(lastClickedIndex.value, currentIndex)
        const endIndex = Math.max(lastClickedIndex.value, currentIndex)
        
        // 获取范围内的所有行
        const rangeRows = filteredStocks.value.slice(startIndex, endIndex + 1)
        
        // 使用 el-table 的 toggleRowSelection 方法选中这些行
        if (tableRef.value) {
          rangeRows.forEach(rangeRow => {
            tableRef.value.toggleRowSelection(rangeRow, true)
          })
        }
      }
      
      // 更新最后点击的索引
      if (isSelected) {
        lastClickedIndex.value = currentIndex
      }
    }

    // 排序变化
    const handleSortChange = ({ prop, order }) => {
      sortField.value = prop
      sortOrder.value = order || 'ascending'
    }

    // 全选
    const handleSelectAll = () => {
      if (tableRef.value) {
        filteredStocks.value.forEach(row => {
          tableRef.value.toggleRowSelection(row, true)
        })
      }
    }

    // 清空选择
    const handleClearSelection = () => {
      if (tableRef.value) {
        tableRef.value.clearSelection()
      }
      selectedStocks.value = []
      lastClickedIndex.value = -1
    }

    // 日期对比函数
    const compareDates = (date1, date2) => {
      if (!date1 && !date2) return 0
      if (!date1) return -1
      if (!date2) return 1
      return new Date(date1).getTime() - new Date(date2).getTime()
    }

    // 按字段排序（用于 Element Plus 的 sort-method）
    const sortByField = (a, b, field, isNumber = false) => {
      const valA = a[field] || (isNumber ? 0 : '')
      const valB = b[field] || (isNumber ? 0 : '')

      if (isNumber) {
        return valA - valB
      }
      return String(valA).localeCompare(String(valB))
    }

    // 按日期排序
    const sortByDate = (a, b, field) => {
      return compareDates(a[field], b[field])
    }

    // 按数据状态排序
    const sortByStatus = (a, b) => {
      // 有数据的排在前面
      return (b.has_data ? 1 : 0) - (a.has_data ? 1 : 0)
    }

    // 下载数据
    const handleDownloadStock = async (code) => {
      try {
        const result = await request.post('/api/data/download', {
          stocks: [code]
        })
        ElMessage.success('下载任务已创建')
      } catch (error) {
        ElMessage.error('创建下载任务失败')
      }
    }

    // 批量下载
    const handleBatchDownload = async () => {
      const codes = selectedStocks.value.map(s => s.code)
      try {
        const result = await request.post('/api/data/download', {
          stocks: codes
        })
        ElMessage.success('批量下载任务已创建')
      } catch (error) {
        ElMessage.error('创建批量下载任务失败')
      }
    }

    // 增量更新
    const handleUpdateStock = async (code) => {
      try {
        await request.post('/api/data/update', { stocks: [code] })
        ElMessage.success('更新任务已创建')
      } catch (error) {
        ElMessage.error('创建更新任务失败')
      }
    }

    // 批量更新
    const handleBatchUpdate = async () => {
      const codes = selectedStocks.value.map(s => s.code)
      try {
        await request.post('/api/data/update', { stocks: codes })
        ElMessage.success('批量更新任务已创建')
      } catch (error) {
        ElMessage.error('创建批量更新任务失败')
      }
    }

    // 删除
    const handleDeleteStock = async (code) => {
      try {
        await ElMessageBox.confirm('确认删除该股票的所有数据吗？', '警告', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning'
        })

        await request.post('/api/data/delete', { stocks: [code] })
        ElMessage.success('删除成功')
        loadStocksData()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败')
        }
      }
    }

    // 批量删除
    const handleBatchDelete = async () => {
      const codes = selectedStocks.value.map(s => s.code)
      try {
        await ElMessageBox.confirm(
          `确认删除选中的 ${codes.length} 只股票的数据吗？`,
          '警告',
          {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await request.post('/api/data/delete', { stocks: codes })
        ElMessage.success('批量删除成功')
        handleClearSelection()
        loadStocksData()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('批量删除失败')
        }
      }
    }

    // 双击行事件处理
    const handleRowDblClick = (row) => {
      selectedStockForHistory.value = {
        code: row.code,
        name: row.name
      }
      historyDialogVisible.value = true
    }

    onMounted(() => {
      loadStocksData()
      wsClient.connect('ws://localhost:8000')
      
      // 添加键盘事件监听器（用于 Shift 多选）
      window.addEventListener('keydown', handleKeyDown)
      window.addEventListener('keyup', handleKeyUp)
      
      wsClient.on('task_update', (message) => {
        console.log('Task update received:', message)
      })
    })

    onUnmounted(() => {
      wsClient.disconnect()
      // 移除键盘事件监听器
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    })

    return {
      searchKeyword,
      stocks,
      selectedStocks,
      loading,
      filteredStocks,
      tableRef,
      historyDialogVisible,
      selectedStockForHistory,
      sortByField,
      sortByDate,
      sortByStatus,
      handleRefresh,
      handleSelectionChange,
      handleSelect,
      handleSelectAll,
      handleClearSelection,
      handleDownloadStock,
      handleUpdateStock,
      handleBatchDownload,
      handleBatchUpdate,
      handleBatchDelete,
      handleDeleteStock,
      handleRowDblClick
    }
  }
}
</script>

<style scoped>
.data-manager {
  padding: 20px;
}

.toolbar-card {
  margin-bottom: 20px;
}

.batch-toolbar {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.batch-toolbar .selection-info {
  color: white;
  font-weight: 500;
}

.text-right {
  text-align: right;
}

.table-card {
  background: white;
}
</style>

