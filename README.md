# Agent Matrix

轻量级多 Agent 协作开发框架。主控 Agent 接收任务后自动拆解、分发给多个执行 Agent，最后汇总结果。

## 特性

- **任务自动分解**：使用 LLM 分析任务并拆解为可执行的子任务
- **多角色 Agent**：Coder、Reviewer、Tester 分工协作
- **依赖拓扑调度**：按依赖关系自动排序执行
- **结果汇总**：整合各 Agent 输出生成最终报告
- **多模型支持**：MiniMax / OpenAI / OpenRouter / DeepSeek / SiliconFlow / Claude
- **多会话管理**：支持持久化会话，跨任务保持上下文
- **真干活**：Coder 写文件、Tester 生成并运行 pytest
- **流式输出**：实时看到 LLM 打字效果
- **Token 统计**：按会话统计消耗 credits
- **Webhook 通知**：任务完成后主动回调
- **项目知识库**：Agent 理解项目结构再写代码
- **安全扫描**：自动检查代码安全漏洞
- **后台任务**：长时间任务后台运行不阻塞

## 安装

```bash
pip install -e .
```

或安装开发依赖：

```bash
pip install -e ".[dev]"
```

## 快速开始

### 环境变量配置

```bash
# MiniMax（默认）
export MINIMAX_API_KEY="your-api-key-here"

# 或 OpenAI
export OPENAI_API_KEY="your-api-key-here"

# 或 OpenRouter
export OPENROUTER_API_KEY="your-api-key-here"
```

### 单任务模式

```bash
agent-matrix "用 Python 写一个快速排序"
agent-matrix "用 Python 写一个快速排序" --provider openai
agent-matrix "用 Python 写一个快速排序" --markdown
```

### 交互模式

```bash
agent-matrix
```

进入后可用指令：

```
/session              # 交互式选择会话
/session new [name]   # 新建会话
/session <id>        # 切换会话
/session delete <id> # 删除会话
/context             # 查看会话元数据/项目上下文
/context clear       # 清空元数据
/project <dir>       # 关联项目目录（知识库）
/provider openai     # 切换 LLM 提供商
/key <api_key>       # 设置 API Key
/model gpt-4o        # 设置模型
/output ./src         # 设置代码输出目录
/config              # 显示当前配置和 Token 统计
/quit                # 退出（自动保存会话）
```

## 支持的模型提供商

| 提供商 | 默认模型 | 说明 |
|--------|---------|------|
| `minimax` | MiniMax-M2 | 默认，国内可用 |
| `openai` | GPT-4o-mini | OpenAI 官方 |
| `openrouter` | Claude 3 Haiku | 支持 Claude/GPT/Llama 等 |
| `deepseek` | deepseek-chat | 便宜 |
| `siliconflow` | Qwen2.5-7B | 国内可用 |
| `claude` | claude-sonnet-4 | Anthropic 官方 |

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Interface                      │
├─────────────────────────────────────────────────────────┤
│                    Master Agent                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │TaskDecomposer│  │协作引擎     │  │  ResultAggregator│  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                      Agent Pool                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Coder   │  │ Reviewer │  │  Tester  │               │
│  └──────────┘  └──────────┘  └──────────┘               │
├─────────────────────────────────────────────────────────┤
│                    LLM Adapter                          │
│         (MiniMax/OpenAI/OpenRouter/Claude...)           │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
agent-matrix/
├── src/
│   └── agent_matrix/
│       ├── __init__.py
│       ├── cli.py              # CLI 入口
│       ├── master.py           # Master Agent 主控
│       ├── decomposer.py       # 任务分解器
│       ├── engine.py           # 协作引擎
│       ├── aggregator.py       # 结果汇总器
│       ├── pool.py             # Agent 池
│       ├── session.py          # 会话管理
│       ├── agents/
│       │   ├── base.py         # Agent 基类
│       │   ├── coder.py        # Coder Agent
│       │   ├── reviewer.py     # Reviewer Agent
│       │   └── tester.py       # Tester Agent
│       └── llm/
│           ├── __init__.py
│           └── adapter.py      # 通用 LLM 适配器
├── tests/
├── pyproject.toml
├── SPEC.md
└── README.md
```

## 开发

运行测试：

```bash
pytest
```

## License

MIT
