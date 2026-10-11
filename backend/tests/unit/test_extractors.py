"""
Unit tests for ParserRegistry and language extractors (§8.4).
Verifies extraction of symbols, signatures, docstrings, imports, line ranges, and entry points.
"""

from app.services.parsing.extractors.config import ConfigExtractor
from app.services.parsing.extractors.docs import DocsExtractor
from app.services.parsing.extractors.go import GoExtractor
from app.services.parsing.extractors.java import JavaExtractor
from app.services.parsing.extractors.javascript import JavascriptExtractor
from app.services.parsing.extractors.python import PythonExtractor
from app.services.parsing.extractors.typescript import TypescriptExtractor
from app.services.parsing.registry import ParserRegistry


def test_python_extractor():
    code = '''"""Module level docstring."""
import os
from datetime import datetime

@app.get("/items/{item_id}")
async def get_item(item_id: int) -> dict:
    """Retrieve an item by ID."""
    return {"id": item_id}

class ItemService:
    """Service managing items."""
    def __init__(self, db_client):
        self.db = db_client

    def find_all(self) -> list:
        return []

if __name__ == "__main__":
    main()
'''
    ext = PythonExtractor()
    parsed = ext.extract(code, path="app/services/item.py")

    assert parsed.language == "python"
    assert parsed.module_docstring == "Module level docstring."
    assert "os" in parsed.imports
    assert "datetime" in parsed.imports

    names = {s.name: s for s in parsed.symbols}
    assert "get_item" in names
    assert names["get_item"].kind == "function"
    assert names["get_item"].docstring == "Retrieve an item by ID."
    assert "ItemService" in names
    assert names["ItemService"].kind == "class"
    assert "find_all" in names
    assert names["find_all"].kind == "method"
    assert names["find_all"].parent == "ItemService"

    # Line ranges: 1-based inclusive
    assert names["get_item"].start_line >= 5
    assert names["get_item"].end_line >= names["get_item"].start_line

    # Route hints and main entry point hints
    reasons = [h.reason for h in parsed.entry_point_hints]
    assert any("Route handler" in r for r in reasons)
    assert any("__main__" in r for r in reasons)
    assert len(parsed.card) > 0


def test_javascript_extractor():
    code = """import express from 'express';
const path = require('path');

const app = express();
app.get('/api/users', (req, res) => res.json([]));

/**
 * Returns greeting for user
 */
function greet(name) {
    return "Hello " + name;
}

export const Header = () => {
    return <header className="p-4"><h1>Title</h1></header>;
};
"""
    ext = JavascriptExtractor()
    parsed = ext.extract(code, path="src/server.jsx")

    assert "express" in parsed.imports
    assert "path" in parsed.imports

    names = {s.name: s for s in parsed.symbols}
    assert "greet" in names
    assert names["greet"].kind == "function"
    assert "Header" in names
    assert names["Header"].kind == "component"

    # Route registration hint
    reasons = [h.reason for h in parsed.entry_point_hints]
    assert any("app.get" in r for r in reasons)


def test_typescript_extractor():
    code = """import { useState } from 'react';

export interface UserDTO {
    id: string;
    email: string;
}

export type Status = 'active' | 'inactive';

export enum Role {
    Admin = 'ADMIN',
    User = 'USER',
}

export class UserManager {
    async getUser(id: string): Promise<UserDTO | null> {
        return null;
    }
}
"""
    ext = TypescriptExtractor()
    parsed = ext.extract(code, path="src/types.ts")

    assert parsed.language == "typescript"
    names = {s.name: s for s in parsed.symbols}
    assert "UserDTO" in names
    assert names["UserDTO"].kind == "interface"
    assert "Status" in names
    assert names["Status"].kind == "type"
    assert "Role" in names
    assert names["Role"].kind == "enum"
    assert "UserManager" in names
    assert names["UserManager"].kind == "class"
    assert "getUser" in names
    assert names["getUser"].kind == "method"


def test_java_extractor():
    code = """package com.example.demo;

import java.util.List;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;

@RestController
public class UserController {
    @GetMapping("/users")
    public List<String> listUsers() {
        return List.of();
    }

    public static void main(String[] args) {
        SpringApplication.run(UserController.class, args);
    }
}
"""
    ext = JavaExtractor()
    parsed = ext.extract(code, path="src/main/java/UserController.java")

    assert parsed.language == "java"
    assert "java.util.List" in parsed.imports
    names = {s.name: s for s in parsed.symbols}
    assert "UserController" in names
    assert names["UserController"].kind == "class"
    assert "listUsers" in names
    assert names["listUsers"].kind == "method"

    reasons = [h.reason for h in parsed.entry_point_hints]
    assert any("public static void main" in r for r in reasons)
    assert any("Spring" in r for r in reasons)


def test_go_extractor():
    code = """package main

import (
    "fmt"
    "net/http"
)

type ServerConfig struct {
    Port int
}

type Handler interface {
    ServeHTTP(w http.ResponseWriter, r *http.Request)
}

func (s *ServerConfig) Address() string {
    return fmt.Sprintf(":%d", s.Port)
}

func main() {
    fmt.Println("Starting")
}
"""
    ext = GoExtractor()
    parsed = ext.extract(code, path="cmd/server/main.go")

    assert parsed.language == "go"
    assert "fmt" in parsed.imports
    assert "net/http" in parsed.imports

    names = {s.name: s for s in parsed.symbols}
    assert "ServerConfig" in names
    assert names["ServerConfig"].kind == "struct"
    assert "Handler" in names
    assert names["Handler"].kind == "interface"
    assert "Address" in names
    assert names["Address"].kind == "method"
    assert names["Address"].parent == "ServerConfig"
    assert "main" in names
    assert names["main"].kind == "function"

    reasons = [h.reason for h in parsed.entry_point_hints]
    assert any("package main; func main()" in r for r in reasons)


def test_docs_extractor():
    markdown = """# Architecture Overview

RepoGPT uses a multi-index hybrid retrieval approach.

## Data Ingestion
Files are filtered and parsed into AST symbols.

### Redaction
Credentials are redacted prior to chunking.
"""
    ext = DocsExtractor()
    parsed = ext.extract(markdown, path="docs/architecture.md")

    assert parsed.language == "markdown"
    assert len(parsed.symbols) == 3
    names = [s.name for s in parsed.symbols]
    assert "Architecture Overview" in names
    assert "Data Ingestion" in names
    assert "Redaction" in names


def test_config_extractor():
    dockerfile = """FROM python:3.13-slim
WORKDIR /app
COPY . .
ENTRYPOINT ["uvicorn", "app.main:app"]
"""
    ext = ConfigExtractor()
    parsed = ext.extract(dockerfile, path="Dockerfile")

    assert "python:3.13-slim" in parsed.imports
    reasons = [h.reason for h in parsed.entry_point_hints]
    assert any("ENTRYPOINT" in r for r in reasons)


def test_parser_registry_fallback_on_error():
    registry = ParserRegistry()
    # Invalid syntax or binary-like text routed to fallback
    res = registry.parse_file("random unknown syntax: $$$", path="unsupported.xyz")
    assert res.language == "generic"
    assert len(res.symbols) > 0
