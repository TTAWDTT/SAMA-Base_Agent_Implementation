from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.core.logger import get_logger
from src.runtime.rss_feed import fetch_feed_items

logger = get_logger("media_hub")

DATE_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "into", "about", "your",
    "you", "are", "was", "were", "will", "have", "has", "had", "not", "but",
    "new", "how", "what", "why", "when", "where", "who", "its", "they", "their",
    "our", "out", "all", "can", "use", "using", "more", "less", "than", "after",
    "over", "under", "just", "now", "today", "yesterday", "latest", "update",
}


def run_media_hub(config) -> Dict[str, Any]:
    if not config or not getattr(config, "enabled", False):
        return {"success": False, "error": "media_hub_disabled"}

    output_dir = Path(getattr(config, "output_dir", "outputs/media"))
    output_dir.mkdir(parents=True, exist_ok=True)

    sources_file = Path(getattr(config, "sources_file", output_dir / "sources.json"))
    items_file = Path(getattr(config, "items_file", output_dir / "items.json"))
    alerts_file = Path(getattr(config, "alerts_file", output_dir / "alerts.json"))
    brief_dir = Path(getattr(config, "brief_dir", output_dir / "briefs"))
    brief_dir.mkdir(parents=True, exist_ok=True)

    sources = _load_sources(sources_file, getattr(config, "sources", []) or [])
    alerts = _load_alerts(alerts_file, getattr(config, "alerts", []) or [])

    items_payload = _load_items(items_file)
    existing_items = items_payload.get("items", []) if isinstance(items_payload, dict) else []
    existing_map = {item.get("id"): item for item in existing_items if item.get("id")}

    max_items = int(getattr(config, "max_items", 2000) or 2000)
    per_source_limit = int(getattr(config, "per_source_limit", 80) or 80)

    now = datetime.now()
    fetched_at = now.isoformat(timespec="seconds")
    date_key = now.strftime("%Y-%m-%d")

    new_items: List[Dict[str, Any]] = []
    errors: List[str] = []
    skipped: List[Dict[str, Any]] = []

    for source in sources:
        if not source.get("enabled", False):
            continue
        if source.get("requires_config") or not source.get("url"):
            skipped.append({"id": source.get("id"), "reason": "requires_config"})
            source["last_status"] = "skipped"
            continue
        source_type = str(source.get("type") or "rss").lower()
        if source_type != "rss":
            skipped.append({"id": source.get("id"), "reason": "unsupported_type"})
            source["last_status"] = "skipped"
            continue
        try:
            feed_title, feed_items = fetch_feed_items(source["url"])
        except Exception as exc:
            msg = f"{source.get('name') or source.get('url')}: {exc}"
            errors.append(msg)
            source["last_status"] = "error"
            source["last_error"] = str(exc)
            continue

        source_name = source.get("name") or feed_title
        source_platform = source.get("platform") or source.get("type") or "RSS"
        items_added = 0
        for entry in feed_items:
            if per_source_limit and items_added >= per_source_limit:
                break
            item = _build_item(entry, source, source_name, source_platform, fetched_at)
            new_items.append(item)
            items_added += 1
        source["last_fetch"] = fetched_at
        source["last_status"] = "success"
        source["last_error"] = ""
        source["fetched_count"] = items_added

    merged_items = _merge_items(existing_map, new_items)
    _apply_alerts(merged_items, alerts)

    merged_items.sort(key=_item_sort_key, reverse=True)
    if max_items and len(merged_items) > max_items:
        merged_items = merged_items[:max_items]

    items_payload = {
        "updated_at": fetched_at,
        "total_items": len(merged_items),
        "items": merged_items,
    }
    items_file.write_text(json.dumps(items_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _save_sources(sources_file, sources)
    _save_alerts(alerts_file, alerts)

    brief_payload = _build_brief_payload(date_key, fetched_at, merged_items, sources, alerts, new_items)
    brief_text = _render_brief_markdown(brief_payload)
    brief_json_path = brief_dir / f"brief_{date_key}.json"
    brief_md_path = brief_dir / f"brief_{date_key}.md"
    brief_json_path.write_text(json.dumps(brief_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    brief_md_path.write_text(brief_text, encoding="utf-8")
    _update_brief_index(brief_dir, brief_payload)

    obsidian_path = None
    if getattr(config, "obsidian_enabled", False):
        obsidian_dir = str(getattr(config, "obsidian_dir", "") or "").strip()
        if obsidian_dir:
            filename_template = str(getattr(config, "obsidian_filename", "media_{date}.md") or "media_{date}.md")
            try:
                obsidian_path = _write_obsidian_copy(obsidian_dir, filename_template, date_key, brief_text)
            except Exception as exc:
                logger.warning(f"Obsidian write failed: {exc}")
                errors.append(f"obsidian_write_failed: {exc}")
        else:
            errors.append("obsidian_dir_missing")

    return {
        "success": True,
        "date": date_key,
        "output_dir": str(output_dir),
        "items_file": str(items_file),
        "brief": str(brief_md_path),
        "obsidian_path": obsidian_path,
        "total_items": len(merged_items),
        "new_items": len(new_items),
        "errors": errors,
        "skipped": skipped,
    }


def list_media_items(
    output_dir: str,
    limit: int = 200,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    items_file = Path(output_dir) / "items.json"
    items_payload = _load_items(items_file)
    items = items_payload.get("items", []) if isinstance(items_payload, dict) else []
    filters = filters or {}

    query = str(filters.get("q") or "").strip().lower()
    source_filter = str(filters.get("source") or "").strip().lower()
    platform_filter = str(filters.get("platform") or "").strip().lower()
    tag_filter = str(filters.get("tag") or "").strip().lower()
    saved_only = _parse_bool(filters.get("saved"))
    read_only = _parse_bool(filters.get("read"))
    alerted_only = _parse_bool(filters.get("alerted"))

    results: List[Dict[str, Any]] = []
    for item in items:
        if query:
            text = f"{item.get('title','')} {item.get('summary','')}".lower()
            if query not in text:
                continue
        if source_filter and source_filter not in str(item.get("source") or "").lower():
            continue
        if platform_filter and platform_filter not in str(item.get("platform") or "").lower():
            continue
        if tag_filter:
            tags = [str(tag).lower() for tag in item.get("tags", []) or []]
            if tag_filter not in tags:
                continue
        if saved_only is not None and bool(item.get("saved", False)) != saved_only:
            continue
        if read_only is not None and bool(item.get("read", False)) != read_only:
            continue
        if alerted_only is not None and not item.get("alert_hits"):
            continue
        results.append(item)

    results.sort(key=_item_sort_key, reverse=True)
    if limit and len(results) > limit:
        results = results[:limit]

    return {
        "items": results,
        "total": len(results),
        "updated_at": items_payload.get("updated_at"),
    }


def update_media_item(output_dir: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    items_file = Path(output_dir) / "items.json"
    items_payload = _load_items(items_file)
    items = items_payload.get("items", []) if isinstance(items_payload, dict) else []
    updated = None
    for item in items:
        if item.get("id") == item_id:
            for key in ["saved", "read", "notes", "tags"]:
                if key in updates:
                    item[key] = updates[key]
            updated = item
            break
    if updated is None:
        return {"error": "item_not_found"}
    items_payload["items"] = items
    items_payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    items_payload["total_items"] = len(items)
    items_file.write_text(json.dumps(items_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"item": updated}


def add_manual_item(output_dir: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    link = str(payload.get("link") or "").strip()
    if not title:
        return {"error": "title_required"}

    source_name = str(payload.get("source") or "Manual").strip() or "Manual"
    platform = str(payload.get("platform") or "Manual").strip() or "Manual"
    summary = str(payload.get("summary") or "").strip()
    now = datetime.now().isoformat(timespec="seconds")
    source_id = _slugify(source_name) or "manual"

    item = {
        "id": _build_item_id(source_id, link, title),
        "title": title,
        "link": link,
        "summary": summary,
        "source": source_name,
        "source_id": source_id,
        "platform": platform,
        "published": now,
        "fetched_at": now,
        "tags": payload.get("tags") or [],
        "saved": True,
        "read": False,
        "notes": "",
        "alert_hits": [],
    }

    items_file = Path(output_dir) / "items.json"
    items_payload = _load_items(items_file)
    items = items_payload.get("items", []) if isinstance(items_payload, dict) else []
    items.append(item)
    items_payload["items"] = items
    items_payload["updated_at"] = now
    items_payload["total_items"] = len(items)
    items_file.write_text(json.dumps(items_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"item": item}


def list_media_briefs(brief_dir: str, limit: int = 30) -> Dict[str, Any]:
    path = Path(brief_dir)
    if not path.exists():
        return {"items": []}
    index_path = path / "brief_index.json"
    items: List[Dict[str, Any]] = []
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception:
            items = []
    if not items:
        items = _scan_brief_files(path)
    items = sorted(items, key=lambda item: item.get("date") or "", reverse=True)
    return {"items": items[:limit]}


def load_media_brief(brief_dir: str, date_key: str) -> Dict[str, Any]:
    if not DATE_KEY_PATTERN.match(date_key or ""):
        return {"error": "invalid_date"}
    path = Path(brief_dir) / f"brief_{date_key}.json"
    if not path.exists():
        return {"error": "brief_not_found"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "brief_load_failed"}


def list_media_sources(sources_file: str) -> List[Dict[str, Any]]:
    return _load_sources(Path(sources_file), [])


def update_media_sources(sources_file: str, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = _normalize_sources(sources)
    _save_sources(Path(sources_file), normalized)
    return normalized


def list_media_alerts(alerts_file: str) -> List[str]:
    return _load_alerts(Path(alerts_file), [])


def update_media_alerts(alerts_file: str, alerts: List[str]) -> List[str]:
    cleaned = _normalize_alerts(alerts)
    _save_alerts(Path(alerts_file), cleaned)
    return cleaned


def build_media_stats(output_dir: str, alerts: Optional[List[str]] = None, top_limit: int = 12) -> Dict[str, Any]:
    items_file = Path(output_dir) / "items.json"
    items_payload = _load_items(items_file)
    items = items_payload.get("items", []) if isinstance(items_payload, dict) else []
    alerts = alerts or []
    trends = _build_trends(items, limit=top_limit)
    sources = _count_by(items, "source")
    platforms = _count_by(items, "platform")
    alert_hits = sum(1 for item in items if item.get("alert_hits"))
    saved = sum(1 for item in items if item.get("saved"))
    unread = sum(1 for item in items if not item.get("read"))
    return {
        "total": len(items),
        "saved": saved,
        "unread": unread,
        "alerted": alert_hits,
        "trends": trends,
        "sources": sources,
        "platforms": platforms,
        "alerts": alerts,
    }


def _load_items(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {"items": []}
    return {"items": []}


def _load_sources(path: Path, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_sources = data.get("sources", [])
            else:
                raw_sources = data
            if isinstance(raw_sources, list):
                return _normalize_sources(raw_sources)
        except Exception:
            pass
    normalized = _normalize_sources(fallback)
    _save_sources(path, normalized)
    return normalized


def _save_sources(path: Path, sources: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sources": sources, "updated_at": datetime.now().isoformat(timespec="seconds")}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_alerts(path: Path, fallback: List[str]) -> List[str]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_alerts = data.get("alerts", [])
            else:
                raw_alerts = data
            if isinstance(raw_alerts, list):
                return _normalize_alerts(raw_alerts)
        except Exception:
            pass
    normalized = _normalize_alerts(fallback)
    _save_alerts(path, normalized)
    return normalized


def _save_alerts(path: Path, alerts: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"alerts": alerts, "updated_at": datetime.now().isoformat(timespec="seconds")}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_alerts(alerts: Iterable[Any]) -> List[str]:
    cleaned = []
    seen = set()
    for entry in alerts:
        text = str(entry).strip()
        if not text:
            continue
        lower = text.lower()
        if lower in seen:
            continue
        seen.add(lower)
        cleaned.append(text)
    return cleaned


def _normalize_sources(sources: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for raw in sources:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("title") or "Untitled").strip()
        url = str(raw.get("url") or "").strip()
        source_id = str(raw.get("id") or _slugify(name) or _hash_text(url or name))
        platform = str(raw.get("platform") or raw.get("type") or "RSS").strip()
        source_type = str(raw.get("type") or "rss").lower().strip() or "rss"
        enabled = bool(raw.get("enabled", False))
        requires_config = bool(raw.get("requires_config", False))
        note = str(raw.get("note") or raw.get("hint") or "").strip()
        normalized.append({
            "id": source_id,
            "name": name,
            "platform": platform,
            "type": source_type,
            "url": url,
            "enabled": enabled,
            "requires_config": requires_config,
            "note": note,
            "tags": raw.get("tags") or [],
            "last_fetch": raw.get("last_fetch"),
            "last_status": raw.get("last_status"),
            "last_error": raw.get("last_error", ""),
            "fetched_count": raw.get("fetched_count", 0),
        })
    return normalized


def _build_item(entry, source: Dict[str, Any], source_name: str, platform: str, fetched_at: str) -> Dict[str, Any]:
    title = entry.title.strip() if entry.title else ""
    link = entry.link.strip() if entry.link else ""
    summary = entry.summary.strip() if entry.summary else ""
    return {
        "id": _build_item_id(source.get("id", ""), link, title),
        "title": title,
        "link": link,
        "summary": summary,
        "source": source_name,
        "source_id": source.get("id"),
        "platform": platform,
        "published": entry.published,
        "fetched_at": fetched_at,
        "tags": [],
        "saved": False,
        "read": False,
        "notes": "",
        "alert_hits": [],
    }


def _build_item_id(source_id: str, link: str, title: str) -> str:
    seed = f"{source_id}|{link or title}".encode("utf-8")
    return hashlib.sha1(seed).hexdigest()[:16]


def _merge_items(existing_map: Dict[str, Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = dict(existing_map)
    for item in incoming:
        item_id = item.get("id")
        if not item_id:
            continue
        if item_id in merged:
            current = merged[item_id]
            user_fields = {
                "saved": current.get("saved", False),
                "read": current.get("read", False),
                "notes": current.get("notes", ""),
                "tags": current.get("tags", []),
            }
            current.update(item)
            current.update(user_fields)
        else:
            merged[item_id] = item
    return list(merged.values())


def _apply_alerts(items: List[Dict[str, Any]], alerts: List[str]) -> None:
    if not alerts:
        for item in items:
            item["alert_hits"] = []
        return
    lowered = [(alert, alert.lower()) for alert in alerts]
    for item in items:
        text = f"{item.get('title','')} {item.get('summary','')}".lower()
        hits = [original for original, lower in lowered if lower in text]
        item["alert_hits"] = hits


def _item_sort_key(item: Dict[str, Any]) -> str:
    return item.get("published") or item.get("fetched_at") or ""


def _build_brief_payload(
    date_key: str,
    generated_at: str,
    items: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
    alerts: List[str],
    new_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    alert_hits = [item for item in items if item.get("alert_hits")]
    return {
        "date": date_key,
        "generated_at": generated_at,
        "total_items": len(items),
        "new_items": len(new_items),
        "alerts": alerts,
        "alert_hits": alert_hits[:40],
        "sources": sources,
        "items": items[:80],
    }


def _render_brief_markdown(payload: Dict[str, Any]) -> str:
    date_key = payload.get("date", "")
    lines = [
        f"# Media Brief ({date_key})",
        "",
        f"Generated: {payload.get('generated_at', '')}",
        f"Total items: {payload.get('total_items', 0)}",
        f"New items: {payload.get('new_items', 0)}",
        "",
    ]

    alert_hits = payload.get("alert_hits") or []
    if alert_hits:
        lines.append("## Alerts")
        for item in alert_hits:
            title = item.get("title") or "Untitled"
            link = item.get("link") or ""
            source = item.get("source") or ""
            lines.append(f"- [{title}]({link})")
            if source:
                lines.append(f"  - {source}")
        lines.append("")

    sources = payload.get("sources") or []
    if sources:
        lines.append("## Sources")
        for source in sources:
            status = source.get("last_status") or "idle"
            label = source.get("name") or source.get("id") or "source"
            note = source.get("note") or ""
            suffix = f" ({note})" if note else ""
            lines.append(f"- {label}: {status}{suffix}")
        lines.append("")

    items = payload.get("items") or []
    if not items:
        lines.append("No items available.")
        return "\n".join(lines)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        key = item.get("platform") or item.get("source") or "Other"
        grouped.setdefault(key, []).append(item)

    for group, group_items in grouped.items():
        lines.append(f"## {group}")
        for item in group_items:
            title = item.get("title") or "Untitled"
            link = item.get("link") or ""
            source = item.get("source") or ""
            published = item.get("published") or ""
            lines.append(f"- [{title}]({link})")
            meta = " | ".join([value for value in [source, published] if value])
            if meta:
                lines.append(f"  - {meta}")
        lines.append("")

    return "\n".join(lines)


def _update_brief_index(brief_dir: Path, payload: Dict[str, Any]) -> None:
    index_path = brief_dir / "brief_index.json"
    items = []
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception:
            items = []
    items = [item for item in items if item.get("date") != payload.get("date")]
    items.append({
        "date": payload.get("date"),
        "generated_at": payload.get("generated_at"),
        "total_items": payload.get("total_items"),
        "new_items": payload.get("new_items"),
    })
    items = sorted(items, key=lambda item: item.get("date") or "", reverse=True)
    index_path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def _scan_brief_files(path: Path) -> List[Dict[str, Any]]:
    items = []
    for entry in path.glob("brief_*.json"):
        name = entry.stem.replace("brief_", "")
        if not DATE_KEY_PATTERN.match(name):
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except Exception:
            continue
        items.append({
            "date": data.get("date", name),
            "generated_at": data.get("generated_at"),
            "total_items": data.get("total_items", len(data.get("items") or [])),
            "new_items": data.get("new_items", 0),
        })
    return items


def _write_obsidian_copy(
    obsidian_dir: str,
    filename_template: str,
    date_key: str,
    markdown_text: str
) -> str:
    target_dir = Path(obsidian_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = _format_filename(filename_template, date_key)
    target_path = target_dir / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown_text, encoding="utf-8")
    return str(target_path)


def _format_filename(template: str, date_key: str) -> str:
    try:
        return template.format_map({"date": date_key})
    except Exception:
        return f"media_{date_key}.md"


def _build_trends(items: List[Dict[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for item in items:
        text = f"{item.get('title','')} {item.get('summary','')}".lower()
        tokens = re.findall(r"[a-z0-9]{3,}", text)
        for token in tokens:
            if token in STOP_WORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    return [{"keyword": word, "count": count} for word, count in ranked[:limit]]


def _count_by(items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for item in items:
        label = str(item.get(key) or "").strip()
        if not label:
            continue
        counts[label] = counts.get(label, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    return [{"label": label, "count": count} for label, count in ranked]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned


def _hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _parse_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None
