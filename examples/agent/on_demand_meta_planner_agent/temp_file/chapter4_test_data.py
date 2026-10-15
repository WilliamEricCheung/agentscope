#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 4: Test Data Preparation
===============================
测试数据准备，生成各种测试场景所需的数据。
"""

import numpy as np
import pandas as pd
import json
import random
from typing import Dict, List, Any
from pathlib import Path

def generate_test_scenarios(num_scenarios: int = 10) -> List[Dict[str, Any]]:
    """生成测试场景"""
    scenarios = []
    
    task_types = [
        "file_operation", "web_browsing", "tool_activation",
        "multi_step_reasoning", "error_handling"
    ]
    
    for i in range(num_scenarios):
        scenario = {
            "scenario_id": f"scenario_{i+1:03d}",
            "task_type": random.choice(task_types),
            "complexity": random.choice(["simple", "medium", "complex"]),
            "expected_tools": [],
            "steps": [],
            "success_criteria": ""
        }
        
        # 根据任务类型设置预期工具和步骤
        if scenario["task_type"] == "file_operation":
            scenario["expected_tools"] = ["write_text_file", "view_text_file", "insert_text_file"]
            scenario["steps"] = [
                "Create a new file with initial content",
                "Read the file to verify content",
                "Insert additional content at specific line",
                "Verify final content"
            ]
            scenario["success_criteria"] = "All file operations complete successfully"
            
        elif scenario["task_type"] == "web_browsing":
            scenario["expected_tools"] = ["reset_equipped_tools", "browser_click", "browser_evaluate"]
            scenario["steps"] = [
                "Activate browser tools",
                "Navigate to target website",
                "Extract relevant information",
                "Process extracted data"
            ]
            scenario["success_criteria"] = "Required information extracted successfully"
            
        elif scenario["task_type"] == "tool_activation":
            scenario["expected_tools"] = ["reset_equipped_tools"]
            scenario["steps"] = [
                "Start with basic tools only",
                "Activate browser tools when needed",
                "Perform required operations",
                "Deactivate unnecessary tools"
            ]
            scenario["success_criteria"] = "Tools activated/deactivated appropriately"
            
        elif scenario["task_type"] == "multi_step_reasoning":
            scenario["expected_tools"] = ["write_text_file", "view_text_file", "generate_response"]
            scenario["steps"] = [
                "Analyze the problem requirements",
                "Plan the solution steps",
                "Execute each step with appropriate tools",
                "Synthesize final answer"
            ]
            scenario["success_criteria"] = "Correct final answer generated"
            
        elif scenario["task_type"] == "error_handling":
            scenario["expected_tools"] = ["view_text_file", "generate_response"]
            scenario["steps"] = [
                "Attempt operation that may fail",
                "Detect and handle errors appropriately",
                "Recover from error state",
                "Complete task successfully"
            ]
            scenario["success_criteria"] = "Errors handled gracefully, task completed"
        
        scenarios.append(scenario)
    
    return scenarios

def generate_synthetic_results(num_trials: int = 100) -> pd.DataFrame:
    """生成合成实验结果数据"""
    np.random.seed(42)
    
    data = {
        'trial_id': range(1, num_trials + 1),
        'scenario_id': [f"scenario_{random.randint(1, 10):03d}" for _ in range(num_trials)],
        'task_type': np.random.choice(
            ['file_operation', 'web_browsing', 'tool_activation', 'multi_step_reasoning', 'error_handling'],
            num_trials
        ),
        'success': np.random.binomial(1, 0.85, num_trials),  # 85% success rate
        'completion_time': np.random.exponential(10, num_trials),  # 耗时分布
        'token_usage': np.random.poisson(500, num_trials),  # token使用量
        'tool_calls': np.random.poisson(5, num_trials),  # 工具调用次数
        'errors': np.random.poisson(0.5, num_trials),  # 错误次数
        'complexity': np.random.choice(['simple', 'medium', 'complex'], num_trials, p=[0.4, 0.4, 0.2])
    }
    
    df = pd.DataFrame(data)
    
    # 调整复杂任务的成功率
    complex_mask = df['complexity'] == 'complex'
    df.loc[complex_mask, 'success'] = np.random.binomial(1, 0.7, complex_mask.sum())
    
    return df

def save_test_data(scenarios: List[Dict[str, Any]], results_df: pd.DataFrame):
    """保存测试数据到文件"""
    # 保存场景数据
    with open(Path("data") / "test_scenarios.json", 'w', encoding='utf-8') as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)
    
    # 保存结果数据
    results_df.to_csv(Path("data") / "synthetic_results.csv", index=False)
    
    # 保存样本数据用于快速测试
    sample_scenarios = scenarios[:3]
    with open(Path("data") / "sample_scenarios.json", 'w', encoding='utf-8') as f:
        json.dump(sample_scenarios, f, indent=2, ensure_ascii=False)
    
    sample_results = results_df.head(10)
    sample_results.to_csv(Path("data") / "sample_results.csv", index=False)

def load_test_data() -> tuple:
    """加载测试数据"""
    scenarios_path = Path("data") / "test_scenarios.json"
    results_path = Path("data") / "synthetic_results.csv"
    
    if not scenarios_path.exists() or not results_path.exists():
        raise FileNotFoundError("Test data files not found. Please run data generation first.")
    
    with open(scenarios_path, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)
    
    results_df = pd.read_csv(results_path)
    
    return scenarios, results_df

# 生成和保存测试数据
if __name__ == "__main__":
    # 创建数据目录
    Path("data").mkdir(exist_ok=True)
    
    # 生成测试数据
    scenarios = generate_test_scenarios(10)
    results_df = generate_synthetic_results(100)
    
    # 保存数据
    save_test_data(scenarios, results_df)
    
    print(f"Generated {len(scenarios)} test scenarios")
    print(f"Generated {len(results_df)} synthetic results")
    print("Test data saved to data/ directory")
    
    # 显示样本数据
    print("\nSample scenarios:")
    for scenario in scenarios[:2]:
        print(f"- {scenario['scenario_id']}: {scenario['task_type']} ({scenario['complexity']})")
    
    print(f"\nResults summary:")
    print(results_df[['task_type', 'success', 'completion_time', 'token_usage']].describe())