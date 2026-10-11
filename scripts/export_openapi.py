#!/usr/bin/env python3
"""
Export FastAPI OpenAPI specification to JSON for frontend contract generation.
"""
import json
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import create_app  # noqa: E402


def export_openapi() -> None:
    app = create_app()
    openapi_schema = app.openapi()

    output_dir = root_dir / "frontend" / "src" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "openapi.json"
    output_file.write_text(json.dumps(openapi_schema, indent=2), encoding="utf-8")
    print(f"Exported OpenAPI schema to {output_file}")


if __name__ == "__main__":
    export_openapi()
