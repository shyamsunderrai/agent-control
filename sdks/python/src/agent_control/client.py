"""Base HTTP client for Agent Control server communication."""

from types import TracebackType

import httpx


class AgentControlClient:
    """
    Async HTTP client for Agent Control server.

    This is the base client that provides the HTTP connection management.
    Specific operations are organized into separate modules:
    agents, policies, controls, evaluation.

    Usage:
        async with AgentControlClient() as client:
            # Use via specific operation modules
            pass
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0
    ):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the Agent Control server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AgentControlClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def health_check(self) -> dict[str, str]:
        """
        Check server health.

        Returns:
            Dictionary with health status

        Raises:
            httpx.HTTPError: If request fails
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        response = await self._client.get("/health")
        response.raise_for_status()
        from typing import cast
        return cast(dict[str, str], response.json())

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get the underlying HTTP client."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client

