import json
import logging
from urllib.parse import urlparse
import requests
import shlex
import re
from bs4 import BeautifulSoup
import os

class CurlCrawler:
    def __init__(self):
        self.session = requests.Session()
        # Get user agent from environment variables
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    def curl_to_requests(self, curl_command):
        """Convert curl command to requests parameters"""
        try:
            # Remove 'curl' from the beginning if present
            if curl_command.startswith('curl '):
                curl_command = curl_command[5:]

            # Split the command into parts while preserving quoted strings
            parts = shlex.split(curl_command)

            method = 'GET'
            url = None
            headers = {}
            data = None
            params = {}

            i = 0
            while i < len(parts):
                part = parts[i]
                
                # Handle different curl options
                if part.startswith('--'):
                    option = part[2:]
                    if option == 'compressed':
                        headers['Accept-Encoding'] = 'gzip, deflate'
                    elif option in ['data', 'data-raw']:
                        method = 'POST'
                        data = parts[i + 1]
                        i += 1
                    elif option == 'header':
                        header_line = parts[i + 1]
                        key, value = header_line.split(':', 1)
                        headers[key.strip()] = value.strip()
                        i += 1
                elif part.startswith('-'):
                    for char in part[1:]:
                        if char == 'H':
                            header_line = parts[i + 1]
                            key, value = header_line.split(':', 1)
                            headers[key.strip()] = value.strip()
                            i += 1
                        elif char == 'X':
                            method = parts[i + 1]
                            i += 1
                        elif char == 'd':
                            method = 'POST'
                            data = parts[i + 1]
                            i += 1
                else:
                    # If not an option, assume it's the URL
                    url = part.strip("'\"")
                
                i += 1

            return {
                'method': method,
                'url': url,
                'headers': headers,
                'data': data,
                'params': params
            }
            
        except Exception as e:
            logging.error(f"Error converting curl command: {str(e)}")
            return None

    def extract_content_from_curl(self, curl_command):
        """Extract content using converted curl command"""
        try:
            # Convert curl to requests parameters
            req_params = self.curl_to_requests(curl_command)
            if not req_params:
                return None

            # Make the request
            response = self.session.request(
                method=req_params['method'],
                url=req_params['url'],
                headers=req_params['headers'],
                data=req_params['data'],
                params=req_params['params']
            )
            response.raise_for_status()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Basic text cleaning
            text = ' '.join(text.split())
            
            return text

        except Exception as e:
            logging.error(f"Error extracting content: {str(e)}")
            return None

    def extract_content(self, url_or_curl):
        """Extract content from either URL or curl command"""
        try:
            # Check if input is a curl command
            if url_or_curl.lower().startswith('curl '):
                return self.extract_content_from_curl(url_or_curl)
            
            # If it's a URL, create a simple curl command
            else:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                curl_command = f'curl "{url_or_curl}" -H "User-Agent: {headers["User-Agent"]}"'
                return self.extract_content_from_curl(curl_command)

        except Exception as e:
            logging.error(f"Error in extract_content: {str(e)}")
            return None

    def get_curl_from_browser(self, url):
        """Generate curl command from URL with browser-like headers"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        curl_parts = [f'curl "{url}"']
        for key, value in headers.items():
            curl_parts.append(f'-H "{key}: {value}"')
        
        return ' '.join(curl_parts) 

if __name__ == "__main__":
    # Example usage of CurlCrawler
    crawler = CurlCrawler()
    
    # Test URL
    test_url = "https://example.com"
    
    print("Testing CurlCrawler...")
    
    # 1. Generate curl command from URL
    print("\n1. Generating curl command:")
    curl_command = crawler.get_curl_from_browser(test_url)
    print(f"Generated curl command:\n{curl_command}")
    
    # 2. Extract content using URL
    print("\n2. Extracting content using URL:")
    content = crawler.extract_content(test_url)
    if content:
        print(f"Successfully extracted content (first 200 chars):\n{content[:200]}...")
    else:
        print("Failed to extract content")
    
    # 3. Test with a custom curl command
    print("\n3. Testing with custom curl command:")
    custom_curl = '''curl 'https://example.com' -H 'User-Agent: Mozilla/5.0' -H 'Accept: text/html' '''
    content = crawler.extract_content(custom_curl)
    if content:
        print(f"Successfully extracted content (first 200 chars):\n{content[:200]}...")
    else:
        print("Failed to extract content")
    
    # 4. Test curl command conversion
    print("\n4. Testing curl command conversion:")
    params = crawler.curl_to_requests(custom_curl)
    print("Converted curl command to requests parameters:")
    print(json.dumps(params, indent=2)) 