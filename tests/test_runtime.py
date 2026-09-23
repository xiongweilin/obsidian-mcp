from ratio_mcp.runtime import (
    filter_runtime_items,
    parse_docker_table,
    parse_json_lines,
    parse_systemd_units,
)


def test_parse_systemd_units_returns_allowlisted_fields() -> None:
    items = parse_systemd_units(
        "nginx.service loaded active running A high performance web server\n"
        "demo.service loaded inactive dead Demo worker\n"
    )

    assert [(item.name, item.state) for item in items] == [
        ("nginx.service", "active/running"),
        ("demo.service", "inactive/dead"),
    ]
    assert items[0].summary == "A high performance web server"


def test_parse_json_lines_counts_invalid_rows() -> None:
    rows, invalid = parse_json_lines('{"Names":"one"}\nnot-json\n[1]\n')

    assert rows == [{"Names": "one"}]
    assert invalid == 2


def test_filter_runtime_items_is_case_insensitive() -> None:
    items = parse_systemd_units(
        "nginx.service loaded active running Web server\n"
        "docker.service loaded active running Docker daemon\n"
    )

    filtered = filter_runtime_items(items, "DOCKER", 10)

    assert [item.name for item in filtered] == ["docker.service"]


def test_parse_docker_table_preserves_status_spaces() -> None:
    items, invalid = parse_docker_table(
        "gateway-nginx\trunning\tnginx:stable\tUp 2 hours\n", "cloud_docker_container"
    )

    assert invalid == 0
    assert items[0].name == "gateway-nginx"
    assert items[0].summary == "image=nginx:stable; status=Up 2 hours"


def test_runtime_service_windows_success(tmp_path, monkeypatch) -> None:
    import subprocess

    from ratio_mcp.config import Settings
    from ratio_mcp.runtime import RuntimeStatusService
    import ratio_mcp.runtime as runtime

    script = tmp_path / "windows.ps1"
    script.write_text("# fixture\n", encoding="utf-8")
    settings = Settings(
        vault_root=tmp_path,
        windows_status_script=script,
        cloud_status_script=tmp_path / "cloud.ps1",
        ssh_wrapper=tmp_path / "ssh.ps1",
        powershell_exe="pwsh",
        docker_exe="docker",
    )
    monkeypatch.setattr(
        runtime,
        "_run",
        lambda args, timeout: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='[{"name":"svc","state":"Running","display_name":"Service","start_mode":"Auto"}]',
            stderr="",
        ),
    )

    result = RuntimeStatusService(settings).query("windows_services", query="svc", limit=5)

    assert result.returned == 1
    assert result.items[0].name == "svc"
    assert result.items[0].state == "Running"
    assert result.warnings == []


def test_runtime_service_local_docker_reports_invalid_rows(tmp_path, monkeypatch) -> None:
    import subprocess

    from ratio_mcp.config import Settings
    from ratio_mcp.runtime import RuntimeStatusService
    import ratio_mcp.runtime as runtime

    settings = Settings(
        vault_root=tmp_path,
        windows_status_script=tmp_path / "windows.ps1",
        cloud_status_script=tmp_path / "cloud.ps1",
        ssh_wrapper=tmp_path / "ssh.ps1",
        powershell_exe="pwsh",
        docker_exe="docker",
    )
    monkeypatch.setattr(
        runtime,
        "_run",
        lambda args, timeout: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"Names":"api","State":"running","Image":"demo","Status":"Up"}\nnot-json\n',
            stderr="",
        ),
    )

    result = RuntimeStatusService(settings).query("local_docker", query="API", limit=5)

    assert result.returned == 1
    assert result.items[0].kind == "docker_container"
    assert result.warnings == ["Ignored 1 invalid Docker result row(s)."]


def test_runtime_service_cloud_combines_systemd_and_docker(tmp_path, monkeypatch) -> None:
    import json
    import subprocess

    from ratio_mcp.config import Settings
    from ratio_mcp.runtime import RuntimeStatusService
    import ratio_mcp.runtime as runtime

    cloud = tmp_path / "cloud.ps1"
    wrapper = tmp_path / "ssh.ps1"
    cloud.write_text("# fixture\n", encoding="utf-8")
    wrapper.write_text("# fixture\n", encoding="utf-8")
    settings = Settings(
        vault_root=tmp_path,
        windows_status_script=tmp_path / "windows.ps1",
        cloud_status_script=cloud,
        ssh_wrapper=wrapper,
        powershell_exe="pwsh",
        docker_exe=None,
    )
    payload = {
        "systemd": {
            "exit_code": 0,
            "lines": ["api.service loaded active running API"],
        },
        "docker": {
            "exit_code": 0,
            "lines": ["proxy\trunning\tnginx:stable\tUp 1 hour", "bad-row"],
        },
    }
    monkeypatch.setattr(
        runtime,
        "_run",
        lambda args, timeout: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        ),
    )

    result = RuntimeStatusService(settings).query("cloud", limit=10)

    assert {item.name for item in result.items} == {"api.service", "proxy"}
    assert result.warnings == ["Ignored 1 invalid cloud Docker result row(s)."]
