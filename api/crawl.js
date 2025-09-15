const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  try {
    console.log('🚀 Starting BJX QN crawler on Vercel...');
    
    // Get parameters from query string
    const maxPages = req.query.max_pages || '3';
    const forceFullCrawl = req.query.force_full_crawl || 'false';
    
    console.log(`Max pages: ${maxPages}, Force full crawl: ${forceFullCrawl}`);
    
    // Set environment variables
    const env = {
      ...process.env,
      MAX_PAGES: maxPages,
      FORCE_FULL_CRAWL: forceFullCrawl,
      OUTPUT_JSON: 'articles.json',
      OUTPUT_CSV: 'articles.csv'
    };
    
    // Run the Python crawler
    const pythonProcess = spawn('python3', ['crawl_bjx_qn_incremental_ci.py'], {
      env,
      cwd: process.cwd()
    });
    
    let output = '';
    let errorOutput = '';
    
    pythonProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      console.log(text);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      const text = data.toString();
      errorOutput += text;
      console.error(text);
    });
    
    // Wait for the process to complete
    const exitCode = await new Promise((resolve) => {
      pythonProcess.on('close', (code) => {
        resolve(code);
      });
    });
    
    if (exitCode !== 0) {
      console.error('❌ Crawler failed with exit code:', exitCode);
      return res.status(500).json({
        success: false,
        error: 'Crawler failed',
        output: output,
        errorOutput: errorOutput,
        exitCode: exitCode
      });
    }
    
    // Check if output files exist
    const articlesJsonPath = path.join(process.cwd(), 'articles.json');
    const articlesCsvPath = path.join(process.cwd(), 'articles.csv');
    
    if (!fs.existsSync(articlesJsonPath)) {
      console.error('❌ articles.json not found');
      return res.status(500).json({
        success: false,
        error: 'Output files not created',
        output: output
      });
    }
    
    // Read the results
    const articlesJson = JSON.parse(fs.readFileSync(articlesJsonPath, 'utf8'));
    const articlesCsv = fs.readFileSync(articlesCsvPath, 'utf8');
    
    console.log(`✅ Crawler completed successfully - ${articlesJson.length} articles found`);
    
    // Return the results
    res.status(200).json({
      success: true,
      message: `Successfully crawled ${articlesJson.length} articles`,
      articlesCount: articlesJson.length,
      articles: articlesJson.slice(0, 10), // Return first 10 articles as preview
      csvData: articlesCsv,
      output: output,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('❌ Vercel function error:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      stack: error.stack
    });
  }
}
