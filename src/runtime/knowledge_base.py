# ==============================================================================
# 本地知识库
# ==============================================================================

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.core.config import KnowledgeBaseConfig, get_config
from src.utils.helpers import estimate_tokens, truncate_text


@dataclass
class KnowledgeEntry:
    entry_id: str
    path: str
    chunk_id: int
    content: str
    tokens: int
    updated_at: str
    file_mtime: float
    file_size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.entry_id,
            "path": self.path,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "tokens": self.tokens,
            "updated_at": self.updated_at,
            "file_mtime": self.file_mtime,
            "file_size": self.file_size,
        }


def index_paths(
    paths: Iterable[str],
    config: Optional[KnowledgeBaseConfig] = None,
    full_rebuild: bool = False
) -> Dict[str, Any]:
    """
    索引知识库
    """
    kb_config = config or get_config().knowledge_base
    index_path = Path(kb_config.index_file)
    meta_path = Path(kb_config.meta_file)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    meta = _load_meta(meta_path)
    if full_rebuild:
        meta = {"files": {}, "aliases": meta.get("aliases", {})}

    aliases = meta.get("aliases", {})
    resolved_paths = _resolve_alias_paths(paths, aliases)
    meta["aliases"] = aliases

    files = _collect_files(resolved_paths, kb_config)
    entries: List[KnowledgeEntry] = []
    removed = []
    updated = 0
    skipped = 0

    current_paths = {str(Path(path).resolve()) for path in files}
    for known_path in list(meta.get("files", {}).keys()):
        if known_path not in current_paths:
            removed.append(known_path)
            meta["files"].pop(known_path, None)

    for file_path in files:
        resolved = str(Path(file_path).resolve())
        stat = os.stat(file_path)
        mtime = stat.st_mtime
        size = stat.st_size
        signature = f"{mtime}:{size}"

        record = meta.get("files", {}).get(resolved)
        if record and record.get("signature") == signature:
            skipped += 1
            continue

        content = _read_text(file_path)
        chunks = _chunk_text(content, kb_config.chunk_size)
        for idx, chunk in enumerate(chunks[: kb_config.max_chunks_per_file]):
            entry_id = _build_entry_id(resolved, idx, signature)
            entries.append(
                KnowledgeEntry(
                    entry_id=entry_id,
                    path=resolved,
                    chunk_id=idx,
                    content=chunk,
                    tokens=estimate_tokens(chunk),
                    updated_at=datetime.now().isoformat(),
                    file_mtime=mtime,
                    file_size=size,
                )
            )

        meta.setdefault("files", {})[resolved] = {
            "signature": signature,
            "mtime": mtime,
            "size": size,
            "updated_at": datetime.now().isoformat(),
        }
        updated += 1

    if not entries and not removed and not full_rebuild:
        return {"updated": updated, "skipped": skipped, "removed": 0, "total": _count_index(index_path)}

    if full_rebuild:
        _write_index(index_path, entries)
    else:
        existing = _load_index(index_path)
        existing = [entry for entry in existing if entry.path not in removed]
        existing.extend(entries)
        _write_index(index_path, existing)

    _write_meta(meta_path, meta)
    return {"updated": updated, "skipped": skipped, "removed": len(removed), "total": _count_index(index_path)}


def search(
    query: str,
    config: Optional[KnowledgeBaseConfig] = None,
    top_k: Optional[int] = None
) -> Dict[str, Any]:
    """
    检索知识库
    """
    kb_config = config or get_config().knowledge_base
    index_path = Path(kb_config.index_file)
    if not index_path.exists():
        return {"results": [], "query": query}

    entries = _load_index(index_path)
    if not entries:
        return {"results": [], "query": query}

    terms = _extract_terms(query)
    if not terms:
        return {"results": [], "query": query}

    ranked: List[Tuple[int, KnowledgeEntry]] = []
    for entry in entries:
        score = _score_chunk(entry.content, terms)
        if score < kb_config.min_score:
            continue
        ranked.append((score, entry))

    ranked.sort(key=lambda item: (-item[0], item[1].path))
    limit = top_k or kb_config.max_results
    results = []
    for score, entry in ranked[:limit]:
        results.append({
            "path": entry.path,
            "chunk_id": entry.chunk_id,
            "score": score,
            "snippet": truncate_text(entry.content, kb_config.snippet_length),
        })

    return {"results": results, "query": query}


def load_entry(
    path: str,
    chunk_id: int,
    config: Optional[KnowledgeBaseConfig] = None
) -> Optional[str]:
    kb_config = config or get_config().knowledge_base
    index_path = Path(kb_config.index_file)
    entries = _load_index(index_path)
    for entry in entries:
        if entry.path == path and entry.chunk_id == chunk_id:
            return entry.content
    return None


def clear_index(config: Optional[KnowledgeBaseConfig] = None) -> None:
    kb_config = config or get_config().knowledge_base
    index_path = Path(kb_config.index_file)
    meta_path = Path(kb_config.meta_file)
    if index_path.exists():
        index_path.unlink()
    if meta_path.exists():
        meta_path.unlink()


