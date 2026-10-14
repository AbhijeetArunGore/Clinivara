"""
Isolated Token Vault for pseudonymization and longitudinal linkage.

Enforces:
1. Cryptographically salted HMAC tokens.
2. Mapping stored strictly inside isolated vault.
3. Zero exposure to downstream API contracts or public logs.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from clinivara.core.config import settings
from clinivara.core.security import generate_pseudonym_token
from clinivara.storage.storage_manager import storage_manager


class TokenVault:
    """Manages isolated pseudonymization token mappings when longitudinal linkage is requested."""

    def __init__(self):
        self.vault_dir = settings.token_vault_dir

    def resolve_token(
        self,
        tenant_id: str,
        document_id: str,
        entity_type: str,
        raw_value: str,
        store_mapping: bool = True,
    ) -> str:
        """
        Generate a pseudonym token and optionally store mapping in isolated vault.
        """
        token = generate_pseudonym_token(entity_type, raw_value)

        if store_mapping and settings.enable_longitudinal_tokens:
            tenant_vault = self.vault_dir / tenant_id
            tenant_vault.mkdir(parents=True, exist_ok=True)
            mapping_file = tenant_vault / f"{document_id}.json"

            mapping = {}
            if mapping_file.exists():
                try:
                    with open(mapping_file, "r", encoding="utf-8") as f:
                        mapping = json.load(f)
                except Exception:
                    mapping = {}

            # Map token -> entity metadata (stored exclusively inside isolated vault)
            mapping[token] = {
                "entity_type": entity_type,
                "raw_identifier": raw_value,
            }

            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2)

        return token


token_vault = TokenVault()
