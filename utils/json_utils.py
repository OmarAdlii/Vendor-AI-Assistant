from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from typing import Any


def make_serializable(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable Python objects into serializable types.

    - Decimal -> float
    - datetime/date -> ISO string
    - UUID -> str
    - bytes -> decode as utf-8 or repr
    - dict/list/tuple: recurse
    """
    # Primitive short-circuits
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return str(obj)

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except Exception:
            return repr(obj)

    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [make_serializable(v) for v in obj]

    # Fallback: try to cast to str
    try:
        return str(obj)
    except Exception:
        return None
