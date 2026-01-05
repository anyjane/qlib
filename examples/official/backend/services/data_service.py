"""Tencent data download service"""
from typing import List
from datetime import datetime
from pathlib import Path
import os
import sys
import shutil
import requests
import pandas as pd
import numpy as np
from loguru import logger
import subprocess

# 统一从 config 模块获取配置
from config import settings
QLIB_PROVIDER_URI = settings.QLIB_PROVIDER_URI

__all__ = ['TencentDataService', 'standardize_stock_codes']


def standardize_stock_codes(codes: List[str]) -> List[str]:
    """
    标准化股票代码格式（模块级别函数）

    将数字股票代码转换为 Qlib 需要的格式：
    - 上海股票（60开头，688开头）：sh600000
    - 深圳股票（00开头，30开头）：sz000001

    Args:
        codes: 原始股票代码列表

    Returns:
        标准化后的股票代码列表
    """
    return TencentDataService.standardize_stock_codes(codes)


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

        如果已经是标准格式（sh或sz前缀），直接返回

        Args:
            codes: 原始股票代码列表

        Returns:
            标准化后的股票代码列表
        """
        standardized = []
        for code in codes:
            code_str = str(code).lower().strip()

            # 如果已经是标准格式（sh开头或sz开头），直接使用
            if code_str.startswith('sh') or code_str.startswith('sz'):
                standardized.append(code_str)
                continue

            # 否则，按数字格式处理
            code_num = code_str.zfill(6)  # 补零到6位
            if code_num.startswith('6') or code_num.startswith('688'):
                # 上海股票
                standardized.append(f'sh{code_num}')
            elif code_num.startswith('00') or code_num.startswith('30'):
                # 深圳股票
                standardized.append(f'sz{code_num}')
            else:
                logger.warning(f"Unknown stock code format: {code_num}")
        return standardized

    @staticmethod
    async def create_download_task(start_date: str, end_date: str, stocks: List[str]) -> str:
        """创建下载任务并保存到 MongoDB"""
        from database import MongoDB
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
        from database import MongoDB
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
    def download_from_tencent(stocks: List[str], start: str, end: str) -> dict:
        """
        从腾讯 API 下载数据（支持分页）

        腾讯 API 限制每次最多返回 2000 条记录，需要分页获取完整数据。

        Args:
            stocks: 股票代码列表
            start: 开始日期（YYYY-MM-DD）
            end: 结束日期（YYYY-MM-DD）

        Returns:
            dict: {股票代码: 完整的K线数据列表}
        """
        data_dict = {}
        for code in stocks:
            try:
                # 分页获取数据
                all_data = []
                current_end_date = pd.Timestamp(end)
                start_timestamp = pd.Timestamp(start)
                fetch_count = 0
                max_fetches = 20  # 安全限制，防止无限循环

                logger.info(f"开始下载 {code} 的数据，从 {start} 到 {end}，最大条目: {max_fetches}")

                while fetch_count < max_fetches:
                    fetch_count += 1
                    end_date_str = current_end_date.strftime("%Y-%m-%d")

                    # 构造请求参数
                    # start 为空表示从最早开始，腾讯 API 会返回最多 count 条数据
                    # 格式: {symbol},{interval},{start},{end},{count},{qfq}
                    param = f"{code},day,,{end_date_str},2000,qfq"
                    url = f"{TencentDataService.BASE_URL}?param={param}"

                    logger.debug(f"[{code}] 第 {fetch_count} 次请求，参数: start=空, end={end_date_str}, count=2000")

                    response = requests.get(
                        url,
                        timeout=TencentDataService.REQUEST_TIMEOUT,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                    )
                    response.raise_for_status()
                    json_data = response.json()

                    # 解析响应数据
                    if "data" not in json_data or not json_data["data"]:
                        logger.warning(f"[{code}] 响应中没有数据")
                        break

                    symbol_data = json_data["data"][code]
                    if "qfqday" in symbol_data:
                        kline_data = symbol_data["qfqday"]
                    elif "day" in symbol_data:
                        kline_data = symbol_data["day"]
                    else:
                        logger.warning(f"[{code}] 响应中没有K线数据")
                        break

                    if not kline_data or len(kline_data) == 0:
                        logger.warning(f"[{code}] K线数据为空")
                        break

                    # 添加到总数据中（注意：腾讯 API 返回的数据是按时间升序排列的）
                    all_data.extend(kline_data)
                    logger.info(f"[{code}] 获取到 {len(kline_data)} 条记录，累计 {len(all_data)} 条")

                    # 检查是否需要继续获取
                    # 获取这批数据中最旧的日期（第一条是最旧的，数据是升序排列）
                    oldest_date_str = kline_data[0][0]
                    try:
                        oldest_date = pd.Timestamp(oldest_date_str)
                    except Exception as e:
                        logger.error(f"[{code}] 解析日期失败: {oldest_date_str}, {e}")
                        break

                    logger.info(f"[{code}] 本批次最旧日期: {oldest_date_str}，请求开始日期: {start}")

                    # 如果最旧的日期仍然晚于开始日期，需要继续往前获取
                    if oldest_date > start_timestamp:
                        # 设置新的结束日期为最旧日期的前一天
                        current_end_date = oldest_date - pd.Timedelta(days=1)
                        logger.debug(f"[{code}] 需要继续获取，新的截止日期: {current_end_date.strftime('%Y-%m-%d')}")
                    else:
                        # 已经到达或超过开始日期，获取完成
                        logger.info(f"[{code}] 已到达开始日期 {start}，获取完成")
                        break

                if fetch_count >= max_fetches:
                    logger.warning(f"[{code}] 达到最大请求次数 {max_fetches}，数据可能不完整")

                # 按日期排序（从旧到新）并去重
                if all_data:
                    # 使用日期去重
                    seen_dates = set()
                    unique_data = []
                    for record in all_data:
                        if record[0] not in seen_dates:
                            seen_dates.add(record[0])
                            unique_data.append(record)

                    # 按日期排序（从旧到新）
                    unique_data.sort(key=lambda x: x[0])

                    # 过滤日期范围
                    filtered_data = [
                        record for record in unique_data
                        if start_timestamp <= pd.Timestamp(record[0]) <= pd.Timestamp(end)
                    ]

                    logger.info(f"[{code}] 去重后 {len(unique_data)} 条，过滤后 {len(filtered_data)} 条")
                    data_dict[code] = {
                        "data": {
                            code: {
                                "qfqday": filtered_data
                            }
                        },
                        "count": len(filtered_data)
                    }
                else:
                    logger.warning(f"[{code}] 没有获取到任何数据")
                    data_dict[code] = {"data": {}, "count": 0}

            except Exception as e:
                logger.error(f"Failed to download {code}: {e}")
                data_dict[code] = {"data": {}, "count": 0, "error": str(e)}

        return data_dict

    @staticmethod
    def save_data_to_qlib_format(data_dict: dict, download_ranges: dict, end_date: str, use_update_mode: bool = False) -> dict:
        """
        将下载的数据保存为 Qlib 格式

        Args:
            data_dict: {股票代码: API响应数据}
            download_ranges: {股票代码: {start: 开始日期, end: 结束日期}} 或 start_date: 统一开始日期
            end_date: 结束日期
            use_update_mode: 是否使用 dump_update 模式（增量更新）

        Returns:
            dict: {股票代码: 保存结果}
        """
        results = {}
        qlib_dir = Path(QLIB_PROVIDER_URI).expanduser()

        # 创建临时目录
        temp_dir = qlib_dir / "temp_download"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 归一化数据目录
        normalize_dir = temp_dir / "normalize"
        normalize_dir.mkdir(parents=True, exist_ok=True)

        # 收集所有需要更新的股票代码
        updated_codes = []

        for code, response_data in data_dict.items():
            try:
                if response_data.get("count", 0) == 0 or "data" not in response_data or not response_data["data"]:
                    logger.warning(f"[{code}] 没有可保存的数据")
                    results[code] = {"success": False, "error": "No data"}
                    continue

                # 提取 K 线数据
                if code not in response_data["data"]:
                    logger.warning(f"[{code}] 响应中没有该股票的数据")
                    results[code] = {"success": False, "error": "Code not in response"}
                    continue

                symbol_data = response_data["data"][code]
                if "qfqday" not in symbol_data and "day" not in symbol_data:
                    logger.warning(f"[{code}] 响应中没有 K 线数据")
                    results[code] = {"success": False, "error": "No kline data"}
                    continue

                kline_data = symbol_data.get("qfqday") or symbol_data.get("day")

                # 获取该股票的实际下载日期范围
                if isinstance(download_ranges, dict) and code in download_ranges:
                    code_start_date = download_ranges[code]["start"]
                    logger.info(f"[{code}] 使用实际下载日期范围: {code_start_date} 到 {end_date}")
                elif isinstance(download_ranges, str):
                    code_start_date = download_ranges
                    logger.info(f"[{code}] 使用统一日期范围: {code_start_date} 到 {end_date}")
                else:
                    code_start_date = "2015-01-01"
                    logger.info(f"[{code}] 使用默认日期范围: {code_start_date} 到 {end_date}")

                # 转换为 DataFrame
                # 数据格式: [日期, 开盘, 收盘, 最高, 最低, 成交量]
                # 动态检测列数，可能有些记录有额外字段
                if len(kline_data) == 0:
                    logger.warning(f"[{code}] K线数据为空")
                    results[code] = {"success": False, "error": "Empty kline data"}
                    continue

                # 检查所有记录的列数是否一致
                column_counts = [len(record) for record in kline_data]
                unique_counts = set(column_counts)
                if len(unique_counts) > 1:
                    logger.warning(f"[{code}] 数据列数不一致: {unique_counts}，使用最常见的列数")
                    num_cols = max(set(column_counts), key=column_counts.count)
                else:
                    num_cols = unique_counts.pop()

                column_names = ['date', 'open', 'close', 'high', 'low', 'volume']
                if num_cols == 7:
                    # 可能有 amount 字段
                    column_names = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
                elif num_cols > 7:
                    logger.warning(f"[{code}] 数据有 {num_cols} 列，超过预期，只使用前7列")
                    column_names = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount']
                elif num_cols < 6:
                    logger.error(f"[{code}] 数据列数不足: {num_cols}，至少需要6列")
                    results[code] = {"success": False, "error": f"Insufficient columns: {num_cols}"}
                    continue

                # 只使用实际存在的列数的数据
                if num_cols > len(column_names):
                    num_cols = len(column_names)
                df = pd.DataFrame([record[:num_cols] for record in kline_data], columns=column_names[:num_cols])

                # 转换数据类型
                df['date'] = pd.to_datetime(df['date'])
                numeric_cols = [col for col in column_names if col != 'date']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 去除重复
                df = df.drop_duplicates('date')

                # 按日期排序
                df = df.sort_values('date').reset_index(drop=True)

                # 过滤日期范围（使用实际下载的日期范围）
                start_ts = pd.Timestamp(code_start_date)
                end_ts = pd.Timestamp(end_date)
                df = df[(df['date'] >= start_ts) & (df['date'] <= end_ts)]

                if df.empty:
                    logger.warning(f"[{code}] 过滤后数据为空")
                    results[code] = {"success": False, "error": "Data empty after filtering"}
                    continue

                # 添加 symbol 列（Qlib 需要）
                df['symbol'] = code

                # 计算变化率
                df['change'] = df['close'].pct_change()
                df['change'] = df['change'].replace([np.inf, -np.inf], np.nan).fillna(0)

                # 添加 factor 列（Qlib 需要）
                df['factor'] = 1.0

                # 如果没有 amount 列，计算成交额
                if 'amount' not in df.columns:
                    df['amount'] = df['close'] * df['volume']

                # 保存为 CSV
                csv_path = normalize_dir / f"{code}.csv"
                df.to_csv(csv_path, index=False)

                # 记录需要更新的股票代码
                updated_codes.append(code)

                logger.info(f"[{code}] 保存了 {len(df)} 条数据到 {csv_path}")
                results[code] = {"success": True, "count": len(df)}

            except Exception as e:
                logger.error(f"[{code}] 保存数据失败: {e}")
                results[code] = {"success": False, "error": str(e)}

        # 将所有 CSV 转换为 Qlib 二进制格式
        try:
            logger.info(f"开始将数据转换为 Qlib 格式，目标目录: {qlib_dir}")

            # 只在 dump_fix 模式（非更新）下删除旧数据
            # dump_update 模式下需要保留旧数据以便追加
            if not use_update_mode:
                # 只对有新数据的股票删除旧数据
                for code in updated_codes:
                    instrument_path = qlib_dir / "features" / code
                    if instrument_path.exists():
                        shutil.rmtree(instrument_path)
                        logger.info(f"[{code}] 删除旧数据（dump_fix 模式）")
            else:
                logger.info("使用 dump_update 模式，保留旧数据以进行追加")

            # 使用 dump_bin.py 脚本来转换数据
            # 由于 dump_bin 有复杂的依赖，使用 subprocess 调用更可靠
            dump_script = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "dump_bin.py"

            # 检查 calendar 文件是否存在（用于判断是否为首次数据导入）
            calendar_file = qlib_dir / "calendars" / "day.txt"
            instruments_file = qlib_dir / "instruments" / "all.txt"
            
            # 选择正确的 dump 模式：
            # - dump_all: 首次导入，创建所有基础文件（calendars, instruments）
            # - dump_fix: 添加新股票到现有数据库
            # - dump_update: 更新现有股票的数据（追加新日期）
            if not calendar_file.exists() or not instruments_file.exists():
                # 首次导入数据，使用 dump_all
                mode = "dump_all"
                logger.info("首次数据导入，使用 dump_all 模式")
            elif use_update_mode:
                # 增量更新现有股票数据
                mode = "dump_update"
                logger.info("使用 dump_update 模式进行增量更新")
            else:
                # 添加新股票或重新下载
                mode = "dump_fix"
                logger.info("使用 dump_fix 模式添加/更新股票数据")

            cmd = [
                sys.executable,
                str(dump_script),
                mode,
                "--data_path", str(normalize_dir),
                "--qlib_dir", str(qlib_dir),
                "--freq", "day",
                "--date_field_name", "date",
                "--symbol_field_name", "symbol",
                "--include_fields", "open,close,high,low,volume,amount,change,factor",
                "--max_workers", "1"
            ]

            logger.info(f"执行 {mode} 命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                logger.error(f"dump_bin 执行失败: {result.stderr}")
                raise Exception(f"dump_bin failed with return code {result.returncode}")
            else:
                logger.info("数据转换完成")

        except subprocess.TimeoutExpired:
            logger.error("dump_bin 执行超时")
            raise Exception("dump_bin execution timeout")
        except Exception as e:
            logger.warning(f"转换数据到 Qlib 格式失败: {e}")
            logger.warning("数据已保存为 CSV 格式，但未转换为 Qlib 二进制格式")

        # 清理临时文件
        try:
            shutil.rmtree(temp_dir)
            logger.info("清理临时文件完成")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

        return results
    
    @staticmethod
    async def get_stock_data_info(code: str) -> dict:
        """
        从文件系统检查股票数据信息（不初始化 Qlib）

        读取 instruments/all.txt 获取日期范围
        通过二进制文件大小计算数据条数
        """
        try:
            data_path = Path(QLIB_PROVIDER_URI).expanduser()
            
            # 标准化代码格式用于匹配（全大写，因为 instruments 文件用大写）
            code_upper = code.upper()
            if not code_upper.startswith('SZ') and not code_upper.startswith('SH'):
                # 如果是 sz000001 格式，转为 SZ000001
                code_upper = code.upper()
            
            instrument_path = data_path / "features" / code
            
            if not instrument_path.exists():
                return {"has_data": False}

            # 检查是否有数据文件（.bin 文件）
            bin_files = list(instrument_path.glob("*.bin"))
            
            if not bin_files:
                return {"has_data": False}

            # 计算数据条数：从 close.day.bin 文件计算
            # Qlib 二进制格式：4字节起始索引 + N个4字节浮点数
            record_count = 0
            close_bin = instrument_path / "close.day.bin"
            if close_bin.exists():
                file_size = close_bin.stat().st_size
                # 减去4字节的起始索引，剩余的每4字节是一条记录
                record_count = (file_size - 4) // 4 if file_size > 4 else 0
            
            # 从 instruments/all.txt 读取日期范围
            start_date = None
            end_date = None
            instruments_file = data_path / "instruments" / "all.txt"
            
            if instruments_file.exists():
                with open(instruments_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            # 格式: SZ000009	2015-01-07	2025-12-31
                            inst_code = parts[0].lower()  # 转为小写比较
                            if inst_code == code.lower():
                                start_date = parts[1]
                                end_date = parts[2]
                                break

            return {
                "has_data": True,
                "start_date": start_date,
                "end_date": end_date,
                "count": record_count
            }

        except Exception as e:
            logger.error(f"Failed to get data info for {code}: {e}")
            return {"has_data": False}
    
    @staticmethod
    async def delete_stock_data(code: str):
        """删除 Qlib 数据文件"""
        data_path = Path(QLIB_PROVIDER_URI).expanduser()

        # 删除 features 目录下的股票数据（Qlib 的实际数据存储位置）
        instrument_path = data_path / "features" / code

        if instrument_path.exists():
            shutil.rmtree(instrument_path)
            logger.info(f"Deleted Qlib data for stock: {code}")
        else:
            logger.warning(f"Qlib data not found for stock: {code}")
