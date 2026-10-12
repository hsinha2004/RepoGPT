from __future__ import annotations

import posixpath
from pathlib import PurePosixPath


class PythonImportResolver:
    """Resolves Python import statements to internal project files or external modules (§8.8)."""

    def resolve(
        self,
        source_path: str,
        raw_import: str,
        all_project_files: set[str],
        **_kwargs: str,
    ) -> str:
        """Resolves Python import to repo file path or ext:<pkg>.

        Examples:
            - 'app.db' -> 'backend/app/db.py' or 'app/db.py'
            - '.service' (from 'app/tasks/routes.py') -> 'app/tasks/service.py'
            - 'fastapi' -> 'ext:fastapi'
        """
        import_str = raw_import.strip()
        if not import_str:
            return "ext:unknown"

        # 1. Handle relative imports: leading dots
        if import_str.startswith("."):
            dot_count = 0
            while dot_count < len(import_str) and import_str[dot_count] == ".":
                dot_count += 1

            sub_path = import_str[dot_count:].strip()
            # Directory of the current source file
            source_dir = posixpath.dirname(source_path)

            # Move up (dot_count - 1) directories
            target_dir = source_dir
            for _ in range(dot_count - 1):
                parent = posixpath.dirname(target_dir)
                if parent == target_dir or parent == "":
                    break
                target_dir = parent

            if sub_path:
                rel_parts = sub_path.split(".")
                candidate_rel = posixpath.join(target_dir, *rel_parts)
            else:
                candidate_rel = target_dir

            # Check if candidate_rel is a file or package directory
            resolved = self._match_file_candidate(candidate_rel, all_project_files)
            if resolved:
                return resolved

            # If it could not be resolved, fallback to external or directory
            return f"ext:{import_str}"

        # 2. Handle absolute imports
        parts = import_str.split(".")
        top_level = parts[0]

        # Convert dotted module path to file system path components: e.g. "app.auth.security" -> "app/auth/security"
        rel_path = posixpath.join(*parts)

        # Check directly from repo root
        direct = self._match_file_candidate(rel_path, all_project_files)
        if direct:
            return direct

        # Search across potential package roots (src/, backend/, app/, etc.)
        package_roots = self._find_package_roots(all_project_files)
        for root in package_roots:
            candidate = posixpath.join(root, rel_path) if root else rel_path
            matched = self._match_file_candidate(candidate, all_project_files)
            if matched:
                return matched

        # If unresolved against project files, it is an external dependency
        return f"ext:{top_level}"

    def _match_file_candidate(self, candidate_base: str, all_files: set[str]) -> str | None:
        """Checks if candidate_base matches .py, .pyi, /__init__.py, or is an exact match."""
        # Exact file match (e.g. if already has extension)
        if candidate_base in all_files:
            return candidate_base

        # Standard .py extension
        as_py = f"{candidate_base}.py"
        if as_py in all_files:
            return as_py

        # Package __init__.py
        as_pkg = posixpath.join(candidate_base, "__init__.py")
        if as_pkg in all_files:
            return as_pkg

        # Stub .pyi
        as_pyi = f"{candidate_base}.pyi"
        if as_pyi in all_files:
            return as_pyi

        return None

    def _find_package_roots(self, all_files: set[str]) -> list[str]:
        """Discovers common package root directories in the project."""
        roots: set[str] = {""}
        for f in all_files:
            p = PurePosixPath(f)
            # Check for directories containing __init__.py or common root conventions (src, backend, lib)
            if p.name == "__init__.py":
                # The parent's parent can be a package root
                parent = str(p.parent)
                roots.add(parent)
                grandparent = str(p.parent.parent) if p.parent.parent != PurePosixPath(".") else ""
                roots.add(grandparent)

            # Common container directories
            parts = p.parts
            if len(parts) > 1:
                if parts[0] in ("src", "backend", "lib", "packages", "apps", "server"):
                    roots.add(parts[0])
                if len(parts) > 2 and parts[0] in ("src", "backend") and parts[1] == "src":
                    roots.add(posixpath.join(parts[0], parts[1]))

        return sorted(roots, key=lambda r: len(r), reverse=True)
