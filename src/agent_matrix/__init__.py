"""agent-matrix: 轻量级多Agent协作开发框架"""

__version__ = "0.1.0"

from .session import Session, SessionConfig, SessionManager
from .aggregator import ExecutionReport
from .knowledge import ProjectContext, ProjectIndexer

__all__ = [
    "Session", "SessionConfig", "SessionManager", "ExecutionReport",
    "ProjectContext", "ProjectIndexer",
]
