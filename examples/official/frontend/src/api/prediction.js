import request from '@/utils/request'

// 验证数据日期
export function validateDataDate(dataDate) {
  return request.get('/api/predict/validate', {
    params: { date: dataDate }
  })
}

// 提交预测任务
export function submitPrediction(dataDate) {
  return request.post('/api/predict/', null, {
    params: { predict_date: dataDate }
  })
}

// 获取预测任务列表
export function getPredictionTasks(params) {
  return request.get('/api/predict/tasks', { params })
}

// 获取预测结果
export function getPredictionResult(taskId) {
  return request.get(`/api/predict/tasks/${taskId}/results`)
}

// 删除预测任务
export function deletePredictionTask(taskId) {
  return request.delete(`/api/predict/tasks/${taskId}`)
}

// 更新任务锁定状态
export function updateTaskLock(taskId, isLocked) {
  return request.put(`/api/predict/tasks/${taskId}/lock`, { is_locked: isLocked })
}
