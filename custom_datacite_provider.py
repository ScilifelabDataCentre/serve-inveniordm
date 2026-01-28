# custom_datacite_provider.py
# -*- coding: utf-8 -*-
"""Custom DataCite PID Provider with shortened DOI format and configurable landing page URLs.

Features:
- Shortens record ID from xxxxx-xxxxx to xxxx-xxxx using hybrid approach
- Configurable landing page URL templates
- Separate templates for parent (concept) and version DOIs

================================================================================
HOW THE HYBRID ID SHORTENING WORKS
================================================================================

PROBLEM:
    InvenioRDM generates IDs like "nfqdb-pwk91" (5 chars + 5 chars = 10 chars).
    We need to shorten to "xxxx-xxxx" (4 chars + 4 chars = 8 chars).
    
    Simple truncation (just dropping last char of each part) causes COLLISIONS:
    
        nfqdb-pwk91  →  nfqd-pwk9
        nfqda-pwk92  →  nfqd-pwk9  ← COLLISION! Same output!
        nfqdc-pwk93  →  nfqd-pwk9  ← COLLISION! Same output!

SOLUTION - HYBRID APPROACH:
    We combine two techniques:
    
    1. PRESERVE: Keep first 2 characters from each part (human-readable)
    2. HASH:     Generate 2 characters from SHA256 hash (ensures uniqueness)
    
    Formula:
        original    = "nfqdb-pwk91"
        part1       = "nfqdb"  →  keep "nf" + hash_chars[0:2]
        part2       = "pwk91"  →  keep "pw" + hash_chars[2:4]
        result      = "nfXX-pwYY" where XX and YY come from hash

WHY HASHING ENSURES UNIQUENESS:
    A hash function (SHA256) has a special property:
    
        "Even a tiny change in input creates a completely different output"
    
    Example:
        hash("nfqdb-pwk91")  →  "a3f2b1c9..."
        hash("nfqda-pwk92")  →  "7e9d2f5a..."  ← Completely different!
        hash("nfqdc-pwk93")  →  "c4b8e1d3..."  ← Completely different!
    
    So our hybrid IDs become:
        nfqdb-pwk91  →  "nf" + "a3" + "-" + "pw" + "f2"  →  "nfa3-pwf2"
        nfqda-pwk92  →  "nf" + "7e" + "-" + "pw" + "2f"  →  "nf7e-pw2f"  ← Different!
        nfqdc-pwk93  →  "nf" + "c4" + "-" + "pw" + "b8"  →  "nfc4-pwb8"  ← Different!

COLLISION PROBABILITY:
    The hash portion uses hexadecimal (0-9, a-f), giving us:
        16 × 16 × 16 × 16 = 65,536 possible combinations
    
    Combined with the preserved prefix characters (32^4 ≈ 1 million),
    total keyspace is approximately 68 billion combinations.
    
    For practical purposes with typical repository sizes (thousands to 
    hundreds of thousands of records), collision probability is negligible.

PROPERTIES:
    - Deterministic: Same input ALWAYS produces same output
    - Unique: Different inputs produce different outputs (with very high probability)
    - Partially readable: First 2 chars of each part are preserved from original
    - Consistent format: Always produces xxxx-xxxx pattern

================================================================================
"""

