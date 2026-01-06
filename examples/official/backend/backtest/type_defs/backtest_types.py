"""回测相关类型定义"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# 策略类型枚举
# ============================================================================

class StrategyType(str, Enum):
    """策略类型枚举"""
    TOPK_DROPOUT = "topk_dropout"
    TOPK_REALLOCATION = "topk_reallocation"


class MethodType(str, Enum):
    """买卖方法枚举"""
    TOP = "top"
    BOTTOM = "bottom"
    RANDOM = "random"


# ============================================================================
# 回测配置
# ============================================================================

class BacktestConfig(BaseModel):
    """回测配置"""
    # 基础配置
    initial_capital: float = Field(default=100.0, ge=0, description="初始资金（万元）")
    market: str = Field(default="csi300", description="市场选择（all/csi300/csi500）")

    # 日期配置
    train_start: str = Field(default="2020-01-01", description="训练开始日期")
    train_end: str = Field(default="2024-12-31", description="训练结束日期")
    test_start: str = Field(default="2025-01-01", description="测试开始日期")
    test_end: str = Field(default="2025-12-30", description="测试结束日期")

    # 交易费用配置
    buy_rate: float = Field(default=0.0005, ge=0, description="买入费率")
    sell_rate: float = Field(default=0.0015, ge=0, description="卖出费率")
    min_commission: float = Field(default=5.0, ge=0, description="最低手续费（元）")
    limit_threshold: float = Field(default=0.095, ge=0, le=1, description="涨跌停阈值")
    deal_price: str = Field(default="close", description="交易价格类型（close/open/high/low）")

    # 策略配置
    strategy_type: StrategyType = Field(default=StrategyType.TOPK_REALLOCATION, description="策略类型")
    topk: int = Field(default=50, ge=1, description="持仓数量")
    n_drop: int = Field(default=5, ge=1, description="每次调仓替换数")
    hold_thresh: int = Field(default=1, ge=1, description="持仓最小天数")
    method_sell: MethodType = Field(default=MethodType.BOTTOM, description="卖出方法")
    method_buy: MethodType = Field(default=MethodType.TOP, description="买入方法")
    only_tradable: bool = Field(default=False, description="只考虑可交易股票")
    forbid_all_trade_at_limit: bool = Field(default=True, description="涨跌停禁止交易")

    # TopkReallocation 策略特有参数
    max_reallocation_rounds: int = Field(default=3, ge=0, description="最大再分配轮数（仅reallocation策略）")

    # 日志配置
    log_prediction_details: bool = Field(default=True, description="是否输出预测详情")
    verbose: bool = Field(default=True, description="是否输出详细日志")


# ============================================================================
# 交易详情
# ============================================================================

class BuyDetail(BaseModel):
    """买入详情"""
    code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    prediction_score: float = Field(..., description="预测得分")
    amount: int = Field(..., description="买入数量（股）")
    price: float = Field(..., description="买入单价")
    value: float = Field(..., description="买入金额")
    commission: float = Field(..., description="交易费用")
    cash_before: float = Field(..., description="交易前资金")
    cash_after: float = Field(..., description="交易后资金")


class SellDetail(BaseModel):
    """卖出详情"""
    code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    prediction_score: float = Field(..., description="预测得分")
    amount: int = Field(..., description="卖出数量（股）")
    price: float = Field(..., description="卖出价格")
    value: float = Field(..., description="卖出金额")
    commission: float = Field(..., description="交易费用")
    actual_received: float = Field(..., description="实际收拢资金（扣除费用后）")
    cash_before: float = Field(..., description="交易前资金")
    cash_after: float = Field(..., description="交易后资金")


class PositionDetail(BaseModel):
    """持仓详情"""
    code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    prediction_score: float = Field(..., description="预测得分")
    rank: int = Field(..., description="排名")
    amount: int = Field(..., description="持仓数量")
    cost_price: float = Field(..., description="成本价")
    current_price: float = Field(..., description="当前价格")
    value: float = Field(..., description="市值")


class TopStock(BaseModel):
    """TopK 股票"""
    code: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    prediction_score: float = Field(..., description="预测得分")
    rank: int = Field(..., description="排名")


class DailyTradeLog(BaseModel):
    """每日交易日志"""
    trade_date: str = Field(..., description="交易日期")

    # 预测得分最高的股票
    top_stocks: List[TopStock] = Field(default_factory=list, description="预测得分最高的TopK股票")

    # 当前持仓
    current_positions: List[PositionDetail] = Field(default_factory=list, description="当前持仓")

    # 买入操作
    buys: List[BuyDetail] = Field(default_factory=list, description="买入操作")

    # 卖出操作
    sells: List[SellDetail] = Field(default_factory=list, description="卖出操作")

    # 资金信息
    cash_before: float = Field(..., description="交易前资金")
    cash_after: float = Field(..., description="交易后资金")
    total_value: float = Field(..., description="总资产（现金+持仓市值）")


# ============================================================================
# 回测结果
# ============================================================================

class BacktestMetrics(BaseModel):
    """回测指标"""
    # 无成本指标
    annual_return_no_cost: float = Field(..., description="年化收益率（无成本）")
    sharpe_ratio_no_cost: float = Field(..., description="夏普比率（无成本）")
    max_drawdown_no_cost: float = Field(..., description="最大回撤（无成本）")

    # 有成本指标
    annual_return_with_cost: float = Field(..., description="年化收益率（有成本）")
    sharpe_ratio_with_cost: float = Field(..., description="夏普比率（有成本）")
    max_drawdown_with_cost: float = Field(..., description="最大回撤（有成本）")

    # 交易统计
    total_trades: int = Field(default=0, description="总交易次数")
    buy_trades: int = Field(default=0, description="买入次数")
    sell_trades: int = Field(default=0, description="卖出次数")
    total_commission: float = Field(default=0.0, description="总交易费用")

    # 资金统计
    initial_capital: float = Field(..., description="初始资金")
    final_capital: float = Field(..., description="最终资金")
    total_return: float = Field(..., description="总收益率")


class EquityPoint(BaseModel):
    """资金曲线点"""
    date: str = Field(..., description="日期")
    cash: float = Field(..., description="现金")
    stock_value: float = Field(..., description="股票市值")
    total_value: float = Field(..., description="总资产")


class BacktestResult(BaseModel):
    """回测结果"""
    # 元数据
    task_id: str = Field(..., description="任务ID")
    experiment_name: str = Field(..., description="实验名称")
    backtest_date: datetime = Field(default_factory=datetime.now, description="回测日期")

    # 配置
    config: BacktestConfig = Field(..., description="回测配置")

    # 指标
    metrics: BacktestMetrics = Field(..., description="回测指标")

    # 详细日志
    trade_logs: List[DailyTradeLog] = Field(default_factory=list, description="每日交易日志")

    # 资金曲线
    equity_curve: List[EquityPoint] = Field(default_factory=list, description="资金曲线")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# ============================================================================
# API 请求/响应
# ============================================================================

class BacktestRequest(BaseModel):
    """回测请求"""
    config: BacktestConfig = Field(..., description="回测配置")


class BacktestResponse(BaseModel):
    """回测响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="状态（started/running/completed/failed）")
    message: str = Field(default="", description="消息")


class StrategyInfo(BaseModel):
    """策略信息"""
    type: StrategyType = Field(..., description="策略类型")
    name: str = Field(..., description="策略名称")
    description: str = Field(..., description="策略描述")
    params: Dict[str, Any] = Field(default_factory=dict, description="支持参数")
