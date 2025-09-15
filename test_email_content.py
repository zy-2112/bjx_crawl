#!/usr/bin/env python3
"""
Test script to generate email content locally for validation.
This helps test email formatting before deploying to GitHub Actions.
"""

import json
import os
from datetime import datetime

def generate_test_email_content():
    """Generate sample email content using existing data."""
    
    # Use existing articles data if available
    json_file = "latest_articles.json"
    if not os.path.exists(json_file):
        json_file = "articles.json"
        
    if not os.path.exists(json_file):
        print("❌ No articles data found. Please run the crawler first.")
        return
        
    with open(json_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    article_count = len(articles)
    crawl_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    
    # Generate HTML email content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ background-color: #e9f7ef; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .articles {{ margin: 20px 0; }}
        .article-item {{ margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; }}
        .footer {{ font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px; margin-top: 30px; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🔋 BJX QN Article Crawler Results</h2>
        <p><strong>Crawl Time:</strong> {crawl_time}</p>
        <p><strong>Repository:</strong> your-repo/bjx-crawler</p>
    </div>
    
    <div class="stats">
        <h3>📊 Crawl Summary</h3>
        <ul>
            <li><strong>Total Articles:</strong> {article_count}</li>
            <li><strong>Run Number:</strong> #123</li>
            <li><strong>Status:</strong> ✅ Success</li>
        </ul>
    </div>
    
    <div class="articles">
        <h3>🔍 Latest Articles Preview</h3>"""
    
    # Add article previews
    for article in articles[:8]:
        html_content += f"""
        <div class="article-item">
            <strong><a href="{article['url']}">{article['title']}</a></strong><br>
            <small>📅 {article['date']}</small>
        </div>"""
    
    html_content += f"""
    </div>
    
    <div class="footer">
        <p>📎 Complete data is attached as CSV file: <code>bjx_articles_{timestamp}.csv</code></p>
        <p>🤖 Generated automatically by GitHub Actions</p>
        <p>🔗 <a href="https://github.com/your-repo/bjx-crawler/actions">View workflow run</a></p>
    </div>
</body>
</html>"""
    
    # Generate plain text content
    text_content = f"""BJX QN Article Crawler Results

Crawl completed successfully at: {crawl_time}
Total articles extracted: {article_count}
Repository: your-repo/bjx-crawler
Run: #123

Latest Articles:"""
    
    for article in articles[:8]:
        text_content += f"\n• {article['title']} ({article['date']})\n  {article['url']}"
    
    text_content += f"""

📎 Complete data is attached as CSV file.

---
🤖 Automated by GitHub Actions
🔗 View run: https://github.com/your-repo/bjx-crawler/actions/runs/123
"""
    
    # Save test files
    with open('test_email_body.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open('test_email_body.txt', 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    print("✅ Test email content generated:")
    print("📄 test_email_body.html - HTML version")
    print("📄 test_email_body.txt - Plain text version")
    print()
    print("📧 Email subject would be:")
    print(f"   📰 BJX Articles Update - {crawl_time.split()[0]} {crawl_time.split()[1]} UTC - {article_count} articles")
    print()
    print("🔍 Preview of email content:")
    print("=" * 50)
    print(text_content[:500] + "..." if len(text_content) > 500 else text_content)
    print("=" * 50)
    
    # Generate test CSV with timestamp
    csv_filename = f"bjx_articles_{timestamp}.csv"
    if os.path.exists("latest_articles.csv"):
        import shutil
        shutil.copy("latest_articles.csv", csv_filename)
        print(f"📎 Test attachment: {csv_filename}")
    elif os.path.exists("articles.csv"):
        import shutil
        shutil.copy("articles.csv", csv_filename)
        print(f"📎 Test attachment: {csv_filename}")

if __name__ == '__main__':
    generate_test_email_content()