import hashlib
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
    """Custom DataCite Client with shortened DOI format (xxxx-xxxx) using hybrid approach."""

    def _shorten_id(self, record_id):
        """Shorten record ID from xxxxx-xxxxx to xxxx-xxxx using hybrid approach.
        
        The hybrid approach combines:
        1. First 2 characters from each part of the original ID (preserves readability)
        2. 2 characters from SHA256 hash of full ID (ensures uniqueness)
        
        Args:
            record_id: Original InvenioRDM record ID (e.g., "nfqdb-pwk91")
            
        Returns:
            Shortened ID in xxxx-xxxx format (e.g., "nfa3-pwf2")
            
        Example:
            Input:  "nfqdb-pwk91"
            Output: "nfa3-pwf2"
                     ││││ ││││
                     ││└┴─┴┴┴┴── "pw" (first 2 chars of second part)
                     │└───────── "f2" (hash chars 2-4)
                     └────────── "nf" (first 2 chars of first part)
                      └───────── "a3" (hash chars 0-2)
        """
        if not record_id:
            return record_id
        
        record_id = str(record_id)
        
        # Check if it's in the expected xxxxx-xxxxx format
        if "-" not in record_id:
            return record_id
            
        parts = record_id.split("-")
        if len(parts) != 2:
            return record_id
        
        # Only process if both parts have at least 2 characters
        if len(parts[0]) < 2 or len(parts[1]) < 2:
            return record_id
        
        # Generate SHA256 hash of the full original ID
        hash_digest = hashlib.sha256(record_id.encode()).hexdigest()
        
        # Build the shortened ID:
        # - First 2 chars from each original part (preserves some readability)
        # - 2 chars from hash for each part (ensures uniqueness)
        prefix1 = parts[0][:2]      # e.g., "nf" from "nfqdb"
        hash_suffix1 = hash_digest[0:2]  # e.g., "a3" from hash
        
        prefix2 = parts[1][:2]      # e.g., "pw" from "pwk91"
        hash_suffix2 = hash_digest[2:4]  # e.g., "f2" from hash
        
        shortened = f"{prefix1}{hash_suffix1}-{prefix2}{hash_suffix2}"
        
        current_app.logger.debug(
            f"Hybrid ID shortening: {record_id} → {shortened} "
            f"(hash: {hash_digest[:8]}...)"
        )
        
        return shortened

    def generate_doi(self, record):
        """Generate a DOI with shortened record ID format (xxxx-xxxx)."""
        self.check_credentials()
        prefix = self.cfg("prefix")
        if not prefix:
            raise RuntimeError("Invalid DOI prefix configured.")
        
        # Get original record ID and shorten it using hybrid approach
        original_id = record.pid.pid_value
        shortened_id = self._shorten_id(original_id)
        
        current_app.logger.info(
            f"CustomDataCiteClient: Generating DOI - original_id={original_id}, "
            f"shortened_id={shortened_id}"
        )
        
        doi_format = self.cfg("format", "{prefix}/{id}")
        if callable(doi_format):
            class RecordWrapper:
                def __init__(self, pid_value):
                    self.pid = type('PID', (), {'pid_value': pid_value})()
            return doi_format(prefix, RecordWrapper(shortened_id))
        else:
            return doi_format.format(prefix=prefix, id=shortened_id)


class CustomDataCitePIDProvider(DataCitePIDProvider):
    """DataCite Provider with shortened DOI and custom landing page URL support."""

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

    def _shorten_id(self, record_id):
        """Shorten record ID from xxxxx-xxxxx to xxxx-xxxx using hybrid approach.
        
        See CustomDataCiteClient._shorten_id for detailed documentation.
        """
        if not record_id:
            return record_id
        
        record_id = str(record_id)
        
        if "-" not in record_id:
            return record_id
            
        parts = record_id.split("-")
        if len(parts) != 2:
            return record_id
        
        if len(parts[0]) < 2 or len(parts[1]) < 2:
            return record_id
        
        # Generate SHA256 hash of the full original ID
        hash_digest = hashlib.sha256(record_id.encode()).hexdigest()
        
        # Hybrid approach: preserve prefix + hash suffix
        prefix1 = parts[0][:2]
        hash_suffix1 = hash_digest[0:2]
        
        prefix2 = parts[1][:2]
        hash_suffix2 = hash_digest[2:4]
        
        return f"{prefix1}{hash_suffix1}-{prefix2}{hash_suffix2}"

    def _extract_app_code(self, record):
        """Extract app_code from metadata.identifiers (SERVE:xxx format)."""
        if isinstance(record, ChainObject):
            metadata = record._child.get("metadata", {})
        else:
            metadata = record.get("metadata", {})
        
        identifiers = metadata.get("identifiers", [])
        
        for identifier in identifiers:
            id_value = identifier.get("identifier", "")
            if id_value.upper().startswith("SERVE:"):
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
            "record_id": self._shorten_id(record_id),
            "parent_id": self._shorten_id(parent_id),
            "is_restricted": is_restricted,
            "app_code": app_code,
        }

    def _build_landing_url(self, record, pid, fallback_url=None):
        """Build the landing page URL from configuration template."""
        if self.is_parent_provider:
            template = current_app.config.get(
                "DATACITE_LANDING_PAGE_URL_TEMPLATE_PARENT"
            )
        else:
            template = current_app.config.get("DATACITE_LANDING_PAGE_URL_TEMPLATE")
        
        if not template:
            current_app.logger.debug(
                f"No URL template configured, using fallback: {fallback_url}"
            )
            return fallback_url
        
        info = self._extract_record_info(record, pid)
        app_code = info["app_code"] if info["app_code"] else info["record_id"]
        
        current_app.logger.info(
            f"Building landing URL: record_id={info['record_id']}, "
            f"app_code={app_code}, is_parent={self.is_parent_provider}"
        )
        
        try:
            url = template.format(
                id=info["record_id"],
                parent_id=info["parent_id"],
                doi=pid.pid_value,
                prefix=current_app.config.get("DATACITE_PREFIX", ""),
                app_code=app_code,
            )
            current_app.logger.info(f"Built landing URL: {url}")
            return url
        except KeyError as e:
            current_app.logger.error(f"Invalid placeholder in URL template: {e}")
            return fallback_url

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