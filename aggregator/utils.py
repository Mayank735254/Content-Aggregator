import requests
from .models import News, Website
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

def process_feed_items(items: List[BeautifulSoup], website: Website) -> List[News]:
    """Process feed items in bulk and return News objects for batch insert."""
    news_items = []
    for item in items:
        try:
            title = item.find(website.news_title_field).text.strip()
            link = item.find(website.news_link_field).text.strip()
            if not link:
                link = item.find(website.news_link_field, href=True)["href"]
            content = item.find(website.news_content_field).text.strip()
            guid = item.find(website.news_guid_field).text.strip()
            
            news = News(
                website=website,
                title=title,
                link=link,
                content=content,
                guid=guid,
                author=''
            )
            news_items.append(news)
        except (AttributeError, KeyError) as e:
            logger.warning(f"Error processing item from {website.name}: {e}")
            continue
    return news_items


def get_source(url):
    """Return the source code for the provided URL.
    Args:
        url (string): URL of the page to scrape.
    Returns:
        response (object): HTTP response object from requests_html.
    """
    try:
        # Use plain requests to avoid depending on requests_html and
        # the lxml_html_clean package. For RSS feeds we only need the
        # response text, not JS rendering. Some feeds block non-browser
        # user agents; set a common User-Agent header to improve success.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/117.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        # Log and return None so callers can handle missing responses
        logger.error(f"Error fetching {url}: {e}")
        return None


def get_feed(website) -> Optional[List[News]]:
    """Fetch and process a single website's RSS feed.
    Args:
        :param website:
    Returns:
        List of News objects if successful, None if failed
    """
    response = get_source(website.rss_url)
    if not response:
        # Could not fetch feed for this website; skip it
        return
    raw_html = response.text
    try:
        soup = BeautifulSoup(raw_html, 'xml')
        items = soup.find_all(website.rss_item_node)
        return process_feed_items(items, website)
    except Exception as e:
        logger.error(f"Error parsing feed {website.rss_url}: {e}")
        return None


def batch_insert_news(all_news: List[News]):
    """Insert or update news items in bulk for better performance."""
    with transaction.atomic():
        # Get existing GUIDs to avoid duplicates
        existing_guids = set(News.objects.filter(
            guid__in=[n.guid for n in all_news]
        ).values_list('guid', flat=True))
        
        # Split into new and existing items
        to_insert = [n for n in all_news if n.guid not in existing_guids]
        
        # Bulk create new items
        if to_insert:
            News.objects.bulk_create(to_insert)


def aggregate_news(website):
    """Process all websites in parallel for better performance."""
    MAX_WORKERS = 4  # Adjust based on your needs
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Start parallel fetches
        future_to_website = {
            executor.submit(get_feed, website): website 
            for website in Website.objects.all()
        }
        
        # Collect results as they complete
        all_news = []
        for future in as_completed(future_to_website):
            website = future_to_website[future]
            try:
                news_items = future.result()
                if news_items:
                    all_news.extend(news_items)
            except Exception as e:
                logger.error(f"Error processing website {website.name}: {e}")
        
        # Batch insert all collected news items
        if all_news:
            batch_insert_news(all_news)
        
        logger.info(f"Aggregation complete. Processed {len(all_news)} items.")
