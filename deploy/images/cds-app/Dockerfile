# The per-user cds-app image (K3): Voilà renders the thin notebook; no code surface.
# Build context is the repo root: docker build -f deploy/images/cds-app/Dockerfile .
FROM python:3.12-slim

RUN useradd --create-home --shell /usr/sbin/nologin cds
WORKDIR /home/cds/app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[app]" && rm -rf src pyproject.toml README.md LICENSE

# voila.json comes from the single hardened source (cds.app.notebook_config, K3) —
# the deploy tier never hand-writes render policy
RUN python -c "from pathlib import Path; from cds.app.notebook_config import write_voila_json; write_voila_json(Path('/home/cds/app'))" \
    && python -c "import shutil, cds.app.widgets as w; from pathlib import Path; shutil.copy(Path(w.__file__).parent / 'notebook' / 'concept_definition_app.ipynb', '/home/cds/app/')"

RUN chown -R cds:cds /home/cds
USER cds

EXPOSE 8888
CMD ["voila", "--no-browser", "--Voila.ip=0.0.0.0", "--port=8888", \
     "/home/cds/app/concept_definition_app.ipynb"]
