from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATHS = (
    REPOSITORY_ROOT / "infra/nginx/default.conf",
    REPOSITORY_ROOT / "infra/nginx/global-web.conf",
)
UPLOAD_PROXY_LOCATION = (
    "location ~ ^/api/v1/(?:resume|job-descriptions|knowledge/collections/[^/]+)"
    "/uploads/proxy$ {"
)


def _location_body(config: str, marker: str) -> str:
    return config.split(marker, 1)[1].split("\n  }", 1)[0]


def test_material_proxy_routes_have_a_scoped_body_allowance() -> None:
    for config_path in CONFIG_PATHS:
        config = config_path.read_text(encoding="utf-8")

        assert UPLOAD_PROXY_LOCATION in config
        scoped_body = _location_body(config, UPLOAD_PROXY_LOCATION)
        assert "client_max_body_size 21m;" in scoped_body

        generic_api_body = _location_body(config, "location /api/ {")
        assert "client_max_body_size" not in generic_api_body
