# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Workflow for training and backtesting with Tencent data source
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml

import qlib
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from qlib.model.trainer import task_train
from loguru import logger

from config import (
    TIME_CONFIG,
    MODEL_CONFIG,
    PORT_ANALYSIS_CONFIG,
    MARKET_CONFIG,
    ALPHA158_CONFIG,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def create_workflow_config(
    provider_uri: str,
    market: str = "csi300",
    alpha_handler: str = "Alpha158",
) -> Dict:
    """
    Create workflow configuration dictionary
    
    Parameters
    ----------
    provider_uri : str
        Path to Qlib data directory
    market : str, optional
        Market name (default: "csi300")
    alpha_handler : str, optional
        Alpha handler class name (default: "Alpha158")
        
    Returns
    -------
    Dict
        Workflow configuration dictionary
    """
    logger.info(f"Creating workflow config for market={market}, handler={alpha_handler}")
    
    market_info = MARKET_CONFIG.get(market, MARKET_CONFIG["csi300"])
    benchmark = market_info["benchmark"]
    
    # Data handler configuration
    # Note: instruments is specified at the dataset level, not in handler kwargs
    data_handler_config = {
        "start_time": TIME_CONFIG["data_start"],
        "end_time": TIME_CONFIG["data_end"],
        "fit_start_time": TIME_CONFIG["train_start"],
        "fit_end_time": TIME_CONFIG["train_end"],
    }
    
    # Dataset configuration
    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": alpha_handler,
                "module_path": ALPHA158_CONFIG["handler_module"],
                "kwargs": data_handler_config,
            },
            "instruments": market,
            "segments": {
                "train": [TIME_CONFIG["train_start"], TIME_CONFIG["train_end"]],
                "valid": [TIME_CONFIG["test_start"], TIME_CONFIG["test_end"]],  # Use test as validation for simplicity
                "test": [TIME_CONFIG["test_start"], TIME_CONFIG["test_end"]],
            },
        },
    }
    
    # Model configuration
    model_config = MODEL_CONFIG.copy()
    
    # Record configuration
    record_config = [
        {
            "class": "SignalRecord",
            "module_path": "qlib.workflow.record_temp",
            "kwargs": {
                "model": "<MODEL>",
                "dataset": "<DATASET>",
            },
        },
        {
            "class": "SigAnaRecord",
            "module_path": "qlib.workflow.record_temp",
            "kwargs": {
                "ana_long_short": False,
                "ann_scaler": 252,  # 252 trading days per year
            },
        },
        {
            "class": "PortAnaRecord",
            "module_path": "qlib.workflow.record_temp",
            "kwargs": {
                "config": PORT_ANALYSIS_CONFIG,
            },
        },
    ]
    
    # Complete workflow configuration
    workflow_config = {
        "qlib_init": {
            "provider_uri": provider_uri,
            "region": REG_CN,
        },
        "market": market,
        "benchmark": benchmark,
        "data_handler_config": data_handler_config,
        "port_analysis_config": PORT_ANALYSIS_CONFIG,
        "task": {
            "model": model_config,
            "dataset": dataset_config,
            "record": record_config,
        },
    }
    
    logger.info(f"Workflow config created successfully")
    logger.debug(f"Train period: {TIME_CONFIG['train_start']} to {TIME_CONFIG['train_end']}")
    logger.debug(f"Test period: {TIME_CONFIG['test_start']} to {TIME_CONFIG['test_end']}")
    
    return workflow_config


