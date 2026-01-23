from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PodcastMeta:
    title: str
    description: str
    category_main: str
    category_sub: str | None
    language: str
    owner_name: str
    owner_email: str
    author: str
    explicit: str  # "yes" or "no"
    site_url: str | None = None


_FOOTER = (
    "OnePlace is a daily network of short, focused shows across entertainment, TV, "
    "sports, human-interest, and nostalgia.\n"
    "If you like this feed, follow the other OnePlace shows for the full picture."
)


def _join_description(primary: str) -> str:
    return f"{primary}\n{_FOOTER}"


DEFAULT_OWNER_NAME = "OnePlace"
DEFAULT_OWNER_EMAIL = "ladislav.work@gmail.com"


PROJECT_PODCASTS: dict[str, PodcastMeta] = {
    "Celebrities / Entertainment": PodcastMeta(
        title="Red Carpet Scoop OP",
        description=_join_description(
            "Your daily hit of celebrity headlines, relationships, and the stories behind the red carpet. "
            "Quick, punchy, and designed to keep you in the loop."
        ),
        category_main="News",
        category_sub="Entertainment News",
        language="en-US",
        owner_name=DEFAULT_OWNER_NAME,
        owner_email=DEFAULT_OWNER_EMAIL,
        author=DEFAULT_OWNER_NAME,
        explicit="no",
    ),
    "TV & Streaming Recaps": PodcastMeta(
        title="Binge Brief OP",
        description=_join_description(
            "Daily recaps and highlights from the shows everyone is watching - plus what to stream next. "
            "Fast summaries with just enough context to keep you caught up."
        ),
        category_main="TV & Film",
        category_sub=None,
        language="en-US",
        owner_name=DEFAULT_OWNER_NAME,
        owner_email=DEFAULT_OWNER_EMAIL,
        author=DEFAULT_OWNER_NAME,
        explicit="no",
    ),
    "Sports (results + storylines)": PodcastMeta(
        title="Game Day Wire OP",
        description=_join_description(
            "Daily sports results, storylines, and the moments that sparked debate. "
            "Scores, context, and the why behind the headlines."
        ),
        category_main="Sports",
        category_sub="Sports News",
        language="en-US",
        owner_name=DEFAULT_OWNER_NAME,
        owner_email=DEFAULT_OWNER_EMAIL,
        author=DEFAULT_OWNER_NAME,
        explicit="no",
    ),
    "Viral / Human-interest": PodcastMeta(
        title="Feel-Good Daily OP",
        description=_join_description(
            "A daily dose of human-interest stories, viral wins, and small moments of hope. "
            "The feel-good feed that resets your day."
        ),
        category_main="Society & Culture",
        category_sub=None,
        language="en-US",
        owner_name=DEFAULT_OWNER_NAME,
        owner_email=DEFAULT_OWNER_EMAIL,
        author=DEFAULT_OWNER_NAME,
        explicit="no",
    ),
    "Nostalgia / Pop-culture history": PodcastMeta(
        title="Retro Recall OP",
        description=_join_description(
            "Daily nostalgia hits from pop culture, music, and throwback moments that shaped us. "
            "Short, story-driven blasts from the past."
        ),
        category_main="History",
        category_sub=None,
        language="en-US",
        owner_name=DEFAULT_OWNER_NAME,
        owner_email=DEFAULT_OWNER_EMAIL,
        author=DEFAULT_OWNER_NAME,
        explicit="no",
    ),
}


def get_meta_for_project(project_name: str) -> PodcastMeta | None:
    return PROJECT_PODCASTS.get(project_name)
