"""Commerce service.

This file is restored from main. Order lookup is attached in storefront routes via
`CommerceService.lookup_public_order = ...` using `order_lookup.lookup_order_by_phone`.

If this module is incomplete, run:
  git checkout origin/main -- backend/app/modules/commerce/service.py
"""
from __future__ import annotations

# Prefer full implementation from the package body if chunks are present (legacy), else import
# requires the full main implementation to be checked out.
from pathlib import Path

_chunks = Path(__file__).with_name("_service_chunks")
if _chunks.is_dir() and all((_chunks / f"part{i}.txt").exists() for i in range(4)):
    _parts = [(_chunks / f"part{i}.txt").read_text() for i in range(4)]
    exec(compile("".join(_parts), str(Path(__file__).resolve()), "exec"), globals())
else:
    raise ImportError(
        "backend/app/modules/commerce/service.py is incomplete on this branch. "
        "Restore with: git checkout origin/main -- backend/app/modules/commerce/service.py"
    )
