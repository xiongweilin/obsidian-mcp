from __future__ import annotations

import json
import subprocess
from datetime import datetime

from ratio_mcp.config import Settings
from ratio_mcp.models import RuntimeItem, RuntimeStatusResponse


class RuntimeStatusService:
    """Execute only fixed, read-only runtime queries and return allowlisted fields."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def query(self, scope: str, query: str = "", limit: int = 50) -> RuntimeStatusResponse:
        clean_query = " ".join(query.split())
        if len(clean_query) > 100:
            raise ValueError("Runtime filter exceeds 100 characters.")

        warnings: list[str] = []
        if scope == "windows_services":
            items, warnings = self._windows_services(clean_query, limit)
        elif scope == "local_docker":
            items, warnings = self._local_docker(clean_query, limit)
        elif scope == "cloud":
            items, warnings = self._cloud(clean_query, limit)
        else:
            raise ValueError("Unsupported runtime scope.")

        return RuntimeStatusResponse(
            scope=scope,
            observed_at=datetime.now().astimezone().isoformat(),
            query=clean_query,
            returned=len(items),
            items=items,
            warnings=warnings,
        )

    def _windows_services(self, query: str, limit: int) -> tuple[list[RuntimeItem], list[str]]:
        script = self.settings.windows_status_script
        if not script.is_file():
            return [], ["Windows service query script is unavailable."]
        result = _run(
            [
                self.settings.powershell_exe,
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(script),
                "-Query",
                query,
                "-Limit",
                str(limit),
            ],
            self.settings.command_timeout_seconds,
        )
        if result.returncode != 0:
            return [], [f"Windows service query failed with exit code {result.returncode}."]
        try:
            rows = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            return [], ["Windows service query returned invalid structured data."]
        items = [
            RuntimeItem(
                kind="windows_service",
                name=str(row.get("name", "")),
                state=str(row.get("state", "unknown")),
                summary=(
                    f"display={row.get('display_name', '')}; start_mode={row.get('start_mode', '')}"
                ),
            )
            for row in rows[:limit]
        ]
        return items, []

    def _local_docker(self, query: str, limit: int) -> tuple[list[RuntimeItem], list[str]]:
        if not self.settings.docker_exe:
            return [], ["Docker CLI is unavailable."]
        result = _run(
            [self.settings.docker_exe, "ps", "--all", "--format", "{{json .}}"],
            self.settings.command_timeout_seconds,
        )
        if result.returncode != 0:
            return [], [f"Local Docker query failed with exit code {result.returncode}."]
        rows, invalid = parse_json_lines(result.stdout)
        items = filter_runtime_items(
            [
                RuntimeItem(
                    kind="docker_container",
                    name=str(row.get("Names", "")),
                    state=str(row.get("State") or row.get("Status") or "unknown"),
                    summary=f"image={row.get('Image', '')}; status={row.get('Status', '')}",
                )
                for row in rows
            ],
            query,
            limit,
        )
        warnings = [f"Ignored {invalid} invalid Docker result row(s)."] if invalid else []
        return items, warnings

    def _cloud(self, query: str, limit: int) -> tuple[list[RuntimeItem], list[str]]:
        wrapper = self.settings.ssh_wrapper
        if not wrapper.is_file():
            return [], ["Cloud SSH wrapper is unavailable."]
        script = self.settings.cloud_status_script
        if not script.is_file():
            return [], ["Cloud status query script is unavailable."]

        warnings: list[str] = []
        result = _run(
            [
                self.settings.powershell_exe,
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(script),
                "-Wrapper",
                str(wrapper),
            ],
            self.settings.command_timeout_seconds * 2 + 5,
        )
        if result.returncode != 0:
            return [], [f"Cloud status query failed with exit code {result.returncode}."]
        try:
            payload = json.loads(result.stdout)
            systemd_payload = payload["systemd"]
            docker_payload = payload["docker"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return [], ["Cloud status query returned invalid structured data."]

        if int(systemd_payload.get("exit_code", 1)) == 0:
            items = parse_systemd_units(_join_lines(systemd_payload.get("lines")))
        else:
            items = []
            warnings.append("Cloud systemd query failed.")

        if int(docker_payload.get("exit_code", 1)) == 0:
            docker_items, invalid = parse_docker_table(
                _join_lines(docker_payload.get("lines")), kind="cloud_docker_container"
            )
            items.extend(docker_items)
            if invalid:
                warnings.append(f"Ignored {invalid} invalid cloud Docker result row(s).")
        else:
            warnings.append("Cloud Docker query failed.")

        return filter_runtime_items(items, query, limit), warnings


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args=args, returncode=124, stdout="", stderr="")


def parse_json_lines(text: str) -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    invalid = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            invalid += 1
    return rows, invalid


def _join_lines(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def parse_docker_table(text: str, kind: str) -> tuple[list[RuntimeItem], int]:
    items: list[RuntimeItem] = []
    invalid = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 3)
        if len(parts) != 4:
            invalid += 1
            continue
        name, state, image, status = parts
        items.append(
            RuntimeItem(
                kind=kind,
                name=name,
                state=state or "unknown",
                summary=f"image={image}; status={status}",
            )
        )
    return items, invalid


def parse_systemd_units(text: str) -> list[RuntimeItem]:
    items: list[RuntimeItem] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("●"):
            stripped = stripped.lstrip("●").strip()
        if not stripped or stripped.startswith("UNIT "):
            continue
        parts = stripped.split(None, 4)
        if len(parts) < 4 or not parts[0].endswith(".service"):
            continue
        description = parts[4] if len(parts) == 5 else ""
        items.append(
            RuntimeItem(
                kind="systemd_service",
                name=parts[0],
                state=f"{parts[2]}/{parts[3]}",
                summary=description,
            )
        )
    return items


def filter_runtime_items(items: list[RuntimeItem], query: str, limit: int) -> list[RuntimeItem]:
    if query:
        needle = query.casefold()
        items = [
            item
            for item in items
            if needle in f"{item.kind} {item.name} {item.state} {item.summary}".casefold()
        ]
    return sorted(items, key=lambda item: (item.kind, item.name.casefold()))[:limit]
