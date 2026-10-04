from __future__ import annotations

import httpx
import pytest

from app.services.provider_imports import ProviderImportError, fetch_chesscom_games


@pytest.mark.asyncio
async def test_chesscom_rejects_untrusted_archive_url_before_request():
    requested: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path.endswith("/games/archives"):
            return httpx.Response(
                200,
                json={"archives": ["https://example.com/private"]},
                request=request,
            )
        return httpx.Response(500, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderImportError, match="invalid archive URL"):
            await fetch_chesscom_games("safeuser", max_games=10, client=client)

    assert requested == ["https://api.chess.com/pub/player/safeuser/games/archives"]


@pytest.mark.asyncio
async def test_provider_requests_never_follow_redirects():
    requested: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path.endswith("/games/archives"):
            return httpx.Response(
                200,
                json={"archives": ["https://api.chess.com/pub/player/safeuser/games/2026/10"]},
                request=request,
            )
        if request.url.host == "api.chess.com":
            return httpx.Response(
                302,
                headers={"Location": "http://169.254.169.254/latest/meta-data/"},
                request=request,
            )
        return httpx.Response(200, json={"games": []}, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    ) as client:
        with pytest.raises(ProviderImportError, match="HTTP 302"):
            await fetch_chesscom_games("safeuser", max_games=10, client=client)

    assert requested == [
        "https://api.chess.com/pub/player/safeuser/games/archives",
        "https://api.chess.com/pub/player/safeuser/games/2026/10",
    ]
