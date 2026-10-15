# Jupyter MCP Environment - Multi-round Planning Agent Robustness Test
# This file contains minimal but complete runnable code blocks for robustness testing

# =============================================================================
# 1) Environment Setup and Dependency Imports
# =============================================================================
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# MCP Protocol imports (mock implementation for demonstration)
try:
    from mcp import Client, Server, Tool
    from mcp.types import Request, Response, Error
except ImportError:
    # Mock MCP implementation for standalone execution
    @dataclass
    class Tool:
        name: str
        description: str
        parameters: Dict[str, Any]
        
    @dataclass  
    class Request:
        id: str
        method: str
        params: Dict[str, Any]
        
    @dataclass
    class Response:
        id: str
        result: Any = None
        error: Optional[str] = None
        
    @dataclass
    class Error:
        code: int
        message: str
        
    class Client:
        def __init__(self):
            self.tools = {}
            
        async def call_tool(self, tool_name: str, **kwargs) -> Response:
            if tool_name not in self.tools:
                return Response(id="1", error=f"Tool {tool_name} not found")
            # Mock successful response
            return Response(id="1", result={"status": "success", "data": f"Executed {tool_name}"})
            
    class Server:
        def __init__(self):
            self.registered_tools = {}
            
        def register_tool(self, tool: Tool):
            self.registered_tools[tool.name] = tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# 2) Experiment Configuration Parameters
# =============================================================================

@dataclass
class ExperimentConfig:
    """Configuration parameters for robustness testing"""
    # Agent configuration
    max_rounds: int = 5
    timeout_per_round: float = 30.0
    retry_attempts: int = 3
    
    # Robustness test parameters
    failure_scenarios: List[str] = None
    noise_levels: List[float] = None
    perturbation_types: List[str] = None
    
    # Evaluation metrics
    success_threshold: float = 0.8
    performance_metrics: List[str] = None
    
    # Output configuration
    output_dir: str = "./results"
    save_intermediate: bool = True
    
    def __post_init__(self):
        if self.failure_scenarios is None:
            self.failure_scenarios = ["network_error", "tool_failure", "timeout", "invalid_input"]
        if self.noise_levels is None:
            self.noise_levels = [0.0, 0.1, 0.3, 0.5]
        if self.perturbation_types is None:
            self.perturbation_types = ["input_noise", "tool_unavailable", "delayed_response"]
        if self.performance_metrics is None:
            self.performance_metrics = ["success_rate", "completion_time", "tool_usage_efficiency"]

# Create default configuration
config = ExperimentConfig()

# =============================================================================
# 3) Agent Initialization and Tool Integration (MCP Protocol)
# =============================================================================

