# 可复现的多轮规划代理稳健性实验环境设计

## 1. 技术选型理由

### 1.1 NixOS vs Docker 对比分析

**NixOS 优势：**
- **完全可重现性**：Nix 的纯函数式包管理确保相同的输入（Nix 表达式）总是产生相同的输出（构建结果）
- **原子升级和回滚**：实验环境可以轻松回滚到之前的版本
- **依赖隔离**：每个包及其依赖都被存储在独立的路径中，避免依赖冲突
- **声明式配置**：整个系统状态通过声明式配置文件定义

**Docker 优势：**
- **广泛采用**：社区支持丰富，文档完善
- **跨平台兼容性**：在任何支持 Docker 的系统上运行一致
- **轻量级虚拟化**：相比完整虚拟机更高效
- **分层镜像**：便于缓存和复用基础环境

**推荐方案：混合使用**
- **主要环境**：使用 Nix flakes 定义核心实验环境
- **部署和共享**：提供 Docker 镜像作为备选方案
- **理由**：Nix 提供更强的可重现保证，而 Docker 提供更好的可访问性

### 1.2 多轮规划代理研究背景

多轮规划代理（Multi-turn Planning Agents）是指能够在多个交互回合中进行规划和决策的智能体。其稳健性研究通常涉及：
- 对抗性输入的鲁棒性
- 环境动态变化的适应性  
- 长期规划的一致性维护
- 不确定性下的决策质量

## 2. 依赖管理策略

### 2.1 Python 依赖管理

```nix
# flake.nix - Python 依赖定义
{
  description = "Multi-turn Planning Agents Robustness Experiment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python310;
        pythonPackages = python.pkgs;
      in
      {
        packages.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPackages.pip
            pythonPackages.setuptools
            # ML/DL 框架
            pythonPackages.torch
            pythonPackages.transformers
            pythonPackages.langchain
            # 实验管理
            pythonPackages.mlflow
            pythonPackages.wandb
            # 测试和验证
            pythonPackages.pytest
            pythonPackages.hypothesis
            # 数据处理
            pythonPackages.pandas
            pythonPackages.numpy
            pythonPackages.scikit-learn
          ];
          
          # 环境变量
          MLFLOW_TRACKING_URI = "file://${toString ./mlruns}";
          PYTHONPATH = "$PYTHONPATH:${toString ./.}";
        };
      });
}
```

### 2.2 版本锁定策略

- **Nix 表达式哈希**：固定 nixpkgs commit hash 确保包版本一致性
- **Python requirements**：使用 `poetry.lock` 或 `requirements.txt` 与 Nix 结合
- **数据集版本**：使用 DVC (Data Version Control) 管理数据集版本

## 3. 环境隔离方法

### 3.1 Nix Shell 环境

```bash
# 创建隔离的开发环境
nix develop

# 在隔离环境中运行实验
nix run .#experiment -- --config configs/robustness_test.yaml
```

### 3.2 Docker 镜像构建

```dockerfile
# Dockerfile
FROM nixos/nix:2.18.1

# 复制 Nix flake 到容器
COPY . /workspace
WORKDIR /workspace

# 构建环境并设置入口点
RUN nix build && nix develop --command which python > /tmp/python-path
ENV PYTHON_PATH=$(cat /tmp/python-path)

ENTRYPOINT ["nix", "develop", "--command"]
CMD ["python", "main.py"]
```

### 3.3 多环境配置管理

```yaml
# configs/environments.yaml
environments:
  development:
    seed: 42
    debug: true
    logging_level: DEBUG
    
  testing:
    seed: 12345
    debug: false
    logging_level: INFO
    test_mode: true
    
  production:
    seed: null  # 随机种子
    debug: false
    logging_level: WARNING
    distributed: true
```

## 4. 详细的复现步骤

### 4.1 前提条件

- 安装 Nix (推荐使用 flakes 支持)
- 或安装 Docker (版本 >= 20.10)

