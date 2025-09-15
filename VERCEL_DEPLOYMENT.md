# Vercel Deployment Guide for BJX QN Crawler

This guide will help you deploy the BJX QN crawler to Vercel as a serverless function.

## Why Vercel?

- **Different IP ranges** - Vercel's servers might not be blocked by the target website
- **Serverless functions** - No need to manage servers
- **Cron jobs** - Built-in scheduling for automatic crawling
- **Easy deployment** - Simple git-based deployment
- **Web interface** - Built-in UI to test and monitor crawls

## Prerequisites

1. **Vercel account** - Sign up at [vercel.com](https://vercel.com)
2. **GitHub repository** - Your code should be in a GitHub repo
3. **Python 3.11+** - Vercel supports Python 3.11

## Deployment Steps

### 1. Connect Repository to Vercel

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Vercel will auto-detect it's a Python project

### 2. Configure Vercel Settings

The `vercel.json` file is already configured with:
- **Function timeout**: 5 minutes (300 seconds)
- **Cron schedule**: Runs twice daily at 9:00 AM and 9:00 PM UTC
- **CORS headers**: Enabled for web access

### 3. Deploy

1. Click "Deploy" in Vercel dashboard
2. Wait for deployment to complete
3. You'll get a URL like `https://your-project.vercel.app`

## Usage

### Web Interface

Visit your Vercel URL to access the web interface:
- **Manual crawling**: Use the form to trigger crawls
- **Real-time results**: See articles and statistics
- **Error handling**: View detailed error messages

### API Endpoints

#### Manual Crawl
```
GET /api/crawl?max_pages=3&force_full_crawl=false
```

#### Parameters:
- `max_pages` (optional): Number of pages to crawl (default: 3)
- `force_full_crawl` (optional): Force full crawl (default: false)

#### Response:
```json
{
  "success": true,
  "message": "Successfully crawled 128 articles",
  "articlesCount": 128,
  "articles": [...], // First 10 articles
  "csvData": "...", // Full CSV data
  "output": "...", // Crawler logs
  "timestamp": "2025-09-15T13:30:00.000Z"
}
```

### Scheduled Crawling

The crawler runs automatically twice daily:
- **9:00 AM UTC** - Morning crawl
- **9:00 PM UTC** - Evening crawl

## Monitoring

### Vercel Dashboard
- View function logs
- Monitor execution times
- Check error rates

### Web Interface
- Real-time crawl results
- Article previews
- Success/failure status

## Troubleshooting

### Common Issues

1. **Function timeout**:
   - Reduce `max_pages` parameter
   - Check Vercel function logs

2. **Import errors**:
   - Ensure `requirements.txt` is in root directory
   - Check Python version compatibility

3. **Network issues**:
   - Vercel uses different IP ranges than GitHub Actions
   - May have better connectivity to target website

### Debugging

1. **Check function logs** in Vercel dashboard
2. **Use web interface** to test manually
3. **Check response** for detailed error messages

## Configuration

### Environment Variables

You can set these in Vercel dashboard:
- `MAX_PAGES`: Default pages to crawl
- `FORCE_FULL_CRAWL`: Default crawl mode

### Cron Schedule

Modify `vercel.json` to change schedule:
```json
{
  "crons": [
    {
      "path": "/api/crawl",
      "schedule": "0 9,21 * * *"  // 9 AM and 9 PM UTC daily
    }
  ]
}
```

## Benefits Over GitHub Actions

1. **Better connectivity** - Different IP ranges
2. **Web interface** - Easy testing and monitoring
3. **No runner limits** - Vercel handles scaling
4. **Built-in cron** - No complex workflow setup
5. **Real-time results** - Immediate feedback

## Next Steps

1. **Deploy to Vercel** using the steps above
2. **Test the web interface** with a small crawl
3. **Monitor the cron jobs** for automatic runs
4. **Set up notifications** if needed (can be added to the function)

The Vercel solution should work much better than GitHub Actions for this use case! 🚀
