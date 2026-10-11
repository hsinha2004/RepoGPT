"""
Chunking service package (§8.5).
"""

from app.services.chunking.chunker import CodeChunker, escape_source_delimiters

__all__ = ["CodeChunker", "escape_source_delimiters"]
