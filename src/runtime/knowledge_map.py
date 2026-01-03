from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def build_knowledge_map(meta_path: str) -> Dict[str, Any]:
    meta = _load_meta(Path(meta_path))
    files = meta.get("files", {})
    folders = defaultdict(int)
    recent: List[Dict[str, Any]] = []
    for path, info in files.items():
        folder = str(Path(path).parent)
        folders[folder] += 1
        recent.append({
            "path": path,
            "updated_at": info.get("updated_at"),
            "size": info.get("size"),
        })
    folder_list = [
        {"path": folder, "count": count}
        for folder, count in sorted(folders.items(), key=lambda item: item[1], reverse=True)
    ]
    recent.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return {
        "folders": folder_list[:30],
        "recent": recent[:40],
        "total_files": len(files),
        "aliases": meta.get("aliases", {}),
    }


def _load_meta(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"files": {}, "aliases": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {"files": {}, "aliases": {}}
    return {"files": {}, "aliases": {}}
