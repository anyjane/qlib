"""Backend configuration for Quantitative Investment Management System"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Quantitative Investment Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017/"
    MONGODB_DB_NAME: str = "quant_system_db"

    # Qlib
    QLIB_PROVIDER_URI: str = str(Path(__file__).parent / "qlib_data")
    QLIB_REGION: str = "cn"

    # Qlib Online Mode
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_TASK_DB: int = 1
    EXPRESSION_CACHE: str = "DiskExpressionCache"
    DATASET_CACHE: str = "DiskDatasetCache"
    LOCAL_CACHE_PATH: str = str(Path(__file__).parent / "qlib_data" / ".cache" / "qlib_simple_cache")

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # Tencent Data API
    TENCENT_API_BASE_URL: str = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    TENCENT_API_TIMEOUT: int = 30

    # Data Tasks
    DATA_START_DATE: str = "2015-01-01"

    # Prediction
    MODEL_NAME: str = "lightgbm_model"
    NUM_PROCESSES: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create log directory if it doesn't exist
os.makedirs(settings.LOG_DIR, exist_ok=True)
