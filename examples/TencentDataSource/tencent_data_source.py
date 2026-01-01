# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Tencent Data Source Collector
Fetches stock data from Tencent's HTTP API with pagination support
"""

import sys
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import numpy as np
from loguru import logger

# Set up sys.path BEFORE any imports
CUR_DIR = Path(__file__).resolve().parent
QLIB_ROOT = CUR_DIR.parent.parent
sys.path.insert(0, str(QLIB_ROOT))
sys.path.insert(0, str(QLIB_ROOT / "scripts"))

# Direct import - will fail if data_collector is not available
from data_collector.base import BaseCollector, BaseNormalize, BaseRun

# Configure loguru - output to both console and file
log_dir = CUR_DIR / "logs"
log_dir.mkdir(exist_ok=True)

# Generate timestamp for log filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"tencent_data_{timestamp}.log"

# Remove default handler
logger.remove()

# Add console handler with colored output
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Add file handler with timestamp
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# Configure standard logging (for BaseRun and other modules)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

logger.info(f"Logging initialized. Log file: {log_file}")


class TencentCollector(BaseCollector):
    """
    Collector for fetching stock data from Tencent's HTTP API

    API URL: https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
    Format: param={symbol},{interval},{start_date},{end_date},{count},{qfq}
    Example: param=sh512290,day,2024-01-01,2025-12-31,2000,qfq

    Note: Tencent API limits to 2000 records per request.
    Pagination is implemented to fetch more than 2000 records.
    """

    BASE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    INTERVAL_DAY = "day"
    REQUEST_TIMEOUT = 30
    RETRY_COUNT = 3
    RETRY_DELAY = 1

    def __init__(
        self,
        save_dir: str,
        start=None,
        end=None,
        interval="day",
        max_workers=1,
        max_collector_count=2,
        delay=0,
        check_data_length=None,
        limit_nums=None,
    ):
        """
        Initialize Tencent collector

        Parameters
        ----------
        save_dir : str
            Directory to save collected data
        start : str, optional
            Start date (default: 2000-01-01)
        end : str, optional
            End date (default: today)
        interval : str, optional
            Data interval: "day" or "1min" (default: "day")
        max_workers : int, optional
            Number of concurrent workers (default: 1, recommended)
        max_collector_count : int, optional
            Max retry attempts for failed requests (default: 2)
        delay : float, optional
            Delay between requests in seconds (default: 0)
        check_data_length : int, optional
            Minimum required data length (default: None)
        limit_nums : int, optional
            Limit number of stocks to fetch for debugging (default: None)
        """
        logger.info(f"Initializing TencentCollector with save_dir={save_dir}, interval={interval}")
        super().__init__(
            save_dir=save_dir,
            start=start,
            end=end,
            interval=interval,
            max_workers=max_workers,
            max_collector_count=max_collector_count,
            delay=delay,
            check_data_length=check_data_length,
            limit_nums=limit_nums,
        )

        self.interval = interval
        logger.info(f"TencentCollector initialized. Instrument list size: {len(self.instrument_list)}")

    def get_instrument_list(self) -> List[str]:
        """
        Get list of stock symbols to collect

        Returns
        -------
        List[str]
            List of stock symbols (e.g., ["sh600000", "sz000001"])
        """
        # Read A500 stock list from CSV file
        logger.info("Getting instrument list from A500 CSV file")
        
        csv_file = Path(__file__).parent / "a500.csv"
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file, encoding='utf-8')
            
            # Extract constituent codes (成份券代码 column)
            if "成份券代码Constituent Code" not in df.columns:
                logger.error(f"Column '成份券代码Constituent Code' not found in CSV")
                logger.info(f"Available columns: {df.columns.tolist()}")
                return []
            
            stock_codes = df["成份券代码Constituent Code"].dropna().unique().tolist()
            logger.info(f"Loaded {len(stock_codes)} unique stock codes from A500 CSV")
            
            # Convert to Tencent API format (pad to 6 digits and add prefix)
            tencent_symbols = []
            for code in stock_codes:
                code_str = str(code).strip()
                
                # Pad to 6 digits with leading zeros
                code_str = code_str.zfill(6)
                
                # Add prefix based on first digit
                if code_str.startswith('6'):
                    # Shanghai stocks start with 6
                    tencent_symbols.append(f"sh{code_str}")
                elif code_str.startswith('0') or code_str.startswith('3'):
                    # Shenzhen stocks start with 0 or 3
                    tencent_symbols.append(f"sz{code_str}")
                else:
                    logger.warning(f"Unknown stock code format: {code_str}")
            
            # Remove duplicates and sort
            tencent_symbols = sorted(list(set(tencent_symbols)))
            logger.info(f"Converted to {len(tencent_symbols)} Tencent format symbols")
            
            return tencent_symbols
            
        except Exception as e:
            logger.error(f"Failed to load instruments from CSV: {e}")
            logger.info("Using fallback sample stocks")
            # Fallback to a small sample
            return [
                "sh600000", "sh600519", "sh601318", "sh601939", "sh600030",
                "sz000001", "sz000002", "sz000651", "sz002594", "sz002415",
            ]

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol for API request

        Parameters
        ----------
        symbol : str
            Stock symbol in Qlib format (e.g., "sh600000")

        Returns
        -------
        str
            Normalized symbol for Tencent API (e.g., "sh600000")
        """
        # Tencent API expects format like "sh600000" or "sz000001"
        # Qlib already uses this format, so no conversion needed
        return symbol.lower()

    def _convert_qlib_symbol_to_tencent(self, qlib_symbol: str) -> str:
        """
        Convert Qlib symbol to Tencent API format

        Parameters
        ----------
        qlib_symbol : str
            Symbol in Qlib format (e.g., "SH600000")

        Returns
        -------
        str
            Symbol in Tencent format (e.g., "sh600000")
        """
        # Qlib uses uppercase (SH600000), Tencent uses lowercase (sh600000)
        return qlib_symbol.lower()

    def get_data(
        self,
        symbol: str,
        interval: str,
        start_datetime: pd.Timestamp,
        end_datetime: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Fetch data from Tencent API with pagination support

        Parameters
        ----------
        symbol : str
            Stock symbol
        interval : str
            Data interval ("day" or "1min")
        start_datetime : pd.Timestamp
            Start date
        end_datetime : pd.Timestamp
            End date

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: date, open, close, high, low, volume
        """
        logger.info(f"Fetching data for {symbol} from {start_datetime.date()} to {end_datetime.date()}")

        # Convert symbol to Tencent format
        tencent_symbol = self._convert_qlib_symbol_to_tencent(symbol)

        # Pagination logic: fetch data in chunks if needed
        all_data = []
        current_end_date = end_datetime
        fetch_count = 0
        max_fetches = 20  # Safety limit to prevent infinite loops

        while fetch_count < max_fetches:
            fetch_count += 1
            logger.info(f"Fetch attempt {fetch_count} for {symbol}, end_date: {current_end_date.date()}")

            # Format dates for API
            start_date_str = start_datetime.strftime("%Y-%m-%d")
            end_date_str = current_end_date.strftime("%Y-%m-%d")

            # Build API parameter string
            # Format: {symbol},{interval},{start},{end},{count},{qfq}
            # Use 2000 as count to get max records per request
            # qfq means "qian fu quan" (前复权, forward adjustment)
            param_str = f"{tencent_symbol},{interval},{start_date_str},{end_date_str},2000,qfq"

            # Make request
            data = self._fetch_from_api(param_str)

            if data is None or len(data) == 0:
                logger.warning(f"No data returned for {symbol} with params {param_str}")
                break

            all_data.extend(data)
            logger.info(f"Fetched {len(data)} records for {symbol} (total: {len(all_data)})")

            # Check if we need to fetch more data
            # Get the oldest date from current batch (first record is oldest)
            oldest_date_str = data[0][0]  # First element of first record is date
            try:
                oldest_date = pd.Timestamp(oldest_date_str)
            except Exception as e:
                logger.error(f"Failed to parse date {oldest_date_str}: {e}")
                break

            logger.info(f"Oldest date in this batch: {oldest_date.date()}, Requested start: {start_datetime.date()}")

            # Check if we have reached or passed the start date
            # If oldest_date is after start_datetime, there may be more data
            if oldest_date > start_datetime:
                # Need to fetch more data
                # Set new end_date to day before oldest date in current batch
                current_end_date = oldest_date - pd.Timedelta(days=1)
                logger.info(f"Still have earlier data, fetching before {current_end_date.date()}")
            else:
                # Reached or passed the start date, we have all data
                logger.info(f"Reached start date {start_datetime.date()}, finished fetching: {len(all_data)} records total")
                break

        if fetch_count >= max_fetches:
            logger.warning(f"Reached max fetch limit ({max_fetches}) for {symbol}, may have incomplete data")

        # Convert to DataFrame
        if len(all_data) == 0:
            logger.warning(f"No data available for {symbol}")
            return pd.DataFrame()

        # Normalize and filter data
        # Handle special cases like dividend records that contain dict objects
        normalized_data = []
        for i, record in enumerate(all_data):
            if len(record) < 6:
                logger.warning(f"Skipping record {i} with insufficient columns: {len(record)}")
                continue
            
            # Check if any column is a dict (dividend info, etc.)
            # Take only the first 6 columns (date, open, close, high, low, volume)
            filtered_record = []
            for j, col in enumerate(record[:6]):
                if isinstance(col, dict):
                    logger.debug(f"Skipping dict column {j} in record {i}: {col}")
                    break
                filtered_record.append(col)
            
            # Ensure we have exactly 6 columns
            if len(filtered_record) == 6:
                normalized_data.append(filtered_record)
            else:
                logger.warning(f"Skipping record {i} after filtering: got {len(filtered_record)} columns")
        
        if len(normalized_data) == 0:
            logger.warning(f"No valid data after filtering for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(normalized_data, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
        logger.info(f"Created DataFrame with {len(df)} rows after filtering {len(all_data)} raw records")
        df['date'] = pd.to_datetime(df['date'])
        df['symbol'] = symbol

        # Filter by date range (in case pagination returned extra data)
        df = df[(df['date'] >= start_datetime) & (df['date'] <= end_datetime)]
        df = df.sort_values('date').reset_index(drop=True)

        logger.info(f"Final data for {symbol}: {len(df)} records from {df['date'].min()} to {df['date'].max()}")
        return df

    def _fetch_from_api(self, param_str: str) -> Optional[List]:
        """
        Fetch data from Tencent API with retry logic

        Parameters
        ----------
        param_str : str
            API parameter string

        Returns
        -------
        Optional[List]
            List of data records if successful, None otherwise
        """
        url = f"{self.BASE_URL}?param={param_str}"

        for attempt in range(self.RETRY_COUNT):
            try:
                logger.debug(f"Fetching from URL: {url} (attempt {attempt + 1}/{self.RETRY_COUNT})")

                response = requests.get(
                    url,
                    timeout=self.REQUEST_TIMEOUT,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()

                # Parse JSON response
                json_data = response.json()

                # Tencent API response structure:
                # {
                #   "data": {
                #     "sh600000": {
                #       "qfqday": [
                #         ["2025-01-02", "10.50", "10.60", "10.70", "10.45", "1000000", "10500000"],
                #         ...
                #       ]
                #     }
                #   }
                # }

                if "data" not in json_data:
                    logger.warning(f"No 'data' field in API response: {json_data}")
                    return None

                # Get the first key (symbol) from data
                data_dict = json_data["data"]
                if not data_dict:
                    logger.warning(f"Empty data dict in API response")
                    return None

                symbol_key = list(data_dict.keys())[0]
                symbol_data = data_dict[symbol_key]

                if "qfqday" not in symbol_data:
                    logger.warning(f"No 'qfqday' field in symbol data for {symbol_key}")
                    return None

                # Extract kline data
                kline_data = symbol_data["qfqday"]
                if not kline_data:
                    logger.warning(f"Empty kline data for {symbol_key}")
                    return None

                logger.debug(f"Successfully fetched {len(kline_data)} records")
                return kline_data

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for URL: {url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")

            if attempt < self.RETRY_COUNT - 1:
                time.sleep(self.RETRY_DELAY * (attempt + 1))

        logger.error(f"Failed to fetch data after {self.RETRY_COUNT} attempts: {url}")
        return None


class TencentNormalize(BaseNormalize):
    """
    Normalize Tencent data to Qlib format
    """

    COLUMNS = ["open", "close", "high", "low", "volume"]

    def __init__(
        self,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
        calendar_list=None,
        **kwargs
    ):
        super().__init__(date_field_name, symbol_field_name, **kwargs)
        self.calendar_list = calendar_list

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize Tencent data to Qlib format

        Parameters
        ----------
        df : pd.DataFrame
            Raw data from Tencent API

        Returns
        -------
        pd.DataFrame
            Normalized data in Qlib format
        """
        logger.debug(f"Normalizing data for symbol: {df[self._symbol_field_name].iloc[0] if len(df) > 0 else 'unknown'}")

        if df.empty:
            return df

        df = df.copy()

        # Ensure required columns exist
        required_cols = ["date", "open", "close", "high", "low", "volume"]
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"Missing required column: {col}")
                return pd.DataFrame()

        # Set date as index
        df = df.set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        # Convert numeric columns
        numeric_cols = ["open", "close", "high", "low", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Remove duplicates
        df = df[~df.index.duplicated(keep="first")]

        # Reindex to calendar if provided
        if self.calendar_list is not None and len(self.calendar_list) > 0:
            df = df.reindex(self.calendar_list)

        # Fill or handle missing values
        # Volume should be 0 for missing data
        df["volume"] = df["volume"].fillna(0)

        # Price columns forward fill, then backward fill
        price_cols = ["open", "close", "high", "low"]
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col].ffill().bfill()

        # Calculate change (daily return)
        df["change"] = df["close"].pct_change()
        df["change"] = df["change"].replace([float("inf"), -float("inf")], np.nan).fillna(0)

        # Reset index
        df = df.reset_index()
        df.rename(columns={"index": "date"}, inplace=True)

        logger.debug(f"Normalized data: {len(df)} records")
        return df

    def _get_calendar_list(self):
        """Get benchmark calendar"""
        # For simplicity, return None (use data's own dates)
        # In production, this could fetch from Qlib's calendar
        return None


