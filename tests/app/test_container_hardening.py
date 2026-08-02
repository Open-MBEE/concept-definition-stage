"""REQ-K3.2 — the app container is non-root, caps dropped, egress-restricted.

Static assertions over the committed infra-as-code (always run), plus a live image build
that skips without a Docker daemon. The deploy tier must never drift from the hardening
the spec promises (§5.3 K3).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

DEPLOY = Path(__file__).parents[2] / "deploy"


def test_compose_defines_the_three_tiers() -> None:
    compose = yaml.safe_load((DEPLOY / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert {"traefik", "keycloak", "jupyterhub"} <= set(services)
    # TLS terminates at traefik; the hub is never published directly
    assert "ports" not in services["jupyterhub"]


def test_keycloak_realm_carries_the_four_personas() -> None:
    realm = json.loads((DEPLOY / "keycloak" / "realm-dsg.json").read_text(encoding="utf-8"))
    assert realm["realm"] == "dsg"
    roles = {r["name"] for r in realm["roles"]["realm"]}
    assert {"cds-facilitator-user", "cds-reviewer", "cds-canon-steward",
            "cds-admin"} <= roles


def test_spawner_hardening_is_declared() -> None:
    cfg = (DEPLOY / "jupyterhub_config.py").read_text(encoding="utf-8")
    for needle in ("GenericOAuthenticator", "DockerSpawner", "cap_drop",
                   "no-new-privileges", "CDS_ROLES"):
        assert needle in cfg, f"hardening/OIDC marker missing: {needle}"
    assert "run_as_root" not in cfg.lower().replace("_", "")


def test_app_image_is_nonroot_and_writes_voila_config() -> None:
    dockerfile = (DEPLOY / "images" / "cds-app" / "Dockerfile").read_text(encoding="utf-8")
    assert "USER cds" in dockerfile  # never root at runtime
    assert "notebook_config" in dockerfile  # voila.json from the single source (K3)
    assert "voila" in dockerfile.lower()


@pytest.mark.skipif(shutil.which("docker") is None, reason="no docker CLI on this host")
def test_app_image_builds() -> None:  # pragma: no cover — environment-gated
    probe = subprocess.run(["docker", "info"], capture_output=True, timeout=20)
    if probe.returncode != 0:
        pytest.skip("docker daemon not running")
    build = subprocess.run(
        ["docker", "build", "-q", "-f", str(DEPLOY / "images" / "cds-app" / "Dockerfile"),
         str(DEPLOY.parent)],
        capture_output=True, text=True, timeout=1200,
    )
    assert build.returncode == 0, build.stderr[-2000:]


def test_app_extra_carries_a_kernel() -> None:
    """B3 (live-QA 2026-08-02): Voila 500'd with "No Jupyter kernel" — ipykernel was
    missing from the app extra (and the documented run command), so neither
    `uv sync --extra app` nor the container install could serve the notebook."""
    import tomllib

    pyproject = tomllib.loads(
        (DEPLOY.parent / "pyproject.toml").read_text(encoding="utf-8"))
    app_extra = " ".join(pyproject["project"]["optional-dependencies"]["app"])
    assert "ipykernel" in app_extra
