from app.core.errors import (
    RateLimitedError,
    format_error_response,
)


def test_error_envelope_structure():
    response = format_error_response(
        code="RESOURCE_NOT_FOUND",
        message="Item could not be found",
        status_code=404,
        request_id="req-12345",
        details={"item_id": "abc"},
    )
    assert response.status_code == 404
    import json

    data = json.loads(response.body.decode())
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert data["error"]["message"] == "Item could not be found"
    assert data["error"]["request_id"] == "req-12345"
    assert data["error"]["details"]["item_id"] == "abc"


def test_rate_limited_error_headers():
    err = RateLimitedError(message="Too many requests", retry_after=30)
    assert err.status_code == 429
    assert err.headers.get("Retry-After") == "30"
