import json
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

try:
    from google.cloud import firestore
except Exception:  # pragma: no cover - optional dependency
    firestore = None

try:
    from google import genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


DEFAULT_FEEDS = [
    "https://news.google.com/rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
]


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_feeds() -> List[str]:
    raw = os.getenv("NEWS_FEEDS", "")
    if not raw.strip():
        return DEFAULT_FEEDS
    return [item.strip() for item in raw.split(",") if item.strip()]


def _safe_text(value: str) -> str:
    return " ".join((value or "").strip().split())


def _parse_pub_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return _safe_text(value)


def _extract_source(link: str) -> str:
    host = urlparse(link).netloc
    return host.replace("www.", "") if host else "unknown"


def _fetch_feed(url: str, per_feed_limit: int) -> List[Dict[str, str]]:
    timeout_seconds = float(os.getenv("NEWS_HTTP_TIMEOUT_SECONDS", "12"))
    headers = {"User-Agent": "daily-news-digest-function/1.0"}

    with httpx.Client(timeout=timeout_seconds, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        xml_data = response.text

    root = ElementTree.fromstring(xml_data)
    items = root.findall(".//item")

    headlines: List[Dict[str, str]] = []
    for item in items[:per_feed_limit]:
        title = _safe_text(item.findtext("title", default=""))
        link = _safe_text(item.findtext("link", default=""))
        pub_date = _parse_pub_date(item.findtext("pubDate", default=""))
        if not title or not link:
            continue

        headlines.append(
            {
                "title": title,
                "url": link,
                "source": _extract_source(link),
                "published": pub_date,
            }
        )

    return headlines


def _collect_headlines() -> List[Dict[str, str]]:
    feeds = _parse_feeds()
    per_feed_limit = int(os.getenv("NEWS_ITEMS_PER_FEED", "5"))
    max_items = int(os.getenv("NEWS_MAX_ITEMS", "15"))

    combined: List[Dict[str, str]] = []
    for feed in feeds:
        try:
            combined.extend(_fetch_feed(feed, per_feed_limit))
        except Exception:
            continue

    deduped: List[Dict[str, str]] = []
    seen = set()
    for item in combined:
        key = (item.get("title", "").lower(), item.get("url", "").lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return deduped


def _gemini_client():
    if genai is None:
        return None

    api_key = os.getenv("GOOGLE_API_KEY", "")
    project_id = os.getenv("PROJECT_ID", "")
    region = os.getenv("REGION", "us-central1")

    try:
        if api_key:
            return genai.Client(api_key=api_key)
        if project_id:
            return genai.Client(vertexai=True, project=project_id, location=region)
    except Exception:
        return None

    return None


def _render_markdown_fallback(headlines: List[Dict[str, str]], generated_at: str) -> str:
    if not headlines:
        return (
            "# Daily News Briefing\n\n"
            f"Generated: {generated_at}\n\n"
            "No headlines were collected from configured feeds today."
        )

    lines = ["# Daily News Briefing", "", f"Generated: {generated_at}", "", "## Top Headlines", ""]
    for idx, item in enumerate(headlines, start=1):
        published = f" ({item['published']})" if item.get("published") else ""
        lines.append(f"{idx}. [{item['title']}]({item['url']}) - {item['source']}{published}")

    lines.extend(
        [
            "",
            "## Watchlist",
            "",
            "- Track the top 3 stories for second-order impacts on markets, policy, and operations.",
            "- Re-check source links before acting on breaking headlines.",
        ]
    )
    return "\n".join(lines)


def _render_markdown_with_llm(headlines: List[Dict[str, str]], generated_at: str) -> str:
    client = _gemini_client()
    if client is None:
        return _render_markdown_fallback(headlines, generated_at)

    model = os.getenv("DIGEST_GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        "You are generating a concise daily morning news digest. "
        "Output strict Markdown only. Keep it skimmable and factual. "
        "Use this exact section structure:"
        "\n# Daily News Briefing"
        "\nGenerated: <timestamp>"
        "\n\n## Executive Summary"
        "\n- 3 to 5 bullets"
        "\n\n## Key Headlines"
        "\n- bullet list with markdown links"
        "\n\n## Why It Matters Today"
        "\n- 3 bullets"
        "\n\n## Watchlist"
        "\n- 3 bullets"
        "\n\nDo not invent facts beyond the provided headlines."
        f"\n\nTimestamp: {generated_at}"
        f"\n\nHeadlines JSON:\n{json.dumps(headlines, ensure_ascii=True)}"
    )

    try:
        response = client.models.generate_content(model=model, contents=prompt)
        text = (response.text or "").strip()
        if text:
            return text
    except Exception:
        pass

    return _render_markdown_fallback(headlines, generated_at)


def _slack_api_request(
    client: httpx.Client,
    token: str,
    endpoint: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = client.post(
        f"https://slack.com/api/{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok", False):
        raise RuntimeError(f"Slack API error on {endpoint}: {data.get('error', 'unknown_error')}")
    return data


def _post_slack_dm(markdown: str) -> Dict[str, Any]:
    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    dm_email = os.getenv("SLACK_DM_EMAIL", "")
    if not bot_token or not dm_email:
        return {"sent": False, "reason": "SLACK_BOT_TOKEN or SLACK_DM_EMAIL not configured"}

    with httpx.Client(timeout=12) as client:
        lookup = _slack_api_request(
            client,
            bot_token,
            "users.lookupByEmail",
            {"email": dm_email},
        )
        user_id = lookup.get("user", {}).get("id", "")
        if not user_id:
            raise RuntimeError("Slack user lookup did not return user id")

        open_dm = _slack_api_request(
            client,
            bot_token,
            "conversations.open",
            {"users": user_id},
        )
        channel_id = open_dm.get("channel", {}).get("id", "")
        if not channel_id:
            raise RuntimeError("Slack DM channel open did not return channel id")

        _slack_api_request(
            client,
            bot_token,
            "chat.postMessage",
            {
                "channel": channel_id,
                "text": "Daily News Briefing",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": markdown[:2900],
                        },
                    }
                ],
            },
        )

    return {"sent": True, "mode": "dm", "email": dm_email}


