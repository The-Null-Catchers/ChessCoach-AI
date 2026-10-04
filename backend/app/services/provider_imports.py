from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
MAX_PROVIDER_BYTES = 8 * 1024 * 1024
USER_AGENT = "ChessCoach-AI/0.17 (+https://github.com/The-Null-Catchers/ChessCoach-AI)"


class ProviderImportError(RuntimeError):
    """Raised when a supported chess provider cannot supply importable games."""


def normalize_username(username: str) -> str:
    value = username.strip()
    if not USERNAME_RE.fullmatch(value):
        raise ValueError("Username must be 2-32 letters, numbers, underscores, or hyphens")
    return value


def _validate_chesscom_archive_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ProviderImportError("Chess.com returned an invalid archive URL") from exc

    path = parsed.path or ""
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.chess.com"
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or not path.startswith("/pub/player/")
        or "/games/" not in path
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderImportError("Chess.com returned an invalid archive URL")
    return url


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    try:
        # Provider endpoints are expected to be canonical API URLs. Never follow
        # redirects here: an upstream redirect to a private/internal address would
        # otherwise turn account imports into an SSRF primitive.
        response = await client.get(url, follow_redirects=False, **kwargs)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ProviderImportError("Chess account was not found") from exc
        if exc.response.status_code == 429:
            raise ProviderImportError("Chess provider rate limit reached; try again later") from exc
        raise ProviderImportError(f"Chess provider returned HTTP {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise ProviderImportError("Chess provider is temporarily unavailable") from exc


def _bounded_text(response: httpx.Response) -> str:
    body = response.content
    if len(body) > MAX_PROVIDER_BYTES:
        raise ProviderImportError("Provider response is too large")
    return body.decode("utf-8", errors="strict")


async def fetch_lichess_games(
    username: str,
    *,
    max_games: int,
    client: httpx.AsyncClient,
) -> str:
    response = await _get(
        client,
        f"https://lichess.org/api/games/user/{username}",
        params={
            "max": max_games,
            "clocks": "true",
            "opening": "true",
            "evals": "false",
        },
        headers={"Accept": "application/x-chess-pgn"},
    )
    return _bounded_text(response)


async def fetch_chesscom_games(
    username: str,
    *,
    max_games: int,
    client: httpx.AsyncClient,
) -> str:
    archive_response = await _get(
        client,
        f"https://api.chess.com/pub/player/{username}/games/archives",
    )
    try:
        archives = archive_response.json().get("archives", [])
    except ValueError as exc:
        raise ProviderImportError("Chess.com returned malformed archive metadata") from exc

    if not isinstance(archives, list):
        raise ProviderImportError("Chess.com returned malformed archive metadata")

    collected: list[str] = []
    for archive_url in reversed(archives[-6:]):
        if not isinstance(archive_url, str):
            raise ProviderImportError("Chess.com returned an invalid archive URL")
        response = await _get(client, _validate_chesscom_archive_url(archive_url))
        try:
            games = response.json().get("games", [])
        except ValueError as exc:
            raise ProviderImportError("Chess.com returned malformed game data") from exc
        for game in reversed(games):
            pgn = game.get("pgn")
            if isinstance(pgn, str) and pgn.strip():
                collected.append(pgn)
                if len(collected) >= max_games:
                    break
        if len(collected) >= max_games:
            break

    collected.reverse()
    return "\n\n".join(collected)


async def fetch_provider_games(
    provider: str,
    username: str,
    *,
    max_games: int = 20,
    client: httpx.AsyncClient | None = None,
) -> str:
    if provider not in {"lichess", "chesscom"}:
        raise ValueError("Unsupported provider")
    if not 1 <= max_games <= 50:
        raise ValueError("max_games must be between 1 and 50")

    handle = normalize_username(username)
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=False,
        )

    try:
        if provider == "lichess":
            return await fetch_lichess_games(handle, max_games=max_games, client=client)
        return await fetch_chesscom_games(handle, max_games=max_games, client=client)
    finally:
        if owns_client:
            await client.aclose()
