# serve-inveniordm

Custom InvenioRDM Docker image for SciLifeLab Serve with shortened DOI format and configurable landing page URLs.

## Features

- Shortened DOI format: `xxxxx-xxxxx` → `xxxx-xxxx` using hybrid approach
- Custom landing page URL templates for DOI resolution
- Separate URL templates for parent (concept) and version DOIs
- Extracts app codes from record metadata identifiers (`SERVE:xxx` format)

## DOI Shortening

InvenioRDM generates 10-character IDs (e.g., `nfqdb-pwk91`). This image shortens them to 8 characters using a hybrid approach:

- **First 2 chars** from each part are preserved (readability)
- **Next 2 chars** come from SHA256 hash of full ID (uniqueness)

Example: `nfqdb-pwk91` → `nfa3-pwf2`

This prevents collisions that would occur with simple truncation. See `custom_datacite_provider.py` for detailed documentation.

## Configuration

Landing page URLs can be configured via environment variables:

| Variable | Default |
|----------|---------|
| `DATACITE_LANDING_PAGE_URL_TEMPLATE` | `https://serve.scilifelab.se/records/{app_code}/{id}` |
| `DATACITE_LANDING_PAGE_URL_TEMPLATE_PARENT` | `https://serve.scilifelab.se/records/{app_code}` |

Available placeholders: `{id}`, `{app_code}`, `{parent_id}`, `{doi}`, `{prefix}`

## Building

```bash
docker build --platform linux/amd64 -t serve-inveniordm .
```

## Testing

```bash
pip install -r ./tests/requirements.txt
docker build --platform linux/amd64 -t inveniordm-dev-img .
IMAGE_NAME=inveniordm-dev-img python3 -m pytest .
```

## Base Image

`ghcr.io/inveniosoftware/demo-inveniordm/demo-inveniordm:13.0.0-post1`

## License

MIT
