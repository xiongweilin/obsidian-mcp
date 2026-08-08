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
