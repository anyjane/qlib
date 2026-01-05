"""Log management API"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from datetime import datetime
from loguru import logger
from config import settings
from models import LogBatchDownload

router = APIRouter(prefix="/api/logs", tags=["Logs"])


def get_log_dir():
    """获取日志目录（运行时动态获取）"""
    return Path(settings.LOG_DIR)


@router.get("/")
async def list_logs():
    """列出所有日志文件"""
    try:
        log_dir = get_log_dir()
        if not log_dir.exists():
            return []

        log_files = []
        for file in log_dir.glob("*.log"):
            stat = file.stat()
            log_files.append({
                "filename": file.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            })

        # 按修改时间倒序排列
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        return log_files
    except Exception as e:
        logger.error(f"Failed to list logs: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/download/{filename}")
async def download_log(filename: str):
    """下载单个日志文件"""
    try:
        from fastapi.responses import FileResponse

        log_dir = get_log_dir()
        log_path = log_dir / filename
        if not log_path.exists():
            raise HTTPException(status_code=404, detail="日志文件不存在")

        return FileResponse(
            path=log_path,
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download log: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.post("/download/batch")
async def download_logs_batch(request: LogBatchDownload):
    """批量下载日志（打包为 ZIP）"""
    try:
        from fastapi.responses import StreamingResponse
        import zipfile
        from io import BytesIO

        log_dir = get_log_dir()
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in request.filenames:
                log_path = log_dir / filename
                if log_path.exists():
                    zipf.write(log_path, arcname=filename)

        zip_buffer.seek(0)

        zip_filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
    except Exception as e:
        logger.error(f"Failed to download logs batch: {e}")
        raise HTTPException(status_code=500, detail=f"批量下载失败: {str(e)}")
