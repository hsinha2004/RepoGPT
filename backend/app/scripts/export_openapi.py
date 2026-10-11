#!/usr/bin/env python3
"""
Export FastAPI OpenAPI specification to JSON for frontend contract generation.
"""

import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import create_app  # noqa: E402


def export_openapi() -> None:
    app = create_app()
    openapi_schema = app.openapi()

    output_dir = backend_dir.parent / "frontend" / "src" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "openapi.json"
    output_file.write_text(json.dumps(openapi_schema, indent=2), encoding="utf-8")
    print(f"Exported OpenAPI schema to {output_file}")


if __name__ == "__main__":
    export_openapi()
