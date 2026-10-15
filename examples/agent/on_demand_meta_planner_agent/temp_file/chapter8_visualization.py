#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 8: Visualization
=======================
可视化代码，创建各种图表来展示实验结果。
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置图形样式
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def load_processed_results(results_path: str = "results/processed_results.csv") -> pd.DataFrame:
    """加载处理后的结果"""
    try:
        df = pd.read_csv(results_path)
        logger.info(f"Loaded processed results from {results_path}")
        return df
    except FileNotFoundError:
        logger.error(f"Processed results file not found: {results_path}")
        raise

def create_success_rate_plot(df: pd.DataFrame, output_dir: str = "figures"):
    """创建成功率图表"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. 整体成功率
    overall_success = df['success'].mean()
    axes[0, 0].bar(['Success Rate'], [overall_success], color='skyblue')
    axes[0, 0].set_ylabel('Success Rate')
    axes[0, 0].set_title('Overall Success Rate')
    axes[0, 0].set_ylim(0, 1)
    axes[0, 0].text(0, overall_success + 0.02, f'{overall_success:.1%}', ha='center')
    
    # 2. 按任务类型的成功率
    task_success = df.groupby('task_type')['success'].mean().sort_values(ascending=False)
    axes[0, 1].bar(task_success.index, task_success.values, color='lightcoral')
    axes[0, 1].set_ylabel('Success Rate')
    axes[0, 1].set_title('Success Rate by Task Type')
    axes[0, 1].set_ylim(0, 1)
    plt.setp(axes[0, 1].get_xticklabels(), rotation=45, ha='right')
    
    # 3. 按复杂度的成功率
    complexity_success = df.groupby('complexity')['success'].mean().sort_values(ascending=False)
    axes[1, 0].bar(complexity_success.index, complexity_success.values, color='lightgreen')
    axes[1, 0].set_ylabel('Success Rate')
    axes[1, 0].set_title('Success Rate by Complexity')
    axes[1, 0].set_ylim(0, 1)
    
    # 4. 成功率随时间的趋势（按试验ID）
    df_sorted = df.sort_values('trial_id')
    rolling_success = df_sorted['success'].rolling(window=10, min_periods=1).mean()
    axes[1, 1].plot(df_sorted['trial_id'], rolling_success, linewidth=2, color='purple')
    axes[1, 1].set_xlabel('Trial ID')
    axes[1, 1].set_ylabel('Rolling Success Rate (Window=10)')
    axes[1, 1].set_title('Success Rate Trend Over Trials')
    axes[1, 1].set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "success_rate_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info("Success rate plots created")

def create_performance_plots(df: pd.DataFrame, output_dir: str = "figures"):
    """创建性能图表"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. 完成时间分布
    axes[0, 0].hist(df['completion_time'], bins=30, alpha=0.7, color='orange')
    axes[0, 0].set_xlabel('Completion Time (seconds)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Completion Times')
    
    # 2. Token使用量分布
    axes[0, 1].hist(df['token_usage'], bins=30, alpha=0.7, color='teal')
    axes[0, 1].set_xlabel('Token Usage')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Distribution of Token Usage')
    
    # 3. 工具调用次数 vs 成功率
    scatter = axes[1, 0].scatter(df['tool_calls'], df['success'], alpha=0.6, c=df['completion_time'], cmap='viridis')
    axes[1, 0].set_xlabel('Tool Calls')
    axes[1, 0].set_ylabel('Success (0=Fail, 1=Success)')
    axes[1, 0].set_title('Tool Calls vs Success (colored by completion time)')
    plt.colorbar(scatter, ax=axes[1, 0], label='Completion Time')
    
    # 4. 箱线图：不同任务类型的完成时间
    df.boxplot(column='completion_time', by='task_type', ax=axes[1, 1])
    axes[1, 1].set_xlabel('Task Type')
    axes[1, 1].set_ylabel('Completion Time (seconds)')
    axes[1, 1].set_title('Completion Time by Task Type')
    plt.setp(axes[1, 1].get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "performance_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info("Performance plots created")

def create_correlation_heatmap(df: pd.DataFrame, output_dir: str = "figures"):
    """创建相关性热力图"""
    # 选择数值列
    numeric_cols = ['success', 'completion_time', 'token_usage', 'tool_calls', 'errors']
    numeric_df = df[numeric_cols].copy()
    numeric_df['success'] = numeric_df['success'].astype(int)  # 转换布尔值为整数
    
    # 计算相关性矩阵
    corr_matrix = numeric_df.corr()
    
    # 创建热力图
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                square=True, fmt='.2f')
    plt.title('Correlation Matrix of Experiment Metrics')
    
    plt.savefig(Path(output_dir) / "correlation_heatmap.png", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info("Correlation heatmap created")

def create_comprehensive_dashboard(df: pd.DataFrame, output_dir: str = "figures"):
    """创建综合仪表板"""
    fig = plt.figure(figsize=(20, 15))
    
    # 创建网格
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. 整体成功率（大图）
    ax1 = fig.add_subplot(gs[0, :])
    overall_success = df['success'].mean()
    ax1.bar(['Overall Success Rate'], [overall_success], color='steelblue')
    ax1.set_ylabel('Success Rate')
    ax1.set_ylim(0, 1)
    ax1.text(0, overall_success + 0.02, f'{overall_success:.1%}', ha='center', fontsize=16, fontweight='bold')
    ax1.set_title('Experiment Overview', fontsize=18, fontweight='bold')
    
    # 2. 按任务类型的成功率
    ax2 = fig.add_subplot(gs[1, 0])
    task_success = df.groupby('task_type')['success'].mean().sort_values(ascending=False)
    ax2.barh(range(len(task_success)), task_success.values, color='lightcoral')
    ax2.set_yticks(range(len(task_success)))
    ax2.set_yticklabels(task_success.index)
    ax2.set_xlabel('Success Rate')
    ax2.set_title('Success Rate by Task Type')
    ax2.set_xlim(0, 1)
    
    # 3. 按复杂度的成功率
    ax3 = fig.add_subplot(gs[1, 1])
    complexity_success = df.groupby('complexity')['success'].mean()
    colors = ['lightgreen', 'gold', 'lightcoral']
    ax3.pie(complexity_success.values, labels=complexity_success.index, autopct='%1.1f%%', colors=colors)
    ax3.set_title('Success Rate by Complexity')
    
    # 4. 完成时间分布
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.hist(df['completion_time'], bins=20, alpha=0.7, color='orange')
    ax4.set_xlabel('Completion Time (s)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Completion Time Distribution')
    
    # 5. Token使用量 vs 工具调用
    ax5 = fig.add_subplot(gs[2, 0])
    scatter = ax5.scatter(df['token_usage'], df['tool_calls'], c=df['success'], alpha=0.6, cmap='RdYlGn')
    ax5.set_xlabel('Token Usage')
    ax5.set_ylabel('Tool Calls')
    ax5.set_title('Token Usage vs Tool Calls')
    plt.colorbar(scatter, ax=ax5, label='Success')
    
    # 6. 成功率趋势
    ax6 = fig.add_subplot(gs[2, 1:])
    df_sorted = df.sort_values('trial_id')
    rolling_success = df_sorted['success'].rolling(window=15, min_periods=1).mean()
    ax6.plot(df_sorted['trial_id'], rolling_success, linewidth=2, color='purple')
    ax6.set_xlabel('Trial ID')
    ax6.set_ylabel('Rolling Success Rate')
    ax6.set_title('Success Rate Trend (15-trial rolling window)')
    ax6.set_ylim(0, 1)
    ax6.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='80% threshold')
    ax6.legend()
    
    plt.savefig(Path(output_dir) / "comprehensive_dashboard.png", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info("Comprehensive dashboard created")

def main():
    """主函数"""
    try:
        # 创建输出目录
        Path("figures").mkdir(exist_ok=True)
        
        # 加载数据
        df = load_processed_results()
        
        # 创建各种图表
        create_success_rate_plot(df)
        create_performance_plots(df)
        create_correlation_heatmap(df)
        create_comprehensive_dashboard(df)
        
        logger.info("All visualizations created successfully!")
        print("Visualizations saved to figures/ directory")
        
    except Exception as e:
        logger.error(f"Error in visualization: {str(e)}")
        raise

if __name__ == "__main__":
    main()