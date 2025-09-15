#!/usr/bin/env python3
"""
BJX QN Website Crawler - Incremental CI Version

Optimized for GitHub Actions with incremental crawling:
- Environment variable configuration
- Proper exit codes for CI
- State persistence across runs
- Efficient new article detection
"""

import os
import sys
from crawl_bjx_qn_incremental import (
    load_crawl_state, save_crawl_state, crawl_incremental, 
    load_existing_articles, merge_articles, save_to_json, save_to_csv,
    BASE_URL
)
from datetime import datetime, timezone, timedelta
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
        max_pages = int(os.getenv('MAX_PAGES', '10'))  # Default to fewer pages for CI
        output_json = os.getenv('OUTPUT_JSON', 'articles.json')
        output_csv = os.getenv('OUTPUT_CSV', 'articles.csv')
        force_full_crawl = os.getenv('FORCE_FULL_CRAWL', 'false').lower() == 'true'
        
        logger.info(f"Starting BJX QN incremental crawler in CI mode")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Output files: {output_json}, {output_csv}")
        logger.info(f"Force full crawl: {force_full_crawl}")
        
        # Load crawl state
        state = load_crawl_state()
        is_first_run = state.get('first_run', True) or force_full_crawl
        last_crawl_time = state.get('last_crawl_time')
        
        # Check if existing articles file exists - if not, treat as first run
        # This handles the case where articles.json is gitignored in GitHub Actions
        if not os.path.exists(output_json):
            logger.info("No existing articles file found, treating as first run")
            is_first_run = True
        
        # Determine cutoff time for incremental crawling
        cutoff_time = None
        if not is_first_run and last_crawl_time and not force_full_crawl:
            # Parse last crawl time and subtract buffer to avoid missing articles
            cutoff_time = datetime.fromisoformat(last_crawl_time.replace('Z', '+00:00')) - timedelta(hours=1)
            logger.info(f"Incremental crawl: looking for articles newer than {cutoff_time.isoformat()}")
        else:
            logger.info("Full crawl mode: crawling all available articles")
            max_pages = min(max_pages * 2, 20)  # Allow more pages for full crawl
        
        # Crawl new articles
        new_articles = crawl_incremental(BASE_URL, cutoff_time, max_pages)
        
        if is_first_run or force_full_crawl:
            # On first run or forced full crawl, save all articles directly
            final_articles = new_articles
            logger.info(f"Full crawl complete: found {len(final_articles)} articles")
        else:
            # On subsequent runs, merge with existing articles
            existing_articles = load_existing_articles()
            final_articles = merge_articles(existing_articles, new_articles)
            logger.info(f"Incremental crawl complete: {len(new_articles)} new articles added")
        
        # Handle no articles scenario
        if not final_articles:
            if is_first_run or force_full_crawl:
                logger.error("No articles were found during full crawl!")
                sys.exit(1)
            else:
                logger.info("No new articles found since last crawl")
                # Load existing articles to ensure we have something to output
                existing_articles = load_existing_articles()
                if existing_articles:
                    final_articles = existing_articles
                    logger.info(f"Using existing articles: {len(final_articles)} articles")
                else:
                    logger.warning("No existing articles found and no new articles - creating empty files")
                    final_articles = []
                
                # Update state even if no new articles
                state.update({
                    'last_crawl_time': datetime.now(timezone.utc).isoformat(),
                    'first_run': False
                })
                save_crawl_state(state)
                
                # Always create output files, even if empty
                save_to_json(final_articles, output_json)
                save_to_csv(final_articles, output_csv)
                
                # For CI, we still want to output success but indicate no new content
                print("SUCCESS: No new articles found")
                print(f"Files: {output_json}, {output_csv} (existing/empty)")
                print(f"Last crawl: {last_crawl_time}")
                sys.exit(0)
        
        # Save results
        save_to_json(final_articles, output_json)
        save_to_csv(final_articles, output_csv)
        
        # Update crawl state
        state.update({
            'last_crawl_time': datetime.now(timezone.utc).isoformat(),
            'total_articles_crawled': len(final_articles),
            'first_run': False
        })
        save_crawl_state(state)
        
        # Print summary for CI
        if is_first_run or force_full_crawl:
            print(f"SUCCESS: Full crawl completed - {len(final_articles)} articles")
        else:
            print(f"SUCCESS: Incremental crawl completed - {len(new_articles)} new articles")
            print(f"Total articles: {len(final_articles)}")
            
        print(f"Files: {output_json}, {output_csv}")
        
        # Output new articles count for GitHub Actions to use
        if new_articles:
            print(f"NEW_ARTICLES_COUNT={len(new_articles)}")
            print(f"LATEST_ARTICLE_DATE={new_articles[0]['date'] if new_articles else 'N/A'}")
        
        # Exit with success
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
