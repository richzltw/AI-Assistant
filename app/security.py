import re
from typing import Iterable

from fastapi import HTTPException


def sanitize_text(text: str, max_len: int) -> str:
    value = text.strip()
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    if not value:
        raise HTTPException(status_code=400, detail="Input cannot be empty")
    if len(value) > max_len:
        raise HTTPException(status_code=400, detail=f"Input exceeds {max_len} chars")
    return value


def enforce_bearer_token(authorization: str | None, expected_token: str) -> None:
    if not expected_token:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


def sanitize_shell_command(command: str, allowed_commands: Iterable[str]) -> str:
    cmd = command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Shell command is empty")

    first_token = cmd.split()[0].lower()
    allowed = {c.lower() for c in allowed_commands}
    if first_token not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{first_token}' is not allowed in sandbox",
        )

    blocked_patterns = [r"[;&|]", r"\$\(", r"`", r">", r"<"]
    if any(re.search(p, cmd) for p in blocked_patterns):
        raise HTTPException(status_code=400, detail="Potentially unsafe shell syntax")

    return cmd
