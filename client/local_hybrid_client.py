import base64
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8080"


def chat(text: str) -> dict:
    payload = {
        "user_id": "local-user",
        "text": text,
        "enable_tools": True,
    }
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/assistant/chat", json=payload)
        r.raise_for_status()
        return r.json()


def transcribe_audio(audio_path: str) -> dict:
    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/wav")}
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{BASE_URL}/assistant/voice/transcribe", files=files)
            r.raise_for_status()
            return r.json()


def synthesize_to_file(text: str, out_path: str = "assistant.mp3") -> str:
    with httpx.Client(timeout=45) as client:
        r = client.post(f"{BASE_URL}/assistant/voice/synthesize", json={"text": text})
        r.raise_for_status()
        audio_b64 = r.json()["audio_base64"]
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
