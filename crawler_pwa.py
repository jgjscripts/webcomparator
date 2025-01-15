import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from urllib.parse import urlparse
import time
from webdriver_manager.chrome import ChromeDriverManager
import re
from bs4 import BeautifulSoup
import requests
import os

class PWAWebCrawler:
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

    def is_pwa_or_react(self, url):
        """Detect if the website is a PWA or React application"""
        try:
            # Use the same user agent in requests
            response = requests.get(url, headers={'User-Agent': self.user_agent})
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for PWA indicators
            pwa_indicators = [
                # Manifest file
                bool(soup.find('link', {'rel': 'manifest'})),
                # Service worker registration
                'serviceWorker' in response.text,
                # App-specific meta tags
                bool(soup.find('meta', {'name': 'apple-mobile-web-app-capable'})),
                bool(soup.find('meta', {'name': 'application-name'}))
            ]
            
            # Check for React indicators
            react_indicators = [
                # React-specific attributes
                bool(soup.find(attrs={'data-reactroot': True})),
                bool(soup.find(attrs={'data-reactid': True})),
                # Common React patterns
                'react' in response.text.lower(),
                '_reactRootContainer' in response.text,
                '__REACT_DEVTOOLS_GLOBAL_HOOK__' in response.text
            ]
            
            # If any PWA indicators are present
            is_pwa = any(pwa_indicators)
            # If any React indicators are present
            is_react = any(react_indicators)
            
            return is_pwa or is_react
            
        except Exception as e:
            logging.warning(f"Error detecting PWA/React for {url}: {str(e)}")
            return False

    def extract_content(self, url, wait_time=10, scroll=False):
        """Modified extract_content method"""
        # First check if it's a PWA/React site
        is_dynamic = self.is_pwa_or_react(url)
        
        if not is_dynamic:
            # If it's not a PWA/React site, use simple requests
            try:
                response = requests.get(url, headers={'User-Agent': self.chrome_options.arguments[-1].split('=')[1]})
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                # Get text content
                text = soup.get_text(separator=' ', strip=True)
                return ' '.join(text.split())
            except Exception as e:
                logging.error(f"Error crawling static site {url}: {str(e)}")
                return None

        # If it is a PWA/React site, use Selenium
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

            # Handle infinite scroll if required
            if scroll:
                self._scroll_to_bottom(driver)

            # Additional wait for React-specific elements
            try:
                WebDriverWait(driver, wait_time).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, 'div')) > 0
                )
            except TimeoutException:
                logging.warning("Timeout waiting for React elements, proceeding with available content")

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

    def _scroll_to_bottom(self, driver, max_scrolls=10):
        """Helper method to handle infinite scroll"""
        scrolls = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while scrolls < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
                
            last_height = new_height
            scrolls += 1

    async def login_if_required(self, driver, login_config):
        """Handle login for protected content"""
        try:
            if not login_config:
                return True

            driver.get(login_config['login_url'])
            
            # Wait for login form
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, login_config['username_selector']))
            )

            # Fill login form
            driver.find_element(By.CSS_SELECTOR, login_config['username_selector']).send_keys(login_config['username'])
            driver.find_element(By.CSS_SELECTOR, login_config['password_selector']).send_keys(login_config['password'])
            
            # Click login button
            driver.find_element(By.CSS_SELECTOR, login_config['submit_selector']).click()
            
            # Wait for login to complete
            WebDriverWait(driver, 10).until(
                EC.url_changes(login_config['login_url'])
            )
            
            return True

        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            return False

    def wait_for_specific_content(self, driver, selectors, wait_time=10):
        """Wait for specific React components to load"""
        try:
            for selector in selectors:
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            return True
        except TimeoutException:
            logging.warning(f"Timeout waiting for selectors: {selectors}")
            return False 

if __name__ == "__main__":
    # Example usage of PWAWebCrawler
    crawler = PWAWebCrawler()
    
    # Example URLs (one React site and one regular site)
    test_urls = [
        "https://reactjs.org",  # React site
        "https://example.com"   # Regular site
    ]
    
    print("Testing PWAWebCrawler...")
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        
        # Check if it's a PWA/React site
        is_pwa = crawler.is_pwa_or_react(url)
        print(f"Is PWA/React: {is_pwa}")
        
        # Extract content
        content = crawler.extract_content(url)
        if content:
            print(f"Successfully extracted content (first 200 chars):\n{content[:200]}...")
        else:
            print(f"Failed to extract content")
        
        # Example login config (commented out)
        """
        login_config = {
            'login_url': 'https://example.com/login',
            'username_selector': '#username',
            'password_selector': '#password',
            'submit_selector': '#login-button',
            'username': 'test_user',
            'password': 'test_pass'
        }
        """ 