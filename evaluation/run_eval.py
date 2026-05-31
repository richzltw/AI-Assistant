import json
import statistics
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8080"


def load_cases() -> list[dict]:
    path = Path(__file__).parent / "test_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def score_case(answer: str, must_include: list[str]) -> float:
    answer_lower = answer.lower()
    hits = sum(1 for token in must_include if token.lower() in answer_lower)
    return hits / max(len(must_include), 1)


def run() -> None:
    cases = load_cases()
    scores = []

    with httpx.Client(timeout=45) as client:
        for case in cases:
            payload = {
                "user_id": "eval-user",
                "text": case["prompt"],
                "enable_tools": True,
            }
            resp = client.post(f"{BASE_URL}/assistant/chat", json=payload)
            resp.raise_for_status()
            answer = resp.json().get("answer", "")
            case_score = score_case(answer, case.get("must_include", []))
            scores.append(case_score)
            print(f"{case['id']}: score={case_score:.2f}")
            print(f"answer: {answer[:250]}\n")

    avg = statistics.mean(scores) if scores else 0.0
    print(f"Overall score: {avg:.2f}")


if __name__ == "__main__":
    run()
