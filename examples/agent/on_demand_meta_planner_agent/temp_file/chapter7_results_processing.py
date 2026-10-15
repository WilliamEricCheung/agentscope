#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 7: Results Processing
============================
结果处理代码，对实验结果进行清洗、转换和分析。
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_experiment_results(results_path: str = "results/experiment_results.csv") -> pd.DataFrame:
    """加载实验结果"""
    try:
        df = pd.read_csv(results_path)
        logger.info(f"Loaded {len(df)} results from {results_path}")
        return df
    except FileNotFoundError:
        logger.error(f"Results file not found: {results_path}")
        raise

def clean_results(df: pd.DataFrame) -> pd.DataFrame:
    """清洗实验结果数据"""
    logger.info("Cleaning results data...")
    
    # 复制数据以避免修改原始数据
    cleaned_df = df.copy()
    
    # 处理缺失值
    cleaned_df['success'] = cleaned_df['success'].fillna(False)
    cleaned_df['completion_time'] = cleaned_df['completion_time'].fillna(cleaned_df['completion_time'].median())
    cleaned_df['token_usage'] = cleaned_df['token_usage'].fillna(cleaned_df['token_usage'].median())
    cleaned_df['tool_calls'] = cleaned_df['tool_calls'].fillna(0)
    cleaned_df['errors'] = cleaned_df['errors'].fillna(0)
    cleaned_df['final_message'] = cleaned_df['final_message'].fillna("")
    
    # 处理异常值
    # 移除完成时间过长的异常值（> 3个标准差）
    time_mean = cleaned_df['completion_time'].mean()
    time_std = cleaned_df['completion_time'].std()
    cleaned_df = cleaned_df[cleaned_df['completion_time'] <= time_mean + 3 * time_std]
    
    # 确保数值列为正确类型
    numeric_columns = ['completion_time', 'token_usage', 'tool_calls', 'errors']
    for col in numeric_columns:
        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce').fillna(0)
    
    # 确保布尔列为正确类型
    cleaned_df['success'] = cleaned_df['success'].astype(bool)
    
    logger.info(f"Cleaned data shape: {cleaned_df.shape}")
    return cleaned_df

def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """计算实验指标"""
    logger.info("Calculating metrics...")
    
    metrics = {}
    
    # 整体指标
    metrics['overall'] = {
        'total_trials': len(df),
        'success_rate': df['success'].mean(),
        'avg_completion_time': df['completion_time'].mean(),
        'avg_token_usage': df['token_usage'].mean(),
        'avg_tool_calls': df['tool_calls'].mean(),
        'error_rate': df['errors'].mean() > 0
    }
    
    # 按任务类型分组
    metrics['by_task_type'] = {}
    for task_type in df['task_type'].unique():
        task_df = df[df['task_type'] == task_type]
        metrics['by_task_type'][task_type] = {
            'count': len(task_df),
            'success_rate': task_df['success'].mean(),
            'avg_completion_time': task_df['completion_time'].mean(),
            'avg_token_usage': task_df['token_usage'].mean()
        }
    
    # 按复杂度分组
    metrics['by_complexity'] = {}
    for complexity in df['complexity'].unique():
        comp_df = df[df['complexity'] == complexity]
        metrics['by_complexity'][complexity] = {
            'count': len(comp_df),
            'success_rate': comp_df['success'].mean(),
            'avg_completion_time': comp_df['completion_time'].mean()
        }
    
    # 工具效率分析
    metrics['tool_efficiency'] = {
        'avg_tool_calls_per_success': df[df['success']]['tool_calls'].mean(),
        'avg_tool_calls_per_failure': df[~df['success']]['tool_calls'].mean(),
        'tool_calls_vs_success_correlation': df['tool_calls'].corr(df['success'].astype(int))
    }
    
    logger.info("Metrics calculation completed")
    return metrics

def save_processed_results(df: pd.DataFrame, metrics: Dict[str, Any], 
                          output_dir: str = "results") -> None:
    """保存处理后的结果"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 保存清洗后的数据
    df.to_csv(output_path / "processed_results.csv", index=False)
    
    # 保存指标
    import json
    with open(output_path / "experiment_metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    
    logger.info(f"Processed results saved to {output_dir}")

def generate_summary_report(metrics: Dict[str, Any]) -> str:
    """生成摘要报告"""
    report = []
    report.append("=" * 60)
    report.append("EXPERIMENT RESULTS SUMMARY REPORT")
    report.append("=" * 60)
    
    # 整体结果
    overall = metrics['overall']
    report.append(f"\nOVERALL RESULTS:")
    report.append(f"  Total Trials: {overall['total_trials']}")
    report.append(f"  Success Rate: {overall['success_rate']:.2%}")
    report.append(f"  Avg Completion Time: {overall['avg_completion_time']:.2f}s")
    report.append(f"  Avg Token Usage: {overall['avg_token_usage']:.0f}")
    report.append(f"  Avg Tool Calls: {overall['avg_tool_calls']:.1f}")
    report.append(f"  Error Rate: {overall['error_rate']:.2%}")
    
    # 按任务类型
    report.append(f"\nBY TASK TYPE:")
    for task_type, stats in metrics['by_task_type'].items():
        report.append(f"  {task_type}:")
        report.append(f"    Count: {stats['count']}")
        report.append(f"    Success Rate: {stats['success_rate']:.2%}")
        report.append(f"    Avg Time: {stats['avg_completion_time']:.2f}s")
        report.append(f"    Avg Tokens: {stats['avg_token_usage']:.0f}")
    
    # 按复杂度
    report.append(f"\nBY COMPLEXITY:")
    for complexity, stats in metrics['by_complexity'].items():
        report.append(f"  {complexity}:")
        report.append(f"    Count: {stats['count']}")
        report.append(f"    Success Rate: {stats['success_rate']:.2%}")
        report.append(f"    Avg Time: {stats['avg_completion_time']:.2f}s")
    
    # 工具效率
    tool_eff = metrics['tool_efficiency']
    report.append(f"\nTOOL EFFICIENCY:")
    report.append(f"  Avg Tool Calls (Success): {tool_eff['avg_tool_calls_per_success']:.1f}")
    report.append(f"  Avg Tool Calls (Failure): {tool_eff['avg_tool_calls_per_failure']:.1f}")
    report.append(f"  Tool Calls vs Success Correlation: {tool_eff['tool_calls_vs_success_correlation']:.3f}")
    
    return "\n".join(report)

def main():
    """主函数"""
    try:
        # 加载结果
        results_df = load_experiment_results()
        
        # 清洗数据
        cleaned_df = clean_results(results_df)
        
        # 计算指标
        metrics = calculate_metrics(cleaned_df)
        
        # 保存处理后的结果
        save_processed_results(cleaned_df, metrics)
        
        # 生成并打印摘要报告
        report = generate_summary_report(metrics)
        print(report)
        
        # 保存报告
        with open("results/summary_report.txt", 'w') as f:
            f.write(report)
        
        logger.info("Results processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in results processing: {str(e)}")
        raise

if __name__ == "__main__":
    main()