class PlanningAgent:
    """Multi-round planning agent with MCP protocol integration"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.mcp_client = Client()
        self.mcp_server = Server()
        self.tools = {}
        self.initialize_tools()
        
    def initialize_tools(self):
        """Initialize and register tools using MCP protocol"""
        # Define available tools
        tools_config = [
            Tool(
                name="web_search",
                description="Search the web for information",
                parameters={"query": "string", "max_results": "integer"}
            ),
            Tool(
                name="code_executor", 
                description="Execute code snippets",
                parameters={"code": "string", "language": "string"}
            ),
            Tool(
                name="file_manager",
                description="Read/write files",
                parameters={"operation": "string", "path": "string", "content": "string"}
            ),
            Tool(
                name="calculator",
                description="Perform mathematical calculations",
                parameters={"expression": "string"}
            )
        ]
        
        # Register tools with MCP server
        for tool in tools_config:
            self.mcp_server.register_tool(tool)
            self.tools[tool.name] = tool
            
        logger.info(f"Initialized {len(self.tools)} tools via MCP protocol")
        
    async def plan_and_execute(self, task: str, round_num: int = 0) -> Dict[str, Any]:
        """Plan and execute a task with error handling"""
        if round_num >= self.config.max_rounds:
            return {"status": "failed", "reason": "max_rounds_exceeded"}
            
        try:
            # Simple planning logic (in real implementation, this would be more sophisticated)
            plan = self._generate_plan(task)
            results = []
            
            for step in plan:
                tool_name = step["tool"]
                params = step["params"]
                
                # Add noise/perturbation based on test scenario
                if hasattr(self, 'current_noise_level') and self.current_noise_level > 0:
                    params = self._add_noise(params, self.current_noise_level)
                
                # Execute tool via MCP client
                response = await self.mcp_client.call_tool(tool_name, **params)
                
                if response.error:
                    # Handle tool failure with retry logic
                    retry_count = 0
                    while retry_count < self.config.retry_attempts:
                        logger.warning(f"Tool {tool_name} failed, retrying ({retry_count + 1}/{self.config.retry_attempts})")
                        response = await self.mcp_client.call_tool(tool_name, **params)
                        if not response.error:
                            break
                        retry_count += 1
                    
                    if response.error:
                        return {"status": "failed", "reason": f"tool_failure_{tool_name}", "error": response.error}
                
                results.append(response.result)
                
            return {"status": "success", "results": results, "rounds_used": round_num + 1}
            
        except asyncio.TimeoutError:
            return {"status": "failed", "reason": "timeout"}
        except Exception as e:
            return {"status": "failed", "reason": "unexpected_error", "error": str(e)}
    
    def _generate_plan(self, task: str) -> List[Dict[str, Any]]:
        """Generate a simple plan for the task"""
        # In a real implementation, this would use LLM or other planning algorithms
        if "calculate" in task.lower():
            return [{"tool": "calculator", "params": {"expression": task.replace("calculate", "").strip()}}]
        elif "search" in task.lower():
            return [{"tool": "web_search", "params": {"query": task.replace("search", "").strip(), "max_results": 3}}]
        else:
            # Default plan
            return [
                {"tool": "web_search", "params": {"query": task, "max_results": 2}},
                {"tool": "code_executor", "params": {"code": "print('Processing results')", "language": "python"}}
            ]
    
    def _add_noise(self, params: Dict[str, Any], noise_level: float) -> Dict[str, Any]:
        """Add noise to parameters for robustness testing"""
        noisy_params = params.copy()
        if noise_level > 0 and "query" in noisy_params:
            # Add random characters to simulate input noise
            noise_chars = "".join(np.random.choice(list("abcdefghijklmnopqrstuvwxyz"), 
                                                 int(len(noisy_params["query"]) * noise_level)))
            noisy_params["query"] += " " + noise_chars
        return noisy_params

# =============================================================================
# 4) Robustness Test Cases Implementation
# =============================================================================

class RobustnessTestSuite:
    """Comprehensive test suite for agent robustness evaluation"""
    
    def __init__(self, agent: PlanningAgent, config: ExperimentConfig):
        self.agent = agent
        self.config = config
        self.test_cases = self._generate_test_cases()
        
    def _generate_test_cases(self) -> List[Dict[str, Any]]:
        """Generate test cases covering different scenarios"""
        base_tasks = [
            "Calculate 2 + 2 * 3",
            "Search for latest AI research papers",
            "Write a Python function to sort a list",
            "Find information about climate change"
        ]
        
        test_cases = []
        for task in base_tasks:
            # Normal case
            test_cases.append({
                "task": task,
                "scenario": "normal",
                "noise_level": 0.0,
                "expected_success": True
            })
            
            # Noise injection cases
            for noise_level in self.config.noise_levels[1:]:  # Skip 0.0 (already covered)
                test_cases.append({
                    "task": task,
                    "scenario": "input_noise",
                    "noise_level": noise_level,
                    "expected_success": noise_level < 0.3  # Expect failure at high noise
                })
                
            # Tool failure simulation
            test_cases.append({
                "task": task,
                "scenario": "tool_unavailable", 
                "noise_level": 0.0,
                "expected_success": False,
                "unavailable_tool": "web_search" if "search" in task.lower() else "calculator"
            })
            
        return test_cases
    
    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single robustness test case"""
        start_time = datetime.now()
        
        # Set up test conditions
        if test_case["scenario"] == "tool_unavailable":
            # Temporarily remove tool to simulate unavailability
            unavailable_tool = test_case.get("unavailable_tool", "web_search")
            original_tool = self.agent.tools.pop(unavailable_tool, None)
            
        # Set noise level for agent
        self.agent.current_noise_level = test_case["noise_level"]
        
        try:
            # Execute the task
            result = await self.agent.plan_and_execute(test_case["task"])
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Evaluate result
            success = result["status"] == "success"
            expected_success = test_case["expected_success"]
            
            test_result = {
                "task": test_case["task"],
                "scenario": test_case["scenario"],
                "noise_level": test_case["noise_level"],
                "success": success,
                "expected_success": expected_success,
                "execution_time": execution_time,
                "result_details": result
            }
            
            return test_result
            
        finally:
            # Restore original state
            if test_case["scenario"] == "tool_unavailable":
                if original_tool:
                    self.agent.tools[test_case["unavailable_tool"]] = original_tool
            self.agent.current_noise_level = 0.0
    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all test cases and collect results"""
        results = []
        for i, test_case in enumerate(self.test_cases):
            logger.info(f"Running test {i+1}/{len(self.test_cases)}: {test_case['task'][:50]}...")
            result = await self.run_single_test(test_case)
            results.append(result)
            
            # Save intermediate results if configured
            if self.config.save_intermediate:
                self._save_intermediate_results(results, f"intermediate_results_{i}.json")
                
        return results
    
    def _save_intermediate_results(self, results: List[Dict[str, Any]], filename: str):
        """Save intermediate test results"""
        os.makedirs(self.config.output_dir, exist_ok=True)
        filepath = os.path.join(self.config.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

# =============================================================================
# 5) Experiment Execution and Data Collection
# =============================================================================

async def run_experiment() -> Dict[str, Any]:
    """Main experiment execution function"""
    # Initialize components
    agent = PlanningAgent(config)
    test_suite = RobustnessTestSuite(agent, config)
    
    logger.info("Starting robustness testing experiment...")
    logger.info(f"Configuration: {config}")
    logger.info(f"Total test cases: {len(test_suite.test_cases)}")
    
    # Run all tests
    start_time = datetime.now()
    results = await test_suite.run_all_tests()
    end_time = datetime.now()
    
    # Calculate experiment metrics
    total_time = (end_time - start_time).total_seconds()
    success_count = sum(1 for r in results if r["success"])
    expected_success_count = sum(1 for r in results if r["expected_success"])
    accuracy = success_count / len(results) if results else 0
    
    experiment_data = {
        "config": config.__dict__,
        "results": results,
        "summary": {
            "total_tests": len(results),
            "successful_tests": success_count,
            "expected_successful_tests": expected_success_count,
            "accuracy": accuracy,
            "total_execution_time": total_time,
            "average_execution_time": total_time / len(results) if results else 0
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Save final results
    os.makedirs(config.output_dir, exist_ok=True)
    final_results_path = os.path.join(config.output_dir, "final_results.json")
    with open(final_results_path, 'w') as f:
        json.dump(experiment_data, f, indent=2, default=str)
    
    logger.info(f"Experiment completed in {total_time:.2f} seconds")
    logger.info(f"Success rate: {accuracy:.2%} ({success_count}/{len(results)})")
    logger.info(f"Results saved to: {final_results_path}")
    
    return experiment_data

# =============================================================================
# 6) Results Analysis and Visualization
# =============================================================================

def analyze_results(experiment_data: Dict[str, Any]):
    """Analyze and visualize experiment results"""
    results = experiment_data["results"]
    summary = experiment_data["summary"]
    
    # Create output directory for plots
    plot_dir = os.path.join(config.output_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Multi-round Planning Agent Robustness Test Results', fontsize=16)
    
    # 1. Success Rate by Scenario
    scenarios = {}
    for result in results:
        scenario = result["scenario"]
        if scenario not in scenarios:
            scenarios[scenario] = {"success": 0, "total": 0}
        scenarios[scenario]["total"] += 1
        if result["success"]:
            scenarios[scenario]["success"] += 1
    
    scenario_names = list(scenarios.keys())
    success_rates = [scenarios[s]["success"] / scenarios[s]["total"] for s in scenario_names]
    
    axes[0, 0].bar(scenario_names, success_rates, color='skyblue')
    axes[0, 0].set_title('Success Rate by Scenario')
    axes[0, 0].set_ylabel('Success Rate')
    axes[0, 0].set_ylim(0, 1)
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. Success Rate vs Noise Level
    noise_levels = sorted(set(r["noise_level"] for r in results))
    noise_success_rates = []
    for noise in noise_levels:
        noise_results = [r for r in results if r["noise_level"] == noise]
        if noise_results:
            success_rate = sum(1 for r in noise_results if r["success"]) / len(noise_results)
            noise_success_rates.append(success_rate)
        else:
            noise_success_rates.append(0)
    
    axes[0, 1].plot(noise_levels, noise_success_rates, marker='o', linewidth=2, markersize=8)
    axes[0, 1].set_title('Success Rate vs Input Noise Level')
    axes[0, 1].set_xlabel('Noise Level')
    axes[0, 1].set_ylabel('Success Rate')
    axes[0, 1].set_ylim(0, 1)
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Execution Time Distribution
    execution_times = [r["execution_time"] for r in results]
    axes[1, 0].hist(execution_times, bins=10, alpha=0.7, color='lightgreen')
    axes[1, 0].set_title('Execution Time Distribution')
    axes[1, 0].set_xlabel('Execution Time (seconds)')
    axes[1, 0].set_ylabel('Frequency')
    
    # 4. Overall Performance Summary
    axes[1, 1].axis('off')
    summary_text = f"""
    Experiment Summary:
    
    Total Tests: {summary['total_tests']}
    Successful Tests: {summary['successful_tests']}
    Success Rate: {summary['accuracy']:.2%}
    Avg Execution Time: {summary['average_execution_time']:.2f}s
    Total Time: {summary['total_execution_time']:.2f}s
    
    Configuration:
    Max Rounds: {config.max_rounds}
    Retry Attempts: {config.retry_attempts}
    Noise Levels Tested: {config.noise_levels}
    """
    axes[1, 1].text(0.1, 0.9, summary_text, transform=axes[1, 1].transAxes, 
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
    
    plt.tight_layout()
    plot_path = os.path.join(plot_dir, "robustness_analysis.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Analysis plots saved to: {plot_path}")
    
    # Print detailed analysis
    print("\n" + "="*60)
    print("ROBUSTNESS TEST ANALYSIS RESULTS")
    print("="*60)
    print(f"Overall Success Rate: {summary['accuracy']:.2%}")
    print(f"Average Execution Time: {summary['average_execution_time']:.2f} seconds")
    print("\nSuccess Rate by Scenario:")
    for scenario, stats in scenarios.items():
        rate = stats["success"] / stats["total"]
        print(f"  {scenario}: {rate:.2%} ({stats['success']}/{stats['total']})")
    print(f"\nDetailed results saved to: {os.path.join(config.output_dir, 'final_results.json')}")
    print(f"Visualization saved to: {plot_path}")

# =============================================================================
# Main Execution Entry Point
# =============================================================================

async def main():
    """Main entry point for the robustness testing experiment"""
    try:
        # Run the experiment
        experiment_data = await run_experiment()
        
        # Analyze results
        analyze_results(experiment_data)
        
        logger.info("Robustness testing experiment completed successfully!")
        
    except Exception as e:
        logger.error(f"Experiment failed with error: {e}")
        raise

# For Jupyter notebook usage, you can call:
# await main()

if __name__ == "__main__":
    # For standalone script execution
    asyncio.run(main())