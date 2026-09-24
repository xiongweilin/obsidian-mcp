from obsidian_mcp.privacy import redact_sensitive_text


def test_redacts_multiple_secret_forms() -> None:
    text = (
        "password=hello\n"
        "URL=https://user:pass@example.com\n"
        "token: eyJabcdefghijk.abcdefghijk.abcdefgh"
    )

    redacted, count = redact_sensitive_text(text)

    assert "hello" not in redacted
    assert "pass@example" not in redacted
    assert "eyJabcdefghijk" not in redacted
    assert count == 3
