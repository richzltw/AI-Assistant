import json
import subprocess
from typing import Any, Dict

import httpx
from google.cloud import firestore

from app.config import settings
from app.security import sanitize_shell_command


class ToolRegistry:
    def __init__(self) -> None:
        self.firestore_client = firestore.Client(project=settings.project_id) if settings.project_id else None
        self.allowed_shell_commands = ["echo", "date", "whoami", "pwd", "ls", "dir"]

    async def web_search(self, query: str) -> Dict[str, Any]:
        if not settings.brave_search_api_key:
            return {"ok": False, "error": "BRAVE_SEARCH_API_KEY is not configured"}

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": settings.brave_search_api_key,
        }
        params = {"q": query, "count": 5}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        snippets = []
        for item in payload.get("web", {}).get("results", [])[:5]:
            snippets.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                }
            )
        return {"ok": True, "results": snippets}

    async def firestore_lookup(self, collection: str, doc_id: str) -> Dict[str, Any]:
        if not self.firestore_client:
            return {"ok": False, "error": "Firestore is not configured"}
        doc = self.firestore_client.collection(collection).document(doc_id).get()
        if not doc.exists:
            return {"ok": False, "error": "Document not found"}
        return {"ok": True, "document": doc.to_dict()}

    async def call_cloud_function(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not settings.function_router_url:
            return {"ok": False, "error": "FUNCTION_ROUTER_URL is not configured"}

        headers = {"Content-Type": "application/json"}
        if settings.function_router_token:
            headers["Authorization"] = f"Bearer {settings.function_router_token}"

        body = {"action": action, "payload": payload}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(settings.function_router_url, json=body, headers=headers)
            response.raise_for_status()
            return {"ok": True, "result": response.json()}

    async def shell_command(self, command: str) -> Dict[str, Any]:
        if not settings.shell_enabled:
            return {"ok": False, "error": "Shell tool is disabled"}

        safe_command = sanitize_shell_command(command, self.allowed_shell_commands)
        process = subprocess.run(
            safe_command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
        return {
            "ok": True,
            "return_code": process.returncode,
            "stdout": process.stdout[:1000],
            "stderr": process.stderr[:1000],
        }

    async def http_api(self, url: str) -> Dict[str, Any]:
        allowed_prefixes = ["https://api.github.com", "https://worldtimeapi.org"]
        if not any(url.startswith(prefix) for prefix in allowed_prefixes):
            return {"ok": False, "error": "URL not allowed"}

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = {"raw": response.text[:1000]}

        return {"ok": True, "data": data}


registry = ToolRegistry()
