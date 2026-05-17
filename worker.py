from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from backend.app.core import LoanValidationError, get_config_payload, optimize_request_data


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path
        method = request.method.upper()

        if path == "/api/health":
            if method != "GET":
                return Response("Method not allowed.", headers={"Allow": "GET"}, status=405)
            return Response.json({"status": "ok"})

        if path == "/api/config":
            if method != "GET":
                return Response("Method not allowed.", headers={"Allow": "GET"}, status=405)
            return Response.json(get_config_payload())

        if path == "/api/optimize":
            if method != "POST":
                return Response("Method not allowed.", headers={"Allow": "POST"}, status=405)
            try:
                payload = json.loads(await request.text())
                return Response.json(optimize_request_data(payload))
            except json.JSONDecodeError:
                return Response.json({"detail": "Invalid JSON request body."}, status=400)
            except LoanValidationError as exc:
                return Response.json({"detail": str(exc)}, status=422)
            except Exception:
                return Response.json({"detail": "Failed to process optimization request."}, status=500)

        return Response("Not found.", status=404)
