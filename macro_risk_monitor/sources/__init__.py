"""Data source adapters with a uniform fetch interface."""

from .base import DataSource, FetchError, SourceUnavailable
from .registry import get_source

__all__ = ["DataSource", "FetchError", "SourceUnavailable", "get_source"]
