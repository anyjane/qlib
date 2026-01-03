# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Example script to demonstrate the complete TencentDataSource workflow
This script collects data, runs training and backtesting, and outputs results
"""

import sys
from pathlib import Path

import fire

# Add current directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tencent_data_source import TencentRun, logger
from workflow import run_tencent_workflow

# Note: Logging is configured in tencent_data_source.py


def collect_data(
    source_dir: str = "~/.qlib/tencent_data/source",
    normalize_dir: str = "~/.qlib/tencent_data/normalize",
    qlib_dir: str = "~/.qlib/tencent_data/qlib_data",
    start: str = "2020-01-01",
    end: str = "2025-12-31",
    skip_dump: bool = False,
):
    """
    Step 1: Collect data from Tencent API

    Parameters
    ----------
    source_dir : str
        Directory to save raw data from API
    normalize_dir : str
        Directory to save normalized data
    qlib_dir : str
        Directory to save Qlib format data
    start : str
        Start date for data collection
    end : str
        End date for data collection
    skip_dump : bool
        Skip dumping to Qlib format if True
    """
    logger.info("=" * 80)
    logger.info("STEP 1: COLLECTING DATA FROM TENCENT API")
    logger.info("=" * 80)
    logger.info(f"Date range: {start} to {end}")

    # Initialize runner
    run = TencentRun(
        source_dir=source_dir,
        normalize_dir=normalize_dir,
    )

    # Download data
    logger.info("Downloading data...")
    run.download_data(
        start=start,
        end=end,
        max_collector_count=2,
        delay=0,
    )
    logger.info("Data download completed")

    # Normalize data
    logger.info("Normalizing data...")
    run.normalize_data(
        date_field_name="date",
        symbol_field_name="symbol",
    )
    logger.info("Data normalization completed")
    
    # Dump to Qlib format
    if not skip_dump:
        logger.info("Dumping data to Qlib format...")

        # Import dump_bin
        scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            from dump_bin import DumpDataAll

            # Dump data
            dumper = DumpDataAll(
                data_path=normalize_dir,
                qlib_dir=qlib_dir,
                freq="day",
                date_field_name="date",
                symbol_field_name="symbol",
                include_fields="open,close,high,low,volume,amount,change",
                max_workers=16,
            )
            dumper.dump()
            logger.info("Data dumping completed")
        except ImportError as e:
            logger.warning(f"Could not import dump_bin: {e}")
            logger.warning("Skipping Qlib format dumping")
            logger.warning("You can manually run:")
            logger.warning(f"  cd {scripts_dir}")
            logger.warning(f"  python dump_bin.py all --csv_path {normalize_dir} --qlib_dir {qlib_dir} --freq day --include_fields open,close,high,low,volume,amount,change")
    else:
        logger.info("Skipping Qlib format dumping (as requested)")
    
    logger.info("=" * 80)
    logger.info("DATA COLLECTION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"Raw data: {source_dir}")
    logger.info(f"Normalized data: {normalize_dir}")
    logger.info(f"Qlib data: {qlib_dir}")
    logger.info("=" * 80)


def run_workflow(
    qlib_dir: str = "~/.qlib/tencent_data/qlib_data",
    experiment_name: str = "tencent_alpha158_example",
    mode: str = "code",
    market: str = "csi300",
):
    """
    Step 2: Run training and backtesting workflow
    
    Parameters
    ----------
    qlib_dir : str
        Path to Qlib data directory
    experiment_name : str
        Name of the experiment
    mode : str
        Execution mode: "code" or "config"
    market : str
        Market name (default: "csi300")
    """
    logger.info("=" * 80)
    logger.info("STEP 2: RUNNING TRAINING AND BACKTESTING")
    logger.info("=" * 80)
    
    # Run workflow
    results = run_tencent_workflow(
        provider_uri=qlib_dir,
        experiment_name=experiment_name,
        mode=mode,
        market=market,
    )
    
    logger.info("=" * 80)
    logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
    logger.info("result is " + str(results))
    logger.info("=" * 80)

    
    return results


def run_all(
    source_dir: str = "~/.qlib/tencent_data/source",
    normalize_dir: str = "~/.qlib/tencent_data/normalize",
    qlib_dir: str = "~/.qlib/tencent_data/qlib_data",
    start: str = "2020-01-01",
    end: str = "2025-12-31",
    experiment_name: str = "tencent_alpha158_full",
    mode: str = "code",
    market: str = "csi300",
):
    """
    Run complete pipeline: data collection + training + backtesting
    
    Parameters
    ----------
    source_dir : str
        Directory for raw data
    normalize_dir : str
        Directory for normalized data
    qlib_dir : str
        Directory for Qlib format data
    start : str
        Start date for data collection
    end : str
        End date for data collection
    experiment_name : str
        Name of the experiment
    mode : str
        Execution mode: "code" or "config"
    market : str
        Market name
    """
    logger.info("=" * 80)
    logger.info("RUNNING COMPLETE TENCENT DATA SOURCE PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Data period: {start} to {end}")
    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Market: {market}")
    logger.info("=" * 80)
    
    # Step 1: Collect data
    collect_data(
        source_dir=source_dir,
        normalize_dir=normalize_dir,
        qlib_dir=qlib_dir,
        start=start,
        end=end,
    )
    
    # Step 2: Run workflow
    results = run_workflow(
        qlib_dir=qlib_dir,
        experiment_name=experiment_name,
        mode=mode,
        market=market,
    )
    
    logger.info("=" * 80)
    logger.info("COMPLETE PIPELINE FINISHED")
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    fire.Fire({
        "collect": collect_data,
        "workflow": run_workflow,
        "all": run_all,
    })
