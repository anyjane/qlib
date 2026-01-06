<template>
  <div class="backtest-config-container">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <h2>回测参数配置</h2>
          <el-button-group>
            <el-button
              type="primary"
              size="default"
              @click="useDefaultConfig"
            >
              使用默认配置
            </el-button>
            <el-button
              size="default"
              @click="resetConfig"
            >
              重置
            </el-button>
          </el-button-group>
        </div>
      </template>
      
      <el-form
        ref="configFormRef"
        :model="form"
        :rules="rules"
        label-width="150px"
        label-position="left"
        size="default"
      >
        <!-- 基础配置区块 -->
        <el-divider content-position="left">基础配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="初始资金" prop="initialCapital">
              <el-input-number
                v-model="form.initialCapital"
                :min="1"
                :max="10000"
                :step="1"
                placeholder="单位：万元"
                controls-position="right"
              >
                <template #suffix>万元</template>
              </el-input-number>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="市场选择" prop="market">
              <el-select
                v-model="form.market"
                placeholder="请选择市场"
              >
                <el-option
                  v-for="item in marketOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 日期配置 -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="训练开始日期" prop="trainStart">
              <el-date-picker
                v-model="form.trainStart"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="训练结束日期" prop="trainEnd">
              <el-date-picker
                v-model="form.trainEnd"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="测试开始日期" prop="testStart">
              <el-date-picker
                v-model="form.testStart"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="测试结束日期" prop="testEnd">
              <el-date-picker
                v-model="form.testEnd"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 交易费用配置区块 -->
        <el-divider content-position="left">交易费用配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="买入费率" prop="buyCommission">
              <el-input-number
                v-model="form.buyCommission"
                :min="0"
                :max="1"
                :step="0.0001"
                :precision="4"
                placeholder="费率（如0.0005表示0.05%）"
                controls-position="right"
              >
                <template #append>%</template>
              </el-input-number>
            </el-form-item>
          </el-col>
          
          <el-col :span="8">
            <el-form-item label="卖出费率" prop="sellCommission">
              <el-input-number
                v-model="form.sellCommission"
                :min="0"
                :max="1"
                :step="0.0001"
                :precision="4"
                placeholder="费率（如0.0015表示0.15%）"
                controls-position="right"
              >
                <template #append>%</template>
              </el-input-number>
            </el-form-item>
          </el-col>
          
          <el-col :span="8">
            <el-form-item label="最低手续费" prop="minCommission">
              <el-input-number
                v-model="form.minCommission"
                :min="0"
                :step="1"
                placeholder="元"
                controls-position="right"
              >
                <template #append>元</template>
              </el-input-number>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 策略配置区块 -->
        <el-divider content-position="left">策略配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="策略类型" prop="strategyType">
              <el-select
                v-model="form.strategyType"
                placeholder="请选择策略"
                @change="handleStrategyChange"
              >
                <el-option
                  v-for="item in strategyOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="持仓股票数" prop="strategy.topk">
              <el-input-number
                v-model="form.strategy.topk"
                :min="1"
                :max="100"
                :step="1"
                placeholder="TopK"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="调仓替换数" prop="strategy.nDrop">
              <el-input-number
                v-model="form.strategy.nDrop"
                :min="1"
                :max="50"
                :step="1"
                placeholder="N_Drop"
              />
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="持仓最小天数" prop="strategy.holdThresh">
              <el-input-number
                v-model="form.strategy.holdThresh"
                :min="1"
                :max="365"
                :step="1"
                placeholder="Hold_Thresh"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="卖出方法" prop="strategy.methodSell">
              <el-select
                v-model="form.strategy.methodSell"
                placeholder="请选择方法"
              >
                <el-option
                  v-for="item in methodOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="买入方法" prop="strategy.methodBuy">
              <el-select
                v-model="form.strategy.methodBuy"
                placeholder="请选择方法"
              >
                <el-option
                  v-for="item in methodOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- TopkDropoutWithReallocation 特有参数 -->
        <div v-if="form.strategyType === 'topk_reallocation'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="资金再分配" prop="strategy.maxReallocationRounds">
                <el-input-number
                  v-model="form.strategy.maxReallocationRounds"
                  :min="0"
                  :max="10"
                  :step="1"
                  placeholder="最大再分配轮数"
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item label="输出预测详情">
            <el-switch
              v-model="form.strategy.logPredictionDetails"
              active-text="启用"
              inactive-text="禁用"
            />
          </el-form-item>
        </div>
        
        <!-- 通用参数 -->
        <el-form-item label="详细日志">
          <el-switch
            v-model="form.strategy.verbose"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
        
        <el-form-item label="只考虑可交易股票">
          <el-switch
            v-model="form.strategy.onlyTradable"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
        
        <el-form-item label="涨跌停禁止交易">
          <el-switch
            v-model="form.strategy.forbidAllTradeAtLimit"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
      </el-form>
      
      <div class="action-bar">
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '回测执行中...' : '开始回测' }}
        </el-button>
        <el-button
          size="large"
          @click="handleCancel"
        >
          取消
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { submitBacktest } from '../api/backtest'
import {
  DEFAULT_BACKTEST_CONFIG,
  MARKET_OPTIONS,
  STRATEGY_OPTIONS,
  METHOD_OPTIONS
} from '../constants/backtestConfig'

