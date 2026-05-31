import json
from typing import Any, Dict, List

from google import genai
from openai import OpenAI

from app.config import settings


class LLMClient:
    def __init__(self) -> None:
        self.google_client = self._create_google_client()
        self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def _create_google_client(self):
        if settings.google_api_key:
            return genai.Client(api_key=settings.google_api_key)

        if settings.project_id:
            try:
                return genai.Client(
                    vertexai=True,
                    project=settings.project_id,
                    location=settings.region,
                )
            except Exception:
                return None

        return None

    def _google_generate(self, prompt: str) -> str:
        if not self.google_client:
            return ""
        response = self.google_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        return (response.text or "").strip()

    def _openai_generate(self, prompt: str) -> str:
        if not self.openai_client:
            return ""
        response = self.openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def generate_text(self, prompt: str) -> str:
        google_text = self._google_generate(prompt)
        if google_text:
            return google_text

        openai_text = self._openai_generate(prompt)
        if openai_text:
            return openai_text

        return (
            "No model provider is configured. Set GOOGLE_API_KEY for Gemini "
            "or OPENAI_API_KEY for fallback."
        )

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        raw = self.generate_text(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"tool": "none", "arguments": {}, "rationale": "Failed to parse JSON"}


llm_client = LLMClient()
