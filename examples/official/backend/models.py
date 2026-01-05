"""Pydantic models for API requests and responses"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# Stock Models
# ============================================================================

class StockCreate(BaseModel):
    code: str = Field(..., min_length=1, description="股票代码，格式: sh600000")
    name: str = Field(..., min_length=1, description="股票名称")
    is_a500: bool = Field(default=False, description="是否来自 A500")


class StockUpdate(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    is_a500: Optional[bool] = None


class StockResponse(StockCreate):
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime
    updated_at: datetime


class StockBatchOperation(BaseModel):
    """批量操作请求模型"""
    codes: List[str] = Field(..., description="股票代码列表")


# ============================================================================
# Position Models
# ============================================================================

class PositionCreate(BaseModel):
    code: str = Field(..., min_length=1, description="股票代码")
    quantity: float = Field(..., ge=0, description="持仓数量")
    cost_price: float = Field(..., ge=0, description="成本价")
    name: Optional[str] = Field(default="", description="股票名称")


class PositionUpdate(BaseModel):
    quantity: Optional[float] = None
    cost_price: Optional[float] = None
    name: Optional[str] = None


class PositionResponse(PositionCreate):
    market_value: float = Field(default=0.0, description="市值")
    pnl: float = Field(default=0.0, description="盈亏")
    pnl_percent: float = Field(default=0.0, description="盈亏百分比")
    added_at: datetime
    updated_at: datetime


class PositionBatchOperation(BaseModel):
    """批量操作请求模型"""
    codes: List[str] = Field(..., description="持仓代码列表")


# ============================================================================
# Agent Models
# ============================================================================

class AgentConfigCreate(BaseModel):
    agent_url: str = Field(..., description="代理 URL")
    agent_token: str = Field(..., description="代理 Token")
    agent_name: str = Field(default="Default Agent", description="代理名称")


class AgentConfigResponse(BaseModel):
    agent_id: str = Field(..., description="代理ID")
    agent_url: str
    agent_token: str
    agent_name: str
    is_primary: bool = Field(default=False, description="是否主用代理")
    status: str = Field(default="inactive", description="状态（active/inactive/unavailable）")
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AgentAssetInfo(BaseModel):
    account_id: str = Field(..., description="账号ID")
    total_assets: float = Field(..., description="总资产")
    available_cash: float = Field(..., description="可用资金")
    market_value: float = Field(..., description="市值")
    positions: List[dict] = Field(default_factory=list, description="持仓列表")
    updated_at: datetime


class AgentPosition(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    quantity: float = Field(..., description="持仓数量")
    cost_price: float = Field(..., description="成本价")
    market_value: float = Field(default=0.0, description="市值")
    pnl: float = Field(default=0.0, description="盈亏")
    pnl_percent: float = Field(default=0.0, description="盈亏百分比")


# ============================================================================
# Order Models
# ============================================================================

class AgentOrderSubmit(BaseModel):
    action: str = Field(..., description="操作类型（buy/sell/cancel）")
    stocks: List[dict] = Field(..., description="股票列表")
    timestamp: str = Field(default_factory=datetime.now().isoformat, description="时间戳")


class AgentOrder(BaseModel):
    order_id: str
    action: str
    code: str
    name: str
    price: float
    quantity: int
    status: str = Field(default="submitted", description="状态")
    created_at: datetime
    updated_at: datetime


class AgentOrdersResponse(BaseModel):
    total: int
    orders: List[AgentOrder]


# ============================================================================
# Prediction Models
# ============================================================================

class Prediction(BaseModel):
    date: str = Field(..., description="预测日期")
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    score: float = Field(..., description="预测得分")
    rank: int = Field(..., description="排名")
    is_held: bool = Field(default=False, description="是否持仓")
    created_at: datetime


# ============================================================================
# Trade Models
# ============================================================================

class TradeStocksRequest(BaseModel):
    stocks: List[str] = Field(..., description="持仓代码列表（支持多选）")


class TradeResponse(BaseModel):
    executed: int
    message: str


class TradeCandidatesItem(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    score: float = Field(..., description="预测得分")
    rank: int = Field(..., description="排名")
    is_held: bool = Field(default=False, description="是否持仓")
    position: Optional[dict] = None  # 持仓信息（如果有）


class TradeCandidates(BaseModel):
    items: List[TradeCandidatesItem]


# ============================================================================
# Log Models
# ============================================================================

class LogBatchDownload(BaseModel):
    """批量下载日志请求模型"""
    filenames: List[str] = Field(..., description="日志文件名列表")


# ============================================================================
# Data Download Models
# ============================================================================

class DataDownloadRequest(BaseModel):
    """数据下载请求模型"""
    start_date: Optional[str] = Field(default="2015-01-01", description="开始日期")
    end_date: Optional[str] = Field(default=None, description="结束日期")
    stocks: Optional[List[str]] = Field(default=None, description="股票代码列表")


class DataUpdateRequest(BaseModel):
    """数据更新请求模型"""
    stocks: Optional[List[str]] = Field(default=None, description="股票代码列表")
