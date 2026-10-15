#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 9: Statistical Tests
===========================
统计检验代码，对实验结果进行统计显著性分析。
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging
from pathlib import Path
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_processed_results(results_path: str = "results/processed_results.csv") -> pd.DataFrame:
    """加载处理后的结果"""
    try:
        df = pd.read_csv(results_path)
        logger.info(f"Loaded processed results from {results_path}")
        return df
    except FileNotFoundError:
        logger.error(f"Processed results file not found: {results_path}")
        raise

def perform_success_rate_tests(df: pd.DataFrame) -> Dict[str, Any]:
    """执行成功率相关的统计检验"""
    results = {}
    
    # 1. 整体成功率是否显著高于基线（假设基线为0.5）
    overall_success_rate = df['success'].mean()
    n_trials = len(df)
    baseline = 0.5
    
    # 单样本比例检验
    z_stat, p_value = stats.proportions_ztest(
        count=df['success'].sum(), 
        nobs=n_trials, 
        value=baseline
    )
    
    results['overall_vs_baseline'] = {
        'success_rate': overall_success_rate,
        'baseline': baseline,
        'z_statistic': z_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'effect_size': overall_success_rate - baseline
    }
    
    # 2. 不同任务类型之间的成功率差异
    task_types = df['task_type'].unique()
    task_success_rates = {}
    
    for task_type in task_types:
        task_df = df[df['task_type'] == task_type]
        task_success_rates[task_type] = task_df['success'].mean()
    
    results['task_type_comparison'] = {
        'success_rates': task_success_rates,
        'pairwise_tests': {}
    }
    
    # 成对比较（使用卡方检验）
    for i, task1 in enumerate(task_types):
        for j, task2 in enumerate(task_types):
            if i < j:
                contingency_table = pd.crosstab(
                    df['task_type'].isin([task1, task2]),
                    df['success']
                )
                chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
                
                results['task_type_comparison']['pairwise_tests'][f"{task1}_vs_{task2}"] = {
                    'chi2_statistic': chi2,
                    'p_value': p_val,
                    'significant': p_val < 0.05,
                    'dof': dof
                }
    
    # 3. 不同复杂度级别的成功率差异
    complexities = df['complexity'].unique()
    complexity_success_rates = {}
    
    for complexity in complexities:
        comp_df = df[df['complexity'] == complexity]
        complexity_success_rates[complexity] = comp_df['success'].mean()
    
    results['complexity_comparison'] = {
        'success_rates': complexity_success_rates
    }
    
    # 复杂度的卡方检验
    complexity_table = pd.crosstab(df['complexity'], df['success'])
    chi2_comp, p_val_comp, dof_comp, expected_comp = stats.chi2_contingency(complexity_table)
    
    results['complexity_comparison']['chi2_test'] = {
        'chi2_statistic': chi2_comp,
        'p_value': p_val_comp,
        'significant': p_val_comp < 0.05,
        'dof': dof_comp
    }
    
    return results

def perform_performance_tests(df: pd.DataFrame) -> Dict[str, Any]:
    """执行性能相关的统计检验"""
    results = {}
    
    # 1. 成功和失败案例的完成时间差异（t检验）
    success_times = df[df['success']]['completion_time']
    failure_times = df[~df['success']]['completion_time']
    
    t_stat, p_value = stats.ttest_ind(success_times, failure_times, equal_var=False)
    
    results['time_success_vs_failure'] = {
        'success_mean_time': success_times.mean(),
        'failure_mean_time': failure_times.mean(),
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'effect_size': (success_times.mean() - failure_times.mean()) / np.sqrt((success_times.var() + failure_times.var()) / 2)
    }
    
    # 2. 成功和失败案例的工具调用次数差异
    success_tools = df[df['success']]['tool_calls']
    failure_tools = df[~df['success']]['tool_calls']
    
    t_stat_tools, p_value_tools = stats.ttest_ind(success_tools, failure_tools, equal_var=False)
    
    results['tools_success_vs_failure'] = {
        'success_mean_tools': success_tools.mean(),
        'failure_mean_tools': failure_tools.mean(),
        't_statistic': t_stat_tools,
        'p_value': p_value_tools,
        'significant': p_value_tools < 0.05
    }
    
    # 3. Token使用量与成功率的相关性
    token_success_corr, token_p_value = stats.pointbiserialr(df['success'], df['token_usage'])
    
    results['token_success_correlation'] = {
        'correlation': token_success_corr,
        'p_value': token_p_value,
        'significant': token_p_value < 0.05
    }
    
    # 4. 工具调用次数与完成时间的相关性
    tool_time_corr, tool_time_p = stats.pearsonr(df['tool_calls'], df['completion_time'])
    
    results['tool_time_correlation'] = {
        'correlation': tool_time_corr,
        'p_value': tool_time_p,
        'significant': tool_time_p < 0.05
    }
    
    return results

