#!/usr/bin/env python3
"""
多轮规划代理稳健性基准测试脚本
"""

import argparse
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List

def load_test_scenarios():
    """加载测试场景"""
    scenarios = {
        "basic_functionality": [
            {
                "name": "simple_web_search",
                "description": "基本网络搜索功能测试",
                "steps": [
                    {
                        "tool": "web_search",
                        "parameters": {"query": "artificial intelligence", "num_results": 3}
                    }
                ]
            },
            {
                "name": "file_read_write",
                "description": "文件读写操作测试",
                "steps": [
                    {
                        "tool": "file_system",
                        "parameters": {"operation": "write", "path": "/tmp/test.txt", "content": "Hello World"}
                    },
                    {
                        "tool": "file_system",
                        "parameters": {"operation": "read", "path": "/tmp/test.txt"}
                    }
                ]
            }
        ],
        "error_recovery": [
            {
                "name": "search_timeout_recovery",
                "description": "搜索超时后的恢复测试",
                "steps": [
                    {
                        "tool": "web_search",
                        "parameters": {"query": "very slow query", "num_results": 10},
                        "expected_failure": "timeout"
                    },
                    {
                        "tool": "web_search",
                        "parameters": {"query": "very slow query", "num_results": 3},
                        "retry": True
                    }
                ]
            },
            {
                "name": "file_permission_recovery",
                "description": "文件权限错误恢复测试",
                "steps": [
                    {
                        "tool": "file_system",
                        "parameters": {"operation": "write", "path": "/root/protected.txt", "content": "test"},
                        "expected_failure": "permission_denied"
                    },
                    {
                        "tool": "file_system",
                        "parameters": {"operation": "write", "path": "/tmp/fallback.txt", "content": "test"}
                    }
                ]
            }
        ],
        "complex_tasks": [
            {
                "name": "research_task",
                "description": "复杂研究任务：搜索、分析、存储",
                "steps": [
                    {
                        "tool": "web_search",
                        "parameters": {"query": "multi-step planning agents robustness", "num_results": 5}
                    },
                    {
                        "tool": "file_system",
                        "parameters": {"operation": "write", "path": "/tmp/research_results.json", "content": '{"results": []}'}
                    },
                    {
                        "tool": "api_call",
                        "parameters": {"endpoint": "/api/analyze", "method": "POST", "data": {"text": "research summary"}}
                    }
                ]
            }
        ]
    }
    return scenarios

def simulate_agent_execution(scenario: Dict[str, Any], tool_manager) -> Dict[str, Any]:
    """模拟代理执行场景"""
    results = {
        "scenario_name": scenario["name"],
        "steps_executed": 0,
        "steps_successful": 0,
        "errors": [],
        "execution_time": 0,
        "final_state": "unknown"
    }
    
    start_time = time.time()
    
    for step in scenario["steps"]:
        try:
            # 模拟代理决策过程
            tool_name = step["tool"]
            parameters = step["parameters"]
            
            # 执行工具
            result = tool_manager.execute_tool(tool_name, parameters)
            results["steps_executed"] += 1
            
            if result["success"]:
                results["steps_successful"] += 1
            else:
                results["errors"].append({
                    "step": results["steps_executed"],
                    "tool": tool_name,
                    "error": result.get("error", "Unknown error"),
                    "error_type": result.get("error_type", "unknown")
                })
                
                # 检查是否需要重试
                if step.get("retry", False) and len(results["errors"]) > 0:
                    # 简单的重试逻辑
                    retry_result = tool_manager.execute_tool(tool_name, parameters)
                    results["steps_executed"] += 1
                    if retry_result["success"]:
                        results["steps_successful"] += 1
                        # 移除之前的错误（因为重试成功了）
                        if results["errors"]:
                            results["errors"].pop()
            
        except Exception as e:
            results["errors"].append({
                "step": results["steps_executed"] + 1,
                "tool": step.get("tool", "unknown"),
                "error": str(e),
                "error_type": "execution_exception"
            })
    
    end_time = time.time()
    results["execution_time"] = end_time - start_time
    
    # 确定最终状态
    if results["steps_executed"] == 0:
        results["final_state"] = "no_execution"
    elif results["steps_successful"] == results["steps_executed"]:
        results["final_state"] = "success"
    elif results["steps_successful"] > 0:
        results["final_state"] = "partial_success"
    else:
        results["final_state"] = "failure"
    
    return results

