from __future__ import annotations

import re
from typing import Any

TECH_RULES: list[dict[str, Any]] = [
    # Frameworks - Web & Backend
    {
        "name": "FastAPI",
        "category": "framework",
        "patterns": [r"\bfastapi\b"],
        "manifests": ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"],
    },
    {
        "name": "Django",
        "category": "framework",
        "patterns": [r"\bdjango\b"],
        "manifests": ["requirements.txt", "pyproject.toml", "Pipfile"],
    },
    {
        "name": "Flask",
        "category": "framework",
        "patterns": [r"\bflask\b"],
        "manifests": ["requirements.txt", "pyproject.toml", "Pipfile"],
    },
    {
        "name": "Express",
        "category": "framework",
        "patterns": [r'"express"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "NestJS",
        "category": "framework",
        "patterns": [r'"@nestjs/core"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Spring Boot",
        "category": "framework",
        "patterns": [r"spring-boot"],
        "manifests": ["pom.xml", "build.gradle"],
    },
    {
        "name": "Gin",
        "category": "framework",
        "patterns": [r"github\.com/gin-gonic/gin"],
        "manifests": ["go.mod"],
    },
    {
        "name": "Fiber",
        "category": "framework",
        "patterns": [r"github\.com/gofiber/fiber"],
        "manifests": ["go.mod"],
    },
    # Frameworks - Frontend
    {
        "name": "React",
        "category": "framework",
        "patterns": [r'"react"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Next.js",
        "category": "framework",
        "patterns": [r'"next"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Vue",
        "category": "framework",
        "patterns": [r'"vue"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Svelte",
        "category": "framework",
        "patterns": [r'"svelte"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Vite",
        "category": "framework",
        "patterns": [r'"vite"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Tailwind CSS",
        "category": "framework",
        "patterns": [r'"tailwindcss"\s*:', r"tailwindcss"],
        "manifests": ["package.json", "tailwind.config.js", "tailwind.config.ts"],
    },
    # Databases & ORMs
    {
        "name": "MongoDB / PyMongo",
        "category": "database",
        "patterns": [r"\bpymongo\b", r"\bmotor\b", r'"mongodb"\s*:', r'"mongoose"\s*:'],
        "manifests": ["requirements.txt", "pyproject.toml", "package.json"],
    },
    {
        "name": "Redis",
        "category": "database",
        "patterns": [r"\bredis\b", r'"redis"\s*:', r'"ioredis"\s*:', r"github\.com/redis/go-redis"],
        "manifests": ["requirements.txt", "pyproject.toml", "package.json", "go.mod"],
    },
    {
        "name": "PostgreSQL",
        "category": "database",
        "patterns": [r"\bpsycopg\b", r"\basyncpg\b", r'"pg"\s*:', r'"postgres"\s*:'],
        "manifests": ["requirements.txt", "pyproject.toml", "package.json"],
    },
    {
        "name": "SQLite",
        "category": "database",
        "patterns": [r"\bsqlite3\b", r"\baiosqlite\b", r'"sqlite3"\s*:'],
        "manifests": ["requirements.txt", "pyproject.toml", "package.json"],
    },
    {
        "name": "SQLAlchemy",
        "category": "database",
        "patterns": [r"\bsqlalchemy\b"],
        "manifests": ["requirements.txt", "pyproject.toml"],
    },
    {
        "name": "Prisma",
        "category": "database",
        "patterns": [r'"@prisma/client"\s*:', r'"prisma"\s*:'],
        "manifests": ["package.json", "schema.prisma"],
    },
    {
        "name": "GORM",
        "category": "database",
        "patterns": [r"gorm\.io/gorm"],
        "manifests": ["go.mod"],
    },
    # Testing
    {
        "name": "pytest",
        "category": "testing",
        "patterns": [r"\bpytest\b"],
        "manifests": ["requirements.txt", "pyproject.toml", "setup.cfg"],
    },
    {
        "name": "Jest",
        "category": "testing",
        "patterns": [r'"jest"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "Vitest",
        "category": "testing",
        "patterns": [r'"vitest"\s*:'],
        "manifests": ["package.json"],
    },
    {
        "name": "JUnit",
        "category": "testing",
        "patterns": [r"junit"],
        "manifests": ["pom.xml", "build.gradle"],
    },
    {
        "name": "Go test",
        "category": "testing",
        "patterns": [r"testing"],
        "manifests": ["*_test.go"],
    },
    # Infrastructure & DevOps
    {
        "name": "Docker",
        "category": "infra",
        "patterns": [r"FROM\s+", r"services:"],
        "manifests": ["Dockerfile", "docker-compose.yml", "compose.yaml", "docker-compose.yaml"],
    },
    {
        "name": "GitHub Actions",
        "category": "infra",
        "patterns": [r"name:\s+", r"on:\s+"],
        "manifests": [".github/workflows"],
    },
    {
        "name": "Kubernetes",
        "category": "infra",
        "patterns": [r"apiVersion:\s+", r"kind:\s+Deployment"],
        "manifests": ["k8s", "deploy"],
    },
    {
        "name": "Celery",
        "category": "infra",
        "patterns": [r"\bcelery\b"],
        "manifests": ["requirements.txt", "pyproject.toml"],
    },
]


class TechStackDetector:
    """Detects technologies, frameworks, databases, infra, and languages from repo manifests (§8.8)."""

    def detect(
        self,
        files: list[dict[str, Any]],
        languages_stats: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Scans repo manifests and language statistics to produce structured tech stack.

        Returns list of items:
            [{"name": "FastAPI", "category": "framework", "evidence": "backend/requirements.txt"}]
        """
        detected: dict[str, dict[str, Any]] = {}
        file_map = {f.get("path", ""): f for f in files if f.get("path")}

        # 1. Add Language categories from language stats
        if languages_stats:
            for lang in languages_stats.keys():
                if lang not in ("Other", "Plain Text"):
                    detected[lang] = {
                        "name": lang,
                        "category": "language",
                        "evidence": "Repository codebase",
                    }

        # 2. Check rules against manifests
        for path, file_doc in file_map.items():
            content = file_doc.get("content") or file_doc.get("text", "")
            base_name = path.split("/")[-1]

            for rule in TECH_RULES:
                rule_name = rule["name"]
                if rule_name in detected:
                    continue

                for manifest_pattern in rule["manifests"]:
                    matches_manifest = False
                    if manifest_pattern.startswith("*") and path.endswith(manifest_pattern[1:]):
                        matches_manifest = True
                    elif manifest_pattern in path or base_name == manifest_pattern:
                        matches_manifest = True

                    if not matches_manifest:
                        continue

                    # If manifest matches, check regex patterns in content
                    for pat in rule["patterns"]:
                        if re.search(pat, content, re.IGNORECASE):
                            detected[rule_name] = {
                                "name": rule_name,
                                "category": rule["category"],
                                "evidence": path,
                            }
                            break

        return sorted(detected.values(), key=lambda x: (x["category"], x["name"]))
