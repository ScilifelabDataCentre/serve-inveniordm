# custom_datacite_provider.py
# -*- coding: utf-8 -*-
"""Custom DataCite PID Provider with configurable landing page URLs.

Features:
- Configurable landing page URL templates
- Separate templates for parent (concept) and version DOIs
"""

from flask import current_app
from invenio_pidstore.models import PIDStatus
from invenio_rdm_records.services.pids.providers.datacite import (
    DataCitePIDProvider,
    DataCiteClient,
)
from invenio_rdm_records.services.pids.providers.base import PIDProvider
from invenio_rdm_records.utils import ChainObject
from datacite.errors import DataCiteError


class CustomDataCiteClient(DataCiteClient):
    """Custom DataCite Client with configurable landing page URLs."""

    def generate_doi(self, record):
        """Generate a DOI using the record's original ID."""
        self.check_credentials()
        prefix = self.cfg("prefix")
        if not prefix:
            raise RuntimeError("Invalid DOI prefix configured.")

        record_id = record.pid.pid_value

        current_app.logger.info(
            f"CustomDataCiteClient: Generating DOI - record_id={record_id}"
        )

        doi_format = self.cfg("format", "{prefix}/{id}")
        if callable(doi_format):
            return doi_format(prefix, record)
        else:
            return doi_format.format(prefix=prefix, id=record_id)


class CustomDataCitePIDProvider(DataCitePIDProvider):
    """DataCite Provider with custom landing page URL support."""

    def __init__(
        self,
        id_,
        client=None,
        serializer=None,
        pid_type="doi",
        is_parent_provider=False,
        **kwargs,
    ):
        """Constructor with parent provider flag."""
        super().__init__(
            id_,
            client=client,
            serializer=serializer,
            pid_type=pid_type,
            **kwargs,
        )
        self.is_parent_provider = is_parent_provider

    APP_CODE_PREFIX = "scilifelab-serve:"

    def _extract_app_code(self, record):
        """Extract app_code from metadata.identifiers (scilifelab-serve:xxx format)."""
        if isinstance(record, ChainObject):
            metadata = record._child.get("metadata", {})
        else:
            metadata = record.get("metadata", {})

        identifiers = metadata.get("identifiers", [])

        for identifier in identifiers:
            id_value = identifier.get("identifier", "")
            if id_value.lower().startswith(self.APP_CODE_PREFIX):
                app_code = id_value.split(":", 1)[1]
                current_app.logger.debug(f"Found app_code: {app_code}")
                return app_code

        return None

    def _extract_record_info(self, record, pid):
        """Extract record information for URL templating."""
        app_code = self._extract_app_code(record)

        if isinstance(record, ChainObject):
            child = record._child
            parent = record._parent
            record_id = child.get("id", pid.pid_value)
            parent_id = parent.get("id", "")
            is_restricted = child["access"]["record"] == "restricted"
        else:
            record_id = record.get("id", pid.pid_value)
            parent_id = record.get("parent", {}).get("id", "")
            is_restricted = record["access"]["record"] == "restricted"

        return {
            "record_id": record_id,
            "parent_id": parent_id,
            "is_restricted": is_restricted,
            "app_code": app_code,
        }

    def _build_landing_url(self, record, pid, fallback_url=None):
        """Build the landing page URL.

        Base URL comes from ``DATACITE_LANDING_PAGE_BASE_URL`` when set
        (allows the public-facing hostname to differ from the Invenio
        internal one), otherwise falls back to ``SITE_UI_URL``.

        - Parent (concept) DOIs   -> ``<base>/records/<app_code>``
        - Version DOIs            -> ``<base>/records/<id>``

        ``<app_code>`` falls back to the record id when no
        ``scilifelab-serve:xxx`` identifier is present.
        """
        base_url = (
            current_app.config.get("DATACITE_LANDING_PAGE_BASE_URL")
            or current_app.config.get("SITE_UI_URL")
            or ""
        ).rstrip("/")
        if not base_url:
            current_app.logger.warning(
                "Neither DATACITE_LANDING_PAGE_BASE_URL nor SITE_UI_URL is "
                "configured; using fallback DOI landing URL."
            )
            return fallback_url

        info = self._extract_record_info(record, pid)
        app_code = info["app_code"] or info["record_id"]

        if self.is_parent_provider:
            url = f"{base_url}/records/{app_code}"
        else:
            url = f"{base_url}/records/{info['record_id']}"

        current_app.logger.info(
            f"Built landing URL: {url} "
            f"(record_id={info['record_id']}, app_code={app_code}, "
            f"is_parent={self.is_parent_provider})"
        )
        return url

    def register(self, pid, record, **kwargs):
        """Register a DOI via the DataCite API with custom URL."""
        info = self._extract_record_info(record, pid)

        if info["is_restricted"]:
            current_app.logger.info(
                f"Skipping DOI registration for restricted record: {pid.pid_value}"
            )
            return False

        local_success = PIDProvider.register(self, pid)
        if not local_success:
            return False

        try:
            doc = self.serializer.dump_obj(record)
            url = self._build_landing_url(record, pid, kwargs.get("url"))

            current_app.logger.info(
                f"Registering DOI {pid.pid_value} with landing URL: {url}"
            )

            self.client.api.public_doi(metadata=doc, url=url, doi=pid.pid_value)
            return True

        except DataCiteError as e:
            current_app.logger.warning(
                f"DataCite error registering DOI {pid.pid_value}"
            )
            self._log_errors(e)
            return False

    def update(self, pid, record, url=None, **kwargs):
        """Update metadata associated with a DOI using custom URL."""
        info = self._extract_record_info(record, pid)

        try:
            if info["is_restricted"]:
                current_app.logger.info(
                    f"Hiding DOI for restricted record: {pid.pid_value}"
                )
                self.client.api.hide_doi(doi=pid.pid_value)
            else:
                doc = self.serializer.dump_obj(record)
                doc["event"] = "publish"
                custom_url = self._build_landing_url(record, pid, url)

                current_app.logger.info(
                    f"Updating DOI {pid.pid_value} with landing URL: {custom_url}"
                )

                self.client.api.update_doi(
                    metadata=doc,
                    doi=pid.pid_value,
                    url=custom_url
                )

        except DataCiteError as e:
            current_app.logger.warning(
                f"DataCite error updating DOI {pid.pid_value}"
            )
            self._log_errors(e)
            return False

        if pid.is_deleted():
            return pid.sync_status(PIDStatus.REGISTERED)

        return True
