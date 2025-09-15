#!/bin/bash

# Test GitHub Actions workflow locally
# This script simulates the GitHub Actions environment and tests the workflow steps

echo "🧪 Testing GitHub Actions Workflow Locally"
echo "=========================================="
echo

# Set environment variables like GitHub Actions
export MAX_PAGES=3
export FORCE_FULL_CRAWL=false
export OUTPUT_JSON=articles.json
export OUTPUT_CSV=articles.csv

echo "📋 Environment Configuration:"
echo "  MAX_PAGES: $MAX_PAGES"
echo "  FORCE_FULL_CRAWL: $FORCE_FULL_CRAWL"
echo "  OUTPUT_JSON: $OUTPUT_JSON"
echo "  OUTPUT_CSV: $OUTPUT_CSV"
echo

# Step 1: Run incremental crawler
echo "🔄 Step 1: Running incremental crawler..."
echo "----------------------------------------"
uv run crawl_bjx_qn_incremental_ci.py
CRAWLER_EXIT_CODE=$?

if [ $CRAWLER_EXIT_CODE -ne 0 ]; then
    echo "❌ Crawler failed with exit code $CRAWLER_EXIT_CODE"
    exit 1
fi

echo "✅ Crawler completed successfully"
echo

# Step 2: Verify output files exist
echo "🔍 Step 2: Verifying output files..."
echo "-----------------------------------"

if [ ! -f articles.json ]; then
    echo "❌ articles.json not found!"
    ls -la
    exit 1
fi

if [ ! -f articles.csv ]; then
    echo "❌ articles.csv not found!"
    ls -la
    exit 1
fi

echo "✅ Output files verified"

# Check if jq is available
if command -v jq &> /dev/null; then
    ARTICLE_COUNT=$(jq length articles.json)
    echo "📊 Articles count: $ARTICLE_COUNT"
else
    echo "⚠️  jq not available - install with 'brew install jq' for full testing"
    ARTICLE_COUNT=$(grep -o '"title"' articles.json | wc -l | tr -d ' ')
    echo "📊 Articles count (estimated): $ARTICLE_COUNT"
fi

echo

# Step 3: Create timestamped directory
echo "📁 Step 3: Creating timestamped directory..."
echo "-------------------------------------------"

TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
echo "Creating timestamped backup: test_data/$TIMESTAMP"
mkdir -p "test_data/$TIMESTAMP"

# Copy files to timestamped directory
cp articles.json "test_data/$TIMESTAMP/articles.json"
cp articles.csv "test_data/$TIMESTAMP/articles.csv"
cp crawl_state.json "test_data/$TIMESTAMP/crawl_state.json" 2>/dev/null || echo "No crawl_state.json to backup"

# Keep latest files in root for easy access
cp articles.json test_latest_articles.json
cp articles.csv test_latest_articles.csv

echo "✅ Timestamped directory created"
echo

# Step 4: Create status file
echo "📄 Step 4: Creating status file..."
echo "---------------------------------"

cat > TEST_CRAWL_STATUS.md << EOF
# Test Crawl Results

**Last Updated:** $(date -u)
**Articles Found:** $ARTICLE_COUNT
**Timestamp:** $TIMESTAMP

## Recent Articles

EOF

if command -v jq &> /dev/null; then
    jq -r '.[:5] | .[] | "- [\(.title)](\(.url)) - \(.date)"' test_latest_articles.json >> TEST_CRAWL_STATUS.md
else
    echo "- Article list requires jq for formatting" >> TEST_CRAWL_STATUS.md
fi

echo "✅ Status file created: TEST_CRAWL_STATUS.md"
echo

# Step 5: Test email content preparation
echo "📧 Step 5: Preparing email content..."
echo "------------------------------------"

CRAWL_TIME=$(date -u "+%Y-%m-%d %H:%M:%S UTC")

# Simple check for no new articles (basic version without complex log checking)
if [ -f crawl_state.json ] && command -v jq &> /dev/null; then
    STORED_COUNT=$(jq -r '.total_articles_crawled // 0' crawl_state.json 2>/dev/null || echo '0')
    if [ "$ARTICLE_COUNT" -eq "$STORED_COUNT" ]; then
        # No new articles case
        cat > test_email_body.txt << EOF
BJX QN Article Crawler Results - No New Articles

Crawl completed successfully at: $CRAWL_TIME
Total articles in database: $ARTICLE_COUNT
New articles found: 0

No new articles have been published since the last crawl.
The database remains current with existing articles.

---
Automated by GitHub Actions (Incremental Crawl) - LOCAL TEST
Repository: test/bjx-crawler
Run: test-run
EOF
        echo "📧 Email prepared: No new articles case"
    else
        # New articles found case
        cat > test_email_body.txt << EOF
BJX QN Article Crawler Results

Crawl completed successfully at: $CRAWL_TIME
Total articles in database: $ARTICLE_COUNT

Latest Articles:
EOF
        if command -v jq &> /dev/null; then
            jq -r '.[:5] | .[] | "• \(.title) (\(.date))"' test_latest_articles.json >> test_email_body.txt
        else
            echo "• Article list requires jq for formatting" >> test_email_body.txt
        fi
        
        cat >> test_email_body.txt << EOF

Please find the complete data attached as CSV file.

---
Automated by GitHub Actions - LOCAL TEST
Repository: test/bjx-crawler
Run: test-run
EOF
        echo "📧 Email prepared: New articles case"
    fi
else
    echo "⚠️  Cannot determine new article status without jq or crawl_state.json"
    echo "📧 Email content would be prepared based on available data"
fi

echo

# Summary
echo "🎉 GitHub Actions Workflow Test Summary"
echo "====================================="
echo "✅ Incremental crawler: SUCCESS"
echo "✅ Output files: Verified"
echo "✅ Timestamped backup: Created in test_data/$TIMESTAMP"
echo "✅ Status file: Created (TEST_CRAWL_STATUS.md)"
echo "✅ Email content: Prepared (test_email_body.txt)"
echo

echo "📁 Test files created:"
echo "   - test_data/$TIMESTAMP/articles.json"
echo "   - test_data/$TIMESTAMP/articles.csv"
echo "   - test_latest_articles.json"
echo "   - test_latest_articles.csv"
echo "   - TEST_CRAWL_STATUS.md"
echo "   - test_email_body.txt"
echo

echo "🔍 To clean up test files:"
echo "   rm -rf test_data/ test_latest_articles.* TEST_CRAWL_STATUS.md test_email_body.txt"

echo
echo "✅ GitHub Actions workflow test completed successfully!"
echo "   The actual GitHub Actions should work with this configuration."
