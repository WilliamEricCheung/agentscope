#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 10: Conclusion Summary
=============================
结论总结代码，整合所有分析结果并生成最终结论。
"""

import json
import pandas as pd
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_analysis_results() -> dict:
    """加载所有分析结果"""
    results = {}
    
    try:
        # 加载实验指标
        with open("results/experiment_metrics.json", 'r') as f:
            results['metrics'] = json.load(f)
        
        # 加载统计检验结果
        with open("results/statistical_tests.json", 'r') as f:
            results['statistics'] = json.load(f)
        
        # 加载处理后的数据
        results['data'] = pd.read_csv("results/processed_results.csv")
        
        logger.info("All analysis results loaded successfully")
        return results
        
    except FileNotFoundError as e:
        logger.error(f"Required analysis file not found: {e}")
        raise

def extract_key_findings(results: dict) -> dict:
    """提取关键发现"""
    findings = {}
    
    # 1. 整体性能
    metrics = results['metrics']['overall']
    findings['overall_performance'] = {
        'success_rate': metrics['success_rate'],
        'is_successful': metrics['success_rate'] >= 0.8,
        'efficiency': metrics['avg_completion_time'] < 15.0,  # 假设15秒是可接受的阈值
        'resource_usage': metrics['avg_token_usage'] < 1000  # 假设1000 tokens是合理的
    }
    
    # 2. 任务类型表现
    task_metrics = results['metrics']['by_task_type']
    best_task = max(task_metrics.items(), key=lambda x: x[1]['success_rate'])
    worst_task = min(task_metrics.items(), key=lambda x: x[1]['success_rate'])
    
    findings['task_performance'] = {
        'best_performing': best_task[0],
        'best_success_rate': best_task[1]['success_rate'],
        'worst_performing': worst_task[0],
        'worst_success_rate': worst_task[1]['success_rate'],
        'performance_gap': best_task[1]['success_rate'] - worst_task[1]['success_rate']
    }
    
    # 3. 统计显著性
    stats = results['statistics']
    findings['statistical_significance'] = {
        'overall_significant': stats['success_rate_tests']['overall_vs_baseline']['significant'],
        'task_differences_significant': any(
            test['significant'] for test in stats['success_rate_tests']['task_type_comparison']['pairwise_tests'].values()
        ),
        'performance_differences_significant': (
            stats['performance_tests']['time_success_vs_failure']['significant'] or
            stats['performance_tests']['tools_success_vs_failure']['significant']
        )
    }
    
    # 4. 关键相关性
    perf_stats = stats['performance_tests']
    findings['key_correlations'] = {
        'token_success_correlation': perf_stats['token_success_correlation']['correlation'],
        'tool_time_correlation': perf_stats['tool_time_correlation']['correlation'],
        'strong_correlations': []
    }
    
    if abs(perf_stats['token_success_correlation']['correlation']) > 0.3:
        findings['key_correlations']['strong_correlations'].append('token_success')
    
    if abs(perf_stats['tool_time_correlation']['correlation']) > 0.3:
        findings['key_correlations']['strong_correlations'].append('tool_time')
    
    return findings

def generate_conclusion(findings: dict) -> str:
    """生成结论"""
    conclusion = []
    
    conclusion.append("=" * 80)
    conclusion.append("FINAL CONCLUSIONS AND RECOMMENDATIONS")
    conclusion.append("=" * 80)
    
    # 整体评估
    conclusion.append("\nOVERALL ASSESSMENT:")
    if findings['overall_performance']['is_successful']:
        conclusion.append("✓ The MCP Agent demonstrates successful performance overall.")
        conclusion.append(f"  Success rate: {findings['overall_performance']['success_rate']:.1%}")
    else:
        conclusion.append("✗ The MCP Agent does not meet the success criteria overall.")
        conclusion.append(f"  Success rate: {findings['overall_performance']['success_rate']:.1%} (target: 80%)")
    
    if findings['overall_performance']['efficiency']:
        conclusion.append("✓ Performance is efficient with acceptable completion times.")
    else:
        conclusion.append("⚠ Performance could be improved with faster completion times.")
    
    if findings['overall_performance']['resource_usage']:
        conclusion.append("✓ Resource usage (tokens) is within reasonable limits.")
    else:
        conclusion.append("⚠ Resource usage is higher than expected and could be optimized.")
    
    # 任务特定发现
    conclusion.append("\nTASK-SPECIFIC FINDINGS:")
    conclusion.append(f"• Best performing task: {findings['task_performance']['best_performing']} "
                     f"({findings['task_performance']['best_success_rate']:.1%} success rate)")
    conclusion.append(f"• Worst performing task: {findings['task_performance']['worst_performing']} "
                     f"({findings['task_performance']['worst_success_rate']:.1%} success rate)")
    
    if findings['task_performance']['performance_gap'] > 0.2:
        conclusion.append(f"• Significant performance gap ({findings['task_performance']['performance_gap']:.1%}) "
                         "suggests task-specific optimization opportunities.")
    
    # 统计验证
    conclusion.append("\nSTATISTICAL VALIDATION:")
    if findings['statistical_significance']['overall_significant']:
        conclusion.append("✓ Overall performance is statistically significant compared to baseline.")
    else:
        conclusion.append("⚠ Overall performance improvement over baseline is not statistically significant.")
    
    if findings['statistical_significance']['task_differences_significant']:
        conclusion.append("✓ Significant differences exist between task types, indicating task-dependent performance.")
    else:
        conclusion.append("• No significant differences between task types were found.")
    
    if findings['statistical_significance']['performance_differences_significant']:
        conclusion.append("✓ Clear performance differences exist between successful and failed attempts.")
    else:
        conclusion.append("• Performance characteristics are similar between successful and failed attempts.")
    
    # 相关性洞察
    conclusion.append("\nKEY INSIGHTS:")
    correlations = findings['key_correlations']
    if correlations['strong_correlations']:
        for corr in correlations['strong_correlations']:
            if corr == 'token_success':
                conclusion.append("• Token usage shows meaningful correlation with success rate.")
            elif corr == 'tool_time':
                conclusion.append("• Tool call frequency correlates with completion time.")
    else:
        conclusion.append("• No strong correlations were found between measured metrics.")
    
    # 建议
    conclusion.append("\nRECOMMENDATIONS:")
    recommendations = []
    
    if not findings['overall_performance']['is_successful']:
        recommendations.append("1. Focus on improving core success rate through better error handling and planning.")
    
    if not findings['overall_performance']['efficiency']:
        recommendations.append("2. Optimize agent logic to reduce completion time, possibly through parallel operations.")
    
    if not findings['overall_performance']['resource_usage']:
        recommendations.append("3. Implement token usage optimization strategies, such as more concise responses.")
    
    if findings['task_performance']['performance_gap'] > 0.2:
        recommendations.append("4. Develop task-specific strategies for underperforming task types.")
    
    if findings['statistical_significance']['task_differences_significant']:
        recommendations.append("5. Consider implementing adaptive tool selection based on task type.")
    
    if not recommendations:
        recommendations.append("1. Maintain current implementation as it meets all performance criteria.")
        recommendations.append("2. Consider expanding to more complex scenarios to test scalability.")
    
    conclusion.extend(recommendations)
    
    # 未来工作
    conclusion.append("\nFUTURE WORK:")
    conclusion.append("• Extend testing to more diverse and complex real-world scenarios")
    conclusion.append("• Implement adaptive learning capabilities for continuous improvement")
    conclusion.append("• Explore integration with additional tool types and external APIs")
    conclusion.append("• Conduct user studies to evaluate practical utility and usability")
    
    conclusion.append("\n" + "=" * 80)
    
    return "\n".join(conclusion)

def save_conclusion(conclusion: str):
    """保存结论"""
    with open("results/final_conclusion.txt", 'w') as f:
        f.write(conclusion)
    
    logger.info("Final conclusion saved to results/final_conclusion.txt")

def main():
    """主函数"""
    try:
        # 加载分析结果
        results = load_analysis_results()
        
        # 提取关键发现
        findings = extract_key_findings(results)
        
        # 生成结论
        conclusion = generate_conclusion(findings)
        
        # 打印结论
        print(conclusion)
        
        # 保存结论
        save_conclusion(conclusion)
        
        logger.info("Conclusion summary completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in conclusion summary: {str(e)}")
        raise

if __name__ == "__main__":
    main()