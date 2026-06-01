from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from google.cloud import firestore

from app.config import settings


class ChatHistoryStore:
    def __init__(self) -> None:
        self.client = None
        if settings.project_id:
            try:
                self.client = firestore.Client(project=settings.project_id)
            except Exception:
                # Allow local app startup without ADC; history persistence is disabled in this mode.
                self.client = None

    def save_message(
        self,
        user_id: str,
        role: str,
        content: str,
        input_mode: str,
        used_tool: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        if not self.client:
            return None

        session_key = (session_id or "").strip() or f"session-{uuid4().hex}"

        user_doc = self.client.collection("chat_history").document(user_id)
        conv_doc = user_doc.collection("conversations").document(session_key)
        msg_doc = conv_doc.collection("messages").document()

        payload: Dict[str, Any] = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "input_mode": input_mode,
            "used_tool": used_tool,
            "session_id": session_key,
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        conv_payload: Dict[str, Any] = {
            "session_id": session_key,
            "last_message": content,
            "last_role": role,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "created_at": firestore.SERVER_TIMESTAMP,
            "message_count": firestore.Increment(1),
        }

        # Keep a short preview for side-panel summary cards.
        preview = content.strip().replace("\n", " ")[:120]
        conv_payload["preview"] = preview

        conv_doc.set(conv_payload, merge=True)
        msg_doc.set(payload)
        return session_key

    def get_recent_messages(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        # Backward-compatible helper across all conversations.
        if not self.client:
            return []

        conv_docs = (
            self.client.collection("chat_history")
            .document(user_id)
            .collection("conversations")
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(20)
            .stream()
        )

        rows: List[Dict[str, Any]] = []
        per_conv = max(1, min(limit, 100))
        for conv in conv_docs:
            session_id = conv.id
            docs = (
                self.client.collection("chat_history")
                .document(user_id)
                .collection("conversations")
                .document(session_id)
                .collection("messages")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(per_conv)
                .stream()
            )

            for doc in docs:
                item = doc.to_dict() or {}
                created_at = item.get("created_at")
                if isinstance(created_at, datetime):
                    created = created_at.astimezone(timezone.utc).isoformat()
                else:
                    created = None

                rows.append(
                    {
                        "id": doc.id,
                        "role": item.get("role"),
                        "content": item.get("content"),
                        "input_mode": item.get("input_mode"),
                        "used_tool": item.get("used_tool"),
                        "session_id": item.get("session_id"),
                        "created_at": created,
                    }
                )

        rows.sort(key=lambda x: x.get("created_at") or "")
        return rows[-limit:]

    def get_conversation_summaries(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        docs = (
            self.client.collection("chat_history")
            .document(user_id)
            .collection("conversations")
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )

        rows: List[Dict[str, Any]] = []
        for doc in docs:
            item = doc.to_dict() or {}

            updated_at = item.get("updated_at")
            if isinstance(updated_at, datetime):
                updated = updated_at.astimezone(timezone.utc).isoformat()
            else:
                updated = None

            rows.append(
                {
                    "session_id": doc.id,
                    "preview": item.get("preview"),
                    "last_message": item.get("last_message"),
                    "last_role": item.get("last_role"),
                    "updated_at": updated,
                    "message_count": item.get("message_count", 0),
                }
            )

        return rows

    def get_conversation_messages(self, user_id: str, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        docs = (
            self.client.collection("chat_history")
            .document(user_id)
            .collection("conversations")
            .document(session_id)
            .collection("messages")
            .order_by("created_at", direction=firestore.Query.ASCENDING)
            .limit(limit)
            .stream()
        )

        rows: List[Dict[str, Any]] = []
        for doc in docs:
            item = doc.to_dict() or {}
            created_at = item.get("created_at")
            if isinstance(created_at, datetime):
                created = created_at.astimezone(timezone.utc).isoformat()
            else:
                created = None

            rows.append(
                {
                    "id": doc.id,
                    "role": item.get("role"),
                    "content": item.get("content"),
                    "input_mode": item.get("input_mode"),
                    "used_tool": item.get("used_tool"),
                    "session_id": item.get("session_id"),
                    "created_at": created,
                }
            )
        return rows

    def get_latest_daily_digest(self) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None

        docs = (
            self.client.collection("daily_news_digest")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )

        for doc in docs:
            item = doc.to_dict() or {}

            created_at = item.get("created_at")
            if isinstance(created_at, datetime):
                created = created_at.astimezone(timezone.utc).isoformat()
            else:
                created = None

            return {
                "id": doc.id,
                "generated_at": item.get("generated_at"),
                "digest_markdown": item.get("digest_markdown", ""),
                "headlines": item.get("headlines", []),
                "deliveries": item.get("deliveries", {}),
                "created_at": created,
            }

        return None


history_store = ChatHistoryStore()
