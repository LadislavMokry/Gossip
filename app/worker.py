import argparse
import time

from .pipeline import run_extraction, run_first_judge, run_generation, run_second_judge
from .scrape import (
    scrape_category_pages,
    upsert_category_pages,
    extract_article_urls,
    scrape_article_pages,
)


def run_scrape_once() -> int:
    rows = scrape_category_pages()
    upserted = upsert_category_pages(rows)
    return len(upserted)


def run_extract_links(limit: int = 50) -> int:
    return extract_article_urls(limit=limit)


def run_scrape_articles(limit: int = 20) -> int:
    return scrape_article_pages(limit=limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Background worker")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scrape", help="Scrape configured sources once")
    sub.add_parser("extract-links", help="Extract article URLs from category pages")
    sub.add_parser("scrape-articles", help="Scrape full articles from URLs")

    sub.add_parser("extract", help="Run extraction once")
    sub.add_parser("judge", help="Run first judge once")
    sub.add_parser("generate", help="Run generation once")
    sub.add_parser("second-judge", help="Run second judge once")

    loop_parser = sub.add_parser("scrape-loop", help="Scrape on an interval")
    loop_parser.add_argument("--interval", type=int, default=3600, help="Seconds between runs")

    extract_loop = sub.add_parser("extract-loop", help="Extraction on an interval")
    extract_loop.add_argument("--interval", type=int, default=600, help="Seconds between runs")

    judge_loop = sub.add_parser("judge-loop", help="First judge on an interval")
    judge_loop.add_argument("--interval", type=int, default=900, help="Seconds between runs")

    gen_loop = sub.add_parser("generate-loop", help="Generation on an interval")
    gen_loop.add_argument("--interval", type=int, default=1200, help="Seconds between runs")

    second_loop = sub.add_parser("second-judge-loop", help="Second judge on an interval")
    second_loop.add_argument("--interval", type=int, default=1800, help="Seconds between runs")

    args = parser.parse_args()

    if args.command == "scrape":
        count = run_scrape_once()
        print(f"scraped={count}")
        return

    if args.command == "extract-links":
        count = run_extract_links()
        print(f"links_extracted={count}")
        return

    if args.command == "scrape-articles":
        count = run_scrape_articles()
        print(f"articles_scraped={count}")
        return

    if args.command == "extract":
        count = run_extraction()
        print(f"extracted={count}")
        return

    if args.command == "judge":
        count = run_first_judge()
        print(f"judged={count}")
        return

    if args.command == "generate":
        count = run_generation()
        print(f"generated_posts={count}")
        return

    if args.command == "second-judge":
        count = run_second_judge()
        print(f"second_judged={count}")
        return

    if args.command == "scrape-loop":
        while True:
            count = run_scrape_once()
            print(f"scraped={count}")
            time.sleep(args.interval)

    if args.command == "extract-loop":
        while True:
            count = run_extraction()
            print(f"extracted={count}")
            time.sleep(args.interval)

    if args.command == "judge-loop":
        while True:
            count = run_first_judge()
            print(f"judged={count}")
            time.sleep(args.interval)

    if args.command == "generate-loop":
        while True:
            count = run_generation()
            print(f"generated_posts={count}")
            time.sleep(args.interval)

    if args.command == "second-judge-loop":
        while True:
            count = run_second_judge()
            print(f"second_judged={count}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
