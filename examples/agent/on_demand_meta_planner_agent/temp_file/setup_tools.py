#!/usr/bin/env python3
"""
多轮规划代理工具环境设置脚本
"""

import argparse
import json
import os
import sys
from pathlib import Path

def create_tool_environment(config_file, output_dir):
    """创建工具环境"""
    # 读取配置文件
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 创建工具模拟器目录
    tools_dir = output_path / "tools"
    tools_dir.mkdir(exist_ok=True)
    
    # 创建基础工具文件
    base_tool_template = '''
"""
{tool_name} 工具模拟器
"""
import random
import time
from typing import Dict, Any, Optional

class {tool_class_name}:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.success_rate = config.get("success_rate", 0.95)
        self.failure_modes = config.get("failure_modes", [])
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具操作"""
        # 模拟处理时间
        if "processing_time" in self.config:
            time.sleep(self.config["processing_time"])
        
        # 检查是否应该失败
        if random.random() > self.success_rate:
            if self.failure_modes:
                failure_mode = random.choice(self.failure_modes)
                return {{
                    "success": False,
                    "error": f"Simulated {failure_mode} error",
                    "error_type": failure_mode
                }}
            else:
                return {{
                    "success": False,
                    "error": "Unknown error",
                    "error_type": "unknown"
                }}
        
        # 成功执行
        return {{
            "success": True,
            "result": self._generate_result(parameters)
        }}
    
    def _generate_result(self, parameters: Dict[str, Any]) -> Any:
        """生成模拟结果 - 子类需要实现"""
        raise NotImplementedError()

'''
    
    # 为每个工具生成文件
    for tool_name, tool_config in config.get("tools", {}).items():
        tool_class_name = "".join(word.capitalize() for word in tool_name.split("_"))
        tool_content = base_tool_template.format(
            tool_name=tool_name,
            tool_class_name=tool_class_name
        )
        
        # 添加具体的工具实现
        if tool_name == "web_search":
            tool_content += '''
    def _generate_result(self, parameters: Dict[str, Any]) -> Any:
        """生成搜索结果"""
        query = parameters.get("query", "")
        num_results = parameters.get("num_results", 5)
        
        # 模拟搜索结果
        results = []
        for i in range(num_results):
            results.append({
                "title": f"Result {i+1} for '{query}'",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a simulated snippet for result {i+1} about {query}"
            })
        
        return {
            "results": results,
            "total_results": num_results * 10,  # 模拟总结果数
            "search_time": 0.123  # 模拟搜索时间
        }
'''
        elif tool_name == "file_system":
            tool_content += '''
    def _generate_result(self, parameters: Dict[str, Any]) -> Any:
        """生成文件系统操作结果"""
        operation = parameters.get("operation", "read")
        path = parameters.get("path", "/tmp/test.txt")
        content = parameters.get("content", "")
        
        if operation == "read":
            return {
                "content": f"Simulated content of {path}",
                "size": len(f"Simulated content of {path}"),
                "last_modified": "2023-12-01T12:00:00Z"
            }
        elif operation == "write":
            return {
                "success": True,
                "bytes_written": len(content),
                "path": path
            }
        elif operation == "list":
            return {
                "files": [f"file_{i}.txt" for i in range(5)],
                "directories": ["subdir1", "subdir2"]
            }
        else:
            return {"error": f"Unsupported operation: {operation}"}
'''
        elif tool_name == "api_call":
            tool_content += '''
    def _generate_result(self, parameters: Dict[str, Any]) -> Any:
        """生成API调用结果"""
        endpoint = parameters.get("endpoint", "/api/test")
        method = parameters.get("method", "GET")
        data = parameters.get("data", {})
        
        # 模拟不同的API响应
        if "user" in endpoint:
            return {
                "id": 123,
                "name": "Test User",
                "email": "test@example.com",
                "created_at": "2023-12-01T12:00:00Z"
            }
        elif "product" in endpoint:
            return {
                "id": 456,
                "name": "Test Product",
                "price": 29.99,
                "in_stock": True
            }
        else:
            return {
                "message": f"Success for {method} {endpoint}",
                "data": data,
                "timestamp": "2023-12-01T12:00:00Z"
            }
'''
        else:
            # 默认通用实现
            tool_content += '''
    def _generate_result(self, parameters: Dict[str, Any]) -> Any:
        """生成通用结果"""
        return {
            "parameters": parameters,
            "status": "success",
            "timestamp": "2023-12-01T12:00:00Z"
        }
'''
        
        # 写入工具文件
        tool_file = tools_dir / f"{tool_name}.py"
        with open(tool_file, 'w') as f:
            f.write(tool_content)
    
    # 创建主工具管理器
    manager_content = '''
"""
工具管理器 - 统一接口访问所有工具
"""
import importlib
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ToolManager:
    def __init__(self, config_file: str, tools_dir: str):
        self.config_file = config_file
        self.tools_dir = Path(tools_dir)
        self.tools = {}
        self._load_config()
        self._load_tools()
    
    def _load_config(self):
        """加载工具配置"""
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
    
    def _load_tools(self):
        """动态加载工具模块"""
        for tool_name in self.config.get("tools", {}).keys():
            try:
                module_name = f"tools.{tool_name}"
                spec = importlib.util.spec_from_file_location(
                    module_name, 
                    self.tools_dir / f"{tool_name}.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 获取工具类名
                tool_class_name = "".join(word.capitalize() for word in tool_name.split("_"))
                tool_class = getattr(module, tool_class_name)
                
                # 创建工具实例
                self.tools[tool_name] = tool_class(self.config["tools"][tool_name])
                
            except Exception as e:
                print(f"Failed to load tool {tool_name}: {e}")
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定工具"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool {tool_name} not found",
                "error_type": "tool_not_found"
            }
        
        try:
            return self.tools[tool_name].execute(parameters)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution_error"
            }

'''
    
    manager_file = output_path / "tool_manager.py"
    with open(manager_file, 'w') as f:
        f.write(manager_content)
    
    # 创建示例配置文件
    example_config = {
        "tools": {
            "web_search": {
                "description": "执行网络搜索",
                "parameters": {"query": "string", "num_results": "integer"},
                "failure_modes": ["rate_limit", "timeout", "invalid_query"],
                "success_rate": 0.95,
                "processing_time": 0.1
            },
            "file_system": {
                "description": "文件系统操作",
                "parameters": {"operation": "string", "path": "string", "content": "string"},
                "failure_modes": ["permission_denied", "disk_full", "file_not_found"],
                "success_rate": 0.98
            },
            "api_call": {
                "description": "调用外部API",
                "parameters": {"endpoint": "string", "method": "string", "data": "object"},
                "failure_modes": ["network_error", "auth_failure", "rate_limit"],
                "success_rate": 0.90
            }
        }
    }
    
    example_config_file = output_path / "example_config.json"
    with open(example_config_file, 'w') as f:
        json.dump(example_config, f, indent=2)
    
    print(f"工具环境已创建在: {output_path}")
    print(f"工具目录: {tools_dir}")
    print(f"配置示例: {example_config_file}")

def main():
    parser = argparse.ArgumentParser(description="设置多轮规划代理工具环境")
    parser.add_argument("--config", default="tools_config.json", help="工具配置文件路径")
    parser.add_argument("--output", default="tool_env", help="输出目录")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"配置文件 {args.config} 不存在，将使用默认配置")
        # 创建默认配置
        default_config = {
            "tools": {
                "web_search": {
                    "description": "执行网络搜索",
                    "parameters": {"query": "string", "num_results": "integer"},
                    "failure_modes": ["rate_limit", "timeout", "invalid_query"],
                    "success_rate": 0.95
                }
            }
        }
        with open(args.config, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    create_tool_environment(args.config, args.output)

if __name__ == "__main__":
    main()