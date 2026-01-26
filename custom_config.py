# custom_config.py
# -*- coding: utf-8 -*-
"""Custom configuration for shortened DOI format and landing page URLs.

DOI Format: xxxxx-xxxxx (InvenioRDM) -> xxxx-xxxx (DataCite)
Example: 10.83812/SCILIFELAB.nfqdb-pwk91 -> 10.83812/SCILIFELAB.nfqd-pwk9

Landing Page URLs:
- Parent DOI: https://serve.scilifelab.se/records/{app_code}
- Version DOI: https://serve.scilifelab.se/records/{app_code}/{id}
"""

import os
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.pids import providers
from invenio_rdm_records.resources.serializers.datacite import DataCite43JSONSerializer
from invenio_rdm_records import config as rdm_config

# Import custom modules
import sys
sys.path.insert(0, '/opt/invenio/var/instance/custom_modules')
from custom_datacite_provider import CustomDataCitePIDProvider, CustomDataCiteClient

# ==============================================================================
# DATACITE LANDING PAGE URL CONFIGURATION
# ==============================================================================
# Available placeholders: {id}, {parent_id}, {doi}, {prefix}, {app_code}
#
# {id} - Record ID shortened to xxxx-xxxx format
# {app_code} - Extracted from metadata.identifiers (SERVE:xxx)
# {parent_id} - Parent record ID (for versioning)
# {doi} - Full DOI value
# {prefix} - DataCite prefix

DATACITE_LANDING_PAGE_URL_TEMPLATE = os.environ.get(
    "DATACITE_LANDING_PAGE_URL_TEMPLATE",
    "https://serve.scilifelab.se/records/{app_code}/{id}"
)

DATACITE_LANDING_PAGE_URL_TEMPLATE_PARENT = os.environ.get(
    "DATACITE_LANDING_PAGE_URL_TEMPLATE_PARENT",
    "https://serve.scilifelab.se/records/{app_code}"
)

# ==============================================================================
# DATACITE PROVIDER REPLACEMENT
# ==============================================================================
# Uses CustomDataCiteClient for shortened DOI generation (xxxx-xxxx)
# Uses CustomDataCitePIDProvider for custom landing page URLs

def _create_custom_provider(serializer=None, label=None, is_parent=False):
    """Factory function to create custom DataCite provider with custom client."""
    return CustomDataCitePIDProvider(
        "datacite",
        client=CustomDataCiteClient("datacite", config_prefix="DATACITE"),
        serializer=serializer,
        label=label or _("DOI"),
        is_parent_provider=is_parent,
    )

# Replace record DOI providers
RDM_PERSISTENT_IDENTIFIER_PROVIDERS = []
for provider in rdm_config.RDM_PERSISTENT_IDENTIFIER_PROVIDERS:
    if isinstance(provider, providers.DataCitePIDProvider):
        RDM_PERSISTENT_IDENTIFIER_PROVIDERS.append(
            _create_custom_provider(label=_("DOI"), is_parent=False)
        )
    else:
        RDM_PERSISTENT_IDENTIFIER_PROVIDERS.append(provider)

# Replace parent DOI providers (concept DOIs)
RDM_PARENT_PERSISTENT_IDENTIFIER_PROVIDERS = []
for provider in rdm_config.RDM_PARENT_PERSISTENT_IDENTIFIER_PROVIDERS:
    if isinstance(provider, providers.DataCitePIDProvider):
        RDM_PARENT_PERSISTENT_IDENTIFIER_PROVIDERS.append(
            _create_custom_provider(
                serializer=DataCite43JSONSerializer(
                    schema_context={"is_parent": True}
                ),
                label=_("Concept DOI"),
                is_parent=True,
            )
        )
    else:
        RDM_PARENT_PERSISTENT_IDENTIFIER_PROVIDERS.append(provider)

del _create_custom_provider
