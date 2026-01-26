"""Tests for the InvenioRDM custom image.

These tests verify that the Docker image was built correctly by checking
that custom files are present. InvenioRDM requires external services
(PostgreSQL, Elasticsearch, Redis) to run, so we only test the image
contents, not runtime behavior.
"""

import os
import pytest
import docker


client = docker.from_env()
IMAGE_NAME = os.environ.get("IMAGE_NAME", "ghcr.io/scilifelabdatacentre/serve-inveniordm:latest")


class TestImageContents:
    """Test that the image contains all required custom files."""

    def test_image_exists(self):
        """Test that the image was built successfully."""
        images = client.images.list(name=IMAGE_NAME)
        assert len(images) >= 1, f"Image {IMAGE_NAME} should exist"

    def test_custom_modules_directory_exists(self):
        """Test that custom modules directory exists."""
        result = client.containers.run(
            IMAGE_NAME,
            command="ls -la /opt/invenio/var/instance/custom_modules/",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8")
        assert "custom_datacite_provider.py" in output

    def test_custom_datacite_provider_exists(self):
        """Test that custom_datacite_provider.py exists and has content."""
        result = client.containers.run(
            IMAGE_NAME,
            command="cat /opt/invenio/var/instance/custom_modules/custom_datacite_provider.py",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8")
        assert "CustomDataCitePIDProvider" in output
        assert "CustomDataCiteClient" in output

    def test_custom_config_exists(self):
        """Test that custom_config.py exists and has content."""
        result = client.containers.run(
            IMAGE_NAME,
            command="cat /opt/invenio/var/instance/custom_config.py",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8")
        assert "DATACITE_LANDING_PAGE_URL_TEMPLATE" in output
        assert "RDM_PERSISTENT_IDENTIFIER_PROVIDERS" in output

    def test_invenio_cfg_includes_custom_config(self):
        """Test that invenio.cfg includes the custom configuration loader."""
        result = client.containers.run(
            IMAGE_NAME,
            command="cat /opt/invenio/var/instance/invenio.cfg",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8")
        assert "Custom DOI Format" in output
        assert "custom_config.py" in output

    def test_init_file_exists(self):
        """Test that __init__.py exists in custom_modules."""
        result = client.containers.run(
            IMAGE_NAME,
            command="ls /opt/invenio/var/instance/custom_modules/__init__.py",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8")
        assert "__init__.py" in output

    def test_file_ownership(self):
        """Test that files are owned by the correct user (UID 1000)."""
        result = client.containers.run(
            IMAGE_NAME,
            command="stat -c '%u' /opt/invenio/var/instance/custom_config.py",
            remove=True,
            entrypoint="",
        )
        output = result.decode("utf-8").strip()
        assert output == "1000", f"File should be owned by UID 1000, got {output}"