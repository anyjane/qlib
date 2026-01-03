#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回测详细分析脚本 - 显示每日交易明细、持仓、预测值等
"""

import sys
from pathlib import Path

# Add current directory to path (same as run_example.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pickle
import pandas as pd
import numpy as np

# 初始化qlib
import qlib
from qlib.constant import REG_CN
print("初始化 Qlib...")
qlib.init(provider_uri="~/.qlib/tencent_data/qlib_data", region=REG_CN)
print("Qlib 初始化成功")

# 实验路径
EXP_DIR = "/home/abc.linux/workspace/qlib/examples/TencentDataSource/mlruns/385165854383783213/c42d455070b0494ca9698bb3bf9cd600"
ARTIFACTS_DIR = str(Path(EXP_DIR) / "artifacts")

def load_pickle_safe(filepath):
    """安全加载pickle文件"""
    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"无法加载文件 {filepath}: {e}")
        return None

def parse_positions_dict(positions_dict):
    """解析dict格式的positions数据，返回结构化数据"""
    if not isinstance(positions_dict, dict):
        return None
    
    parsed_data = []
    for date, position_obj in positions_dict.items():
        # 获取股票持仓权重
        stock_weights = getattr(position_obj, 'get_stock_weight_dict', lambda: {})()
        
        row = {
            'date': date,
            '_settle_type': getattr(position_obj, '_settle_type', None),
            'init_cash': getattr(position_obj, 'init_cash', None),
            'cash': getattr(position_obj, 'get_cash', lambda: None)(),
            'now_account_value': getattr(position_obj, 'calculate_value', lambda: None)(),
            'stock_weights': stock_weights,
            'stock_count': len(stock_weights)
        }
        
        parsed_data.append(row)
    
    df = pd.DataFrame(parsed_data)
    df.set_index('date', inplace=True)
    return df

def analyze_detailed_backtest():
    """详细分析回测过程"""
    print("=" * 100)
    print("回测详细分析")
    print("=" * 100)
    
    # 加载预测数据
    print("\n[1] 加载预测数据...")
    pred = load_pickle_safe(f"{ARTIFACTS_DIR}/pred.pkl")
    
    if pred is None:
        print("无法加载预测数据，退出")
        return
    
    print(f"预测数据类型: {type(pred)}")
    print(f"预测数据维度: {pred.shape}")
    print(f"预测数据索引类型: {type(pred.index)}")
    
    if isinstance(pred.index, pd.MultiIndex):
        print(f"  - 时间范围: {pred.index.get_level_values(0)[0]} 至 {pred.index.get_level_values(0)[-1]}")
        print(f"  - 股票数量: {pred.index.get_level_values(1).nunique()}")
        
        # 重组数据为时间 x 股票格式
        try:
            pred_pivot = pred.unstack()
            print(f"  重组后维度: {pred_pivot.shape}")
        except Exception as e:
            print(f"  无法重组数据: {e}")
            pred_pivot = pred
    else:
        pred_pivot = pred
    
    # 加载持仓数据（尝试直接加载，处理dict格式）
    print("\n[2] 加载持仓数据...")
    positions = load_pickle_safe(f"{ARTIFACTS_DIR}/portfolio_analysis/positions_normal_1day.pkl")
    
    if positions is None:
        print("直接加载持仓数据失败，跳过")
        positions = None
    else:
        print(f"持仓数据类型: {type(positions)}")
        
        # 检查是否是dict格式
        if isinstance(positions, dict):
            print("检测到dict格式的positions数据，正在解析...")
            positions_df = parse_positions_dict(positions)
            if positions_df is not None:
                positions = positions_df
                print(f"解析后的positions数据维度: {positions.shape}")
                print(f"解析后的positions数据列名: {positions.columns.tolist()}")
                print(f"  - 时间范围: {positions.index[0]} 至 {positions.index[-1]}")
            else:
                print("解析positions数据失败")
                positions = None
        elif hasattr(positions, 'shape'):
            print(f"持仓数据维度: {positions.shape}")
            if isinstance(positions.index, pd.MultiIndex):
                print(f"  - 时间范围: {positions.index.get_level_values(0)[0]} 至 {positions.index.get_level_values(0)[-1]}")
                print(f"  - 股票数量: {positions.index.get_level_values(1).nunique()}")
            else:
                print(f"  - 时间范围: {positions.index[0]} 至 {positions.index[-1]}")
    
    # 加载指标数据（必须加载，后续分析需要）
    print("\n[3] 加载指标数据...")
    indicators = load_pickle_safe(f"{ARTIFACTS_DIR}/portfolio_analysis/indicators_normal_1day.pkl")
    if indicators is not None:
        print(f"指标数据类型: {type(indicators)}")
        if isinstance(indicators, pd.DataFrame):
            print(f"指标数据维度: {indicators.shape}")
            print(f"指标数据列名: {indicators.columns.tolist()}")
        else:
            print(f"指标数据内容: {indicators}")
    else:
        print("无法加载指标数据")
        return
    
    # 加载组合分析结果
    print("\n[4] 加载组合分析...")
    port_analysis = load_pickle_safe(f"{ARTIFACTS_DIR}/portfolio_analysis/port_analysis_1day.pkl")
    if port_analysis is not None:
        print(f"组合分析结果:")
        print(port_analysis)
    
    # 加载报告数据
    print("\n[4b] 加载报告数据...")
    report = load_pickle_safe(f"{ARTIFACTS_DIR}/portfolio_analysis/report_normal_1day.pkl")
    if report is not None:
        print(f"报告数据类型: {type(report)}")
        if isinstance(report, pd.DataFrame):
            print(f"报告数据维度: {report.shape}")
            print(f"报告数据列名: {report.columns.tolist()}")
            print(f"\n报告数据前10行:")
            print(report.head(10))
        else:
            print(f"报告数据内容: {report}")
    
    # 尝试解析 pos 列（可能包含持仓信息）
    print("\n[5] 分析持仓数据（indicators.pos列）...")
    if 'pos' in indicators.columns:
        print(f"\n  pos 列前5个值:")
        for i, val in enumerate(indicators['pos'].head()):
            print(f"    {indicators.index[i]}: {val} (类型: {type(val)})")
            
        # 尝试解析 pos 数据（可能是字典或其他格式）
        first_pos = indicators['pos'].iloc[0]
        if isinstance(first_pos, (dict, pd.Series)):
            print(f"\n  第一天的持仓详细信息:")
            for stock, weight in list(first_pos.items())[:10]:  # 只显示前10个
                print(f"    {stock}: {weight}")
            print(f"  ... (共 {len(first_pos)} 只股票)")
    
    # 显示每日交易明细（使用 report 数据）
    print("\n" + "=" * 100)
    print("每日交易明细（显示前10个交易日）")
    print("=" * 100)
    
    if report is None:
        print("无法加载报告数据，无法显示每日交易明细")
    else:
        for i in range(min(10, len(report))):
            date = report.index[i]
            
            print(f"\n【交易日 {i+1}】日期: {date}")
            print("-" * 100)
            
            # 获取当日报告数据
            account = report['account'].iloc[i]
            return_rate = report['return'].iloc[i]
            turnover = report['turnover'].iloc[i]
            total_cost = report['total_cost'].iloc[i]
            value = report['value'].iloc[i]
            cash = report['cash'].iloc[i]
            bench = report['bench'].iloc[i]
            
            # 显示当日资金信息
            print(f"  账户总资产: {account:,.2f} 元")
            print(f"  当日收益率: {return_rate:.6f} ({return_rate*100:.2f}%)")
            print(f"  累计收益率: {(account/100000000 - 1):.6f} ({(account/100000000 - 1)*100:.2f}%)")
            print(f"  持仓市值: {value:,.2f} 元")
            print(f"  现金余额: {cash:,.2f} 元")
            print(f"  交易成本: {total_cost:,.2f} 元")
            print(f"  换手率: {turnover:.6f} ({turnover*100:.2f}%)")
            print(f"  基准收益率: {bench:.6f} ({bench*100:.2f}%)")
            print(f"  超额收益: {return_rate - bench:.6f} ({(return_rate - bench)*100:.2f}%)")
            
            # 显示positions数据中的账户状态信息和股票持仓
            if positions is not None and date in positions.index:
                pos_row = positions.loc[date]
                print(f"\n  账户状态信息（来自positions数据）:")
                if isinstance(pos_row, pd.Series):
                    if 'cash' in pos_row.index and pd.notna(pos_row['cash']):
                        print(f"    positions中的现金余额: {pos_row['cash']:,.2f} 元")
                    if 'now_account_value' in pos_row.index and pd.notna(pos_row['now_account_value']):
                        print(f"    positions中的账户总值: {pos_row['now_account_value']:,.2f} 元")
                    if 'init_cash' in pos_row.index and pd.notna(pos_row['init_cash']):
                        print(f"    初始资金: {pos_row['init_cash']:,.2f} 元")
                    if 'stock_count' in pos_row.index and pd.notna(pos_row['stock_count']):
                        print(f"    持仓股票数量: {pos_row['stock_count']} 只")
                    if '_settle_type' in pos_row.index and pd.notna(pos_row['_settle_type']):
                        print(f"    结算类型: {pos_row['_settle_type']}")
                    
                    # 显示股票持仓明细
                    if 'stock_weights' in pos_row.index:
                        stock_weights = pos_row['stock_weights']
                        if isinstance(stock_weights, dict) and len(stock_weights) > 0:
                            print(f"\n  股票持仓明细（显示前10只）:")
                            print(f"  {'股票代码':<12} {'持仓权重':<12} {'持仓金额':<15} {'预测分数':<12} {'排序'}")
                            print(f"  {'-'*12} {'-'*12} {'-'*15} {'-'*12} {'-'*12}")
                            
                            # 获取当日预测分数
                            if date in pred_pivot.index:
                                pred_scores = pred_pivot.loc[date]
                            else:
                                # 找最近的一天
                                date_idx = pred_pivot.index.get_indexer([date], method='nearest')[0]
                                pred_scores = pred_pivot.iloc[date_idx]
                            
                            # 按权重排序
                            sorted_stocks = sorted(stock_weights.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
                            
                            for stock, weight in sorted_stocks:
                                amount = account * abs(weight) if account else 0
                                pred_score = pred_scores.get(stock, 0)
                                rank = pred_scores.rank(ascending=False).get(stock, '-') if stock in pred_scores.index else '-'
                                print(f"  {str(stock):<12} {float(weight):<12.6f} {amount:>13,.2f} {float(pred_score):<12.6f} {rank}")
                            
                            if len(stock_weights) > 10:
                                print(f"  ... (共 {len(stock_weights)} 只股票)")
                            
                            # 计算组合预测分数（加权平均）
                            weighted_pred = 0
                            total_weight = 0
                            for stock, weight in stock_weights.items():
                                pred_score = pred_scores.get(stock, 0)
                                weighted_pred += pred_score * abs(weight)
                                total_weight += abs(weight)
                            
                            if total_weight > 0:
                                weighted_pred = weighted_pred / total_weight
                                print(f"\n  组合平均预测分数（加权平均）: {weighted_pred:.6f}")
                        else:
                            print(f"\n  股票持仓明细: 当日无股票持仓")
                    else:
                        print(f"\n  无法获取股票持仓明细（positions中无stock_weights列）")
            else:
                print(f"\n  无法获取持仓明细（positions数据不可用）")
    
    # 换手率分析
    print("\n" + "=" * 100)
    print("换手率分析")
    print("=" * 100)
    
    if 'deal_amount' in indicators.columns and 'value' in indicators.columns:
        turnover_rates = []
        for i in range(1, len(indicators)):
            if pd.notna(indicators['deal_amount'].iloc[i]) and pd.notna(indicators['value'].iloc[i]):
                turnover = indicators['deal_amount'].iloc[i] / indicators['value'].iloc[i]
                turnover_rates.append(turnover)
        
        turnover_series = pd.Series(turnover_rates, index=indicators.index[1:])
        
        if len(turnover_series) > 0:
            print(f"\n每日换手率（前10个交易日）:")
            for i in range(min(10, len(turnover_series))):
                print(f"  {turnover_series.index[i]}: {turnover_series.iloc[i]:.4f} ({turnover_series.iloc[i]*100:.2f}%)")
            
            print(f"\n换手率统计:")
            print(f"  平均换手率: {turnover_series.mean():.4f} ({turnover_series.mean()*100:.2f}%)")
            print(f"  最大换手率: {turnover_series.max():.4f} ({turnover_series.max()*100:.2f}%)")
            print(f"  最小换手率: {turnover_series.min():.4f} ({turnover_series.min()*100:.2f}%)")
    
    # 预测分数统计
    print(f"\n预测分数统计:")
    print(f"  均值: {pred_pivot.mean().mean():.6f}")
    print(f"  标准差: {pred_pivot.std().mean():.6f}")
    print(f"  最小值: {pred_pivot.min().min():.6f}")
    print(f"  最大值: {pred_pivot.max().max():.6f}")
    
    print("\n" + "=" * 100)
    print("分析完成")
    print("=" * 100)

if __name__ == "__main__":
    analyze_detailed_backtest()
