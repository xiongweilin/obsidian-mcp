from __future__ import annotations

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
        return cls(
            vault_root=Path(r"D:\download\ratio"),
            windows_status_script=project_root / "scripts" / "windows_services.ps1",
            cloud_status_script=project_root / "scripts" / "cloud_status.ps1",
            ssh_wrapper=home / ".local" / "bin" / "Invoke-RatioSsh.ps1",
            powershell_exe=shutil.which("pwsh") or "pwsh",
            docker_exe=shutil.which("docker"),
        )
