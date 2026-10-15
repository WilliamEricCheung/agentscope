#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 3: Tool Simulator
========================
工具模拟器设置，模拟各种可用工具的行为和响应。
"""

import json
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ToolResponse:
    """工具响应数据类"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ToolSimulator:
    """工具模拟器类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化工具模拟器"""
        self.config = config or {}
        self.tools = {
            "write_text_file": self._simulate_write_text_file,
            "insert_text_file": self._simulate_insert_text_file,
            "view_text_file": self._simulate_view_text_file,
            "reset_equipped_tools": self._simulate_reset_equipped_tools,
            "generate_response": self._simulate_generate_response,
            "browser_click": self._simulate_browser_click,
            "browser_evaluate": self._simulate_browser_evaluate,
            "browser_close": self._simulate_browser_close
        }
        self.file_system = {}  # 模拟文件系统
        
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """执行指定工具"""
        if tool_name not in self.tools:
            return ToolResponse(
                success=False,
                message=f"Tool '{tool_name}' not found",
                error="ToolNotFound"
            )
        
        try:
            return self.tools[tool_name](**kwargs)
        except Exception as e:
            return ToolResponse(
                success=False,
                message=f"Error executing tool '{tool_name}': {str(e)}",
                error=str(e)
            )
    
    def _simulate_write_text_file(self, file_path: str, content: str, ranges: List[int] = None) -> ToolResponse:
        """模拟写入文本文件"""
        try:
            if ranges is None:
                self.file_system[file_path] = content
            else:
                # 模拟范围写入
                existing_content = self.file_system.get(file_path, "")
                lines = existing_content.split('\n') if existing_content else []
                
                start, end = ranges[0] - 1, ranges[1]
                new_lines = content.split('\n')
                
                # 确保列表足够长
                while len(lines) < end:
                    lines.append("")
                
                # 替换指定范围
                lines[start:end] = new_lines
                
                self.file_system[file_path] = '\n'.join(lines)
            
            return ToolResponse(
                success=True,
                message=f"Successfully wrote to {file_path}",
                data={"file_path": file_path, "content_length": len(content)}
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                message=f"Failed to write to {file_path}: {str(e)}",
                error=str(e)
            )
    
    def _simulate_insert_text_file(self, file_path: str, content: str, line_number: int) -> ToolResponse:
        """模拟插入文本文件"""
        try:
            existing_content = self.file_system.get(file_path, "")
            lines = existing_content.split('\n') if existing_content else []
            
            # 确保行号有效
            if line_number > len(lines) + 1:
                line_number = len(lines) + 1
            
            lines.insert(line_number - 1, content)
            self.file_system[file_path] = '\n'.join(lines)
            
            return ToolResponse(
                success=True,
                message=f"Successfully inserted at line {line_number} in {file_path}",
                data={"file_path": file_path, "line_number": line_number}
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                message=f"Failed to insert in {file_path}: {str(e)}",
                error=str(e)
            )
    
    def _simulate_view_text_file(self, file_path: str, ranges: List[int] = None) -> ToolResponse:
        """模拟查看文本文件"""
        try:
            if file_path not in self.file_system:
                return ToolResponse(
                    success=False,
                    message=f"File {file_path} not found",
                    error="FileNotFound"
                )
            
            content = self.file_system[file_path]
            lines = content.split('\n')
            
            if ranges is None:
                displayed_content = content
            else:
                start, end = ranges[0] - 1, ranges[1]
                if start < 0:
                    start = len(lines) + start
                if end < 0:
                    end = len(lines) + end + 1
                displayed_lines = lines[start:end]
                displayed_content = '\n'.join(displayed_lines)
            
            return ToolResponse(
                success=True,
                message=f"Successfully read {file_path}",
                data={"file_path": file_path, "content": displayed_content}
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                message=f"Failed to read {file_path}: {str(e)}",
                error=str(e)
            )
    
    def _simulate_reset_equipped_tools(self, browser_tools: bool = False) -> ToolResponse:
        """模拟重置装备工具"""
        try:
            active_tools = []
            if browser_tools:
                active_tools.extend(["browser_click", "browser_evaluate", "browser_close"])
            
            # 添加基本工具
            active_tools.extend([
                "write_text_file", "insert_text_file", "view_text_file",
                "reset_equipped_tools", "generate_response"
            ])
            
            return ToolResponse(
                success=True,
                message=f"Successfully reset tools. Active tools: {active_tools}",
                data={"active_tools": active_tools, "browser_tools_enabled": browser_tools}
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                message=f"Failed to reset tools: {str(e)}",
                error=str(e)
            )
    
    def _simulate_generate_response(self, success: bool, message: str) -> ToolResponse:
        """模拟生成响应"""
        return ToolResponse(
            success=success,
            message=message,
            data={"final_response": {"success": success, "message": message}}
        )
    
    def _simulate_browser_click(self, element: str) -> ToolResponse:
        """模拟浏览器点击"""
        return ToolResponse(
            success=True,
            message=f"Successfully clicked on element: {element}",
            data={"element": element, "action": "click"}
        )
    
    def _simulate_browser_evaluate(self, script: str) -> ToolResponse:
        """模拟浏览器脚本执行"""
        # 简单模拟返回一些数据
        result = f"Executed script: {script[:50]}..."
        return ToolResponse(
            success=True,
            message="Script executed successfully",
            data={"script": script, "result": result}
        )
    
    def _simulate_browser_close(self) -> ToolResponse:
        """模拟关闭浏览器"""
        return ToolResponse(
            success=True,
            message="Browser closed successfully",
            data={"action": "close"}
        )

# 测试工具模拟器
if __name__ == "__main__":
    simulator = ToolSimulator()
    
    # 测试基本文件操作
    response1 = simulator.execute_tool("write_text_file", file_path="test.txt", content="Hello, World!")
    print(f"Write response: {response1}")
    
    response2 = simulator.execute_tool("view_text_file", file_path="test.txt")
    print(f"Read response: {response2}")
    
    response3 = simulator.execute_tool("insert_text_file", file_path="test.txt", content="Inserted line", line_number=2)
    print(f"Insert response: {response3}")
    
    response4 = simulator.execute_tool("reset_equipped_tools", browser_tools=True)
    print(f"Reset tools response: {response4}")