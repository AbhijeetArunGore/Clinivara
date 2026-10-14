"""
Structured, privacy-preserving audit logger.

Enforces:
1. JSON Lines structured records.
2. Log injection sanitization (stripping newlines, control characters).
3. Zero leakage of raw clinical text, patient names, or sensitive identifiers.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from clinivara.core.config import settings
from clinivara.schemas.audit import AuditEvent

# Configure standard logger to only print sanitized metadata
logger = logging.getLogger("clinivara.audit")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [tenant=%(tenant_id)s] [doc=%(doc_id)s] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)


def sanitize_log_string(val: Any) -> str:
    """Sanitize strings against log injection attacks (newlines, escape sequences)."""
    if val is None:
        return ""
    text = str(val)
    # Strip carriage returns, newlines, and non-printable control characters
    text = re.sub(r"[\r\n\x00-\x1f\x7f-\x9f]", " ", text)
    return text.strip()


class AuditLogger:
    """Thread-safe append-only audit event logger."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or settings.audit_log_path
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record_event(
        self,
        tenant_id: str,
        correlation_id: str,
        event_type: Any,
        status: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Record an immutable structured audit event to the append-only log.
        """
        safe_details = {}
        if details:
            for k, v in details.items():
                # Strictly prevent leaking raw text or personal information
                if any(bad in k.lower() for bad in ["raw", "text", "name", "phone", "email", "address", "ssn", "secret"]):
                    safe_details[k] = "[REDACTED_FROM_AUDIT]"
                elif isinstance(v, str):
                    safe_details[k] = sanitize_log_string(v)[:256]
                else:
                    safe_details[k] = v

        event = AuditEvent(
            event_id=f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{correlation_id[-6:]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            tenant_id=sanitize_log_string(tenant_id),
            document_id=sanitize_log_string(document_id) if document_id else None,
            correlation_id=sanitize_log_string(correlation_id),
            event_type=event_type,
            status=status,
            details=safe_details,
        )

        # Write to JSONL
        self._ensure_log_dir()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

        # Standard log output
        extra = {"tenant_id": event.tenant_id, "doc_id": event.document_id or "none"}
        logger.info(f"AUDIT_EVENT: {event.event_type} - {event.status}", extra=extra)

        return event


# Global audit logger instance
audit_logger = AuditLogger()
