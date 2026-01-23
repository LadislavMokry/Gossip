from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Iterable
from xml.sax.saxutils import escape

from app.podcast.meta import PodcastMeta


@dataclass
class PodcastEpisode:
    title: str
    description: str
    guid: str
    audio_url: str
    audio_length: int
    duration_seconds: int
    published_at: datetime


def _rfc2822(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def _itunes_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _category_xml(meta: PodcastMeta) -> str:
    if meta.category_sub:
        return (
            f'<itunes:category text="{escape(meta.category_main)}">'
            f'<itunes:category text="{escape(meta.category_sub)}" />'
            "</itunes:category>"
        )
    return f'<itunes:category text="{escape(meta.category_main)}" />'


def build_rss(
    meta: PodcastMeta,
    episodes: Iterable[PodcastEpisode],
    feed_url: str,
    site_url: str | None,
    image_url: str,
) -> str:
    items_xml = []
    for ep in episodes:
        items_xml.append(
            "\n".join(
                [
                    "<item>",
                    f"<title>{escape(ep.title)}</title>",
                    f"<description>{escape(ep.description)}</description>",
                    f"<guid isPermaLink=\"false\">{escape(ep.guid)}</guid>",
                    f"<pubDate>{_rfc2822(ep.published_at)}</pubDate>",
                    (
                        f"<enclosure url=\"{escape(ep.audio_url)}\" "
                        f"length=\"{int(ep.audio_length)}\" type=\"audio/mpeg\" />"
                    ),
                    f"<itunes:duration>{_itunes_duration(ep.duration_seconds)}</itunes:duration>",
                    f"<itunes:explicit>{escape(meta.explicit)}</itunes:explicit>",
                    "</item>",
                ]
            )
        )
    items = "\n".join(items_xml)

    description = escape(meta.description)
    link = escape(site_url or feed_url)
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                '<rss version="2.0" '
                'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
                'xmlns:atom="http://www.w3.org/2005/Atom">'
            ),
            "<channel>",
            f"<title>{escape(meta.title)}</title>",
            f"<link>{link}</link>",
            f"<language>{escape(meta.language)}</language>",
            f"<description>{description}</description>",
            f"<itunes:author>{escape(meta.author)}</itunes:author>",
            f"<itunes:explicit>{escape(meta.explicit)}</itunes:explicit>",
            f"<atom:link href=\"{escape(feed_url)}\" rel=\"self\" type=\"application/rss+xml\" />",
            "<itunes:owner>",
            f"<itunes:name>{escape(meta.owner_name)}</itunes:name>",
            f"<itunes:email>{escape(meta.owner_email)}</itunes:email>",
            "</itunes:owner>",
            f"<itunes:image href=\"{escape(image_url)}\" />",
            _category_xml(meta),
            items,
            "</channel>",
            "</rss>",
        ]
    )
