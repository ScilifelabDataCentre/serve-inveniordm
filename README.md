# serve-inveniordm

SciLifeLab Serve's [InvenioRDM](https://inveniordm.docs.cern.ch/) instance.

Builds a custom Docker image on top of the upstream
`registry.cern.ch/inveniosoftware/almalinux:1` base image, with SciLifeLab-specific
customizations (DOI provider, landing-page URLs, theme tweaks).

## Customizations

- **Custom DataCite landing-page URLs** — separate templates for parent
  (concept) DOIs and version DOIs. App codes are extracted from record
  metadata identifiers (`scilifelab-serve:xxx` format), so a record carrying
  `scilifelab-serve:1` resolves to a per-app landing page.
- **Restricted records** are not published to DataCite (DOIs are hidden on
  update and skipped on register).

Provider implementation lives in [site/serve/custom_datacite_provider.py](site/serve/custom_datacite_provider.py);
configuration is in [invenio.cfg](invenio.cfg).

### Landing page URLs

The base URL comes from `DATACITE_LANDING_PAGE_BASE_URL` (set per environment,
e.g. `https://serve.scilifelab.se`) when present, otherwise falls back to
`SITE_UI_URL`. Path components are decided in code:

| DOI type | URL shape |
|---|---|
| Version | `<base>/records/<id>` |
| Parent (concept) | `<base>/records/<app_code>` |

`<app_code>` falls back to the record id when the record has no
`scilifelab-serve:xxx` identifier.

## Repository layout

Scaffolded with `invenio-cli init rdm -c v13.0` (the InvenioRDM v13 cookiecutter
template), then pinned to the latest 13.1.x release via [Pipfile](Pipfile).
Key files:

| Path | Purpose |
|---|---|
| `Dockerfile` | Image build instructions (Almalinux 1 + pipenv). |
| `Pipfile` / `Pipfile.lock` | Pinned Python dependencies (`invenio-app-rdm ~=13.1.0`). |
| `invenio.cfg` | Flask / InvenioRDM configuration, including SciLifeLab customizations. |
| `site/` | The `serve-inveniordm-v13` Python package (custom providers, views, etc.). |
| `app_data/`, `assets/`, `static/`, `templates/`, `translations/` | Invenio instance assets. |
| `docker/` | uWSGI / NGINX configs baked into the image. |

## Build

```bash
docker build --platform linux/amd64 -t serve-inveniordm .
```

## CI / publishing

- `.github/workflows/publish-image.yml` builds and pushes the image to
  `ghcr.io/scilifelabdatacentre/serve-inveniordm` on every push to `main` /
  `develop` and on manual dispatch.
- `.github/workflows/serve-inveniordm.yml` runs a PR-time build + Trivy scan.

## Deployment

Deployed to the cluster via the
[`serve-invenio`](https://github.com/ScilifelabDataCentre/serve-invenio) Helm
chart, which wires this image to PostgreSQL, OpenSearch, Redis and RabbitMQ.

## Upgrading InvenioRDM

Bump `invenio-app-rdm` in [Pipfile](Pipfile), regenerate `Pipfile.lock`
(`pipenv lock` against Python 3.9), and build a new image. For cross-minor
upgrades, check the [upstream release notes](https://inveniordm.docs.cern.ch/releases/)
for required DB/index migrations (typically `invenio alembic upgrade heads`
and `invenio index init`).

## License

MIT — see [LICENSE](LICENSE).
