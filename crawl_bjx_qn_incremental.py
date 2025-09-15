#!/usr/bin/env python3
"""
BJX QN Website Crawler - Incremental Version

This script implements incremental crawling to avoid duplicates:
- On first run: crawls all available articles
- On subsequent runs: only crawls articles newer than last crawl time
- Maintains a state file with last crawl timestamp
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import csv
import sys
import time
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = 'https://qn.bjx.com.cn/zq'

# Multiple User-Agent strings for rotation (helps bypass some blocking)
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

def get_headers():
    """Get headers with random User-Agent for better compatibility."""
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',  # Chinese language preference
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }

CRAWL_STATE_FILE = 'crawl_state.json'

def load_crawl_state() -> Dict:
    """Load the last crawl state from file."""
    try:
        if os.path.exists(CRAWL_STATE_FILE):
            with open(CRAWL_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"Loaded crawl state: last_crawl_time={state.get('last_crawl_time', 'None')}")
                return state
    except Exception as e:
        logger.warning(f"Error loading crawl state: {e}")
    
    return {
        'last_crawl_time': None,
        'total_articles_crawled': 0,
        'first_run': True
    }

def save_crawl_state(state: Dict):
    """Save the current crawl state to file."""
    try:
        with open(CRAWL_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved crawl state: last_crawl_time={state.get('last_crawl_time')}")
    except Exception as e:
        logger.error(f"Error saving crawl state: {e}")

def parse_article_date(date_str: str) -> Optional[datetime]:
    """Parse article date string to datetime object."""
    try:
        # Assuming format is YYYY-MM-DD
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            # Try alternative format if needed
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Unable to parse date: {date_str}")
            return None

def is_article_newer_than_cutoff(article_date_str: str, cutoff_time: datetime) -> bool:
    """Check if article is newer than the cutoff time."""
    article_date = parse_article_date(article_date_str)
    if not article_date:
        return True  # Include if we can't parse the date
    
    return article_date > cutoff_time

def fetch_html(url: str, timeout: int = 15, retries: int = 5) -> str:
    """
    Fetch HTML content from URL with retry logic and error handling.
    Enhanced for GitHub Actions with DNS optimization and longer timeouts.
    """
    session = requests.Session()
    session.headers.update(get_headers())
    
    # Add connection pooling and keep-alive for better performance
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=1,
        pool_maxsize=1,
        max_retries=0  # We handle retries manually
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # DNS optimization - ensure domain resolution works
    try:
        import socket
        ip = socket.gethostbyname('qn.bjx.com.cn')
        logger.debug(f"Resolved IP: {ip}")
    except Exception as e:
        logger.warning(f"DNS resolution failed: {e}")
        # Try alternative DNS servers
        for dns in ['8.8.8.8', '1.1.1.1', '208.67.222.222']:
            try:
                # This is just for logging, actual resolution happens in the request
                logger.debug(f"Testing DNS server: {dns}")
            except:
                pass
    
    for attempt in range(retries):
        try:
            logger.info(f"Fetching URL: {url} (attempt {attempt + 1}/{retries})")
            
            # Progressive timeout increase for GitHub Actions
            current_timeout = timeout + (attempt * 5)
            logger.debug(f"Using timeout: {current_timeout}s")
            
            response = session.get(url, timeout=current_timeout)
            response.raise_for_status()
            
            if len(response.text) < 100:
                logger.warning(f"Response too short ({len(response.text)} chars), may be blocked")
                if attempt < retries - 1:
                    logger.info("Retrying due to short response...")
                    time.sleep(3)
                    continue
                
            logger.info(f"Successfully fetched {len(response.text)} characters")
            return response.text
            
        except requests.exceptions.ConnectTimeout as e:
            logger.warning(f"Attempt {attempt + 1} failed: Connection timeout - {e}")
            if attempt < retries - 1:
                wait_time = (2 ** attempt) + 5  # Longer wait for timeouts
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise requests.RequestException(f"Connection timeout after {retries} attempts: {e}")
                
        except requests.exceptions.ReadTimeout as e:
            logger.warning(f"Attempt {attempt + 1} failed: Read timeout - {e}")
            if attempt < retries - 1:
                wait_time = (2 ** attempt) + 3
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise requests.RequestException(f"Read timeout after {retries} attempts: {e}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = (2 ** attempt) + 2
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise requests.RequestException(f"Failed to fetch {url} after {retries} attempts: {e}")

def parse_articles(html: str, base_url: str, cutoff_time: Optional[datetime] = None) -> List[Dict[str, str]]:
    """
    Parse article information from HTML content.
    Only include articles newer than cutoff_time if specified.
    """
    articles = []
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        container = soup.find('div', class_='cc-list-content')
        if not container:
            logger.error("Could not find container with class 'cc-list-content'")
            return articles
            
        ul_element = container.find('ul')
        if not ul_element:
            logger.error("Could not find ul element within cc-list-content")
            return articles
            
        li_elements = ul_element.find_all('li')
        logger.info(f"Found {len(li_elements)} article items on page")
        
        for i, li in enumerate(li_elements):
            try:
                link = li.find('a')
                if not link:
                    logger.warning(f"No link found in item {i+1}")
                    continue
                
                title = link.get('title', '').strip()
                if not title:
                    title = link.get_text(strip=True)
                
                href = link.get('href', '')
                if not href:
                    logger.warning(f"No href found in item {i+1}")
                    continue
                
                url = urljoin(base_url, href)
                
                date_span = li.find('span')
                date = date_span.get_text(strip=True) if date_span else ''
                
                if not title or not url:
                    logger.warning(f"Incomplete data for item {i+1}: title='{title}', url='{url}'")
                    continue
                
                # Check if article is newer than cutoff time
                if cutoff_time and date:
                    if not is_article_newer_than_cutoff(date, cutoff_time):
                        logger.debug(f"Skipping old article: {title} ({date})")
                        continue
                
                article = {
                    'title': title,
                    'date': date,
                    'url': url
                }
                
                articles.append(article)
                logger.debug(f"Included article: {article['title'][:50]}... ({date})")
                
            except Exception as e:
                logger.error(f"Error parsing item {i+1}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        
    return articles

def get_next_page_url(html: str, base_url: str) -> Optional[str]:
    """Extract the URL for the next page if pagination exists."""
    try:
        soup = BeautifulSoup(html, 'lxml')
        pagination = soup.find('div', class_='cc-paging')
        if not pagination:
            return None
            
        next_link = pagination.find('a', string='下一页')
        if not next_link:
            return None
            
        if 'disable' in next_link.get('class', []):
            return None
            
        href = next_link.get('href')
        if href and href != 'javascript:;':
            return urljoin(base_url, href)
            
    except Exception as e:
        logger.error(f"Error finding next page URL: {e}")
        
    return None

def crawl_incremental(start_url: str, cutoff_time: Optional[datetime] = None, max_pages: int = 50) -> List[Dict[str, str]]:
    """
    Crawl articles incrementally, stopping when we hit articles older than cutoff_time.
    """
    all_articles = []
    current_url = start_url
    page_count = 0
    found_old_articles = False
    
    while current_url and page_count < max_pages and not found_old_articles:
        page_count += 1
        logger.info(f"Crawling page {page_count}: {current_url}")
        
        try:
            html = fetch_html(current_url)
            page_articles = parse_articles(html, current_url, cutoff_time)
            
            if not page_articles:
                if cutoff_time:
                    logger.info(f"No new articles found on page {page_count}, assuming we've reached old content")
                    break
                else:
                    logger.warning(f"No articles found on page {page_count}")
            else:
                all_articles.extend(page_articles)
                logger.info(f"Found {len(page_articles)} new articles on page {page_count}")
                
                # If we have a cutoff time and found fewer articles than expected,
                # we might be hitting older content
                if cutoff_time and len(page_articles) < 20:  # Typical page has ~64 items
                    logger.info("Found fewer articles than expected, might be reaching old content")
            
            # Get next page URL
            next_url = get_next_page_url(html, current_url)
            if next_url:
                logger.info(f"Found next page: {next_url}")
                current_url = next_url
                time.sleep(1)  # Be respectful to the server
            else:
                logger.info("No more pages found")
                break
                
        except Exception as e:
            logger.error(f"Error crawling page {page_count}: {e}")
            break
    
    logger.info(f"Incremental crawling completed. New articles found: {len(all_articles)}")
    return all_articles

def load_existing_articles() -> List[Dict[str, str]]:
    """Load existing articles from the latest JSON file."""
    existing_files = ['latest_articles.json', 'articles.json']
    
    for filename in existing_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                logger.info(f"Loaded {len(articles)} existing articles from {filename}")
                return articles
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}")
    
    return []

def merge_articles(existing_articles: List[Dict[str, str]], new_articles: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Merge new articles with existing ones, avoiding duplicates based on URL.
    """
    # Create a set of existing URLs for fast lookup
    existing_urls = {article['url'] for article in existing_articles}
    
    # Add new articles that don't already exist
    unique_new_articles = []
    for article in new_articles:
        if article['url'] not in existing_urls:
            unique_new_articles.append(article)
        else:
            logger.debug(f"Skipping duplicate article: {article['title'][:50]}...")
    
    # Combine and sort by date (newest first)
    all_articles = existing_articles + unique_new_articles
    
    # Sort by date, handling cases where date might be missing
    def sort_key(article):
        try:
            return datetime.strptime(article['date'], '%Y-%m-%d')
        except:
            return datetime.min
    
    all_articles.sort(key=sort_key, reverse=True)
    
    logger.info(f"Merged articles: {len(existing_articles)} existing + {len(unique_new_articles)} new = {len(all_articles)} total")
    return all_articles

