# BJX QN Website Crawler

A Python web crawler to extract article information from the BJX Hydrogen Energy website (https://qn.bjx.com.cn/zq).

## Features

- **Incremental Crawling**: Only fetches new articles since last run, preventing duplicates
- **State Management**: Tracks last crawl time for efficient updates
- **Complete Coverage**: Initial setup crawls all historical articles
- **Duplicate Prevention**: URL-based deduplication ensures no repeated articles
- Extracts article titles, publication dates, and URLs
- Supports pagination to crawl multiple pages
- Exports data in both JSON and CSV formats
- Robust error handling and retry logic
- Respectful crawling with delays between requests

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- lxml

## Installation

This project uses `uv` as the package manager:

```bash
# Clone or navigate to the project directory
cd bjx-crawler

# Install dependencies (uv will create a virtual environment automatically)
uv sync
```

## Usage

### First-time Setup (Run Once)
```bash
# Run the initial setup to crawl all existing articles
uv run setup_initial_crawl.py
```
This creates a baseline of all available articles and sets up state tracking for incremental updates.

### Regular Usage (Incremental Crawling)
```bash
# Run incremental crawling (only new articles)
uv run crawl_bjx_qn_incremental.py
```
Subsequent runs will only fetch articles newer than the last crawl time, preventing duplicates.

### Legacy Usage (Full Crawl Every Time)
```bash
# Run full crawl (not recommended for regular use)
uv run crawl_bjx_qn.py
```

## Output

The script generates two output files:

- `articles.json`: JSON format with all article data
- `articles.csv`: CSV format with columns: title, date, url

## Configuration

- By default, the crawler fetches the first 5 pages (configurable in the `main()` function)
- Request timeout: 10 seconds
- Retry attempts: 3
- Delay between pages: 1 second

## Example Output

```json
[
  {
    "title": "湖北交投集团氢能科技未来中心备案获得批复",
    "date": "2025-09-15",
    "url": "https://news.bjx.com.cn/html/20250915/1460982.shtml"
  }
]
```

## GitHub Actions Automation

The project includes GitHub Actions workflows for automated crawling:

### Daily Crawling Workflow (`.github/workflows/crawler.yml`)
- **Schedule**: Runs twice daily at 9:00 AM and 9:00 PM UTC
- **Triggers**: Scheduled, manual trigger, or push to main branch
- **Features**:
  - Automatically crawls articles and commits results
  - Creates timestamped data backups in `data/` directory
  - Maintains `latest_articles.json`, `latest_articles.csv`, and `CRAWL_STATUS.md`
  - Uploads artifacts for each run

### Vercel-Only Approach (Recommended)
- **Schedule**: Uses Vercel cron jobs (configured in `vercel.json`)
- **Features**:
  - Calls Vercel serverless function to bypass region blocks
  - Sends email notifications directly from Vercel
  - No need for GitHub Actions coordination
  - Simplified architecture with fewer moving parts

### Vercel-Backed Workflow (`.github/workflows/crawler-vercel.yml`)
- **Schedule**: Runs twice daily at 9:00 AM and 9:00 PM UTC
- **Features**:
  - Calls Vercel serverless function to bypass region blocks
  - Sends email notifications with CSV attachments
  - Maintains data backups and commit history
  - Handles both success and failure scenarios

### Weekly Analysis Workflow (`.github/workflows/analysis.yml`)
- **Schedule**: Runs weekly on Sundays at 10:00 AM UTC
- **Features**: Analyzes historical data and generates `WEEKLY_ANALYSIS.md`

### Email Notifications 📧
- **Service**: Resend API for reliable email delivery
- **Features**: 
  - 📎 CSV file attachment with complete data
  - 📊 Crawl summary with article count and previews
  - ✅ Success notifications after each crawl
  - ❌ Error notifications if crawling fails
  - 🎨 HTML and plain text email formats
- **Setup**: See [EMAIL_SETUP.md](EMAIL_SETUP.md) for configuration guide

### Setup Instructions

1. **Deploy to Vercel**: Deploy the crawler as a Vercel serverless function
2. **Configure Email Secrets**: Set up Resend API key and notification email as Vercel environment variables:
   - `RESEND_API_KEY` - Your Resend API key
   - `NOTIFICATION_EMAIL` - Your email address
3. **Fork/Clone** the repository to your GitHub account (optional for Vercel-only approach)
4. **Enable Actions**: Go to the "Actions" tab and enable GitHub Actions (only if using GitHub Actions workflows)
5. **Set Permissions**: Ensure the repository has write permissions for Actions (only if using GitHub Actions):
   - Go to Settings → Actions → General
   - Set "Workflow permissions" to "Read and write permissions"
6. **Manual Trigger**: You can manually trigger workflows from the Actions tab (only if using GitHub Actions)

### Vercel-Only Setup (Recommended)

For the simplest approach using only Vercel:

1. **Deploy to Vercel**:
   - Push your code to a Git repository
   - Connect to Vercel and deploy
   - The cron job is already configured in `vercel.json`

2. **Configure Environment Variables**:
   - In Vercel dashboard, go to your project settings
   - Add these environment variables:
     - `RESEND_API_KEY` = your Resend API key
     - `NOTIFICATION_EMAIL` = your email address

3. **That's it!**:
   - The Vercel function will run automatically twice daily
   - You'll receive email notifications with results
   - No GitHub Actions needed

### Customization

- **Schedule**: Modify the `cron` expressions in the workflow files
- **Page Limit**: Change the `MAX_PAGES` environment variable (default: 3 for CI)
- **Timezone**: Adjust cron schedules for your timezone (currently UTC)

### Output Structure

```
data/
├── 2025-09-15_09-00-00/
│   ├── articles.json
│   └── articles.csv
├── 2025-09-15_21-00-00/
│   ├── articles.json
│   └── articles.csv
latest_articles.json      # Latest crawl results
latest_articles.csv       # Latest crawl results
CRAWL_STATUS.md          # Summary of latest crawl
WEEKLY_ANALYSIS.md       # Weekly analysis report
```

## Legal and Ethical Considerations

- This tool is intended for educational and research purposes
- Please respect the website's robots.txt and terms of service
- The crawler includes delays to avoid overloading the server
- Use responsibly and in accordance with applicable laws
- GitHub Actions provide automated, respectful crawling with appropriate intervals
