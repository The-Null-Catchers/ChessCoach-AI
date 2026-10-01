import httpx
import pytest

from app.services.provider_imports import (
    ProviderImportError,
    fetch_provider_games,
    normalize_username,
)


@pytest.mark.asyncio
async def test_lichess_import_uses_pgn_endpoint():
    pgn = '[Event "Rated"]\n[White "demo"]\n[Black "opponent"]\n\n1. e4 e5 1/2-1/2'

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "lichess.org"
        assert request.url.path == "/api/games/user/demo"
        assert request.url.params["max"] == "3"
        assert request.headers["accept"] == "application/x-chess-pgn"
        return httpx.Response(200, text=pgn)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_provider_games("lichess", "demo", max_games=3, client=client)

    assert result == pgn


@pytest.mark.asyncio
async def test_chesscom_import_reads_latest_archives_until_limit():
    game_one = '[Event "One"]\n[White "demo"]\n[Black "a"]\n\n1. e4 e5 1-0'
    game_two = '[Event "Two"]\n[White "b"]\n[Black "demo"]\n\n1. d4 d5 0-1'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/games/archives"):
            return httpx.Response(
                200,
                json={"archives": ["https://api.chess.com/pub/player/demo/games/2026/09"]},
            )
        return httpx.Response(200, json={"games": [{"pgn": game_one}, {"pgn": game_two}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_provider_games("chesscom", "demo", max_games=2, client=client)

    assert game_one in result
    assert game_two in result


@pytest.mark.asyncio
async def test_provider_404_is_user_friendly():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderImportError, match="not found"):
            await fetch_provider_games("lichess", "missing-user", max_games=1, client=client)


def test_username_validation_blocks_provider_path_injection():
    with pytest.raises(ValueError):
        normalize_username("../someone")
