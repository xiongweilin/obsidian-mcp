from __future__ import annotations

from obsidian_mcp.config import Settings
from obsidian_mcp.runtime import RuntimeStatusService


def main() -> None:
    service = RuntimeStatusService(Settings.defaults())
    failed = False
    for scope in ("windows_services", "local_docker", "cloud"):
        result = service.query(scope, limit=5)
        print(f"{scope}: items={result.returned}, warnings={len(result.warnings)}")
        failed = failed or bool(result.warnings)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
