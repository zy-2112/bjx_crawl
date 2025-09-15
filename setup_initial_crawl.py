#!/usr/bin/env python3
"""
Initial Setup Script for BJX QN Crawler

This script performs the first full crawl to establish the baseline.
Run this manually before setting up GitHub Actions.
"""

import os
import sys
from crawl_bjx_qn_incremental import main as incremental_main
import json

def setup_initial_crawl():
    """Setup the initial crawl and provide guidance."""
    
    print("🚀 BJX QN Crawler Initial Setup")
    print("=" * 50)
    print()
    
    # Check if this is already set up
    if os.path.exists('crawl_state.json'):
        try:
            with open('crawl_state.json', 'r') as f:
                state = json.load(f)
            
            if not state.get('first_run', True):
                print("⚠️  Crawler is already initialized!")
                print(f"   Last crawl: {state.get('last_crawl_time', 'Unknown')}")
                print(f"   Total articles: {state.get('total_articles_crawled', 0)}")
                print()
                
                response = input("Do you want to run a fresh full crawl anyway? (y/N): ")
                if response.lower() != 'y':
                    print("🔄 Use the incremental crawler for regular updates:")
                    print("   python crawl_bjx_qn_incremental.py")
                    return
                else:
                    # Reset state for fresh crawl
                    os.remove('crawl_state.json')
                    print("🗑️  Removed existing state, starting fresh...")
                    print()
        except Exception as e:
            print(f"⚠️  Error reading state file: {e}")
            print("🔄 Proceeding with setup...")
            print()
    
    print("📋 This initial setup will:")
    print("   1. Crawl ALL available articles from the website")
    print("   2. Create baseline data files (articles.json, articles.csv)")
    print("   3. Set up state tracking for incremental updates")
    print("   4. May take several minutes depending on content volume")
    print()
    
    response = input("Continue with initial full crawl? (Y/n): ")
    if response.lower() == 'n':
        print("❌ Setup cancelled")
        return
    
    print()
    print("🔍 Starting initial full crawl...")
    print("=" * 50)
    
    try:
        # Run the incremental main function (it will do a full crawl on first run)
        incremental_main()
        
        print("=" * 50)
        print("✅ Initial setup completed successfully!")
        print()
        print("📄 Files created:")
        
        if os.path.exists('articles.json'):
            with open('articles.json', 'r') as f:
                data = json.load(f)
            print(f"   📄 articles.json ({len(data)} articles)")
        
        if os.path.exists('articles.csv'):
            print("   📄 articles.csv (CSV format)")
            
        if os.path.exists('crawl_state.json'):
            print("   📄 crawl_state.json (state tracking)")
        
        print()
        print("🔄 Future runs will be incremental:")
        print("   - Only new articles since last crawl will be fetched")
        print("   - Much faster execution time")
        print("   - Automatic duplicate prevention")
        print()
        print("📚 Next steps:")
        print("   1. Set up GitHub Actions with your repository")
        print("   2. Configure email notifications (see EMAIL_SETUP.md)")
        print("   3. GitHub Actions will handle automated incremental updates")
        print()
        print("🧪 Test incremental crawling:")
        print("   python crawl_bjx_qn_incremental.py")
        
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   - Check your internet connection")
        print("   - Verify the website is accessible")
        print("   - Try running again in a few minutes")
        sys.exit(1)

if __name__ == '__main__':
    setup_initial_crawl()
