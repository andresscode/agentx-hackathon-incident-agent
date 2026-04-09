"""Peppermint API client with automatic token management."""

from datetime import datetime, timedelta
from typing import Any, Optional
import os

import httpx


class PeppermintAuthError(Exception):
    """Raised when Peppermint authentication fails."""


class PeppermintClient:
    """Client for Peppermint API with automatic token refresh.

    Usage:
        client = PeppermintClient()
        ticket = await client.get_ticket("ticket-uuid")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (base_url or os.getenv("PEPPERMINT_URL", "http://peppermint:5003/api/v1")).rstrip("/")
        self.email = email or os.getenv("PEPPERMINT_EMAIL", "admin@admin.com")
        self.password = password or os.getenv("PEPPERMINT_PASSWORD", "1234")
        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    # ─── Token Management ─────────────────────────────────────────────────────

    async def _ensure_token(self) -> str:
        """Return a valid token, refreshing if needed."""
        now = datetime.utcnow()
        if self._token and self._expires_at and now < self._expires_at:
            return self._token
        await self._login()
        return self._token  # type: ignore[return-value]

    async def _login(self) -> None:
        """Login to Peppermint and cache the JWT token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/auth/login",
                json={"email": self.email, "password": self.password},
            )
            if resp.status_code != 200:
                raise PeppermintAuthError(
                    f"Failed to login to Peppermint: {resp.status_code} {resp.text}"
                )
            data = resp.json()
            self._token = data["token"]
            # JWT expires in 8 hours; refresh 5 min early
            self._expires_at = datetime.utcnow() + timedelta(hours=8, minutes=-5)

    async def logout(self) -> None:
        """Clear cached token (forces re-login on next call)."""
        self._token = None
        self._expires_at = None

    # ─── Request Wrapper ──────────────────────────────────────────────────────

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated request with auto-retry on 401."""
        token = await self._ensure_token()

        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method,
                f"{self.base_url}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {token}"},
                json=json,
            )

            # Token may have expired server-side — retry once after re-login
            if resp.status_code == 401:
                await self._login()
                token = await self._ensure_token()
                resp = await client.request(
                    method,
                    f"{self.base_url}/{path.lstrip('/')}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=json,
                )

            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text}

    # ─── Ticket Helpers ───────────────────────────────────────────────────────

    async def get_ticket(self, ticket_id: str) -> dict:
        return await self.request("GET", f"/ticket/{ticket_id}")

    async def get_all_tickets(self) -> dict:
        return await self.request("GET", "/tickets/all")

    async def get_open_tickets(self) -> dict:
        return await self.request("GET", "/tickets/open")

    async def create_ticket(
        self,
        title: str,
        name: str,
        detail: str = "",
        priority: str = "medium",
        ticket_type: str = "incident",
        email: str = "test@hackathon.com",
    ) -> dict:
        # Get current user for assignment
        profile = await self.request("GET", "/auth/profile")
        user = profile["user"]
        user_id = user["id"]
        user_name = user["name"]

        return await self.request(
            "POST",
            "/ticket/create",
            json={
                "title": title,
                "name": name,
                "detail": detail or f"Test ticket: {title}",
                "priority": priority,
                "type": ticket_type,
                "email": email,
                "engineer": {"id": user_id, "name": user_name},
                "createdBy": {
                    "id": user_id,
                    "name": user_name,
                    "role": "admin",
                    "email": user["email"],
                },
            },
        )

    async def update_ticket(self, ticket_id: str, **fields: Any) -> dict:
        return await self.request(
            "PUT", "/ticket/update", json={"id": ticket_id, **fields}
        )

    async def close_ticket(self, ticket_id: str) -> dict:
        return await self.request(
            "PUT", "/ticket/status/update", json={"id": ticket_id, "status": True}
        )

    async def reopen_ticket(self, ticket_id: str) -> dict:
        return await self.request(
            "PUT", "/ticket/status/update", json={"id": ticket_id, "status": False}
        )


# ─── Singleton for easy import ───────────────────────────────────────────────

peppermint = PeppermintClient()
