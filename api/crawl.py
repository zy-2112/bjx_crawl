from http.server import BaseHTTPRequestHandler
import json
import subprocess
import os
import sys
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()
    
    def do_POST(self):
        self.handle_request()
    
    def handle_request(self):
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            print('🚀 Starting BJX QN crawler on Vercel...')
            
            # Get parameters from query string
            import urllib.parse
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            max_pages = query_params.get('max_pages', ['3'])[0]
            force_full_crawl = query_params.get('force_full_crawl', ['false'])[0]
            
            print(f'Max pages: {max_pages}, Force full crawl: {force_full_crawl}')
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'MAX_PAGES': max_pages,
                'FORCE_FULL_CRAWL': force_full_crawl,
                'OUTPUT_JSON': 'articles.json',
                'OUTPUT_CSV': 'articles.csv'
            })
            
            # Run the crawler
            try:
                result = subprocess.run(
                    [sys.executable, 'crawl_bjx_qn_incremental_ci.py'],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                print(f'Crawler exit code: {result.returncode}')
                print(f'Crawler output: {result.stdout}')
                if result.stderr:
                    print(f'Crawler errors: {result.stderr}')
                
                if result.returncode != 0:
                    response = {
                        'success': False,
                        'error': 'Crawler failed',
                        'output': result.stdout,
                        'errorOutput': result.stderr,
                        'exitCode': result.returncode
                    }
                else:
                    # Check if output files exist
                    if not os.path.exists('articles.json'):
                        response = {
                            'success': False,
                            'error': 'Output files not created',
                            'output': result.stdout
                        }
                    else:
                        # Read the results
                        with open('articles.json', 'r', encoding='utf-8') as f:
                            articles = json.load(f)
                        
                        with open('articles.csv', 'r', encoding='utf-8') as f:
                            csv_data = f.read()
                        
                        print(f'✅ Crawler completed successfully - {len(articles)} articles found')
                        
                        response = {
                            'success': True,
                            'message': f'Successfully crawled {len(articles)} articles',
                            'articlesCount': len(articles),
                            'articles': articles[:10],  # Return first 10 articles as preview
                            'csvData': csv_data,
                            'output': result.stdout,
                            'timestamp': datetime.now().isoformat()
                        }
                
            except subprocess.TimeoutExpired:
                response = {
                    'success': False,
                    'error': 'Crawler timed out after 5 minutes',
                    'output': 'Process was terminated due to timeout'
                }
            except Exception as e:
                response = {
                    'success': False,
                    'error': f'Failed to run crawler: {str(e)}',
                    'output': ''
                }
            
            # Send response
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            print(f'❌ Vercel function error: {e}')
            error_response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
