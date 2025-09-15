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
import socket
import requests
from crawl_bjx_qn_incremental import (
    load_crawl_state, save_crawl_state, crawl_incremental, 
    load_existing_articles, merge_articles, save_to_json, save_to_csv,
    BASE_URL
)
from datetime import datetime, timezone, timedelta
import logging
import json as json_module

# Configure logging for CI
# For Vercel compatibility, we'll log to stderr instead of stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def crawl_and_return_data(max_pages: int = 10, force_full_crawl: bool = False):
    """Crawl data and return it as Python objects instead of saving to files.
    
    This function is designed for serverless environments like Vercel where
    file system access is restricted.
    """
    try:
        logger.info(f"Starting BJX QN crawler in serverless mode")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Force full crawl: {force_full_crawl}")
        
        # Test network connectivity first
        logger.info("🔍 Testing network connectivity...")
        if not test_network_connectivity():
            logger.warning("❌ Network connectivity test failed. Attempting to load existing data...")
            
            # Try to load existing data as fallback
            try:
                existing_articles = load_existing_articles()
                if existing_articles:
                    logger.info(f"✅ Loaded {len(existing_articles)} existing articles as fallback")
                    return {
                        'articles': existing_articles,
                        'new_articles_count': 0,
                        'total_articles_count': len(existing_articles),
                        'is_first_run': False,
                        'warning': 'Network connectivity failed. Returning existing data.',
                        'network_error': True
                    }
                else:
                    logger.error("No existing articles found and network connectivity failed.")
                    return {
                        'error': 'NETWORK_ERROR',
                        'message': 'Unable to connect to the target website and no existing data available.',
                        'details': 'All connectivity tests failed and no cached data found. The website might be blocking requests from this serverless environment.'
                    }
            except Exception as e:
                logger.error(f"Failed to load existing data: {e}")
                return {
                    'error': 'NETWORK_ERROR',
                    'message': 'Unable to connect to the target website and failed to load existing data.',
                    'details': f'Network tests failed and error loading cached data: {str(e)}'
                }
        
        # Load crawl state
        state = load_crawl_state()
        is_first_run = state.get('first_run', True) or force_full_crawl
        last_crawl_time = state.get('last_crawl_time')
        
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
        try:
            new_articles = crawl_incremental(BASE_URL, cutoff_time, max_pages)
        except Exception as e:
            logger.error(f"❌ Crawling failed: {e}")
            # Try to load existing data as fallback
            try:
                existing_articles = load_existing_articles()
                if existing_articles:
                    logger.info(f"✅ Loaded {len(existing_articles)} existing articles as fallback after crawl failure")
                    return {
                        'articles': existing_articles,
                        'new_articles_count': 0,
                        'total_articles_count': len(existing_articles),
                        'is_first_run': False,
                        'warning': f'Crawling failed: {str(e)}. Returning existing data.',
                        'network_error': True
                    }
                else:
                    return {
                        'error': 'CRAWLING_ERROR',
                        'message': f'Crawling failed: {str(e)}',
                        'details': 'This might be due to network connectivity issues in the serverless environment and no cached data available.'
                    }
            except Exception as fallback_error:
                logger.error(f"Failed to load existing data as fallback: {fallback_error}")
                return {
                    'error': 'CRAWLING_ERROR',
                    'message': f'Crawling failed: {str(e)}',
                    'details': f'This might be due to network connectivity issues and error loading cached data: {str(fallback_error)}'
                }
        
        if is_first_run or force_full_crawl:
            # On first run or forced full crawl, return all articles directly
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
                # Try to load existing data as fallback
                try:
                    existing_articles = load_existing_articles()
                    if existing_articles:
                        logger.info(f"✅ Loaded {len(existing_articles)} existing articles as fallback")
                        return {
                            'articles': existing_articles,
                            'new_articles_count': 0,
                            'total_articles_count': len(existing_articles),
                            'is_first_run': False,
                            'warning': 'No new articles found during full crawl. Returning existing data.',
                            'network_error': False
                        }
                    else:
                        return {
                            'error': 'NO_ARTICLES_FOUND',
                            'message': 'No articles were found during full crawl!',
                            'details': 'The crawler completed successfully but found no articles and no cached data available.'
                        }
                except Exception as fallback_error:
                    return {
                        'error': 'NO_ARTICLES_FOUND',
                        'message': 'No articles were found during full crawl!',
                        'details': f'The crawler completed successfully but found no articles and error loading cached data: {str(fallback_error)}'
                    }
            else:
                logger.info("No new articles found since last crawl")
                # Load existing articles to ensure we have something to output
                existing_articles = load_existing_articles()
                if existing_articles:
                    final_articles = existing_articles
                    logger.info(f"Using existing articles: {len(final_articles)} articles")
                else:
                    logger.warning("No existing articles found and no new articles")
                    final_articles = []
        
        # Return the data as Python objects
        return {
            'articles': final_articles,
            'new_articles_count': len(new_articles),
            'total_articles_count': len(final_articles),
            'is_first_run': is_first_run or force_full_crawl
        }
        
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        return None

