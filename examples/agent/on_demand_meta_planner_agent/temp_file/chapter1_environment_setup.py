#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 1: Environment Setup
===========================
最小可运行的环境设置代码块，包含所有必要的依赖导入和环境配置。
"""

# 标准库导入
import sys
import os
import logging
from pathlib import Path

# 第三方库导入
try:
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats
    import json
    import pickle
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install required packages: pip install numpy pandas matplotlib seaborn scipy")
    sys.exit(1)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 设置随机种子以确保可重现性
np.random.seed(42)

# 设置matplotlib样式
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# 创建必要的目录
Path("data").mkdir(exist_ok=True)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)

# 验证环境设置
def verify_environment():
    """验证环境是否正确设置"""
    logger.info("Verifying environment setup...")
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        logger.error("Python 3.7 or higher is required")
        return False
    
    # 检查关键库版本
    required_versions = {
        'numpy': '1.19.0',
        'pandas': '1.3.0',
        'matplotlib': '3.4.0',
        'seaborn': '0.11.0',
        'scipy': '1.7.0'
    }
    
    import pkg_resources
    for package, min_version in required_versions.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(min_version):
                logger.warning(f"{package} version {installed_version} is below minimum required {min_version}")
        except pkg_resources.DistributionNotFound:
            logger.error(f"{package} is not installed")
            return False
    
    logger.info("Environment setup verified successfully!")
    return True

# 执行环境验证
if __name__ == "__main__":
    success = verify_environment()
    if success:
        print("Environment setup completed successfully!")
    else:
        print("Environment setup failed!")
        sys.exit(1)