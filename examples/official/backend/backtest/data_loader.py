"""Features 数据加载器"""
import struct
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger


class FeaturesDataLoader:
    """
    从 backend/qlib_data/features 目录加载特征数据

    直接读取 .bin 文件，绕过 Qlib 的数据集构建流程
    """

    def __init__(self, data_dir: str):
        """
        初始化数据加载器

        Args:
            data_dir: Qlib 数据目录路径
        """
        self.data_dir = Path(data_dir).expanduser()
        self.features_dir = self.data_dir / "features"
        self.calendars_dir = self.data_dir / "calendars"
        self.instruments_dir = self.data_dir / "instruments"

        # 缓存交易日历和股票池
        self._calendar: List[str] = None
        self._instruments: Dict[str, List[Tuple]] = None

    def load_calendar(self) -> List[str]:
        """
        加载交易日历

        Returns:
            交易日列表 (YYYY-MM-DD)
        """
        if self._calendar is not None:
            return self._calendar

        calendar_path = self.calendars_dir / "day.txt"
        if not calendar_path.exists():
            raise FileNotFoundError(f"Calendar file not found: {calendar_path}")

        with open(calendar_path, 'r') as f:
            self._calendar = [line.strip() for line in f if line.strip()]

        logger.info(f"Loaded {len(self._calendar)} trading days from calendar")
        return self._calendar

    def load_instruments(self, market: str = "all") -> List[str]:
        """
        加载股票池

        Args:
            market: 市场类型（all/csi300/csi500）

        Returns:
            股票代码列表
        """
        if self._instruments is None:
            self._instruments = {}

        if market not in self._instruments:
            instruments_path = self.instruments_dir / f"{market}.txt"
            if not instruments_path.exists():
                raise FileNotFoundError(f"Instruments file not found: {instruments_path}")

            instruments = []
            with open(instruments_path, 'r') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        code = parts[0]
                        start_date = parts[1]
                        end_date = parts[2]
                        instruments.append((code, start_date, end_date))

            self._instruments[market] = instruments
            logger.info(f"Loaded {len(instruments)} instruments for market: {market}")

        return [code for code, _, _ in self._instruments[market]]

    def load_stock_data(
        self,
        stock_code: str,
        features: List[str] = None,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, np.ndarray]:
        """
        加载单个股票的特征数据

        Args:
            stock_code: 股票代码（如 sh600000）
            features: 要加载的特征列表（默认全部）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {feature_name: data_array} 特征数据字典
        """
        if features is None:
            features = ["open", "close", "high", "low", "volume", "amount", "change", "factor"]

        stock_dir = self.features_dir / stock_code.lower()
        if not stock_dir.exists():
            logger.warning(f"Stock data directory not found: {stock_dir}")
            return {}

        data = {}
        for feature in features:
            bin_path = stock_dir / f"{feature}.day.bin"
            if not bin_path.exists():
                continue

            start_index, values = self._read_bin_file(bin_path)

            # 处理日期范围
            calendar = self.load_calendar()
            if start_date or end_date:
                date_indices = self._get_date_indices(
                    calendar, start_date, end_date, start_index
                )
                if date_indices:
                    values = values[date_indices]

            data[feature] = values

        return data

    def _read_bin_file(self, bin_path: Path) -> Tuple[int, np.ndarray]:
        """
        读取 Qlib .bin 文件

        Args:
            bin_path: .bin 文件路径

        Returns:
            (start_index, data_array)
        """
        try:
            with open(bin_path, 'rb') as f:
                # 读取起始索引（前4字节，float32）
                index_bytes = f.read(4)
                if len(index_bytes) == 4:
                    start_index = int(np.frombuffer(index_bytes, dtype='<f')[0])
                else:
                    start_index = 0

                # 读取数据
                f.seek(0, 2)  # 移到文件末尾
                file_size = f.tell()
                data_count = (file_size - 4) // 4 if file_size > 4 else 0

                f.seek(4)  # 回到数据起始位置
                data = np.fromfile(f, dtype='<f', count=data_count)

            return start_index, data
        except Exception as e:
            logger.error(f"Failed to read bin file {bin_path}: {e}")
            return 0, np.array([])

    def _get_date_indices(
        self,
        calendar: List[str],
        start_date: str = None,
        end_date: str = None,
        start_index: int = 0,
    ) -> np.ndarray:
        """
        获取日期范围对应的索引数组

        Args:
            calendar: 交易日历
            start_date: 开始日期
            end_date: 结束日期
            start_index: 数据起始索引

        Returns:
            索引数组
        """
        if start_date is None and end_date is None:
            return np.arange(len(calendar))

        start_idx = 0
        end_idx = len(calendar)

        if start_date:
            try:
                start_idx = calendar.index(start_date) - start_index
                if start_idx < 0:
                    start_idx = 0
            except ValueError:
                start_idx = 0

        if end_date:
            try:
                end_idx = calendar.index(end_date) - start_index + 1
                if end_idx > len(calendar):
                    end_idx = len(calendar)
            except ValueError:
                end_idx = len(calendar)

        return np.arange(start_idx, end_idx)

    def get_available_stocks(self) -> List[str]:
        """
        获取所有可用的股票代码

        Returns:
            股票代码列表
        """
        if not self.features_dir.exists():
            return []

        stocks = []
        for item in self.features_dir.iterdir():
            if item.is_dir():
                stocks.append(item.name.upper())

        logger.info(f"Found {len(stocks)} stocks in features directory")
        return sorted(stocks)

    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票数据信息

        Args:
            stock_code: 股票代码

        Returns:
            股票信息字典
        """
        stock_dir = self.features_dir / stock_code.lower()
        if not stock_dir.exists():
            return {"has_data": False}

        # 读取收盘价数据作为参考
        close_path = stock_dir / "close.day.bin"
        if not close_path.exists():
            return {"has_data": False}

        start_index, values = self._read_bin_file(close_path)

        calendar = self.load_calendar()

        # 计算日期范围
        data_len = len(values)
        if data_len == 0:
            return {"has_data": False}

        start_idx = int(start_index)
        end_idx = start_idx + data_len

        start_date = calendar[start_idx] if start_idx < len(calendar) else None
        end_date = calendar[end_idx - 1] if end_idx > 0 and end_idx <= len(calendar) else None

        return {
            "has_data": True,
            "start_index": start_index,
            "end_index": end_idx,
            "start_date": start_date,
            "end_date": end_date,
            "count": data_len,
        }
