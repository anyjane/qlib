<template>
  <div class="backtest-result-container">
    <el-card class="result-card">
      <template #header>
        <div class="card-header">
          <h2>回测结果</h2>
          <el-button-group>
            <el-button
              size="default"
              @click="exportResult('csv')"
            >
              导出CSV
            </el-button>
            <el-button
              size="default"
              @click="exportResult('json')"
            >
              导出JSON
            </el-button>
            <el-button
              size="default"
              type="primary"
              @click="goBack"
            >
              返回配置
            </el-button>
          </el-button-group>
        </div>
      </template>
      
      <!-- 结果摘要 -->
      <div v-if="backtestResult" class="summary-section">
        <h3 class="section-title">回测摘要</h3>
        
        <el-row :gutter="20" class="summary-row">
          <el-col :span="6">
            <div class="summary-item">
              <div class="item-label">回测日期</div>
              <div class="item-value">{{ backtestResult.backtestDate }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="summary-item">
              <div class="item-label">策略类型</div>
              <div class="item-value">{{ formatStrategyName(backtestResult.config.strategyType) }}</div>
            </div>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" class="summary-row">
          <el-col :span="6">
            <div class="summary-item">
              <div class="item-label">初始资金</div>
              <div class="item-value">{{ formatMoney(backtestResult.config.initialCapital * 10000) }}</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="summary-item">
              <div class="item-label">最终资金</div>
              <div class="item-value" :class="getProfitClass(backtestResult.finalCapital, backtestResult.config.initialCapital * 10000)">
                {{ formatMoney(backtestResult.finalCapital) }}
              </div>
            </div>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" class="summary-row">
          <el-col :span="8">
            <div class="summary-item">
              <div class="item-label">总收益率</div>
              <div class="item-value" :class="getProfitClass(backtestResult.finalCapital, backtestResult.config.initialCapital * 10000)">
                {{ calculateReturn(backtestResult.finalCapital, backtestResult.config.initialCapital * 10000) }}%
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-item">
              <div class="item-label">交易次数</div>
              <div class="item-value">{{ backtestResult.totalTrades || 0 }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-item">
              <div class="item-label">交易费用</div>
              <div class="item-value">{{ formatMoney(backtestResult.totalCommission || 0) }}</div>
            </div>
          </el-col>
        </el-row>
      </div>
      
      <!-- 回测参数配置 -->
      <div v-if="backtestResult" class="params-section">
        <h3 class="section-title">回测参数</h3>
        
        <el-collapse v-model="paramsVisible">
          <el-collapse-item title="基础配置" name="basic">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="初始资金">{{ backtestResult.config.initialCapital }} 万元</el-descriptions-item>
              <el-descriptions-item label="市场">{{ formatMarketName(backtestResult.config.market) }}</el-descriptions-item>
              <el-descriptions-item label="训练期">{{ backtestResult.config.trainStart }} 至 {{ backtestResult.config.trainEnd }}</el-descriptions-item>
              <el-descriptions-item label="测试期">{{ backtestResult.config.testStart }} 至 {{ backtestResult.config.testEnd }}</el-descriptions-item>
              <el-descriptions-item label="买入费率">{{ (backtestResult.config.buyCommission * 100).toFixed(4) }}%</el-descriptions-item>
              <el-descriptions-item label="卖出费率">{{ (backtestResult.config.sellCommission * 100).toFixed(4) }}%</el-descriptions-item>
            </el-descriptions>
          </el-collapse-item>
          
          <el-collapse-item title="策略参数" name="strategy">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="策略类型">{{ formatStrategyName(backtestResult.config.strategyType) }}</el-descriptions-item>
              <el-descriptions-item label="TopK">{{ backtestResult.config.strategyParams.topk }}</el-descriptions-item>
              <el-descriptions-item label="N_Drop">{{ backtestResult.config.strategyParams.nDrop }}</el-descriptions-item>
              <el-descriptions-item label="卖出方法">{{ backtestResult.config.strategyParams.methodSell }}</el-descriptions-item>
              <el-descriptions-item label="买入方法">{{ backtestResult.config.strategyParams.methodBuy }}</el-descriptions-item>
              <el-descriptions-item label="持仓最小天数">{{ backtestResult.config.strategyParams.holdThresh }}</el-descriptions-item>
              <el-descriptions-item label="详细日志">{{ backtestResult.config.strategyParams.verbose ? '启用' : '禁用' }}</el-descriptions-item>
            </el-descriptions>
            
            <div v-if="backtestResult.config.strategyType === 'topk_dropout_with_reallocation'">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="最大再分配轮数">{{ backtestResult.config.strategyParams.maxReallocationRounds }}</el-descriptions-item>
                <el-descriptions-item label="预测详情">{{ backtestResult.config.strategyParams.logPredictionDetails ? '启用' : '禁用' }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <!-- 交易过程明细 -->
      <div v-if="backtestResult && backtestResult.trades" class="trades-section">
        <h3 class="section-title">交易过程明细</h3>
        
        <el-table
          :data="backtestResult.trades"
          stripe
          border
          :row-key="(row) => row.tradeDate"
          max-height="600"
        >
          <el-table-column type="expand" width="50" />
          
          <el-table-column
            prop="tradeDate"
            label="交易日期"
            width="120"
            sortable
          />
          
          <el-table-column label="预测最高" width="200">
            <template #default="{ row }">
              <div class="top-prediction">
                <div v-for="(stock, index) in row.topPredictions.slice(0, 3)" :key="index" class="stock-item">
                  <el-tag size="small" type="primary">{{ stock.code }}</el-tag>
                  <span class="score">{{ stock.score.toFixed(4) }}</span>
                </div>
                <div v-if="row.topPredictions.length > 3" class="more-hint">
                  +{{ row.topPredictions.length - 3 }}
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="当前持仓" width="200">
            <template #default="{ row }">
              <div class="holdings">
                <div v-for="(stock, index) in row.holdings.slice(0, 3)" :key="index" class="holding-item">
                  <span class="code">{{ stock.code }}</span>
                  <span class="score">{{ stock.score.toFixed(4) }}</span>
                </div>
                <div v-if="row.holdings.length > 3" class="more-hint">
                  +{{ row.holdings.length - 3 }}
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="买入交易" width="280">
            <template #default="{ row }">
              <div v-if="row.buyTrades && row.buyTrades.length > 0" class="buy-trades">
                <div v-for="(trade, index) in row.buyTrades.slice(0, 2)" :key="index" class="trade-item buy">
                  <el-tag size="small" type="success">买入</el-tag>
                  <span class="code">{{ trade.code }}</span>
                  <span class="detail">{{ trade.quantity }}股 @ {{ formatPrice(trade.price) }}</span>
                  <span class="capital">{{ formatMoney(trade.value) }}</span>
                </div>
                <div v-if="row.buyTrades.length > 2" class="more-hint">
                  +{{ row.buyTrades.length - 2 }}
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="卖出交易" width="280">
            <template #default="{ row }">
              <div v-if="row.sellTrades && row.sellTrades.length > 0" class="sell-trades">
                <div v-for="(trade, index) in row.sellTrades.slice(0, 2)" :key="index" class="trade-item sell">
                  <el-tag size="small" type="warning">卖出</el-tag>
                  <span class="code">{{ trade.code }}</span>
                  <span class="detail">{{ trade.quantity }}股 @ {{ formatPrice(trade.price) }}</span>
                  <span class="fee">手续费{{ formatMoney(trade.fee) }}</span>
                  <span class="actual">{{ formatMoney(trade.actualAmount) }}</span>
                </div>
                <div v-if="row.sellTrades.length > 2" class="more-hint">
                  +{{ row.sellTrades.length - 2 }}
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column
            prop="startCapital"
            label="起始资金"
            width="120"
            :formatter="(row) => formatMoney(row.startCapital)"
          />
          
          <el-table-column
            prop="endCapital"
            label="完成资金"
            width="120"
            :formatter="(row) => formatMoney(row.endCapital)"
          >
            <template #default="{ row }">
              <span :class="getProfitClass(row.endCapital, row.startCapital)">
                {{ formatMoney(row.endCapital) }}
              </span>
            </template>
          </el-table-column>
          
          <!-- 展开行显示详情 -->
          <template #expand="{ row }">
            <div class="expand-detail">
              <!-- 预测详情 -->
              <h4 class="detail-section">预测得分详情 (Top 20)</h4>
              <el-table :data="row.topPredictions" size="small" border max-height="200">
                <el-table-column prop="code" label="股票代码" width="120" />
                <el-table-column
                  prop="score"
                  label="预测得分"
                  width="100"
                  :formatter="(val) => val.toFixed(4)"
                />
                <el-table-column
                  label="持仓"
                  width="80"
                  align="center"
                >
                  <template #default="{ row }">
                    <el-icon v-if="isHolding(row.code, row.holdings)" name="Check" color="#67C23A" />
                    <el-icon v-else name="Close" color="#909399" />
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- 持仓详情 -->
              <h4 class="detail-section">持仓详情</h4>
              <el-table :data="row.holdings" size="small" border max-height="200">
                <el-table-column prop="code" label="股票代码" width="120" />
                <el-table-column
                  prop="score"
                  label="预测得分"
                  width="100"
                  :formatter="(val) => val.toFixed(4)"
                />
                <el-table-column
                  prop="amount"
                  label="持仓数量"
                  width="100"
                  align="right"
                  :formatter="(val) => val.toLocaleString() + '股'"
                />
              </el-table>
              
              <!-- 买入交易详情 -->
              <h4 v-if="row.buyTrades && row.buyTrades.length > 0" class="detail-section">买入交易详情</h4>
              <el-table v-if="row.buyTrades && row.buyTrades.length > 0" :data="row.buyTrades" size="small" border max-height="200">
                <el-table-column prop="code" label="股票代码" width="120" />
                <el-table-column
                  prop="score"
                  label="预测得分"
                  width="100"
                  :formatter="(val) => val.toFixed(4)"
                />
                <el-table-column
                  prop="quantity"
                  label="买入数量"
                  width="100"
                  align="right"
                  :formatter="(val) => val.toLocaleString() + '股'"
                />
                <el-table-column
                  prop="price"
                  label="买入单价"
                  width="100"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
                <el-table-column
                  prop="value"
                  label="买入金额"
                  width="120"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
                <el-table-column
                  prop="fee"
                  label="交易费用"
                  width="120"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
              </el-table>
              
              <!-- 卖出交易详情 -->
              <h4 v-if="row.sellTrades && row.sellTrades.length > 0" class="detail-section">卖出交易详情</h4>
              <el-table v-if="row.sellTrades && row.sellTrades.length > 0" :data="row.sellTrades" size="small" border max-height="200">
                <el-table-column prop="code" label="股票代码" width="120" />
                <el-table-column
                  prop="score"
                  label="预测得分"
                  width="100"
                  :formatter="(val) => val.toFixed(4)"
                />
                <el-table-column
                  prop="quantity"
                  label="卖出数量"
                  width="100"
                  align="right"
                  :formatter="(val) => val.toLocaleString() + '股'"
                />
                <el-table-column
                  prop="price"
                  label="卖出价格"
                  width="100"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
                <el-table-column
                  prop="value"
                  label="卖出金额"
                  width="120"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
                <el-table-column
                  prop="fee"
                  label="交易费用"
                  width="120"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
                <el-table-column
                  prop="actualAmount"
                  label="实际收拢"
                  width="120"
                  align="right"
                  :formatter="(val) => '￥' + val.toFixed(2)"
                />
              </el-table>
            </div>
          </template>
        </el-table>
      </div>
      
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="10" animated />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getBacktestResult, getBacktestTrades, exportBacktestResult } from '../api/backtest'

const route = useRoute()
const router = useRouter()

// 数据状态
const backtestResult = ref(null)
const trades = ref([])
const loading = ref(true)
const paramsVisible = ref(['basic'])

// 获取任务ID
const taskId = route.query.taskId

// 获取回测结果
const loadBacktestResult = async () => {
  if (!taskId) {
    ElMessage.error('缺少任务ID参数')
    router.push('/backtest/config')
    return
  }
  
  try {
    loading.value = true
    
    // 获取基本信息
    const resultData = await getBacktestResult(taskId)
    
    // 获取交易明细
    const tradesData = await getBacktestTrades(taskId)
    
    backtestResult.value = {
      ...resultData,
      trades: tradesData
    }
    
    ElMessage.success('回测结果加载成功')
  } catch (error) {
    console.error('加载回测结果失败:', error)
    ElMessage.error('加载回测结果失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 格式化金额
const formatMoney = (value) => {
  return '￥' + parseFloat(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

// 格式化价格
const formatPrice = (value) => {
  return parseFloat(value).toFixed(2)
}

// 计算收益率
const calculateReturn = (final, initial) => {
  if (!initial || initial === 0) return 0
  return ((final - initial) / initial * 100).toFixed(4)
}

// 判断是否持仓
const isHolding = (code, holdings) => {
  return holdings.some(h => h.code === code)
}

// 获取收益率样式
const getProfitClass = (final, initial) => {
  const returnVal = calculateReturn(final, initial)
  if (parseFloat(returnVal) > 0) return 'profit'
  if (parseFloat(returnVal) < 0) return 'loss'
  return ''
}

// 格式化策略名称
const formatStrategyName = (type) => {
  const nameMap = {
    'topk_dropout': 'TopkDropout',
    'topk_dropout_with_reallocation': 'TopkDropoutWithReallocation'
  }
  return nameMap[type] || type
}

// 格式化市场名称
const formatMarketName = (market) => {
  const nameMap = {
    'csi300': '沪深300',
    'csi500': '中证500',
    'all': '全市场'
  }
  return nameMap[market] || market
}

// 导出结果
const exportResult = async (format) => {
  if (!taskId) return
  
  try {
    ElMessage.info('正在导出数据...')
    
    const blob = await exportBacktestResult(taskId, format)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `backtest_result_${taskId}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败，请稍后重试')
  }
}

// 返回配置页面
const goBack = () => {
  router.push('/backtest')
}

// 组件挂载时加载数据
onMounted(() => {
  loadBacktestResult()
})
</script>

<style scoped>
.backtest-result-container {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.result-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.summary-section,
.params-section,
.trades-section {
  margin-top: 30px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}

.summary-row {
  margin-bottom: 15px;
}

.summary-item {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 10px;
}

.item-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.item-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}

.top-prediction,
.holdings {
  font-size: 12px;
}

.stock-item,
.holding-item {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  gap: 8px;
}

.stock-item .score,
.holding-item .score {
  color: #909399;
  font-size: 11px;
  margin-left: 4px;
}

.more-hint {
  color: #909399;
  font-size: 12px;
}

.buy-trades,
.sell-trades {
  font-size: 12px;
}

.trade-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 4px;
}

.trade-item.buy {
  color: #67c23a;
}

.trade-item.sell {
  color: #e6a23c;
}

.trade-item .code {
  font-weight: 600;
}

.trade-item .detail {
  color: #606266;
  font-size: 11px;
}

.trade-item .fee {
  color: #f56c6c;
  font-size: 11px;
}

.trade-item .actual {
  color: #303133;
  font-weight: 600;
  font-size: 11px;
}

.expand-detail {
  padding: 20px;
  background: #fafafa;
  border-radius: 4px;
}

.detail-section {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 20px 0 10px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.loading-container {
  padding: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-table__expand-icon) {
  color: #409eff;
}
</style>
