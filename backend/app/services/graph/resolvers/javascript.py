from __future__ import annotations

import posixpath


class JavaScriptImportResolver:
    """Resolves JavaScript and TypeScript import specifiers (§8.8)."""

    EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
    INDEX_FILES = (
        "index.ts",
        "index.tsx",
        "index.js",
        "index.jsx",
        "index.mjs",
        "index.cjs",
    )

    def resolve(
        self,
        source_path: str,
        raw_import: str,
        all_project_files: set[str],
        **_kwargs: str,
    ) -> str:
        """Resolves JS/TS import to internal project file or ext:<package>.

        Examples:
            - './api/tasks' from 'frontend/src/pages/TasksPage.tsx' -> 'frontend/src/api/tasks.ts'
            - '@/components/Button' -> 'src/components/Button.tsx' or 'frontend/src/components/Button.tsx'
            - 'react' -> 'ext:react'
            - '@tanstack/react-query' -> 'ext:@tanstack/react-query'
        """
        spec = raw_import.strip()
        if not spec:
            return "ext:unknown"

        # 1. Relative imports starting with ./ or ../
        if spec.startswith("./") or spec.startswith("../"):
            source_dir = posixpath.dirname(source_path)
            candidate_base = posixpath.normpath(posixpath.join(source_dir, spec))
            matched = self._match_file_candidate(candidate_base, all_project_files)
            if matched:
                return matched
            return f"ext:{spec}"

        # 2. Path aliases (e.g. "@/..." or "~/...")
        if spec.startswith("@/") or spec.startswith("~/"):
            suffix = spec[2:]
            # Search under common src directories
            for prefix in ("src", "frontend/src", "client/src", "app", ""):
                candidate = posixpath.normpath(posixpath.join(prefix, suffix))
                matched = self._match_file_candidate(candidate, all_project_files)
                if matched:
                    return matched

        # 3. Non-relative imports could be internal if project has baseUrl (e.g. "components/...")
        for root in ("src", "frontend/src", "client/src", ""):
            if root:
                candidate = posixpath.normpath(posixpath.join(root, spec))
                matched = self._match_file_candidate(candidate, all_project_files)
                if matched:
                    return matched

        # 4. Bare specifier -> external package
        # Preserve scoped packages: e.g. "@radix-ui/react-dialog" or "lucide-react"
        parts = spec.split("/")
        if spec.startswith("@") and len(parts) >= 2:
            pkg_name = f"{parts[0]}/{parts[1]}"
        else:
            pkg_name = parts[0]

        return f"ext:{pkg_name}"

    def _match_file_candidate(self, candidate_base: str, all_files: set[str]) -> str | None:
        """Checks exact match, extension additions, and index files."""
        # Exact match
        if candidate_base in all_files:
            return candidate_base

        # Extension additions
        for ext in self.EXTENSIONS:
            cand = f"{candidate_base}{ext}"
            if cand in all_files:
                return cand

        # Index files in directory
        for idx in self.INDEX_FILES:
            cand = posixpath.join(candidate_base, idx)
            if cand in all_files:
                return cand

        return None
