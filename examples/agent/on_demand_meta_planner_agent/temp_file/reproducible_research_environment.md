# 可复现实验环境设计方案

## 1. 概述

可复现性是科学研究的核心原则之一。本方案旨在提供一个基于现代工具链的完整解决方案，确保实验环境的一致性、可复现性和可移植性。方案结合了NixOS/Nix包管理器和Docker容器技术的优势，提供了多层次的环境隔离和依赖管理策略。

## 2. 核心原则

### 2.1 确定性构建
- 所有依赖项必须明确指定版本
- 构建过程必须是纯函数式的（相同输入产生相同输出）
- 避免隐式依赖和全局状态

### 2.2 环境隔离
- 实验环境与系统环境完全隔离
- 不同实验之间的依赖互不干扰
- 支持并行运行多个不同版本的实验

### 2.3 版本控制集成
- 环境配置文件纳入版本控制系统
- 支持环境配置的差异比较和回滚
- 与代码版本保持同步

## 3. 技术栈选择

### 3.1 Nix/NixOS 方案
**优势：**
- 纯函数式包管理，确保构建的确定性
- 原子性升级和回滚
- 多版本软件共存
- 跨平台支持（Linux, macOS, Windows via WSL2）

**适用场景：**
- 需要高度确定性的科学计算环境
- 长期项目维护
- 复杂依赖关系管理

### 3.2 Docker 方案
**优势：**
- 广泛的社区支持和镜像生态
- 轻量级虚拟化
- 易于部署和分发
- 云原生友好

**适用场景：**
- 快速原型开发
- 微服务架构
- 云部署需求

### 3.3 混合方案（推荐）
结合两者优势：
- 使用Nix定义精确的软件依赖
- 使用Docker进行运行时隔离和部署
- 利用Nix构建Docker镜像，确保镜像的可复现性

## 4. 详细实施方案

### 4.1 依赖管理

#### 4.1.1 Nix 方案
创建 `shell.nix` 文件定义开发环境：

```nix
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python39
    pkgs.python39Packages.numpy
    pkgs.python39Packages.scipy
    pkgs.python39Packages.matplotlib
    pkgs.python39Packages.pandas
    pkgs.git
    pkgs.jq
    # 添加其他必需的包
  ];
  
  # 设置环境变量
  shellHook = ''
    export PYTHONPATH="${pkgs.python39Packages.numpy}/lib/python3.9/site-packages:$PYTHONPATH"
    echo "Development environment activated!"
  '';
}
```

对于更复杂的项目，使用 `default.nix`：

```nix
{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python39.withPackages (ps: with ps; [
    numpy
    scipy
    matplotlib
    pandas
    scikit-learn
    jupyter
  ]);
in
pkgs.stdenv.mkDerivation {
  name = "research-project";
  src = ./.;
  buildInputs = [ pythonEnv git jq ];
  shellHook = ''
    export PATH="${pythonEnv}/bin:$PATH"
    echo "Research environment ready!"
  '';
}
```

#### 4.1.2 Docker 方案
创建 `Dockerfile`：

```dockerfile
# 使用特定版本的基础镜像
FROM python:3.9.16-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖（使用--no-cache-dir避免缓存问题）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 默认命令
CMD ["python", "main.py"]
```

对应的 `requirements.txt`：

```
numpy==1.24.3
scipy==1.10.1
matplotlib==3.7.1
pandas==2.0.1
scikit-learn==1.2.2
jupyter==1.0.0
```

### 4.2 环境隔离策略

#### 4.2.1 开发阶段
- **Nix Shell**: 使用 `nix-shell` 进入隔离的开发环境
- **Docker Compose**: 对于多服务应用，使用 `docker-compose.yml` 定义服务依赖

`docker-compose.yml` 示例：