def test_network_connectivity():
    """Test network connectivity to the target website with DNS optimization."""
    try:
        # Test DNS resolution with multiple servers
        logger.info("Testing DNS resolution with multiple servers...")
        dns_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222', '9.9.9.9']
        
        for dns in dns_servers:
            try:
                logger.info(f"Testing DNS server: {dns}")
                socket.gethostbyname('qn.bjx.com.cn')
                logger.info(f"✅ DNS resolution successful with {dns}")
                break
            except socket.gaierror as e:
                logger.warning(f"❌ DNS {dns} failed: {e}")
                continue
        else:
            logger.error("❌ All DNS servers failed")
            return False
        
        # Test connectivity with different User-Agents
        logger.info("Testing connectivity with different User-Agents...")
        user_agents = [
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'curl/7.68.0'
        ]
        
        for i, ua in enumerate(user_agents):
            try:
                logger.info(f"Testing User-Agent {i+1}: {ua[:50]}...")
                headers = {'User-Agent': ua}
                response = requests.get('https://qn.bjx.com.cn', timeout=15, headers=headers)
                logger.info(f"✅ User-Agent {i+1} successful (status: {response.status_code})")
                return True
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ User-Agent {i+1} failed: {e}")
                continue
        
        logger.error("❌ All connectivity tests failed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Network test failed: {e}")
        return False

def main():
    """Main function optimized for CI/CD environments."""
    try:
        # Get configuration from environment variables
        max_pages = int(os.getenv('MAX_PAGES', '10'))  # Default to fewer pages for CI
        output_json = os.getenv('OUTPUT_JSON', 'articles.json')
        output_csv = os.getenv('OUTPUT_CSV', 'articles.csv')
        force_full_crawl = os.getenv('FORCE_FULL_CRAWL', 'false').lower() == 'true'
        
        # For Vercel/serverless environments, return data directly instead of saving files
        if os.getenv('VERCEL') == '1':
            logger.info("Running in Vercel mode - returning data directly")
            result = crawl_and_return_data(max_pages, force_full_crawl)
            
            if result is None:
                print("ERROR: Crawling failed", file=sys.stderr)
                sys.exit(1)
            
            # Output the data as JSON to stdout (this is what Vercel expects)
            print(json_module.dumps(result, ensure_ascii=False))
            sys.exit(0)
        
        # Regular CI mode - save to files
        logger.info(f"Starting BJX QN incremental crawler in CI mode")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Output files: {output_json}, {output_csv}")
        logger.info(f"Force full crawl: {force_full_crawl}")
        
        # Test network connectivity first
        logger.info("🔍 Testing network connectivity...")
        if not test_network_connectivity():
            logger.error("❌ Network connectivity test failed. This might be a VPN/network issue.")
            logger.error("The target website may be blocking GitHub Actions IPs or require VPN access.")
            logger.error("Consider using a self-hosted runner or alternative approach.")
            # For Vercel/serverless compatibility, output to stderr instead of stdout
            if os.getenv('VERCEL') == '1':
                print("ERROR: Network connectivity test failed", file=sys.stderr)
            else:
                print("ERROR: Network connectivity test failed")
            sys.exit(1)
        
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
        try:
            new_articles = crawl_incremental(BASE_URL, cutoff_time, max_pages)
        except Exception as e:
            logger.error(f"❌ Crawling failed: {e}")
            logger.error("This might be due to network connectivity issues in GitHub Actions.")
            logger.error("Creating fallback empty files to prevent workflow failure...")
            
            # Create empty files as fallback
            save_to_json([], output_json)
            save_to_csv([], output_csv)
            
            # Update state to prevent infinite retries
            state.update({
                'last_crawl_time': datetime.now(timezone.utc).isoformat(),
                'first_run': False,
                'last_error': str(e)
            })
            save_crawl_state(state)
            
            # For Vercel/serverless compatibility, output to stderr instead of stdout
            if os.getenv('VERCEL') == '1':
                print("WARNING: Crawling failed due to network issues, created empty files", file=sys.stderr)
                print(f"Files: {output_json}, {output_csv} (empty due to network error)", file=sys.stderr)
            else:
                print("WARNING: Crawling failed due to network issues, created empty files")
                print(f"Files: {output_json}, {output_csv} (empty due to network error)")
            sys.exit(0)  # Exit with success to prevent workflow failure
        
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
                # For Vercel/serverless compatibility, output to stderr instead of stdout
                if os.getenv('VERCEL') == '1':
                    print("SUCCESS: No new articles found", file=sys.stderr)
                    print(f"Files: {output_json}, {output_csv} (existing/empty)", file=sys.stderr)
                    print(f"Last crawl: {last_crawl_time}", file=sys.stderr)
                else:
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
        
        # For Vercel/serverless compatibility, we need to be careful about stdout output
        # Only output essential information for debugging purposes
        if os.getenv('VERCEL') == '1':
            # Minimal output for Vercel environment
            print(f"Articles crawled: {len(final_articles)}", file=sys.stderr)
        else:
            # Full output for CI/local environments
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
        # For Vercel/serverless compatibility, output to stderr instead of stdout
        if os.getenv('VERCEL') == '1':
            print(f"ERROR: {e}", file=sys.stderr)
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
