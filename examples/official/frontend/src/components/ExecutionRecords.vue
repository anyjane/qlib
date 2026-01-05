<template>
  <div class="execution-records">
    <div class="records-header">
      <h3>执行记录</h3>
      <el-button
        type="primary"
        icon="el-icon-refresh"
        @click="handleRefresh"
        :loading="loading"
      >
        刷新
      </el-button>
    </div>

    <el-table
      :data="records"
      v-loading="loading"
      @row-dblclick="handleRowDblClick"
      style="width: 100%"
      :row-class-name="getRowClassName"
    >
      <el-table-column label="开始时间" width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.start_time) }}
        </template>
      </el-table-column>

      <el-table-column label="数据日期" width="110">
        <template #default="{ row }">
          {{ row.data_date }}
        </template>
      </el-table-column>

      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="锁定状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_locked ? 'warning' : 'info'" size="small">
            {{ row.is_locked ? '已锁定' : '可删除' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            v-if="row.is_locked"
            @click.stop="handleToggleLock(row)"
          >
            解锁
          </el-button>
          <el-button
            type="warning"
            size="small"
            v-else
            @click.stop="handleToggleLock(row)"
          >
            锁定
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click.stop="handleDelete(row)"
            :disabled="row.is_locked"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && records.length === 0"
      description="暂无执行记录"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, defineEmits } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPredictionTasks, deletePredictionTask, updateTaskLock } from '@/api/prediction'

const emit = defineEmits(['view-result'])

const loading = ref(false)
const records = ref([])

const loadRecords = async () => {
  loading.value = true
  try {
    const data = await getPredictionTasks({ limit: 50 })
    records.value = data || []
  } catch (error) {
    ElMessage.error('加载执行记录失败')
    console.error('Load records error:', error)
  } finally {
    loading.value = false
  }
}

const handleRefresh = () => {
  loadRecords()
}

const handleRowDblClick = (row) => {
  if (row.status === 'completed') {
    emit('view-result', row)
  } else {
    ElMessage.warning('该任务尚未完成，无法查看结果')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '确认删除', {
      type: 'warning'
    })

    await deletePredictionTask(row.id)
    ElMessage.success('删除成功')
    loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error('Delete error:', error)
    }
  }
}

const handleToggleLock = async (row) => {
  try {
    const newStatus = !row.is_locked
    await updateTaskLock(row.id, newStatus)
    row.is_locked = newStatus
    ElMessage.success(newStatus ? '已锁定' : '已解锁')
    loadRecords()
  } catch (error) {
    ElMessage.error('操作失败')
    console.error('Toggle lock error:', error)
  }
}

const getRowClassName = ({ row }) => {
  return row.status === 'completed' ? 'completed-row' : ''
}

const getStatusType = (status) => {
  const typeMap = {
    running: 'primary',
    completed: 'success',
    interrupted: 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    running: '执行中',
    completed: '完成',
    interrupted: '中断'
  }
  return textMap[status] || '未知'
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

defineExpose({
  loadRecords
})

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.execution-records {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.records-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.records-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.completed-row) {
  background-color: #f0f9ff;
}
</style>
