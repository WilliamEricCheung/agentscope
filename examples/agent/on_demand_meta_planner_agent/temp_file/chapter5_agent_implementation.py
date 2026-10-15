#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 5: Agent Implementation
==============================
Agent实现，包含核心逻辑和决策流程。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

# 导入必要的模块（在实际环境中会被正确导入）
try:
    from chapter3_tool_simulator import ToolSimulator, ToolResponse
    from chapter2_experiment_config import ExperimentConfig
except ImportError:
    # 如果无法导入，使用本地定义
    pass

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Agent状态数据类"""
    current_step: int = 0
    max_steps: int = 50
    active_tools: List[str] = None
    file_system: Dict[str, str] = None
    memory: Dict[str, Any] = None
    success: bool = False
    final_message: str = ""
    
    def __post_init__(self):
        if self.active_tools is None:
            self.active_tools = [
                "write_text_file", "insert_text_file", "view_text_file",
                "reset_equipped_tools", "generate_response"
            ]
        if self.file_system is None:
            self.file_system = {}
        if self.memory is None:
            self.memory = {}

class MCPAgent:
    """MCP Agent实现"""
    
    def __init__(self, config: ExperimentConfig = None):
        """初始化Agent"""
        self.config = config or ExperimentConfig()
        self.simulator = ToolSimulator()
        self.state = AgentState(max_steps=self.config.max_steps)
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def process_task(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """处理给定任务"""
        self.logger.info(f"Processing task: {task_description}")
        self.state.current_step = 0
        self.state.success = False
        self.state.final_message = ""
        
        # 分析任务类型并选择策略
        task_type = scenario.get("task_type", "unknown")
        strategy = self._select_strategy(task_type)
        
        try:
            # 执行策略
            result = self._execute_strategy(strategy, task_description, scenario)
            self.state.success = result.success
            self.state.final_message = result.message
            
            # 生成最终响应
            final_response = self._generate_final_response(result)
            return final_response
            
        except Exception as e:
            error_msg = f"Error processing task: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(success=False, message=error_msg, error=str(e))
    
    def _select_strategy(self, task_type: str) -> str:
        """根据任务类型选择策略"""
        strategy_map = {
            "file_operation": "file_strategy",
            "web_browsing": "web_strategy",
            "tool_activation": "tool_strategy",
            "multi_step_reasoning": "reasoning_strategy",
            "error_handling": "error_strategy"
        }
        return strategy_map.get(task_type, "default_strategy")
    
    def _execute_strategy(self, strategy: str, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行选定的策略"""
        if strategy == "file_strategy":
            return self._execute_file_strategy(task_description, scenario)
        elif strategy == "web_strategy":
            return self._execute_web_strategy(task_description, scenario)
        elif strategy == "tool_strategy":
            return self._execute_tool_strategy(task_description, scenario)
        elif strategy == "reasoning_strategy":
            return self._execute_reasoning_strategy(task_description, scenario)
        elif strategy == "error_strategy":
            return self._execute_error_strategy(task_description, scenario)
        else:
            return self._execute_default_strategy(task_description, scenario)
    
    def _execute_file_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行文件操作策略"""
        steps = scenario.get("steps", [])
        
        # 步骤1: 创建文件
        if len(steps) > 0:
            file_path = "output.txt"
            content = f"# {task_description}\nInitial content for testing."
            response = self.simulator.execute_tool("write_text_file", file_path=file_path, content=content)
            if not response.success:
                return response
        
        # 步骤2: 读取文件
        if len(steps) > 1:
            response = self.simulator.execute_tool("view_text_file", file_path=file_path)
            if not response.success:
                return response
        
        # 步骤3: 插入内容
        if len(steps) > 2:
            insert_content = "This line was inserted during the experiment."
            response = self.simulator.execute_tool("insert_text_file", file_path=file_path, content=insert_content, line_number=2)
            if not response.success:
                return response
        
        # 步骤4: 验证最终内容
        if len(steps) > 3:
            response = self.simulator.execute_tool("view_text_file", file_path=file_path)
            if response.success:
                return ToolResponse(success=True, message="File operations completed successfully", data=response.data)
        
        return ToolResponse(success=True, message="File strategy executed successfully")
    
    def _execute_web_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行Web浏览策略"""
        # 激活浏览器工具
        response = self.simulator.execute_tool("reset_equipped_tools", browser_tools=True)
        if not response.success:
            return response
        
        # 模拟点击操作
        response = self.simulator.execute_tool("browser_click", element="search_button")
        if not response.success:
            return response
        
        # 模拟脚本执行
        response = self.simulator.execute_tool("browser_evaluate", script="document.title")
        if not response.success:
            return response
        
        return ToolResponse(success=True, message="Web browsing strategy executed successfully", data=response.data)
    
    def _execute_tool_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行工具激活策略"""
        # 初始状态只有基本工具
        basic_response = self.simulator.execute_tool("reset_equipped_tools", browser_tools=False)
        if not basic_response.success:
            return basic_response
        
        # 根据需要激活浏览器工具
        web_response = self.simulator.execute_tool("reset_equipped_tools", browser_tools=True)
        if not web_response.success:
            return web_response
        
        # 执行一些操作后停用浏览器工具
        final_response = self.simulator.execute_tool("reset_equipped_tools", browser_tools=False)
        if not final_response.success:
            return final_response
        
        return ToolResponse(success=True, message="Tool activation strategy executed successfully")
    
    def _execute_reasoning_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行多步推理策略"""
        # 分析问题
        analysis = f"Analyzing task: {task_description}"
        self.simulator.execute_tool("write_text_file", file_path="analysis.txt", content=analysis)
        
        # 制定计划
        plan = "Step 1: Analyze\nStep 2: Plan\nStep 3: Execute\nStep 4: Verify"
        self.simulator.execute_tool("write_text_file", file_path="plan.txt", content=plan)
        
        # 执行步骤
        execution = "Executing planned steps..."
        self.simulator.execute_tool("write_text_file", file_path="execution.txt", content=execution)
        
        # 生成答案
        answer = f"Final answer for: {task_description}"
        self.simulator.execute_tool("write_text_file", file_path="answer.txt", content=answer)
        
        return ToolResponse(success=True, message="Reasoning strategy executed successfully", data={"answer": answer})
    
    def _execute_error_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行错误处理策略"""
        # 尝试可能失败的操作
        response = self.simulator.execute_tool("view_text_file", file_path="nonexistent.txt")
        
        # 处理错误
        if not response.success:
            error_handling = f"Handled error: {response.error}. Creating fallback file."
            self.simulator.execute_tool("write_text_file", file_path="fallback.txt", content=error_handling)
            return ToolResponse(success=True, message="Error handled successfully", data={"error_handled": True})
        
        return ToolResponse(success=True, message="No errors to handle")
    
    def _execute_default_strategy(self, task_description: str, scenario: Dict[str, Any]) -> ToolResponse:
        """执行默认策略"""
        # 简单的文件写入操作
        content = f"Default strategy for task: {task_description}"
        response = self.simulator.execute_tool("write_text_file", file_path="default_output.txt", content=content)
        return response
    
    def _generate_final_response(self, result: ToolResponse) -> ToolResponse:
        """生成最终响应"""
        final_response = self.simulator.execute_tool(
            "generate_response",
            success=result.success,
            message=result.message if result.success else f"Task failed: {result.error or result.message}"
        )
        return final_response

# 测试Agent实现
if __name__ == "__main__":
    # 创建配置
    config = ExperimentConfig()
    
    # 创建Agent
    agent = MCPAgent(config)
    
    # 创建测试场景
    test_scenario = {
        "scenario_id": "test_001",
        "task_type": "file_operation",
        "complexity": "simple",
        "steps": ["Create file", "Read file", "Insert content", "Verify"],
        "success_criteria": "All operations successful"
    }
    
    # 执行任务
    result = agent.process_task("Test file operations", test_scenario)
    
    print(f"Task result: {result.success}")
    print(f"Message: {result.message}")
    if result.data:
        print(f"Data: {result.data}")