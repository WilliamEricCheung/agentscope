#!/usr/bin/env python3
"""
Test script to verify that all required packages are properly installed
and GPU support is working (if available).
"""

import sys
import torch
import tensorflow as tf
from transformers import pipeline
import pandas as pd
import numpy as np
import wandb
import mlflow

def test_pytorch():
    """Test PyTorch installation and GPU support"""
    print("Testing PyTorch...")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device count: {torch.cuda.device_count()}")
        print(f"Current CUDA device: {torch.cuda.current_device()}")
        print(f"CUDA device name: {torch.cuda.get_device_name()}")
    else:
        print("Running on CPU")
    print("✓ PyTorch test passed\n")

def test_tensorflow():
    """Test TensorFlow installation and GPU support"""
    print("Testing TensorFlow...")
    print(f"TensorFlow version: {tf.__version__}")
    print(f"Built with CUDA: {tf.test.is_built_with_cuda()}")
    gpu_devices = tf.config.list_physical_devices('GPU')
    print(f"GPU devices available: {len(gpu_devices)}")
    if gpu_devices:
        for i, device in enumerate(gpu_devices):
            print(f"  GPU {i}: {device}")
    else:
        print("Running on CPU")
    print("✓ TensorFlow test passed\n")

def test_transformers():
    """Test Hugging Face Transformers"""
    print("Testing Transformers...")
    # Simple sentiment analysis pipeline
    classifier = pipeline("sentiment-analysis")
    result = classifier("This is a great test!")
    print(f"Sentiment analysis result: {result}")
    print("✓ Transformers test passed\n")

def test_langchain():
    """Test LangChain installation"""
    print("Testing LangChain...")
    try:
        import langchain
        print(f"LangChain version: {langchain.__version__}")
        print("✓ LangChain test passed\n")
    except ImportError as e:
        print(f"LangChain import failed: {e}")
        print("✗ LangChain test failed\n")

def test_data_processing():
    """Test pandas and numpy"""
    print("Testing data processing libraries...")
    # Create a simple DataFrame
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    print(f"DataFrame:\n{df}")
    
    # Test numpy operations
    arr = np.array([1, 2, 3, 4, 5])
    print(f"NumPy array mean: {np.mean(arr)}")
    print("✓ Data processing test passed\n")

def test_experiment_tools():
    """Test experiment management tools"""
    print("Testing experiment management tools...")
    print(f"W&B version: {wandb.__version__}")
    print(f"MLflow version: {mlflow.__version__}")
    print("✓ Experiment tools test passed\n")

def main():
    """Run all tests"""
    print("🧪 Running environment validation tests...\n")
    
    try:
        test_pytorch()
        test_tensorflow()
        test_transformers()
        test_langchain()
        test_data_processing()
        test_experiment_tools()
        
        print("🎉 All tests passed! Environment is ready for experiments.")
        return 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())