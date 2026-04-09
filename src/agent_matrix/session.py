"""会话管理 - 多会话支持与持久化"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .aggregator import ExecutionReport
from .knowledge import ProjectContext, ProjectIndexer
from .master import MasterAgent


@dataclass
class SessionConfig:
    """会话配置"""
    provider: str = "minimax"
    api_key: Optional[str] = None
    output_dir: str = "."
    model: Optional[str] = None
    webhooks: List[str] = field(default_factory=list)  # Webhook URL 列表
    project_root: Optional[str] = None  # 项目根目录路径

    async def trigger_webhooks(self, payload: dict) -> None:
        """触发所有 Webhook

        Args:
            payload: Webhook 负载数据
        """
        if not self.webhooks:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in self.webhooks:
                try:
                    await client.post(url, json=payload)
                except Exception as e:
                    print(f"[Webhook] 触发失败 {url}: {e}")


@dataclass
class Session:
    """会话对象"""
    id: str
    name: str
    created_at: datetime
    last_active: datetime
    config: SessionConfig
    reports: List[ExecutionReport] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    project_context: Optional[ProjectContext] = field(default=None, repr=False)
    _master: Optional[MasterAgent] = field(default=None, repr=False)
    _project_indexer: Optional[ProjectIndexer] = field(default=None, repr=False)

    def __post_init__(self):
        # 确保 config 是 SessionConfig 实例
        if isinstance(self.config, dict):
            self.config = SessionConfig(**self.config)
        # 初始化项目索引器
        if self._project_indexer is None:
            self._project_indexer = ProjectIndexer()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "config": asdict(self.config),
            "reports": [],  # reports 不持久化
            "metadata": self.metadata,
            "project_root": self.project_context.root if self.project_context else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """从字典反序列化"""
        session = cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            config=SessionConfig(**data["config"]),
            reports=[],
            metadata=data.get("metadata", {}),
            _master=None,
        )
        # 恢复项目上下文
        project_root = data.get("project_root")
        if project_root:
            try:
                session.set_project_root(project_root)
            except ValueError:
                pass  # 项目目录可能不存在
        return session

    def set_project_root(self, path: str) -> ProjectContext:
        """设置项目根目录并索引

        Args:
            path: 项目根目录路径

        Returns:
            项目上下文
        """
        self.project_context = self._project_indexer.set_root(path)
        self.config.project_root = path  # 同时保存到 config 以便序列化
        return self.project_context

    def get_project_context(self) -> Optional[ProjectContext]:
        """获取项目上下文"""
        return self.project_context


class SessionManager:
    """会话管理器

    管理多个会话的生命周期，支持持久化存储。
    """

    def __init__(self, storage_dir: Path = Path.home() / ".agent-matrix" / "sessions"):
        """初始化会话管理器

        Args:
            storage_dir: 会话存储目录
        """
        self._storage_dir = Path(storage_dir)
        self._sessions: Dict[str, Session] = {}
        self._current_id: Optional[str] = None

        # 确保存储目录存在
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = self._storage_dir / "current"

        # 加载已有会话
        self.load_sessions()

    def create_session(self, name: Optional[str] = None) -> Session:
        """创建新会话

        Args:
            name: 会话名称（默认自动生成）

        Returns:
            新创建的会话
        """
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        if name is None:
            name = f"session-{now.strftime('%Y%m%d-%H%M%S')}"

        session = Session(
            id=session_id,
            name=name,
            created_at=now,
            last_active=now,
            config=SessionConfig(),
            reports=[],
            metadata={},
            _master=MasterAgent(),
        )

        self._sessions[session_id] = session
        self.set_current(session_id)
        self.save_session(session)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话对象，不存在返回 None
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功
        """
        if session_id not in self._sessions:
            return False

        # 删除文件
        session_file = self._storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()

        # 从内存移除
        del self._sessions[session_id]

        # 如果删除的是当前会话，清除当前标记
        if self._current_id == session_id:
            self._current_id = None
            self._save_current()

        return True

    def list_sessions(self) -> List[Session]:
        """列出所有会话

        Returns:
            会话列表（按最后活跃时间倒序）
        """
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda s: s.last_active, reverse=True)
        return sessions

    def save_session(self, session: Session) -> None:
        """保存会话到磁盘

        Args:
            session: 会话对象
        """
        session_file = self._storage_dir / f"{session.id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def load_sessions(self) -> None:
        """从磁盘加载所有会话"""
        if not self._storage_dir.exists():
            return

        # 加载所有会话文件
        for session_file in self._storage_dir.glob("*.json"):
            if session_file.name == "current":
                continue
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = Session.from_dict(data)
                self._sessions[session.id] = session
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[SessionManager] 加载会话失败 {session_file}: {e}")

        # 加载当前会话标记
        self._load_current()

    def get_current(self) -> Optional[Session]:
        """获取当前会话

        Returns:
            当前会话，不存在返回 None
        """
        if self._current_id is None:
            return None
        return self._sessions.get(self._current_id)

    def set_current(self, session_id: str) -> None:
        """设置当前会话

        Args:
            session_id: 会话 ID

        Raises:
            ValueError: 会话不存在
        """
        if session_id not in self._sessions:
            raise ValueError(f"会话不存在: {session_id}")

        self._current_id = session_id
        self._save_current()

        # 更新 last_active
        session = self._sessions[session_id]
        session.last_active = datetime.now()
        self.save_session(session)

    def _load_current(self) -> None:
        """加载当前会话 ID"""
        if self._current_file.exists():
            try:
                with open(self._current_file, "r", encoding="utf-8") as f:
                    self._current_id = f.read().strip()
                # 验证会话是否存在
                if self._current_id and self._current_id not in self._sessions:
                    self._current_id = None
            except Exception:
                self._current_id = None

    def _save_current(self) -> None:
        """保存当前会话 ID"""
        with open(self._current_file, "w", encoding="utf-8") as f:
            if self._current_id:
                f.write(self._current_id)
            else:
                f.write("")
