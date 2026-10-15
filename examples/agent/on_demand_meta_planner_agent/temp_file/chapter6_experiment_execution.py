#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 6: Experiment Execution
==============================
实验执行代码，运行完整的实验流程。
"""

import logging
import time
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

# 导入必要的模块
try:
    from chapter2_experiment_config import ExperimentConfig, load_config
    from chapter4_test_data import load_test_data
    from chapter5_agent_implementation import MCPAgent
except ImportError:
    # 在独立运行时提供简化版本
    pass

logger = logging.getLogger(__name__)

class ExperimentRunner:
    """实验执行器"""
    
    def __init__(self, config: ExperimentConfig = None):
        """初始化实验执行器"""
        self.config = config or load_config() if Path("experiment_config.json").exists() else ExperimentConfig()
        self.results = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def run_single_trial(self, scenario: Dict[str, Any], trial_id: int) -> Dict[str, Any]:
        """运行单个试验"""
        start_time = time.time()
        token_usage = 0
        tool_calls = 0
        errors = 0
        
        try:
            # 创建Agent实例
            agent = MCPAgent(self.config)
            
            # 执行任务
            task_description = f"Execute {scenario['task_type']} task with complexity {scenario['complexity']}"
            result = agent.process_task(task_description, scenario)
            
            # 记录结果
            trial_result = {
                'trial_id': trial_id,
                'scenario_id': scenario['scenario_id'],
                'task_type': scenario['task_type'],
                'complexity': scenario['complexity'],
                'success': result.success,
                'completion_time': time.time() - start_time,
                'token_usage': token_usage,  # 在实际实现中会跟踪token使用
                'tool_calls': tool_calls,    # 在实际实现中会跟踪工具调用
                'errors': errors,
                'final_message': result.message[:200] if result.message else ""  # 截断长消息
            }
            
            self.logger.info(f"Trial {trial_id} completed: {'Success' if result.success else 'Failed'}")
            return trial_result
            
        except Exception as e:
            self.logger.error(f"Trial {trial_id} failed with error: {str(e)}")
            return {
                'trial_id': trial_id,
                'scenario_id': scenario['scenario_id'],
                'task_type': scenario['task_type'],
                'complexity': scenario['complexity'],
                'success': False,
                'completion_time': time.time() - start_time,
                'token_usage': token_usage,
                'tool_calls': tool_calls,
                'errors': 1,
                'final_message': f"Error: {str(e)}"
            }
    
    def run_all_trials(self) -> pd.DataFrame:
        """运行所有试验"""
        self.logger.info(f"Starting experiment: {self.config.experiment_name}")
        self.logger.info(f"Number of trials: {self.config.num_trials}")
        
        # 加载测试数据
        try:
            scenarios, _ = load_test_data()
        except FileNotFoundError:
            self.logger.warning("Test data not found, generating minimal test scenarios")
            scenarios = self._generate_minimal_scenarios()
        
        # 运行试验
        for trial_id in range(1, self.config.num_trials + 1):
            # 循环使用场景（如果场景数量少于试验数量）
            scenario = scenarios[(trial_id - 1) % len(scenarios)]
            result = self.run_single_trial(scenario, trial_id)
            self.results.append(result)
            
            # 显示进度
            if trial_id % 10 == 0:
                success_rate = sum(r['success'] for r in self.results) / len(self.results)
                self.logger.info(f"Progress: {trial_id}/{self.config.num_trials}, Success rate: {success_rate:.2%}")
        
        # 转换为DataFrame
        results_df = pd.DataFrame(self.results)
        
        # 保存结果
        results_path = Path(self.config.results_dir) / "experiment_results.csv"
        results_path.parent.mkdir(exist_ok=True)
        results_df.to_csv(results_path, index=False)
        
        self.logger.info(f"Experiment completed! Results saved to {results_path}")
        return results_df
    
    def _generate_minimal_scenarios(self) -> List[Dict[str, Any]]:
        """生成最小测试场景（当没有预定义数据时）"""
        return [
            {
                "scenario_id": "minimal_001",
                "task_type": "file_operation",
                "complexity": "simple",
                "steps": ["Create", "Read", "Write"],
                "success_criteria": "Basic file operations work"
            },
            {
                "scenario_id": "minimal_002",
                "task_type": "web_browsing",
                "complexity": "medium",
                "steps": ["Activate", "Navigate", "Extract"],
                "success_criteria": "Web tools work correctly"
            },
            {
                "scenario_id": "minimal_003",
                "task_type": "tool_activation",
                "complexity": "simple",
                "steps": ["Deactivate", "Activate", "Use"],
                "success_criteria": "Tool switching works"
            }
        ]

def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建实验执行器
    runner = ExperimentRunner()
    
    # 运行实验
    results_df = runner.run_all_trials()
    
    # 显示摘要
    print("\n" + "="*50)
    print("EXPERIMENT SUMMARY")
    print("="*50)
    print(f"Total trials: {len(results_df)}")
    print(f"Success rate: {results_df['success'].mean():.2%}")
    print(f"Average completion time: {results_df['completion_time'].mean():.2f}s")
    print(f"Average tool calls: {results_df['tool_calls'].mean():.1f}")
    print(f"Error rate: {results_df['errors'].mean():.2%}")
    
    # 按任务类型分组统计
    print("\nBy task type:")
    task_summary = results_df.groupby('task_type')['success'].agg(['mean', 'count'])
    task_summary.columns = ['Success Rate', 'Count']
    print(task_summary.round(3))

if __name__ == "__main__":
    main()