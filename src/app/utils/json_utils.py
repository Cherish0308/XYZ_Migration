from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> str:
    
    return json.dumps(obj, default=str)


def loads(text: str) -> Any:
    
    return json.loads(text)
