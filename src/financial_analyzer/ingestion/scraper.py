# FILE: src/financial_analyzer/ingestion/scraper.py

import boto3
import feedparser
import requests
from bs4 import BeautifulSoup
import json
import hashlib
import logging

# Conditional import for running as a script vs. as a module
if __name__ == "__main__" and __package__ is None:
    # Add src to path to allow absolute imports
    import sys
    from pathlib import Path

    file = Path(__file__).resolve()
    parent, root = file.parent, file.parents[2]
    sys.path.append(str(root))
    from src.financial_analyzer.config import settings
else:
    from ..config import settings

# --- Setup basic logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class NewsScraper:
    """
    Scrapes financial news articles from a list of RSS feeds,
    parses their content, and saves them to an AWS S3 bucket.
    """

    def __init__(self, feed_urls: list[str], bucket_name: str):
        self.feed_urls = feed_urls
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        logging.info(f"NewsScraper initialized for bucket: {self.bucket_name}")

    def _get_article_content(self, url: str) -> str:
        """Fetches and parses the main content from a given article URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Find all paragraph tags and join their text
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text() for p in paragraphs])
            return content
        except requests.RequestException as e:
            logging.error(f"Could not fetch article content from {url}: {e}")
            return ""

    def scrape_and_save(self):
        """
        Iterates through RSS feeds, scrapes articles, and saves them to S3.
        """
        logging.info("Starting scrape and save process...")
        for feed_url in self.feed_urls:
            feed = feedparser.parse(feed_url)
            logging.info(f"Processing feed: {feed.feed.title}")

            for entry in feed.entries:
                article_url = entry.link
                # Create a unique, consistent filename from the URL
                file_name = hashlib.md5(article_url.encode('utf-8')).hexdigest() + '.json'

                content = self._get_article_content(article_url)
                if not content:
                    continue

                article_data = {
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", "N/A"),
                    "source": feed.feed.title,
                    "content": content
                }

                try:
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=f"raw_news/{file_name}",
                        Body=json.dumps(article_data, indent=4),
                        ContentType='application/json'
                    )
                    logging.info(f"Successfully saved article to S3: {file_name}")
                except Exception as e:
                    logging.error(f"Failed to upload article to S3: {e}")


if __name__ == "__main__":
    # Example RSS feeds (replace with your preferred sources)
    RSS_FEEDS = [
        "http://feeds.reuters.com/reuters/businessNews",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # Wall Street Journal
    ]

    scraper = NewsScraper(feed_urls=RSS_FEEDS, bucket_name=settings.S3_BUCKET_NAME)
    scraper.scrape_and_save()