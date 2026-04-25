import hashlib
from typing import Optional


def generate_fingerprint(error_type: str, message: str, stack_trace: Optional[str] = None) -> str:
    first_trace_line = stack_trace.strip().split("\n")[0] if stack_trace else ""
    key = f"{error_type}|{message[:100]}|{first_trace_line}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def build_embed_text(error_type: str, message: str, stack_trace: Optional[str] = None) -> str:
    text = f"{error_type}: {message}"
    if stack_trace:
        text += f"\n{stack_trace[:500]}"
    return text
