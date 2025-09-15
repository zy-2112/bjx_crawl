#!/bin/bash

# Test CI workflow locally
# This script simulates what GitHub Actions will do

echo "🧪 Testing CI workflow locally..."
echo ""

# Set environment variables like GitHub Actions
export MAX_PAGES=2
export OUTPUT_JSON="test_articles.json"
export OUTPUT_CSV="test_articles.csv"

echo "📋 Configuration:"
echo "  MAX_PAGES: $MAX_PAGES"
echo "  OUTPUT_JSON: $OUTPUT_JSON"
echo "  OUTPUT_CSV: $OUTPUT_CSV"
echo ""

# Run the CI crawler
echo "🚀 Running crawler..."
uv run crawl_bjx_qn_ci.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Crawler succeeded!"
    
    # Show file sizes
    if [ -f "$OUTPUT_JSON" ]; then
        echo "📄 $OUTPUT_JSON: $(wc -l < "$OUTPUT_JSON") lines"
    fi
    
    if [ -f "$OUTPUT_CSV" ]; then
        echo "📄 $OUTPUT_CSV: $(wc -l < "$OUTPUT_CSV") lines"
    fi
    
    # Test creating status file (like GitHub Actions does)
    echo ""
    echo "📝 Creating status file..."
    
    TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
    echo "# Test Crawl Results" > TEST_STATUS.md
    echo "" >> TEST_STATUS.md
    echo "**Last Updated:** $(date -u)" >> TEST_STATUS.md
    
    # Check if jq is available for JSON processing
    if command -v jq &> /dev/null; then
        echo "**Articles Found:** $(jq length $OUTPUT_JSON)" >> TEST_STATUS.md
        echo "" >> TEST_STATUS.md
        echo "## Recent Articles" >> TEST_STATUS.md
        echo "" >> TEST_STATUS.md
        jq -r '.[:3] | .[] | "- [\(.title)](\(.url)) - \(.date)"' $OUTPUT_JSON >> TEST_STATUS.md
    else
        echo "**Articles Found:** $(grep -o '"title"' $OUTPUT_JSON | wc -l)" >> TEST_STATUS.md
        echo "" >> TEST_STATUS.md
        echo "## Status" >> TEST_STATUS.md
        echo "" >> TEST_STATUS.md
        echo "✅ Crawl completed successfully (jq not available for detailed parsing)" >> TEST_STATUS.md
    fi
    
    echo "📄 Created TEST_STATUS.md"
    echo ""
    echo "🎉 Local CI test completed successfully!"
    
else
    echo ""
    echo "❌ Crawler failed!"
    exit 1
fi
