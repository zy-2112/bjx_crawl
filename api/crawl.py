from http.server import BaseHTTPRequestHandler
import json
import subprocess
import os
import sys
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def _handle_request(self):
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # Get parameters from query string
            import urllib.parse
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            max_pages = query_params.get('max_pages', ['3'])[0]
            force_full_crawl = query_params.get('force_full_crawl', ['false'])[0]
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'MAX_PAGES': max_pages,
                'FORCE_FULL_CRAWL': force_full_crawl,
                'OUTPUT_JSON': 'articles.json',
                'OUTPUT_CSV': 'articles.csv'
            })
            
            # Debug information
            debug_info = {
                'cwd': os.getcwd(),
                'script_path': 'crawl_bjx_qn_incremental_ci.py',
                'full_script_path': os.path.join(os.getcwd(), 'crawl_bjx_qn_incremental_ci.py'),
                'script_exists': os.path.exists('crawl_bjx_qn_incremental_ci.py'),
                'files_in_dir': list(os.listdir('.')) if os.path.exists('.') else 'Directory not accessible',
                'python_executable': sys.executable,
                'max_pages': max_pages,
                'force_full_crawl': force_full_crawl
            }
            
            # Check if the crawler script exists
            if not os.path.exists('crawl_bjx_qn_incremental_ci.py'):
                response = {
                    'success': False,
                    'error': 'Crawler script not found',
                    'details': debug_info
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                return
            
            # Run the crawler
            try:
                result = subprocess.run(
                    [sys.executable, 'crawl_bjx_qn_incremental_ci.py'],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Enhanced error reporting
                if result.returncode != 0:
                    response = {
                        'success': False,
                        'error': 'Crawler failed',
                        'details': {
                            'exitCode': result.returncode,
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'debug_info': debug_info
                        }
                    }
                else:
                    # Check if output files exist
                    if not os.path.exists('articles.json'):
                        response = {
                            'success': False,
                            'error': 'Output files not created',
                            'details': {
                                'stdout': result.stdout,
                                'stderr': result.stderr,
                                'debug_info': debug_info
                            }
                        }
                    else:
                        # Read the results
                        with open('articles.json', 'r', encoding='utf-8') as f:
                            articles = json.load(f)
                        
                        with open('articles.csv', 'r', encoding='utf-8') as f:
                            csv_data = f.read()
                        
                        response = {
                            'success': True,
                            'message': f'Successfully crawled {len(articles)} articles',
                            'articlesCount': len(articles),
                            'articles': articles[:10],  # Return first 10 articles as preview
                            'csvData': csv_data,
                            'details': {
                                'stdout': result.stdout,
                                'stderr': result.stderr,
                                'debug_info': debug_info
                            },
                            'timestamp': datetime.now().isoformat()
                        }
                
            except subprocess.TimeoutExpired:
                response = {
                    'success': False,
                    'error': 'Crawler timed out after 5 minutes',
                    'details': {
                        'stdout': 'Process was terminated due to timeout',
                        'stderr': 'Timeout occurred during crawling',
                        'debug_info': debug_info
                    }
                }
            except Exception as e:
                response = {
                    'success': False,
                    'error': f'Failed to run crawler: {str(e)}',
                    'details': {
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'debug_info': debug_info
                    }
                }
            
            # Send response
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            error_response = {
                'success': False,
                'error': f'Server error: {str(e)}',
                'details': {
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                },
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
