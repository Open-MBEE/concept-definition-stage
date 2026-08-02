# The JupyterHub image: hub + OIDC authenticator + docker spawner (config mounted at run).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && npm install -g configurable-http-proxy \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "jupyterhub>=5" "dockerspawner>=13" "oauthenticator>=17"

WORKDIR /srv/jupyterhub
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
