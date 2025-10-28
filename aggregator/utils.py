import requests
from .models import News, Website
from bs4 import BeautifulSoup


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
        print(f"Error fetching {url}: {e}")
        return None


def get_feed(website):
    """Return a Pandas dataframe containing the RSS feed contents.

    Args:
        :param website:

    Returns:
    """

    response = get_source(website.rss_url)

    if not response:
        # Could not fetch feed for this website; skip it
        return

    raw_html = response.text
    soup = BeautifulSoup(raw_html, 'xml')
    items = soup.find_all(website.rss_item_node)
    for item in items:
        title = item.find(website.news_title_field).text
        # pub_date = item.find(website.news_published_field, first=True).text
        link = item.find(website.news_link_field).text
        if not link:
            link = item.find(website.news_link_field, href=True)["href"]
        content = item.find(website.news_content_field).text
        guid = item.find(website.news_guid_field).text
        author = ''  # item.find(website.news_author_field, first=True).text

        news = News()
        news.website = website
        news.title = title
        # news.published = pub_date
        news.link = link
        news.content = content
        news.guid = guid
        news.author = author
        insert_news(news)


def insert_news(news):
    if News.objects.filter(guid=news.guid).exists():
        update_news = News.objects.get(guid=news.guid)
        #update_news = news
        #update_news.save()
    else:
        insert_news = news
        insert_news.save()


def aggregate_news(website):
    get_feed(website)
