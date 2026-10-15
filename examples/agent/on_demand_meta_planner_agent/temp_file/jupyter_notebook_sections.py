# Jupyter Notebook 主要部分代码模板

# 1) 环境设置和依赖导入
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# 设置随机种子以确保结果可重现
np.random.seed(42)

print("环境设置完成，所有依赖已成功导入。")

# 2) 评估框架定义（四个维度的具体指标计算）
def calculate_accuracy(y_true, y_pred):
    """计算准确率"""
    return accuracy_score(y_true, y_pred)

def calculate_precision(y_true, y_pred):
    """计算精确率"""
    return precision_score(y_true, y_pred, average='weighted')

def calculate_recall(y_true, y_pred):
    """计算召回率"""
    return recall_score(y_true, y_pred, average='weighted')

def calculate_f1(y_true, y_pred):
    """计算F1分数"""
    return f1_score(y_true, y_pred, average='weighted')

def evaluation_framework(y_true, y_pred):
    """综合评估框架：返回四个维度的指标"""
    metrics = {
        'accuracy': calculate_accuracy(y_true, y_pred),
        'precision': calculate_precision(y_true, y_pred),
        'recall': calculate_recall(y_true, y_pred),
        'f1_score': calculate_f1(y_true, y_pred)
    }
    return metrics

# 3) 实验数据加载和预处理（模拟数据生成）
def generate_sample_data(n_samples=1000, n_features=10, n_classes=3):
    """生成模拟数据集"""
    # 生成特征矩阵
    X = np.random.randn(n_samples, n_features)
    
    # 生成目标变量（分类标签）
    y = np.random.randint(0, n_classes, n_samples)
    
    # 创建DataFrame便于处理
    feature_names = [f'feature_{i}' for i in range(n_features)]
    df = pd.DataFrame(X, columns=feature_names)
    df['target'] = y
    
    return df

# 加载模拟数据
data = generate_sample_data()
print(f"数据集形状: {data.shape}")
print(f"类别分布:\n{data['target'].value_counts().sort_index()}")

# 数据预处理示例
X = data.drop('target', axis=1)
y = data['target']

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"训练集大小: {X_train.shape[0]}")
print(f"测试集大小: {X_test.shape[0]}")

# 4) 评估函数实现
def evaluate_model(model, X_test, y_test):
    """评估模型性能"""
    # 预测
    y_pred = model.predict(X_test)
    
    # 计算评估指标
    metrics = evaluation_framework(y_test, y_pred)
    
    return metrics, y_pred

# 简单的基线模型（使用随机预测作为示例）
class RandomPredictor:
    def __init__(self, n_classes):
        self.n_classes = n_classes
        
    def fit(self, X, y):
        # 随机预测器不需要训练
        pass
        
    def predict(self, X):
        return np.random.randint(0, self.n_classes, len(X))

# 5) 实验执行
# 初始化模型
baseline_model = RandomPredictor(n_classes=3)

# 训练模型（对于随机预测器，这一步实际上不做任何事情）
baseline_model.fit(X_train, y_train)

# 评估模型
baseline_metrics, baseline_predictions = evaluate_model(baseline_model, X_test, y_test)

print("基线模型评估结果:")
for metric, value in baseline_metrics.items():
    print(f"{metric}: {value:.4f}")

# 6) 结果分析和可视化
def visualize_results(metrics_dict, model_names):
    """可视化多个模型的评估结果"""
    # 转换为DataFrame便于绘图
    results_df = pd.DataFrame(metrics_dict).T
    
    # 绘制柱状图
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    metrics_list = ['accuracy', 'precision', 'recall', 'f1_score']
    
    for i, metric in enumerate(metrics_list):
        ax = axes[i]
        bars = ax.bar(model_names, results_df[metric])
        ax.set_title(f'{metric.capitalize()} Comparison')
        ax.set_ylabel('Score')
        ax.set_ylim(0, 1)
        
        # 在柱子上添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.show()
    
    return results_df

# 可视化基线模型结果
results = {'Baseline': baseline_metrics}
results_df = visualize_results(results, ['Baseline'])

# 显示详细结果表格
print("\n详细评估结果:")
print(results_df.round(4))

# 7) 结论模板
def generate_conclusion(metrics, model_name="Model"):
    """生成结论模板"""
    conclusion = f"""
    # 实验结论: {model_name}
    
    ## 主要发现
    - 准确率 (Accuracy): {metrics['accuracy']:.4f}
    - 精确率 (Precision): {metrics['precision']:.4f}
    - 召回率 (Recall): {metrics['recall']:.4f}
    - F1分数 (F1-Score): {metrics['f1_score']:.4f}
    
    ## 分析
    [在此处添加对结果的详细分析]
    
    ## 改进建议
    [在此处添加可能的改进方向]
    
    ## 限制性
    [在此处说明实验的局限性]
    """
    return conclusion

# 生成结论
conclusion = generate_conclusion(baseline_metrics, "Random Baseline")
print(conclusion)