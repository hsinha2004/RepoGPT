from __future__ import annotations

import posixpath


class JavaImportResolver:
    """Resolves Java import statements to project files or package nodes (§8.8)."""

    def resolve(
        self,
        source_path: str,
        raw_import: str,
        all_project_files: set[str],
        **_kwargs: str,
    ) -> str:
        _ = source_path
        """Resolves Java import to internal path or ext:<pkg>.

        Examples:
            - 'com.taskflow.report.CsvExporter' -> 'tools/report/CsvExporter.java' or 'src/main/java/.../CsvExporter.java'
            - 'java.util.List' -> 'ext:java.util'
            - 'org.springframework.boot.*' -> 'ext:org.springframework.boot'
        """
        spec = raw_import.strip().rstrip(";")
        if not spec:
            return "ext:unknown"

        # Check standard Java / Android packages
        if spec.startswith(("java.", "javax.", "jakarta.", "android.")):
            parts = spec.split(".")
            pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
            return f"ext:{pkg}"

        # 1. Wildcard import e.g. "com.example.service.*"
        is_wildcard = spec.endswith(".*")
        clean_spec = spec[:-2] if is_wildcard else spec

        parts = clean_spec.split(".")
        if not parts:
            return "ext:unknown"

        # If it's a specific class import: last part is class name
        class_name = parts[-1]
        rel_class_path = posixpath.join(*parts) + ".java"

        # Direct search: do any project files end with this full package path?
        for f in all_project_files:
            if f.endswith(rel_class_path):
                return f

        # If not matched by full package path, match by ClassName.java
        target_file = f"{class_name}.java"
        matches = [
            f for f in all_project_files if f.endswith(f"/{target_file}") or f == target_file
        ]
        if len(matches) == 1:
            return matches[0]

        # If wildcard or package, check for package directory
        pkg_dir = posixpath.join(*parts)
        for f in all_project_files:
            if pkg_dir in f:
                return posixpath.dirname(f)

        # Unresolved -> external package
        top_pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        return f"ext:{top_pkg}"
