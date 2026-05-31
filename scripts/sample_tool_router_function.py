# Deploy this as an HTTP Cloud Function (2nd gen).
# It acts as a simple automation target for the assistant's call_cloud_function tool.

import json
from datetime import datetime, timezone


def handler(request):
    auth = request.headers.get("Authorization", "")
    expected = "Bearer REPLACE_WITH_SHARED_TOKEN"
    if auth != expected:
        return (json.dumps({"ok": False, "error": "Unauthorized"}), 403, {"Content-Type": "application/json"})

    body = request.get_json(silent=True) or {}
    action = body.get("action", "")
    payload = body.get("payload", {})

    if action == "get_time":
        now = datetime.now(timezone.utc).isoformat()
        return (json.dumps({"ok": True, "utc_time": now}), 200, {"Content-Type": "application/json"})

    if action == "echo":
        return (json.dumps({"ok": True, "payload": payload}), 200, {"Content-Type": "application/json"})

    if action == "run_daily_news_digest":
        digest_function_url = "https://REPLACE_WITH_DAILY_DIGEST_FUNCTION_URL"
        return (
            json.dumps(
                {
                    "ok": True,
                    "message": "Forward this action to your dedicated daily digest function.",
                    "target": digest_function_url,
                    "payload": payload,
                }
            ),
            200,
            {"Content-Type": "application/json"},
        )

    return (json.dumps({"ok": False, "error": "Unknown action"}), 400, {"Content-Type": "application/json"})
