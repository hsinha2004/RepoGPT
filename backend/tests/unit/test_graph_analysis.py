from __future__ import annotations

from app.services.analysis.entry_points import EntryPointDetector
from app.services.analysis.reading_order import ReadingOrderGenerator
from app.services.analysis.tech_stack import TechStackDetector
from app.services.graph.analyzer import GraphAnalyzer
from app.services.graph.builder import GraphBuilder


def test_graph_builder_and_analyzer_metrics():
    files = [
        {
            "path": "app/main.py",
            "language": "python",
            "imports": [".api", ".core.config", "fastapi"],
            "loc": 100,
        },
        {
            "path": "app/api.py",
            "language": "python",
            "imports": [".services.user", ".core.config"],
            "loc": 150,
        },
        {
            "path": "app/services/user.py",
            "language": "python",
            "imports": ["..core.config", ".db.repo"],
            "loc": 200,
        },
        {
            "path": "app/db/repo.py",
            "language": "python",
            "imports": ["..core.config"],
            "loc": 80,
        },
        {
            "path": "app/core/config.py",
            "language": "python",
            "imports": [],
            "loc": 50,
        },
        {
            "path": "app/orphan.py",
            "language": "python",
            "imports": [],
            "loc": 20,
        },
    ]

    symbols_by_file = {
        "app/core/config.py": [{"name": "Settings", "kind": "class"}],
        "app/services/user.py": [{"name": "get_user", "kind": "function"}],
    }

    builder = GraphBuilder()
    edges = builder.build_edges(files, symbols_by_file=symbols_by_file)

    # Must contain import edges and external edges
    assert len(edges) > 0
    external_edges = [e for e in edges if e["target"] == "ext:fastapi"]
    assert len(external_edges) == 1

    all_paths = [f["path"] for f in files]
    analyzer = GraphAnalyzer(edges, all_paths)
    metrics = analyzer.compute_file_metrics()

    # Core config should have highest fan_in because all modules import it
    assert metrics["app/core/config.py"]["fan_in"] >= 4
    assert metrics["app/core/config.py"]["pagerank"] > 0

    # Orphan should have 0 fan_in and 0 fan_out
    assert metrics["app/orphan.py"]["fan_in"] == 0
    assert metrics["app/orphan.py"]["fan_out"] == 0
    assert metrics["app/orphan.py"]["is_orphan"] is True


def test_graph_analyzer_cycles_and_directory_aggregation():
    # Construct a cycle: A -> B -> C -> A
    edges = [
        {"source": "backend/a.py", "target": "backend/b.py", "type": "imports", "heuristic": False},
        {"source": "backend/b.py", "target": "backend/c.py", "type": "imports", "heuristic": False},
        {"source": "backend/c.py", "target": "backend/a.py", "type": "imports", "heuristic": False},
        {
            "source": "frontend/ui.ts",
            "target": "frontend/button.ts",
            "type": "imports",
            "heuristic": False,
        },
    ]
    files = ["backend/a.py", "backend/b.py", "backend/c.py", "frontend/ui.ts", "frontend/button.ts"]

    analyzer = GraphAnalyzer(edges, files)
    metrics = analyzer.compute_file_metrics()

    # Cycle detection
    assert metrics["backend/a.py"]["in_cycle"] is True
    assert metrics["backend/b.py"]["in_cycle"] is True
    assert metrics["backend/c.py"]["in_cycle"] is True
    assert metrics["frontend/ui.ts"]["in_cycle"] is False

    # Directory aggregation
    dir_view = analyzer.get_graph_view(level="directory")
    assert dir_view["level"] == "directory"
    node_ids = {n["id"] for n in dir_view["nodes"]}
    assert "backend" in node_ids
    assert "frontend" in node_ids


def test_tech_stack_detection():
    files = [
        {"path": "requirements.txt", "content": "fastapi==0.110.0\npymongo>=4.6\npytest\n"},
        {
            "path": "frontend/package.json",
            "content": '{"dependencies": {"react": "^19.0.0", "vite": "^5.0.0"}}',
        },
        {"path": "Dockerfile", "content": "FROM python:3.11-slim\n"},
    ]
    languages = {"python": 5000, "typescript": 3000}

    detector = TechStackDetector()
    stack = detector.detect(files, languages)

    names = {s["name"] for s in stack}
    assert "FastAPI" in names
    assert "React" in names
    assert "MongoDB / PyMongo" in names
    assert "pytest" in names
    assert "Vite" in names


def test_entry_point_detection():
    files = [
        {
            "path": "backend/app/main.py",
            "content": "from fastapi import FastAPI\napp = FastAPI()\nif __name__ == '__main__':\n    pass\n",
        },
        {
            "path": "cmd/server/main.go",
            "content": "package main\n\nfunc main() {\n}\n",
        },
        {
            "path": "frontend/src/main.tsx",
            "content": "import { createRoot } from 'react-dom/client';\ncreateRoot(document.getElementById('root')).render();\n",
        },
    ]

    detector = EntryPointDetector()
    entries = detector.detect(files)

    paths = {e["path"] for e in entries}
    assert "backend/app/main.py" in paths
    assert "cmd/server/main.go" in paths
    assert "frontend/src/main.tsx" in paths


def test_reading_order_generator():
    all_files = [
        "README.md",
        "docs/architecture.md",
        "backend/app/main.py",
        "backend/app/core/config.py",
        "backend/app/services/auth.py",
        "backend/app/db/mongo.py",
        "frontend/src/main.tsx",
        "docker-compose.yml",
    ]
    entry_points = [
        {"path": "backend/app/main.py", "kind": "app_factory", "description": "API factory"}
    ]
    file_metrics = {
        "backend/app/core/config.py": {"pagerank": 0.25, "fan_in": 12},
        "backend/app/db/mongo.py": {"pagerank": 0.18, "fan_in": 8},
        "backend/app/services/auth.py": {"pagerank": 0.10, "fan_in": 5},
    }
    edges = [
        {
            "source": "backend/app/main.py",
            "target": "backend/app/services/auth.py",
            "type": "imports",
        },
    ]

    generator = ReadingOrderGenerator()
    order = generator.generate(all_files, entry_points, file_metrics, edges)

    assert len(order) >= 4
    # Step 1 should be README.md
    assert order[0]["path"] == "README.md"
    # An entry point should follow
    step_paths = [s["path"] for s in order]
    assert "backend/app/main.py" in step_paths
    # High pagerank core should be included
    assert "backend/app/core/config.py" in step_paths
