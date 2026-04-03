from fastmcp import FastMCP, Context
import asyncio
import fastmcp.utilities.logging as logging

logger = logging.get_logger("My MCP Server")

mcp = FastMCP("My MCP Server")

@mcp.tool
async def greet(name: str, ctx: Context) -> str:
    # server向client发送日志信息，告知正在执行复杂操作
    await ctx.info(f"mock sleep 2s to simulate complex operation")
    logger.info(f"Received request to greet {name}, simulating complex operation for 2s...")
    # 模拟复杂操作，等待2s再返回
    await asyncio.sleep(2)
    return f"Hello, {name}!"


if __name__ == "__main__":
    # 按照Streamable HTTP方式管理Server，来实现预热，池化，数据交换等功能
    mcp.run(transport="http", host="0.0.0.0", port=8080)