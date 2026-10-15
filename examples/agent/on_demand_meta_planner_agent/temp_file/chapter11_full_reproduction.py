#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 11: Full Reproduction Script
===================================
完整复现脚本，按顺序执行所有章节的代码以复现实验。
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_script(script_name: str, cwd: str = ".") -> bool:
    """运行指定的Python脚本"""
    try:
        logger.info(f"Running {script_name}...")
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            logger.info(f"{script_name} completed successfully")
            return True
        else:
            logger.error(f"{script_name} failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"{script_name} timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error running {script_name}: {str(e)}")
        return False

def main():
    """主函数 - 按顺序执行所有章节"""
    logger.info("Starting full experiment reproduction...")
    
    # 创建必要的目录
    Path("data").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)
    Path("figures").mkdir(exist_ok=True)
    
    # 定义执行顺序
    chapters = [
        "chapter1_environment_setup.py",
        "chapter2_experiment_config.py",
        "chapter3_tool_simulator.py",
        "chapter4_test_data.py",
        "chapter5_agent_implementation.py",
        "chapter6_experiment_execution.py",
        "chapter7_results_processing.py",
        "chapter8_visualization.py",
        "chapter9_statistical_tests.py",
        "chapter10_conclusion_summary.py"
    ]
    
    # 执行每个章节
    failed_chapters = []
    
    for chapter in chapters:
        if not run_script(chapter):
            failed_chapters.append(chapter)
            logger.error(f"Stopping execution due to failure in {chapter}")
            break
    
    # 生成最终报告
    if not failed_chapters:
        logger.info("All chapters executed successfully!")
        logger.info("Experiment reproduction completed!")
        
        # 显示关键结果文件
        result_files = [
            "results/experiment_results.csv",
            "results/processed_results.csv",
            "results/experiment_metrics.json",
            "results/final_conclusion.txt"
        ]
        
        logger.info("Key result files generated:")
        for file in result_files:
            if Path(file).exists():
                logger.info(f"  ✓ {file}")
            else:
                logger.warning(f"  ✗ {file} (not found)")
        
        # 显示图形文件
        figure_files = list(Path("figures").glob("*.png"))
        logger.info(f"Generated {len(figure_files)} visualization files in figures/ directory")
        
    else:
        logger.error(f"Experiment reproduction failed at chapter: {failed_chapters[0]}")
        sys.exit(1)

if __name__ == "__main__":
    main()