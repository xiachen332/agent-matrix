# Multi-Agent 协作开发框架 - SPEC.md

## 1. 概念与目标

**项目名称**: `agent-matrix`
**项目类型**: CLI 工具（Python）
**核心愿景**: 主控 Agent 接收任务后自动拆解、分发给多个执行 Agent，最后汇总结果
**核心价值**: 复用 LLM 能力实现自动化任务分解与多角色协作

---

## 2. 架构设计

### 2.1 整体架构

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

### 2.2 核心模块

| 模块 | 职责 | 状态 |
|------|------|------|
| `TaskDecomposer` | 用 LLM 分析任务，拆解成子任务列表 | Phase 1 |
| `AgentPool` | 管理不同角色的 Agent 实例 | Phase 1 |
| `CollaborationEngine` | 解析依赖拓扑，执行调度 | Phase 1 |
| `ResultAggregator` | 汇总各 Agent 输出，生成最终报告 | Phase 1 |
| `LLMAdapter` | 封装 MiniMax API 调用 | Phase 2 |
| `CLI` | 命令行交互界面 | Phase 1 |

---

## 3. 目录结构

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
│       │   ├── reviewer.py      # Reviewer Agent
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
└── README.md
```

---

## 4. 接口设计

### 4.1 Agent 基类接口

```python
class Agent(ABC):
    @property
    @abstractmethod
    def role(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def execute(self, task: Task) -> AgentResult: ...
```

### 4.2 Task 结构

```python
@dataclass
class Task:
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)  # 依赖的 task id 列表
    assigned_agent: Optional[str] = None
    result: Optional[AgentResult] = None
    status: TaskStatus = TaskStatus.PENDING
```

### 4.3 CollaborationEngine 接口

```python
class CollaborationEngine:
    def __init__(self, pool: AgentPool): ...

    async def execute(self, tasks: List[Task]) -> List[Task]: ...
    # 按依赖拓扑排序执行，返回带结果的 task 列表
```

---

## 5. 第一阶段实现范围

### 5.1 必须完成

- [x] SPEC.md 架构定义
- [x] `pyproject.toml` 项目配置
- [x] `src/agent_matrix/agents/base.py` - Agent 抽象基类
- [x] `src/agent_matrix/decomposer.py` - 任务分解器（LLM 调用部分可 Mock）
- [x] `src/agent_matrix/engine.py` - 协作引擎核心逻辑
- [x] `src/agent_matrix/pool.py` - Agent 池
- [x] `src/agent_matrix/master.py` - Master Agent 主控
- [x] `src/agent_matrix/aggregator.py` - 结果汇总器
- [x] `src/agent_matrix/cli.py` - CLI 入口
- [x] 基础测试用例

### 5.2 第二阶段

- [x] MiniMax API 真实调用
- [x] Agent 具体实现（Coder/Reviewer/Tester）
- [ ] 完整测试覆盖

---

## 6. 关键设计决策

### 6.1 依赖管理
- 使用 `dataclass` + `field(default_factory=list)` 表示任务依赖
- 协作引擎使用拓扑排序（Kahn 算法）保证执行顺序

### 6.2 Agent 发现机制
- Agent 池通过注册表模式管理
- 每个 Agent 声明自己的 `role` 和 `description`
- 任务分解时根据 description 匹配最适合的 Agent

### 6.3 扩展性
- 新增 Agent 只需继承 `Agent` 基类并注册到池中
- LLM 适配器抽象接口，便于后续支持其他 API

---

## 7. 技术约束

- **Python 版本**: 3.11+
- **异步**: 使用 `asyncio` 实现并发任务执行
- **类型提示**: 全程类型提示，便于维护
- **测试**: 使用 `pytest`
