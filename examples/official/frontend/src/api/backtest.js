/**
 * 回测 API 服务
 * 提供回测配置提交和结果获取的接口
 */
import request from '../utils/request'

/**
 * 提交回测配置并执行回测
 * @param {Object} config - 回测配置参数
 * @returns {Promise<Object>} 回测任务ID
 */
export function submitBacktest(config) {
  return request.post('/api/backtest/', config)
}

/**
 * 获取回测任务状态
 * @param {String} taskId - 任务ID
 * @returns {Promise<Object>} 任务状态
 */
export function getBacktestStatus(taskId) {
  return request.get(`/api/backtest/tasks/${taskId}`)
}

/**
 * 获取回测结果 (包含配置、指标、交易明细)
 * @param {String} taskId - 任务ID
 * @returns {Promise<Object>} 回测结果
 */
export function getBacktestResult(taskId) {
  return request.get(`/api/backtest/tasks/${taskId}/results`)
}

/**
 * 获取回测交易明细 (已包含在结果中，为了兼容暂保留，返回部分数据)
 * 注意：建议直接使用 getBacktestResult
 */
export function getBacktestTrades(taskId, params = {}) {
  // 由于后端 unified 返回，这里只是为了兼容旧代码，实际应该在组件中处理
  return getBacktestResult(taskId).then(res => res.trade_logs || [])
}

/**
 * 取消回测任务
 * @param {String} taskId - 任务ID
 * @returns {Promise<Object>} 操作结果
 */
export function cancelBacktest(taskId) {
  return request.post(`/api/backtest/cancel/${taskId}`)
}

/**
 * 导出回测结果
 * @param {String} taskId - 任务ID
 * @param {String} format - 导出格式（csv/json）
 * @returns {Promise<Blob>} 文件数据
 */
export function exportBacktestResult(taskId, format = 'csv') {
  return request.get(`/api/backtest/export/${taskId}`, {
    params: { format },
    responseType: 'blob'
  })
}
