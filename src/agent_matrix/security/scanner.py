"""安全扫描器 - 集成 bandit 进行代码安全扫描"""

from __future__ import annotations
import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Severity(Enum):
    """漏洞严重等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Vulnerability:
    """安全漏洞数据类"""
    severity: Severity
    location: str  # 文件路径:行号
    description: str
    fix: str  # 修复建议
    test_id: Optional[str] = None  # bandit 测试 ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "location": self.location,
            "description": self.description,
            "fix": self.fix,
            "test_id": self.test_id,
        }


class SecurityScanner:
    """安全扫描器 - 集成 bandit"""

    def __init__(self, project_root: Optional[Path] = None):
        """初始化扫描器

        Args:
            project_root: 项目根目录，默认为当前目录
        """
        self.project_root = project_root or Path.cwd()

    def scan_file(self, file_path: str | Path) -> List[Vulnerability]:
        """扫描单个文件

        Args:
            file_path: 文件路径

        Returns:
            漏洞列表
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        # 使用 bandit 扫描
        result = self._run_bandit(file_path)
        return self._parse_bandit_result(result, str(file_path))

    def scan_directory(self, dir_path: str | Path) -> List[Vulnerability]:
        """扫描目录

        Args:
            dir_path: 目录路径

        Returns:
            漏洞列表
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return []

        result = self._run_bandit(dir_path)
        return self._parse_bandit_result(result, str(dir_path))

    def _run_bandit(self, target: Path) -> Dict[str, Any]:
        """运行 bandit 扫描

        Args:
            target: 扫描目标（文件或目录）

        Returns:
            bandit JSON 输出
        """
        try:
            # 构建 bandit 命令
            cmd = [
                "bandit",
                "-r",  # 递归扫描
                "-f", "json",  # JSON 格式输出
                "-ll",  # 只显示 MEDIUM 及以上级别
                str(target),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=120,
            )

            if result.returncode in (0, 1):
                # 0 = 无问题, 1 = 发现问题
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"results": [], "errors": []}
            else:
                return {"results": [], "errors": [result.stderr]}

        except FileNotFoundError:
            # bandit 未安装
            return {
                "results": [],
                "errors": ["bandit 未安装，请运行: pip install bandit"]
            }
        except subprocess.TimeoutExpired:
            return {
                "results": [],
                "errors": ["bandit 扫描超时"]
            }
        except Exception as e:
            return {
                "results": [],
                "errors": [str(e)]
            }

    def _parse_bandit_result(
        self, result: Dict[str, Any], target: str
    ) -> List[Vulnerability]:
        """解析 bandit 输出

        Args:
            result: bandit JSON 输出
            target: 扫描目标

        Returns:
            漏洞列表
        """
        vulnerabilities = []

        for item in result.get("results", []):
            # 确定严重等级
            severity_str = item.get("issue_severity", "MEDIUM").upper()
            try:
                severity = Severity[severity_str]
            except KeyError:
                severity = Severity.MEDIUM

            # 提取位置
            filename = item.get("filename", "")
            line_no = item.get("line_number", 0)
            location = f"{filename}:{line_no}" if line_no else filename

            # 构建漏洞对象
            vuln = Vulnerability(
                severity=severity,
                location=location,
                description=item.get("issue_text", ""),
                fix=self._get_fix_suggestion(item),
                test_id=item.get("test_id"),
            )
            vulnerabilities.append(vuln)

        return vulnerabilities

    def _get_fix_suggestion(self, item: Dict[str, Any]) -> str:
        """获取修复建议

        Args:
            item: bandit 结果项

        Returns:
            修复建议
        """
        test_id = item.get("test_id", "")

        # 针对常见问题的修复建议
        suggestions = {
            "B101": "使用刻意的默认值，而不是直接断言。考虑使用 pytest.fail() 或明确的条件检查。",
            "B102": "避免使用 shell=True，这可能导致 shell 注入攻击。",
            "B103": "避免设置允许不安全操作的权限，使用更严格的权限模式。",
            "B104": "避免使用 hardcoded 密码或密钥，使用环境变量或配置管理。",
            "B105": "避免在代码中 hardcode 密码，使用环境变量或配置文件。",
            "B106": "避免使用弱加密算法（如 DES），使用更安全的算法如 AES。",
            "B107": "避免使用空的密码，应使用强密码或密钥。",
            "B108": "避免在代码中 hardcode 密钥，使用环境变量或密钥管理服务。",
            "B112": "避免忽略异常处理，使用 try-except 块并记录错误。",
            "B301": "避免使用已弃用的方法，检查 Python 文档获取替代方案。",
            "B302": "避免使用 marshal 加载不可信数据，使用 json 或其他安全方法。",
            "B303": "避免使用 MD5 或 SHA1 进行哈希，使用更安全的哈希算法。",
            "B304": "避免使用 cPickle 加载不可信数据，使用 json 或其他安全方法。",
            "B305": "避免使用 crypt()，使用更安全的密码哈希方法如 bcrypt。",
            "B306": "避免使用 mktemp()，使用 tempfile.mkstemp() 或其他安全方法。",
            "B307": "避免使用 eval()，使用 ast.literal_eval() 或其他安全方法。",
            "B308": "避免使用 mark_safe()，除非完全信任输入。",
            "B309": "避免使用允许连接任意主机的 URL，使用白名单。",
            "B310": "避免使用允许访问任意 URL 的功能，使用白名单验证。",
            "B311": "避免使用随机数生成器生成安全关键的随机数，使用 secrets 模块。",
            "B312": "避免忽略 HTTP 头中的敏感信息，确保正确处理。",
            "B313": "避免在 HTTP 请求中忽略证书验证，使用 verify=True。",
            "B314": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B315": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B316": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B317": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B318": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B319": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B320": "避免使用 XML 解析处理不可信数据，使用 defusedxml。",
            "B321": "避免导入或使用可疑模块，确保只使用可信模块。",
            "B322": "避免使用 goto 语句，重构代码以消除 goto 的使用。",
            "B323": "避免使用未经验证的输入，确保所有输入都经过验证。",
            "B324": "避免使用哈希存储密码，使用 bcrypt 或其他专用密码哈希算法。",
            "B325": "避免使用 tempfile 创建不安全临时文件，使用 NamedTemporaryFile。",
            "B401": "避免使用不安全的加密算法，使用更安全的加密方法。",
            "B402": "避免使用不安全的 SSL/TLS 配置，使用安全的配置。",
            "B403": "避免使用不安全的序列化方法，使用安全的序列化方法。",
            "B404": "避免导入可疑模块，确保只使用可信模块。",
            "B405": "避免导入可疑模块，确保只使用可信模块。",
            "B406": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B407": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B408": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B409": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B410": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B411": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B412": "避免使用可疑的安全相关操作，确保操作是安全的。",
            "B413": "避免使用禁止的加密算法，使用更安全的加密方法。",
            "B501": "避免使用不安全的配置，确保配置是安全的。",
            "B502": "避免使用不安全的 SSL/TLS 配置，使用安全的配置。",
            "B503": "避免使用不安全的 SSL/TLS 配置，使用安全的配置。",
            "B504": "避免使用不安全的 SSL/TLS 配置，使用安全的配置。",
            "B505": "避免使用不安全的 SSL/TLS 配置，使用安全的配置。",
            "B506": "避免使用不安全的配置，确保配置是安全的。",
            "B507": "避免使用不安全的 SSH 配置，使用安全的配置。",
            "B508": "避免使用不安全的配置，确保配置是安全的。",
            "B601": "避免使用不安全的 SQL 操作，使用参数化查询。",
            "B602": "避免使用不安全的 subprocess 操作，确保输入是安全的。",
            "B603": "避免使用不安全的 subprocess 操作，确保输入是安全的。",
            "B604": "避免使用不安全的 subprocess 操作，确保输入是安全的。",
            "B605": "避免使用不安全的 shell 操作，使用 shell=False。",
            "B606": "避免使用不安全的 subprocess 操作，使用 shell=False。",
            "B607": "避免使用不安全的 subprocess 操作，确保路径是安全的。",
            "B608": "避免使用不安全的 SQL 操作，使用参数化查询。",
            "B701": "避免使用不安全的 XSS 操作，使用适当的转义或框架的 XSS 保护。",
            "B702": "避免使用不安全的 XSS 操作，使用适当的转义或框架的 XSS 保护。",
            "B703": "避免使用不安全的 XSS 操作，使用适当的转义或框架的 XSS 保护。",
        }

        return suggestions.get(test_id, "查看 https://bandit.readthedocs.io 获取详细信息。")

    def scan_code_content(self, code: str, filename: str = "test.py") -> List[Vulnerability]:
        """扫描代码内容（不依赖文件）

        Args:
            code: 代码内容
            filename: 文件名（用于显示）

        Returns:
            漏洞列表
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # 扫描临时文件
            result = self._run_bandit(Path(temp_path))
            return self._parse_bandit_result(result, filename)
        finally:
            # 删除临时文件
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
