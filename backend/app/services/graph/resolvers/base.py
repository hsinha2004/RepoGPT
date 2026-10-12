from __future__ import annotations

from typing import Protocol


class ImportResolver(Protocol):
    """Protocol for language-specific import path resolvers (§8.8)."""

    def resolve(
        self,
        source_path: str,
        raw_import: str,
        all_project_files: set[str],
        **kwargs: str,
    ) -> str:
        """Resolves a raw import specifier to a project-relative file path or an external package.

        Returns:
            - A normalized internal path relative to repo root (e.g., 'backend/app/db.py')
            - Or 'ext:<package_name>' for external dependencies (e.g., 'ext:fastapi')
        """
        ...
