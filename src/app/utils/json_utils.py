from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> str:
    """
    JSON dumps helper with datetime support.
    """
    return json.dumps(obj, default=str)


def loads(text: str) -> Any:
    """
    Thin wrapper around json.loads for symmetry.
    """
    return json.loads(text)
