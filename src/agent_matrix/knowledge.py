"""项目知识库 - 项目上下文索引与检索"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


# 支持的代码文件扩展名
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h"}


# Python import 提取正则
PYTHON_IMPORT_PATTERN = re.compile(
    r'^(?:from\s+(\S+)\s+import|import\s+(\S+))',
    re.MULTILINE
)


@dataclass
class ProjectContext:
    """项目上下文"""
    root: str  # 项目根目录
    file_tree: Dict[str, List[str]] = field(default_factory=dict)  # dir -> [files]
    key_modules: List[str] = field(default_factory=list)  # 关键模块列表
    import_graph: Dict[str, Set[str]] = field(default_factory=dict)  # module -> dependencies


class ProjectIndexer:
    """项目索引器

    索引项目目录，提取文件结构和 import 关系。
    """

    def __init__(self, root: Optional[str] = None):
        """初始化索引器

        Args:
            root: 项目根目录路径
        """
        self._root: Optional[Path] = Path(root) if root else None
        self._context: Optional[ProjectContext] = None

    @property
    def root(self) -> Optional[Path]:
        return self._root

    @property
    def context(self) -> Optional[ProjectContext]:
        return self._context

    def set_root(self, path: str) -> ProjectContext:
        """设置项目根目录并索引

        Args:
            path: 项目根目录路径

        Returns:
            项目上下文
        """
        self._root = Path(path).expanduser().resolve()
        if not self._root.exists():
            raise ValueError(f"目录不存在: {self._root}")
        if not self._root.is_dir():
            raise ValueError(f"路径不是目录: {self._root}")

        self._context = self._index_project()
        return self._context

    def _index_project(self) -> ProjectContext:
        """索引项目"""
        context = ProjectContext(root=str(self._root))

        # 遍历项目文件
        for root, dirs, files in os.walk(self._root):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env',
                'build', 'dist', '.egg-info', '.git', '.hg', '.svn', 'target'
            }]

            rel_root = str(Path(root).relative_to(self._root))
            if rel_root == ".":
                rel_root = ""

            context.file_tree[rel_root] = sorted([
                f for f in files
                if not f.startswith('.') and (
                    Path(f).suffix in CODE_EXTENSIONS or
                    f in {"Makefile", "CMakeLists.txt", "setup.py", "pyproject.toml", "package.json"}
                )
            ])

        # 提取关键模块和 import 关系
        context.key_modules = self._extract_key_modules(context)
        context.import_graph = self._build_import_graph(context)

        return context

    def _extract_key_modules(self, context: ProjectContext) -> List[str]:
        """提取关键模块"""
        modules = []

        # Python 项目
        pyproject = self._root / "pyproject.toml"
        if pyproject.exists():
            modules.append("pyproject.toml")

        setup_py = self._root / "setup.py"
        if setup_py.exists():
            modules.append("setup.py")

        # 查找 src 目录
        src_dir = self._root / "src"
        if src_dir.exists():
            for item in src_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    modules.append(f"src/{item.name}")

        # 查找主入口文件
        for pattern in ["main.py", "app.py", "index.js", "main.js", "app.go"]:
            if (self._root / pattern).exists():
                modules.append(pattern)

        return modules

    def _build_import_graph(self, context: ProjectContext) -> Dict[str, Set[str]]:
        """构建 import 关系图"""
        graph: Dict[str, Set[str]] = {}

        # 遍历所有 Python 文件
        for root, dirs, files in os.walk(self._root):
            # 跳过非 Python 目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                '__pycache__', 'node_modules', 'venv', '.venv', 'env'
            }]

            for file in files:
                if Path(file).suffix != ".py":
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(self._root)
                module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')

                graph[module_name] = set()

                try:
                    content = file_path.read_text(encoding="utf-8")
                    for match in PYTHON_IMPORT_PATTERN.finditer(content):
                        imported = match.group(1) or match.group(2)
                        if imported:
                            # 清理模块名
                            base_module = imported.split('.')[0]
                            graph[module_name].add(base_module)
                except (UnicodeDecodeError, OSError):
                    pass

        return graph

    def get_file_tree_display(self) -> str:
        """获取文件树显示格式"""
        if not self._context:
            return "(未设置项目目录)"

        lines = []
        for dir_path in sorted(self._context.file_tree.keys()):
            files = self._context.file_tree[dir_path]
            if not files:
                continue

            if dir_path:
                lines.append(f"{dir_path}/")
                for f in files:
                    lines.append(f"  ├── {f}")
            else:
                for f in files:
                    lines.append(f"├── {f}")

        return "\n".join(lines) if lines else "(空)"

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        if not self._context:
            return "(未设置项目目录)"

        parts = [
            f"项目根目录: {self._context.root}",
            f"关键模块: {', '.join(self._context.key_modules) or '(无)'}",
            f"文件结构:\n{self.get_file_tree_display()}",
        ]

        if self._context.import_graph:
            parts.append(f"已索引 {len(self._context.import_graph)} 个模块的导入关系")

        return "\n\n".join(parts)