def run_workflow_by_code(
    provider_uri: str,
    experiment_name: str = "tencent_alpha158_workflow",
    market: str = "csi300",
) -> Dict:
    """
    Run training and backtesting workflow using Python code
    
    Parameters
    ----------
    provider_uri : str
        Path to Qlib data directory
    experiment_name : str, optional
        Name of the experiment (default: "tencent_alpha158_workflow")
    market : str, optional
        Market name (default: "csi300")
        
    Returns
    -------
    Dict
        Dictionary containing experiment results including annual return and Sharpe ratio
    """
    logger.info(f"Starting workflow: {experiment_name}")
    logger.info(f"Provider URI: {provider_uri}")
    
    # Initialize Qlib
    logger.info("Initializing Qlib...")
    qlib.init(provider_uri=provider_uri, region=REG_CN)
    logger.info("Qlib initialized successfully")
    
    # Get workflow configuration
    workflow_config = create_workflow_config(provider_uri, market)
    
    # Create model and dataset
    logger.info("Creating model...")
    model = init_instance_by_config(workflow_config["task"]["model"])
    logger.info(f"Model created: {model.__class__.__name__}")
    
    logger.info("Creating dataset...")
    dataset = init_instance_by_config(workflow_config["task"]["dataset"])
    logger.info("Dataset created")
    
    # Run experiment
    logger.info(f"Starting experiment: {experiment_name}")
    with R.start(experiment_name=experiment_name):
        # Log parameters
        R.log_params(**flatten_dict(workflow_config["task"]))
        logger.info("Parameters logged")
        
        # Train model
        logger.info("Training model...")
        model.fit(dataset)
        logger.info("Model training completed")
        
        # Save model
        R.save_objects(**{"params.pkl": model})
        logger.info("Model saved")
        
        # Generate predictions
        logger.info("Generating predictions...")
        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        sr.generate()
        logger.info("Predictions generated")
        
        # Signal analysis
        logger.info("Performing signal analysis...")
        sar = SigAnaRecord(recorder)
        sar.generate()
        logger.info("Signal analysis completed")
        
        # Backtest and portfolio analysis
        logger.info("Running backtest and portfolio analysis...")
        par = PortAnaRecord(recorder, PORT_ANALYSIS_CONFIG, "day")
        par.generate()
        logger.info("Portfolio analysis completed")
        
        # Extract results
        logger.info("Extracting results...")
        results = extract_backtest_results(recorder)
        logger.info("Results extracted")
    
    logger.info(f"Workflow completed: {experiment_name}")
    logger.info("=" * 80)
    logger.info("FINAL RESULTS:")
    logger.info(f"Annualized Return (without cost): {results.get('annual_return_no_cost', 'N/A')}")
    logger.info(f"Sharpe Ratio (without cost): {results.get('sharpe_ratio_no_cost', 'N/A')}")
    logger.info(f"Annualized Return (with cost): {results.get('annual_return_with_cost', 'N/A')}")
    logger.info(f"Sharpe Ratio (with cost): {results.get('sharpe_ratio_with_cost', 'N/A')}")
    logger.info("=" * 80)
    
    return results


