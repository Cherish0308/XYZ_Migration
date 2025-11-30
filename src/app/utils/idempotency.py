from __future__ import annotations

import hashlib
from typing import Dict


def compute_idempotency_key(payload: Dict[str, str]) -> str:
    """
    Build a deterministic SHA-256 hash from a small dict.

    Used so that the same S3 event / job payload always produces
    the same idempotency key.
    """
    canonical = "|".join(f"{k}={payload[k]}" for k in sorted(payload.keys()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
