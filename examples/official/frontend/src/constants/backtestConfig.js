/**
 * 回测配置常量
 * 定义回测的默认参数值
 */

/**
 * 回测默认配置
 */
export const DEFAULT_BACKTEST_CONFIG = {
  // 基础配置
  initialCapital: 100, // 初始资金（万元）
  market: 'csi300', // 市场：csi300 / csi500 / all
  
  // 日期范围
  trainStart: '2020-01-01', // 训练开始日期
  trainEnd: '2024-12-31', // 训练结束日期
  testStart: '2025-01-01', // 测试开始日期
  testEnd: '2025-12-30', // 测试结束日期
  
  // 交易费用配置
  buyCommission: 0.0005, // 买入费率 0.05%
  sellCommission: 0.0015, // 卖出费率 0.15%
  minCommission: 5, // 最低手续费 5元
  limitThreshold: 0.095, // 涨跌停阈值 9.5%
  dealPrice: 'close', // 交易价格：close（收盘价）
  
  // 策略类型
  strategyType: 'topk_dropout_with_reallocation', // topk_dropout / topk_dropout_with_reallocation
  
  // TopkDropoutStrategy 参数
  strategy: {
    topk: 50, // 持仓股票数量
    nDrop: 5, // 每次调仓替换数
    methodSell: 'bottom', // 卖出方法：bottom（评分最低）/ random（随机）
    methodBuy: 'top', // 买入方法：top（评分最高）/ random（随机）
    holdThresh: 1, // 持仓最小天数
    onlyTradable: false, // 只考虑可交易股票
    forbidAllTradeAtLimit: true, // 涨跌停禁止交易
    
    // TopkDropoutWithReallocation 额外参数
    maxReallocationRounds: 3, // 最大再分配轮数
    verbose: true, // 输出详细日志
    logPredictionDetails: true, // 输出预测详情
  }
}

/**
 * 市场选项
 */
export const MARKET_OPTIONS = [
  { label: '沪深300', value: 'csi300' },
  { label: '中证500', value: 'csi500' },
  { label: '全市场', value: 'all' }
]

/**
 * 策略类型选项
 */
export const STRATEGY_OPTIONS = [
  { label: 'TopkDropout', value: 'topk_dropout' },
  { label: 'TopkDropoutWithReallocation', value: 'topk_dropout_with_reallocation' }
]

/**
 * 卖出/买入方法选项
 */
export const METHOD_OPTIONS = [
  { label: '评分最高/最低', value: 'top' },
  { label: '随机', value: 'random' }
]

/**
 * 交易价格选项
 */
export const DEAL_PRICE_OPTIONS = [
  { label: '开盘价', value: 'open' },
  { label: '收盘价', value: 'close' }
]
