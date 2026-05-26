"""Report rendering: markdown -> HTML -> (optional) PDF, plus matplotlib charts."""

from .html import render_report
from .markdown import write_raw_markdown
from .pdf import html_to_pdf

__all__ = ["render_report", "write_raw_markdown", "html_to_pdf"]