```yaml
version: '3.8'
services:
  research-app:
    build: .
    volumes:
      - .:/app
      - ./data:/app/data
    ports:
      - "8888:8888"
    environment:
      - PYTHONPATH=/app
    command: jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
  database:
    image: postgres:15
    environment:
      POSTGRES_DB: research_db
      POSTGRES_USER: researcher
      POSTGRES_PASSWORD: secure_password
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

#### 4.2.2 生产/共享阶段
- **Nix Flake**: 使用Flakes确保跨机器的一致性
- **Docker Registry**: 将构建好的镜像推送到私有或公共registry

`flake.nix` 示例：

```nix
{
  description = "Reproducible Research Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python39.withPackages (ps: with ps; [
          numpy scipy matplotlib pandas scikit-learn jupyter
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv git jq ];
          shellHook = ''
            export PATH="${pythonEnv}/bin:$PATH"
          '';
        };
        
        packages.default = pkgs.dockerTools.buildImage {
          name = "research-environment";
          tag = "latest";
          contents = [ pythonEnv git jq ];
          config = {
            Cmd = [ "${pythonEnv}/bin/python" "main.py" ];
            WorkingDir = "/app";
          };
        };
      });
}
```

### 4.3 版本控制策略

#### 4.3.1 必须纳入版本控制的文件
```
.
├── .gitignore
├── README.md
├── shell.nix                 # Nix开发环境定义
├── default.nix               # Nix包定义
├── flake.nix                 # Nix Flakes定义（可选）
├── flake.lock                # Flakes锁定文件
├── Dockerfile                # Docker镜像定义
├── docker-compose.yml        # 多服务定义
├── requirements.txt          # Python依赖（如果使用）
├── environment.yml           # Conda环境（如果使用）
└── src/                      # 源代码目录
```

#### 4.3.2 .gitignore 推荐配置
```
# 系统文件
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Jupyter
.ipynb_checkpoints

# Data files (consider using Git LFS for small datasets)
data/
*.csv
*.json
*.h5
*.hdf5

# Docker
.dockerignore

# IDE
.vscode/
.idea/
*.swp
*.swo
```

### 4.4 部署说明

#### 4.4.1 本地开发环境设置

**Nix 方式：**
```bash
# 安装Nix（如果尚未安装）
curl -L https://nixos.org/nix/install | sh

# 进入开发环境
nix-shell

# 或者使用Flakes（需要启用）
nix develop
```

**Docker 方式：**
```bash
# 构建镜像
docker build -t research-project .

# 运行容器
docker run -it --rm -v $(pwd):/app -p 8888:8888 research-project

# 或使用Docker Compose
docker-compose up
```

#### 4.4.2 共享和协作

**Nix 方式：**
```bash
# 其他协作者只需克隆仓库并进入环境
git clone <repository-url>
cd <repository>
nix-shell  # 或 nix develop
```

**Docker 方式：**
```bash
# 推送镜像到registry
docker tag research-project your-registry/research-project:v1.0
docker push your-registry/research-project:v1.0

# 其他协作者拉取并运行
docker pull your-registry/research-project:v1.0
docker run -it --rm your-registry/research-project:v1.0
```

#### 4.4.3 CI/CD 集成

GitHub Actions 示例 (`.github/workflows/test.yml`)：

```yaml
name: Test Research Environment

on: [push, pull_request]

jobs:
  test-nix:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: cachix/install-nix-action@v20
    - name: Build and test with Nix
      run: |
        nix-build
        nix-shell --run "python -m pytest tests/"

  test-docker:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: docker build -t research-project .
    - name: Run tests in container
      run: docker run research-project python -m pytest tests/
```

## 5. 最佳实践

### 5.1 依赖版本固定
- 始终指定确切的版本号
- 定期更新依赖并测试兼容性
- 使用锁定文件（如 `flake.lock`, `package-lock.json`）

### 5.2 环境文档化
- 在README中详细说明环境设置步骤
- 提供快速启动指南
- 记录已知问题和解决方案

### 5.3 数据管理
- 将原始数据和处理后的数据分开存储
- 使用数据版本控制工具（如DVC）管理大型数据集
- 在环境中包含数据验证脚本

### 5.4 测试策略
- 包含环境验证测试
- 自动化依赖兼容性测试
- 定期进行端到端测试

## 6. 故障排除

### 6.1 常见问题
- **依赖冲突**: 使用Nix的多版本支持或Docker的完全隔离
- **性能问题**: 优化Docker镜像层，使用Nix的二进制缓存
- **跨平台兼容性**: Nix在所有支持平台上提供一致的构建体验

### 6.2 验证环境一致性
```bash
# Nix: 验证构建哈希
nix-store --query --hash $(nix-instantiate default.nix)

# Docker: 验证镜像哈希
docker images --digests research-project
```

## 7. 结论

本方案提供了两种主要的技术路径（Nix和Docker）以及它们的混合使用方式。对于大多数科研项目，推荐采用混合方案：

1. **开发阶段**: 使用Nix提供精确的依赖管理和开发环境
2. **部署阶段**: 使用Nix构建Docker镜像，确保部署的一致性
3. **协作阶段**: 通过版本控制共享环境配置，协作者可以轻松重现环境

这种组合充分利用了Nix的确定性构建优势和Docker的广泛部署支持，为科研工作的可复现性提供了坚实的基础。