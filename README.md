# Agent Matrix

轻量级多 Agent 协作开发框架。主控 Agent 接收任务后自动拆解、分发给多个执行 Agent，最后汇总结果。

## 特性

- **任务自动分解**：使用 LLM 分析任务并拆解为可执行的子任务
- **多角色 Agent**：Coder、Reviewer、Tester 分工协作
- **依赖拓扑调度**：按依赖关系自动排序执行
- **结果汇总**：整合各 Agent 输出生成最终报告

## 安装

```bash
pip install -e .
```

或安装开发依赖：

```bash
pip install -e ".[dev]"
```

## 配置

需要设置 MiniMax API Key：

```bash
export MINIMAX_API_KEY="your-api-key-here"
```

或直接在代码中传入。

## 使用方法

### 单任务模式

```bash
agent-matrix "实现一个计算器程序"
```

### 交互模式

```bash
agent-matrix
```

### Markdown 格式输出

```bash
agent-matrix "实现一个排序算法" --markdown
```

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
│  │  Coder   │  │ Reviewer │  │  Tester  │  ...         │
│  └──────────┘  └──────────┘  └──────────┘               │
├─────────────────────────────────────────────────────────┤
│                    LLM Adapter (MiniMax)                │
└─────────────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `TaskDecomposer` | 用 LLM 分析任务，拆解成子任务列表 |
| `AgentPool` | 管理不同角色的 Agent 实例 |
| `CollaborationEngine` | 解析依赖拓扑，执行调度 |
| `ResultAggregator` | 汇总各 Agent 输出，生成最终报告 |
| `LLMAdapter` | 封装 MiniMax API 调用 |

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
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py         # Agent 基类
│       │   ├── coder.py        # Coder Agent
│       │   ├── reviewer.py     # Reviewer Agent
│       │   └── tester.py       # Tester Agent
│       └── llm/
│           ├── __init__.py
│           └── minimax.py      # MiniMax API 适配器
├── tests/
│   ├── __init__.py
│   ├── test_decomposer.py
│   ├── test_engine.py
│   └── test_agents.py
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
