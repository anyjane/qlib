<template>
  <el-card v-if="tasks.length > 0" shadow="hover" class="task-monitor-card">
    <template #header>
      <div class="task-header">
        <span>任务监控</span>
        <el-badge :value="tasks.length" class="badge">
          <el-icon><Timer /></el-icon>
        </el-badge>
      </div>
    </template>
    
    <div v-for="task in tasks" :key="task.task_id" class="task-item">
      <div class="task-info">
        <el-tag :type="getTaskStatusType(task.status)">
          {{ getTaskStatusText(task.status) }}
        </el-tag>
        <span class="task-id">{{ task.task_id }}</span>
      </div>
      
      <el-progress
        :percentage="task.progress || 0"
        :status="getProgressStatus(task.status)"
      />
      
      <div v-if="task.current_stock" class="task-detail">
        正在处理：{{ task.current_stock }}
        <span class="count-info">
          ({{ task.downloaded_count || task.updated_count }} / {{ task.total_count }})
        </span>
      </div>
      
      <div v-if="task.error" class="task-error">
        <el-alert type="error" :closable="false">
          {{ task.error }}
        </el-alert>
      </div>
      
      <div v-if="task.status === 'completed'" class="task-success">
        <el-icon color="#67c23a"><SuccessFilled /></el-icon>
        <span>任务完成！共处理 {{ task.downloaded_count || task.updated_count }} 只股票</span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Timer, SuccessFilled } from '@element-plus/icons-vue'
import wsClient from '../utils/websocket'

const tasks = ref([])

onMounted(() => {
  wsClient.on('task_update', (message) => {
    const { task_id, data } = message
    
    // 更新或添加任务
    const existingIndex = tasks.value.findIndex(t => t.task_id === task_id)
    if (existingIndex >= 0) {
      tasks.value[existingIndex] = { ...tasks.value[existingIndex], ...data }
    } else {
      tasks.value.push({
        task_id,
        status: data.status,
        progress: data.progress || 0,
        ...data
      })
    }
    
    // 任务完成后5秒移除
    if (data.status === 'completed' || data.status === 'failed') {
      setTimeout(() => {
        tasks.value = tasks.value.filter(t => t.task_id !== task_id)
      }, 5000)
    }
  })
})

const getTaskStatusType = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status]
}

const getTaskStatusText = (status) => {
  const map = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status]
}

const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}
</script>

<style scoped>
.task-monitor-card {
  position: fixed;
  right: 20px;
  top: 80px;
  width: 400px;
  max-height: 600px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.badge {
  margin-left: 10px;
}

.task-item {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
}

.task-info {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.task-id {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.task-detail {
  margin-top: 10px;
  color: #606266;
  font-size: 13px;
}

.count-info {
  margin-left: 5px;
  color: #909399;
}

.task-success {
  margin-top: 10px;
  display: flex;
  align-items: center;
  color: #67c23a;
  font-weight: 500;
}
</style>
