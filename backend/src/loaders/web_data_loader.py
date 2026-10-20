import random
import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils import logger

_log = logger.bind(service="web_data_loader")
class ScraperSession:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        
        # Retry strategy for network resilience
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_page(self, url: str) -> BeautifulSoup | None:
        headers = {
            "User-Agent": self.ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        # Polite delay with jitter
        time.sleep(random.uniform(1.5, 3.5))
        
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None


def parse_data(soup: BeautifulSoup) -> dict[str, str]:
    """Extract clean title, metadata, and main content text from any webpage."""
    # 1. Remove non-content elements
    for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "svg"]):
        element.decompose()

    # 2. Extract Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    main_container = soup.find("article") or soup.find("main") or soup.find("body") or soup
    
    text_blocks = []
    for tag in main_container.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        content = tag.get_text(strip=True)
        if content:
            text_blocks.append(content)

    full_text = "\n\n".join(text_blocks)

    return {
        "title": title,
        "text": full_text
    }

