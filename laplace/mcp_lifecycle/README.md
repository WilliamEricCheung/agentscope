# Laplace Runtime Notes

本目录用于存放与运行期能力相关的辅助文件。当前已经接入了 **AgentScope MCP lifecycle daemon**，用于在 Agent 进程结束后继续管理本地 Docker MCP 容器。

## 1. 状态文件默认位置

守护进程默认会把状态写到：

- `laplace/mcp_lifecycle/*.json`：每个 MCP 容器对应一个状态文件
- `laplace/mcp_lifecycle/daemon.pid`：当前后台 daemon 的 PID 文件

这些状态文件记录的信息包括：

- `container_name`
- `last_used_at`
- `stop_after_seconds`
- `remove_after_seconds`
- `in_use`
- `bound_clients`
- `owner_pids`

其中 `owner_pids` 用于判断某个 Agent 进程是否已经异常退出；如果退出了，daemon 会回收陈旧的 `in_use` 状态，随后继续按空闲时间规则停止或删除容器。

## 2. 自动运行方式

当代码调用本地 Docker MCP ensure helper（例如 `_ensure_local_docker_mcp_server(...)`）时，会自动触发：

1. 确保 MCP 容器已启动或恢复；
2. 更新 `laplace/mcp_lifecycle/` 下的状态文件；
3. 如果后台 daemon 尚未运行，则自动以 detached 模式启动：

```bash
python -m agentscope.mcp._mcp_daemon
```

这样即使主 Agent 被 `Ctrl+C` 或异常终止，daemon 仍会继续轮询并处理容器生命周期。

## 3. 手动运行方式

### 持续运行

```bash
python -m agentscope.mcp._mcp_daemon
```

### 只执行一次扫描

```bash
python -m agentscope.mcp._mcp_daemon --once
```

### 自定义轮询间隔

```bash
python -m agentscope.mcp._mcp_daemon --poll-interval 10
```

## 4. 空闲处理规则

daemon 会周期性检查状态文件与 Docker 容器状态：

- 达到 `MCP_CONTAINER_IDLE_STOP_SECONDS` 后：执行 `docker stop`
- 达到 `MCP_CONTAINER_IDLE_REMOVE_SECONDS` 后：执行 `docker rm -f`

默认值目前为：

- `stop`: 2 分钟
- `remove`: 5 分钟

## 5. 常用环境变量

### 修改状态目录

```bash
AGENTSCOPE_MCP_LIFECYCLE_DIR=/your/custom/path
```

### 禁用自动 daemon 拉起

```bash
AGENTSCOPE_MCP_DAEMON_ENABLED=false
```

### 调整空闲停止/删除阈值

```bash
MCP_CONTAINER_IDLE_STOP_SECONDS=120
MCP_CONTAINER_IDLE_REMOVE_SECONDS=300
```

## 6. 适用场景

这个 daemon 主要解决以下问题：

- Agent 进程退出后，MCP 容器仍然遗留在后台；
- 需要把容器生命周期管理与单次对话/任务进程解耦；
- 需要保留一个可观测、可检查的 repo-local 状态目录。
