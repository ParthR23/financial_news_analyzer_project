"""financial_analyzer.ingestion.scraper

This module provides a `NewsScraper` class that can download articles from a
set of RSS feeds and persist them to AWS S3 as JSON files.  It is intended to
be used as part of the ingestion layer for the financial-news-analyzer
pipeline.

Requirements (ensure they are installed in your environment):
    - boto3
    - feedparser
    - beautifulsoup4
    - requests

Environment:
    A valid AWS credential chain must be available so that the underlying
    `boto3` client can authenticate when uploading the article objects.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Iterable, List

import boto3
import feedparser
import requests
from bs4 import BeautifulSoup

try:
    # The project may expose a centralised settings module; fall back to env vars
    # if that is not the case.
    from settings import S3_BUCKET_NAME  # type: ignore
except ImportError:  # pragma: no cover
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("NEWS_SCRAPER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NewsScraper:
    """Download articles from RSS feeds and save them to S3 as JSON files."""

    def __init__(
        self,
        rss_feeds: Iterable[str],
        bucket_name: str,
        s3_folder: str = "raw_articles",
        aws_region: str | None = None,
    ) -> None:
        """Create a new ``NewsScraper``.

        Args:
            rss_feeds: A collection of RSS/Atom feed URLs.
            bucket_name: The name of the destination S3 bucket.
            s3_folder: The folder (key prefix) inside the bucket under which
                the article JSON files will be stored.  Defaults to
                ``raw_articles``.
            aws_region: Optionally force the AWS region to use when
                initialising the Boto3 client.
        """
        self.rss_feeds: List[str] = list(rss_feeds)
        self.bucket_name = bucket_name
        self.s3_folder = s3_folder.rstrip("/")  # remove any trailing slash

        # Lazily initialised boto3 client so that unit-tests can patch it.
        logger.debug("Initialising boto3 S3 client for bucket '%s'", bucket_name)
        self.s3_client = boto3.client("s3", region_name=aws_region)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def scrape_and_save(self) -> None:
        """Iterate through all feeds and persist each article as JSON to S3."""

        if not self.bucket_name:
            raise RuntimeError(
                "S3 bucket name was not provided and could not be resolved from settings."
            )

        for feed_url in self.rss_feeds:
            logger.info("Processing feed: %s", feed_url)
            try:
                feed = feedparser.parse(feed_url)
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to parse feed '%s': %s", feed_url, exc)
                continue

            for entry in feed.entries:
                try:
                    self._process_entry(entry)
                except Exception as exc:  # pragma: no cover
                    logger.exception(
                        "Error processing entry from feed '%s' (link=%s): %s",
                        feed_url,
                        getattr(entry, "link", "<unknown>"),
                        exc,
                    )
                    # continue with next entry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _process_entry(self, entry: feedparser.FeedParserDict) -> None:
        """Fetch a feed *entry* and upload it to S3 as JSON."""
        url: str = entry.get("link", "")
        if not url:
            logger.warning("Skipping entry without link: %s", entry)
            return

        logger.debug("Fetching article: %s", url)
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Rudimentary content extraction: concatenate text from all <p> tags
        content_parts = [p.get_text(strip=True) for p in soup.find_all("p")]
        content = "\n\n".join(content_parts)

        item = {
            "title": entry.get("title", ""),
            "url": url,
            "published": self._parse_published(entry),
            "content": content,
        }

        object_key = f"{self.s3_folder}/{self._article_filename(url)}"

        logger.info("Uploading article to s3://%s/%s", self.bucket_name, object_key)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=json.dumps(item, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _article_filename(url: str) -> str:
        """Return a deterministic filename (without path) for *url*."""
        digest = hashlib.sha256(url.encode()).hexdigest()
        return f"{digest}.json"

    @staticmethod
    def _parse_published(entry: feedparser.FeedParserDict) -> str:
        """Return an ISO-8601 string representing the *entry*'s published date."""
        # feedparser normalises dates to struct_time tuples when possible.
        if "published_parsed" in entry and entry.published_parsed is not None:
            ts = time.mktime(entry.published_parsed)
            return datetime.utcfromtimestamp(ts).isoformat() + "Z"
        # Fallback to the raw string if no structured time is available.
        return entry.get("published", "")


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    # A non-exhaustive list of publicly available financial-news RSS feeds.
    default_feeds = [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://www.bloomberg.com/feed/podcast/etf-report.xml",
        "https://www.marketwatch.com/rss/topstories",
    ]

    bucket = S3_BUCKET_NAME
    if not bucket:
        raise SystemExit(
            "S3 bucket name is not configured. Set S3_BUCKET_NAME in settings.py or as env var."
        )

    scraper = NewsScraper(default_feeds, bucket)
    scraper.scrape_and_save()