def run_workflow_by_config(
    provider_uri: str,
    config_path: Optional[str] = None,
    experiment_name: str = "tencent_alpha158_workflow",
) -> Dict:
    """
    Run training and backtesting workflow using YAML configuration file
    
    Parameters
    ----------
    provider_uri : str
        Path to Qlib data directory
    config_path : str, optional
        Path to YAML config file. If None, generate default config
    experiment_name : str, optional
        Name of the experiment
        
    Returns
    -------
    Dict
        Dictionary containing experiment results
    """
    logger.info(f"Running workflow from config: {config_path if config_path else 'default'}")
    
    # Load or create config
    if config_path and Path(config_path).exists():
        logger.info(f"Loading config from: {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        logger.info("Generating default workflow config")
        config = create_workflow_config(provider_uri)
    
    # Update provider_uri in config
    config["qlib_init"]["provider_uri"] = provider_uri
    
    # Run workflow using Qlib's task_train
    logger.info("Initializing Qlib...")
    qlib.init(**config["qlib_init"])
    logger.info("Qlib initialized")
    
    logger.info(f"Starting experiment: {experiment_name}")
    recorder = task_train(config["task"], experiment_name=experiment_name)
    logger.info(f"Experiment completed: {experiment_name}")
    
    # Extract results
    logger.info("Extracting results...")
    results = extract_backtest_results(recorder)
    
    logger.info("=" * 80)
    logger.info("FINAL RESULTS:")
    logger.info(f"Annualized Return (without cost): {results.get('annual_return_no_cost', 'N/A')}")
    logger.info(f"Sharpe Ratio (without cost): {results.get('sharpe_ratio_no_cost', 'N/A')}")
    logger.info(f"Annualized Return (with cost): {results.get('annual_return_with_cost', 'N/A')}")
    logger.info(f"Sharpe Ratio (with cost): {results.get('sharpe_ratio_with_cost', 'N/A')}")
    logger.info("=" * 80)
    
    return results


def extract_backtest_results(recorder) -> Dict:
    """
    Extract backtest results from recorder
    
    Parameters
    ----------
    recorder : Recorder
        Qlib experiment recorder
        
    Returns
    -------
    Dict
        Dictionary containing key performance metrics
    """
    logger.info("Extracting backtest results from recorder")
    
    results = {}
    
    try:
        # Load portfolio analysis results
        port_analysis = recorder.load_object("portfolio_analysis/port_analysis_1day.pkl")
        logger.info("Loaded portfolio analysis")
        
        # Extract metrics for excess return without cost
        excess_no_cost = port_analysis.loc["excess_return_without_cost", "risk"]
        results["annual_return_no_cost"] = float(excess_no_cost.loc["annualized_return"])
        results["sharpe_ratio_no_cost"] = float(excess_no_cost.loc["information_ratio"])
        
        logger.info(f"Excess return (no cost): annual_return={results['annual_return_no_cost']:.4f}, sharpe={results['sharpe_ratio_no_cost']:.4f}")
        
        # Extract metrics for excess return with cost
        excess_with_cost = port_analysis.loc["excess_return_with_cost", "risk"]
        results["annual_return_with_cost"] = float(excess_with_cost.loc["annualized_return"])
        results["sharpe_ratio_with_cost"] = float(excess_with_cost.loc["information_ratio"])
        
        logger.info(f"Excess return (with cost): annual_return={results['annual_return_with_cost']:.4f}, sharpe={results['sharpe_ratio_with_cost']:.4f}")
        
    except Exception as e:
        logger.error(f"Failed to extract portfolio analysis: {e}")
        logger.warning("Results may be incomplete")
    
    return results


def save_workflow_config(config: Dict, save_path: str):
    """
    Save workflow configuration to YAML file
    
    Parameters
    ----------
    config : Dict
        Workflow configuration dictionary
    save_path : str
        Path to save the config file
    """
    logger.info(f"Saving workflow config to: {save_path}")
    
    with open(save_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"Config saved successfully")


def run_tencent_workflow(
    provider_uri: str,
    experiment_name: str = "tencent_alpha158_workflow",
    mode: str = "code",
    market: str = "csi300",
) -> Dict:
    """
    Main entry point for running Tencent data source workflow
    
    Parameters
    ----------
    provider_uri : str
        Path to Qlib data directory with Tencent data
    experiment_name : str, optional
        Name of the experiment
    mode : str, optional
        Execution mode: "code" or "config" (default: "code")
    market : str, optional
        Market name (default: "csi300")
        
    Returns
    -------
    Dict
        Dictionary containing experiment results including annual return and Sharpe ratio
    """
    logger.info("=" * 80)
    logger.info("TENCENT DATA SOURCE WORKFLOW")
    logger.info("=" * 80)
    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Market: {market}")
    logger.info(f"Provider URI: {provider_uri}")
    logger.info(f"Train period: {TIME_CONFIG['train_start']} to {TIME_CONFIG['train_end']}")
    logger.info(f"Test period: {TIME_CONFIG['test_start']} to {TIME_CONFIG['test_end']}")
    logger.info("=" * 80)
    
    # Run workflow based on mode
    if mode == "code":
        results = run_workflow_by_code(
            provider_uri=provider_uri,
            experiment_name=experiment_name,
            market=market,
        )
    elif mode == "config":
        results = run_workflow_by_config(
            provider_uri=provider_uri,
            experiment_name=experiment_name,
        )
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'code' or 'config'")
    
    return results


if __name__ == "__main__":
    import fire
    
    # Example usage
    fire.Fire({
        "run": run_tencent_workflow,
        "create_config": create_workflow_config,
    })
