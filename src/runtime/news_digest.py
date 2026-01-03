from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.core.logger import get_logger
from src.runtime.rss_feed import fetch_feed_items

logger = get_logger("news_digest")
DATE_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: Optional[str]
    topic: Optional[str]


def run_news_digest(config) -> Dict[str, Any]:
    if not config or not getattr(config, "enabled", False):
        return {"success": False, "error": "news_digest_disabled"}

    output_dir = Path(getattr(config, "output_dir", "outputs/news"))
    output_dir.mkdir(parents=True, exist_ok=True)

    topics = list(getattr(config, "topics", []) or [])
    sources = list(getattr(config, "sources", []) or [])
    max_items = int(getattr(config, "max_items", 40) or 40)
    per_topic_limit = int(getattr(config, "per_topic_limit", 6) or 6)

    now = datetime.now()
    date_key = now.strftime("%Y-%m-%d")
    generated_at = now.isoformat(timespec="seconds")

    items, errors = _collect_items(topics, sources, per_topic_limit)
    items = items[:max_items] if max_items else items

    payload = {
        "date": date_key,
        "generated_at": generated_at,
        "topics": topics,
        "total_items": len(items),
        "errors": errors,
        "items": [item.__dict__ for item in items],
    }

    markdown_text = _render_markdown(payload)

    obsidian_path = None
    if getattr(config, "obsidian_enabled", False):
        obsidian_dir = str(getattr(config, "obsidian_dir", "") or "").strip()
        if obsidian_dir:
            filename_template = str(getattr(config, "obsidian_filename", "news_{date}.md") or "news_{date}.md")
            try:
                obsidian_path = _write_obsidian_copy(obsidian_dir, filename_template, date_key, markdown_text)
            except Exception as exc:
                logger.warning(f"Obsidian写入失败: {exc}")
                errors.append(f"obsidian_write_failed: {exc}")
        else:
            errors.append("obsidian_dir_missing")

    payload["obsidian_path"] = obsidian_path

    json_path = output_dir / f"news_{date_key}.json"
    md_path = output_dir / f"news_{date_key}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_text, encoding="utf-8")

    _update_index(output_dir, payload)

    return {
        "success": True,
        "date": date_key,
        "output_dir": str(output_dir),
        "json": str(json_path),
        "markdown": str(md_path),
        "obsidian_path": obsidian_path,
        "total_items": len(items),
        "errors": errors,
    }


def list_news_digests(output_dir: str, limit: int = 30) -> Dict[str, Any]:
    path = Path(output_dir)
    if not path.exists():
        return {"items": []}
    index_path = path / "news_index.json"
    items: List[Dict[str, Any]] = []
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception:
            items = []
    if not items:
        items = _scan_news_files(path)
    items = sorted(items, key=lambda item: item.get("date") or "", reverse=True)
    return {"items": items[:limit]}


def load_news_digest(output_dir: str, date_key: str) -> Dict[str, Any]:
    if not DATE_KEY_PATTERN.match(date_key or ""):
        return {"error": "invalid_date"}
    path = Path(output_dir) / f"news_{date_key}.json"
    if not path.exists():
        return {"error": "news_not_found"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "news_load_failed"}


def _scan_news_files(path: Path) -> List[Dict[str, Any]]:
    items = []
    for entry in path.glob("news_*.json"):
        name = entry.stem.replace("news_", "")
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
            "errors": data.get("errors", []),
        })
    return items


def _update_index(output_dir: Path, digest: Dict[str, Any]) -> None:
    index_path = output_dir / "news_index.json"
    items = []
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else []
        except Exception:
            items = []
    items = [item for item in items if item.get("date") != digest.get("date")]
    items.append({
        "date": digest.get("date"),
        "generated_at": digest.get("generated_at"),
        "total_items": digest.get("total_items"),
        "errors": digest.get("errors", []),
    })
    items = sorted(items, key=lambda item: item.get("date") or "", reverse=True)
    index_path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")


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
        return f"news_{date_key}.md"


def _collect_items(
    topics: List[str],
    sources: List[str],
    per_topic_limit: int
) -> Tuple[List[NewsItem], List[str]]:
    collected: List[NewsItem] = []
    errors: List[str] = []
    seen = set()
    tasks = _expand_sources(sources, topics)
    for url, topic in tasks:
        try:
            feed_title, feed_items = fetch_feed_items(url)
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue
        for item in feed_items:
            news_item = NewsItem(
                title=item.title,
                link=item.link,
                summary=item.summary,
                source=item.source,
                published=item.published,
                topic=None,
            )
            if topic:
                news_item.topic = topic
            if topics and not news_item.topic:
                hit = _match_topic(news_item, topics)
                if not hit:
                    continue
                news_item.topic = hit
            key = news_item.link or news_item.title
            if not key or key in seen:
                continue
            seen.add(key)
            news_item.source = news_item.source or feed_title or news_item.source
            collected.append(news_item)

    if topics:
        grouped = []
        for topic in topics:
            chunk = [item for item in collected if item.topic == topic]
            grouped.extend(chunk[:per_topic_limit] if per_topic_limit else chunk)
        collected = grouped or collected

    collected.sort(key=lambda item: item.published or "", reverse=True)
    return collected, errors


def _expand_sources(sources: Iterable[str], topics: List[str]) -> List[Tuple[str, Optional[str]]]:
    expanded: List[Tuple[str, Optional[str]]] = []
    if not sources:
        return expanded
    for raw in sources:
        if "{topic}" in raw and topics:
            for topic in topics:
                url = raw.replace("{topic}", urllib.parse.quote(topic))
                expanded.append((url, topic))
        else:
            expanded.append((raw, None))
    return expanded


def _match_topic(item: NewsItem, topics: List[str]) -> Optional[str]:
    text = f"{item.title} {item.summary}".lower()
    for topic in topics:
        if topic.lower() in text:
            return topic
    return None


def _render_markdown(digest: Dict[str, Any]) -> str:
    date_key = digest.get("date", "")
    topics = digest.get("topics") or []
    items = digest.get("items") or []
    lines = [
        f"# Daily News Digest ({date_key})",
        "",
        f"Generated: {digest.get('generated_at', '')}",
        f"Topics: {', '.join(topics) if topics else '--'}",
        f"Total items: {digest.get('total_items', 0)}",
        "",
    ]
    if not items:
        lines.append("No news items found.")
        return "\n".join(lines)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        topic = item.get("topic") or "Other"
        grouped.setdefault(topic, []).append(item)

    for topic, topic_items in grouped.items():
        lines.append(f"## {topic}")
        for entry in topic_items:
            title = entry.get("title") or "Untitled"
            link = entry.get("link") or ""
            summary = entry.get("summary") or ""
            source = entry.get("source") or ""
            published = entry.get("published") or ""
            lines.append(f"- [{title}]({link})")
            if published or source:
                meta = " | ".join([value for value in [source, published] if value])
                lines.append(f"  - {meta}")
            if summary:
                lines.append(f"  - {summary}")
        lines.append("")
    return "\n".join(lines)
