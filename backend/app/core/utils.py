from __future__ import annotations

import re
from uuid import uuid4


def normalize_slug(value: str) -> str:
    prepared = re.sub(r"[^\w\s-]", "", value.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", prepared)
    return slug or f"product-{uuid4().hex[:8]}"

