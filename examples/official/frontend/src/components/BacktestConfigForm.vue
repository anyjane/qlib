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
          @click="saveConfig"
        >
          {{ submitting ? '保存中...' : '保存并更新参数' }}
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
import { useRouter } from 'vue-router'
import { submitBacktest, getBacktestConfig, saveBacktestConfig } from '../api/backtest'
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

const router = useRouter()
// 提交状态
const submitting = ref(false)
const configFormRef = ref(null)

// 加载配置
const loadConfig = async () => {
  try {
    const savedConfig = await getBacktestConfig()
    if (savedConfig && Object.keys(savedConfig).length > 0) {
      // 映射 snake_case 到 camelCase (如果后端存的是 snake_case)
      // 但这里我们存的时候是 snake_case，所以回显时需要反向映射或者统一格式
      // 假设我们存的是 snake_case (即 backtestConfig 对象)，我们需要转换回 form 结构
      // 或者更简单：我们修改 saveBacktestConfig 存的是 form 结构 (camelCase)
      // 让我们看看 saveConfig 怎么写的。
      // 下面的 saveConfig 会构造 snake_case 对象。为了方便前端回显，
      // 我们其实应该存 frontend-friendly config (camelCase) 或者做好 mapping
      // 为简单起见，我修改 saveConfig 存 camelCase 的 form 对象，这样回显最容易
      // 且后端只是当做 JSON 存，不校验内部结构？ 
      // 不，后端 validation 需要 snake_case.
      // 所以我们必须做 mapping.
      
      form.initialCapital = savedConfig.initial_capital || form.initialCapital
      form.market = savedConfig.market || form.market
      form.trainStart = savedConfig.train_start || form.trainStart
      form.trainEnd = savedConfig.train_end || form.trainEnd
      form.testStart = savedConfig.test_start || form.testStart
      form.testEnd = savedConfig.test_end || form.testEnd
      form.buyCommission = savedConfig.buy_rate!==undefined ? savedConfig.buy_rate : form.buyCommission
      form.sellCommission = savedConfig.sell_rate!==undefined ? savedConfig.sell_rate : form.sellCommission
      form.minCommission = savedConfig.min_commission!==undefined ? savedConfig.min_commission : form.minCommission
      form.strategyType = savedConfig.strategy_type || form.strategyType
      
      // Strategy params
      form.strategy.topk = savedConfig.topk || form.strategy.topk
      form.strategy.nDrop = savedConfig.n_drop || form.strategy.nDrop
      form.strategy.holdThresh = savedConfig.hold_thresh || form.strategy.holdThresh
      form.strategy.methodSell = savedConfig.method_sell || form.strategy.methodSell
      form.strategy.methodBuy = savedConfig.method_buy || form.strategy.methodBuy
      form.strategy.onlyTradable = savedConfig.only_tradable!==undefined ? savedConfig.only_tradable : form.strategy.onlyTradable
      form.strategy.forbidAllTradeAtLimit = savedConfig.forbid_all_trade_at_limit!==undefined ? savedConfig.forbid_all_trade_at_limit : form.strategy.forbidAllTradeAtLimit
      form.strategy.maxReallocationRounds = savedConfig.max_reallocation_rounds!==undefined ? savedConfig.max_reallocation_rounds : form.strategy.maxReallocationRounds
      form.strategy.logPredictionDetails = savedConfig.log_prediction_details!==undefined ? savedConfig.log_prediction_details : form.strategy.logPredictionDetails
      form.strategy.verbose = savedConfig.verbose!==undefined ? savedConfig.verbose : form.strategy.verbose
      
      ElMessage.success('已加载保存的配置')
    }
  } catch (error) {
    console.error('加载配置失败', error)
  }
}

onMounted(() => {
  loadConfig()
})

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

// 保存配置
const saveConfig = async () => {
  if (!configFormRef.value) return
  
  try {
    await configFormRef.value.validate()
  } catch (error) {
    console.error('表单验证失败:', error)
    return
  }
  
  submitting.value = true
  
  try {
    // 构建回测配置对象 (snake_case for backend)
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
    
    await saveBacktestConfig(backtestConfig)
    ElMessage.success('配置已保存')
    
    // 可选：保存后留在这里，或者返回
    // 根据用户习惯，可能是保存并返回
    // 但按钮叫 "保存并更新参数"
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存失败，请稍后重试')
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
    router.push('/backtest')
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
