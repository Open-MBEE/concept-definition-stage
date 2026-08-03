"""JupyterHub configuration — OIDC identity (N2) + per-user hardened containers (K3.2).

Identity is established at exactly one auditable point (Keycloak, realm `dsg`); realm
roles flow from the OIDC claim into the spawned container's environment (`CDS_ROLES`),
where the session context binds them — roles are IDENTITY-derived, never caller-claimed
(K2). Each user gets an isolated `cds-app` container: non-root, all capabilities dropped,
no privilege escalation, on an internal network with no published ports.
"""

import json
import os

c = get_config()  # noqa: F821 — provided by JupyterHub at load time

# ---------------------------------------------------------------- identity (N2, Keycloak)
from oauthenticator.generic import GenericOAuthenticator  # noqa: E402

auth_host = os.environ["CDS_AUTH_HOST"]
c.JupyterHub.authenticator_class = GenericOAuthenticator
c.GenericOAuthenticator.client_id = "cds-hub"
c.GenericOAuthenticator.client_secret = os.environ["CDS_OAUTH_CLIENT_SECRET"]
c.GenericOAuthenticator.oauth_callback_url = (
    f"https://{os.environ['CDS_APP_HOST']}/hub/oauth_callback"
)
c.GenericOAuthenticator.authorize_url = (
    f"https://{auth_host}/realms/dsg/protocol/openid-connect/auth"
)
c.GenericOAuthenticator.token_url = (
    f"https://{auth_host}/realms/dsg/protocol/openid-connect/token"
)
c.GenericOAuthenticator.userdata_url = (
    f"https://{auth_host}/realms/dsg/protocol/openid-connect/userinfo"
)
c.GenericOAuthenticator.username_claim = "preferred_username"
c.GenericOAuthenticator.scope = ["openid", "profile", "email", "roles"]
c.GenericOAuthenticator.claim_groups_key = "realm_roles"
c.GenericOAuthenticator.allowed_groups = {
    "cds-facilitator-user", "cds-reviewer", "cds-canon-steward", "cds-admin"
}
c.GenericOAuthenticator.admin_groups = {"cds-admin"}
c.GenericOAuthenticator.enable_auth_state = True  # roles ride the auth state to spawn

# ------------------------------------------------------- isolation + hardening (K3.2)
from dockerspawner import DockerSpawner  # noqa: E402


class CdsSpawner(DockerSpawner):
    """DockerSpawner that injects identity-derived roles into the session (K2)."""

    async def start(self):  # type: ignore[override]
        auth_state = await self.user.get_auth_state() or {}
        userinfo = auth_state.get("oauth_user", {})
        roles = [r for r in userinfo.get("realm_roles", [])
                 if isinstance(r, str) and r.startswith("cds-")]
        self.environment["CDS_ROLES"] = json.dumps(sorted(roles))
        self.environment["CDS_APPROVER"] = (
            f"https://{os.environ['CDS_APP_HOST']}/agent/{self.user.name}"
        )
        return await super().start()


c.JupyterHub.spawner_class = CdsSpawner
c.DockerSpawner.image = os.environ.get("DOCKER_NOTEBOOK_IMAGE", "cds-app:latest")
c.DockerSpawner.network_name = "cds-internal"
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True
c.DockerSpawner.extra_host_config = {
    "cap_drop": ["ALL"],
    "security_opt": ["no-new-privileges:true"],
    "read_only": False,  # the session scratch dir is the writable surface
    "mem_limit": "1g",
    "pids_limit": 256,
}
c.DockerSpawner.extra_create_kwargs = {"user": "cds"}  # never root in the container
c.DockerSpawner.notebook_dir = "/home/cds/app"
c.DockerSpawner.default_url = "/voila/render/concept_definition_app.ipynb"

c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "jupyterhub"
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/data/cookie_secret"
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"
