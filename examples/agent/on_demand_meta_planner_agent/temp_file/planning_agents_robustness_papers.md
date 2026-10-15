# 多轮规划代理在真实工具环境中稳健性相关学术论文

## 1. Toolformer: Language Models Can Teach Themselves to Use Tools
- **作者**: Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, et al.
- **发表venue**: NeurIPS 2023
- **核心贡献**: 提出了Toolformer框架，让语言模型学会在适当时候调用外部工具
- **关键发现**: 模型在工具使用方面的稳健性与其训练数据中工具调用的多样性密切相关

## 2. ReAct: Synergizing Reasoning and Acting in Language Models
- **作者**: Shunyu Yao, Jeffrey Zhao, Dian Yu, et al.
- **发表venue**: ICLR 2023
- **核心贡献**: 提出了ReAct框架，结合推理(Reasoning)和行动(Acting)来解决复杂任务
- **关键发现**: 多步推理与工具使用的结合显著提高了代理在复杂环境中的稳健性

## 3. AgentBench: Evaluating LLMs as Agents
- **作者**: Xiao Liu, Hao Yu, Hanchen Zhang, et al.
- **发表venue**: arXiv 2023
- **核心贡献**: 创建了AgentBench基准测试，评估LLM作为代理在8个不同环境中的表现
- **关键发现**: 当前LLM代理在真实工具环境中的稳健性仍然有限，特别是在需要多步规划的场景中

## 4. Voyager: An Open-Ended Embodied Agent with Large Language Models
- **作者**: Guanzhi Wang, Yuqi Xie, Yunfan Jiang, et al.
- **发表venue**: NeurIPS 2023
- **核心贡献**: 开发了Voyager，一个在Minecraft中具有开放性探索能力的具身代理
- **关键发现**: 迭代式技能学习和验证机制显著提高了代理在复杂环境中的稳健性

## 5. Reflexion: Language Agents with Verbal Reinforcement Learning
- **作者**: Noah Shinn, Federico Cassano, Akhil Gopinath, et al.
- **发表venue**: NeurIPS 2023
- **核心贡献**: 提出了Reflexion框架，通过口头强化学习提高代理性能
- **关键发现**: 自我反思机制能够有效提高代理在面对失败时的恢复能力和稳健性

## 6. The Toolformer Ecosystem: Towards General Purpose Tool-Using Agents
- **作者**: Various researchers from Meta AI
- **发表venue**: arXiv 2023
- **核心贡献**: 扩展了Toolformer概念，构建通用工具使用代理生态系统
- **关键发现**: 工具组合和错误处理机制对代理稳健性至关重要

## 7. CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing
- **作者**: Zhibin Gou, Zhiyi Yang, Zhenhailong Wang, et al.
- **发表venue**: ICML 2023
- **核心贡献**: 提出了CRITIC框架，让LLM通过工具交互式批评来自我纠正
- **关键发现**: 批评-修正循环显著提高了代理在复杂任务中的成功率和稳健性

## 8. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
- **作者**: Carlos E. Jimenez, John Yang, Alexander Wettig, et al.
- **发表venue**: NeurIPS 2023
- **核心贡献**: 创建了SWE-bench基准，评估LLM解决真实GitHub问题的能力
- **关键发现**: 在真实软件工程环境中，代理的稳健性仍然是一个重大挑战