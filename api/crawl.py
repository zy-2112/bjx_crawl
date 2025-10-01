from http.server import BaseHTTPRequestHandler
import json
import subprocess
import os
import sys
from datetime import datetime
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def _send_email_notification(self, subject, text_content, csv_data=None):
        """Send email notification using Resend API"""
        try:
            resend_api_key = os.environ.get('RESEND_API_KEY')
            notification_email = os.environ.get('NOTIFICATION_EMAIL')
            
            if not resend_api_key or not notification_email:
                print("Email configuration not found. Skipping email notification.")
                return False
                
            # Prepare email data
            email_data = {
                "from": "BJX Crawler <notifications@resend.dev>",
                #"to": ['info@gaincue.com'],
                "to": [notification_email],
                "subject": subject,
                "text": text_content
            }
            
            # Add attachment if CSV data is provided
            if csv_data:
                import base64
                # Encode CSV data as base64 for attachment
                csv_base64 = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')
                email_data["attachments"] = [
                    {
                        "filename": "articles.xlsx",
                        "content": csv_base64
                    }
                ]
            
            # Send email via Resend API
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=email_data,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Email notification sent successfully")
                return True
            else:
                print(f"❌ Failed to send email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
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
                'OUTPUT_CSV': 'articles.xlsx',
                'VERCEL': '1'  # Signal to the crawler that we're in Vercel mode
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
                
                # Handle subprocess errors
                if result.returncode != 0:
                    error_response = {
                        'success': False,
                        'error': 'Crawler failed',
                        'details': {
                            'exitCode': result.returncode,
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'debug_info': debug_info
                        }
                    }
                    
                    # Send failure notification email
                    subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
                    text_content = f"""BJX QN Article Crawler FAILED

Crawl failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error Details:
- Exit Code: {result.returncode}
- Error: {result.stderr}

Please check the Vercel function logs for details.

---
Automated by Vercel Serverless Function
"""
                    self._send_email_notification(subject, text_content)
                    
                    self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
                    return
                else:
                    # Parse the JSON output from the crawler
                    try:
                        crawler_result = json.loads(result.stdout)
                        
                        # Check if it's an error response from our crawler
                        if isinstance(crawler_result, dict) and 'error' in crawler_result:
                            error_response = {
                                'success': False,
                                'error': crawler_result['error'],
                                'message': crawler_result.get('message', 'Crawler encountered an error'),
                                'details': {
                                    'crawler_details': crawler_result.get('details', ''),
                                    'stderr': result.stderr,
                                    'debug_info': debug_info
                                }
                            }
                            
                            # Send failure notification email
                            subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
                            text_content = f"""BJX QN Article Crawler FAILED

Crawl failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error: {crawler_result['error']}
Message: {crawler_result.get('message', 'Unknown error')}

Details: {crawler_result.get('details', 'No details provided')}

---
Automated by Vercel Serverless Function
"""
                            self._send_email_notification(subject, text_content)
                            
                            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
                            return
                        else:
                            # Handle successful response or fallback response with warning
                            # Convert articles to CSV format
                            import csv
                            import io
                            
                            csv_buffer = io.StringIO()
                            if crawler_result['articles']:
                                fieldnames = ['title', 'date', 'url']
                                writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(crawler_result['articles'])
                            csv_data = csv_buffer.getvalue()
                            csv_buffer.close()
                            
                            response = {
                                'success': True,
                                'message': f"Successfully crawled {crawler_result['total_articles_count']} articles",
                                'articlesCount': crawler_result['total_articles_count'],
                                'articles': crawler_result['articles'][:10],  # Return first 10 articles as preview
                                'csvData': csv_data,
                                'details': {
                                    'stdout': result.stdout,
                                    'stderr': result.stderr,
                                    'debug_info': debug_info
                                },
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Add warning if present
                            if 'warning' in crawler_result:
                                response['warning'] = crawler_result['warning']
                                response['message'] += f" ({crawler_result['warning']})"
                            
                            # Add network error flag if present
                            if crawler_result.get('network_error', False):
                                response['networkError'] = True
                            
                            # Send success notification email
                            subject = f"📰 BJX Articles Update - {datetime.now().strftime('%Y-%m-%d')} - {crawler_result['total_articles_count']} articles"
                            text_content = f"""BJX QN Article Crawler Results

Crawl completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Total articles in database: {crawler_result['total_articles_count']}

Latest Articles:
"""
                            for article in crawler_result['articles'][:5]:
                                text_content += f"• {article['title']} ({article['date']})\n"
                            
                            text_content += """

Please find the complete data in the attached CSV.

---
Automated by Vercel Serverless Function
"""
                            
                            self._send_email_notification(subject, text_content, csv_data)
                            
                            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                            return
                    except json.JSONDecodeError as e:
                        # If we can't parse the JSON, it might be an error message
                        error_response = {
                            'success': False,
                            'error': 'Failed to parse crawler output',
                            'details': {
                                'stdout': result.stdout,
                                'stderr': result.stderr,
                                'parse_error': str(e),
                                'debug_info': debug_info
                            }
                        }
                        
                        # Send failure notification email
                        subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
                        text_content = f"""BJX QN Article Crawler FAILED

Crawl failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error: Failed to parse crawler output
Parse Error: {str(e)}

Raw Output:
STDOUT: {result.stdout}
STDERR: {result.stderr}

---
Automated by Vercel Serverless Function
"""
                        self._send_email_notification(subject, text_content)
                        
                        self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
                        return
                
            except subprocess.TimeoutExpired:
                error_response = {
                    'success': False,
                    'error': 'Crawler timed out after 5 minutes',
                    'details': {
                        'stdout': 'Process was terminated due to timeout',
                        'stderr': 'Timeout occurred during crawling',
                        'debug_info': debug_info
                    }
                }
                
                # Send failure notification email
                subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
                text_content = f"""BJX QN Article Crawler FAILED

Crawl timed out after 5 minutes at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error: Process was terminated due to timeout
Details: Timeout occurred during crawling

---
Automated by Vercel Serverless Function
"""
                self._send_email_notification(subject, text_content)
                
                self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
                return
            except Exception as e:
                error_response = {
                    'success': False,
                    'error': f'Failed to run crawler: {str(e)}',
                    'details': {
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'debug_info': debug_info
                    }
                }
                
                # Send failure notification email
                subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
                text_content = f"""BJX QN Article Crawler FAILED

Crawl failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error: Failed to run crawler
Exception: {type(e).__name__}: {str(e)}

---
Automated by Vercel Serverless Function
"""
                self._send_email_notification(subject, text_content)
                
                self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))
                return
            
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
            
            # Send failure notification email
            subject = f"❌ BJX Crawler Failed - {datetime.now().strftime('%Y-%m-%d')}"
            text_content = f"""BJX QN Article Crawler FAILED

Server error at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error: Server error
Exception: {type(e).__name__}: {str(e)}

---
Automated by Vercel Serverless Function
"""
            self._send_email_notification(subject, text_content)
            
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