// 表单数据
const form = reactive({
  initialCapital: DEFAULT_BACKTEST_CONFIG.initialCapital,
  market: DEFAULT_BACKTEST_CONFIG.market,
  trainStart: DEFAULT_BACKTEST_CONFIG.trainStart,
  trainEnd: DEFAULT_BACKTEST_CONFIG.trainEnd,
  testStart: DEFAULT_BACKTEST_CONFIG.testStart,
  testEnd: DEFAULT_BACKTEST_CONFIG.testEnd,
  buyCommission: DEFAULT_BACKTEST_CONFIG.buyCommission,
  sellCommission: DEFAULT_BACKTEST_CONFIG.sellCommission,
  minCommission: DEFAULT_BACKTEST_CONFIG.minCommission,
  strategyType: DEFAULT_BACKTEST_CONFIG.strategyType,
  strategy: { ...DEFAULT_BACKTEST_CONFIG.strategy }
})

// 选项数据
const marketOptions = MARKET_OPTIONS
const strategyOptions = STRATEGY_OPTIONS
const methodOptions = METHOD_OPTIONS

// 提交状态
const submitting = ref(false)
const configFormRef = ref(null)

// 表单校验规则
const rules = {
  initialCapital: [
    { required: true, message: '请输入初始资金', trigger: 'blur' }
  ],
  market: [
    { required: true, message: '请选择市场', trigger: 'change' }
  ],
  trainStart: [
    { required: true, message: '请选择训练开始日期', trigger: 'change' }
  ],
  trainEnd: [
    { required: true, message: '请选择训练结束日期', trigger: 'change' }
  ],
  testStart: [
    { required: true, message: '请选择测试开始日期', trigger: 'change' }
  ],
  testEnd: [
    { required: true, message: '请选择测试结束日期', trigger: 'change' }
  ],
  strategyType: [
    { required: true, message: '请选择策略类型', trigger: 'change' }
  ],
  'strategy.topk': [
    { required: true, message: '请输入持仓股票数', trigger: 'blur' }
  ],
  'strategy.nDrop': [
    { required: true, message: '请输入调仓替换数', trigger: 'blur' }
  ]
}

// 使用默认配置
const useDefaultConfig = () => {
  Object.assign(form, {
    initialCapital: DEFAULT_BACKTEST_CONFIG.initialCapital,
    market: DEFAULT_BACKTEST_CONFIG.market,
    trainStart: DEFAULT_BACKTEST_CONFIG.trainStart,
    trainEnd: DEFAULT_BACKTEST_CONFIG.trainEnd,
    testStart: DEFAULT_BACKTEST_CONFIG.testStart,
    testEnd: DEFAULT_BACKTEST_CONFIG.testEnd,
    buyCommission: DEFAULT_BACKTEST_CONFIG.buyCommission,
    sellCommission: DEFAULT_BACKTEST_CONFIG.sellCommission,
    minCommission: DEFAULT_BACKTEST_CONFIG.minCommission,
    strategyType: DEFAULT_BACKTEST_CONFIG.strategyType,
    strategy: { ...DEFAULT_BACKTEST_CONFIG.strategy }
  })
  ElMessage.success('已加载默认配置')
}

// 重置配置
const resetConfig = () => {
  ElMessageBox.confirm('确定要重置所有配置吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    configFormRef.value?.resetFields()
    ElMessage.success('配置已重置')
  }).catch(() => {})
}

// 策略类型变化
const handleStrategyChange = (value) => {
  console.log('策略类型变化:', value)
}

// 提交回测
const handleSubmit = async () => {
  if (!configFormRef.value) return
  
  try {
    await configFormRef.value.validate()
  } catch (error) {
    console.error('表单验证失败:', error)
    return
  }
  
  submitting.value = true
  
  try {
    // 构建回测配置对象
    const backtestConfig = {
      initial_capital: form.initialCapital,
      market: form.market,
      train_start: form.trainStart,
      train_end: form.trainEnd,
      test_start: form.testStart,
      test_end: form.testEnd,
      buy_rate: form.buyCommission,
      sell_rate: form.sellCommission,
      min_commission: form.minCommission,
      strategy_type: form.strategyType,
      topk: form.strategy.topk,
      n_drop: form.strategy.nDrop,
      hold_thresh: form.strategy.holdThresh,
      method_sell: form.strategy.methodSell,
      method_buy: form.strategy.methodBuy,
      only_tradable: form.strategy.onlyTradable,
      forbid_all_trade_at_limit: form.strategy.forbidAllTradeAtLimit,
      // TopkReallocation specific
      max_reallocation_rounds: form.strategy.maxReallocationRounds,
      log_prediction_details: form.strategy.logPredictionDetails,
      verbose: form.strategy.verbose
    }
    
    const result = await submitBacktest(backtestConfig)
    
    if (result.success) {
      ElMessage.success('回测任务已提交，正在执行中...')
      
      // 跳转到结果页面
      window.location.href = `/backtest/result?taskId=${result.data.taskId}`
    } else {
      ElMessage.error(result.message || '回测任务提交失败')
    }
  } catch (error) {
    console.error('提交回测失败:', error)
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

// 取消操作
const handleCancel = () => {
  ElMessageBox.confirm('确定要取消并返回吗？未保存的配置将丢失', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    window.location.href = '/backtest'
  }).catch(() => {})
}
</script>

<style scoped>
.backtest-config-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.config-card {
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
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.action-bar {
  margin-top: 30px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.action-bar .el-button {
  margin: 0 10px;
  min-width: 120px;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input-number .el-input__inner) {
  text-align: right;
}
</style>
