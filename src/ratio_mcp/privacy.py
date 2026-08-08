import re

_PRIVATE_KEY = re.compile(
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_ASSIGNMENT = re.compile(
    r"(?im)^(\s*(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key|"
    r"authorization|cookie|private[_-]?key)\s*[:=]\s*)([^\r\n]+)$"
)
_BASIC_AUTH_URL = re.compile(r"(?i)(https?://[^\s:/@]+:)([^\s@/]+)(@)")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b")
_KNOWN_TOKEN = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|AKID[A-Za-z0-9]{12,})\b"
)


def redact_sensitive_text(text: str) -> tuple[str, int]:
    """Redact common credential forms without retaining or logging their values."""

    redactions = 0

    def replace_private_key(_: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return "[REDACTED PRIVATE KEY]"

    def replace_assignment(match: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return f"{match.group(1)}[REDACTED]"

    def replace_basic_auth(match: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return f"{match.group(1)}[REDACTED]{match.group(3)}"

    def replace_token(_: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        return "[REDACTED TOKEN]"

    text = _PRIVATE_KEY.sub(replace_private_key, text)
    text = _ASSIGNMENT.sub(replace_assignment, text)
    text = _BASIC_AUTH_URL.sub(replace_basic_auth, text)
    text = _JWT.sub(replace_token, text)
    text = _KNOWN_TOKEN.sub(replace_token, text)
    return text, redactions
