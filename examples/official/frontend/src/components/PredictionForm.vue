<template>
  <div class="prediction-form">
    <div class="form-header">
      <h3>创建预测任务</h3>
    </div>

    <el-form :model="form" label-width="100px" class="form-content">
      <el-form-item label="数据日期">
        <el-date-picker
          v-model="form.dataDate"
          type="date"
          placeholder="选择数据日期"
          value-format="YYYY-MM-DD"
          :clearable="false"
          :disabled-date="disabledDate"
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          icon="el-icon-video-play"
          @click="handleSubmit"
          :loading="validating || submitting"
        >
          执行预测
        </el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { validateDataDate, submitPrediction } from '@/api/prediction'

const emit = defineEmits(['prediction-started', 'prediction-failed'])

const form = ref({
  dataDate: ''
})

const validating = ref(false)
const submitting = ref(false)

const disabledDate = (time) => {
  // 禁用未来日期
  return time.getTime() > Date.now()
}

const handleSubmit = async () => {
  if (!form.value.dataDate) {
    ElMessage.warning('请选择数据日期')
    return
  }

  // 验证数据
  validating.value = true
  try {
    const validationResult = await validateDataDate(form.value.dataDate)

    if (!validationResult.valid) {
      ElMessage.error(validationResult.error || '数据验证失败')
      return
    }

    // 提交预测
    submitting.value = true
    await submitPrediction(form.value.dataDate)

    ElMessage.success('预测任务已创建')
    emit('prediction-started', {
      dataDate: form.value.dataDate
    })
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '执行预测失败'
    ElMessage.error(errorMsg)
    emit('prediction-failed', { error: errorMsg })
    console.error('Submit prediction error:', error)
  } finally {
    validating.value = false
    submitting.value = false
  }
}

const handleReset = () => {
  form.value.dataDate = ''
}

const initDefaultDate = () => {
  const today = new Date()
  form.value.dataDate = today.toISOString().split('T')[0]
}

onMounted(() => {
  initDefaultDate()
})
</script>

<style scoped>
.prediction-form {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.form-header {
  margin-bottom: 20px;
}

.form-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.form-content {
  padding: 0 20px 20px 20px;
}
</style>