def save_to_json(articles: List[Dict[str, str]], filename: str = 'articles.json') -> None:
    """Save articles to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving JSON file: {e}")

def save_to_csv(articles: List[Dict[str, str]], filename: str = 'articles.csv') -> None:
    """Save articles to CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            if articles:
                fieldnames = ['title', 'date', 'url']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(articles)
        logger.info(f"Saved {len(articles)} articles to {filename}")
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")

def main():
    """Main function to orchestrate incremental crawling."""
    try:
        logger.info("Starting BJX QN incremental crawler...")
        
        # Load crawl state
        state = load_crawl_state()
        is_first_run = state.get('first_run', True)
        last_crawl_time = state.get('last_crawl_time')
        
        # Determine cutoff time for incremental crawling
        cutoff_time = None
        if not is_first_run and last_crawl_time:
            # Parse last crawl time and subtract a small buffer (1 hour) to avoid missing articles
            cutoff_time = datetime.fromisoformat(last_crawl_time.replace('Z', '+00:00')) - timedelta(hours=1)
            logger.info(f"Incremental crawl: looking for articles newer than {cutoff_time.isoformat()}")
        else:
            logger.info("First run: crawling all available articles")
        
        # Determine max pages based on run type
        max_pages = 50 if is_first_run else 10  # More pages for first run
        
        # Crawl new articles
        new_articles = crawl_incremental(BASE_URL, cutoff_time, max_pages)
        
        if is_first_run:
            # On first run, save all articles directly
            final_articles = new_articles
            logger.info(f"First run complete: found {len(final_articles)} articles")
        else:
            # On subsequent runs, merge with existing articles
            existing_articles = load_existing_articles()
            final_articles = merge_articles(existing_articles, new_articles)
            logger.info(f"Incremental crawl complete: {len(new_articles)} new articles added")
        
        if not final_articles:
            if is_first_run:
                logger.error("No articles were found on first run!")
                sys.exit(1)
            else:
                logger.info("No new articles found since last crawl")
                # Update state even if no new articles
                state.update({
                    'last_crawl_time': datetime.now(timezone.utc).isoformat(),
                    'first_run': False
                })
                save_crawl_state(state)
                sys.exit(0)
        
        # Save results
        save_to_json(final_articles)
        save_to_csv(final_articles)
        
        # Update crawl state
        state.update({
            'last_crawl_time': datetime.now(timezone.utc).isoformat(),
            'total_articles_crawled': len(final_articles),
            'first_run': False
        })
        save_crawl_state(state)
        
        # Print summary
        if is_first_run:
            print(f"\n✅ First crawl completed: {len(final_articles)} articles")
        else:
            print(f"\n✅ Incremental crawl completed: {len(new_articles)} new articles")
            print(f"📄 Total articles in database: {len(final_articles)}")
            
        print(f"📄 Results saved to:")
        print(f"   - articles.json")
        print(f"   - articles.csv")
        
        # Show latest articles
        if new_articles:
            print(f"\n🔍 Latest new articles:")
            for i, article in enumerate(new_articles[:3], 1):
                print(f"{i}. {article['title'][:60]}...")
                print(f"   Date: {article['date']}")
                print(f"   URL: {article['url']}")
                print()
        
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