def _post_slack(markdown: str) -> Dict[str, Any]:
    dm_error = ""
    try:
        dm_result = _post_slack_dm(markdown)
        if dm_result.get("sent"):
            return dm_result
        dm_error = dm_result.get("reason", "")
    except Exception as exc:
        dm_error = f"Slack DM failed: {str(exc)}"

    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook:
        reason = "Neither Slack DM nor webhook is configured"
        if dm_error:
            reason = f"{reason}. {dm_error}"
        return {"sent": False, "reason": reason}

    payload = {
        "text": "Daily News Briefing",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": markdown[:2900],
                },
            }
        ],
    }

    with httpx.Client(timeout=12) as client:
        response = client.post(webhook, json=payload)
        response.raise_for_status()

    result: Dict[str, Any] = {"sent": True, "mode": "webhook"}
    if dm_error:
        result["fallback_reason"] = dm_error
    return result


def _post_twilio_sms(markdown: str) -> Dict[str, Any]:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_FROM_NUMBER", "")
    to_number = os.getenv("TWILIO_TO_NUMBER", "")

    if not all([account_sid, auth_token, from_number, to_number]):
        return {"sent": False, "reason": "Twilio env vars are incomplete"}

    summary_lines = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("1.") or stripped.startswith("2."):
            summary_lines.append(stripped)
        if len(summary_lines) >= 10:
            break

    sms_body = "Daily News Briefing\n" + "\n".join(summary_lines)
    sms_body = sms_body[:1500]

    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    with httpx.Client(timeout=12, auth=(account_sid, auth_token)) as client:
        response = client.post(
            endpoint,
            data={
                "From": from_number,
                "To": to_number,
                "Body": sms_body,
            },
        )
        response.raise_for_status()

    return {"sent": True}


def _persist_digest(
    generated_at: str,
    digest_markdown: str,
    headlines: List[Dict[str, str]],
    deliveries: Dict[str, Any],
) -> Dict[str, Any]:
    if firestore is None:
        return {"stored": False, "reason": "google-cloud-firestore is not installed"}

    project_id = os.getenv("PROJECT_ID", "")
    try:
        client = firestore.Client(project=project_id) if project_id else firestore.Client()
        doc_ref = client.collection("daily_news_digest").document()
        doc_ref.set(
            {
                "generated_at": generated_at,
                "digest_markdown": digest_markdown,
                "headlines": headlines,
                "deliveries": deliveries,
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )
        return {"stored": True, "document_id": doc_ref.id}
    except Exception as exc:
        return {"stored": False, "reason": f"Failed to persist digest: {str(exc)}"}


def handler(request):
    expected_token = os.getenv("DIGEST_FUNCTION_TOKEN", "")
    if expected_token:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {expected_token}":
            return (
                json.dumps({"ok": False, "error": "Unauthorized"}),
                403,
                {"Content-Type": "application/json"},
            )

    generated_at = _now_iso()
    headlines = _collect_headlines()
    digest_markdown = _render_markdown_with_llm(headlines, generated_at)

    slack_result = _post_slack(digest_markdown)
    sms_result = _post_twilio_sms(digest_markdown)
    delivery_status = {
        "slack": slack_result,
        "sms": sms_result,
    }
    storage_result = _persist_digest(generated_at, digest_markdown, headlines, delivery_status)

    result = {
        "ok": True,
        "generated_at": generated_at,
        "headlines_collected": len(headlines),
        "deliveries": delivery_status,
        "storage": storage_result,
        "digest_markdown": digest_markdown,
    }

    return (json.dumps(result), 200, {"Content-Type": "application/json"})
