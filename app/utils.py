from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from app.schemas import MentionItem

def normalize_mention(mention_item: MentionItem) -> MentionItem:
    return mention_item.model_copy(
        update={
            "source": normalize_source(mention_item.source),
            "title": normalize_text(mention_item.title),
            "content": normalize_text(mention_item.content),
            "published_at": parse_date(mention_item.published_at),
            "engagement": parse_int(mention_item.engagement),
        }
    )

def normalize_source(source: Optional[str]) -> Optional[str]:
    if not source:
        return None

    return " ".join(source.strip().split())

def normalize_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    bs = BeautifulSoup(value, "html.parser") 
    value = bs.get_text(separator=" ", strip=True)

    return value

def parse_int(value: Any) -> Optional[int]:
    if isinstance(value, (bool, float, int)):
        return int(value)

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        try:
            return int(float(value.replace(",", "")))
        except ValueError:
            return None

    return None

def parse_date(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    # ISO 8601:
    # 2026-08-10T08:15:00Z
    # 2026-08-11T14:02:33+08:00
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue

    return None
