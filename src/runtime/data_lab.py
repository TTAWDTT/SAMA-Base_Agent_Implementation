from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional


def preview_csv(content: str, limit: int = 20) -> Dict[str, Any]:
    rows = _read_csv(content)
    header = rows[0] if rows else []
    body = rows[1:] if len(rows) > 1 else []
    return {
        "header": header,
        "rows": body[:limit],
        "total_rows": max(len(rows) - 1, 0),
    }


def transform_csv(content: str, operations: List[Dict[str, Any]], limit: int = 50) -> Dict[str, Any]:
    rows = _read_csv(content)
    if not rows:
        return {"error": "empty_csv"}
    header = rows[0]
    body = rows[1:]
    for op in operations:
        name = str(op.get("op") or "").lower()
        if name == "trim":
            body = [[cell.strip() for cell in row] for row in body]
        elif name == "drop_empty":
            body = [row for row in body if any(cell.strip() for cell in row)]
        elif name == "select":
            columns = op.get("columns") or []
            indices = _resolve_columns(header, columns)
            header = [header[i] for i in indices]
            body = [[row[i] if i < len(row) else "" for i in indices] for row in body]
        elif name == "dedup":
            seen = set()
            deduped = []
            for row in body:
                key = tuple(row)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(row)
            body = deduped
    return {
        "header": header,
        "rows": body[:limit],
        "total_rows": len(body),
    }


def _read_csv(content: str) -> List[List[str]]:
    if not content:
        return []
    reader = csv.reader(io.StringIO(content))
    return [list(row) for row in reader]


def _resolve_columns(header: List[str], columns: List[Any]) -> List[int]:
    indices: List[int] = []
    for col in columns:
        if isinstance(col, int):
            if 0 <= col < len(header):
                indices.append(col)
        else:
            name = str(col).strip()
            if name in header:
                indices.append(header.index(name))
    if not indices:
        return list(range(len(header)))
    return indices
