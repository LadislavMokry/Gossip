from __future__ import annotations

from app.admin import create_source
from app.db import get_supabase


TOPIC_SOURCES: dict[str, list[dict]] = {
    "Celebrities / Entertainment": [
        {"name": "TMZ", "source_type": "rss", "url": "https://www.tmz.com/rss.xml"},
        {"name": "Page Six", "source_type": "rss", "url": "https://pagesix.com/feed/"},
        {"name": "Variety", "source_type": "rss", "url": "https://variety.com/feed/"},
        {"name": "Hollywood Reporter", "source_type": "rss", "url": "https://www.hollywoodreporter.com/feed/"},
        {"name": "Deadline", "source_type": "rss", "url": "https://deadline.com/feed/"},
        {
            "name": "Google News - Celebrity Gossip",
            "source_type": "rss",
            "url": "https://news.google.com/rss/search?q=celebrity+gossip&hl=en-US&gl=US&ceid=US:en",
        },
        {"name": "Reddit - PopCultureChat", "source_type": "reddit", "url": "https://www.reddit.com/r/popculturechat/"},
        {"name": "Reddit - Entertainment", "source_type": "reddit", "url": "https://www.reddit.com/r/entertainment/"},
    ],
    "TV & Streaming Recaps": [
        {"name": "TVLine", "source_type": "rss", "url": "https://tvline.com/feed/"},
        {"name": "TV Insider", "source_type": "rss", "url": "https://www.tvinsider.com/feed/"},
        {"name": "Variety - TV", "source_type": "rss", "url": "https://variety.com/v/tv/feed/"},
        {"name": "Deadline - TV", "source_type": "rss", "url": "https://deadline.com/v/tv/feed/"},
        {
            "name": "Google News - TV Recaps",
            "source_type": "rss",
            "url": "https://news.google.com/rss/search?q=tv+recap+OR+streaming+series&hl=en-US&gl=US&ceid=US:en",
        },
        {"name": "Reddit - Television", "source_type": "reddit", "url": "https://www.reddit.com/r/television/"},
        {"name": "Reddit - Movies", "source_type": "reddit", "url": "https://www.reddit.com/r/movies/"},
    ],
    "Sports (results + storylines)": [
        {"name": "CBS Sports", "source_type": "rss", "url": "https://www.cbssports.com/rss/headlines/"},
        {"name": "ESPN", "source_type": "rss", "url": "https://www.espn.com/espn/rss/news"},
        {"name": "Yahoo Sports", "source_type": "rss", "url": "https://sports.yahoo.com/rss/"},
        {
            "name": "Google News - US Sports",
            "source_type": "rss",
            "url": "https://news.google.com/rss/search?q=NFL+OR+NBA+OR+MLB+OR+NHL&hl=en-US&gl=US&ceid=US:en",
        },
        {"name": "Reddit - NFL", "source_type": "reddit", "url": "https://www.reddit.com/r/nfl/"},
        {"name": "Reddit - NBA", "source_type": "reddit", "url": "https://www.reddit.com/r/nba/"},
    ],
    "Viral / Human-interest": [
        {"name": "Good News Network", "source_type": "rss", "url": "https://www.goodnewsnetwork.org/feed/"},
        {"name": "Positive News", "source_type": "rss", "url": "https://positive.news/feed/"},
        {"name": "Upworthy", "source_type": "rss", "url": "https://www.upworthy.com/feed/"},
        {"name": "Bored Panda", "source_type": "rss", "url": "https://www.boredpanda.com/feed/"},
        {
            "name": "Google News - Human Interest",
            "source_type": "rss",
            "url": "https://news.google.com/rss/search?q=human+interest+story+OR+feel+good+news&hl=en-US&gl=US&ceid=US:en",
        },
        {"name": "Reddit - UpliftingNews", "source_type": "reddit", "url": "https://www.reddit.com/r/UpliftingNews/"},
        {"name": "Reddit - HumansBeingBros", "source_type": "reddit", "url": "https://www.reddit.com/r/HumansBeingBros/"},
    ],
    "Nostalgia / Pop-culture history": [
        {"name": "Smithsonian", "source_type": "rss", "url": "https://www.smithsonianmag.com/rss/"},
        {"name": "History Today", "source_type": "rss", "url": "http://www.historytoday.com/feed/rss.xml"},
        {"name": "Mental Floss", "source_type": "rss", "url": "https://www.mentalfloss.com/rss"},
        {"name": "Retro Dodo", "source_type": "rss", "url": "https://retrododo.com/feed/"},
        {
            "name": "Google News - Nostalgia",
            "source_type": "rss",
            "url": "https://news.google.com/rss/search?q=nostalgia+OR+\"on+this+day\"+OR+\"pop+culture\"+history&hl=en-US&gl=US&ceid=US:en",
        },
        {"name": "Reddit - OldSchoolCool", "source_type": "reddit", "url": "https://www.reddit.com/r/OldSchoolCool/"},
        {"name": "Reddit - Nostalgia", "source_type": "reddit", "url": "https://www.reddit.com/r/nostalgia/"},
    ],
}


def main() -> None:
    sb = get_supabase()
    projects = sb.table("projects").select("id, name").execute().data or []
    project_map = {str(p.get("name")).strip(): p.get("id") for p in projects if p.get("id")}

    for topic, sources in TOPIC_SOURCES.items():
        project_id = project_map.get(topic)
        if not project_id:
            print(f"skip: no project for {topic}")
            continue
        existing = (
            sb.table("sources")
            .select("id, url, name")
            .eq("project_id", project_id)
            .execute()
            .data
            or []
        )
        existing_urls = {str(row.get("url", "")).strip().lower() for row in existing}
        for src in sources:
            url = src["url"].strip()
            if url.lower() in existing_urls:
                print(f"skip: {topic} -> {src['name']}")
                continue
            created = create_source(project_id, src)
            print(f"created: {topic} -> {created.get('name')} ({created.get('id')})")


if __name__ == "__main__":
    main()