def run_benchmark(agent_config: str, scenarios_to_run: str):
    """运行基准测试"""
    print("加载测试场景...")
    all_scenarios = load_test_scenarios()
    
    # 确定要运行的场景
    if scenarios_to_run == "all":
        scenarios_to_execute = []
        for category in all_scenarios.values():
            scenarios_to_execute.extend(category)
    else:
        scenarios_to_execute = all_scenarios.get(scenarios_to_run, [])
        if not scenarios_to_execute:
            print(f"未找到场景类别: {scenarios_to_run}")
            return
    
    print(f"准备运行 {len(scenarios_to_execute)} 个测试场景...")
    
    # 创建模拟工具管理器（简化版，不依赖实际文件）
    class MockToolManager:
        def __init__(self, config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        
        def execute_tool(self, tool_name, parameters):
            # 模拟工具执行
            if tool_name not in self.config["tools"]:
                return {"success": False, "error": f"Tool {tool_name} not found", "error_type": "tool_not_found"}
            
            tool_config = self.config["tools"][tool_name]
            success_rate = tool_config.get("success_rate", 0.9)
            
            if random.random() < success_rate:
                return {"success": True, "result": f"Simulated result for {tool_name}"}
            else:
                failure_modes = tool_config.get("failure_modes", ["unknown_error"])
                error_type = random.choice(failure_modes)
                return {"success": False, "error": f"Simulated {error_type}", "error_type": error_type}
    
    tool_manager = MockToolManager("tools_config.json")
    
    # 执行所有场景
    all_results = []
    for scenario in scenarios_to_execute:
        print(f"执行场景: {scenario['name']}")
        result = simulate_agent_execution(scenario, tool_manager)
        all_results.append(result)
        print(f"  结果: {result['final_state']} ({result['steps_successful']}/{result['steps_executed']} 步骤成功)")
        time.sleep(0.1)  # 避免过于密集的输出
    
    # 生成汇总报告
    total_scenarios = len(all_results)
    successful_scenarios = sum(1 for r in all_results if r["final_state"] == "success")
    partial_success_scenarios = sum(1 for r in all_results if r["final_state"] == "partial_success")
    
    print("\n" + "="*60)
    print("基准测试汇总报告")
    print("="*60)
    print(f"总场景数: {total_scenarios}")
    print(f"完全成功: {successful_scenarios} ({successful_scenarios/total_scenarios*100:.1f}%)")
    print(f"部分成功: {partial_success_scenarios} ({partial_success_scenarios/total_scenarios*100:.1f}%)")
    print(f"完全失败: {total_scenarios - successful_scenarios - partial_success_scenarios} ({(total_scenarios - successful_scenarios - partial_success_scenarios)/total_scenarios*100:.1f}%)")
    
    # 计算平均执行时间
    avg_time = sum(r["execution_time"] for r in all_results) / total_scenarios
    print(f"平均执行时间: {avg_time:.3f} 秒")
    
    # 保存详细结果
    results_file = "benchmark_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n详细结果已保存到: {results_file}")

def main():
    parser = argparse.ArgumentParser(description="运行多轮规划代理稳健性基准测试")
    parser.add_argument("--agent", default="default", help="代理配置文件")
    parser.add_argument("--scenarios", default="all", 
                       help="要运行的场景类别 (basic_functionality, error_recovery, complex_tasks, 或 all)")
    
    args = parser.parse_args()
    
    run_benchmark(args.agent, args.scenarios)

if __name__ == "__main__":
    main()