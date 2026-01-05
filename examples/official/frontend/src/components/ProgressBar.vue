<template>
  <div class="progress-container" v-if="visible">
    <div class="progress-header">
      <span class="progress-label">{{ label }}</span>
      <span class="progress-percentage">{{ percentage }}%</span>
    </div>
    <el-progress
      :percentage="percentage"
      :status="status"
      :stroke-width="12"
      :show-text="false"
    />
    <div class="progress-status">
      <el-tag :type="statusType" size="small">
        {{ statusText }}
      </el-tag>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  percentage: {
    type: Number,
    default: 0
  },
  status: {
    type: String,
    default: 'success'
  },
  label: {
    type: String,
    default: '预测执行中'
  }
})

defineEmits(['update:visible'])

const statusType = computed(() => {
  const statusMap = {
    success: 'success',
    exception: 'danger',
    warning: 'warning',
    active: 'primary'
  }
  return statusMap[props.status] || 'info'
})

const statusText = computed(() => {
  const textMap = {
    success: '完成',
    exception: '失败',
    warning: '中断',
    active: '执行中'
  }
  return textMap[props.status] || '执行中'
})
</script>

<style scoped>
.progress-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.progress-percentage {
  font-size: 16px;
  font-weight: 600;
  color: #409EFF;
}

.progress-status {
  margin-top: 12px;
  text-align: right;
}
</style>
