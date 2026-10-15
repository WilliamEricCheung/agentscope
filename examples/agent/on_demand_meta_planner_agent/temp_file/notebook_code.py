# Jupyter MCP环境中的多轮规划代理实验框架

# 1) 依赖导入和环境设置
import os
import sys
import json
import time
import random
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保在Jupyter环境中运行
try:
    get_ipython()
    IN_JUPYTER = True
except NameError:
    IN_JUPYTER = False

# 2) 实验配置参数的具体定义
@dataclass
class ExperimentConfig:
    """实验配置参数"""
    # 基础配置
    experiment_name: str = "multi_round_planning"
    max_rounds: int = 5
    max_steps_per_round: int = 10
    
    # 代理配置
    agent_temperature: float = 0.7
    agent_max_tokens: int = 500
    
    # 扰动配置
    perturbation_probability: float = 0.3
    perturbation_types: List[str] = None
    
    # 输出配置
    output_dir: str = "./results"
    save_intermediate: bool = True
    
    def __post_init__(self):
        if self.perturbation_types is None:
            self.perturbation_types = ["noise", "delay", "interruption"]
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

# 3) 工具环境模拟器的核心实现
class ToolEnvironmentSimulator:
    """工具环境模拟器"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.tools = {
            "search": self._search_tool,
            "calculate": self._calculate_tool,
            "memory": self._memory_tool,
            "api_call": self._api_call_tool
        }
        self.memory_store = {}
        self.call_count = 0
        
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行指定工具"""
        try:
            if tool_name not in self.tools:
                return {"error": f"Unknown tool: {tool_name}"}
            
            self.call_count += 1
            result = self.tools[tool_name](**kwargs)
            return {"success": True, "result": result, "call_id": self.call_count}
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e), "call_id": self.call_count}
    
    def _search_tool(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """模拟搜索工具"""
        # 在真实环境中，这里会调用实际的搜索引擎API
        results = []
        for i in range(min(max_results, 3)):  # 模拟返回3个结果
            results.append({
                "title": f"Result {i+1} for '{query}'",
                "snippet": f"This is a simulated search result snippet for query: {query}",
                "url": f"http://example.com/result{i+1}"
            })
        return results
    
    def _calculate_tool(self, expression: str) -> float:
        """模拟计算工具"""
        # 注意：在生产环境中，应该使用更安全的表达式求值方法
        try:
            # 简单的安全检查
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            return eval(expression)
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")
    
    def _memory_tool(self, operation: str, key: str = None, value: Any = None) -> Any:
        """模拟记忆工具"""
        if operation == "store":
            if key is None or value is None:
                raise ValueError("Key and value required for store operation")
            self.memory_store[key] = value
            return "Stored successfully"
        elif operation == "retrieve":
            if key is None:
                raise ValueError("Key required for retrieve operation")
            return self.memory_store.get(key, None)
        elif operation == "list":
            return list(self.memory_store.keys())
        else:
            raise ValueError(f"Unknown memory operation: {operation}")
    
    def _api_call_tool(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """模拟API调用工具"""
        # 模拟不同的API响应
        if endpoint == "weather":
            return {"temperature": 22.5, "condition": "sunny", "location": params.get("location", "unknown")}
        elif endpoint == "stock":
            symbol = params.get("symbol", "AAPL")
            return {"symbol": symbol, "price": round(random.uniform(100, 300), 2), "change": round(random.uniform(-5, 5), 2)}
        else:
            return {"message": f"Mock response for {endpoint}", "params": params}

# 4) 多轮规划代理的基础框架
class MultiRoundPlanningAgent:
    """多轮规划代理基础框架"""
    
    def __init__(self, config: ExperimentConfig, environment: ToolEnvironmentSimulator):
        self.config = config
        self.environment = environment
        self.current_round = 0
        self.plan_history = []
        self.execution_history = []
        
    def plan(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成计划"""
        if context is None:
            context = {}
            
        # 简单的计划生成逻辑（在实际应用中，这里会使用LLM）
        plan = {
            "task": task,
            "steps": [
                {"step_id": 1, "action": "analyze", "description": f"Analyze the task: {task}"},
                {"step_id": 2, "action": "gather_info", "description": "Gather necessary information using tools"},
                {"step_id": 3, "action": "execute", "description": "Execute the main task logic"},
                {"step_id": 4, "action": "validate", "description": "Validate the results"}
            ],
            "expected_tools": ["search", "calculate", "memory"],
            "round": self.current_round
        }
        
        self.plan_history.append(plan)
        return plan
    
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        # 这里简化了执行逻辑，在实际应用中会更复杂
        action = step.get("action")
        
        if action == "analyze":
            return {"status": "completed", "result": "Task analysis completed"}
        elif action == "gather_info":
            # 使用工具收集信息
            search_result = self.environment.execute_tool("search", query="example query")
            return {"status": "completed", "result": search_result}
        elif action == "execute":
            # 执行计算示例
            calc_result = self.environment.execute_tool("calculate", expression="2 + 2 * 3")
            return {"status": "completed", "result": calc_result}
        elif action == "validate":
            return {"status": "completed", "result": "Results validated successfully"}
        else:
            return {"status": "failed", "error": f"Unknown action: {action}"}
    
    def run_round(self, task: str) -> Dict[str, Any]:
        """运行一轮完整的规划-执行循环"""
        self.current_round += 1
        logger.info(f"Starting round {self.current_round}")
        
        # 生成计划
        plan = self.plan(task)
        
        # 执行计划步骤
        execution_results = []
        for step in plan["steps"][:self.config.max_steps_per_round]:
            result = self.execute_step(step)
            execution_results.append({
                "step": step,
                "result": result,
                "timestamp": time.time()
            })
            
            if result.get("status") == "failed":
                logger.warning(f"Step failed in round {self.current_round}: {result.get('error')}")
                break
        
        round_result = {
            "round": self.current_round,
            "plan": plan,
            "execution": execution_results,
            "success": all(r["result"].get("status") == "completed" for r in execution_results)
        }
        
        self.execution_history.append(round_result)
        return round_result

# 5) 扰动注入机制的示例代码
class PerturbationInjector:
    """扰动注入机制"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.perturbation_count = 0
        
    def should_inject_perturbation(self) -> bool:
        """决定是否注入扰动"""
        return random.random() < self.config.perturbation_probability
    
    def inject_perturbation(self, agent: MultiRoundPlanningAgent, 
                          current_state: Dict[str, Any]) -> Dict[str, Any]:
        """注入扰动到当前状态"""
        if not self.should_inject_perturbation():
            return current_state
            
        perturbation_type = random.choice(self.config.perturbation_types)
        self.perturbation_count += 1
        
        logger.info(f"Injecting perturbation: {perturbation_type}")
        
        if perturbation_type == "noise":
            # 添加随机噪声到结果中
            if "execution" in current_state:
                for exec_item in current_state["execution"]:
                    if "result" in exec_item and isinstance(exec_item["result"], dict):
                        exec_item["result"]["perturbation"] = "noise_added"
                        
        elif perturbation_type == "delay":
            # 模拟延迟
            delay_time = random.uniform(0.1, 1.0)
            time.sleep(delay_time)
            current_state["delay_injected"] = delay_time
            
        elif perturbation_type == "interruption":
            # 模拟中断
            if "execution" in current_state and len(current_state["execution"]) > 1:
                # 移除最后一个执行步骤来模拟中断
                current_state["execution"] = current_state["execution"][:-1]
                current_state["interruption_occurred"] = True
                
        current_state["perturbation_applied"] = perturbation_type
        return current_state

# 6) 实验执行循环的骨架
def run_experiment(config: ExperimentConfig, task: str) -> Dict[str, Any]:
    """实验执行主循环"""
    logger.info(f"Starting experiment: {config.experiment_name}")
    
    # 初始化组件
    environment = ToolEnvironmentSimulator(config)
    agent = MultiRoundPlanningAgent(config, environment)
    perturbation_injector = PerturbationInjector(config)
    
    # 存储实验结果
    experiment_results = {
        "config": config.__dict__,
        "task": task,
        "rounds": [],
        "final_result": None,
        "total_perturbations": 0,
        "start_time": time.time()
    }
    
    # 执行多轮实验
    for round_num in range(config.max_rounds):
        try:
            # 运行一轮
            round_result = agent.run_round(task)
            
            # 注入扰动（如果适用）
            round_result = perturbation_injector.inject_perturbation(agent, round_result)
            
            # 更新扰动计数
            if "perturbation_applied" in round_result:
                experiment_results["total_perturbations"] += 1
            
            # 保存轮次结果
            experiment_results["rounds"].append(round_result)
            
            # 如果配置要求保存中间结果
            if config.save_intermediate:
                intermediate_file = os.path.join(
                    config.output_dir, 
                    f"intermediate_round_{round_num + 1}.json"
                )
                with open(intermediate_file, 'w') as f:
                    json.dump(round_result, f, indent=2, default=str)
            
            # 检查是否成功完成（简单条件）
            if round_result["success"]:
                logger.info(f"Task completed successfully in round {round_num + 1}")
                break
                
        except Exception as e:
            logger.error(f"Error in round {round_num + 1}: {e}")
            experiment_results["rounds"].append({
                "round": round_num + 1,
                "error": str(e),
                "timestamp": time.time()
            })
            continue
    
    # 设置最终结果
    experiment_results["end_time"] = time.time()
    experiment_results["duration"] = experiment_results["end_time"] - experiment_results["start_time"]
    
    # 简单的成功判断
    successful_rounds = [r for r in experiment_results["rounds"] if r.get("success", False)]
    experiment_results["final_result"] = {
        "success": len(successful_rounds) > 0,
        "completed_rounds": len(experiment_results["rounds"]),
        "successful_rounds": len(successful_rounds)
    }
    
    return experiment_results

# 7) 结果收集的基本函数
def collect_and_save_results(experiment_results: Dict[str, Any], 
                           config: ExperimentConfig) -> str:
    """收集并保存实验结果"""
    try:
        # 创建结果文件路径
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(
            config.output_dir, 
            f"{config.experiment_name}_{timestamp}.json"
        )
        
        # 保存完整结果
        with open(results_file, 'w') as f:
            json.dump(experiment_results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {results_file}")
        return results_file
        
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        return None

# 8) 简单的可视化代码
def visualize_results(results_file: str):
    """简单的结果可视化"""
    try:
        import matplotlib.pyplot as plt
        
        # 加载结果
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # 创建可视化
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Experiment Results: {results["config"]["experiment_name"]}')
        
        # 1. 轮次成功率
        rounds = results["rounds"]
        round_numbers = [r["round"] for r in rounds]
        success_status = [1 if r.get("success", False) else 0 for r in rounds]
        
        axes[0, 0].bar(round_numbers, success_status)
        axes[0, 0].set_title('Round Success Status')
        axes[0, 0].set_xlabel('Round Number')
        axes[0, 0].set_ylabel('Success (1) / Failure (0)')
        
        # 2. 扰动统计
        perturbation_counts = {}
        for r in rounds:
            pert_type = r.get("perturbation_applied", "none")
            perturbation_counts[pert_type] = perturbation_counts.get(pert_type, 0) + 1
        
        if len(perturbation_counts) > 1 or "none" not in perturbation_counts:
            axes[0, 1].pie(perturbation_counts.values(), labels=perturbation_counts.keys(), autopct='%1.1f%%')
            axes[0, 1].set_title('Perturbation Distribution')
        
        # 3. 执行时间（如果有时间戳）
        execution_times = []
        for r in rounds:
            if "execution" in r and len(r["execution"]) > 0:
                first_ts = r["execution"][0].get("timestamp", 0)
                last_ts = r["execution"][-1].get("timestamp", 0)
                execution_times.append(last_ts - first_ts if last_ts > first_ts else 0)
            else:
                execution_times.append(0)
        
        if any(t > 0 for t in execution_times):
            axes[1, 0].plot(round_numbers, execution_times, 'o-')
            axes[1, 0].set_title('Execution Time per Round')
            axes[1, 0].set_xlabel('Round Number')
            axes[1, 0].set_ylabel('Time (seconds)')
        
        # 4. 工具调用统计
        tool_calls = {}
        for r in rounds:
            if "execution" in r:
                for exec_item in r["execution"]:
                    if "result" in exec_item and isinstance(exec_item["result"], dict):
                        call_id = exec_item["result"].get("call_id")
                        if call_id:
                            tool_calls[call_id] = tool_calls.get(call_id, 0) + 1
        
        if tool_calls:
            axes[1, 1].hist(list(tool_calls.values()), bins=10)
            axes[1, 1].set_title('Tool Call Distribution')
            axes[1, 1].set_xlabel('Number of Calls')
            axes[1, 1].set_ylabel('Frequency')
        
        plt.tight_layout()
        plt.savefig(os.path.join(results["config"]["output_dir"], 'results_visualization.png'))
        plt.show()
        
    except ImportError:
        logger.warning("matplotlib not available, skipping visualization")
    except Exception as e:
        logger.error(f"Error in visualization: {e}")

# 主执行函数（用于测试）
def main():
    """主函数 - 用于测试代码"""
    if not IN_JUPYTER:
        print("This code is designed to run in Jupyter MCP environment")
        print("The following is a basic test of the framework:")
    
    # 创建配置
    config = ExperimentConfig(
        experiment_name="test_experiment",
        max_rounds=3,
        perturbation_probability=0.5,
        output_dir="./test_results"
    )
    
    # 运行实验
    task = "Research and analyze the impact of climate change on coastal cities"
    results = run_experiment(config, task)
    
    # 保存结果
    results_file = collect_and_save_results(results, config)
    
    if results_file:
        print(f"Experiment completed successfully!")
        print(f"Results saved to: {results_file}")
        print(f"Final result: {results['final_result']}")
        print(f"Total perturbations applied: {results['total_perturbations']}")
        
        # 尝试可视化
        if IN_JUPYTER:
            visualize_results(results_file)
    
    return results

# 如果直接运行此文件（非Jupyter环境），执行测试
if __name__ == "__main__" and not IN_JUPYTER:
    main()