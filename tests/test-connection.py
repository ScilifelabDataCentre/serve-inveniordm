"""Tests for the InvenioRDM custom image."""

import os
import time
import requests
import docker


# Settings
PORT = 5000  # InvenioRDM default port
TIMEOUT_CALL = 10  # Request timeout in seconds
STARTUP_WAIT = 30  # Initial container startup wait


client = docker.from_env()
container = client.containers.run(
    os.environ["IMAGE_NAME"],
    ports={
        f"{PORT}/tcp": PORT,
    },
    environment={
        "INVENIO_SECRET_KEY": "test-secret-key-for-testing-only",
        "INVENIO_SECURITY_SESSION_COOKIE_SECURE": "false",
    },
    detach=True,
)
time.sleep(STARTUP_WAIT)
container.reload()


def test_inveniordm_container():
    """Test that the InvenioRDM container is running."""
    assert container.status == "running"


def test_inveniordm_port():
    """Test that the expected container port is exposed."""
    assert len(container.ports) >= 1, "At least 1 port should be exposed"
    assert f"{PORT}/tcp" in container.ports


def test_custom_modules_exist():
    """Test that custom modules are present in the container."""
    exit_code, output = container.exec_run(
        "ls -la /opt/invenio/var/instance/custom_modules/"
    )
    assert exit_code == 0, "Custom modules directory should exist"
    assert b"custom_datacite_provider.py" in output


def test_custom_config_exists():
    """Test that custom config file is present."""
    exit_code, output = container.exec_run(
        "ls -la /opt/invenio/var/instance/custom_config.py"
    )
    assert exit_code == 0, "Custom config file should exist"


def test_invenio_cfg_modified():
    """Test that invenio.cfg includes custom configuration."""
    exit_code, output = container.exec_run(
        "cat /opt/invenio/var/instance/invenio.cfg"
    )
    assert exit_code == 0
    assert b"Custom DOI Format" in output, "invenio.cfg should include custom config"


def test_shutdown():
    """Test stopping the container."""
    container.stop()
    container.reload()
    assert container.status == "exited"
    container.remove()


# Private methods


def _get_url(container):
    """Gets the URL of the container."""
    ip = container.attrs["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]
    url = f"http://{ip}:{PORT}"
    return url