class TencentRun(BaseRun):
    """
    Run class for Tencent data collection
    """

    def __init__(self, source_dir=None, normalize_dir=None, max_workers=1, interval="day"):
        """
        Override parent __init__ to avoid importing 'collector' module
        Use the current module instead
        """
        # Set _cur_module to current module instead of importing "collector"
        self._cur_module = sys.modules[__name__]
        self.max_workers = max_workers
        self.interval = interval

        # Initialize directories (same as parent)
        if source_dir is None:
            source_dir = Path(self.default_base_dir).joinpath("source")
        self.source_dir = Path(source_dir).expanduser().resolve()
        self.source_dir.mkdir(parents=True, exist_ok=True)

        if normalize_dir is None:
            normalize_dir = Path(self.default_base_dir).joinpath("normalize")
        self.normalize_dir = Path(normalize_dir).expanduser().resolve()
        self.normalize_dir.mkdir(parents=True, exist_ok=True)

    @property
    def default_base_dir(self):
        """Default base directory for data storage"""
        return Path(__file__).parent

    @property
    def collector_class_name(self):
        """Name of collector class"""
        return "TencentCollector"

    @property
    def normalize_class_name(self):
        """Name of normalize class"""
        return "TencentNormalize"


if __name__ == "__main__":
    # Test the collector
    import fire

    # Create run instance
    run = TencentRun()

    # Example: download data
    fire.Fire({
        "download_data": run.download_data,
        "normalize_data": run.normalize_data,
    })
