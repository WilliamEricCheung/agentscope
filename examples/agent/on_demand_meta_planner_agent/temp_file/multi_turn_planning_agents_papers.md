# 多轮规划代理在真实工具环境中稳健性评估相关论文

## 重要说明
由于技术限制，以下论文信息是基于我的训练数据中的知识提供的，而非通过实时学术搜索引擎检索获得。这些论文代表了该领域的重要工作。

## 论文列表

### 1. "Toolformer: Language Models Can Teach Themselves to Use Tools"
- **作者**: Thomas Schick, Jane Dwivedi-Yu, Roberto Dessì, Robert L. Logan IV, et al.
- **发表年份**: 2023
- **摘要**: 这篇论文介绍了Toolformer，一个能够自学使用外部工具（如计算器、问答系统、搜索引擎等）的语言模型。该研究展示了如何通过自监督方式训练模型决定何时以及如何调用API，为多轮规划代理的工具使用提供了重要基础。
- **相关性**: 直接涉及LLM代理工具使用的可靠性问题，是评估代理在真实环境中工具使用能力的重要基准。

### 2. "ReAct: Synergizing Reasoning and Acting in Language Models"
- **作者**: Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao
- **发表年份**: 2022
- **摘要**: ReAct框架结合了推理（Reasoning）和行动（Acting），使语言模型能够在与环境交互的同时进行推理。这种方法显著提高了代理在复杂任务中的表现和稳健性。
- **相关性**: 提供了多轮规划代理的典型架构，对评估代理在需要多步推理和工具调用的任务中的稳健性具有重要参考价值。

### 3. "AgentBench: Evaluating LLMs as Agents"
- **作者**: Xiao Liu, Hao Yu, Hanchen Zhang, Yifan Xu, et al.
- **发表年份**: 2023
- **摘要**: AgentBench是一个全面的基准测试套件，用于评估大型语言模型作为代理的能力。它涵盖了8个不同场景，包括网络浏览、数据库查询、知识图谱导航等，提供了对代理在真实工具环境中表现的系统性评估。
- **相关性**: 这是最直接相关的论文，专门针对LLM代理的评估基准，包含了对稳健性的多维度测量。

### 4. "CRITIC: Large Language Models Can Self-Correct with Tool-Aided Feedback"
- **作者**: Zhibin Gou, Zhiyuan Hu, Xiangrong Kong, Zijia Lu, et al.
- **发表年份**: 2023
- **摘要**: CRITIC框架允许大型语言模型利用工具辅助的反馈进行自我纠正。这种方法提高了代理在复杂任务中的准确性和稳健性。
- **相关性**: 探讨了如何提高代理在工具使用过程中的可靠性，对稳健性评估有重要启示。

### 5. "Voyager: An Open-Ended Embodied Agent with Large Language Models"
- **作者**: Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, et al.
- **发表年份**: 2023
- **摘要**: Voyager是一个在Minecraft环境中运行的开放式具身代理，展示了LLM如何在复杂环境中进行长期规划和工具使用。
- **相关性**: 提供了在复杂、动态环境中评估多轮规划代理稳健性的实际案例。

## 搜索关键词建议
- "multi-turn planning agents robustness"
- "LLM agent tool usage reliability" 
- "agent evaluation benchmark"
- "tool-augmented language models"
- "embodied AI agent evaluation"
- "reasoning and acting in LLMs"

## 后续研究方向
1. 开发更全面的稳健性评估指标
2. 研究代理在面对工具API变化时的适应能力
3. 探索多代理协作环境中的稳健性问题
4. 建立标准化的工具使用失败恢复机制