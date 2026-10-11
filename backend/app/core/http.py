"""
Shared HTTP client utilities using httpx.AsyncClient.
"""

import httpx

_http_client: httpx.AsyncClient | None = None


async def init_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def get_http_client() -> httpx.AsyncClient:
    if _http_client is None:
        return httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    return _http_client
