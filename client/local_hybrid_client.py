import base64
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8080"


def _safe_json(response: httpx.Response) -> dict:
    try:
        return response.json()
    except ValueError:
        return {"message": (response.text or "").strip()}


def chat(text: str) -> dict:
    payload = {
        "user_id": "local-user",
        "text": text,
        "enable_tools": True,
    }
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/assistant/chat", json=payload)
        if r.is_error:
            body = _safe_json(r)
            raise RuntimeError(f"Chat request failed with HTTP {r.status_code}: {body.get('message') or body}")
        return _safe_json(r)


def transcribe_audio(audio_path: str) -> dict:
    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/wav")}
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{BASE_URL}/assistant/voice/transcribe", files=files)
            if r.is_error:
                body = _safe_json(r)
                raise RuntimeError(f"Transcribe request failed with HTTP {r.status_code}: {body.get('message') or body}")
            return _safe_json(r)


def synthesize_to_file(text: str, out_path: str = "assistant.mp3") -> str:
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/assistant/voice/synthesize", json={"text": text})
        if r.is_error:
            body = _safe_json(r)
            raise RuntimeError(f"Synthesize request failed with HTTP {r.status_code}: {body.get('message') or body}")
        payload = _safe_json(r)
        audio_b64 = payload.get("audio_base64", "")
    audio_bytes = base64.b64decode(audio_b64)
    Path(out_path).write_bytes(audio_bytes)
    return out_path


if __name__ == "__main__":
    prompt = "Plan a focused 5-day cloud AI study schedule and include one automation task."
    result = chat(prompt)
    print("Answer:\n", result.get("answer", ""))
    print("Used tool:", result.get("used_tool"))

    mp3 = synthesize_to_file(result.get("answer", "No answer generated"))
    print("Saved voice response to", mp3)
