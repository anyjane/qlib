"""Stock management API with import/export features"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from typing import List
from io import BytesIO
import pandas as pd
from datetime import datetime
from loguru import logger

from database import MongoDB
from models import StockCreate, StockUpdate, StockResponse, StockBatchOperation
from services.data_service import standardize_stock_codes

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
            # 创建一个空的 DataFrame 包含正确的列
            df = pd.DataFrame(columns=["code", "name", "enabled", "is_a500"])
        else:
            # 只选择需要的列
            df = df[["code", "name", "enabled", "is_a500"]]

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

        # 验证必需列
        required_columns = {'code', 'name'}
        if not required_columns.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"缺少必需的列: {required_columns}")

        # 标准化股票代码格式
        df['code'] = standardize_stock_codes(df['code'].tolist())

        # 导入数据
        imported = 0
        updated = 0

        for _, row in df.iterrows():
            code = row['code']
            name = row['name']

            # 检查是否已存在
            existing = await MongoDB.get_stock(code)
            if existing:
                # 更新
                await MongoDB.update_stock(code, {
                    "name": name,
                    "enabled": row.get('enabled', True),
                    "is_a500": row.get('is_a500', False),
                    "updated_at": datetime.utcnow()
                })
                updated += 1
            else:
                # 插入新股票
                await MongoDB.insert_stock({
                    "code": code,
                    "name": name,
                    "enabled": row.get('enabled', True),
                    "is_a500": row.get('is_a500', False),
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
        stock_codes = df['成份券代码Constituent Code'].tolist()
        stock_names = df['成份券名称Constituent Name'].tolist()

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
