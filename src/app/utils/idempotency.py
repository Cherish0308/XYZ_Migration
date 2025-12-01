from __future__ import annotations

import hashlib
from typing import Dict


def compute_idempotency_key(payload: Dict[str, str]) -> str:
    
    canonical = "|".join(f"{k}={payload[k]}" for k in sorted(payload.keys()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
