from __future__ import annotations

from pathlib import Path

_parts = []
_base = Path(__file__).with_name("_service_chunks")
for _i in range(4):
    _parts.append((_base / f"part{_i}.txt").read_text())
exec(compile("".join(_parts), str(Path(__file__).resolve()), "exec"), globals())
