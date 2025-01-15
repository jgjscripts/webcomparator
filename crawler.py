import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import urlparse
import time
from webdriver_manager.chrome import ChromeDriverManager
import os

class WebCrawler:
    def __init__(self):
        # Set up Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # Run in headless mode
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # Get user agent from environment variables
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.chrome_options.add_argument(f'user-agent={self.user_agent}')

    def extract_content(self, url, wait_time=10):
        driver = None
        try:
            # Validate URL
            if not urlparse(url).scheme:
                raise ValueError("Invalid URL format")

            # Initialize webdriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            # Set page load timeout
            driver.set_page_load_timeout(wait_time)
            
            # Navigate to URL
            driver.get(url)
            
            # Wait for React to render content
            time.sleep(3)  # Basic wait for React rendering
            
            # Wait for dynamic content to load
            WebDriverWait(driver, wait_time).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )

            # Additional wait for React-specific elements (modify selector based on your target website)
            try:
                WebDriverWait(driver, wait_time).until(
                    lambda driver: len(driver.find_elements('css selector', 'div')) > 0
                )
            except TimeoutException:
                logging.warning("Timeout waiting for React elements, proceeding with available content")

            # Get the rendered page source
            page_source = driver.page_source
            
            # Extract text content using JavaScript
            text_content = driver.execute_script("""
                function extractContent(element) {
                    const excludeTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME'];
                    if (excludeTags.includes(element.tagName)) return '';
                    
                    if (element.children.length === 0) {
                        return element.textContent.trim();
                    }
                    
                    let text = '';
                    for (let child of element.children) {
                        text += ' ' + extractContent(child);
                    }
                    return text.trim();
                }
                return extractContent(document.body);
            """)
            
            # Clean the text
            text_content = ' '.join(text_content.split())
            
            return text_content

        except Exception as e:
            logging.error(f"Error crawling {url}: {str(e)}")
            return None
            
        finally:
            if driver:
                driver.quit() 

if __name__ == "__main__":
    # Example usage of WebCrawler
    crawler = WebCrawler()
    
    # Example URLs
    test_urls = [
        "https://example.com",
        "https://python.org",
    ]
    
    print("Testing WebCrawler...")
    for url in test_urls:
        print(f"\nCrawling {url}:")
        content = crawler.extract_content(url)
        if content:
            print(f"Successfully extracted content (first 200 chars):\n{content[:200]}...")
        else:
            print(f"Failed to extract content from {url}") 