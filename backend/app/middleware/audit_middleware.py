"""Middleware that logs read-access events for sensitive endpoints.

Intercepts successful GET requests to configurable route prefixes and
fires a ``READ_ACCESS`` audit event via the triple-write system.  The
event is written asynchronously (fire-and-forget) so it does not slow
down the response.

User information is read from ``request.state._audit_user``, which is
set by ``get_current_user()`` in ``middleware/auth.py``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.services.audit_service import (
    AuditEvent,
    AuditEventCategory,
    TripleAuditWriter,
)

logger = logging.getLogger(__name__)


class AuditReadAccessMiddleware(BaseHTTPMiddleware):
    """Log read-access events for sensitive data views."""

    def __init__(
        self,
        app,
        writer: TripleAuditWriter,
        prefixes: list[str],
        system_name: str = "erp",
    ) -> None:
        super().__init__(app)
        self.writer = writer
        self.prefixes = prefixes
        self.system_name = system_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only intercept GET requests
        if request.method != "GET":
            return await call_next(request)

        path = request.url.path
        matched = any(path.startswith(p) for p in self.prefixes)
        if not matched:
            return await call_next(request)

        response = await call_next(request)

        # Only log successful responses (2xx)
        if 200 <= response.status_code < 300:
            user_info = getattr(request.state, "_audit_user", None)

            event = AuditEvent(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                category=AuditEventCategory.READ_ACCESS,
                user_id=(
                    str(user_info["user_id"]) if user_info else None
                ),
                username=(
                    user_info.get("username") if user_info else None
                ),
                action=f"read.{path.strip('/').replace('/', '.')}",
                resource_type="endpoint",
                resource_id=path,
                details={
                    "query_params": dict(request.query_params),
                    "status_code": response.status_code,
                },
                ip_address=(
                    request.client.host if request.client else None
                ),
                system_name=self.system_name,
            )
            self.writer.fire_and_forget(event)

        return response
