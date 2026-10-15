{
  description = "NixOS Flake for Multi-round Planning Agent Robustness Experiments";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python包集合，包含所有必要的依赖
        pythonPackages = pkgs.python311Packages;
        
        # 自定义Python环境，包含所有实验所需的库
        planningAgentEnv = pythonPackages.buildPythonApplication {
          pname = "planning-agent-robustness-env";
          version = "1.0.0";
          
          # 定义所有Python依赖
          propagatedBuildInputs = with pythonPackages; [
            # 核心机器学习库
            torch
            tensorflow
            
            # LLM相关工具
            transformers
            langchain
            
            # 实验管理工具
            wandb
            mlflow
            
            # 数据处理库
            pandas
            numpy
            
            # 其他常用库
            matplotlib
            scikit-learn
            jupyter
            ipykernel
            requests
            tqdm
            pyyaml
            click
            rich
          ];
          
          # 确保环境可复现
          doCheck = false;
          meta = {
            description = "Python environment for multi-round planning agent robustness experiments";
            license = pkgs.lib.licenses.mit;
          };
        };
        
        # 创建完整的开发shell环境
        devShell = pkgs.mkShell {
          packages = with pkgs; [
            # 基础开发工具
            git
            curl
            wget
            htop
            tmux
            
            # Python环境
            planningAgentEnv
            
            # GPU支持相关工具（如果系统有GPU）
            cudaPackages.cudnn
            cudaPackages.cuda_cudart
            
            # 其他有用的工具
            nodejs
            ripgrep
            fd
          ];
          
          # 环境变量设置
          shellHook = ''
            # 设置Python路径
            export PYTHONPATH="${planningAgentEnv}/${pythonPackages.python.sitePackages}:$PYTHONPATH"
            
            # 设置Jupyter内核
            ${pythonPackages.ipykernel}/bin/python -m ipykernel install --user --name planning-agent-env --display-name "Planning Agent Env"
            
            # GPU相关环境变量
            export CUDA_HOME=${pkgs.cudatoolkit}
            export LD_LIBRARY_PATH="${pkgs.cudatoolkit}/lib:${pkgs.cudnn}/lib:$LD_LIBRARY_PATH"
            
            # 显示环境信息
            echo "Planning Agent Robustness Environment Ready!"
            echo "Python version: $(python --version)"
            echo "Available packages:"
            pip list | grep -E "(torch|tensorflow|transformers|langchain|wandb|mlflow|pandas|numpy)"
          '';
        };
        
      in
      {
        # 主要的包输出
        packages.default = planningAgentEnv;
        packages.planningAgentEnv = planningAgentEnv;
        
        # 开发环境
        devShells.default = devShell;
        devShells.planningAgent = devShell;
        
        # 可直接运行的环境
        apps.default = {
          type = "app";
          program = "${devShell}/bin/bash";
        };
        
        # NixOS模块（如果在NixOS系统上使用）
        nixosModule = { config, lib, pkgs, ... }: {
          environment.systemPackages = [ planningAgentEnv ];
          # 可选：配置GPU驱动
          services.xserver.videoDrivers = [ "nvidia" ];
          hardware.opengl.enable = true;
          hardware.opengl.driSupport = true;
          hardware.opengl.driSupport32Bit = true;
        };
      });
}