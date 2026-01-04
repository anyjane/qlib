"""Tencent data download service"""
from typing import List
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd
from loguru import logger

from config import settings
from database import MongoDB


__all__ = ['TencentDataService', 'standardize_stock_codes']


class TencentDataService:
    """腾讯数据下载服务"""

    BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    REQUEST_TIMEOUT = 30

    @staticmethod
    def standardize_stock_codes(codes: List[str]) -> List[str]:
        """
        标准化股票代码格式

        将数字股票代码转换为 Qlib 需要的格式：
        - 上海股票（60开头，688开头）：sh600000
        - 深圳股票（00开头，30开头）：sz000001

        Args:
            codes: 原始股票代码列表

        Returns:
            标准化后的股票代码列表
        """
        standardized = []
        for code in codes:
            code_str = str(code).zfill(6)  # 补零到6位
            if code_str.startswith('6') or code_str.startswith('688'):
                # 上海股票
                standardized.append(f'sh{code_str}')
            elif code_str.startswith('00') or code_str.startswith('30'):
                # 深圳股票
                standardized.append(f'sz{code_str}')
            else:
                logger.warning(f"Unknown stock code format: {code_str}")
        return standardized

    @staticmethod
    async def create_download_task(start_date: str, end_date: str, stocks: List[str]) -> str:
        """创建下载任务并保存到 MongoDB"""
        task_id = f"download_{datetime.now().timestamp()}"
        await MongoDB.insert_data_task({
            "task_id": task_id,
            "status": "pending",
            "start_date": start_date,
            "end_date": end_date or datetime.now().strftime("%Y-%m-%d"),
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def create_update_task(stocks: List[str]) -> str:
        """创建更新任务并保存到 MongoDB"""
        task_id = f"update_{datetime.now().timestamp()}"
        await MongoDB.insert_data_task({
            "task_id": task_id,
            "status": "pending",
            "start_date": None,
            "end_date": None,
            "stocks": stocks or [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        return task_id

    @staticmethod
    async def get_latest_data_date() -> str:
        """获取最新数据日期"""
        try:
            # 这里应该从 Qlib 获取最新数据日期
            # 暂时返回当前日期
            return datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Failed to get latest data date: {e}")
            return None

    @staticmethod
    async def download_from_tencent(stocks: List[str], start: str, end: str) -> dict:
        """从腾讯 API 下载数据"""
        data_dict = {}
        for code in stocks:
            try:
                # 构造请求参数
                param = f"{code},day,{start},{end},2000,qfq"
                url = f"{TencentDataService.BASE_URL}?param={param}"
                response = requests.get(url, timeout=TencentDataService.REQUEST_TIMEOUT)
                response.raise_for_status()
                data_dict[code] = response.json()
            except Exception as e:
                logger.error(f"Failed to download {code}: {e}")
        return data_dict
