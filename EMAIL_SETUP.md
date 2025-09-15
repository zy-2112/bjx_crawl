# Email Notifications Setup Guide

This guide will help you set up automated email notifications for the BJX crawler using the Resend service.

## Prerequisites

1. **Resend Account**: Sign up at [resend.com](https://resend.com)
2. **GitHub Repository**: Your crawler code needs to be in a GitHub repository
3. **GitHub Actions enabled** in your repository

## Step 1: Get Resend API Key

1. **Sign up/Login** to [Resend](https://resend.com)
2. **Navigate to API Keys** in your dashboard
3. **Create a new API key** with a descriptive name like "BJX Crawler"
4. **Copy the API key** (it starts with `re_...`)

## Step 2: Configure GitHub Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these two secrets:

### Required Secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `RESEND_API_KEY` | Your Resend API key | `re_123abc...` |
| `NOTIFICATION_EMAIL` | Your email address | `your-email@example.com` |

### How to add secrets:
```
Name: RESEND_API_KEY
Secret: re_your_actual_api_key_here

Name: NOTIFICATION_EMAIL  
Secret: your-email@example.com
```

## Step 3: Choose Your Workflow

You have two email workflow options:

### Option 1: Basic Email (Recommended)
- File: `.github/workflows/crawler.yml`
- Features: Plain text emails with CSV attachment
- Simple and reliable

### Option 2: Enhanced HTML Email  
- File: `.github/workflows/crawler-with-html-email.yml`
- Features: Beautiful HTML emails with styled previews
- More visual appeal

**To switch between workflows:**
1. Rename the workflow file you DON'T want to use (add `.disabled` extension)
2. Keep only one active workflow file

## Step 4: Test the Setup

### Manual Test:
1. Go to your repository's **Actions** tab
2. Select the crawler workflow
3. Click **Run workflow** → **Run workflow**
4. Check your email for the notification

### Test Email Content:

**Success Email includes:**
- ✅ Crawl completion summary
- 📊 Number of articles found
- 🔍 Preview of latest articles  
- 📎 Complete CSV file attached
- 🔗 Link to GitHub Actions run

**Failure Email includes:**
- ❌ Error notification
- 🔗 Link to troubleshooting logs
- 📧 Run details for debugging

## Step 5: Customize Email Settings

### Email Frequency
The crawler runs **twice daily** by default:
- 9:00 AM UTC (5:00 PM Beijing time)
- 9:00 PM UTC (5:00 AM Beijing time next day)

### Customize Schedule
Edit the `cron` expressions in the workflow file:
```yaml
schedule:
  - cron: '0 9 * * *'   # 9:00 AM UTC daily
  - cron: '0 21 * * *'  # 9:00 PM UTC daily
```

### Email Subject Customization
Modify the `subject` field in the workflow:
```yaml
subject: "📰 BJX Articles Update - $(date -u +%Y-%m-%d %H:%M) UTC - $(jq length latest_articles.json) articles"
```

## Step 6: Email Content Examples

### Success Email Preview:
```
Subject: 📰 BJX Articles Update - 2025-09-15 09:00 UTC - 64 articles

BJX QN Article Crawler Results

Crawl completed successfully at: 2025-09-15 09:00:15 UTC
Total articles extracted: 64

Latest Articles:
• 湖北交投集团氢能科技未来中心备案获得批复 (2025-09-15)
• 法国液化空气集团在华绿色甲醇项目获备案 (2025-09-15)
• 强强联合！绿氢装备零碳产业园项目签约 (2025-09-15)

📎 Complete data is attached as CSV file.

---
🤖 Automated by GitHub Actions
```

### HTML Email Features:
- 🎨 Professional styling with CSS
- 📊 Highlighted statistics section
- 🔗 Clickable article links  
- 📱 Mobile-friendly layout

## Step 7: Troubleshooting

### Common Issues:

1. **No emails received**
   - ✅ Check spam/junk folder
   - ✅ Verify `NOTIFICATION_EMAIL` secret
   - ✅ Confirm `RESEND_API_KEY` is correct

2. **Email delivery fails**  
   - ✅ Check GitHub Actions logs
   - ✅ Verify Resend API key hasn't expired
   - ✅ Ensure email address is valid

3. **Attachment missing**
   - ✅ Check if CSV file was generated successfully
   - ✅ Verify file size isn't too large (Resend limits apply)

### Monitoring
- **GitHub Actions logs**: Check workflow execution details
- **Resend dashboard**: Monitor email delivery status
- **Repository artifacts**: Download backup copies of data

## Security Notes

- 🔒 API keys are stored securely as GitHub secrets
- 🔒 Never commit API keys to your repository
- 🔒 Use repository secrets, not environment variables in code
- 🔒 Regularly rotate API keys for security

## Cost Considerations

**Resend Free Tier:**
- 100 emails/day
- 3,000 emails/month
- Sufficient for twice-daily notifications

**Your usage:**
- 2 emails/day (success notifications)  
- ~60 emails/month
- Well within free limits

## Support

- **Resend docs**: [resend.com/docs](https://resend.com/docs)  
- **GitHub Actions docs**: [docs.github.com/actions](https://docs.github.com/actions)
- **Issues**: Create GitHub issues for crawler-specific problems
