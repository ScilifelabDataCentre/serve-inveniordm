# Dockerfile
# Custom InvenioRDM with shortened DOI format and custom landing page URLs

FROM ghcr.io/inveniosoftware/demo-inveniordm/demo-inveniordm:13.0.0-post1

LABEL maintainer="SciLifeLab Data Centre <serve@scilifelab.se>"
LABEL description="InvenioRDM with shortened DOI (xxxx-xxxx) and custom landing page URLs"
LABEL org.opencontainers.image.source="https://github.com/scilifelabdatacentre/serve-inveniordm"

USER root

# Create custom modules directory
RUN mkdir -p /opt/invenio/var/instance/custom_modules

# Copy custom provider module
COPY custom_datacite_provider.py /opt/invenio/var/instance/custom_modules/

# Copy configuration loader
COPY custom_config.py /opt/invenio/var/instance/

# Create __init__.py for the custom modules package
RUN touch /opt/invenio/var/instance/custom_modules/__init__.py

# Append configuration to invenio.cfg
RUN echo '' >> /opt/invenio/var/instance/invenio.cfg && \
    echo '# =============================================' >> /opt/invenio/var/instance/invenio.cfg && \
    echo '# Custom DOI Format and Landing Page URLs' >> /opt/invenio/var/instance/invenio.cfg && \
    echo '# =============================================' >> /opt/invenio/var/instance/invenio.cfg && \
    echo 'import sys' >> /opt/invenio/var/instance/invenio.cfg && \
    echo 'sys.path.insert(0, "/opt/invenio/var/instance")' >> /opt/invenio/var/instance/invenio.cfg && \
    echo 'exec(open("/opt/invenio/var/instance/custom_config.py").read())' >> /opt/invenio/var/instance/invenio.cfg

# Set proper ownership
RUN chown -R 1000:1000 /opt/invenio/var/instance/

USER 1000

EXPOSE 5000