"""Position management API with trading operations"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime
from loguru import logger

from ..database import MongoDB
from ..models import PositionCreate, PositionUpdate

router = APIRouter(prefix="/api/positions", tags=["Positions"])


@router.get("/")
async def get_positions():
    """获取持仓列表"""
    try:
        return await MongoDB.get_positions()
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/")
async def create_position(position: PositionCreate):
    """添加持仓"""
    try:
        # 检查是否已存在
        existing = await MongoDB.get_position(position.code)
        if existing:
            raise HTTPException(status_code=400, detail="持仓已存在")

        # 从数据库获取股票名称
        stock = await MongoDB.get_stock(position.code)
        if stock:
            position.name = stock["name"]

        position_dict = position.dict()
        position_dict["added_at"] = datetime.utcnow()
        position_dict["updated_at"] = datetime.utcnow()
        position_dict["market_value"] = position_dict["quantity"] * position_dict["cost_price"]

        await MongoDB.insert_position(position_dict)

        logger.info(f"Created position: {position.code} - {position.quantity}")
        return {"message": f"持仓 {position.code} 已添加"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create position: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.put("/{code}")
async def update_position(code: str, position: PositionUpdate):
    """修改持仓（数量、成本价等）"""
    try:
        # 从数据库获取股票名称
        stock = await MongoDB.get_stock(code)
        if stock:
            position.name = stock["name"]

        update_dict = position.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()

        if position.name is not None:
            update_dict["name"] = position.name

        # 重新计算市值
        existing = await MongoDB.get_position(code)
        if existing and "quantity" in update_dict and "cost_price" in update_dict:
            update_dict["market_value"] = update_dict["quantity"] * update_dict["cost_price"]

        success = await MongoDB.update_position(code, update_dict)
        if not success:
            raise HTTPException(status_code=404, detail="持仓不存在")

        logger.info(f"Updated position: {code}")
        return {"message": f"持仓 {code} 已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update position: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{code}")
async def delete_position(code: str):
    """删除持仓"""
    try:
        success = await MongoDB.delete_position(code)
        if not success:
            raise HTTPException(status_code=404, detail="持仓不存在")

        logger.info(f"Deleted position: {code}")
        return {"message": f"持仓 {code} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete position: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/import")
async def import_positions(file: UploadFile = File(...)):
    """导入持仓（CSV 格式）"""
    try:
        import pandas as pd
        from io import BytesIO

        content = await file.read()
        df = pd.read_csv(BytesIO(content))

        imported = 0
        for _, row in df.iterrows():
            try:
                position = PositionCreate(
                    code=row["code"],
                    quantity=row["quantity"],
                    cost_price=row["cost_price"],
                    name=row.get("name", "")
                )

                # 检查是否已存在
                existing = await MongoDB.get_position(position.code)
                if not existing:
                    position_dict = position.dict()
                    position_dict["added_at"] = datetime.utcnow()
                    position_dict["updated_at"] = datetime.utcnow()
                    position_dict["market_value"] = position_dict["quantity"] * position_dict["cost_price"]
                    await MongoDB.insert_position(position_dict)
                    imported += 1
            except Exception as e:
                logger.error(f"Failed to import position: {e}")

        logger.info(f"Imported {imported} positions from CSV")

        return {
            "message": f"成功导入 {imported} 个持仓",
            "imported": imported,
            "total": len(df)
        }
    except Exception as e:
        logger.error(f"Failed to import positions: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/batch")
async def batch_operations(operation: str, codes: List[str], update_data: dict = None):
    """
    批量操作（支持多选和连续多选）

    Args:
        operation: 操作类型（delete/update）
        codes: 选中的持仓代码列表
        update_data: 更新数据（仅用于 update 操作）

    Returns:
        操作结果统计
    """
    try:
        if operation == "delete":
            result = await MongoDB.batch_delete_positions(codes)
        elif operation == "update" and update_data:
            result = await MongoDB.batch_update_positions(codes, update_data)
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")

        logger.info(f"Batch operation {operation} on {len(codes)} positions, modified: {result}")

        return {"modified_count": result, "operation": operation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed batch operation: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.post("/sync")
async def sync_positions():
    """
    从交易代理同步持仓到本地数据库

    Returns:
        同步结果统计
    """
    try:
        from ..services.agent_service import AgentService

        # 获取代理持仓
        primary_agent = await AgentService.get_primary_agent()
        if not primary_agent:
            raise HTTPException(status_code=503, detail="没有可用的主用代理")

        # 获取代理持仓
        response = await AgentService.get_agent_positions(primary_agent['agent_id'])

        # 清空本地持仓
        await MongoDB.clear_all_local_positions()

        # 同步代理持仓到本地
        imported = 0
        for agent_pos in response.get("positions", []):
            # 检查是否已存在
            existing = await MongoDB.get_position(agent_pos["code"])

            if existing:
                # 更新持仓信息
                await MongoDB.update_position(
                    agent_pos["code"],
                    {
                        "quantity": agent_pos["quantity"],
                        "cost_price": agent_pos["cost_price"],
                        "market_value": agent_pos["market_value"],
                        "updated_at": datetime.utcnow(),
                    }
                )
            else:
                # 插入新持仓
                await MongoDB.insert_position({
                    "code": agent_pos["code"],
                    "name": agent_pos["name"],
                    "quantity": agent_pos["quantity"],
                    "cost_price": agent_pos["cost_price"],
                    "market_value": agent_pos["market_value"],
                    "pnl": agent_pos.get("pnl", 0.0),
                    "pnl_percent": agent_pos.get("pnl_percent", 0.0),
                    "added_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
                imported += 1

        logger.info(f"Synced {imported} positions from agent")

        return {
            "message": f"成功从代理同步 {imported} 个持仓",
            "imported": imported,
            "total": len(response.get("positions", []))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync positions: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")