def perform_anova_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """执行ANOVA分析"""
    results = {}
    
    # 1. 任务类型对完成时间的影响（单因素ANOVA）
    task_groups = [group['completion_time'].values for name, group in df.groupby('task_type')]
    f_stat, p_value = stats.f_oneway(*task_groups)
    
    results['task_type_anova'] = {
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < 0.05
    }
    
    # 2. 复杂度对完成时间的影响
    complexity_groups = [group['completion_time'].values for name, group in df.groupby('complexity')]
    f_stat_comp, p_value_comp = stats.f_oneway(*complexity_groups)
    
    results['complexity_anova'] = {
        'f_statistic': f_stat_comp,
        'p_value': p_value_comp,
        'significant': p_value_comp < 0.05
    }
    
    # 3. 双因素ANOVA（任务类型和复杂度对成功率的影响）
    # 由于scipy没有直接的双因素ANOVA，我们使用线性回归的方法
    try:
        import statsmodels.api as sm
        from statsmodels.formula.api import ols
        
        # 准备数据
        anova_df = df[['task_type', 'complexity', 'success']].copy()
        anova_df['success'] = anova_df['success'].astype(int)
        
        # 拟合模型
        model = ols('success ~ C(task_type) + C(complexity) + C(task_type):C(complexity)', data=anova_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        
        results['two_way_anova'] = {
            'task_type_p': anova_table.loc['C(task_type)', 'PR(>F)'],
            'complexity_p': anova_table.loc['C(complexity)', 'PR(>F)'],
            'interaction_p': anova_table.loc['C(task_type):C(complexity)', 'PR(>F)'],
            'task_type_significant': anova_table.loc['C(task_type)', 'PR(>F)'] < 0.05,
            'complexity_significant': anova_table.loc['C(complexity)', 'PR(>F)'] < 0.05,
            'interaction_significant': anova_table.loc['C(task_type):C(complexity)', 'PR(>F)'] < 0.05
        }
    except ImportError:
        logger.warning("statsmodels not available, skipping two-way ANOVA")
        results['two_way_anova'] = "statsmodels not available"
    
    return results

def save_statistical_results(stat_results: Dict[str, Any], output_dir: str = "results"):
    """保存统计检验结果"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    import json
    with open(output_path / "statistical_tests.json", 'w') as f:
        json.dump(stat_results, f, indent=2, default=str)
    
    logger.info(f"Statistical results saved to {output_path / 'statistical_tests.json'}")

def generate_statistical_report(stat_results: Dict[str, Any]) -> str:
    """生成统计检验报告"""
    report = []
    report.append("=" * 70)
    report.append("STATISTICAL ANALYSIS REPORT")
    report.append("=" * 70)
    
    # 成功率检验
    report.append("\nSUCCESS RATE ANALYSIS:")
    overall_test = stat_results['success_rate_tests']['overall_vs_baseline']
    report.append(f"  Overall success rate: {overall_test['success_rate']:.2%}")
    report.append(f"  vs baseline ({overall_test['baseline']:.0%}): p={overall_test['p_value']:.4f}")
    report.append(f"  Significant: {'Yes' if overall_test['significant'] else 'No'}")
    report.append(f"  Effect size: {overall_test['effect_size']:.3f}")
    
    # 任务类型比较
    report.append("\nTASK TYPE COMPARISON:")
    task_comp = stat_results['success_rate_tests']['task_type_comparison']
    for task, rate in task_comp['success_rates'].items():
        report.append(f"  {task}: {rate:.2%}")
    
    report.append("\n  Pairwise comparisons (significant differences):")
    significant_pairs = []
    for pair, test in task_comp['pairwise_tests'].items():
        if test['significant']:
            significant_pairs.append(f"{pair} (p={test['p_value']:.4f})")
    
    if significant_pairs:
        for pair in significant_pairs:
            report.append(f"    {pair}")
    else:
        report.append("    No significant pairwise differences found")
    
    # 性能检验
    report.append("\nPERFORMANCE ANALYSIS:")
    perf_tests = stat_results['performance_tests']
    
    time_test = perf_tests['time_success_vs_failure']
    report.append(f"  Success vs Failure completion time:")
    report.append(f"    Success: {time_test['success_mean_time']:.2f}s, Failure: {time_test['failure_mean_time']:.2f}s")
    report.append(f"    p-value: {time_test['p_value']:.4f}, Significant: {'Yes' if time_test['significant'] else 'No'}")
    
    tools_test = perf_tests['tools_success_vs_failure']
    report.append(f"  Success vs Failure tool calls:")
    report.append(f"    Success: {tools_test['success_mean_tools']:.1f}, Failure: {tools_test['failure_mean_tools']:.1f}")
    report.append(f"    p-value: {tools_test['p_value']:.4f}, Significant: {'Yes' if tools_test['significant'] else 'No'}")
    
    # ANOVA结果
    report.append("\nANOVA ANALYSIS:")
    anova_results = stat_results['anova_analysis']
    
    task_anova = anova_results['task_type_anova']
    report.append(f"  Task type effect on completion time: p={task_anova['p_value']:.4f}, Significant: {'Yes' if task_anova['significant'] else 'No'}")
    
    comp_anova = anova_results['complexity_anova']
    report.append(f"  Complexity effect on completion time: p={comp_anova['p_value']:.4f}, Significant: {'Yes' if comp_anova['significant'] else 'No'}")
    
    return "\n".join(report)

def main():
    """主函数"""
    try:
        # 加载数据
        df = load_processed_results()
        
        # 执行各种统计检验
        success_tests = perform_success_rate_tests(df)
        performance_tests = perform_performance_tests(df)
        anova_tests = perform_anova_analysis(df)
        
        # 组合结果
        stat_results = {
            'success_rate_tests': success_tests,
            'performance_tests': performance_tests,
            'anova_analysis': anova_tests
        }
        
        # 保存结果
        save_statistical_results(stat_results)
        
        # 生成报告
        report = generate_statistical_report(stat_results)
        print(report)
        
        # 保存报告
        with open("results/statistical_report.txt", 'w') as f:
            f.write(report)
        
        logger.info("Statistical analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in statistical analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()