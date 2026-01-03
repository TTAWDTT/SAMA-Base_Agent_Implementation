from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Tuple

USER_AGENT = "SAMA-RSS/1.0"


@dataclass
class FeedItem:
    title: str
    link: str
    summary: str
    source: str
    published: Optional[str]
    author: Optional[str] = None


def fetch_feed_items(url: str, timeout: int = 12, user_agent: str = USER_AGENT) -> Tuple[str, List[FeedItem]]:
    xml_text = _fetch_text(url, timeout=timeout, user_agent=user_agent)
    if not xml_text:
        raise ValueError("empty_feed")
    root = ET.fromstring(xml_text)
    if root.tag.lower().endswith("rss") or root.find("channel") is not None:
        return _parse_rss(root)
    if root.tag.lower().endswith("feed"):
        return _parse_atom(root)
    return _parse_rss(root)


def _parse_rss(root: ET.Element) -> Tuple[str, List[FeedItem]]:
    channel = root.find("channel") if root is not None else None
    title = _text(channel, "title") if channel is not None else ""
    items: List[FeedItem] = []
    for item in channel.findall("item") if channel is not None else []:
        items.append(FeedItem(
            title=_text(item, "title"),
            link=_text(item, "link"),
            summary=_strip_html(_text(item, "description") or _text(item, "content:encoded")),
            published=_parse_date(_text(item, "pubDate")) or _parse_date(_text(item, "published")),
            source=_text(item, "source") or title,
            author=_text(item, "author") or _text(item, "dc:creator"),
        ))
    return title, items


def _parse_atom(root: ET.Element) -> Tuple[str, List[FeedItem]]:
    title = _text_ns(root, "title")
    items: List[FeedItem] = []
    for entry in root.findall("{*}entry"):
        link = ""
        for link_el in entry.findall("{*}link"):
            rel = (link_el.attrib.get("rel") or "").lower()
            if rel in {"alternate", ""}:
                link = link_el.attrib.get("href", "")
                if link:
                    break
        items.append(FeedItem(
            title=_text_ns(entry, "title"),
            link=link,
            summary=_strip_html(_text_ns(entry, "summary") or _text_ns(entry, "content")),
            published=_parse_date(_text_ns(entry, "updated") or _text_ns(entry, "published")),
            source=title,
            author=_text_ns(entry, "author"),
        ))
    return title, items


def _text(node: Optional[ET.Element], tag: str) -> str:
    if node is None:
        return ""
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _text_ns(node: Optional[ET.Element], tag: str) -> str:
    if node is None:
        return ""
    child = node.find(f"{{*}}{tag}")
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _strip_html(value: str) -> str:
    if not value:
        return ""
    clean = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", clean).strip()


def _parse_date(value: str) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed:
            if parsed.tzinfo:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.isoformat(timespec="seconds")
    except Exception:
        pass
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.isoformat(timespec="seconds")
    except Exception:
        return None


def _fetch_text(url: str, timeout: int = 12, user_agent: str = USER_AGENT) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="ignore")
