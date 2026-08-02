<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Hosting the web app (T8c) — self-hosted single-tenant

> **Honest limits:** this runbook stands up the spec's §6.2 topology from `deploy/`;
> the login → spawn → author → commit smoke must be validated on your host (it needs real
> DNS + TLS). Identity-derived roles close spec §11 D10's precondition — signing/anchoring
> remains open there.

The composition (`deploy/docker-compose.yml`): **Traefik** (TLS, WS passthrough) →
**Keycloak** (realm `dsg`, the four personas as realm roles) → **JupyterHub**
(`GenericOAuthenticator` + a hardened `DockerSpawner`) → one **cds-app** container per user
(Voilà, no code surface, non-root, all caps dropped).

## Bring-up

1. DNS: point `app.example.org` and `auth.example.org` at the host.
2. Secrets (environment or an operator secrets file — never committed):
   `CDS_ACME_EMAIL`, `CDS_APP_HOST`, `CDS_AUTH_HOST`, `CDS_KC_ADMIN`,
   `CDS_KC_ADMIN_PASSWORD`, `CDS_OAUTH_CLIENT_SECRET` (mirror it on the `cds-hub` client
   in Keycloak after first boot).
3. Build the per-user image, then start:

```bash
docker build -t cds-app:latest -f deploy/images/cds-app/Dockerfile .
```

```bash
docker compose -f deploy/docker-compose.yml up -d
```

4. In Keycloak (`https://auth.example.org`, realm `dsg`): create users and grant realm
   roles. Roles flow through the OIDC claim into each spawned container (`CDS_ROLES`) and
   bind the session — a facilitator-user authors candidates; only `cds-reviewer` can
   commit; the UI never asks for or accepts role claims (K2).
5. Smoke: log in → a container spawns → author a record → verify (advisory) → as a
   reviewer, commit → confirm the changeplan/provenance/audit artifacts in the analysis
   repo.

## What enforces what

| Constraint | Mechanism here |
|---|---|
| N2 one auditable identity point | Keycloak realm `dsg`; hub is OIDC-only |
| K2 roles are identity-derived | OIDC `realm_roles` claim → spawner env → session; never caller-claimed |
| K3 no code surface / isolation | Voilà hardened config (from `cds.app.notebook_config`), non-root `USER cds`, `cap_drop: ALL`, `no-new-privileges`, internal network, no published ports |
| N1 self-hosted single-tenant | everything in this compose; hosted LLM optional via ADR-8 triplet |

## Related docs

[Hosting locally](hosting-local.md) · [Playground](playground.md) ·
[Architecture spec](architecture/cds-web-app.md) · [Factoring](architecture/factoring.md)
