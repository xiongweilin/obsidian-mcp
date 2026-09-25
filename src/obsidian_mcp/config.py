from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Local paths and bounded subprocess settings for the MCP server."""

    vault_root: Path
    windows_status_script: Path
    cloud_status_script: Path
    ssh_wrapper: Path
    powershell_exe: str
    docker_exe: str | None
    command_timeout_seconds: int = 20

    @classmethod
    def defaults(cls) -> Settings:
        project_root = Path(__file__).resolve().parents[2]
        home = Path.home()
        # Environment overrides exist so tests and CI can point the server at a
        # fixture vault without editing source. Values are paths or integers,
        # never secrets; absent variables keep the platform defaults.
        vault_root = Path(os.environ.get("OBSIDIAN_MCP_VAULT_ROOT", r"D:\agent\obsidian"))
        timeout_raw = os.environ.get("OBSIDIAN_MCP_COMMAND_TIMEOUT_SECONDS")
        timeout = int(timeout_raw) if timeout_raw else 20
        return cls(
            vault_root=vault_root,
            windows_status_script=Path(
                os.environ.get("OBSIDIAN_MCP_WINDOWS_STATUS_SCRIPT")
                or (project_root / "scripts" / "windows_services.ps1")
            ),
            cloud_status_script=Path(
                os.environ.get("OBSIDIAN_MCP_CLOUD_STATUS_SCRIPT")
                or (project_root / "scripts" / "cloud_status.ps1")
            ),
            ssh_wrapper=Path(
                os.environ.get("OBSIDIAN_MCP_SSH_WRAPPER")
                or home / ".local" / "bin" / "Invoke-MetratioSsh.ps1"
            ),
            powershell_exe=shutil.which("pwsh") or "pwsh",
            docker_exe=shutil.which("docker"),
            command_timeout_seconds=timeout,
        )
