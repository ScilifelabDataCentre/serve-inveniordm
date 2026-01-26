# serve-inveniordm

Custom InvenioRDM Docker image for SciLifeLab Serve with shortened DOI format and configurable landing page URLs.

## Features

- Shortened DOI format: converts `xxxxx-xxxxx` to `xxxx-xxxx`
- Custom landing page URL templates for DOI resolution
- Separate URL templates for parent (concept) and version DOIs
- Extracts app codes from record metadata identifiers (`SERVE:xxx` format)

## DOI Format

Standard InvenioRDM generates DOIs like:
```
10.83812/SCILIFELAB.nfqdb-pwk91
```

This image shortens them to:
```
10.83812/SCILIFELAB.nfqd-pwk9
```

## Configuration

Landing page URLs can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATACITE_LANDING_PAGE_URL_TEMPLATE` | `https://serve.scilifelab.se/records/{app_code}/{id}` | URL template for version DOIs |
| `DATACITE_LANDING_PAGE_URL_TEMPLATE_PARENT` | `https://serve.scilifelab.se/records/{app_code}` | URL template for concept DOIs |

### URL Template Placeholders

- `{id}` - Record ID (shortened to xxxx-xxxx format)
- `{app_code}` - Extracted from metadata identifiers (SERVE:xxx)
- `{parent_id}` - Parent record ID for versioning
- `{doi}` - Full DOI value
- `{prefix}` - DataCite prefix

## Building

Build the image locally:

```bash
docker build -t serve-inveniordm ./serve-inveniordm
```

## Testing

Run the test suite:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r ./serve-inveniordm/tests/requirements.txt

# Build and test
docker build -t inveniordm-dev-img ./serve-inveniordm
IMAGE_NAME=inveniordm-dev-img python3 -m pytest ./serve-inveniordm/
```

Or use the convenience script:

```bash
./run_inveniordm.sh
```

## Base Image

Built on top of `ghcr.io/inveniosoftware/demo-inveniordm/demo-inveniordm:13.0.0-post1`

## CI/CD

The GitHub Actions workflow:

1. Builds the Docker image on push to `serve-inveniordm/` path
2. Runs Trivy vulnerability scanner
3. Executes tests
4. Pushes to GHCR on main branch (tagged with timestamp and `latest`)

## File Structure

```
serve-inveniordm/
├── Dockerfile
├── custom_datacite_provider.py    # Custom DataCite PID provider
├── custom_config.py               # Configuration loader
├── tests/
│   ├── requirements.txt
│   └── test_connection.py
└── README.md
```

## License

MIT