from __future__ import annotations

from app.services.graph.resolvers import (
    GoImportResolver,
    JavaImportResolver,
    JavaScriptImportResolver,
    PythonImportResolver,
    get_import_resolver,
)


def test_python_resolver_relative_and_external():
    project_files = {
        "app/main.py",
        "app/utils.py",
        "app/core/config.py",
        "app/api/v1/repos.py",
        "src/core/app.py",
    }
    resolver = PythonImportResolver()

    # Relative same dir
    res = resolver.resolve("app/main.py", ".utils", project_files)
    assert res == "app/utils.py"

    # Relative parent dir
    res = resolver.resolve("app/api/v1/repos.py", "...core.config", project_files)
    assert res == "app/core/config.py"

    # Absolute within package
    res = resolver.resolve("app/main.py", "app.core.config", project_files)
    assert res == "app/core/config.py"

    # Standard library
    res = resolver.resolve("app/main.py", "os", project_files)
    assert res == "ext:os"
    res = resolver.resolve("app/main.py", "sys", project_files)
    assert res == "ext:sys"

    # External third-party package
    res = resolver.resolve("app/main.py", "fastapi", project_files)
    assert res == "ext:fastapi"
    res = resolver.resolve("app/main.py", "pydantic.v1", project_files)
    assert res == "ext:pydantic"


def test_javascript_resolver_relative_aliases_and_external():
    project_files = {
        "src/components/Button.tsx",
        "src/components/Form.tsx",
        "src/utils/index.ts",
        "src/App.tsx",
    }
    resolver = JavaScriptImportResolver()

    # Relative same dir with extension inference (.tsx)
    res = resolver.resolve("src/components/Form.tsx", "./Button", project_files)
    assert res == "src/components/Button.tsx"

    # Relative to index file
    res = resolver.resolve("src/App.tsx", "./utils", project_files)
    assert res == "src/utils/index.ts"

    # Path alias @/*
    res = resolver.resolve("src/App.tsx", "@/components/Button", project_files)
    assert res == "src/components/Button.tsx"

    # External scoped package
    res = resolver.resolve("src/App.tsx", "@radix-ui/react-dialog", project_files)
    assert res == "ext:@radix-ui/react-dialog"

    # External standard package
    res = resolver.resolve("src/App.tsx", "react", project_files)
    assert res == "ext:react"


def test_java_resolver_internal_and_external():
    project_files = {
        "src/main/java/com/example/demo/Application.java",
        "src/main/java/com/example/demo/service/UserService.java",
        "src/main/java/com/example/demo/repository/UserRepository.java",
    }
    resolver = JavaImportResolver()

    # Internal class import
    res = resolver.resolve(
        "src/main/java/com/example/demo/Application.java",
        "com.example.demo.service.UserService",
        project_files,
    )
    assert res == "src/main/java/com/example/demo/service/UserService.java"

    # Wildcard package import
    res = resolver.resolve(
        "src/main/java/com/example/demo/Application.java",
        "com.example.demo.repository.*",
        project_files,
    )
    assert res == "src/main/java/com/example/demo/repository"

    # External library import
    res = resolver.resolve(
        "src/main/java/com/example/demo/Application.java",
        "org.springframework.boot.SpringApplication",
        project_files,
    )
    assert res == "ext:org.springframework"


def test_go_resolver_stdlib_internal_and_external():
    project_files = {
        "main.go",
        "pkg/server/server.go",
        "pkg/models/user.go",
    }
    resolver = GoImportResolver()

    # Standard library
    res = resolver.resolve("main.go", "fmt", project_files)
    assert res == "ext:fmt"
    res = resolver.resolve("main.go", "net/http", project_files)
    assert res == "ext:net/http"

    # Internal module with go_module prefix
    res = resolver.resolve(
        "main.go",
        "github.com/example/myrepo/pkg/server",
        project_files,
        go_module="github.com/example/myrepo",
    )
    assert res == "pkg/server"

    # External package
    res = resolver.resolve("main.go", "github.com/gin-gonic/gin", project_files)
    assert res == "ext:github.com/gin-gonic/gin"


def test_resolver_factory():
    assert isinstance(get_import_resolver("python"), PythonImportResolver)
    assert isinstance(get_import_resolver("typescript"), JavaScriptImportResolver)
    assert isinstance(get_import_resolver("javascript"), JavaScriptImportResolver)
    assert isinstance(get_import_resolver("java"), JavaImportResolver)
    assert isinstance(get_import_resolver("go"), GoImportResolver)
    assert get_import_resolver("brainfuck") is None
