from __future__ import annotations

from app.admin import create_project
from app.db import get_supabase


TOPICS = [
    "Celebrities / Entertainment",
    "TV & Streaming Recaps",
    "Sports (results + storylines)",
    "Viral / Human-interest",
    "Nostalgia / Pop-culture history",
]


def main() -> None:
    sb = get_supabase()
    existing = sb.table("projects").select("id, name").execute().data or []
    existing_names = {str(row.get("name", "")).strip().lower() for row in existing}

    for topic in TOPICS:
        key = topic.strip().lower()
        if key in existing_names:
            print(f"skip: {topic}")
            continue
        created = create_project(
            name=topic,
            description=f"Launch topic: {topic}",
            language="en",
        )
        print(f"created: {created.get('id')} {topic}")


if __name__ == "__main__":
    main()
