from __future__ import annotations

import posixpath


class GoImportResolver:
    """Resolves Go import paths to internal package directories or external packages (§8.8)."""

    STD_PACKAGES = {
        "archive",
        "bufio",
        "bytes",
        "compress",
        "container",
        "context",
        "crypto",
        "database",
        "debug",
        "encoding",
        "errors",
        "expvar",
        "flag",
        "fmt",
        "go",
        "hash",
        "html",
        "image",
        "index",
        "io",
        "log",
        "math",
        "mime",
        "net",
        "os",
        "path",
        "plugin",
        "reflect",
        "regexp",
        "runtime",
        "sort",
        "strconv",
        "strings",
        "sync",
        "syscall",
        "testing",
        "text",
        "time",
        "unicode",
        "unsafe",
    }

    def resolve(
        self,
        source_path: str,
        raw_import: str,
        all_project_files: set[str],
        **kwargs: str,
    ) -> str:
        _ = source_path
        """Resolves Go import path.

        Examples:
            - 'fmt' -> 'ext:fmt'
            - 'net/http' -> 'ext:net/http'
            - 'github.com/gorilla/mux' -> 'ext:github.com/gorilla/mux'
            - 'taskflow/services/reminder' -> 'services/reminder-worker'
        """
        spec = raw_import.strip().strip('"').strip("'")
        if not spec:
            return "ext:unknown"

        # Standard library package
        first_segment = spec.split("/")[0]
        if first_segment in self.STD_PACKAGES:
            return f"ext:{spec}"

        module_name = kwargs.get("go_module", "").strip()

        # In-module relative import: e.g. "taskflow/scheduler" where module is "taskflow"
        if module_name and spec.startswith(module_name):
            sub_path = spec[len(module_name) :].lstrip("/")
            # Check if any .go file in project exists under this directory
            for f in all_project_files:
                if f.endswith(".go") and (sub_path in f or posixpath.dirname(f).endswith(sub_path)):
                    return posixpath.dirname(f)

        # Direct directory check: does any .go file exist whose directory matches the spec suffix?
        last_pkg = spec.split("/")[-1]
        matching_dirs = {
            posixpath.dirname(f)
            for f in all_project_files
            if f.endswith(".go") and posixpath.dirname(f).endswith(last_pkg)
        }
        if len(matching_dirs) == 1:
            return next(iter(matching_dirs))

        # External package
        return f"ext:{spec}"
