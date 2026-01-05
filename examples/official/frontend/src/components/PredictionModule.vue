<template>
  <div class="prediction-module">
    <!-- 预测表单 -->
    <PredictionForm
      @prediction-started="handlePredictionStarted"
      @prediction-failed="handlePredictionFailed"
    />

    <!-- 进度条 -->
    <ProgressBar
      v-model:visible="progressVisible"
      v-model:percentage="progressPercentage"
      v-model:status="progressStatus"
      :label="progressLabel"
    />

    <!-- 执行记录列表 -->
    <ExecutionRecords
      ref="recordsRef"
      @view-result="handleViewResult"
    />

    <!-- 结果表格对话框 -->
    <ResultTableDialog
      v-model:visible="resultDialogVisible"
      :record="selectedRecord"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PredictionForm from './PredictionForm.vue'
import ProgressBar from './ProgressBar.vue'
import ExecutionRecords from './ExecutionRecords.vue'
import ResultTableDialog from './ResultTableDialog.vue'

const progressVisible = ref(false)
const progressPercentage = ref(0)
const progressStatus = ref('success')
const progressLabel = ref('预测执行中')

const resultDialogVisible = ref(false)
const selectedRecord = ref(null)

const recordsRef = ref(null)

const handlePredictionStarted = (data) => {
  progressVisible.value = true
  progressPercentage.value = 0
  progressStatus.value = 'active'
  progressLabel.value = `预测执行中 - ${data.dataDate}`

  // 刷新记录列表
  if (recordsRef.value) {
    recordsRef.value.loadRecords()
  }

  // 模拟进度更新（实际应该通过 WebSocket 获取实时进度）
  simulateProgress()
}

const handlePredictionFailed = (data) => {
  progressStatus.value = 'exception'
  progressLabel.value = `预测失败 - ${data.error}`

  setTimeout(() => {
    progressVisible.value = false
  }, 3000)
}

const handleViewResult = (record) => {
  selectedRecord.value = record
  resultDialogVisible.value = true
}

const simulateProgress = () => {
  const interval = setInterval(() => {
    if (progressPercentage.value < 90) {
      progressPercentage.value += Math.random() * 10
    }
  }, 1000)

  // 模拟任务完成
  setTimeout(() => {
    clearInterval(interval)
    progressPercentage.value = 100
    progressStatus.value = 'success'
    progressLabel.value = '预测完成'

    // 刷新记录列表
    if (recordsRef.value) {
      recordsRef.value.loadRecords()
    }

    // 3秒后隐藏进度条
    setTimeout(() => {
      progressVisible.value = false
      progressPercentage.value = 0
    }, 3000)
  }, 5000)
}
</script>

<style scoped>
.prediction-module {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}
</style>