### 4.2 使用 Nix 复现实验

```bash
# 1. 克隆实验仓库
git clone <repository-url>
cd multi-turn-planning-robustness

# 2. 进入 Nix 开发环境
nix develop

# 3. 下载数据集（如果需要）
python scripts/download_datasets.py

# 4. 运行基准实验
python experiments/baseline.py --config configs/baseline.yaml

# 5. 运行稳健性测试
python experiments/robustness_test.py --config configs/robustness_test.yaml

# 6. 生成结果报告
python scripts/generate_report.py --output results/report.pdf
```

### 4.3 使用 Docker 复现实验

```bash
# 1. 构建 Docker 镜像
docker build -t planning-robustness .

# 2. 运行基准实验
docker run --rm -v $(pwd)/results:/workspace/results \
  planning-robustness python experiments/baseline.py \
  --config configs/baseline.yaml

# 3. 运行稳健性测试
docker run --rm -v $(pwd)/results:/workspace/results \
  planning-robustness python experiments/robustness_test.py \
  --config configs/robustness_test.yaml
```

### 4.4 验证复现性

```bash
# 验证环境一致性
nix hash path .  # 应该产生相同的哈希值

# 验证实验结果一致性
python scripts/validate_reproducibility.py \
  --expected-results reference_results.json \
  --actual-results results/latest.json
```

## 5. 实验设计要素

### 5.1 稳健性测试维度

1. **输入扰动测试**：
   - 添加高斯噪声到观测值
   - 随机丢弃部分观测信息
   - 对抗性攻击生成

2. **环境动态测试**：
   - 突然改变环境动力学
   - 引入未见过的状态转移
   - 修改奖励函数结构

3. **长期一致性测试**：
   - 多轮对话一致性检查
   - 目标漂移检测
   - 规划冲突识别

### 5.2 评估指标

- **成功率**：任务完成率
- **稳健性得分**：在扰动下的性能保持率
- **一致性度量**：多轮决策的一致性分数
- **恢复能力**：从错误中恢复的速度和质量

## 6. 最佳实践建议

### 6.1 实验记录

- 使用 MLflow 或 Weights & Biases 记录所有实验参数和结果
- 自动保存模型检查点和中间结果
- 记录完整的环境哈希和依赖版本

### 6.2 代码组织

```
project/
├── flake.nix                 # Nix 环境定义
├── pyproject.toml           # Python 项目配置
├── configs/                 # 实验配置文件
├── data/                    # 数据集（通过 DVC 管理）
├── experiments/             # 实验脚本
├── src/                     # 核心代码
├── tests/                   # 测试代码
├── scripts/                 # 辅助脚本
└── results/                 # 实验结果
```

### 6.3 持续集成

```yaml
# .github/workflows/reproducibility.yml
name: Reproducibility Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cachix/install-nix-action@v20
      - name: Build environment
        run: nix build
      - name: Run reproducibility test
        run: nix run .#reproducibility-test
```

## 7. 故障排除指南

### 7.1 常见问题

**问题：Nix 构建失败**
- 解决方案：检查 nixpkgs 版本兼容性，更新 flake.lock

**问题：Docker 镜像过大**
- 解决方案：使用多阶段构建，只包含运行时依赖

**问题：实验结果不一致**
- 解决方案：检查随机种子设置，验证硬件差异影响

### 7.2 调试工具

- `nix log`：查看构建日志
- `nix why-depends`：分析依赖关系
- `docker history`：检查镜像层大小

## 结论

通过结合 NixOS 的强可重现性保证和 Docker 的广泛兼容性，本设计方案提供了多层次的实验环境保障。研究人员可以根据具体需求选择合适的技术栈，同时确保实验结果的可靠性和可复现性。这种混合方法特别适合多轮规划代理这类复杂的 AI 系统研究，其中环境一致性和依赖管理对实验有效性至关重要。