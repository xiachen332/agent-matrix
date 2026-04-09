"""文档解析模块测试"""

import pytest
from pathlib import Path
import tempfile
import os

from agent_matrix.document import (
    DocumentParser,
    PDFParser,
    WordParser,
    DocumentService,
    get_document_service,
    parse_document,
    parse_documents,
)


class TestDocumentParser:
    """测试文档解析器基类"""

    def test_pdf_parser_supported_extensions(self):
        parser = PDFParser()
        assert ".pdf" in parser.supported_extensions

    def test_word_parser_supported_extensions(self):
        parser = WordParser()
        assert ".docx" in parser.supported_extensions

    def test_can_parse_pdf(self):
        parser = PDFParser()
        assert parser.can_parse("test.pdf")
        assert not parser.can_parse("test.docx")

    def test_can_parse_word(self):
        parser = WordParser()
        assert parser.can_parse("test.docx")
        assert not parser.can_parse("test.pdf")


class TestDocumentService:
    """测试文档服务"""

    def test_supported_extensions(self):
        service = DocumentService()
        extensions = service.supported_extensions
        assert ".pdf" in extensions
        assert ".docx" in extensions

    def test_supported_formats(self):
        service = DocumentService()
        formats = service.supported_formats()
        assert "*.pdf" in formats
        assert "*.docx" in formats

    def test_parse_nonexistent_file(self):
        service = DocumentService()
        with pytest.raises(FileNotFoundError):
            service.parse("nonexistent.pdf")

    def test_parse_unsupported_format(self):
        service = DocumentService()
        with pytest.raises(ValueError) as exc_info:
            service.parse("test.txt")
        assert "不支持" in str(exc_info.value)


class TestPDFParser:
    """测试 PDF 解析"""

    def test_parse_pdf_basic(self, tmp_path):
        # 创建临时 PDF 文件
        pdf_path = tmp_path / "test.pdf"
        # 简单的 PDF 内容（实际测试需要真实 PDF）
        # 这里测试文件不存在的情况
        parser = PDFParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(str(pdf_path))


class TestWordParser:
    """测试 Word 文档解析"""

    def test_parse_docx_nonexistent(self, tmp_path):
        parser = WordParser()
        docx_path = tmp_path / "test.docx"
        with pytest.raises(FileNotFoundError):
            parser.parse(str(docx_path))


class TestGlobalFunctions:
    """测试全局函数"""

    def test_get_document_service_singleton(self):
        service1 = get_document_service()
        service2 = get_document_service()
        assert service1 is service2

    def test_parse_document_helper(self):
        # 测试不存在的文件会抛出正确的异常
        with pytest.raises(FileNotFoundError):
            parse_document("nonexistent.pdf")


class TestIntegration:
    """集成测试"""

    def test_document_service_and_parsers(self):
        """测试文档服务与解析器的协作"""
        service = DocumentService()

        # 测试不支持的格式
        with pytest.raises(ValueError):
            service.parse("test.txt")

        # 验证支持的扩展名
        assert service.can_parse("test.pdf")
        assert service.can_parse("test.docx")
        assert not service.can_parse("test.txt")