def _collect_files(paths: Iterable[str], config: KnowledgeBaseConfig) -> List[str]:
    files: List[str] = []
    include_ext = {ext.lower() for ext in config.include_extensions}
    exclude_dirs = {str(Path(p).resolve()) for p in config.exclude_dirs}
    max_size = getattr(config, "max_file_size", None)
    skip_binary = getattr(config, "skip_binary", True)
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            if _is_supported(path, include_ext) and _is_valid_file(path, max_size, skip_binary):
                files.append(str(path))
            continue
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if _is_excluded(file_path, exclude_dirs):
                continue
            if _is_supported(file_path, include_ext) and _is_valid_file(file_path, max_size, skip_binary):
                files.append(str(file_path))
    return files


def _resolve_alias_paths(paths: Iterable[str], aliases: Dict[str, str]) -> List[str]:
    resolved: List[str] = []
    for raw in paths:
        if not raw:
            continue
        item = str(raw).strip()
        if not item:
            continue
        if "=" in item:
            alias, path = [part.strip() for part in item.split("=", 1)]
            if alias and path:
                aliases[alias] = str(Path(path).resolve())
                resolved.append(path)
            continue
        if item.startswith("@"):
            alias = item[1:].strip()
            target = aliases.get(alias)
            if target:
                resolved.append(target)
            continue
        resolved.append(item)
    return resolved


def _is_valid_file(path: Path, max_size: Optional[int], skip_binary: bool) -> bool:
    try:
        if max_size and path.stat().st_size > max_size:
            return False
    except OSError:
        return False
    if skip_binary and _is_binary_file(path):
        return False
    return True


def _is_binary_file(path: Path, sample_size: int = 4096) -> bool:
    try:
        data = path.read_bytes()[:sample_size]
    except Exception:
        return False
    if not data:
        return False
    if b"\x00" in data:
        return True
    text = data.decode("utf-8", errors="replace")
    if not text:
        return False
    replacement_ratio = text.count("\ufffd") / max(len(text), 1)
    return replacement_ratio > 0.2


def _is_supported(path: Path, include_ext: set) -> bool:
    if not include_ext:
        return True
    return path.suffix.lower() in include_ext


def _is_excluded(path: Path, exclude_dirs: set) -> bool:
    parent = str(path.parent.resolve())
    for excluded in exclude_dirs:
        if parent.startswith(excluded):
            return True
    return False


def _chunk_text(text: str, max_chars: int) -> List[str]:
    if not text:
        return []
    if max_chars <= 0:
        return [text]
    paragraphs = text.split("\n\n")
    chunks = []
    current = []
    length = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para)
        if para_len > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                length = 0
            for idx in range(0, para_len, max_chars):
                slice_text = para[idx:idx + max_chars].strip()
                if slice_text:
                    chunks.append(slice_text)
            continue
        if length + para_len + (2 if current else 0) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            length = para_len
        else:
            if current:
                length += 2 + para_len
            else:
                length = para_len
            current.append(para)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _extract_terms(text: str) -> List[str]:
    if not text:
        return []
    tokens = []
    buff = []
    for ch in text.lower():
        if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff"):
            buff.append(ch)
        else:
            if buff:
                tokens.append("".join(buff))
                buff = []
    if buff:
        tokens.append("".join(buff))
    seen = set()
    result = []
    for token in tokens:
        if token in seen:
            continue
        if token.isascii() and len(token) < 2:
            continue
        seen.add(token)
        result.append(token)
    return result[:64]


def _score_chunk(chunk: str, terms: List[str]) -> int:
    if not chunk or not terms:
        return 0
    chunk_lower = chunk.lower()
    score = 0
    for term in terms:
        if term and term in chunk_lower:
            score += 1
    return score


def _build_entry_id(path: str, chunk_id: int, signature: str) -> str:
    raw = f"{path}:{chunk_id}:{signature}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _write_index(path: Path, entries: List[KnowledgeEntry]) -> None:
    path.write_text(
        "\n".join(json.dumps(entry.to_dict(), ensure_ascii=False) for entry in entries),
        encoding="utf-8"
    )


def _load_index(path: Path) -> List[KnowledgeEntry]:
    if not path.exists():
        return []
    entries: List[KnowledgeEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(
            KnowledgeEntry(
                entry_id=str(data.get("id")),
                path=str(data.get("path")),
                chunk_id=int(data.get("chunk_id", 0)),
                content=str(data.get("content", "")),
                tokens=int(data.get("tokens", 0)),
                updated_at=str(data.get("updated_at", "")),
                file_mtime=float(data.get("file_mtime", 0)),
                file_size=int(data.get("file_size", 0)),
            )
        )
    return entries


def _count_index(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def _load_meta(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"files": {}, "aliases": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("files", {})
            data.setdefault("aliases", {})
            return data
    except Exception:
        return {"files": {}, "aliases": {}}
    return {"files": {}, "aliases": {}}


def _write_meta(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
