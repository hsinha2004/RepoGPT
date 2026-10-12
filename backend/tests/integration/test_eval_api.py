from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.main import create_app


@pytest.mark.asyncio
async def test_eval_api_endpoints_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        DATA_DIR=".",
        LLM_PROVIDER="fake",
        LLM_MODEL="fake-model",
    )
    app = create_app()

    # Create dummy user auth token
    user_token = create_access_token(
        user_id="user_eval_1",
        role="user",
    )
    auth_headers = {"Authorization": f"Bearer {user_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthorized access fails
        unauth_res = await client.get("/api/v1/eval/benchmarks")
        assert unauth_res.status_code == 401

        # Authenticate for subsequent requests
        app.dependency_overrides[get_current_user] = lambda: {
            "_id": "user_eval_1",
            "email": "eval@example.com",
            "role": "user",
        }

        # 2. List benchmarks returns built-ins
        b_res = await client.get("/api/v1/eval/benchmarks", headers=auth_headers)
        assert b_res.status_code == 200
        benchmarks = b_res.json()
        assert len(benchmarks) >= 1
        b_id = benchmarks[0]["id"]

        # 3. Get single benchmark
        b_detail = await client.get(f"/api/v1/eval/benchmarks/{b_id}", headers=auth_headers)
        assert b_detail.status_code == 200
        assert b_detail.json()["id"] == b_id

        # 4. Non-existent benchmark -> 404
        missing_b = await client.get(
            "/api/v1/eval/benchmarks/non_existent_123", headers=auth_headers
        )
        assert missing_b.status_code == 404

        # 5. Pre-flight Estimation
        est_res = await client.post(
            "/api/v1/eval/estimate",
            json={
                "benchmark_id": b_id,
                "strategies": ["keyword", "hybrid_rerank"],
                "generate_answers": True,
            },
            headers=auth_headers,
        )
        assert est_res.status_code == 200
        est_data = est_res.json()
        assert "estimated_llm_calls" in est_data
        assert "estimated_tokens" in est_data
        assert est_data["strategies_count"] == 2

        # 6. Live Metrics Endpoint
        live_res = await client.get("/api/v1/eval/live", headers=auth_headers)
        assert live_res.status_code == 200
        live_data = live_res.json()
        assert "questions_per_day" in live_data
        assert "confidence_distribution" in live_data

        # 7. Upload Custom Benchmark
        yaml_content = """name: custom-unit-test
description: Custom benchmark for unit testing
repo:
  type: fixture
  path: eval/fixtures/sample-repo
questions:
  - id: q01
    question: Where is login defined?
    category: locate
    expected_intent: locate
    expected_files: [backend/app/auth/routes.py]
    expected_symbols: [login]
"""
        upload_res = await client.post(
            "/api/v1/eval/benchmarks",
            files={"file": ("custom.yaml", yaml_content.encode("utf-8"), "application/x-yaml")},
            headers=auth_headers,
        )
        assert upload_res.status_code == 201
        custom_b = upload_res.json()
        custom_id = custom_b["id"]

        # 8. Delete Custom Benchmark
        del_res = await client.delete(f"/api/v1/eval/benchmarks/{custom_id}", headers=auth_headers)
        assert del_res.status_code == 204

        # Cannot delete built-in benchmark
        del_builtin = await client.delete(f"/api/v1/eval/benchmarks/{b_id}", headers=auth_headers)
        assert del_builtin.status_code == 422
