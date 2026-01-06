"""Stock management API with import/export features"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from typing import List
from io import BytesIO
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import sys
import os

# 添加项目路径到 sys.path，确保能够导入 qlib
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database import MongoDB
from models import StockCreate, StockUpdate, StockResponse, StockBatchOperation
from services.data_service import standardize_stock_codes
from config import settings

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])


@router.get("/", response_model=List[StockResponse])
async def get_stocks(enabled_only: bool = False):
    """获取股票列表"""
    return await MongoDB.get_stocks(enabled_only=enabled_only)


@router.get("/export")
async def export_stocks(format: str = "csv"):
    """
    导出股票列表

    Args:
        format: 导出格式（csv/excel）

    Returns:
        文件响应（CSV或Excel）
    """
    try:
        stocks = await MongoDB.get_stocks()

        # 转换为 DataFrame
        df = pd.DataFrame(stocks)

        # 处理空列表的情况
        if df.empty:
            # 创建一个空的 DataFrame 包含正确的列（只包含 code 和 name）
            df = pd.DataFrame(columns=["code", "name"])
        else:
            # 只选择需要的列（仅 code 和 name）
            df = df[["code", "name"]]

        # 根据格式导出
        if format.lower() == "excel":
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="Stocks")
            output.seek(0)

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
            )
        else:
            # CSV 格式（默认）
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)

            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
    except Exception as e:
        logger.error(f"Failed to export stocks: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/import")
async def import_stocks(file: UploadFile = File(...)):
    """
    导入股票列表（支持 CSV 和 Excel）

    Args:
        file: 上传的文件（CSV 或 Excel）

    Returns:
        导入结果统计
    """
    try:
        content = await file.read()
        filename = file.filename.lower()

        # 读取文件
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(BytesIO(content), engine='openpyxl')
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式，请上传 CSV 或 Excel 文件")

        # 验证必需列（支持多种列名格式）
        # 优先匹配中文名称，避免匹配到英文名称
        code_col = None
        name_col = None

        # 查找代码列
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['code', '股票代码', 'stockcode', 'stock_code', '成份券代码', 'constituent code']:
                code_col = col
                break

        # 查找名称列（优先中文名称）
        # 1. 优先匹配常见的标准列名（英文）
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ['name', '股票名称']:
                name_col = col
                break

        # 2. 如果没找到，匹配"成份券名称"（但排除英文名列）
        if name_col is None:
            for col in df.columns:
                col_lower = col.lower().strip()
                if '成份券名称' in col or 'constituent name' in col_lower:
                    # 排除英文名称列
                    if 'eng' not in col_lower and 'english' not in col_lower and '(eng)' not in col_lower:
                        name_col = col
                        break

        if code_col is None or name_col is None:
            logger.error(f"CSV columns: {df.columns.tolist()}")
            logger.error(f"Found code_col: {code_col}, name_col: {name_col}")
            raise HTTPException(
                status_code=400,
                detail=f"CSV 格式不正确，无法找到代码或名称列。找到的列: {df.columns.tolist()}"
            )

        # 导入数据
        imported = 0
        updated = 0

        for _, row in df.iterrows():
            code = row[code_col]
            name = row[name_col]

            # 标准化代码格式
            code = standardize_stock_codes([code])[0]

            # 检查是否已存在
            existing = await MongoDB.get_stock(code)
            if existing:
                # 更新
                await MongoDB.update_stock(code, {
                    "name": name,
                    "enabled": row.get('enabled', True) if 'enabled' in row else True,
                    "is_a500": row.get('is_a500', False) if 'is_a500' in row else False,
                    "updated_at": datetime.utcnow()
                })
                updated += 1
            else:
                # 插入新股票
                await MongoDB.insert_stock({
                    "code": code,
                    "name": name,
                    "enabled": row.get('enabled', True) if 'enabled' in row else True,
                    "is_a500": row.get('is_a500', False) if 'is_a500' in row else False,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                imported += 1

        logger.info(f"Stocks imported: {imported} added, {updated} updated, total: {len(df)}")

        return {
            "message": f"成功导入股票: 新增 {imported} 个，更新 {updated} 个",
            "imported": imported,
            "updated": updated,
            "total": len(df)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import stocks: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/initialize")
async def initialize_stocks_from_csv():
    """
    重新初始化代码列表
    从 A500.csv 文件读取股票列表，清空现有数据并导入
    """
    try:
        from pathlib import Path

        csv_path = Path("A500.csv")
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="A500.csv 文件不存在")

        # 读取 A500.csv
        df = pd.read_csv(csv_path)

        # 检查列名是否存在（按优先级查找）
        code_col = None
        name_col = None

        # 查找代码列
        for col in df.columns:
            col_lower = col.lower()
            if '成份券代码' in col or 'constituent code' in col_lower:
                code_col = col
                break

        # 查找名称列（优先中文名称，避免匹配到英文名称）
        # 完全匹配优先：成份券名称Constituent Name
        for col in df.columns:
            if col == '成份券名称Constituent Name':
                name_col = col
                break

        # 如果没有完全匹配，查找包含"成份券名称"的列
        if name_col is None:
            for col in df.columns:
                col_lower = col.lower()
                # 包含"成份券名称"但不包含"英文名"或"(eng)"
                if '成份券名称' in col and 'eng' not in col_lower and 'english' not in col_lower:
                    name_col = col
                    break

        # 如果还没找到，尝试其他列名
        if name_col is None:
            for col in df.columns:
                col_lower = col.lower()
                if 'constituent name' in col_lower and 'eng' not in col_lower:
                    name_col = col
                    break

        if code_col is None or name_col is None:
            logger.error(f"A500.csv columns: {df.columns.tolist()}")
            logger.error(f"Found code_col: {code_col}, name_col: {name_col}")
            raise HTTPException(
                status_code=500,
                detail=f"A500.csv 格式不正确，无法找到股票代码或名称列。找到的列: {df.columns.tolist()}"
            )

        stock_codes = df[code_col].tolist()
        stock_names = df[name_col].tolist()

        logger.info(f"Found code column: {code_col}, name column: {name_col}")
        logger.info(f"Sample data: code={stock_codes[0] if stock_codes else 'N/A'}, name={stock_names[0] if stock_names else 'N/A'}")

        # 标准化股票代码格式
        standardized_codes = standardize_stock_codes(stock_codes)

        # 清空现有股票列表
        await MongoDB.clear_all_stocks()

        # 批量导入新股票
        imported = 0
        for code, name in zip(standardized_codes, stock_names):
            await MongoDB.insert_stock({
                "code": code,
                "name": name,
                "enabled": True,
                "is_a500": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
            imported += 1

        logger.info(f"Initialized {imported} stocks from A500.csv")

        return {
            "message": f"成功从 A500.csv 初始化 {imported} 个股票",
            "imported": imported,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize stocks: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@router.post("/", response_model=StockResponse, status_code=201)
async def create_stock(stock: StockCreate):
    """添加股票"""
    try:
        existing = await MongoDB.get_stock(stock.code)
        if existing:
            raise HTTPException(status_code=400, detail="股票已存在")

        stock_dict = stock.model_dump()
        stock_dict["created_at"] = datetime.utcnow()
        stock_dict["updated_at"] = datetime.utcnow()
        await MongoDB.insert_stock(stock_dict)

        logger.info(f"Created stock: {stock.code} - {stock.name}")
        return StockResponse(**stock_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create stock: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.delete("/{code}")
async def delete_stock(code: str):
    """删除股票"""
    try:
        success = await MongoDB.delete_stock(code)
        if not success:
            raise HTTPException(status_code=404, detail="股票不存在")

        logger.info(f"Deleted stock: {code}")
        return {"message": f"股票 {code} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete stock: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/{code}")
async def update_stock(code: str, stock: StockUpdate):
    """修改股票信息"""
    try:
        existing = await MongoDB.get_stock(code)
        if not existing:
            raise HTTPException(status_code=404, detail="股票不存在")

        update_dict = stock.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()

        await MongoDB.update_stock(code, update_dict)

        logger.info(f"Updated stock: {code}")
        return {"message": f"股票 {code} 已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update stock: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.put("/{code}/enable")
async def enable_stock(code: str, enabled: bool):
    """使能/去使能股票"""
    try:
        success = await MongoDB.update_stock(code, {"enabled": enabled})
        if not success:
            raise HTTPException(status_code=404, detail="股票不存在")

        logger.info(f"Stock {code} {'enabled' if enabled else 'disabled'}")
        return {"message": f"股票 {code} {'已启用' if enabled else '已禁用'}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable/disable stock: {e}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/batch")
async def batch_operations(operation: str, codes: List[str] = Body(..., embed=True)):
    """
    批量操作（支持多选和连续多选）

    Args:
        operation: 操作类型（enable/disable/delete）
        codes: 选中的股票代码列表（支持多选）

    Returns:
        操作结果统计
    """
    try:
        if operation == "enable":
            result = await MongoDB.batch_update_stocks(codes, {"enabled": True})
        elif operation == "disable":
            result = await MongoDB.batch_update_stocks(codes, {"enabled": False})
        elif operation == "delete":
            result = await MongoDB.batch_delete_stocks(codes)
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")

        logger.info(f"Batch operation {operation} on {len(codes)} stocks, modified: {result}")

        return {"modified_count": result, "operation": operation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed batch operation: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.get("/{code}/history")
async def get_stock_history(code: str, limit: int = 20):
    """
    获取股票历史数据

    Args:
        code: 股票代码
        limit: 返回记录数限制（默认20条）

    Returns:
        历史数据列表
    """
    try:
        # 检查股票是否存在
        stock = await MongoDB.get_stock(code)
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")

        # 导入 Qlib
        try:
            import qlib
            from qlib.data import D
            from qlib.config import REG_CN

            # 初始化 Qlib（如果尚未初始化）
            try:
                provider_uri = settings.QLIB_PROVIDER_URI
                region_config = REG_CN if settings.QLIB_REGION.upper() == "CN" else settings.QLIB_REGION
                qlib.init(provider_uri=provider_uri, region=region_config, redis_cache=None)
                logger.info(f"Qlib initialized for history query: {code}")
            except Exception as init_error:
                logger.warning(f"Qlib may already be initialized: {init_error}")

            # 查询历史数据
            # 获取最近 30 天的数据（确保足够 limit 条）
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            # 使用 Qlib 的 features API 查询数据
            fields = [
                "$open", "$close", "$high", "$low", "$volume", "$amount"
            ]

            try:
                df = D.features(
                    [code],
                    fields,
                    start_time=start_date,
                    end_time=end_date,
                    freq="day"
                )

                logger.info(f"Qlib returned DataFrame with columns: {df.columns.tolist()}, shape: {df.shape}")

                # 转换数据格式
                if df.empty:
                    logger.warning(f"No history data found for {code}")
                    return []

                # 重置索引，将日期列转为普通列
                df = df.reset_index()
                logger.info(f"DataFrame columns after reset: {df.columns.tolist()}")

                # 提取数据
                history = []
                
                # 检测实际的列名格式
                # Qlib 可能返回不同格式: '$open', '($open, code)', 或多级索引
                def get_column_value(row, field):
                    """灵活获取列值"""
                    possible_names = [
                        field,  # '$open'
                        f"({field}, {code})",  # '($open, code)'
                        f"({field}, '{code}')",  # "($open, 'code')"
                        field.replace('$', ''),  # 'open'
                    ]
                    for name in possible_names:
                        if name in row.index:
                            val = row[name]
                            if pd.notna(val):
                                return float(val)
                    return None
                
                for _, row in df.iterrows():
                    open_price = get_column_value(row, "$open")
                    close_price = get_column_value(row, "$close")
                    high_price = get_column_value(row, "$high")
                    low_price = get_column_value(row, "$low")
                    volume = get_column_value(row, "$volume")
                    amount = get_column_value(row, "$amount")

                    # 计算涨跌幅（change）
                    if close_price and open_price and open_price != 0:
                        change = (close_price - open_price) / open_price
                    else:
                        change = 0

                    # 获取日期
                    date_val = row.get("datetime") if "datetime" in row.index else row.get("date")
                    if pd.notna(date_val):
                        if hasattr(date_val, 'strftime'):
                            date_str = date_val.strftime("%Y-%m-%d")
                        else:
                            date_str = str(date_val)[:10]
                    else:
                        date_str = ""

                    history.append({
                        "date": date_str,
                        "open": open_price,
                        "close": close_price,
                        "high": high_price,
                        "low": low_price,
                        "volume": volume,
                        "amount": amount,
                        "change": change
                    })

                # 按日期降序排序，并限制返回数量
                history.sort(key=lambda x: x["date"], reverse=True)
                history = history[:limit]

                logger.info(f"Retrieved {len(history)} history records for {code}")
                return history

            except Exception as query_error:
                logger.error(f"Failed to query Qlib data for {code}: {query_error}")
                # 如果 Qlib 查询失败，尝试读取 CSV 文件
                return await _read_history_from_csv(code, limit)

        except ImportError as import_error:
            logger.warning(f"Failed to import qlib: {import_error}")
            # 如果无法导入 Qlib，尝试读取 CSV 文件
            return await _read_history_from_csv(code, limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stock history for {code}: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")


async def _read_history_from_csv(code: str, limit: int) -> List[dict]:
    """
    从 CSV 文件读取历史数据（备用方法）

    Args:
        code: 股票代码
        limit: 返回记录数限制

    Returns:
        历史数据列表
    """
    try:
        from pathlib import Path
        import pandas as pd

        # 查找 CSV 文件
        provider_uri = Path(settings.QLIB_PROVIDER_URI).expanduser()
        metadata_file = provider_uri / "metadata" / f"{code}.json"

        if not metadata_file.exists():
            logger.warning(f"Metadata file not found for {code}")
            return []

        # 读取元数据获取日期范围
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # 尝试从 normalize 目录读取 CSV
        normalize_dir = provider_uri / "features" / code
        csv_files = list(normalize_dir.glob("*.csv")) if normalize_dir.exists() else []

        if csv_files:
            csv_path = csv_files[0]
            df = pd.read_csv(csv_path)

            # 转换为历史数据格式
            history = []
            for _, row in df.tail(limit).iterrows():
                history.append({
                    "date": row.get("date", ""),
                    "open": float(row.get("open", 0)) if pd.notna(row.get("open")) else None,
                    "close": float(row.get("close", 0)) if pd.notna(row.get("close")) else None,
                    "high": float(row.get("high", 0)) if pd.notna(row.get("high")) else None,
                    "low": float(row.get("low", 0)) if pd.notna(row.get("low")) else None,
                    "volume": float(row.get("volume", 0)) if pd.notna(row.get("volume")) else None,
                    "amount": float(row.get("amount", 0)) if pd.notna(row.get("amount")) else None,
                    "change": float(row.get("change", 0)) if pd.notna(row.get("change")) else 0
                })

            # 按日期降序排序
            history.sort(key=lambda x: x["date"], reverse=True)
            return history
        else:
            logger.warning(f"No CSV files found for {code}")
            return []

    except Exception as e:
        logger.error(f"Failed to read history from CSV for {code}: {e}")
        return []

