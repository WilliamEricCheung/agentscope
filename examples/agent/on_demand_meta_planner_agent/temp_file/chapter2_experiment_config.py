#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 2: Experiment Configuration
==================================
实验配置参数定义，包含所有可调参数和实验设置。
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any

@dataclass
class ExperimentConfig:
    """实验配置参数类"""
    
    # 基本实验设置
    experiment_name: str = "mcp_agent_experiment"
    random_seed: int = 42
    num_trials: int = 100
    max_steps: int = 50
    
    # Agent配置
    agent_type: str = "worker"
    temperature: float = 0.7
    max_tokens: int = 2000
    use_streaming: bool = True
    speculation_interval: int = 20
    
    # 工具配置
    available_tool_groups: List[str] = None
    active_tools: List[str] = None
    
    # 实验参数
    test_scenarios: List[str] = None
    evaluation_metrics: List[str] = None
    success_threshold: float = 0.8
    
    # 文件路径配置
    data_dir: str = "data"
    results_dir: str = "results"
    figures_dir: str = "figures"
    log_file: str = "experiment.log"
    
    def __post_init__(self):
        """初始化默认值"""
        if self.available_tool_groups is None:
            self.available_tool_groups = ["browser_tools"]
        
        if self.active_tools is None:
            self.active_tools = [
                "write_text_file", "insert_text_file", "view_text_file",
                "reset_equipped_tools", "generate_response"
            ]
        
        if self.test_scenarios is None:
            self.test_scenarios = [
                "web_browsing", "file_operations", "tool_activation",
                "multi_step_reasoning", "error_handling"
            ]
        
        if self.evaluation_metrics is None:
            self.evaluation_metrics = [
                "success_rate", "completion_time", "token_usage",
                "tool_calls", "error_rate"
            ]

def create_default_config() -> ExperimentConfig:
    """创建默认实验配置"""
    return ExperimentConfig()

def save_config(config: ExperimentConfig, filepath: str = "experiment_config.json"):
    """保存配置到JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=4, ensure_ascii=False)

def load_config(filepath: str = "experiment_config.json") -> ExperimentConfig:
    """从JSON文件加载配置"""
    with open(filepath, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
    return ExperimentConfig(**config_dict)

# 创建并保存默认配置
if __name__ == "__main__":
    config = create_default_config()
    save_config(config)
    print(f"Default configuration saved to experiment_config.json")
    print(f"Experiment name: {config.experiment_name}")
    print(f"Number of trials: {config.num_trials}")
    print(f"Available tool groups: {config.available_tool_groups}")