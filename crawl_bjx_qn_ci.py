#!/usr/bin/env python3
"""
BJX QN Website Crawler - CI Version

This script is optimized for GitHub Actions with:
- Exit codes for CI/CD
- JSON output for easy parsing
- Configurable page limits via environment variables
- Better error reporting for automated runs
"""

import os
import sys
from crawl_bjx_qn import crawl_all_pages, save_to_json, save_to_csv, BASE_URL
import logging

# Configure logging for CI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function optimized for CI/CD environments."""
    try:
        # Get configuration from environment variables
        max_pages = int(os.getenv('MAX_PAGES', '3'))  # Default to 3 pages for CI
        output_json = os.getenv('OUTPUT_JSON', 'articles.json')
        output_csv = os.getenv('OUTPUT_CSV', 'articles.csv')
        
        logger.info(f"Starting BJX QN crawler in CI mode")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Output files: {output_json}, {output_csv}")
        
        # Crawl articles
        articles = crawl_all_pages(BASE_URL, max_pages=max_pages)
        
        if not articles:
            logger.error("No articles were extracted!")
            sys.exit(1)
        
        # Save results
        save_to_json(articles, output_json)
        save_to_csv(articles, output_csv)
        
        # Print summary for CI
        print(f"SUCCESS: Extracted {len(articles)} articles")
        print(f"Files: {output_json}, {output_csv}")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
