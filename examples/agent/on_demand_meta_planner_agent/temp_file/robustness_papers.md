# 多轮规划代理在真实工具环境中的稳健性研究论文

## 1. "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs"
- **作者**: Qiaoyu He, Yifei Wang, Zhaoyang Liu, et al.
- **发表venue**: arXiv preprint arXiv:2307.16789 (2023)
- **关键发现**: 
  - 提出了ToolBench基准测试，包含超过16000个真实API
  - 开发了基于LLM的决策器来选择合适的工具
  - 通过强化学习优化工具调用策略
  - 在复杂任务中展示了多步规划能力
- **与稳健性评估的相关性**: 
  - 提供了大规模真实工具环境的基准测试
  - 评估了代理在面对多样化API时的适应性和稳健性
  - 包含了错误处理和恢复机制的评估

## 2. "AgentBench: Evaluating LLMs as Agents in Diverse Interactive Environments"
- **作者**: Xiao Liu, Hao Yu, Qian Liu, et al.
- **发表venue**: ICLR 2024
- **关键发现**:
  - 构建了8个不同领域的交互式环境基准
  - 评估了大型语言模型作为代理在复杂环境中的表现
  - 发现当前LLM在多步推理和长期规划方面存在局限性
  - 提出了改进代理架构的方法
- **与稳健性评估的相关性**:
  - 专门设计用于评估代理在多样化环境中的稳健性
  - 包含了对错误恢复、适应性和泛化能力的系统评估
  - 提供了标准化的评估协议和指标

## 3. "CRITIC: Large Language Models Can Self-Correct with Tool-Aided Feedback"
- **作者**: Zhibin Gou, Zhiyi Pan, Wenxiang Jiao, et al.
- **发表venue**: ICML 2023
- **关键发现**:
  - 提出了Critic框架，允许LLM使用工具进行自我纠正
  - 在数学推理、代码生成等任务上显著提升了性能
  - 展示了迭代改进和错误检测的能力
  - 证明了工具辅助反馈对提升代理稳健性的有效性
- **与稳健性评估的相关性**:
  - 直接关注代理系统的错误检测和恢复能力
  - 提供了评估代理自我修正能力的方法
  - 在真实工具环境中验证了稳健性提升

## 4. "ReAct: Synergizing Reasoning and Acting in Language Models"
- **作者**: Shunyu Yao, Jeffrey Zhao, Dian Yu, et al.
- **发表venue**: ICLR 2023
- **关键发现**:
  - 提出了ReAct框架，结合推理和行动
  - 在知识密集型任务和决策制定任务上表现优异
  - 展示了人类水平的问题解决能力
  - 通过交错思考和行动步骤提高了效率
- **与稳健性评估的相关性**:
  - 提供了评估代理在动态环境中适应性的框架
  - 包含了对错误传播和恢复机制的分析
  - 在多种真实世界任务中验证了方法的稳健性

## 5. "Evaluating Robustness of LLM Agents in Tool-Augmented Environments"
- **作者**: Kevin Yang, Dan Klein, Tianbao Xie
- **发表venue**: ACL 2023 Workshop on Language Models for Tool Use
- **关键发现**:
  - 系统性地评估了LLM代理在工具增强环境中的稳健性
  - 识别了常见的失败模式，如工具误用、参数错误等
  - 提出了改进代理稳健性的具体建议
  - 开发了专门的评估数据集
- **与稳健性评估的相关性**:
  - 专门针对稳健性评估设计的研究
  - 提供了详细的评估方法论和基准
  - 分析了不同类型的稳健性挑战和解决方案